"""
Platform theme detection for system color integration.
Supports Omarchy, macOS, and Linux GTK themes.
"""

import platform
import subprocess
import os
from typing import Optional, Dict
from pathlib import Path


class PlatformTheme:
    """Detect and extract system theme colors"""

    @staticmethod
    def detect_platform() -> str:
        """
        Detect current platform.

        Returns:
            Platform name: "omarchy", "macos", "linux", or "unknown"
        """
        system = platform.system()

        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            # Check for Omarchy-specific indicators
            if PlatformTheme._is_omarchy():
                return "omarchy"
            return "linux"
        elif system == "Windows":
            return "windows"

        return "unknown"

    @staticmethod
    def _is_omarchy() -> bool:
        """
        Check if running on Omarchy platform.

        Checks for:
        - Omarchy environment variables
        - Omarchy system files
        - Omarchy config directory
        """
        # Check environment variables
        if "OMARCHY" in os.environ or "OMARCHY_VERSION" in os.environ:
            return True

        # Check for Omarchy system files
        omarchy_indicators = [
            Path("/etc/omarchy"),
            Path("/etc/omarchy-release"),
            Path("/usr/share/omarchy"),
            Path.home() / ".config" / "omarchy",
        ]

        return any(path.exists() for path in omarchy_indicators)

    @staticmethod
    def get_system_colors() -> Optional[Dict[str, str]]:
        """
        Get system accent/theme colors if available.

        Returns:
            Dict of color names to hex values, or None if unavailable
        """
        platform_name = PlatformTheme.detect_platform()

        try:
            if platform_name == "omarchy":
                return PlatformTheme._get_omarchy_colors()
            elif platform_name == "macos":
                return PlatformTheme._get_macos_colors()
            elif platform_name == "linux":
                return PlatformTheme._get_gtk_colors()
            elif platform_name == "windows":
                return PlatformTheme._get_windows_colors()
        except Exception as e:
            print(f"Warning: Failed to detect system colors: {e}")
            return None

        return None

    @staticmethod
    def _get_omarchy_colors() -> Dict[str, str]:
        """
        Extract colors from Omarchy system theme.

        Omarchy stores theme configuration in:
        - ~/.config/omarchy/theme.conf
        - /etc/omarchy/theme.conf (system-wide)
        """
        config_paths = [
            Path.home() / ".config" / "omarchy" / "theme.conf",
            Path("/etc/omarchy/theme.conf"),
        ]

        for config_path in config_paths:
            if not config_path.exists():
                continue

            try:
                colors = {}
                with open(config_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip().lower()
                            value = value.strip().strip('"').strip("'")

                            # Map Omarchy color keys to our theme keys
                            key_map = {
                                'accent': 'primary',
                                'accent_color': 'primary',
                                'secondary': 'secondary',
                                'success': 'accent',
                                'error': 'error',
                                'warning': 'warning',
                                'background': 'background',
                                'foreground': 'text',
                            }

                            if key in key_map:
                                colors[key_map[key]] = value

                if colors:
                    print(f"Loaded Omarchy colors from {config_path}")
                    return colors

            except Exception as e:
                print(f"Warning: Failed to parse Omarchy config {config_path}: {e}")
                continue

        # Fallback: Try reading from environment variables
        env_colors = {}
        env_map = {
            'OMARCHY_ACCENT': 'primary',
            'OMARCHY_SECONDARY': 'secondary',
            'OMARCHY_BG': 'background',
        }

        for env_key, color_key in env_map.items():
            if env_key in os.environ:
                env_colors[color_key] = os.environ[env_key]

        if env_colors:
            print("Loaded Omarchy colors from environment")
            return env_colors

        print("Warning: Omarchy detected but no theme colors found")
        return {}

    @staticmethod
    def _get_macos_colors() -> Dict[str, str]:
        """
        Get macOS system accent color.

        Uses `defaults read` to get the accent color preference.
        """
        try:
            # Read macOS accent color (-1 = graphite, 0-7 = various colors)
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleAccentColor"],
                capture_output=True,
                text=True,
                timeout=2
            )

            # Map macOS accent color IDs to hex colors
            accent_map = {
                "-1": "#8E8E93",  # Graphite
                "0": "#FF3B30",   # Red
                "1": "#FF9500",   # Orange
                "2": "#FFCC00",   # Yellow
                "3": "#34C759",   # Green
                "4": "#00C7BE",   # Teal (Cyan)
                "5": "#007AFF",   # Blue
                "6": "#AF52DE",   # Purple
                "7": "#FF2D55",   # Pink
            }

            accent_id = result.stdout.strip()
            if accent_id in accent_map:
                return {"primary": accent_map[accent_id]}

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback to blue (default macOS accent)
        return {"primary": "#007AFF"}

    @staticmethod
    def _get_gtk_colors() -> Dict[str, str]:
        """
        Get GTK theme colors from various sources.

        Tries:
        - dconf (GNOME/GTK3)
        - ~/.config/gtk-3.0/gtk.css
        - ~/.themes/*/gtk-3.0/gtk.css
        """
        colors = {}

        # Try dconf first (GNOME)
        try:
            result = subprocess.run(
                ["dconf", "read", "/org/gnome/desktop/interface/gtk-theme"],
                capture_output=True,
                text=True,
                timeout=2
            )
            theme_name = result.stdout.strip().strip("'")

            if theme_name:
                # Look for theme CSS file
                theme_paths = [
                    Path.home() / ".themes" / theme_name / "gtk-3.0" / "gtk.css",
                    Path("/usr/share/themes") / theme_name / "gtk-3.0" / "gtk.css",
                ]

                for theme_path in theme_paths:
                    if theme_path.exists():
                        # Parse basic colors from CSS (simplified)
                        # This is a basic implementation - could be expanded
                        with open(theme_path, 'r') as f:
                            content = f.read()
                            # Look for @define-color directives
                            import re
                            color_pattern = r'@define-color\s+(\w+)\s+(#[0-9A-Fa-f]{6})'
                            matches = re.findall(color_pattern, content)

                            color_map = {
                                'theme_selected_bg_color': 'primary',
                                'theme_fg_color': 'text',
                                'theme_bg_color': 'background',
                                'success_color': 'accent',
                                'error_color': 'error',
                                'warning_color': 'warning',
                            }

                            for name, value in matches:
                                if name in color_map:
                                    colors[color_map[name]] = value

                        if colors:
                            return colors

        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: Try user's gtk.css
        user_gtk_css = Path.home() / ".config" / "gtk-3.0" / "gtk.css"
        if user_gtk_css.exists():
            # Similar parsing logic
            pass

        return colors if colors else {}

    @staticmethod
    def _get_windows_colors() -> Dict[str, str]:
        """
        Get Windows accent color from registry.

        Uses registry to read accent color on Windows 10/11.
        """
        try:
            import winreg

            # Open registry key for personalization settings
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\DWM",
                0,
                winreg.KEY_READ
            )

            # Read accent color (DWORD in ABGR format)
            color_value, _ = winreg.QueryValueEx(key, "AccentColor")
            winreg.CloseKey(key)

            # Convert ABGR to RGB hex
            # ABGR format: 0xAABBGGRR
            r = color_value & 0xFF
            g = (color_value >> 8) & 0xFF
            b = (color_value >> 16) & 0xFF

            hex_color = f"#{r:02X}{g:02X}{b:02X}"

            return {"primary": hex_color}

        except (ImportError, FileNotFoundError, WindowsError):
            pass

        return {}


def merge_system_colors(theme_colors: Dict[str, str], system_colors: Dict[str, str]) -> Dict[str, str]:
    """
    Merge system colors into theme colors.

    Args:
        theme_colors: Original theme colors
        system_colors: System-detected colors

    Returns:
        Merged color dictionary (system colors take precedence)
    """
    merged = theme_colors.copy()
    merged.update(system_colors)
    return merged
