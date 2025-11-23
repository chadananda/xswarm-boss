"""
Core Voice Module.
Consolidated from previous voice/ package.
Includes:
- Moshi Bridge (MLX Inference)
- Moshi Client (Audio/Codec handling)
- Conversation Loop (VAD -> STT -> AI -> TTS)
- Voice Bridge Orchestrator (High-level management)
"""

import asyncio
import numpy as np
import queue
import time
import os
import threading
from enum import Enum
from typing import Optional, Callable, Dict, Any, AsyncGenerator, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Third-party imports
import sentencepiece
import huggingface_hub
import backoff

# Local imports
from .audio import AudioIO, VoiceActivityDetector
from .memory import MemoryManager, MemoryOrchestrator
from .tools import registry, CommandParser, ToolExecutor
# Note: Persona imports will be updated when personas are consolidated.
# For now, assuming they are still in ..personas
from .personas.manager import PersonaManager
from .personas.config import PersonaConfig

# MLX imports (try/except for safety)
try:
    import mlx.core as mx
    import mlx.nn as nn
    import rustymimi
    from moshi_mlx import models, utils
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
except ImportError:
    # Allow import without MLX for non-Mac systems or build steps
    pass

# ==============================================================================
# MOSHI BRIDGE (MLX Inference)
# ==============================================================================

def _create_download_with_retry():
    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, TimeoutError, HfHubHTTPError, OSError),
        max_time=None,
        max_value=300,
        on_backoff=lambda details: print(f"  ↻ Download retry #{details['tries']} after {details['wait']:.1f}s...")
    )
    def download_with_retry(repo_id: str, filename: str) -> str:
        return hf_hub_download(repo_id=repo_id, filename=filename, resume_download=True)
    return download_with_retry

class MoshiBridge:
    """MLX MOSHI bridge optimized for Apple Silicon."""
    def __init__(self, hf_repo: Optional[str] = None, quantized: Optional[int] = None, max_steps: int = 500, sample_rate: int = 24000, quality: str = "auto", progress_callback: Optional[callable] = None):
        print(f"🚀 Starting Moshi initialization (quality={quality})...")
        
        if quality == "auto":
            # Simplified auto-detection logic or default to q4 for safety if detector missing
            try:
                from .hardware import detect_gpu_capability, select_services
                gpu = detect_gpu_capability()
                config = select_services(gpu)
                quality = config.moshi_quality
            except ImportError:
                quality = "q4"

        quality_map = {
            "bf16": ("kyutai/moshiko-mlx-bf16", None, "model.safetensors"),
            "q8": ("kyutai/moshiko-mlx-bf16", 8, "model.safetensors"),
            "q4": ("kyutai/moshiko-mlx-bf16", 4, "model.safetensors"),
        }
        
        if quality not in quality_map:
            quality = "q4" # Fallback

        self.quality = quality
        default_repo, default_quant, default_file = quality_map[quality]
        self.hf_repo = hf_repo or default_repo
        self.quantized = quantized if quantized is not None else default_quant
        self.max_steps = max_steps
        self.sample_rate = sample_rate
        self.frame_size = 1920

        download = _create_download_with_retry()
        
        try:
            model_file = hf_hub_download(self.hf_repo, default_file, local_files_only=True)
            mimi_file = hf_hub_download(self.hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors", local_files_only=True)
            tokenizer_file = hf_hub_download(self.hf_repo, "tokenizer_spm_32k_3.model", local_files_only=True)
        except Exception:
            print("Downloading Moshi models...")
            model_file = download(self.hf_repo, default_file)
            mimi_file = download(self.hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")
            tokenizer_file = download(self.hf_repo, "tokenizer_spm_32k_3.model")

        self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_file)
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)

        mx.random.seed(299792458)
        lm_config = models.config_v0_1()
        self.model = models.Lm(lm_config)
        self.model.set_dtype(mx.bfloat16)

        if self.quantized is not None:
            group_size = 32 if self.quantized == 4 else 64
            nn.quantize(self.model, bits=self.quantized, group_size=group_size)

        self.model.load_weights(model_file, strict=True)
        self.model.warmup()

        self.mic_amplitude = 0.0
        self.moshi_amplitude = 0.0

    def encode_audio(self, audio: np.ndarray) -> np.ndarray:
        audio = audio.astype(np.float32)
        self.audio_tokenizer.encode(audio)
        while True:
            codes = self.audio_tokenizer.get_encoded()
            if codes is not None:
                return codes
            time.sleep(0.001)

    def decode_audio(self, codes: np.ndarray) -> np.ndarray:
        self.audio_tokenizer.decode(codes)
        while True:
            audio = self.audio_tokenizer.get_decoded()
            if audio is not None:
                return audio
            time.sleep(0.001)

    def generate_response(self, user_audio: np.ndarray, text_prompt: Optional[str] = None, max_frames: int = 125) -> tuple[np.ndarray, str]:
        frame_size = self.frame_size
        audio_len = len(user_audio)
        if audio_len % frame_size != 0:
            pad_len = frame_size - (audio_len % frame_size)
            user_audio = np.pad(user_audio, (0, pad_len), mode='constant')

        all_input_codes = []
        for offset in range(0, len(user_audio), frame_size):
            frame = user_audio[offset:offset + frame_size].astype(np.float32)
            codes = self.encode_audio(frame)
            all_input_codes.append(codes)

        lm_gen = models.LmGen(
            model=self.model,
            max_steps=min(len(all_input_codes) + max_frames, self.max_steps),
            text_sampler=utils.Sampler(),
            audio_sampler=utils.Sampler(),
            batch_size=1,
            check=False
        )

        output_audio_chunks = []
        text_tokens_list = []

        for input_codes in all_input_codes:
            audio_codes_mx = mx.array(input_codes).transpose(1, 0)[:, :8]
            text_token = lm_gen.step(audio_codes_mx)
            text_token_id = text_token[0].item()
            if text_token_id not in (0, 3):
                text_tokens_list.append(text_token_id)
            audio_tokens = lm_gen.last_audio_tokens()
            if audio_tokens is not None:
                audio_tokens_np = np.array(audio_tokens).astype(np.uint32)
                audio_chunk = self.decode_audio(audio_tokens_np)
                output_audio_chunks.append(audio_chunk)

        for _ in range(max_frames):
            silence_codes = mx.zeros((1, 8), dtype=mx.int32)
            text_token = lm_gen.step(silence_codes)
            text_token_id = text_token[0].item()
            if text_token_id not in (0, 3):
                text_tokens_list.append(text_token_id)
            audio_tokens = lm_gen.last_audio_tokens()
            if audio_tokens is not None:
                audio_tokens_np = np.array(audio_tokens).astype(np.uint32)
                audio_chunk = self.decode_audio(audio_tokens_np)
                output_audio_chunks.append(audio_chunk)

        response_audio = np.concatenate(output_audio_chunks) if output_audio_chunks else np.array([], dtype=np.float32)
        response_text = "".join([self.text_tokenizer.id_to_piece(tid).replace(" ", " ") for tid in text_tokens_list]) if text_tokens_list else ""
        return response_audio, response_text

    def get_amplitude(self, audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio ** 2))
        return float(np.clip(rms * 4, 0, 1))

    def update_mic_amplitude(self, audio: np.ndarray):
        self.mic_amplitude = self.get_amplitude(audio)

    def update_moshi_amplitude(self, audio: np.ndarray):
        self.moshi_amplitude = self.get_amplitude(audio)


