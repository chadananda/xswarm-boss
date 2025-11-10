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
        "initializing": "blue",
        "idle": "cyan",
        "ready": "green",
        "listening": "yellow",
        "speaking": "magenta",
        "thinking": "purple",
        "error": "red"
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
        """Render status information with MAXIMUM PERSONALITY"""
        result = Text()

        # Header with decorative borders
        result.append("╔════════════════════════════════════╗\n", style="bold yellow")
        result.append("║ ", style="bold yellow")
        result.append("   SYSTEM STATUS DASHBOARD    ", style="bold yellow")
        result.append("  ║\n", style="bold yellow")
        result.append("╠════════════════════════════════════╣\n", style="bold yellow")

        # === DEVICE INFO ===
        result.append("║ ", style="bold yellow")
        result.append("▓▒░ HARDWARE ░▒▓", style="bold cyan")
        result.append(" " * 15)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append(f"  Device: ", style="dim white")
        result.append(f"{self.device_name}", style="bold green")
        # Padding to 38 chars (36 content + 2 border)
        padding = 38 - 11 - len(self.device_name)
        result.append(" " * padding)
        result.append("║\n", style="bold yellow")

        # === STATE INFO ===
        result.append("║ ", style="bold yellow")
        result.append(" " * 36)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("▓▒░ OPERATIONAL MODE ░▒▓", style="bold magenta")
        result.append(" " * 12)
        result.append("║\n", style="bold yellow")

        # State message
        state_msg = self.STATE_MESSAGES.get(self.state, "UNKNOWN STATE")
        state_color = self.STATE_COLORS.get(self.state, "white")
        result.append("║ ", style="bold yellow")
        result.append(f"  {state_msg}", style=f"bold {state_color}")
        padding = 38 - 2 - len(state_msg)
        result.append(" " * padding)
        result.append("║\n", style="bold yellow")

        # === SERVER STATUS ===
        result.append("║ ", style="bold yellow")
        result.append(" " * 36)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("  Server: ", style="dim white")
        server_color = "green" if self.server_status == "connected" else "red"
        result.append(f"{self.server_status.upper()}", style=f"bold {server_color}")
        padding = 38 - 11 - len(self.server_status)
        result.append(" " * padding)
        result.append("║\n", style="bold yellow")

        # === WAKE WORD INDICATOR ===
        if self.last_wake_word:
            result.append("║ ", style="bold yellow")
            result.append(" " * 36)
            result.append("║\n", style="bold yellow")

            result.append("║ ", style="bold yellow")
            result.append("  Wake Word: ", style="dim white")
            result.append(f"'{self.last_wake_word}'", style="bold yellow")
            padding = 38 - 14 - len(self.last_wake_word) - 2  # 2 for quotes
            result.append(" " * padding)
            result.append("║\n", style="bold yellow")

        # === SYSTEM METRICS ===
        result.append("║ ", style="bold yellow")
        result.append(" " * 36)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("▓▒░ SYSTEM METRICS ░▒▓", style="bold cyan")
        result.append(" " * 14)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append(f"  Uptime: ", style="dim white")
        uptime = self._get_uptime()
        result.append(f"{uptime}", style="bold green")
        padding = 38 - 11 - len(uptime)
        result.append(" " * padding)
        result.append("║\n", style="bold yellow")

        # Neural link strength (simulated)
        result.append("║ ", style="bold yellow")
        result.append(f"  Neural Link: ", style="dim white")
        link_percent = 0.95 if self.server_status == "connected" else 0.0
        result.append("█" * 8 if link_percent > 0.9 else "░" * 8)
        result.append(" 95%", style="bold green" if link_percent > 0.9 else "dim red")
        result.append(" " * 8)
        result.append("║\n", style="bold yellow")

        # === CONTROLS ===
        result.append("║ ", style="bold yellow")
        result.append(" " * 36)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("▓▒░ CONTROLS ░▒▓", style="bold magenta")
        result.append(" " * 19)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("  [SPACE] Toggle Listening", style="dim cyan")
        result.append(" " * 11)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("  [S]     Settings", style="dim cyan")
        result.append(" " * 18)
        result.append("║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        result.append("  [Q]     Quit", style="dim cyan")
        result.append(" " * 22)
        result.append("║\n", style="bold yellow")

        # Footer
        result.append("╚════════════════════════════════════╝", style="bold yellow")

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
        state_color = StatusWidget.STATE_COLORS.get(self.state, "white")
        result.append("◉", style=f"bold {state_color}")
        result.append(f" {self.state.upper()} ", style=f"bold {state_color}")

        # Server status
        server_color = "green" if self.server_status == "connected" else "red"
        result.append("│ ", style="dim white")
        result.append("SERVER:", style="dim white")
        result.append(f"{self.server_status.upper()} ", style=f"bold {server_color}")

        # Wake word
        if self.last_wake_word:
            result.append("│ ", style="dim white")
            result.append(f"WAKE:'{self.last_wake_word}' ", style="bold yellow")

        return result
