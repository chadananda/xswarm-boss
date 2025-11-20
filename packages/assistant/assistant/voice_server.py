# Copyright (c) Kyutai, all rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#
# Adapted from official moshi_mlx local.py for use with Textual TUI.

"""
Voice Server Process - Runs MLX inference in a separate process.

This mirrors the official local.py architecture where the ML model
runs in its own process to maximize Metal GPU utilization.
"""

import multiprocessing
import time
from pathlib import Path

import numpy as np
try:
    import mlx.core as mx
    import mlx.nn as nn
    import sentencepiece
    import huggingface_hub
    from moshi_mlx import models, utils
except ImportError:
    # Allow import for tests even if dependencies are missing
    pass


def hf_hub_download(repo, path: str) -> str:
    """Download file from HuggingFace hub."""
    if repo is None or repo == "":
        raise ValueError(f"the --hf-repo flag is required to retrieve {path}")
    return huggingface_hub.hf_hub_download(repo, path)


def server_process(
    client_to_server: multiprocessing.Queue,
    server_to_client: multiprocessing.Queue,
    status_queue: multiprocessing.Queue,
    hf_repo: str,
    quantized: int,
    max_steps: int = 2000
):
    """
    Server process that runs MLX inference.

    This is the "server" from local.py - it receives encoded audio codes,
    runs the LM model, and returns audio tokens for decoding.

    Args:
        client_to_server: Queue for receiving encoded audio from client
        server_to_client: Queue for sending audio tokens to client
        status_queue: Queue for sending status messages back to main process
        hf_repo: HuggingFace repo for model weights
        quantized: Quantization level (4 or 8) or None for bf16
        max_steps: Maximum generation steps
    """
    def log(msg):
        status_queue.put(("info", msg))

    try:
        # Download model files
        if quantized == 8:
            model_file = hf_hub_download(hf_repo, "model.q8.safetensors")
        elif quantized == 4:
            model_file = hf_hub_download(hf_repo, "model.q4.safetensors")
        elif quantized is None:
            model_file = hf_hub_download(hf_repo, "model.safetensors")
        else:
            raise ValueError(f"Invalid quantized value: {quantized}")

        tokenizer_file = hf_hub_download(hf_repo, "tokenizer_spm_32k_3.model")

        # Load text tokenizer
        log("Loading text tokenizer...")
        text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_file)

        # Initialize model
        mx.random.seed(299792458)
        lm_config = models.config_v0_1()
        model = models.Lm(lm_config)
        model.set_dtype(mx.bfloat16)

        # Apply quantization if needed
        if quantized is not None:
            group_size = 32 if quantized == 4 else 64
            nn.quantize(model, bits=quantized, group_size=group_size)

        # Load weights
        log("Loading model weights...")
        model.load_weights(model_file, strict=True)
        log("Weights loaded")

        # Warmup
        model.warmup()
        log("Model warmed up")

        # Create generator
        gen = models.LmGen(
            model=model,
            max_steps=max_steps + 5,
            text_sampler=utils.Sampler(),
            audio_sampler=utils.Sampler(),
            check=False,
        )

        # Signal ready
        server_to_client.put("ready")
        log("Server ready!")

        # Main inference loop
        while True:
            # Get encoded audio from client
            data = client_to_server.get()

            if data is None:
                # Shutdown signal
                break

            # Convert to MLX array and run inference
            # data comes in as (8, T) from encoder, need (1, 8, T) for Moshi
            data = mx.array(data)
            if len(data.shape) == 2:
                # Add batch dimension: (8, T) -> (1, 8, T)
                data = data[None, :, :]
            text_token = gen.step(data)
            text_token_id = text_token[0].item()

            # Get audio tokens
            audio_tokens = gen.last_audio_tokens()

            # Decode text token
            text_piece = ""
            if text_token_id not in (0, 3):
                text_piece = text_tokenizer.id_to_piece(text_token_id)
                text_piece = text_piece.replace("▁", " ")

            # Send results back
            if audio_tokens is not None:
                audio_tokens = np.array(audio_tokens).astype(np.uint32)
                server_to_client.put(("audio", audio_tokens, text_piece))
            else:
                server_to_client.put(("text", None, text_piece))

    except Exception as e:
        status_queue.put(("error", str(e)))
        import traceback
        traceback.print_exc()


def start_server_process(quality: str = "q4", max_steps: int = 2000):
    """
    Start the Voice server process.

    This should be called BEFORE Textual starts to avoid multiprocessing issues.

    Args:
        quality: "bf16", "q8", or "q4"
        max_steps: Maximum generation steps

    Returns:
        Tuple of (process, client_to_server, server_to_client, status_queue)
    """
    # Map quality to repo and quantization
    quality_map = {
        "bf16": ("kyutai/moshiko-mlx-bf16", None),
        "q8": ("kyutai/moshiko-mlx-q8", 8),
        "q4": ("kyutai/moshiko-mlx-q4", 4),
    }

    if quality not in quality_map:
        raise ValueError(f"Invalid quality: {quality}")

    hf_repo, quantized = quality_map[quality]

    # Create queues
    client_to_server = multiprocessing.Queue()
    server_to_client = multiprocessing.Queue()
    status_queue = multiprocessing.Queue()

    # Start server process
    process = multiprocessing.Process(
        target=server_process,
        args=(client_to_server, server_to_client, status_queue, hf_repo, quantized, max_steps),
        daemon=True
    )
    process.start()

    return process, client_to_server, server_to_client, status_queue
