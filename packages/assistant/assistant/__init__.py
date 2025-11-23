"""
Voice Assistant with MOSHI, Textual TUI, and persona system.
"""

from .config import Config

__version__ = Config.get_project_version()
__all__ = ["Config"]
