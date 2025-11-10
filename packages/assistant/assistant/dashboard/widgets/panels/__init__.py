"""
Multi-panel system for comprehensive TUI.

All panels inherit from PanelBase for consistent behavior.
"""

from .panel_base import PanelBase
from .chat_panel import ChatPanel, Message

__all__ = ["PanelBase", "ChatPanel", "Message"]
