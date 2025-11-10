"""
Plugin system for xswarm assistant.

Enables dynamic loading of features and community contributions.
"""

from .base import PluginBase, PluginMetadata, PluginPermissions
from .manager import PluginManager

__all__ = [
    "PluginBase",
    "PluginMetadata",
    "PluginPermissions",
    "PluginManager",
]