# ==============================================================================
# MOSHI CLIENT (Audio/Codec Handling)
# ==============================================================================

class MoshiClient:
    """Client that handles audio codec and communicates with server process."""
    def __init__(self, client_to_server, server_to_client, hf_repo: str = "kyutai/moshiko-mlx-bf16", mimi_file: Optional[str] = None, log_callback: Optional[Callable[[str], None]] = None):
        self.client_to_server = client_to_server
        self.server_to_client = server_to_client
        self.log_callback = log_callback
        if mimi_file is None:
            mimi_file = hf_hub_download(hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.on_output_audio: Optional[Callable[[np.ndarray], None]] = None
        self.on_text_token: Optional[Callable[[str], None]] = None
        self._running = False
        self.mic_amplitude = 0.0
        self.moshi_amplitude = 0.0

    def log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)

    def get_amplitude(self, audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio ** 2))
        return float(np.clip(rms * 4, 0, 1))

    def update_mic_amplitude(self, audio: np.ndarray):
        self.mic_amplitude = self.get_amplitude(audio)

    def update_moshi_amplitude(self, audio: np.ndarray):
        self.moshi_amplitude = self.get_amplitude(audio)

    def feed_audio(self, audio: np.ndarray):
        self.input_queue.put_nowait(audio.astype(np.float32))

    def get_output_audio(self) -> Optional[np.ndarray]:
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    def wait_for_ready(self, timeout: float = 30.0) -> bool:
        """Wait for server ready signal."""
        self.log("⏳ Waiting for voice server to be ready...")
        try:
            msg = self.server_to_client.get(timeout=timeout)
            if msg == "ready":
                self.log("✅ Voice server is ready!")
                return True
            else:
                self.log(f"⚠️ Unexpected initial message from voice server: {msg}")
                # If it's not ready, maybe it's data? Put it back? 
                # No, if it's not ready, we probably shouldn't start.
                return False
        except queue.Empty:
            self.log("❌ Timed out waiting for voice server ready signal")
            return False

    def set_persona(self, system_prompt: str):
        """Send system prompt/persona to the server."""
        if self.client_to_server:
            self.log(f"🎭 Setting persona: {len(system_prompt)} chars")
            self.client_to_server.put(("system", system_prompt))

    def inject_text(self, text: str):
        """Send text to be injected into the stream."""
        if self.client_to_server:
            self.log(f"💉 Injecting text: {len(text)} chars")
            self.client_to_server.put(("inject", text))
            
    async def run_async_loops(self):
        self._running = True
        async def send_loop():
            while self._running:
                await asyncio.sleep(0.001)
                try:
                    pcm_data = self.input_queue.get(block=False)
                    
                    # DEBUG: Log mic input
                    rms = np.sqrt(np.mean(pcm_data**2))
                    if rms > 0.01:
                        # self.log(f"🎤 Mic Input: {len(pcm_data)} samples, RMS={rms:.4f}")
                        pass
                        
                    self.audio_tokenizer.encode(pcm_data)
                except queue.Empty:
                    continue
        async def send_loop2():
            while self._running:
                data = self.audio_tokenizer.get_encoded()
                if data is None:
                    await asyncio.sleep(0.001)
                    continue
                # self.log(f"DEBUG: Client sending codes: {data.shape}")
                self.client_to_server.put_nowait(data)
        async def recv_loop2():
            while self._running:
                try:
                    result = self.server_to_client.get(block=False)
                except queue.Empty:
                    await asyncio.sleep(0.001)
                    continue
                
                # Robust unpacking
                if isinstance(result, str):
                    if result == "ready":
                        # Should have been consumed by wait_for_ready, but ignore if late
                        continue
                    self.log(f"⚠️ Unknown string message: {result}")
                    continue
                    
                if not isinstance(result, (tuple, list)) or len(result) != 3:
                    self.log(f"⚠️ Invalid message format: {result}")
                    continue
                    
                msg_type, audio_tokens, text_piece = result
                # self.log(f"DEBUG: Recv {msg_type} | Audio: {len(audio_tokens) if audio_tokens is not None else 0} | Text: {text_piece}")
                if text_piece and self.on_text_token:
                    self.on_text_token(text_piece)
                if audio_tokens is not None and audio_tokens.size > 0:
                    # rustymimi expects (8, 1) frames. If we have (8, T), slice it.
                    if len(audio_tokens.shape) == 2 and audio_tokens.shape[0] == 8:
                        T = audio_tokens.shape[1]
                        for t in range(T):
                            frame = audio_tokens[:, t]  # (8,)
                            # rustymimi expects (Time, Codebooks) = (1, 8)
                            frame = frame[None, :] # (1, 8)
                            frame = frame.astype(np.uint32)
                            
                            if not frame.flags['C_CONTIGUOUS']:
                                frame = np.ascontiguousarray(frame)
                            self.audio_tokenizer.decode(frame)
                    else:
                        # Fallback
                        audio_tokens = audio_tokens.astype(np.uint32)
                        if not audio_tokens.flags['C_CONTIGUOUS']:
                            audio_tokens = np.ascontiguousarray(audio_tokens)
                        self.audio_tokenizer.decode(audio_tokens)
                
        async def recv_loop():
            while self._running:
                data = self.audio_tokenizer.get_decoded()
                if data is None:
                    await asyncio.sleep(0.001)
                    continue
                
                # DEBUG: Check data type and range
                print(f"🎵 recv_loop: dtype={data.dtype}, min={np.min(data):.4f}, max={np.max(data):.4f}, rms={np.sqrt(np.mean(data**2)):.4f}")
                
                # Sanitize decoded audio - ENSURE float32
                data = np.asarray(data, dtype=np.float32)
                
                # Check for NaN/Inf
                if not np.isfinite(data).all():
                    self.log("⚠️ Warning: Decoded audio contains NaN/Inf! Replacing with silence.")
                    data = np.zeros_like(data)
                
                # Clip to [-1, 1] to prevent distortion
                data = np.clip(data, -1.0, 1.0)

                # Noise Gate: Silence very quiet audio to prevent white noise
                rms = np.sqrt(np.mean(data**2))
                
                # DEBUG: Log every chunk's RMS to see what's happening
                # self.log(f"🔊 Audio Out RMS: {rms:.4f}")

                # Hiss floor is around 0.04 RMS. 
                # User reported 0.05 was cutting off speech. Lowering to 0.01 for now.
                if rms < 0.01: 
                    data = np.zeros_like(data)
                elif rms < 0.04:
                     # Soft knee / expansion for the hiss zone?
                     # For now just let it through so we can hear if it's working
                     pass
                
                # DEBUG: Log audio stats occasionally
                if np.random.random() < 0.005:
                    self.log(f"🔊 Decoded Audio: Shape={data.shape}, RMS={rms:.4f}")

                self.output_queue.put_nowait(data)
                if self.on_output_audio:
                    self.on_output_audio(data)
        await asyncio.gather(send_loop(), send_loop2(), recv_loop(), recv_loop2())

    def stop(self):
        self._running = False


