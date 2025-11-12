"""
Tool calling system for Moshi voice assistant.

Provides function calling capabilities for the assistant,
allowing it to perform actions like theme changes, persona switching, etc.
"""

from .registry import ToolRegistry, Tool
from .theme_tool import ThemeChangeTool

__all__ = ["ToolRegistry", "Tool", "ThemeChangeTool"]
