"""Activity feed / event log widget - CYBERPUNK HACKER TERMINAL EDITION"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from datetime import datetime
from collections import deque
import re


class ActivityFeed(Static):
    """
    Scrolling activity log - HACKER TERMINAL STYLE.

    Features:
    - Color-coded message types (info, success, warning, error, system)
    - Timestamp with milliseconds
    - Line numbers
    - Terminal prompt style
    - Message type indicators
    """

    def __init__(self, max_messages: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.messages = deque(maxlen=max_messages)
        self._message_counter = 0

    def add_message(self, message: str, msg_type: str = "info"):
        """
        Add a message to the activity feed.

        Args:
            message: The message text
            msg_type: Type of message (info, success, warning, error, system)
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        self._message_counter += 1

        self.messages.append({
            "id": self._message_counter,
            "timestamp": timestamp,
            "message": message,
            "type": msg_type
        })
        self.refresh()

    def _detect_message_type(self, message: str) -> str:
        """Auto-detect message type from keywords"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["error", "failed", "fail", "critical"]):
            return "error"
        elif any(word in message_lower for word in ["warning", "warn", "caution"]):
            return "warning"
        elif any(word in message_lower for word in ["success", "complete", "loaded", "ready", "connected"]):
            return "success"
        elif any(word in message_lower for word in ["initializing", "loading", "starting", "booting"]):
            return "system"
        else:
            return "info"

    def _format_message(self, msg: dict) -> Text:
        """Format a single message with subtle grayscale shades"""
        result = Text()

        # Message type indicator - subtle shade variations
        type_indicators = {
            "info": ("▓", "#6b7a8a"),           # shade-4 (light)
            "success": ("✓", "#8899aa"),        # shade-5 (lightest)
            "warning": ("⚠", "#6b7a8a"),        # shade-4 (light)
            "error": ("✖", "#8899aa"),          # shade-5 (lightest)
            "system": ("◉", "#4d5966")          # shade-3 (medium)
        }

        indicator, color = type_indicators.get(msg["type"], ("▓", "#6b7a8a"))

        # Line number (4 digits, zero-padded)
        result.append(f"{msg['id']:04d} ", style="#363d47")  # shade-2 (dark)

        # Timestamp
        result.append(f"[{msg['timestamp']}] ", style="#4d5966")  # shade-3 (medium)

        # Type indicator
        result.append(f"{indicator} ", style=color)

        # Message text - subtle shade variations
        if msg["type"] == "error":
            text_style = "#8899aa"  # shade-5 (lightest)
        elif msg["type"] == "success":
            text_style = "#6b7a8a"  # shade-4 (light)
        elif msg["type"] == "system":
            text_style = "#4d5966"  # shade-3 (medium)
        else:
            text_style = "#6b7a8a"  # shade-4 (light)

        result.append(msg["message"], style=text_style)

        return result

    def render(self) -> Text:
        """Render activity feed - simple list without inner border"""
        result = Text()

        if not self.messages:
            result.append("▓▒░ AWAITING SYSTEM EVENTS ░▒▓\n", style="bold cyan")
            result.append("No activity logged...\n", style="dim white")
        else:
            # Show messages that fit in available height
            visible_messages = list(self.messages)

            for msg in visible_messages:
                # Format message
                msg_text = self._format_message(msg)
                result.append(msg_text)
                result.append("\n")

        return result


class CyberpunkActivityFeed(Static):
    """
    MAXIMUM CYBERPUNK activity feed.
    No borders, matrix-style scrolling log.
    """

    def __init__(self, max_messages: int = 200, **kwargs):
        super().__init__(**kwargs)
        self.messages = deque(maxlen=max_messages)
        self._message_counter = 0

    def add_message(self, message: str, msg_type: str = None):
        """Add a message with auto-detected type if not specified"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._message_counter += 1

        # Auto-detect type if not specified
        if msg_type is None:
            msg_type = self._detect_message_type(message)

        self.messages.append({
            "id": self._message_counter,
            "timestamp": timestamp,
            "message": message,
            "type": msg_type
        })
        self.refresh()

    def _detect_message_type(self, message: str) -> str:
        """Auto-detect message type from keywords"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["error", "failed", "fail", "critical", "crash"]):
            return "error"
        elif any(word in message_lower for word in ["warning", "warn", "caution"]):
            return "warning"
        elif any(word in message_lower for word in ["success", "complete", "loaded", "ready", "connected", "online"]):
            return "success"
        elif any(word in message_lower for word in ["initializing", "loading", "starting", "booting", "processing"]):
            return "system"
        else:
            return "info"

    def render(self) -> Text:
        """Render as pure scrolling terminal output"""
        result = Text()

        if not self.messages:
            result.append("▓▒░ TERMINAL LOG INITIALIZED ░▒▓\n", style="bold cyan")
            result.append("Awaiting system events...\n", style="dim cyan")
        else:
            # Show all messages that fit
            for msg in list(self.messages):
                # Type colors
                type_colors = {
                    "info": "cyan",
                    "success": "green",
                    "warning": "yellow",
                    "error": "red",
                    "system": "magenta"
                }
                color = type_colors.get(msg["type"], "white")

                # Type prefix
                type_prefix = {
                    "info": "[INFO]",
                    "success": "[OK]  ",
                    "warning": "[WARN]",
                    "error": "[ERR] ",
                    "system": "[SYS] "
                }
                prefix = type_prefix.get(msg["type"], "[LOG]")

                # Format line
                result.append(f"{msg['timestamp']} ", style="dim white")
                result.append(f"{prefix} ", style=f"bold {color}")
                result.append(f"{msg['message']}\n", style=color)

        return result
