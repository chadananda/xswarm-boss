"""
MLX MOSHI bridge optimized for Apple Silicon (M1/M2/M3).

This implementation uses:
- MLX framework (Apple's ML framework for Metal GPU)
- RustyMimi codec (Rust-based audio tokenizer)
- Runtime quantization (4-bit or 8-bit) for efficiency

Key Design Decision:
    Instead of using pre-quantized checkpoints (kyutai/moshiko-mlx-q8, q4),
    we load the BF16 checkpoint and quantize at runtime. This avoids
    dimension mismatch issues while providing the same memory/speed benefits.

Quality Levels:
    - BF16: Full precision (~7.6GB VRAM, highest quality)
    - Q8: 8-bit quantization (~3.8GB VRAM, excellent quality)
    - Q4: 4-bit quantization (~1.9GB VRAM, good quality)

Replaces PyTorch implementation which has MPS limitations on M3.

Requires:
    pip install moshi_mlx
"""

import numpy as np
from typing import Optional
from pathlib import Path
import sentencepiece
import os
import time

# CRITICAL: Disable hf_transfer BEFORE importing huggingface_hub
# hf_transfer auto-enables when installed and ignores local_files_only=True
# This causes network requests and hangs when offline or files are cached
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
if "HF_HUB_ENABLE_HF_TRANSFER" in os.environ:
    del os.environ["HF_HUB_ENABLE_HF_TRANSFER"]

try:
    import mlx.core as mx
    import mlx.nn as nn
    import rustymimi
    from moshi_mlx import models, utils
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
    import backoff
except ImportError as e:
    raise ImportError(
        f"MLX dependencies not installed: {e}\n"
        "Install with: cd /tmp/moshi-official/moshi_mlx && pip install -e ."
    )


def _create_download_with_retry():
    """
    Create retry-wrapped download function for robust downloads.

    Handles intermittent connections with exponential backoff:
    - NEVER gives up - waits indefinitely for internet to return
    - Automatic resume on connection drops
    - Exponential backoff caps at 5 minutes between retries
    - User-friendly retry notifications
    """
    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, TimeoutError, HfHubHTTPError, OSError),
        max_time=None,  # Never give up - wait for internet to return
        max_value=300,  # Cap backoff at 5 minutes between retries
        on_backoff=lambda details: print(
            f"  ↻ Download interrupted. Retry #{details['tries']} "
            f"after {details['wait']:.1f}s... (waiting for internet, will resume from checkpoint)"
        )
    )
    def download_with_retry(repo_id: str, filename: str) -> str:
        """Download with automatic resume and retry - never gives up."""
        return hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            resume_download=True  # Always enable resume
        )

    return download_with_retry