# ==============================================================================
# SUBCONSCIOUS BRIDGE (Bicameral Thinking)
# ==============================================================================




# ==============================================================================
# CONVERSATION LOOP
# ==============================================================================

@dataclass
class ConversationTurn:
    user_text: str
    assistant_text: str
    persona_name: str
    timestamp: float
    user_audio: Optional[np.ndarray] = None
    assistant_audio: Optional[np.ndarray] = None
    metadata: Optional[Dict[str, Any]] = None

class AIClient:
    """Unified AI client wrapper."""
    def __init__(self, config):
        self.config = config
        self.provider = None
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if getattr(self.config, 'anthropic_api_key', None):
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=self.config.anthropic_api_key)
                self.provider = "anthropic"
                return
            except ImportError:
                pass
        if getattr(self.config, 'openai_api_key', None):
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
                self.provider = "openai"
                return
            except ImportError:
                pass

    async def chat(self, messages: list, max_tokens: int = 1024) -> str:
        if self.provider == "anthropic":
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
            conversation = [m for m in messages if m["role"] != "system"]
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022", max_tokens=max_tokens, messages=conversation, system=system_msg
            )
            return response.content[0].text
        elif self.provider == "openai":
            response = await self.client.chat.completions.create(
                model="gpt-4o", messages=messages, max_tokens=max_tokens
            )
            return response.choices[0].message.content
        raise RuntimeError("AI client not initialized")

    def is_available(self) -> bool:
        return self.client is not None

# ==============================================================================
# SUBCONSCIOUS BRIDGE (Bicameral Thinking)
# ==============================================================================

