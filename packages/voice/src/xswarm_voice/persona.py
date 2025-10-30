"""
Persona configuration loader for MOSHI voice bridge.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
import tomli

logger = logging.getLogger(__name__)


class PersonaConfig:
    """
    Loads and manages persona configuration for voice synthesis.

    Personas are defined in packages/personas/{name}/ with:
    - personality.md: Character description and dialogue samples
    - config.toml: Voice parameters and conditioning settings
    - audio/: Optional voice samples for cloning
    """

    def __init__(self, persona_name: str, project_root: Optional[Path] = None):
        """
        Initialize persona configuration.

        Args:
            persona_name: Name of the persona (e.g., "boss", "hal-9000")
            project_root: Optional project root path (auto-detected if None)
        """
        self.name = persona_name

        # Find project root (look for config.toml)
        if project_root is None:
            project_root = self._find_project_root()

        self.project_root = project_root
        self.persona_dir = project_root / "packages" / "personas" / persona_name

        # Configuration dictionaries
        self.config: Dict[str, Any] = {}
        self.personality: Optional[str] = None

        # Load configurations
        self._load_config()
        self._load_personality()

    def _find_project_root(self) -> Path:
        """
        Find the project root by looking for config.toml.

        Returns:
            Path to project root

        Raises:
            FileNotFoundError: If project root cannot be found
        """
        current = Path(__file__).resolve().parent

        # Walk up directories looking for config.toml
        for _ in range(10):  # Limit depth to avoid infinite loop
            if (current / "config.toml").exists():
                return current
            current = current.parent

        raise FileNotFoundError(
            "Could not find project root (config.toml not found). "
            "Please specify project_root explicitly."
        )

    def _load_config(self):
        """Load persona config.toml file."""
        config_path = self.persona_dir / "config.toml"

        if not config_path.exists():
            logger.warning(f"Persona config not found: {config_path}")
            logger.warning(f"Using default configuration for persona '{self.name}'")
            # Set minimal defaults
            self.config = {
                "persona": {
                    "name": self.name,
                    "voice_style": "neutral",
                    "speaking_pace": "moderate",
                    "formality": "professional",
                },
                "conditioning": {
                    "system_prompt": f"You are {self.name}, a helpful AI assistant.",
                },
                "voice": {
                    "sample_rate": 24000,
                    "chunk_duration_ms": 80,
                    "model_temperature": 0.8,
                },
            }
            return

        try:
            with open(config_path, "rb") as f:
                self.config = tomli.load(f)

            logger.info(f"✓ Loaded persona config: {config_path}")
            logger.info(f"  Voice style: {self.config.get('persona', {}).get('voice_style', 'unknown')}")
            logger.info(f"  Speaking pace: {self.config.get('persona', {}).get('speaking_pace', 'unknown')}")

        except Exception as e:
            logger.error(f"Failed to load persona config: {e}")
            raise

    def _load_personality(self):
        """Load personality.md file."""
        personality_path = self.persona_dir / "personality.md"

        if not personality_path.exists():
            logger.warning(f"Personality description not found: {personality_path}")
            return

        try:
            with open(personality_path, "r", encoding="utf-8") as f:
                self.personality = f.read()

            logger.info(f"✓ Loaded personality description: {personality_path}")
            logger.info(f"  Length: {len(self.personality)} characters")

        except Exception as e:
            logger.error(f"Failed to load personality: {e}")
            # Non-fatal, continue without personality description

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for model conditioning.

        Returns:
            System prompt string
        """
        return self.config.get("conditioning", {}).get(
            "system_prompt",
            f"You are {self.name}, a helpful AI assistant."
        )

    def get_voice_params(self) -> Dict[str, Any]:
        """
        Get voice synthesis parameters.

        Returns:
            Dictionary of voice parameters
        """
        return self.config.get("voice", {})

    def get_persona_params(self) -> Dict[str, Any]:
        """
        Get persona characteristics.

        Returns:
            Dictionary of persona parameters
        """
        return self.config.get("persona", {})

    def get_conditioning_params(self) -> Dict[str, Any]:
        """
        Get conditioning parameters for the model.

        Returns:
            Dictionary with all conditioning info
        """
        return {
            "system_prompt": self.get_system_prompt(),
            "voice_style": self.config.get("persona", {}).get("voice_style", "neutral"),
            "speaking_pace": self.config.get("persona", {}).get("speaking_pace", "moderate"),
            "formality": self.config.get("persona", {}).get("formality", "professional"),
            "pitch_shift": self.config.get("persona", {}).get("pitch_shift", 0.0),
            "speech_rate": self.config.get("persona", {}).get("speech_rate", 1.0),
            "warmth": self.config.get("persona", {}).get("warmth", 0.5),
            "temperature": self.config.get("voice", {}).get("model_temperature", 0.8),
            "top_p": self.config.get("voice", {}).get("top_p", 0.9),
            "repetition_penalty": self.config.get("voice", {}).get("repetition_penalty", 1.0),
        }

    def get_audio_params(self) -> Dict[str, Any]:
        """
        Get audio processing parameters.

        Returns:
            Dictionary with audio parameters
        """
        voice = self.config.get("voice", {})
        return {
            "sample_rate": voice.get("sample_rate", 24000),
            "chunk_duration_ms": voice.get("chunk_duration_ms", 80),
        }


def load_persona_from_config(config_path: Path) -> PersonaConfig:
    """
    Load persona configuration from main config.toml file.

    Args:
        config_path: Path to main config.toml file

    Returns:
        PersonaConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If persona not specified in config
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load main config
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    # Try to get persona name from config
    # Check test_user.persona first, then voice.default_persona
    persona_name = None

    if "test_user" in config and "persona" in config["test_user"]:
        persona_name = config["test_user"]["persona"]
        logger.info(f"Using persona from test_user: {persona_name}")
    elif "voice" in config and "default_persona" in config["voice"]:
        persona_name = config["voice"]["default_persona"]
        logger.info(f"Using default persona: {persona_name}")

    if not persona_name:
        raise ValueError(
            "No persona specified in config. Please set either:\n"
            "  test_user.persona = \"name\"\n"
            "  or voice.default_persona = \"name\""
        )

    # Get project root from config path
    project_root = config_path.parent

    # Load and return persona config
    return PersonaConfig(persona_name, project_root)
