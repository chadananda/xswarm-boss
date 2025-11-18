"""
Voice processing components for the assistant.
"""

# Import PyTorch bridge (cross-platform, MPS/CUDA/ROCm support)
from .moshi_pytorch import MoshiBridge
from .audio_io import AudioIO
from .vad import VoiceActivityDetector

__all__ = [
    "MoshiBridge",
    "AudioIO",
    "VoiceActivityDetector",
]
