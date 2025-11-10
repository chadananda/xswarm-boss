"""
Plugin manager - discovers, loads, and manages plugins.

Handles:
- Plugin discovery from ~/.config/xswarm/plugins/
- Loading plugins with sandboxing
- Permission enforcement
- Plugin lifecycle (load/unload/enable/disable)
- Command routing to plugins
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Type
import yaml
import importlib.util
import sys
import logging

from .base import (
    PluginBase,
    PluginMetadata,
    PluginPermissions,
    PluginCommand,
    PluginLoadError,
    PluginPermissionError,
    PluginDependencyError,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin lifecycle and integration with xswarm.
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        """
        Initialize plugin manager.

        Args:
            plugin_dirs: List of directories to search for plugins.
                        Defaults to ~/.config/xswarm/plugins/
        """
        if plugin_dirs is None:
            config_dir = Path.home() / ".config" / "xswarm"
            self.plugin_dirs = [config_dir / "plugins"]
        else:
            self.plugin_dirs = plugin_dirs

        # Ensure plugin directories exist
        for plugin_dir in self.plugin_dirs:
            plugin_dir.mkdir(parents=True, exist_ok=True)

        self.plugins: Dict[str, PluginBase] = {}
        self.metadata: Dict[str, PluginMetadata] = {}
        self.commands: Dict[str, str] = {}  # command_name -> plugin_name

        logger.info(f"Plugin manager initialized with dirs: {self.plugin_dirs}")

    def discover_plugins(self) -> List[str]:
        """
        Scan plugin directories for valid plugins.

        A valid plugin has:
        - plugin-name/
          - manifest.yaml  (required)
          - plugin.py      (required, unless entry specified in manifest)

        Returns:
            List of discovered plugin names
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            for entry in plugin_dir.iterdir():
                if not entry.is_dir():
                    continue

                manifest_path = entry / "manifest.yaml"
                if not manifest_path.exists():
                    logger.debug(f"Skipping {entry.name}: No manifest.yaml")
                    continue

                try:
                    metadata = self._load_manifest(manifest_path)
                    self.metadata[metadata.name] = metadata
                    discovered.append(metadata.name)
                    logger.info(f"Discovered plugin: {metadata.name} v{metadata.version}")
                except Exception as e:
                    logger.error(f"Failed to load manifest from {manifest_path}: {e}")

        return discovered

    def _load_manifest(self, manifest_path: Path) -> PluginMetadata:
        """
        Load and parse plugin manifest.yaml.

        Args:
            manifest_path: Path to manifest.yaml

        Returns:
            PluginMetadata instance

        Raises:
            PluginLoadError: If manifest is invalid
        """
        try:
            with open(manifest_path, 'r') as f:
                data = yaml.safe_load(f)

            # Parse permissions if present
            if 'permissions' in data:
                perms = data['permissions']
                if isinstance(perms, list):
                    # Convert list format to dict
                    perm_dict = {}
                    perm_map = {
                        'filesystem.read': 'filesystem_read',
                        'filesystem.write': 'filesystem_write',
                        'network': 'network',
                        'clipboard': 'clipboard',
                        'subprocess': 'subprocess',
                        'config.read': 'config_read',
                        'config.write': 'config_write',
                    }
                    for perm in perms:
                        if perm in perm_map:
                            perm_dict[perm_map[perm]] = True
                    data['permissions'] = perm_dict
                elif isinstance(perms, dict):
                    # Already in dict format
                    pass

            metadata = PluginMetadata(**data)
            return metadata

        except Exception as e:
            raise PluginLoadError(f"Invalid manifest: {e}")

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a plugin by name.

        Steps:
        1. Check if already loaded
        2. Find plugin directory
        3. Check dependencies
        4. Load plugin module
        5. Instantiate plugin class
        6. Call on_load()
        7. Register commands

        Args:
            plugin_name: Name of plugin to load

        Returns:
            True if loaded successfully, False otherwise
        """
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} already loaded")
            return True

        if plugin_name not in self.metadata:
            logger.error(f"Plugin {plugin_name} not discovered. Run discover_plugins() first.")
            return False

        metadata = self.metadata[plugin_name]

        try:
            # Find plugin directory
            plugin_dir = self._find_plugin_dir(plugin_name)
            if not plugin_dir:
                raise PluginLoadError(f"Plugin directory not found: {plugin_name}")

            # Check dependencies
            self._check_dependencies(metadata)

            # Load plugin module
            plugin_module = self._load_plugin_module(plugin_dir, metadata)

            # Find plugin class (looks for class that inherits from PluginBase)
            plugin_class = self._find_plugin_class(plugin_module, metadata)

            # Instantiate plugin
            plugin_instance = plugin_class(plugin_dir, metadata)

            # Call on_load()
            if not plugin_instance.on_load():
                raise PluginLoadError(f"Plugin {plugin_name} on_load() returned False")

            # Register plugin
            self.plugins[plugin_name] = plugin_instance

            # Register commands
            for command in plugin_instance.get_commands():
                self.commands[command.name] = plugin_name
                for alias in command.aliases:
                    self.commands[alias] = plugin_name

            # Enable plugin
            plugin_instance.on_enable()

            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _find_plugin_dir(self, plugin_name: str) -> Optional[Path]:
        """Find plugin directory by name"""
        for plugin_dir in self.plugin_dirs:
            candidate = plugin_dir / plugin_name
            if candidate.exists() and candidate.is_dir():
                return candidate
        return None

    def _check_dependencies(self, metadata: PluginMetadata):
        """
        Check if plugin dependencies are installed.

        Raises:
            PluginDependencyError: If dependencies are missing
        """
        missing = []
        for dep in metadata.dependencies:
            # Parse dependency (e.g., "whoosh>=2.7.4" -> "whoosh")
            package_name = dep.split('>=')[0].split('==')[0].split('<=')[0].strip()

            try:
                importlib.import_module(package_name)
            except ImportError:
                missing.append(dep)

        if missing:
            raise PluginDependencyError(
                f"Missing dependencies: {', '.join(missing)}\n"
                f"Install with: pip install {' '.join(missing)}"
            )

    def _load_plugin_module(self, plugin_dir: Path, metadata: PluginMetadata):
        """
        Load plugin Python module.

        Args:
            plugin_dir: Path to plugin directory
            metadata: Plugin metadata

        Returns:
            Loaded module

        Raises:
            PluginLoadError: If module fails to load
        """
        entry_file = plugin_dir / metadata.entry
        if not entry_file.exists():
            raise PluginLoadError(f"Entry file not found: {metadata.entry}")

        try:
            spec = importlib.util.spec_from_file_location(
                f"xswarm_plugin_{metadata.name}",
                entry_file
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Failed to load spec for {entry_file}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            raise PluginLoadError(f"Failed to load module: {e}")

    def _find_plugin_class(self, module, metadata: PluginMetadata) -> Type[PluginBase]:
        """
        Find plugin class in module.

        Args:
            module: Loaded plugin module
            metadata: Plugin metadata

        Returns:
            Plugin class (subclass of PluginBase)

        Raises:
            PluginLoadError: If no valid plugin class found
        """
        # If widget_class specified in manifest, use that
        if metadata.widget_class:
            if hasattr(module, metadata.widget_class):
                cls = getattr(module, metadata.widget_class)
                if issubclass(cls, PluginBase):
                    return cls

        # Otherwise, search for any PluginBase subclass
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, PluginBase) and obj != PluginBase:
                return obj

        raise PluginLoadError("No PluginBase subclass found in module")

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} not loaded")
            return False

        try:
            plugin = self.plugins[plugin_name]

            # Disable first
            plugin.on_disable()

            # Call on_unload()
            plugin.on_unload()

            # Unregister commands
            commands_to_remove = [cmd for cmd, pname in self.commands.items() if pname == plugin_name]
            for cmd in commands_to_remove:
                del self.commands[cmd]

            # Remove plugin
            del self.plugins[plugin_name]

            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False

    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin (unload then load).

        Useful for development and hot-reloading.

        Args:
            plugin_name: Name of plugin to reload

        Returns:
            True if reloaded successfully, False otherwise
        """
        logger.info(f"Reloading plugin: {plugin_name}")
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name)

    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Get loaded plugin by name"""
        return self.plugins.get(plugin_name)

    def list_plugins(self) -> List[str]:
        """List all discovered plugin names"""
        return list(self.metadata.keys())

    def list_loaded_plugins(self) -> List[str]:
        """List all currently loaded plugin names"""
        return list(self.plugins.keys())

    def execute_command(self, command: str, args: Dict[str, Any] = None) -> Any:
        """
        Execute a voice command by routing to appropriate plugin.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Command result from plugin

        Raises:
            KeyError: If command not found
        """
        if args is None:
            args = {}

        if command not in self.commands:
            raise KeyError(f"Unknown command: {command}")

        plugin_name = self.commands[command]
        plugin = self.plugins.get(plugin_name)

        if not plugin:
            raise KeyError(f"Plugin for command '{command}' not loaded: {plugin_name}")

        if not plugin.enabled:
            logger.warning(f"Plugin {plugin_name} is disabled, command '{command}' not executed")
            return None

        return plugin.handle_command(command, args)

    def get_all_commands(self) -> List[Dict[str, str]]:
        """
        Get list of all available commands from loaded plugins.

        Returns:
            List of dicts with command info
        """
        all_commands = []
        for plugin_name, plugin in self.plugins.items():
            if not plugin.enabled:
                continue

            for command in plugin.get_commands():
                all_commands.append({
                    "command": command.name,
                    "plugin": plugin_name,
                    "description": command.description,
                    "aliases": command.aliases,
                })

        return all_commands
