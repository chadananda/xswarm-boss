"""Status information widget - CYBERPUNK EDITION with OVERABUNDANT PERSONALITY"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
import time


class StatusWidget(Static):
    """
    Display connection status and current state with DRAMATIC cyberpunk flair.

    Features:
    - Animated progress bars
    - Dramatic state messages
    - System statistics
    - Wake word indicator
    - ASCII art decorations
    """

    device_name = reactive("Unknown")
    state = reactive("initializing")
    server_status = reactive("disconnected")
    last_wake_word = reactive(None)  # Track last detected wake word

    # Uptime tracking
    _start_time = None

    # Dramatic state messages
    STATE_MESSAGES = {
        "initializing": "⚡ INITIALIZING NEURAL NETWORKS",
        "idle": "◉ STANDING BY - AWAITING COMMAND",
        "ready": "◉ SYSTEMS ONLINE - READY TO ENGAGE",
        "listening": "👂 LISTENING - AUDIO INPUT ACTIVE",
        "speaking": "🗣 SPEAKING - OUTPUT STREAM ACTIVE",
        "thinking": "🧠 PROCESSING - NEURAL COMPUTATION",
        "error": "✖ CRITICAL ERROR - SYSTEM FAULT"
    }

    STATE_COLORS = {
        "initializing": "#4d5966",  # shade-3 (medium)
        "idle": "#363d47",          # shade-2 (dark)
        "ready": "#6b7a8a",         # shade-4 (light)
        "listening": "#8899aa",     # shade-5 (lightest)
        "speaking": "#8899aa",      # shade-5 (lightest)
        "thinking": "#6b7a8a",      # shade-4 (light)
        "error": "#8899aa"          # shade-5 (lightest)
    }

    def on_mount(self) -> None:
        """Initialize status tracking"""
        self._start_time = time.time()
        self.set_interval(1.0, self.refresh)  # Refresh every second for uptime

    def _get_uptime(self) -> str:
        """Calculate system uptime"""
        if not self._start_time:
            return "00:00:00"

        elapsed = int(time.time() - self._start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _draw_progress_bar(self, label: str, percent: float, width: int = 20) -> Text:
        """Draw a dramatic progress bar"""
        result = Text()
        result.append(f"{label}: ", style="dim white")

        # Bar characters
        filled = int(percent * width)
        bar = "█" * filled + "░" * (width - filled)

        # Color based on percentage
        if percent < 0.3:
            color = "red"
        elif percent < 0.7:
            color = "yellow"
        else:
            color = "green"

        result.append(f"[{bar}]", style=f"bold {color}")
        result.append(f" {int(percent * 100)}%", style=f"bold {color}")
        return result

    def render(self) -> Text:
        """Render compact status - single line"""
        result = Text()

        # State indicator
        state_msg = self.STATE_MESSAGES.get(self.state, "UNKNOWN")
        state_color = self.STATE_COLORS.get(self.state, "#6b7a8a")
        result.append(f"{state_msg}", style=state_color)

        # Device
        result.append("  │  ", style="#4d5966")  # shade-3
        result.append("Device: ", style="#4d5966")  # shade-3
        result.append(f"{self.device_name}", style="#6b7a8a")  # shade-4

        # Server status
        result.append("  │  ", style="#4d5966")  # shade-3
        result.append("Server: ", style="#4d5966")  # shade-3
        server_color = "#6b7a8a" if self.server_status == "connected" else "#363d47"  # shade-4 or shade-2
        result.append(f"{self.server_status.upper()}", style=server_color)

        # Uptime
        uptime = self._get_uptime()
        result.append("  │  ", style="#4d5966")  # shade-3
        result.append("Uptime: ", style="#4d5966")  # shade-3
        result.append(f"{uptime}", style="#6b7a8a")  # shade-4

        return result


class CompactStatusWidget(Static):
    """
    Compact status widget for smaller terminals.
    One-line status display.
    """

    device_name = reactive("Unknown")
    state = reactive("idle")
    server_status = reactive("disconnected")
    last_wake_word = reactive(None)

    def render(self) -> Text:
        """Render compact status"""
        result = Text()

        # State indicator
        state_color = StatusWidget.STATE_COLORS.get(self.state, "#6b7a8a")
        result.append("◉", style=state_color)
        result.append(f" {self.state.upper()} ", style=state_color)

        # Server status
        server_color = "#6b7a8a" if self.server_status == "connected" else "#363d47"  # shade-4 or shade-2
        result.append("│ ", style="#4d5966")  # shade-3
        result.append("SERVER:", style="#4d5966")  # shade-3
        result.append(f"{self.server_status.upper()} ", style=server_color)

        # Wake word
        if self.last_wake_word:
            result.append("│ ", style="#4d5966")  # shade-3
            result.append(f"WAKE:'{self.last_wake_word}' ", style="#8899aa")  # shade-5

        return result
