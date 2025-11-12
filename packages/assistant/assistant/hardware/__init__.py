"""Hardware detection and capability assessment."""

from .gpu_detector import GPUCapability, detect_gpu_capability

__all__ = ["GPUCapability", "detect_gpu_capability"]
