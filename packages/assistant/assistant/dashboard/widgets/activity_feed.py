"""Activity feed / event log widget"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from datetime import datetime
from collections import deque


class ActivityFeed(Static):
    """Scrolling activity log"""

    def __init__(self, max_messages: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.messages = deque(maxlen=max_messages)

    def add_message(self, message: str):
        """Add a timestamped message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] {message}")
        self.refresh()

    def render(self) -> Text:
        """Render activity feed"""
        result = Text()

        result.append("Activity Log\n", style="bold underline")
        result.append("\n")

        if not self.messages:
            result.append("No activity yet...", style="dim")
        else:
            # Show most recent messages
            for msg in list(self.messages)[-20:]:  # Last 20 messages
                result.append(msg + "\n")

        return result
