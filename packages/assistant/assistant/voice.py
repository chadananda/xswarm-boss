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
    def __init__(self, client_to_server, server_to_client, hf_repo: str = "kyutai/moshiko-mlx-bf16", mimi_file: Optional[str] = None):
        self.client_to_server = client_to_server
        self.server_to_client = server_to_client
        if mimi_file is None:
            mimi_file = hf_hub_download(hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.on_output_audio: Optional[Callable[[np.ndarray], None]] = None
        self.on_text_token: Optional[Callable[[str], None]] = None
        self._running = False

    def feed_audio(self, audio: np.ndarray):
        self.input_queue.put_nowait(audio.astype(np.float32))

    def get_output_audio(self) -> Optional[np.ndarray]:
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    async def run_async_loops(self):
        self._running = True
        async def send_loop():
            while self._running:
                await asyncio.sleep(0.001)
                try:
                    pcm_data = self.input_queue.get(block=False)
                    self.audio_tokenizer.encode(pcm_data)
                except queue.Empty:
                    continue
        async def send_loop2():
            while self._running:
                data = self.audio_tokenizer.get_encoded()
                if data is None:
                    await asyncio.sleep(0.001)
                    continue
                self.client_to_server.put_nowait(data)
        async def recv_loop2():
            while self._running:
                try:
                    result = self.server_to_client.get(block=False)
                except queue.Empty:
                    await asyncio.sleep(0.001)
                    continue
                msg_type, audio_tokens, text_piece = result
                if text_piece and self.on_text_token:
                    self.on_text_token(text_piece)
                if audio_tokens is not None:
                    self.audio_tokenizer.decode(audio_tokens)
        async def recv_loop():
            while self._running:
                data = self.audio_tokenizer.get_decoded()
                if data is None:
                    await asyncio.sleep(0.001)
                    continue
                self.output_queue.put_nowait(data)
                if self.on_output_audio:
                    self.on_output_audio(data)
        await asyncio.gather(send_loop(), send_loop2(), recv_loop(), recv_loop2())

    def stop(self):
        self._running = False


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

class ConversationLoop:
    """Manages the conversation loop with VAD -> STT -> AI -> TTS -> Output."""
    def __init__(self, moshi_bridge: MoshiBridge, persona_manager: PersonaManager, memory_manager: MemoryManager, ai_client: AIClient, memory_orchestrator: Optional[MemoryOrchestrator] = None, user_id: str = "default", on_turn_complete: Optional[Callable] = None, on_state_change: Optional[Callable] = None):
        self.moshi = moshi_bridge
        self.persona = persona_manager
        self.memory = memory_manager
        self.ai = ai_client
        self.memory_orchestrator = memory_orchestrator
        self.user_id = user_id
        self.on_turn_complete = on_turn_complete
        self.on_state_change = on_state_change
        self.audio_io = AudioIO()
        self.vad = VoiceActivityDetector()
        self.tool_executor = ToolExecutor(registry)
        self.command_parser = CommandParser()
        self.running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._audio_buffer = []
        self._is_listening = False

    async def start(self):
        self.running = True
        try:
            self.audio_io.start_input(callback=self._on_audio_frame)
            self.audio_io.start_output()
            print("✅ Audio streams started")
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
        
        self._loop_task = asyncio.create_task(self._conversation_loop())
        self._set_state("listening")

    async def stop(self):
        self.running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        self.audio_io.stop()
        self._set_state("idle")

    async def _conversation_loop(self):
        while self.running:
            try:
                if not self._is_listening:
                    await asyncio.sleep(0.05)
                    continue
                user_audio = await self._capture_speech_segment()
                if user_audio is None or len(user_audio) == 0:
                    await asyncio.sleep(0.1)  # Prevent tight loop
                    continue
                await self._process_turn(user_audio)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Loop error: {e}")
                await asyncio.sleep(1.0)

    def _on_audio_frame(self, audio: np.ndarray):
        """Callback for each audio frame from microphone"""
        if not self._is_listening:
            return
        
        # Update amplitude for visualization
        self.moshi.update_mic_amplitude(audio)
        
        # Check for voice activity
        is_speaking = self.vad.process_frame(audio)
        
        if is_speaking:
            self._audio_buffer.append(audio)
            # Log first frame of speech
            if len(self._audio_buffer) == 1:
                print(f"🎤 Speech detected! Starting capture...")
        elif len(self._audio_buffer) > 0:
            # End of speech - log buffer size
            total_samples = sum(len(chunk) for chunk in self._audio_buffer)
            duration_ms = (total_samples / 24000) * 1000
            print(f"🎤 Speech ended. Captured {len(self._audio_buffer)} frames ({duration_ms:.0f}ms)")

    async def _capture_speech_segment(self) -> Optional[np.ndarray]:
        """Capture a speech segment with timeout to prevent hanging"""
        # Wait for audio buffer to have content, but with timeout
        max_wait = 10  # seconds
        wait_time = 0
        while len(self._audio_buffer) == 0 and wait_time < max_wait:
            await asyncio.sleep(0.1)
            wait_time += 0.1
            if not self.running:
                return None
        
        if len(self._audio_buffer) == 0:
            return None
            
        segment = np.concatenate(self._audio_buffer)
        self._audio_buffer = []
        self.vad.reset()
        return segment

    async def _process_turn(self, user_audio: np.ndarray):
        print(f"🤔 Processing turn with {len(user_audio)} audio samples...")
        self._set_state("thinking")
        self.moshi.update_mic_amplitude(user_audio)
        
        inner_monologue = None
        if self.memory_orchestrator and self.memory_orchestrator.is_available():
            try:
                recent_context_list = await self.memory.get_context(self.user_id, limit=5)
                recent_context = "\n".join([f"{msg.get('role', 'user')}: {msg.get('message', '')}" for msg in recent_context_list]) if recent_context_list else "context"
                filtered_memories = await self.memory_orchestrator.get_memories(self.user_id, query=recent_context, context=recent_context, thinking_level="light", max_memories=3)
                if filtered_memories:
                    inner_monologue = "[Inner thoughts]:\n" + "\n".join([f"- {mem.text}" for mem in filtered_memories])
            except Exception:
                pass

        moshi_audio, moshi_text = self.moshi.generate_response(user_audio=user_audio, text_prompt=inner_monologue, max_frames=125)
        print(f"🎙️ Moshi generated: {len(moshi_audio)} audio samples, text: '{moshi_text[:50] if moshi_text else 'None'}...'")
        
        tool_output_text = ""
        if moshi_text:
            commands = self.command_parser.parse(moshi_text)
            if commands:
                results = await self.tool_executor.execute_commands(commands)
                for i, (tool_name, _, _) in enumerate(commands):
                    tool_output_text += f"\n[Tool '{tool_name}' result]:\n{results[i]}\n"

        assistant_text = (moshi_text if moshi_text else "[No response]") + tool_output_text
        self.moshi.update_moshi_amplitude(moshi_audio)
        
        self._set_state("speaking")
        if len(moshi_audio) > 0:
            self.audio_io.play_audio(moshi_audio)
            await asyncio.sleep(len(moshi_audio) / 24000.0)

        persona_name = self.persona.get_current_persona().name
        await self.memory.store_message(self.user_id, "[Audio input]", "user", {"persona": persona_name})
        await self.memory.store_message(self.user_id, assistant_text, "assistant", {"persona": persona_name})

        turn = ConversationTurn(
            user_text="[Audio input]", assistant_text=assistant_text, persona_name=persona_name,
            timestamp=datetime.now().timestamp(), user_audio=user_audio, assistant_audio=moshi_audio,
            metadata={"mic_amplitude": self.moshi.mic_amplitude, "moshi_amplitude": self.moshi.moshi_amplitude, "inner_monologue": inner_monologue}
        )
        if self.on_turn_complete:
            self.on_turn_complete(turn)
        
        self._set_state("listening")
        self._is_listening = False

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
            
    def get_amplitude(self, audio: np.ndarray) -> float:
        rms = np.sqrt(np.mean(audio ** 2))
        return float(np.clip(rms * 4, 0, 1))

    def update_mic_amplitude(self, audio: np.ndarray):
        self.mic_amplitude = self.get_amplitude(audio)

    def update_moshi_amplitude(self, audio: np.ndarray):
        self.moshi_amplitude = self.get_amplitude(audio)

    def generate_response(self, user_audio: np.ndarray, text_prompt: Optional[str] = None, max_frames: int = 125) -> tuple[np.ndarray, str]:
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
        text_tokens_list = [] # We get text pieces directly from server
        text_pieces = []
        
        # 2. Send input codes and read responses
        for i, input_codes in enumerate(all_input_codes):
            print(f"📤 Sending frame {i+1}/{len(all_input_codes)} to voice server (shape: {input_codes.shape})")
            self.client_to_server.put(input_codes)
            
            # Read response (blocking)
            # Server sends ("audio", tokens, text) or ("text", None, text)
            print(f"📥 Waiting for response from voice server...")
            msg = self.server_to_client.get()
            type_, audio_tokens, text_piece = msg
            print(f"📥 Received: type={type_}, audio_tokens={'present' if audio_tokens is not None else 'None'}, text='{text_piece}'")
            
            if text_piece:
                text_pieces.append(text_piece)
                
            if audio_tokens is not None:
                audio_chunk = self.decode_audio(audio_tokens)
                output_audio_chunks.append(audio_chunk)
                print(f"🔊 Decoded audio chunk: {len(audio_chunk)} samples")
                
        # 3. Send silence codes for generation
        # We need to send empty codes to keep the model generating
        # MoshiBridge uses mx.zeros((1, 8))
        # We need to send numpy equivalent with correct shape (1, 8)
        # The server will add the time dimension -> (1, 8, 1)
        silence_codes = np.zeros((1, 8), dtype=np.int32)
        
        for _ in range(max_frames):
            self.client_to_server.put(silence_codes)
            
            msg = self.server_to_client.get()
            type_, audio_tokens, text_piece = msg
            
            if text_piece:
                text_pieces.append(text_piece)
                
            if audio_tokens is not None:
                audio_chunk = self.decode_audio(audio_tokens)
                output_audio_chunks.append(audio_chunk)
                
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
        self.conversation_loop: Optional[ConversationLoop] = None
        self.state = ConversationState.IDLE
        self.state_callbacks: list = []
        self._audio_buffer: list[np.ndarray] = []
        self._current_mic_amplitude: float = 0.0
        self._current_moshi_amplitude: float = 0.0
        self._running = False

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
            self.moshi = MoshiBridgeProxy(c2s, s2c, status, quality=self.moshi_quality)
            self.log("✅ Voice Server Proxy created")
        else:
            self.log("🖥️  Initializing Local Moshi Bridge (In-Process)...")
            self.moshi = MoshiBridge(quality=self.moshi_quality)
            self.log("✅ Local Moshi Bridge initialized")
            
        self.ai_client = AIClient(self.config)
        await self.memory_manager.initialize()
        print(f"📝 Creating ConversationLoop (persona: {self.current_persona.name})...")
        self.conversation_loop = ConversationLoop(
            moshi_bridge=self.moshi, persona_manager=self.persona_manager, memory_manager=self.memory_manager,
            ai_client=self.ai_client, user_id=self.user_id, on_turn_complete=self._on_conversation_turn,
            on_state_change=self._on_state_change
        )
        print("✅ ConversationLoop created")
        self._set_state(ConversationState.IDLE)

    async def start_conversation(self):
        if not self.conversation_loop:
            raise RuntimeError("Not initialized")
        print("🎙️  Starting conversation loop...")
        self._running = True
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

    def _on_conversation_turn(self, turn: ConversationTurn):
        if turn.metadata:
            self._current_mic_amplitude = turn.metadata.get("mic_amplitude", 0.0)
            self._current_moshi_amplitude = turn.metadata.get("moshi_amplitude", 0.0)

    def _on_state_change(self, state: str):
        state_map = {"idle": ConversationState.IDLE, "listening": ConversationState.LISTENING, "thinking": ConversationState.THINKING, "speaking": ConversationState.SPEAKING, "error": ConversationState.ERROR}
        self._set_state(state_map.get(state, ConversationState.IDLE))
