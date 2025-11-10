"""
Application configuration with cross-platform device detection.
Supports MPS (Mac M3), ROCm/CUDA (AMD/NVIDIA), and CPU fallback.
"""

import torch
import yaml
from pathlib import Path
from typing import Literal, Optional
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
    wake_word: str = "jarvis"  # Default, overridden by persona
    wake_word_model: Path = Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15"
    wake_word_sensitivity: float = 0.7  # 0.0-1.0

    # Server settings
    server_url: str = "http://localhost:3000"

    # Memory settings
    api_token: Optional[str] = None
    memory_enabled: bool = True

    # Persona settings
    default_persona: Optional[str] = None

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

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the default config file path."""
        config_dir = Path.home() / ".config" / "xswarm"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.yaml"

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from YAML file.

        Args:
            config_path: Optional custom config path. If None, uses ~/.config/xswarm/config.yaml

        Returns:
            Config: Loaded configuration, or default config if file doesn't exist
        """
        if config_path is None:
            config_path = cls.get_config_path()

        if not config_path.exists():
            # Return default config if file doesn't exist
            return cls()

        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)

            # Convert string paths back to Path objects
            if "model_dir" in data:
                data["model_dir"] = Path(data["model_dir"])
            if "wake_word_model" in data:
                data["wake_word_model"] = Path(data["wake_word_model"])

            return cls(**data)
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
            print("Using default configuration")
            return cls()

    def save_to_file(self, config_path: Optional[Path] = None):
        """
        Save configuration to YAML file.

        Args:
            config_path: Optional custom config path. If None, uses ~/.config/xswarm/config.yaml
        """
        if config_path is None:
            config_path = self.get_config_path()

        # Convert Path objects to strings for YAML serialization
        data = self.dict()
        data["model_dir"] = str(data["model_dir"])
        data["wake_word_model"] = str(data["wake_word_model"])

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            print(f"Configuration saved to {config_path}")
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
