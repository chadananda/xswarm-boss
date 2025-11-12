"""
MLX MOSHI bridge optimized for Apple Silicon (M1/M2/M3).

This implementation uses:
- MLX framework (Apple's ML framework for Metal GPU)
- RustyMimi codec (Rust-based audio tokenizer)
- Quantized models (4-bit or 8-bit) for efficiency

Replaces PyTorch implementation which has MPS limitations on M3.

Requires:
    pip install moshi_mlx
"""

import numpy as np
from typing import Optional
from pathlib import Path
import sentencepiece

try:
    import mlx.core as mx
    import mlx.nn as nn
    import rustymimi
    from moshi_mlx import models, utils
    from huggingface_hub import hf_hub_download
except ImportError as e:
    raise ImportError(
        f"MLX dependencies not installed: {e}\n"
        "Install with: cd /tmp/moshi-official/moshi_mlx && pip install -e ."
    )


class MoshiBridge:
    """
    MLX MOSHI bridge optimized for Apple Silicon.

    This class provides the same interface as moshi_pytorch.MoshiBridge
    but uses MLX for efficient inference on Apple Metal GPUs.
    """

    def __init__(
        self,
        hf_repo: str = "kyutai/moshiko-mlx-q8",
        quantized: int = 8,  # 4 or 8 bit quantization
        max_steps: int = 500,  # Max generation steps (~40s at 12.5 Hz)
        sample_rate: int = 24000
    ):
        """
        Initialize MLX Moshi bridge.

        Args:
            hf_repo: HuggingFace repo for models (default: 8-bit quantized)
            quantized: Quantization level (4 or 8 bits, None for full precision)
            max_steps: Maximum generation steps
            sample_rate: Audio sample rate (24kHz)
        """
        self.hf_repo = hf_repo
        self.quantized = quantized
        self.max_steps = max_steps
        self.sample_rate = sample_rate
        self.frame_size = 1920  # 80ms at 24kHz

        print(f"Loading Moshi MLX from {hf_repo} (q{quantized})...")

        # Download model files
        print("Downloading models from HuggingFace (cached locally)...")
        if quantized == 8:
            model_file = hf_hub_download(hf_repo, "model.q8.safetensors")
        elif quantized == 4:
            model_file = hf_hub_download(hf_repo, "model.q4.safetensors")
        else:
            model_file = hf_hub_download(hf_repo, "model.safetensors")

        mimi_file = hf_hub_download(hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")
        tokenizer_file = hf_hub_download(hf_repo, "tokenizer_spm_32k_3.model")

        # Load text tokenizer
        print("Loading text tokenizer...")
        self.text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_file)

        # Load Mimi audio codec (Rust implementation)
        print("Loading Mimi audio codec...")
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)

        # Load Moshi language model
        print(f"Loading Moshi LM from {model_file}...")
        mx.random.seed(299792458)
        lm_config = models.config_v0_1()
        self.model = models.Lm(lm_config)
        self.model.set_dtype(mx.bfloat16)

        if quantized is not None:
            group_size = 32 if quantized == 4 else 64
            nn.quantize(self.model, bits=quantized, group_size=group_size)

        self.model.load_weights(model_file, strict=True)
        print("Warming up model...")
        self.model.warmup()

        print("✓ Moshi MLX loaded successfully")

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
        import time
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
        import time
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
        # Normalize to 0-1 range
        return float(np.clip(rms * 3, 0, 1))

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
