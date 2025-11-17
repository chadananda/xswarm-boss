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

        Returns:
            int: The message ID (for tracking/updating later)
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
        return self._message_counter

    def update_last_message(self, message: str, msg_type: str = None):
        """Update the last message instead of adding a new one (useful for progress updates)"""
        if not self.messages:
            # No messages yet, add one
            self.add_message(message, msg_type)
            return

        # Auto-detect type if not specified
        if msg_type is None:
            msg_type = self._detect_message_type(message)

        # Update last message in place
        self.messages[-1] = {
            "id": self.messages[-1]["id"],  # Keep same ID
            "timestamp": self.messages[-1]["timestamp"],  # Keep original timestamp
            "message": message,
            "type": msg_type
        }
        self.refresh()

    def update_message_by_id(self, message_id: int, message: str, msg_type: str = None):
        """Update a specific message by its ID (useful for tracking specific progress messages)"""
        # Find message with this ID
        for i, msg in enumerate(self.messages):
            if msg["id"] == message_id:
                # Auto-detect type if not specified
                if msg_type is None:
                    msg_type = self._detect_message_type(message)

                # Update message in place
                self.messages[i] = {
                    "id": msg["id"],  # Keep same ID
                    "timestamp": msg["timestamp"],  # Keep original timestamp
                    "message": message,
                    "type": msg_type
                }
                self.refresh()
                return True

        # Message ID not found - add as new message
        self.add_message(message, msg_type)
        return False

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

        # Use dynamic theme colors if available, otherwise fallback to defaults
        theme = getattr(self, 'theme_colors', None)
        if theme:
            shade_2 = theme["shade_2"]
            shade_3 = theme["shade_3"]
            shade_4 = theme["shade_4"]
            shade_5 = theme["shade_5"]
        else:
            # Fallback to default grayscale
            shade_2 = "#363d47"
            shade_3 = "#4d5966"
            shade_4 = "#6b7a8a"
            shade_5 = "#8899aa"

        # Message type indicator - subtle shade variations
        type_indicators = {
            "info": ("▓", shade_4),           # shade-4 (light)
            "success": ("✓", shade_5),        # shade-5 (lightest)
            "warning": ("⚠", shade_4),        # shade-4 (light)
            "error": ("✖", "#800000"),        # dark red/maroon for errors
            "system": ("◉", shade_3)          # shade-3 (medium)
        }

        indicator, color = type_indicators.get(msg["type"], ("▓", shade_4))

        # Line number (4 digits, zero-padded)
        result.append(f"{msg['id']:04d} ", style=shade_2)  # shade-2 (dark)

        # Timestamp
        result.append(f"[{msg['timestamp']}] ", style=shade_3)  # shade-3 (medium)

        # Type indicator
        result.append(f"{indicator} ", style=color)

        # Message text - subtle shade variations with dark red/maroon for errors
        if msg["type"] == "error":
            text_style = "#800000"  # dark red/maroon for error messages
        elif msg["type"] == "success":
            text_style = shade_4  # shade-4 (light)
        elif msg["type"] == "system":
            text_style = shade_3  # shade-3 (medium)
        else:
            text_style = shade_4  # shade-4 (light)

        result.append(msg["message"], style=text_style)

        return result

    def render(self) -> Text:
        """Render activity feed - simple list without inner border"""
        result = Text()

        if not self.messages:
            # Use theme colors if available
            theme = getattr(self, 'theme_colors', None)
            if theme:
                shade_4 = theme["shade_4"]
                shade_2 = theme["shade_2"]
            else:
                shade_4 = "#6b7a8a"
                shade_2 = "#363d47"
            result.append("▓▒░ AWAITING SYSTEM EVENTS ░▒▓\n", style=f"bold {shade_4}")
            result.append("No activity logged...\n", style=shade_2)
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

    def update_last_message(self, message: str, msg_type: str = None):
        """Update the last message instead of adding a new one (useful for progress updates)"""
        if not self.messages:
            # No messages yet, add one
            self.add_message(message, msg_type)
            return

        # Auto-detect type if not specified
        if msg_type is None:
            msg_type = self._detect_message_type(message)

        # Update last message in place
        self.messages[-1] = {
            "id": self.messages[-1]["id"],  # Keep same ID
            "timestamp": self.messages[-1]["timestamp"],  # Keep original timestamp
            "message": message,
            "type": msg_type
        }
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
