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
        """Format a single message with cyberpunk styling"""
        result = Text()

        # Message type indicator
        type_indicators = {
            "info": ("▓▒░", "cyan"),
            "success": ("✓✓✓", "green"),
            "warning": ("⚠⚠⚠", "yellow"),
            "error": ("✖✖✖", "red"),
            "system": ("◉◉◉", "magenta")
        }

        indicator, color = type_indicators.get(msg["type"], ("▓▒░", "cyan"))

        # Line number (4 digits, zero-padded)
        result.append(f"{msg['id']:04d} ", style="dim white")

        # Timestamp
        result.append(f"[{msg['timestamp']}] ", style="dim cyan")

        # Type indicator
        result.append(f"{indicator} ", style=f"bold {color}")

        # Message text
        result.append(msg["message"], style=color)

        return result

    def render(self) -> Text:
        """Render HACKER TERMINAL activity feed"""
        result = Text()

        # Header with dramatic styling
        result.append("╔════════════════════════════════════════╗\n", style="bold magenta")
        result.append("║ ", style="bold magenta")
        result.append("   SYSTEM ACTIVITY LOG - LIVE FEED  ", style="bold magenta")
        result.append("   ║\n", style="bold magenta")
        result.append("╠════════════════════════════════════════╣\n", style="bold magenta")

        if not self.messages:
            result.append("║ ", style="bold magenta")
            result.append("  ▓▒░ AWAITING SYSTEM EVENTS ░▒▓      ", style="dim cyan")
            result.append("  ║\n", style="bold magenta")
            result.append("║ ", style="bold magenta")
            result.append("  No activity logged...               ", style="dim white")
            result.append("  ║\n", style="bold magenta")
        else:
            # Calculate how many messages we can show
            # Each message takes 1 line minimum
            visible_height = self.size.height - 4  # Subtract header/footer
            visible_messages = list(self.messages)[-visible_height:] if visible_height > 0 else []

            for msg in visible_messages:
                # Format message
                msg_text = self._format_message(msg)

                # Wrap long messages to fit in panel
                msg_str = msg_text.plain
                panel_width = 40  # Inside panel width

                # If message is too long, truncate
                if len(msg_str) > panel_width - 2:
                    # Truncate and add ellipsis
                    msg_text = self._format_message(msg)
                    result.append("║ ", style="bold magenta")
                    result.append(msg_text.plain[:panel_width - 5], style=msg_text.style)
                    result.append("...", style="dim white")
                    result.append(" ║\n", style="bold magenta")
                else:
                    result.append("║ ", style="bold magenta")
                    result.append(msg_text)
                    # Pad to panel width
                    padding = panel_width - len(msg_str) - 2
                    result.append(" " * padding)
                    result.append(" ║\n", style="bold magenta")

        result.append("╚════════════════════════════════════════╝", style="bold magenta")

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
