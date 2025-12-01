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
import logging # Added by user instruction
import queue # Added to resolve missing import for queue.Empty

import numpy as np
import mlx.core as mx
import mlx.nn as nn
import sentencepiece
import huggingface_hub
from moshi_mlx import models, utils


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
    log_file: str = "/tmp/xswarm_voice_server.log",
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
        log_file: Path to log file
        max_steps: Maximum generation steps
    """
    import sys
    import os

    # CRITICAL: Redirect stdout/stderr to prevent TUI corruption
    # Must be done IMMEDIATELY before any other code runs
    sys.stdout = open(log_file, 'a')
    sys.stderr = sys.stdout

    # Also suppress any warnings
    import warnings
    warnings.filterwarnings("ignore")

    # Suppress HuggingFace warnings
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/xswarm_voice_server.log', mode='w'),
            # logging.StreamHandler() # Disabled to prevent TUI corruption
        ]
    )
    logger = logging.getLogger("voice_server")
    
    # Track last log message to avoid flooding with duplicates
    last_log_message = None
    duplicate_count = 0
    
    def log(msg):
        nonlocal last_log_message, duplicate_count
        
        # Skip if identical to previous message
        if msg == last_log_message:
            duplicate_count += 1
            # Only log every 100th duplicate to show we're still alive
            if duplicate_count % 100 == 0:
                summary = f"(repeated {duplicate_count} times)"
                logger.info(summary)
                status_queue.put(("info", f"LOG: {summary}"))
            return
        
        # New message - reset counter and log it
        if duplicate_count > 0:
            summary = f"(previous message repeated {duplicate_count} times total)"
            logger.info(summary)
            status_queue.put(("info", f"LOG: {summary}"))
            duplicate_count = 0
        
        last_log_message = msg
        logger.info(msg)
        status_queue.put(("info", f"LOG: {msg}"))

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

        # Create generator with large max_steps for long conversations
        # NOTE: This is a temporary fix. True duplex operation requires rearchitecting
        # the server to handle simultaneous input/output streams.
        gen = models.LmGen(
            model=model,
            max_steps=50000,  # Large enough for extended conversations
            text_sampler=utils.Sampler(),
            audio_sampler=utils.Sampler(),
            check=False,
        )

        # Signal ready
        server_to_client.put("ready")
        log("Server ready!")

        # Define silence tokens (8 codebooks, each with silence code 1685)
        # These codes represent silence in Moshi's audio vocabulary
        SILENCE_CODES = [1685, 618, 1258, 701, 1725, 359, 1939, 782]
        SILENCE_TOKENS = mx.array(SILENCE_CODES, dtype=mx.uint32).reshape(1, 8)
        
        # Pending input queue for multi-step audio chunks
        pending_input = queue.Queue()
        
        log("🔄 Starting continuous duplex generation loop...")
        step_count = 0
        client_connected = False  # Wait for first client message before generating
        
        # CONTINUOUS GENERATION LOOP (True Duplex)
        # This loop NEVER blocks - it always generates, feeding silence when no user audio
        while True:
            # 1. GET USER AUDIO (non-blocking)
            user_tokens = None
            
            # Check for stop signal
            try:
                data = client_to_server.get_nowait()
                
                if isinstance(data, str) and data == "stop":
                    log("🛑 Received stop signal")
                    break
                
                # Handle tuples (system prompts, text input, etc)
                if isinstance(data, tuple):
                    msg_type = data[0]
                    text = data[1]
                    
                    if msg_type == "user_text":
                        # User text input - treat as if spoken
                        # We tokenize it and feed it to the model, then let it generate a response
                        log(f"💬 Processing user text: {text[:50]}...")
                        try:
                            # Tokenize text
                            ids = text_tokenizer.encode(text)
                            text_tokens = mx.array(ids)
                            
                            # Feed tokens as user input (this will trigger a response)
                            for i in range(len(ids)):
                                token = text_tokens[i].reshape(1, 1)
                                # Feed with silence audio, model will generate response
                                gen.step(SILENCE_TOKENS, token)
                                
                            log(f"✅ Processed {len(ids)} user text tokens")
                        except Exception as e:
                            log(f"❌ User text processing failed: {e}")
                        # DON'T continue - let the loop generate response
                        
                    elif msg_type == "inject" or msg_type == "system":
                        log(f"💉 Processing {msg_type}: {text[:50]}...")
                        try:
                            # Tokenize text
                            ids = text_tokenizer.encode(text)
                            text_tokens = mx.array(ids)
                            
                            # Feed tokens into the generator
                            # We feed them alongside silence audio tokens
                            # This effectively "forces" the model to process this text context
                            for i in range(len(ids)):
                                token = text_tokens[i].reshape(1, 1)
                                # Assuming gen.step(audio_tokens, text_tokens) signature
                                # We discard the output during injection as we are "forcing" context
                                gen.step(SILENCE_TOKENS, token)
                                
                            log(f"✅ Processed {len(ids)} tokens for {msg_type}")
                        except Exception as e:
                            log(f"❌ Processing failed: {e}")
                        continue
                
                # Normal audio data
                if isinstance(data, np.ndarray):
                    client_connected = True  # Mark client as connected
                    data = mx.array(data)
                    
                    # Ensure shape is (1, 8, T)
                    if len(data.shape) == 2:
                        data = data[None, :, :]
                    
                    T = data.shape[-1]
                    
                    # Use first time step immediately
                    user_tokens = data[:, :, 0]
                    
                    # Queue remaining time steps for future iterations
                    for t in range(1, T):
                        pending_input.put(data[:, :, t])
                        
            except queue.Empty:
                pass
            except Exception as e:
                log(f"Error reading input: {e}")
            
            # WAIT FOR CLIENT CONNECTION before generating
            if not client_connected:
                # Sleep briefly to avoid busy-waiting
                time.sleep(0.001)
                continue
            
            # 2. CHECK PENDING QUEUE if we didn't get fresh input
            if user_tokens is None:
                try:
                    user_tokens = pending_input.get_nowait()
                except queue.Empty:
                    # Use silence when no input available
                    user_tokens = SILENCE_TOKENS
            
            # 3. STEP GENERATOR (ALWAYS - this is the key to duplex)
            try:
                text_token = gen.step(user_tokens)
                text_token_id = text_token[0].item()
                step_count += 1
                
                # Log progress occasionally
                if step_count % 1000 == 0:
                    log(f"Generated {step_count} steps, queue size: {pending_input.qsize()}")
                
            except ValueError as e:
                if "reached max-steps" in str(e):
                    log(f"❌ Reached max steps ({gen.max_steps}) - this shouldn't happen with 50000 limit")
                else:
                    log(f"❌ Generation error: {e}")
                continue
            
            # 4. STREAM AUDIO OUTPUT (immediately)
            audio_tokens = gen.last_audio_tokens()
            if audio_tokens is not None:
                audio_arr = np.array(audio_tokens).astype(np.uint32)
                # Reshape to (8, T) format for client
                if audio_arr.ndim == 2 and audio_arr.shape[0] != 8:
                    audio_arr = audio_arr.T
                
                try:
                    server_to_client.put_nowait(("audio", audio_arr, None))
                except queue.Full:
                    log("⚠️ Output queue full, dropping audio frame")
            
            # 5. STREAM TEXT OUTPUT (immediately)
            if text_token_id not in (0, 3):  # Skip special tokens
                try:
                    # Use id_to_piece to get the raw token string (e.g., " world" -> "\u2581world")
                    # This preserves the spacing information which is critical for reconstruction
                    piece = text_tokenizer.id_to_piece(text_token_id)
                    
                    # Replace the SentencePiece space marker (U+2581) with a normal space
                    # Note: Punctuation usually attaches to the previous word (no leading space)
                    # Words usually start with a leading space
                    piece = piece.replace("\u2581", " ")
                    
                    if piece:
                        server_to_client.put_nowait(("text", None, piece))
                except queue.Full:
                    pass  # Silently drop text if queue full
                except Exception as e:
                    log(f"Text decode error: {e}")



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
    import sys
    import os

    # CRITICAL: Suppress all output during multiprocessing spawn
    # This prevents TUI corruption from spawn-related errors/warnings
    os.environ["PYTHONWARNINGS"] = "ignore"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

    # Map quality to repo and quantization
    quality_map = {
        "bf16": ("kyutai/moshiko-mlx-bf16", None),
        "q8": ("kyutai/moshiko-mlx-q8", 8),
        "q4": ("kyutai/moshiko-mlx-q4", 4),
    }

    if quality not in quality_map:
        raise ValueError(f"Invalid quality: {quality}")

    hf_repo, quantized = quality_map[quality]

    # Use spawn context for macOS/MLX compatibility
    ctx = multiprocessing.get_context("spawn")

    # Create queues using the spawn context
    client_to_server = ctx.Queue()
    server_to_client = ctx.Queue()
    status_queue = ctx.Queue()

    log_file = "/tmp/xswarm_voice_server.log"

    # Start server process using the spawn context
    process = ctx.Process(
        target=server_process,
        args=(client_to_server, server_to_client, status_queue, hf_repo, quantized, log_file, max_steps),
        daemon=True
    )

    # Redirect stderr during process start to prevent TUI corruption
    old_stderr = sys.stderr
    try:
        sys.stderr = open(log_file, 'a')
        process.start()
    finally:
        sys.stderr.close()
        sys.stderr = old_stderr

    return process, client_to_server, server_to_client, status_queue
