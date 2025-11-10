"""
Base classes and interfaces for xswarm plugins.

All plugins must inherit from PluginBase and implement required methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field
from textual.widgets import Widget
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PluginPermissions(BaseModel):
    """
    Permissions requested by a plugin.

    Controls what system resources the plugin can access.
    """

    filesystem_read: bool = Field(False, description="Read files from filesystem")
    filesystem_write: bool = Field(False, description="Write files to filesystem")
    network: bool = Field(False, description="Make network requests")
    clipboard: bool = Field(False, description="Access system clipboard")
    subprocess: bool = Field(False, description="Execute subprocesses")
    config_read: bool = Field(False, description="Read app configuration")
    config_write: bool = Field(False, description="Modify app configuration")


class PluginMetadata(BaseModel):
    """
    Plugin metadata from manifest.yaml.
    """

    # Identity
    name: str = Field(..., description="Plugin name (slug)")
    display_name: str = Field(..., description="Human-readable name")
    version: str = Field(..., description="Semantic version")
    author: str = Field(..., description="Author name or organization")
    description: str = Field("", description="Brief description")
    license: str = Field("MIT", description="License (MIT, GPL, etc.)")

    # Dependencies
    dependencies: List[str] = Field(default_factory=list, description="Python package dependencies")
    min_xswarm_version: Optional[str] = Field(None, description="Minimum xswarm version required")

    # Permissions
    permissions: PluginPermissions = Field(default_factory=PluginPermissions)

    # Entry point
    entry: str = Field("plugin.py", description="Entry point Python file")
    widget_class: Optional[str] = Field(None, description="Widget class name (if plugin has UI)")

    # Configuration
    settings: Dict[str, Any] = Field(default_factory=dict, description="User-configurable settings")

    # Categorization
    category: str = Field("utility", description="Plugin category (productivity, theme, integration, etc.)")
    tags: List[str] = Field(default_factory=list, description="Search tags")

    # URLs
    homepage: Optional[str] = None
    repository: Optional[str] = None
    documentation: Optional[str] = None


class PluginCommand(BaseModel):
    """
    Voice command registered by plugin.
    """

    name: str = Field(..., description="Command name (e.g., 'search files')")
    handler: str = Field(..., description="Method name to call")
    description: str = Field("", description="Command description for help")
    aliases: List[str] = Field(default_factory=list, description="Alternative command phrases")


class PluginBase(ABC):
    """
    Base class for all xswarm plugins.

    Plugins must inherit from this class and implement required methods.
    """

    def __init__(self, plugin_dir: Path, metadata: PluginMetadata):
        """
        Initialize plugin.

        Args:
            plugin_dir: Path to plugin directory
            metadata: Parsed plugin metadata
        """
        self.plugin_dir = plugin_dir
        self.metadata = metadata
        self.enabled = False
        self.logger = logging.getLogger(f"plugin.{metadata.name}")

        # User settings (loaded from config)
        self.settings: Dict[str, Any] = {}

    @abstractmethod
    def on_load(self) -> bool:
        """
        Called when plugin is loaded.

        Perform initialization, check dependencies, etc.

        Returns:
            True if load successful, False otherwise
        """
        pass

    @abstractmethod
    def on_unload(self) -> bool:
        """
        Called when plugin is unloaded or app exits.

        Clean up resources, save state, etc.

        Returns:
            True if unload successful, False otherwise
        """
        pass

    def on_enable(self) -> bool:
        """
        Called when plugin is enabled (after load).

        Returns:
            True if enable successful, False otherwise
        """
        self.enabled = True
        return True

    def on_disable(self) -> bool:
        """
        Called when plugin is disabled (but still loaded).

        Returns:
            True if disable successful, False otherwise
        """
        self.enabled = False
        return True

    def get_widget(self) -> Optional[Widget]:
        """
        Get Textual widget for this plugin (if plugin has UI).

        Returns:
            Textual Widget instance, or None if plugin has no UI
        """
        return None

    def get_commands(self) -> List[PluginCommand]:
        """
        Get list of voice commands registered by this plugin.

        Returns:
            List of PluginCommand objects
        """
        return []

    def handle_command(self, command: str, args: Dict[str, Any]) -> Any:
        """
        Handle voice command directed to this plugin.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Command result (can be text, data, etc.)
        """
        self.logger.warning(f"Unhandled command: {command}")
        return None

    def get_settings_schema(self) -> Dict[str, Any]:
        """
        Get JSON schema for plugin settings.

        Returns:
            JSON schema dict describing configurable settings
        """
        return self.metadata.settings

    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Update plugin settings.

        Args:
            settings: New settings dict

        Returns:
            True if settings valid and applied, False otherwise
        """
        self.settings.update(settings)
        return True

    def get_status(self) -> Dict[str, Any]:
        """
        Get plugin status information.

        Returns:
            Dict with status info (for debugging, monitoring)
        """
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "enabled": self.enabled,
            "loaded": True,
        }

    # Helper methods for common tasks

    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message)

    def read_plugin_file(self, filename: str) -> Optional[str]:
        """
        Read file from plugin directory.

        Args:
            filename: File name relative to plugin dir

        Returns:
            File contents as string, or None if file doesn't exist
        """
        file_path = self.plugin_dir / filename
        if not file_path.exists():
            self.log_error(f"File not found: {filename}")
            return None

        try:
            with open(file_path, 'r') as f:
                return f.read()
        except Exception as e:
            self.log_error(f"Failed to read {filename}: {e}")
            return None

    def write_plugin_file(self, filename: str, content: str) -> bool:
        """
        Write file to plugin directory (requires filesystem_write permission).

        Args:
            filename: File name relative to plugin dir
            content: Content to write

        Returns:
            True if successful, False otherwise
        """
        if not self.metadata.permissions.filesystem_write:
            self.log_error("filesystem_write permission not granted")
            return False

        file_path = self.plugin_dir / filename
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            self.log_error(f"Failed to write {filename}: {e}")
            return False


class PluginError(Exception):
    """Base exception for plugin-related errors"""
    pass


class PluginLoadError(PluginError):
    """Raised when plugin fails to load"""
    pass


class PluginPermissionError(PluginError):
    """Raised when plugin attempts unauthorized action"""
    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies are missing"""
    pass
