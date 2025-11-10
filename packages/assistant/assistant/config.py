"""
Application configuration with cross-platform device detection.
Supports MPS (Mac M3), ROCm/CUDA (AMD/NVIDIA), and CPU fallback.
"""

import torch
from pathlib import Path
from typing import Literal
from pydantic import BaseModel


class Config(BaseModel):
    """Application configuration"""

    # Device settings
    device: str = "auto"  # auto, mps, cuda, cpu

    # Audio settings
    sample_rate: int = 24000
    frame_size: int = 1920  # 80ms at 24kHz

    # MOSHI model paths
    model_dir: Path = Path.home() / ".cache" / "moshi"

    # Wake word settings
    wake_word: str = "jarvis"  # Can be customized per persona
    wake_word_model: Path = Path.home() / ".cache" / "vosk-model-small-en-us-0.15"

    # Server settings
    server_url: str = "http://localhost:3000"

    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True

    def detect_device(self) -> torch.device:
        """
        Detect best available device for PyTorch.

        Priority:
        1. CUDA/ROCm (NVIDIA/AMD GPUs)
        2. MPS (Mac M3 Metal)
        3. CPU (fallback)

        Returns:
            torch.device: Best available device
        """
        if self.device == "auto":
            if torch.cuda.is_available():
                # ROCm or CUDA
                device_name = torch.cuda.get_device_name(0)
                print(f"Using CUDA/ROCm device: {device_name}")
                return torch.device("cuda")
            elif torch.backends.mps.is_available():
                # Mac M3 Metal
                print("Using MPS (Metal) device")
                return torch.device("mps")
            else:
                print("Using CPU device")
                return torch.device("cpu")
        else:
            return torch.device(self.device)