class SubconsciousBridge:
    """
    The 'System 2' bridge that monitors the conversation and injects thoughts.
    """
    def __init__(self, moshi_client: MoshiClient, ai_client: AIClient, tokenizer):
        self.moshi = moshi_client
        self.ai = ai_client
        self.tokenizer = tokenizer # SentencePiece processor
        self.transcript_buffer = ""
        self.last_injection_time = 0
        self.running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Phrases to smooth the insertion of external memories
        self.pivots = [
            " actually, I just realized ",
            " oh, and looking at the details, ",
            " wait, I recall that ",
            " correction, "
        ]

    async def start(self):
        self.running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        print("🧠 Subconscious Bridge started")

    def stop(self):
        self.running = False
        if self._monitor_task:
            self._monitor_task.cancel()

    def add_to_transcript(self, text: str):
        self.transcript_buffer += text
        # Keep buffer size manageable
        if len(self.transcript_buffer) > 2000:
            self.transcript_buffer = self.transcript_buffer[-2000:]

    async def _monitor_loop(self):
        """
        Constantly watches the transcript. If it sees a need for RAG/Reasoning,
        it queries Anthropic and queues the result.
        """
        while self.running:
            await asyncio.sleep(2.0) # Check every 2 seconds
            
            # Simple heuristic: if buffer changed significantly since last check?
            # For now, let's just rely on VAD or other signals if we had them.
            # Here we'll just do a random check if we have enough context
            # In a real implementation, we'd want smarter triggers.
            
            if len(self.transcript_buffer) > 50 and (time.time() - self.last_injection_time > 10):
                # Only query if we haven't injected recently
                # await self._query_brain()
                pass

    async def trigger_thought(self, context_override: Optional[str] = None):
        """Manually trigger a thought process (e.g. from a tool or specific event)."""
        await self._query_brain(context_override)

    async def _query_brain(self, context_override: Optional[str] = None):
        if not self.ai or not self.ai.is_available():
            return

        # This prompt is critical. It tells Anthropic to be a "silent observer"
        system_prompt = (
            "You are the subconscious memory of an AI assistant. "
            "Read the current transcript. If the assistant is missing a fact "
            "or needs to use a tool, output the CORRECT sentence to say next. "
            "If the conversation is fine, output NOTHING."
        )
        
        transcript = context_override or self.transcript_buffer[-1000:]
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Transcript so far: {transcript}"}
            ]
            
            # Use a quick model if possible, or just the main one
            response_text = await self.ai.chat(messages, max_tokens=100)
            
            if response_text and len(response_text) > 5 and "NOTHING" not in response_text:
                # We found a thought!
                await self._inject_thought(response_text)
                
        except Exception as e:
            print(f"🧠 Subconscious error: {e}")

    async def _inject_thought(self, text: str):
        # Wrap it in a pivot
        import random
        pivot = random.choice(self.pivots)
        full_thought = f"{pivot}{text}"
        
        print(f"🧠 Injecting thought: '{full_thought}'")
        
        self.moshi.inject_text(full_thought)
        self.last_injection_time = time.time()

    async def inject_persona(self, persona_text: str):
        """
        Injects the full persona description as a thought.
        This is called shortly after startup to 'inception' the personality.
        """
        # We don't use a pivot for this, or we use a specific one.
        # "I am..." is a strong affirmation.
        
        # If the text is very long, we might want to summarize it or break it up.
        # For now, let's inject the core identity.
        
        print(f"🧠 Injecting Persona: {len(persona_text)} chars")
        
        # We frame it as an internal monologue of self-definition.
        # Moshi will 'think' this text, effectively becoming it.
        # We prefix with a space to ensure clean tokenization if needed.
        
        # Example: " I am Jarvis. My personality is..."
        
        # We strip "You are" if present and replace with "I am"
        if persona_text.startswith("You are"):
            persona_text = "I am" + persona_text[7:]
            
        full_thought = f" {persona_text}"
        
        self.moshi.inject_text(full_thought)
        self.last_injection_time = time.time()

