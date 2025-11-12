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
    from moshi.models import loaders
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

        # Load MOSHI components
        self.mimi = loaders.load_mimi(device=str(device))
        self.lm = loaders.load_lm(device=str(device))
        self.tokenizer = loaders.load_text_tokenizer()

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
        3. MPS (Apple Silicon)
        4. CPU (fallback)

        Returns:
            torch.device: Best available device
        """
        if torch.cuda.is_available():
            # NVIDIA GPU or AMD GPU with ROCm
            device_name = torch.cuda.get_device_name(0)
            print(f"✓ Using CUDA: {device_name}")
            return torch.device("cuda:0")

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # Apple Silicon (M1/M2/M3)
            print("✓ Using Apple Metal (MPS)")
            return torch.device("mps")

        print("⚠ Using CPU (no GPU acceleration)")
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
        max_tokens: int = 500
    ) -> tuple[np.ndarray, str]:
        """
        Generate MOSHI response from user audio.

        Args:
            user_audio: User audio at 24kHz
            text_prompt: Optional text context (e.g., from persona)
            max_tokens: Max generation length

        Returns:
            (response_audio, response_text) tuple
        """
        # Encode user audio
        user_codes = self.encode_audio(user_audio)

        # Prepare text prompt if provided
        text_tokens = None
        if text_prompt:
            text_tokens = self.tokenizer.encode(text_prompt)
            text_tokens = torch.tensor([text_tokens], device=self.device)

        # Generate response
        with torch.no_grad():
            response_codes = self.lm.generate(
                user_codes,
                text_tokens=text_tokens,
                max_new_tokens=max_tokens,
                temperature=0.8,
                top_k=25
            )

        # Decode response audio
        response_audio = self.decode_audio(response_codes)

        # Decode text (if available)
        response_text = self._extract_text(response_codes)

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
