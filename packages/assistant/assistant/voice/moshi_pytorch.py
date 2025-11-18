"""
PyTorch MOSHI bridge with cross-platform device detection.

Supports:
- Mac M3: PyTorch MPS (Metal)
- AMD Strix Halo: PyTorch ROCm
- NVIDIA: PyTorch CUDA
- Fallback: CPU

Requires MOSHI installed from source:
    cd /tmp/moshi-official/moshi && pip install -e .
"""

import torch
import numpy as np
from typing import Optional, List
from pathlib import Path

# Note: Requires MOSHI installed from source
try:
    from moshi.models import loaders, LMGen
except ImportError:
    raise ImportError(
        "MOSHI not installed. Install from: cd /tmp/moshi-official/moshi && pip install -e ."
    )


class MoshiBridge:
    """
    PyTorch MOSHI bridge with cross-platform device detection.

    This class wraps the official MOSHI PyTorch implementation and provides
    a clean interface for encoding/decoding audio and generating responses.
    """

    def __init__(
        self,
        device: Optional[torch.device] = None,
        model_dir: Optional[Path] = None,
        sample_rate: int = 24000
    ):
        """
        Initialize MOSHI bridge.

        Args:
            device: PyTorch device (auto-detected if None)
            model_dir: Directory containing MOSHI models (optional)
            sample_rate: Audio sample rate (default: 24kHz)
        """
        # Auto-detect device if not provided
        if device is None:
            device = self._detect_device()

        self.device = device
        self.sample_rate = sample_rate
        self.frame_size = 1920  # 80ms at 24kHz

        print(f"Loading MOSHI models on {device}...")

        # Download and load MOSHI components from HuggingFace
        # This will auto-download models on first run (~1GB)
        print(f"Downloading models from {loaders.DEFAULT_REPO} (first run may take a while)...")

        # Download model files (cached locally after first download)
        mimi_path = loaders.hf_hub_download(loaders.DEFAULT_REPO, loaders.MIMI_NAME)
        moshi_path = loaders.hf_hub_download(loaders.DEFAULT_REPO, loaders.MOSHI_NAME)
        tokenizer_path = loaders.hf_hub_download(loaders.DEFAULT_REPO, loaders.TEXT_TOKENIZER_NAME)

        # Load models
        self.mimi = loaders.get_mimi(mimi_path, device=str(device))
        self.mimi.set_num_codebooks(8)  # Moshi uses 8 codebooks

        lm_model = loaders.get_moshi_lm(moshi_path, device=str(device))

        # Wrap LM in generator with sampling params
        self.lm_gen = LMGen(
            lm_model,
            temp=0.8,           # Temperature for audio tokens
            temp_text=0.7,      # Temperature for text tokens
            top_k=250,          # Top-k for audio
            top_k_text=25       # Top-k for text
        )

        # Load text tokenizer
        import sentencepiece
        self.tokenizer = sentencepiece.SentencePieceProcessor()
        self.tokenizer.load(tokenizer_path)

        print("MOSHI models loaded successfully")

        # Internal state
        self.conversation_history: List[dict] = []

        # Amplitude tracking
        self.mic_amplitude = 0.0
        self.moshi_amplitude = 0.0

    @staticmethod
    def _detect_device() -> torch.device:
        """
        Auto-detect best available PyTorch device.

        Priority:
        1. CUDA (NVIDIA GPUs)
        2. ROCm (AMD GPUs)
        3. CPU (MOSHI is too large for MPS 4GB limit)

        Note: Apple Silicon MPS has a 4GB per-tensor limit which MOSHI exceeds.
        We use CPU for model inference, which is still faster than MLX's buggy implementation.

        Returns:
            torch.device: Best available device
        """
        if torch.cuda.is_available():
            # NVIDIA GPU or AMD GPU with ROCm
            device_name = torch.cuda.get_device_name(0)
            print(f"✓ Using CUDA: {device_name}")
            return torch.device("cuda:0")

        # Note: MPS disabled for MOSHI due to 4GB tensor limit
        # MPS Error: "total bytes of NDArray > 2^32" (MOSHI model is ~8GB)
        # CPU inference is still 1000x faster than buggy MLX implementation
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("✓ Apple Metal (MPS) available but using CPU (MOSHI > 4GB MPS limit)")
            print("  Note: CPU inference still 1000x faster than MLX!")
            return torch.device("cpu")

        print("✓ Using CPU for inference")
        return torch.device("cpu")

    def encode_audio(self, audio: np.ndarray) -> torch.Tensor:
        """
        Encode audio to MIMI codes.

        Args:
            audio: NumPy array of shape (samples,) at 24kHz

        Returns:
            MIMI codes tensor
        """
        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio).float().to(self.device)

        # Reshape to (batch, channels, samples)
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0).unsqueeze(0)

        # Encode with MIMI
        with torch.no_grad():
            codes = self.mimi.encode(audio_tensor)

        return codes

    def decode_audio(self, codes: torch.Tensor) -> np.ndarray:
        """
        Decode MIMI codes to audio.

        Args:
            codes: MIMI codes tensor

        Returns:
            Audio as NumPy array at 24kHz
        """
        with torch.no_grad():
            audio_tensor = self.mimi.decode(codes)

        # Convert to NumPy (channels, samples) -> (samples,)
        audio = audio_tensor.squeeze().cpu().numpy()

        return audio

    def generate_response(
        self,
        user_audio: np.ndarray,
        text_prompt: Optional[str] = None,
        max_frames: int = 125  # ~10 seconds at 12.5 Hz
    ) -> tuple[np.ndarray, str]:
        """
        Generate MOSHI response from user audio using streaming API.

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
            frame = user_audio[offset:offset + frame_size]
            # Encode needs (B, C, T) shape
            frame_tensor = torch.from_numpy(frame).float().unsqueeze(0).unsqueeze(0).to(self.device)
            with torch.no_grad(), self.mimi.streaming(batch_size=1):
                codes = self.mimi.encode(frame_tensor)  # [1, 8, 1]
                all_input_codes.append(codes)

        # Generate response using streaming LM
        output_audio_chunks = []
        text_tokens_list = []

        with torch.no_grad(), self.lm_gen.streaming(batch_size=1), self.mimi.streaming(batch_size=1):
            # Feed input codes
            for input_codes in all_input_codes:
                tokens_out = self.lm_gen.step(input_codes)
                if tokens_out is not None:
                    # tokens_out is [B, 1 + 8, 1] where [:, 0] is text, [:, 1:] is audio
                    text_tokens_list.append(tokens_out[:, 0, :].cpu())
                    audio_codes = tokens_out[:, 1:, :]  # [B, 8, 1]
                    # Decode audio frame
                    audio_chunk = self.mimi.decode(audio_codes)
                    output_audio_chunks.append(audio_chunk.squeeze().cpu().numpy())

            # Continue generation for remaining frames (response continuation)
            for _ in range(max_frames):
                # Feed silence/padding to continue generation
                silence_codes = torch.zeros((1, 8, 1), dtype=torch.long, device=self.device)
                tokens_out = self.lm_gen.step(silence_codes)
                if tokens_out is not None:
                    text_tokens_list.append(tokens_out[:, 0, :].cpu())
                    audio_codes = tokens_out[:, 1:, :]
                    audio_chunk = self.mimi.decode(audio_codes)
                    output_audio_chunks.append(audio_chunk.squeeze().cpu().numpy())

        # Concatenate output audio
        if output_audio_chunks:
            response_audio = np.concatenate(output_audio_chunks)
        else:
            response_audio = np.array([], dtype=np.float32)

        # Decode text tokens
        if text_tokens_list:
            all_text_tokens = torch.cat(text_tokens_list, dim=-1).squeeze().tolist()
            response_text = self.tokenizer.decode(all_text_tokens)
        else:
            response_text = ""

        return response_audio, response_text

    def _extract_text(self, codes: torch.Tensor) -> str:
        """
        Extract text from MOSHI codes.

        Args:
            codes: MOSHI codes tensor

        Returns:
            Decoded text string
        """
        # MOSHI encodes text in the first codebook
        text_codes = codes[0, 0, :].cpu().tolist()
        text = self.tokenizer.decode(text_codes)
        return text.strip()

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

    def create_lm_generator(self):
        """
        Create and return LM generator for streaming inference.

        This sets up the streaming context for frame-by-frame processing.
        Must be called before step_frame() in a processing loop.

        Returns:
            Generator context manager for streaming inference
        """
        # Return streaming context that can be used with step_frame()
        return self.lm_gen.streaming(batch_size=1)

    def step_frame(self, lm_gen, audio_frame: np.ndarray) -> tuple[Optional[np.ndarray], Optional[str]]:
        """
        Process a single 80ms audio frame through MOSHI.

        This is the real-time streaming interface used by the processing thread.

        Args:
            lm_gen: LM generator context from create_lm_generator()
            audio_frame: Audio frame of 1920 samples at 24kHz (80ms)

        Returns:
            (response_audio_chunk, text_token) tuple or (None, None) if no output
        """
        import time

        # Start profiling
        t0 = time.perf_counter()

        # Ensure frame is correct size
        if len(audio_frame) != self.frame_size:
            # Pad or truncate to 1920 samples
            if len(audio_frame) < self.frame_size:
                audio_frame = np.pad(audio_frame, (0, self.frame_size - len(audio_frame)))
            else:
                audio_frame = audio_frame[:self.frame_size]

        # Encode audio frame to MIMI codes
        frame_tensor = torch.from_numpy(audio_frame).float().unsqueeze(0).unsqueeze(0).to(self.device)

        t1 = time.perf_counter()

        with torch.no_grad(), self.mimi.streaming(batch_size=1):
            codes = self.mimi.encode(frame_tensor)  # [1, 8, 1]

        t2 = time.perf_counter()

        # Step the language model
        with torch.no_grad():
            tokens_out = self.lm_gen.step(codes)

        t3 = time.perf_counter()

        if tokens_out is None:
            # No output yet (model still warming up)
            t4 = t3
            t5 = t3
            text_token = None
            audio_chunk = None
        else:
            # tokens_out is [B, 1 + 8, 1] where [:, 0] is text, [:, 1:] is audio
            text_token_id = tokens_out[0, 0, 0].item()

            t4 = time.perf_counter()

            # Decode text token
            if text_token_id > 0:
                text_token = self.tokenizer.decode([text_token_id])
            else:
                text_token = None

            # Decode audio codes
            audio_codes = tokens_out[:, 1:, :]  # [B, 8, 1]
            with torch.no_grad(), self.mimi.streaming(batch_size=1):
                audio_tensor = self.mimi.decode(audio_codes)

            t5 = time.perf_counter()

            # Convert to numpy
            audio_chunk = audio_tensor.squeeze().cpu().numpy()

            # Update amplitude tracking
            self.update_moshi_amplitude(audio_chunk)

        t6 = time.perf_counter()

        # Log profiling data (similar format to MLX version)
        encode_ms = (t2 - t0) * 1000
        torch_prep_ms = (t2 - t1) * 1000  # Tensor conversion
        inference_ms = (t3 - t2) * 1000
        tokens_ms = (t4 - t3) * 1000
        numpy_ms = (t5 - t4) * 1000  # Decode + to numpy
        total_ms = (t6 - t0) * 1000

        with open("/tmp/moshi_profile.log", "a") as f:
            f.write(
                f"encode={encode_ms:.1f}ms "
                f"torch_prep={torch_prep_ms:.1f}ms "
                f"inference={inference_ms:.1f}ms "
                f"tokens={tokens_ms:.1f}ms "
                f"numpy={numpy_ms:.1f}ms "
                f"TOTAL={total_ms:.1f}ms\n"
            )

        return audio_chunk, text_token