class ConversationLoop:
    """Manages the conversation loop with VAD -> STT -> AI -> TTS -> Output."""
    def __init__(self, moshi_bridge: MoshiBridge, persona_manager: PersonaManager, memory_manager: MemoryManager, ai_client: AIClient, memory_orchestrator: Optional[MemoryOrchestrator] = None, subconscious_bridge: Optional['SubconsciousBridge'] = None, user_id: str = "default", on_turn_complete: Optional[Callable[[ConversationTurn], None]] = None, on_state_change: Optional[Callable[[str], None]] = None, log_callback: Optional[Callable[[str], None]] = None):
        self.moshi = moshi_bridge
        self.persona = persona_manager
        self.memory = memory_manager
        self.ai = ai_client
        self.memory_orchestrator = memory_orchestrator
        self.subconscious = subconscious_bridge
        self.user_id = user_id
        self.on_turn_complete = on_turn_complete
        self.on_state_change = on_state_change
        self.log_callback = log_callback
        self.audio_io = AudioIO(log_callback=self.log_callback)
        self.vad = VoiceActivityDetector()
        self.tool_executor = ToolExecutor(registry)
        self.command_parser = CommandParser()
        self.running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._audio_buffer = []
        self._is_listening = False

    def log(self, msg: str):
        print(msg)
        if self.log_callback:
            self.log_callback(msg)

    async def start(self):
        self.running = True
        try:
            self.audio_io.start_input(callback=self._on_audio_frame)
            self.audio_io.start_output()
            self.log("✅ Audio streams started")
        except Exception as e:
            # Handle microphone permission errors gracefully
            error_msg = str(e)
            if "PortAudio" in error_msg or "InputStream" in error_msg:
                print(f"⚠️  Microphone access error: {error_msg}")
                print("   Voice features disabled. Please grant microphone permission in System Settings.")
                # Continue without voice - app can still function
                self.running = False
                raise RuntimeError(f"Microphone access denied: {error_msg}")
            else:
                raise
        
        # Enable listening AFTER audio streams are started
        self._is_listening = True
        print("✅ Listening enabled - ready to capture audio")
        
        # Register Moshi callbacks
        if hasattr(self.moshi, 'on_output_audio'):
            self.moshi.on_output_audio = self._on_moshi_audio
        if hasattr(self.moshi, 'on_text_token'):
            self.moshi.on_text_token = self._on_moshi_text
            
        # Start Moshi async loops if available (MoshiClient)
        if hasattr(self.moshi, 'run_async_loops'):
            self._loop_task = asyncio.create_task(self.moshi.run_async_loops())
            self.log("🔄 Moshi Client Async Loops Started")
        else:
            # Fallback for local bridge (if any)
            self._loop_task = asyncio.create_task(self._conversation_loop_legacy())
            
        self._set_state("listening")

    async def stop(self):
        self._running = False # Assuming _running is the new internal state variable
        if self.audio_io:
            self.audio_io.stop()
        
        # Stop client (assuming self.client refers to MoshiBridgeProxy or similar)
        if hasattr(self.moshi, 'stop'): # Check if moshi has a stop method
            self.moshi.stop()

        # Fix multiprocessing queue hang: Cancel join threads to prevent deadlock
        if self.voice_queues:
            for q in self.voice_queues:
                try:
                    if hasattr(q, 'cancel_join_thread'):
                        q.cancel_join_thread()
                    if hasattr(q, 'close'):
                        q.close()
                except Exception as e:
                    self.log(f"⚠️ Error closing queue: {e}")

        # Terminate server process aggressively
        if hasattr(self.moshi, 'server_process') and self.moshi.server_process and self.moshi.server_process.is_alive():
            self.log("🔌 Terminating voice server process...")
            self.moshi.server_process.terminate()
            self.moshi.server_process.join(timeout=1.0)
            if self.moshi.server_process.is_alive():
                self.log("💀 Kill voice server process...")
                self.moshi.server_process.kill()
        
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        
        self.log("✅ Voice bridge stopped.")
        self._set_state("idle")

    def _on_audio_frame(self, audio: np.ndarray):
        """Callback for each audio frame from microphone"""
        # Always process audio for duplex communication
        # if not self._is_listening:
        #     return
        
        # Update amplitude for visualization (USER INPUT)
        if hasattr(self.moshi, 'update_mic_amplitude'):
            self.moshi.update_mic_amplitude(audio)
        
        # Feed audio to Moshi
        if hasattr(self.moshi, 'feed_audio'):
            self.moshi.feed_audio(audio)

    def _on_moshi_audio(self, audio: np.ndarray):
        """Callback for audio received from Moshi"""
        # self.log(f"DEBUG: Playing audio chunk {audio.shape}")
        # Update amplitude (MOSHI OUTPUT)
        if hasattr(self.moshi, 'update_moshi_amplitude'):
            self.moshi.update_moshi_amplitude(audio)
            
        # Play audio
        self.audio_io.play_audio(audio)
        self._set_state("speaking")

    def _on_moshi_text(self, text: str):
        """Callback for text received from Moshi"""
        # self.log(f"🤖 Moshi: {text}")
        if self.subconscious:
            self.subconscious.add_to_transcript(text)

    async def _conversation_loop_legacy(self):
        """Legacy loop for non-client bridges (if any)."""
        while self.running:
            await asyncio.sleep(1.0)

    # Legacy methods removed/stubbed
    async def _capture_speech_segment(self): pass
    async def _process_turn(self, user_audio): pass

    def _set_state(self, state: str):
        if self.on_state_change:
            self.on_state_change(state)

    def get_amplitudes(self) -> Dict[str, float]:
        return {"mic_amplitude": self.moshi.mic_amplitude, "moshi_amplitude": self.moshi.moshi_amplitude}


# ==============================================================================
# VOICE BRIDGE ORCHESTRATOR
# ==============================================================================

# ==============================================================================
# MOSHI BRIDGE PROXY (Process Communication)
# ==============================================================================

