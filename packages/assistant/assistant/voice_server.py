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
            try:
                data = client_to_server.get(timeout=0.1) # Faster timeout for checking
                log(f"DEBUG: Server received data: {type(data)}")
            except queue.Empty:
                continue
            except Exception as e:
                log(f"Error getting data: {e}")
                continue

            if isinstance(data, str) and data == "stop":
                break
                
            # Handle system prompts / persona injection
            if isinstance(data, tuple):
                msg_type = data[0]
                content = data[1]
                
                if msg_type == "system":
                    system_prompt = content
                    log(f"📝 Injecting system prompt: {len(system_prompt)} chars")
                    try:
                        # Encode the system prompt to text tokens
                        tokens = text_tokenizer.encode(system_prompt)
                        log(f"🎭 Priming model with {len(tokens)} text tokens...")
                        
                        # Prime the generator by forcing it to process these text tokens
                        # CRITICAL FIX: Use actual silence codes, not zeros (which is noise)
                        # Codes extracted from test_server_integration.py
                        silence_codes = [1685, 618, 1258, 701, 1725, 359, 1939, 782]
                        silence_audio = mx.array(silence_codes, dtype=mx.uint32).reshape(1, 8)
                        
                        for i, token in enumerate(tokens):
                            if gen.step_idx >= gen.max_steps:
                                log("⚠️ Reached max steps during priming")
                                break
                            
                            # Manually set the text token in the sequence
                            gen.gen_sequence[0, 0, gen.step_idx] = token
                            
                            # Step with silence to advance the generator
                            _ = gen.step(silence_audio)
                        
                        log(f"✅ Persona injected successfully ({len(tokens)} tokens)")
                        
                    except Exception as e:
                        log(f"❌ Failed to inject system prompt: {e}")
                        import traceback
                        log(traceback.format_exc())
                    continue
                    
                elif msg_type == "inject":
                    # Subconscious injection (Bicameral Thinking)
                    injection_text = content
                    log(f"💉 Processing injection: '{injection_text}'")
                    try:
                        tokens = text_tokenizer.encode(injection_text)
                        log(f"💉 Forcing {len(tokens)} tokens into stream...")
                        
                        # For injection during active conversation, we don't just prime.
                        # We need to set the NEXT text tokens that will be generated.
                        # But we can't easily "queue" them for future steps in this loop structure
                        # without modifying the LmGen class or maintaining a buffer here.
                        
                        # HACK: For now, we'll use the same priming approach but this might 
                        # cause a slight audio gap or "fast forward" effect if we do it 
                        # while audio is playing. 
                        # Ideally, we should have a 'forced_tokens' buffer that we check 
                        # inside the main inference loop below.
                        
                        # Let's try to just insert them into the sequence at the CURRENT step
                        # and advance the generator. This effectively makes Moshi "say" them
                        # immediately, consuming time steps.
                        
                        silence_audio = mx.zeros((1, 8), dtype=mx.uint32)
                        
                        for token in tokens:
                            if gen.step_idx >= gen.max_steps:
                                break
                                
                            # Force the token
                            gen.gen_sequence[0, 0, gen.step_idx] = token
                            
                            # Step to generate the audio for this token
                            _ = gen.step(silence_audio)
                            
                            # Send audio back
                            audio_tokens = gen.last_audio_tokens()
                            if audio_tokens is not None:
                                audio_arr = np.array(audio_tokens).astype(np.uint32)
                                server_to_client.put(("audio", audio_arr.T, None))
                                
                            # Send text back so client knows what was said
                            piece = text_tokenizer.decode(token)
                            piece = piece.replace(" ", " ")
                            if piece:
                                server_to_client.put(("text", None, piece))
                                
                        log(f"✅ Injection complete")
                        
                    except Exception as e:
                        log(f"❌ Failed to inject thought: {e}")
                    continue


            # Convert to MLX array
            # data comes in as (8, T) from encoder
            data = mx.array(data)
            
            # Ensure we have (1, 8, T) shape
            if len(data.shape) == 2:
                data = data[None, :, :]
            
            # Iterate over time steps
            # Moshi LmGen.step() expects (Batch=1, Codebooks=8) or (Batch=1, Codebooks=8, Time=1)
            # We must feed it one step at a time if T > 1
            
            T = data.shape[-1]
            
            # Lists to collect outputs if we process multiple steps
            all_audio_tokens = []
            last_text_piece = ""
            
            for t in range(T):
                # Extract single time step: (1, 8, 1) -> squeeze to (1, 8)
                # shape: (Batch, Codebooks, Time) -> slice -> (Batch, Codebooks)
                step_data = data[:, :, t] 
                
                try:
                    # Run inference step
                    text_token = gen.step(step_data)
                    text_token_id = text_token[0].item()
                    
                    # Collect audio tokens from this step
                    step_audio = gen.last_audio_tokens()
                    if step_audio is not None:
                        all_audio_tokens.append(np.array(step_audio).astype(np.uint32))
                    
                    # Decode text token (only keep the last one if multiple steps, 
                    # or accumulate? For now, let's just send the last one or all?
                    # Moshi usually generates text slower than audio, so text might be sparse.
                    # But we should probably send every text token.
                    
                    if text_token_id not in (0, 3):
                        piece = text_tokenizer.decode(text_token_id)
                        piece = piece.replace(" ", " ")
                        if piece:
                            # Send text immediately to avoid lag
                            server_to_client.put(("text", None, piece))
                            last_text_piece = piece

                except ValueError as e:
                    log(f"❌ Inference Error at step {t}: {e}")
                    continue

            # Send accumulated audio tokens
            if all_audio_tokens:
                # Stack audio tokens: List of (1, 8) -> (T, 8) or similar?
                # gen.last_audio_tokens() returns shape (1, 8) usually?
                # Let's check what client expects. 
                # Client expects (8, T) or (T, 8)? 
                # Audio tokenizer decode expects (8, T).
                
                # Concatenate along time dimension
                # Each step_audio is (1, 8) or (8,)
                # We want final shape (8, T)
                
                # Convert list of arrays to single array
                # [ (1, 8), (1, 8) ] -> (T, 8) -> transpose to (8, T)
                combined_audio = np.concatenate(all_audio_tokens, axis=0) # (T, 8)
                combined_audio = combined_audio.T # (8, T)
                
                if combined_audio.size > 0:
                    server_to_client.put(("audio", combined_audio, None))

    except Exception as e:
        status_queue.put(("error", str(e)))
        import traceback
        traceback.print_exc()


def start_server_process(quality: str = "q8", max_steps: int = 2000):
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

    # Use spawn context for macOS/MLX compatibility
    ctx = multiprocessing.get_context("spawn")

    # Create queues using the spawn context
    client_to_server = ctx.Queue()
    server_to_client = ctx.Queue()
    status_queue = ctx.Queue()

    # Start server process using the spawn context
    process = ctx.Process(
        target=server_process,
        args=(client_to_server, server_to_client, status_queue, hf_repo, quantized, max_steps),
        daemon=True
    )
    process.start()

    return process, client_to_server, server_to_client, status_queue
