"""External persona system - loads from YAML configs"""

from .config import PersonaConfig, PersonalityTraits, VoiceSettings
from .manager import PersonaManager

__all__ = [
    "PersonaConfig",
    "PersonalityTraits",
    "VoiceSettings",
    "PersonaManager"
]