class MoshiBridgeProxy:
    """
    Proxy that looks like MoshiBridge but communicates with the Voice Server process.
    Enables the synchronous ConversationLoop to work with the async/process-based server.
    """
    def __init__(self, client_to_server, server_to_client, status_queue, quality="q4"):
        self.client_to_server = client_to_server
        self.server_to_client = server_to_client
        self.status_queue = status_queue
        self.quality = quality
        self.sample_rate = 24000
        self.frame_size = 1920
        
        # We need a local tokenizer to encode/decode audio before sending to server
        # This duplicates some logic but is necessary since server expects codes
        # We use the same download logic as MoshiBridge
        quality_map = {
            "bf16": ("kyutai/moshiko-mlx-bf16", None, "model.safetensors"),
            "q8": ("kyutai/moshiko-mlx-bf16", 8, "model.safetensors"),
            "q4": ("kyutai/moshiko-mlx-bf16", 4, "model.safetensors"),
        }
        if quality not in quality_map:
            quality = "q4"
            
        repo, _, _ = quality_map[quality]
        
        try:
            mimi_file = hf_hub_download(repo, "tokenizer-e351c8d8-checkpoint125.safetensors", local_files_only=True)
            tokenizer_file = hf_hub_download(repo, "tokenizer_spm_32k_3.model", local_files_only=True)
        except Exception:
            mimi_file = hf_hub_download(repo, "tokenizer-e351c8d8-checkpoint125.safetensors")
            tokenizer_file = hf_hub_download(repo, "tokenizer_spm_32k_3.model")
            
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)
        self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_file)
        
        self.mic_amplitude = 0.0
        self.moshi_amplitude = 0.0
        
        self.mic_amplitude = 0.0
        self.moshi_amplitude = 0.0
        
        # Wait for server ready
        print("⏳ Waiting for voice server to be ready...")
        try:
            # Wait up to 30 seconds for model loading
            msg = self.server_to_client.get(timeout=30.0)
            if msg == "ready":
                print("✅ Voice server is ready!")
            else:
                print(f"⚠️ Unexpected initial message from voice server: {msg}")
        except queue.Empty:
            print("❌ Timed out waiting for voice server ready signal")
            # Don't raise here, let it fail later if needed, or retry
        except Exception as e:
            print(f"❌ Error waiting for voice server: {e}")
        
    def encode_audio(self, audio: np.ndarray) -> np.ndarray:
        audio = audio.astype(np.float32)
        self.audio_tokenizer.encode(audio)
        start_time = time.time()
        while time.time() - start_time < 1.0: # 1s timeout
            codes = self.audio_tokenizer.get_encoded()
            if codes is not None:
                return codes
            time.sleep(0.001)
        print("❌ Timeout encoding audio frame")
        return np.zeros((1, 8), dtype=np.int32) # Return silence/empty on failure

    def decode_audio(self, codes: np.ndarray) -> np.ndarray:
        self.audio_tokenizer.decode(codes)
        start_time = time.time()
        while time.time() - start_time < 1.0: # 1s timeout
            audio = self.audio_tokenizer.get_decoded()
            if audio is not None:
                return audio
            time.sleep(0.001)
        print("❌ Timeout decoding audio frame")
        return np.zeros(1920, dtype=np.float32) # Return silence on failure
            
    def get_amplitude(self, audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio ** 2))
        return float(np.clip(rms * 4, 0, 1))

    def update_mic_amplitude(self, audio: np.ndarray):
        self.mic_amplitude = self.get_amplitude(audio)

    def update_moshi_amplitude(self, audio: np.ndarray):
        self.moshi_amplitude = self.get_amplitude(audio)

    def process_frame(self, user_audio: np.ndarray):
        """Send a single audio frame to the server."""
        frame_size = self.frame_size
        audio_len = len(user_audio)
        
        # Pad if needed
        if audio_len < frame_size:
            user_audio = np.pad(user_audio, (0, frame_size - audio_len), mode='constant')
        elif audio_len > frame_size:
            # If too long, just take the first chunk (or loop? for now assume frame-sized chunks)
            user_audio = user_audio[:frame_size]
            
        codes = self.encode_audio(user_audio)
        self.client_to_server.put(codes)

    def send_silence(self):
        """Send a silence frame to keep the model generating."""
        # Moshi expects (1, 8) or (8, 1) depending on side, server handles it.
        # We send (8, 1) to match what we do in generate_response
        silence_codes = np.zeros((8, 1), dtype=np.int32)
        self.client_to_server.put(silence_codes)

    def get_output(self, timeout: float = 0.01) -> tuple[Optional[np.ndarray], Optional[str]]:
        """Get output from server (non-blocking by default)."""
        try:
            msg = self.server_to_client.get(timeout=timeout)
            type_, audio_tokens, text_piece = msg
            
            audio_chunk = None
            if audio_tokens is not None:
                audio_chunk = self.decode_audio(audio_tokens)
                
            return audio_chunk, text_piece
        except queue.Empty:
            return None, None

    def generate_response(self, user_audio: np.ndarray, text_prompt: Optional[str] = None, max_frames: int = 125) -> tuple[np.ndarray, str]:
        """
        Legacy method for turn-based interaction.
        Kept for compatibility but uses streaming methods internally if possible, 
        or just the old logic.
        """
        # ... (keeping old logic for now to avoid breaking other things, or just wrapping streaming?)
        # Let's keep the old logic as a fallback or reference, but we won't use it in the new loop.
        return self._generate_response_legacy(user_audio, text_prompt, max_frames)

    def _generate_response_legacy(self, user_audio: np.ndarray, text_prompt: Optional[str] = None, max_frames: int = 125) -> tuple[np.ndarray, str]:
        """
        Generate response by sending codes to server process and reading results.
        Replicates the loop from MoshiBridge but distributed.
        """
        frame_size = self.frame_size
        audio_len = len(user_audio)
        if audio_len % frame_size != 0:
            pad_len = frame_size - (audio_len % frame_size)
            user_audio = np.pad(user_audio, (0, pad_len), mode='constant')

        # 1. Encode all input
        all_input_codes = []
        for offset in range(0, len(user_audio), frame_size):
            frame = user_audio[offset:offset + frame_size].astype(np.float32)
            codes = self.encode_audio(frame)
            all_input_codes.append(codes)
            
        output_audio_chunks = []
        text_pieces = []
        
        # 2. Send input codes and read responses
        for i, input_codes in enumerate(all_input_codes):
            # print(f"📤 Sending frame {i+1}/{len(all_input_codes)} to voice server")
            self.client_to_server.put(input_codes)
            
            try:
                msg = self.server_to_client.get(timeout=5.0)
                type_, audio_tokens, text_piece = msg
                if text_piece: text_pieces.append(text_piece)
                if audio_tokens is not None:
                    output_audio_chunks.append(self.decode_audio(audio_tokens))
            except queue.Empty:
                print("❌ Timeout waiting for voice server response")
                break
                
        # 3. Send silence codes for generation
        silence_codes = np.zeros((8, 1), dtype=np.int32)
        for _ in range(max_frames):
            self.client_to_server.put(silence_codes)
            try:
                msg = self.server_to_client.get(timeout=1.0)
                type_, audio_tokens, text_piece = msg
                if text_piece: text_pieces.append(text_piece)
                if audio_tokens is not None:
                    output_audio_chunks.append(self.decode_audio(audio_tokens))
            except queue.Empty:
                break
                
        response_audio = np.concatenate(output_audio_chunks) if output_audio_chunks else np.array([], dtype=np.float32)
        response_text = "".join(text_pieces)
        return response_audio, response_text


# ==============================================================================
# VOICE BRIDGE ORCHESTRATOR
# ==============================================================================

class ConversationState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"

