"""
Application configuration with cross-platform device detection.
Supports MPS (Mac M3), ROCm/CUDA (AMD/NVIDIA), and CPU fallback.
"""

import torch
import yaml
from pathlib import Path
from typing import Literal, Optional, List
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
    wake_word: str | List[str] = "jarvis"  # Default, overridden by persona
    wake_word_model: Path = Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15"
    wake_word_sensitivity: float = 0.7  # 0.0-1.0

    # Server settings
    server_url: str = "http://localhost:3000"

    # Memory settings
    api_token: Optional[str] = None
    memory_enabled: bool = True

    # Voice configuration
    voice_enabled: bool = False  # Voice disabled by default
    moshi_quality: str = "q4"
    moshi_mode: str = "local"
    
    # Persona settings
    default_persona: Optional[str] = "Jarvis"  # Default to Jarvis persona

    # UI Theme settings
    theme_base_color: str = "#8899aa"  # Base color for shade palette generation
    # Can be: hex color ("#8899aa"), or preset name ("blue-gray", "slate", "cyan", etc.)

    # Service selection settings (auto-selected based on GPU capability)
    moshi_quality: str = "auto"  # "auto", "bf16", "q8", "q4", or "cloud"
    thinking_mode: str = "auto"  # "auto", "local", or "cloud"
    thinking_model: str = "auto"  # "auto", "ollama:70b", "ollama:13b", "ollama:7b", or "anthropic:claude"
    embedding_mode: str = "cpu"  # "cpu" or "cloud" (always CPU for now)

    # API Keys (loaded from .env in debug mode)
    is_debug_mode: bool = False  # Set to True when --debug flag used
    anthropic_api_key: Optional[str] = None  # For cloud thinking
    openai_api_key: Optional[str] = None  # For future cloud services
    openrouter_api_key: Optional[str] = None  # For alternative cloud routing
    google_api_key: Optional[str] = None  # For Google Gemini
    groq_api_key: Optional[str] = None  # For Groq

    # AI Thinking Configuration (Settings pane)
    ai_provider: str = "anthropic"  # anthropic, openai, google, openrouter, groq
    ai_auth_method: str = "api_key"  # api_key, oauth
    ai_model: str = "claude-sonnet-4-5"  # Provider-specific model ID

    # OAuth tokens (encrypted storage)
    anthropic_oauth_token: Optional[str] = None

    # Local AI settings
    local_ai_provider: str = "disabled"  # disabled, ollama, lmstudio
    local_ai_model: str = ""  # Model name for local provider

    # Network Mode
    network_role: str = "standalone"  # standalone, master, slave
    master_address: str = ""  # Address of master when in slave mode

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
    def load_env_keys(cls, config: "Config") -> "Config":
        """
        Load API keys from .env file when in debug mode.

        Only loads keys if is_debug_mode is True.

        Args:
            config: Existing config to update

        Returns:
            Config: Updated configuration with API keys
        """
        if not config.is_debug_mode:
            return config

        try:
            from dotenv import load_dotenv
            import os

            # Load .env from project root
            load_dotenv()

            # Load API keys from environment
            if os.getenv("ANTHROPIC_API_KEY"):
                config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

            if os.getenv("OPENAI_API_KEY"):
                config.openai_api_key = os.getenv("OPENAI_API_KEY")

            if os.getenv("OPENROUTER_API_KEY"):
                config.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

            if os.getenv("GOOGLE_API_KEY"):
                config.google_api_key = os.getenv("GOOGLE_API_KEY")

            if os.getenv("GROQ_API_KEY"):
                config.groq_api_key = os.getenv("GROQ_API_KEY")

        except ImportError:
            pass  # python-dotenv not installed

        return config

    @classmethod
    def load_from_file(cls, config_path: Optional[Path] = None) -> "Config":
        """
        Load configuration from file (YAML or JSON).
        Prioritizes:
        1. Custom path (if provided)
        2. Project root config.json (if exists)
        3. ~/.config/xswarm/config.yaml (default)

        Args:
            config_path: Optional custom config path.

        Returns:
            Config: Loaded configuration
        """
        # 1. Try custom path
        if config_path and config_path.exists():
            return cls._load_from_path(config_path)

        # 2. Try project root config.json
        root_config = Path("config.json")
        if root_config.exists():
            print(f"Loading config from project root: {root_config.absolute()}")
            return cls._load_from_json_root(root_config)

        # 3. Try default user config
        default_path = cls.get_config_path()
        if default_path.exists():
            return cls._load_from_path(default_path)

        # 4. Return default
        return cls()

    @classmethod
    def _load_from_path(cls, path: Path) -> "Config":
        """Helper to load from YAML/JSON based on extension"""
        try:
            with open(path, "r") as f:
                if path.suffix == ".json":
                    import json
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)
            
            # Handle potential nested structure if loading raw config.json directly
            if "voice" in data:
                return cls._map_root_json_to_config(data)

            # Convert string paths back to Path objects
            if "model_dir" in data:
                data["model_dir"] = Path(data["model_dir"])
            if "wake_word_model" in data:
                data["wake_word_model"] = Path(data["wake_word_model"])

            return cls(**data)
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
            return cls()

    @classmethod
    def _load_from_json_root(cls, path: Path) -> "Config":
        """Load from the specific project root config.json structure"""
        try:
            import json
            with open(path, "r") as f:
                data = json.load(f)
            return cls._map_root_json_to_config(data)
        except Exception as e:
            print(f"Error loading root config.json: {e}")
            return cls()

    @classmethod
    def _map_root_json_to_config(cls, data: dict) -> "Config":
        """Map root config.json structure to Config model"""
        config_data = {}
        
        # Map 'voice' section
        if "voice" in data:
            voice = data["voice"]
            if "defaultPersona" in voice:
                config_data["default_persona"] = voice["defaultPersona"]
            if "sampleRate" in voice:
                config_data["sample_rate"] = voice["sampleRate"]
            
            # Map wake word
            if "wakeWord" in voice and isinstance(voice["wakeWord"], dict):
                ww = voice["wakeWord"]
                if "keywords" in ww:
                    config_data["wake_word"] = ww["keywords"]
        
        # Map 'ai' section
        if "ai" in data:
            ai = data["ai"]
            if "defaultTextProvider" in ai:
                # Map to thinking model if possible, or just note it
                pass
                
        # Map 'server' section
        if "server" in data:
            server = data["server"]
            host = server.get("host", "localhost")
            port = server.get("port", 8787)
            protocol = "https" if server.get("useHttps") else "http"
            config_data["server_url"] = f"{protocol}://{host}:{port}"

        return cls(**config_data)

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

    @staticmethod
    def get_common_wake_words() -> List[str]:
        """
        Get list of common wake words that are always available.

        These are generic wake words that users might say when they forget
        which persona is active. They work in addition to persona-specific names.

        Returns:
            List of common wake word strings
        """
        return [
            "computer",
            "alexa",
            "boss",
            "assistant",
            "hey"
        ]

    @staticmethod
    def get_project_version() -> str:
        """
        Get project version from root config.json.
        Source of Truth: /config.json
        """
        try:
            import json
            # Look for config.json in project root (3 levels up from this file)
            # packages/assistant/assistant/config.py -> packages/assistant/assistant -> packages/assistant -> packages -> root
            # Actually it's 4 levels:
            # 1. assistant (package)
            # 2. assistant (package root)
            # 3. packages
            # 4. root
            
            # Let's try to find it relative to this file
            current_file = Path(__file__).resolve()
            # parents[0] = assistant/assistant
            # parents[1] = assistant
            # parents[2] = packages
            # parents[3] = root
            
            project_root = current_file.parents[3]
            config_path = project_root / "config.json"
            
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = json.load(f)
                    return data.get("project", {}).get("version", "0.0.0")
            
            # Fallback to package.json
            package_json = project_root / "package.json"
            if package_json.exists():
                with open(package_json, "r") as f:
                    data = json.load(f)
                    return data.get("version", "0.0.0")
                    
        except Exception as e:
            print(f"Error reading version from root: {e}")
            
        return "0.0.0"