class MoshiBridge:
    """
    MLX MOSHI bridge optimized for Apple Silicon.

    This class provides the same interface as moshi_pytorch.MoshiBridge
    but uses MLX for efficient inference on Apple Metal GPUs.
    """

    def __init__(
        self,
        hf_repo: Optional[str] = None,  # Auto-selected if None
        quantized: Optional[int] = None,  # Auto-selected if None
        max_steps: int = 500,  # Max generation steps (~40s at 12.5 Hz)
        sample_rate: int = 24000,
        quality: str = "auto"  # "auto", "bf16", "q8", "q4"
    ):
        """
        Initialize MLX Moshi bridge with automatic quality selection.

        Args:
            hf_repo: HuggingFace repo (auto-selected if None based on quality)
            quantized: Quantization level (auto-selected if None based on quality)
            max_steps: Maximum generation steps
            sample_rate: Audio sample rate (24kHz)
            quality: Quality preset ("auto" detects from GPU, or "bf16"/"q8"/"q4")
        """
        print(f"🚀 Starting Moshi initialization (quality={quality})...")

        # Auto-select quality based on GPU capability
        if quality == "auto":
            from ..hardware.gpu_detector import detect_gpu_capability
            from ..hardware.service_selector import select_services

            gpu = detect_gpu_capability()
            config = select_services(gpu)

            if config.moshi_mode == "cloud":
                raise RuntimeError(
                    f"GPU insufficient for local Moshi (score: {gpu.compute_score:.1f}/100, grade: {gpu.grade}). "
                    "Cloud Moshi not yet implemented."
                )

            quality = config.moshi_quality

        # Map quality to repo and quantization strategy
        # Key insight: For quantized models, we load BF16 weights and quantize at runtime
        # This avoids dimension mismatch issues with pre-quantized checkpoints
        quality_map = {
            "bf16": ("kyutai/moshiko-mlx-bf16", None, "model.safetensors"),
            "q8": ("kyutai/moshiko-mlx-bf16", 8, "model.safetensors"),  # Load BF16, quantize to 8-bit
            "q4": ("kyutai/moshiko-mlx-bf16", 4, "model.safetensors"),  # Load BF16, quantize to 4-bit
        }

        if quality not in quality_map:
            raise ValueError(f"Invalid quality: {quality}. Must be 'auto', 'bf16', 'q8', or 'q4'")

        # Use provided values or auto-selected values
        self.quality = quality
        default_repo, default_quant, default_file = quality_map[quality]
        self.hf_repo = hf_repo or default_repo
        self.quantized = quantized if quantized is not None else default_quant
        self.max_steps = max_steps
        self.sample_rate = sample_rate
        self.frame_size = 1920  # 80ms at 24kHz

        # Download model files with robust retry logic
        # Always use BF16 checkpoint and quantize at runtime if needed
        print(f"📦 Checking for cached model files...")
        download = _create_download_with_retry()

        # Try cached versions first for all files
        print(f"🔍 Looking for {self.hf_repo}/{default_file}...")
        try:
            model_file = hf_hub_download(self.hf_repo, default_file, local_files_only=True)
            mimi_file = hf_hub_download(self.hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors", local_files_only=True)
            tokenizer_file = hf_hub_download(self.hf_repo, "tokenizer_spm_32k_3.model", local_files_only=True)
        except Exception as e:
            # Files not in cache, download with automatic retry and resume support
            print(f"Downloading Moshi models (~14GB, may take time on slow connections)...")
            print(f"Error loading cached files: {e}")
            model_file = download(self.hf_repo, default_file)
            mimi_file = download(self.hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")
            tokenizer_file = download(self.hf_repo, "tokenizer_spm_32k_3.model")

        # Load text tokenizer
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("Loading text tokenizer...")
        self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_file)
        logger.debug("Text tokenizer loaded")

        # Load Mimi audio codec (Rust implementation)
        logger.debug("Loading Mimi audio codec...")
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)
        logger.debug("Mimi codec loaded")

        # Load Moshi language model
        logger.debug("Initializing Moshi model...")
        mx.random.seed(299792458)
        lm_config = models.config_v0_1()
        self.model = models.Lm(lm_config)
        self.model.set_dtype(mx.bfloat16)
        logger.debug("Model structure initialized")

        if quantized is not None:
            logger.debug(f"Quantizing model to {quantized}-bit...")
            group_size = 32 if quantized == 4 else 64
            nn.quantize(self.model, bits=quantized, group_size=group_size)
            logger.debug("Model quantized")

        # Load weights - strict=True works with quantized checkpoints
        # The reference implementation uses strict=True successfully
        logger.debug(f"Loading model weights (~{self.quality}, ~14GB)...")
        self.model.load_weights(model_file, strict=True)
        logger.debug("Weights loaded")

        logger.debug("Warming up GPU...")
        self.model.warmup()
        logger.debug("Model ready!")

        # Amplitude tracking
        self.mic_amplitude = 0.0
        self.moshi_amplitude = 0.0

    def encode_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Encode audio to Mimi codes using RustyMimi.

        Args:
            audio: NumPy array of shape (samples,) at 24kHz

        Returns:
            Audio codes as NumPy array
        """
        # Ensure audio is float32
        audio = audio.astype(np.float32)

        # Encode with RustyMimi
        self.audio_tokenizer.encode(audio)

        # Wait for encoding to complete
        while True:
            codes = self.audio_tokenizer.get_encoded()
            if codes is not None:
                return codes
            time.sleep(0.001)

    def decode_audio(self, codes: np.ndarray) -> np.ndarray:
        """
        Decode Mimi codes to audio using RustyMimi.

        Args:
            codes: Audio codes array

        Returns:
            Audio as NumPy array at 24kHz
        """
        # Decode with RustyMimi
        self.audio_tokenizer.decode(codes)

        # Wait for decoding to complete
        while True:
            audio = self.audio_tokenizer.get_decoded()
            if audio is not None:
                return audio
            time.sleep(0.001)

    def generate_response(
        self,
        user_audio: np.ndarray,
        text_prompt: Optional[str] = None,
        max_frames: int = 125  # ~10 seconds at 12.5 Hz
    ) -> tuple[np.ndarray, str]:
        """
        Generate Moshi response from user audio.

        Args:
            user_audio: User audio at 24kHz
            text_prompt: Optional text context (e.g., from persona)
            max_frames: Max generation length in frames (12.5 Hz, so 125 = ~10s)

        Returns:
            (response_audio, response_text) tuple
        """
        # Ensure audio is multiple of frame size (1920 samples = 80ms)
        frame_size = self.frame_size
        audio_len = len(user_audio)
        if audio_len % frame_size != 0:
            pad_len = frame_size - (audio_len % frame_size)
            user_audio = np.pad(user_audio, (0, pad_len), mode='constant')

        # Encode user audio in frames
        all_input_codes = []
        for offset in range(0, len(user_audio), frame_size):
            frame = user_audio[offset:offset + frame_size].astype(np.float32)
            codes = self.encode_audio(frame)
            all_input_codes.append(codes)

        # Create LM generator
        lm_gen = models.LmGen(
            model=self.model,
            max_steps=min(len(all_input_codes) + max_frames, self.max_steps),
            text_sampler=utils.Sampler(),
            audio_sampler=utils.Sampler(),
            batch_size=1,
            check=False
        )

        # Generate response
        output_audio_chunks = []
        text_tokens_list = []

        # Process input audio codes
        for input_codes in all_input_codes:
            # Convert to MLX array (transpose to [batch, codebooks, time])
            audio_codes_mx = mx.array(input_codes).transpose(1, 0)[:, :8]

            # Step through model
            text_token = lm_gen.step(audio_codes_mx)
            text_token_id = text_token[0].item()

            # Collect text tokens (skip special tokens 0 and 3)
            if text_token_id not in (0, 3):
                text_tokens_list.append(text_token_id)

            # Get generated audio codes
            audio_tokens = lm_gen.last_audio_tokens()
            if audio_tokens is not None:
                audio_tokens_np = np.array(audio_tokens).astype(np.uint32)
                # Decode to audio
                audio_chunk = self.decode_audio(audio_tokens_np)
                output_audio_chunks.append(audio_chunk)

        # Continue generation for response
        for _ in range(max_frames):
            # Feed silence/padding to continue generation
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

        # Concatenate output audio
        if output_audio_chunks:
            response_audio = np.concatenate(output_audio_chunks)
        else:
            response_audio = np.array([], dtype=np.float32)

        # Decode text tokens
        if text_tokens_list:
            response_text = "".join([
                self.text_tokenizer.id_to_piece(token_id).replace("▁", " ")
                for token_id in text_tokens_list
            ])
        else:
            response_text = ""

        return response_audio, response_text

    def get_amplitude(self, audio: np.ndarray) -> float:
        """
        Calculate RMS amplitude for visualization.

        Args:
            audio: Audio samples

        Returns:
            RMS amplitude (0.0 - 1.0)
        """
        rms = np.sqrt(np.mean(audio ** 2))
        # Normalize to 0-1 range with responsive scaling
        # Typical speech RMS is 0.01-0.3, so scale by ~4x for 0.04-1.2 range (clips at 1.0)
        return float(np.clip(rms * 4, 0, 1))

    def update_mic_amplitude(self, audio: np.ndarray):
        """
        Update mic amplitude from audio input.

        Args:
            audio: Microphone audio samples
        """
        self.mic_amplitude = self.get_amplitude(audio)

    def update_moshi_amplitude(self, audio: np.ndarray):
        """
        Update Moshi amplitude from audio output.

        Args:
            audio: Moshi audio output samples
        """
        self.moshi_amplitude = self.get_amplitude(audio)
    # Streaming methods for full-duplex phone integration
    def create_lm_generator(self, max_steps: int = 500):
        """
        Create a persistent LM generator for streaming.

        Returns:
            LmGen instance for frame-by-frame processing
        """
        return models.LmGen(
            model=self.model,
            max_steps=max_steps,
            text_sampler=utils.Sampler(),
            audio_sampler=utils.Sampler(),
            batch_size=1,
            check=False
        )
    def step_frame(self, lm_gen, audio_frame: np.ndarray) -> tuple[Optional[np.ndarray], Optional[str]]:
        """
        Process a single 80ms frame through Moshi.

        Args:
            lm_gen: LmGen generator instance
            audio_frame: 1920 samples at 24kHz (80ms)

        Returns:
            (response_audio_chunk, text_token) or (None, None)
        """
        # Encode frame
        codes = self.encode_audio(audio_frame)
        audio_codes_mx = mx.array(codes).transpose(1, 0)[:, :8]
        # Step model
        text_token = lm_gen.step(audio_codes_mx)
        text_token_id = text_token[0].item()
        # Get audio output
        audio_tokens = lm_gen.last_audio_tokens()
        if audio_tokens is not None:
            audio_tokens_np = np.array(audio_tokens).astype(np.uint32)
            audio_chunk = self.decode_audio(audio_tokens_np)
            # Return audio and text
            text_piece = ""
            if text_token_id not in (0, 3):
                text_piece = self.text_tokenizer.id_to_piece(text_token_id).replace("▁", " ")
            return audio_chunk, text_piece
        return None, None
    def generate_greeting(self, lm_gen, persona_prompt: str = None, num_frames: int = 25) -> tuple[np.ndarray, str]:
        """
        Generate Moshi greeting by feeding silence frames.

        Args:
            lm_gen: LmGen generator instance
            persona_prompt: Optional persona context
            num_frames: Number of frames to generate (~2 seconds for 25 frames)

        Returns:
            (greeting_audio, greeting_text)
        """
        silence_frame = np.zeros(self.frame_size, dtype=np.float32)
        audio_chunks = []
        text_pieces = []
        for _ in range(num_frames):
            audio_chunk, text_piece = self.step_frame(lm_gen, silence_frame)
            if audio_chunk is not None:
                audio_chunks.append(audio_chunk)
            if text_piece:
                text_pieces.append(text_piece)
        greeting_audio = np.concatenate(audio_chunks) if audio_chunks else np.array([], dtype=np.float32)
        greeting_text = "".join(text_pieces)
        return greeting_audio, greeting_text