class VoiceBridgeOrchestrator:
    """Orchestrates voice conversation using MoshiBridge, PersonaManager, and MemoryManager."""
    def __init__(self, persona_manager: PersonaManager, memory_manager: MemoryManager, config, user_id: str = "default", moshi_quality: str = "auto", voice_queues=None, log_callback: Optional[Callable[[str], None]] = None):
        self.persona_manager = persona_manager
        self.memory_manager = memory_manager
        self.config = config
        self.user_id = user_id
        self.moshi_quality = moshi_quality
        self.voice_queues = voice_queues
        self.log_callback = log_callback
        self.moshi: Optional[Any] = None # MoshiBridge or MoshiBridgeProxy
        self.current_persona: Optional[PersonaConfig] = None
        self.ai_client: Optional[AIClient] = None
        self.subconscious: Optional[SubconsciousBridge] = None
        self.conversation_loop: Optional[ConversationLoop] = None
        self.state = ConversationState.IDLE
        self.state_callbacks: list = []
        self._audio_buffer: list[np.ndarray] = []
        self._running = False

    @property
    def _current_mic_amplitude(self) -> float:
        if self.moshi:
            return getattr(self.moshi, 'mic_amplitude', 0.0)
        return 0.0

    @property
    def _current_moshi_amplitude(self) -> float:
        if self.moshi:
            return getattr(self.moshi, 'moshi_amplitude', 0.0)
        return 0.0

    def log(self, msg: str):
        print(msg)
        if self.log_callback:
            self.log_callback(msg)

    async def initialize(self):
        self.current_persona = self.persona_manager.get_current_persona()
        if not self.current_persona:
            raise ValueError("No persona set")
            
        if self.voice_queues:
            self.log("🔌 Connecting to Voice Server Process...")
            c2s, s2c, status = self.voice_queues
            # Use MoshiClient for full duplex streaming
            self.moshi = MoshiClient(c2s, s2c, log_callback=self.log_callback)
            self.moshi.wait_for_ready()
            self.log("✅ Moshi Client created (Full Duplex)")
            
            # Initialize AudioIO for playback
            from .audio import AudioIO
            self.audio_io = AudioIO(log_callback=self.log_callback)
            self.audio_io.start_output()
            self.log("✅ Audio output started")
            
            # Hook up Moshi audio output to AudioIO
            self.moshi.on_output_audio = self.audio_io.play_audio
            self.log("✅ Moshi audio output connected")
            
            # Set initial persona - inject name + short personality description
        if self.current_persona:
            # Use simpler prompt - just name and core personality
            persona_name = self.current_persona.name
            
            # FAST STARTUP: Use a very short first-person prompt.
            # This minimizes the time Moshi spends "thinking" before being ready.
            # The full personality will be injected by the SubconsciousBridge shortly after.
            persona_prompt = f"I am {persona_name}."
            
            self.log(f"🎭 Setting persona: {persona_name} ({len(persona_prompt)} chars)")
            self.moshi.set_persona(persona_prompt)
        else:
            self.log("🖥️  Initializing Local Moshi Bridge (In-Process)...")
            self.moshi = MoshiBridge(quality=self.moshi_quality)
            self.log("✅ Local Moshi Bridge initialized")
            
        self.ai_client = AIClient(self.config)
        
        # Initialize Subconscious Bridge if we have a client and tokenizer
        if isinstance(self.moshi, MoshiClient) and hasattr(self.moshi, 'client_to_server'):
             # We need a tokenizer for the bridge. MoshiClient has one but it's for audio.
             # The bridge needs a text tokenizer.
             # For now, we can pass None and let the bridge rely on string injection, 
             # as the tokenization happens on the server side.
             self.subconscious = SubconsciousBridge(self.moshi, self.ai_client, None)
             await self.subconscious.start()
             
             # INJECT FULL PERSONA
             # Now that the bridge is running, we inject the full personality as a "thought".
             # This uses the Bicameral "inception" mechanism to make Moshi adopt the persona.
             if self.current_persona:
                 full_prompt = self.current_persona.build_system_prompt()
                 # We frame it as a realization to make it natural
                 await self.subconscious.inject_persona(full_prompt)
        

        
        await self.memory_manager.initialize()
        print(f"📝 Creating ConversationLoop (persona: {self.current_persona.name})...")
        self.conversation_loop = ConversationLoop(
            moshi_bridge=self.moshi,
            persona_manager=self.persona_manager,
            memory_manager=self.memory_manager,
            ai_client=self.ai_client,
            subconscious_bridge=self.subconscious,
            user_id=self.user_id,
            on_turn_complete=self._on_conversation_turn,
            on_state_change=self._on_state_change,
            log_callback=self.log_callback
        )
        print("✅ ConversationLoop created")
        self._set_state(ConversationState.IDLE)

    async def start_conversation(self):
        if not self.conversation_loop:
            raise RuntimeError("Not initialized")
        print("🎙️  Starting conversation loop...")
        self._running = True
        
        # Start Subconscious Bridge
        if self.subconscious:
            await self.subconscious.start()
            
        try:
            await self.conversation_loop.start()
            self._set_state(ConversationState.LISTENING)
            print("✅ Conversation loop started - microphone active")
        except Exception as e:
            print(f"❌ Failed to start conversation: {e}")
            raise

    async def stop_conversation(self):
        self._running = False
        if self.conversation_loop:
            await self.conversation_loop.stop()
        self._set_state(ConversationState.IDLE)

    async def process_audio_input(self, audio_chunk: np.ndarray) -> Optional[Dict[str, Any]]:
        # This method seems redundant if ConversationLoop handles everything, 
        # but kept for compatibility if used directly by UI.
        # However, ConversationLoop logic is more complete.
        # If UI calls this, it bypasses ConversationLoop's VAD loop.
        # Assuming UI uses this for manual audio feeding?
        # For now, mirroring original logic but using MoshiBridge directly.
        if not self.moshi: raise RuntimeError("Moshi not initialized")
        self._current_mic_amplitude = self.moshi.get_amplitude(audio_chunk)
        self._set_state(ConversationState.THINKING)
        try:
            history = await self.memory_manager.get_conversation_history(self.user_id, limit=10)
            system_prompt = self._build_prompt_with_history(history)
            response_audio, response_text = self.moshi.generate_response(user_audio=audio_chunk, text_prompt=system_prompt, max_frames=125)
            self._current_moshi_amplitude = self.moshi.get_amplitude(response_audio)
            await self.memory_manager.store_message(self.user_id, "[Audio input]", "user", {"persona": self.current_persona.name})
            await self.memory_manager.store_message(self.user_id, response_text, "assistant", {"persona": self.current_persona.name})
            self._set_state(ConversationState.SPEAKING)
            self._audio_buffer.append(response_audio)
            return {"response_audio": response_audio, "response_text": response_text, "mic_amplitude": self._current_mic_amplitude, "moshi_amplitude": self._current_moshi_amplitude}
        except Exception:
            self._set_state(ConversationState.ERROR)
            return None
        finally:
            if self._running: self._set_state(ConversationState.LISTENING)

    async def generate_response(self, text: str) -> Optional[Dict[str, Any]]:
        await self.memory_manager.store_message(self.user_id, text, "user")
        history = await self.memory_manager.get_conversation_history(self.user_id, limit=10)
        system_prompt = self._build_prompt_with_history(history)
        if self.ai_client and self.ai_client.is_available():
            try:
                response_text = await self.ai_client.chat([{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], max_tokens=150)
            except Exception:
                response_text = f"Hello! I'm {self.current_persona.name}."
        else:
            response_text = f"Hello! I'm {self.current_persona.name}."
        await self.memory_manager.store_message(self.user_id, response_text, "assistant", {"persona": self.current_persona.name})
        return {"response_text": response_text}

    def get_audio_stream(self) -> AsyncGenerator[np.ndarray, None]:
        async def stream():
            while self._running or self._audio_buffer:
                if self._audio_buffer:
                    yield self._audio_buffer.pop(0)
                else:
                    await asyncio.sleep(0.01)
        return stream()

    def get_conversation_state(self) -> ConversationState:
        return self.state

    def get_amplitudes(self) -> Dict[str, float]:
        if self.conversation_loop:
            return self.conversation_loop.get_amplitudes()
        return {"mic_amplitude": self._current_mic_amplitude, "moshi_amplitude": self._current_moshi_amplitude}

    def on_state_change(self, callback):
        self.state_callbacks.append(callback)

    async def switch_persona(self, persona_name: str) -> bool:
        if self.persona_manager.set_current_persona(persona_name):
            self.current_persona = self.persona_manager.get_current_persona()
            return True
        return False

    async def reload_persona(self) -> bool:
        if self.current_persona and self.persona_manager.reload_persona(self.current_persona.name):
            self.current_persona = self.persona_manager.get_current_persona()
            return True
        return False

    async def clear_conversation_history(self):
        await self.memory_manager.clear_history(self.user_id)

    def _build_prompt_with_history(self, history: str) -> str:
        persona_prompt = self.current_persona.build_system_prompt(include_personality=True)
        tool_prompt = registry.get_tool_prompt()
        full_prompt = f"{persona_prompt}\n\n{tool_prompt}"
        if history:
            return f"{full_prompt}\n\n## Recent Conversation\n{history}"
        return full_prompt

    def _set_state(self, new_state: ConversationState):
        if self.state != new_state:
            self.state = new_state
            for callback in self.state_callbacks:
                try:
                    callback(new_state)
                except Exception:
                    pass

    async def cleanup(self):
        await self.stop_conversation()
        await self.memory_manager.close()

    def stop(self):
        print("🛑 Stopping VoiceAssistant...")
        self._running = False
        if self.conversation_loop:
            # ConversationLoop.stop() is async, but we're in sync context
            # Just set running flag and let it clean up
            if hasattr(self.conversation_loop, 'running'):
                self.conversation_loop.running = False
            
        # Stop Subconscious Bridge
        if self.subconscious:
            self.subconscious.stop()
            
        if self.moshi:
            self.moshi.stop()
        
        # Fix multiprocessing queue hang: Cancel join threads to prevent deadlock
        if self.voice_queues:
            for q in self.voice_queues:
                try:
                    if hasattr(q, 'cancel_join_thread'):
                        q.cancel_join_thread()
                    if hasattr(q, 'close'):
                        q.close()
                except Exception as e:
                    self.log(f"⚠️ Error closing queue: {e}")

    def _on_conversation_turn(self, turn: ConversationTurn):
        # This is called when a turn is complete (user spoke, AI responded)
        # We can use this to update the UI or trigger other events
        # self.log(f"Turn complete: {turn.user_text} -> {turn.ai_text}")
        
        # Feed transcript to Subconscious Bridge
        if self.subconscious:
            self.subconscious.on_transcript_update(turn.user_text, turn.ai_text)
            
        if turn.metadata:
            self._current_mic_amplitude = turn.metadata.get("mic_amplitude", 0.0)
            self._current_moshi_amplitude = turn.metadata.get("moshi_amplitude", 0.0)
            if "latency_ms" in turn.metadata:
                pass # self.log(f"  Latency: {turn.metadata['latency_ms']}ms")

    def _on_state_change(self, state: str):
        state_map = {"idle": ConversationState.IDLE, "listening": ConversationState.LISTENING, "thinking": ConversationState.THINKING, "speaking": ConversationState.SPEAKING, "error": ConversationState.ERROR}
        self._set_state(state_map.get(state, ConversationState.IDLE))
