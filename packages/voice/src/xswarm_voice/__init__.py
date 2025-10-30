"""
xSwarm Voice Bridge - MOSHI integration for xSwarm
"""

__version__ = "0.1.0"

from .bridge import VoiceBridge
from .server import VoiceServer

__all__ = ["VoiceBridge", "VoiceServer"]
