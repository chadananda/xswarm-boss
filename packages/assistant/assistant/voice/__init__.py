"""
Voice processing components for the assistant.
"""

# Import MLX bridge (optimized for Apple Silicon Metal GPU)
from .moshi_mlx import MoshiBridge
from .audio_io import AudioIO
from .vad import VoiceActivityDetector

__all__ = [
    "MoshiBridge",
    "AudioIO",
    "VoiceActivityDetector",
]
