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

        # Get actual widget width (fallback to 36 if too small)
        widget_width = max(self.size.width, 30)
        border_width = widget_width - 2  # Account for borders
        inner_width = border_width - 2  # Account for "║ " padding

        # Header with decorative borders
        result.append("╔" + "═" * border_width + "╗\n", style="bold yellow")

        # Title centered
        title = "SYSTEM STATUS DASHBOARD"
        title_padding = (border_width - len(title)) // 2
        result.append("║ " + " " * (title_padding - 1), style="bold yellow")
        result.append(title, style="bold yellow")
        remaining = border_width - title_padding - len(title) - 1
        result.append(" " * remaining + " ║\n", style="bold yellow")

        result.append("╠" + "═" * border_width + "╣\n", style="bold yellow")

        # === DEVICE INFO ===
        result.append("║ ", style="bold yellow")
        hardware_label = "▓▒░ HARDWARE ░▒▓"
        result.append(hardware_label, style="bold cyan")
        result.append(" " * (inner_width - len(hardware_label)))
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        device_line = f"  Device: {self.device_name}"
        result.append(f"  Device: ", style="dim white")
        result.append(f"{self.device_name}", style="bold green")
        padding = inner_width - len(device_line)
        result.append(" " * padding)
        result.append(" ║\n", style="bold yellow")

        # === STATE INFO ===
        result.append("║ ", style="bold yellow")
        result.append(" " * inner_width)
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        mode_label = "▓▒░ OPERATIONAL MODE ░▒▓"
        result.append(mode_label, style="bold magenta")
        result.append(" " * (inner_width - len(mode_label)))
        result.append(" ║\n", style="bold yellow")

        # State message
        state_msg = self.STATE_MESSAGES.get(self.state, "UNKNOWN STATE")
        state_color = self.STATE_COLORS.get(self.state, "white")
        result.append("║ ", style="bold yellow")
        state_line = f"  {state_msg}"
        result.append(state_line, style=f"bold {state_color}")
        padding = inner_width - len(state_line)
        result.append(" " * padding)
        result.append(" ║\n", style="bold yellow")

        # === SERVER STATUS ===
        result.append("║ ", style="bold yellow")
        result.append(" " * inner_width)
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        server_line = f"  Server: {self.server_status.upper()}"
        result.append("  Server: ", style="dim white")
        server_color = "green" if self.server_status == "connected" else "red"
        result.append(f"{self.server_status.upper()}", style=f"bold {server_color}")
        padding = inner_width - len(server_line)
        result.append(" " * padding)
        result.append(" ║\n", style="bold yellow")

        # === WAKE WORD INDICATOR ===
        if self.last_wake_word:
            result.append("║ ", style="bold yellow")
            result.append(" " * inner_width)
            result.append(" ║\n", style="bold yellow")

            result.append("║ ", style="bold yellow")
            wake_line = f"  Wake Word: '{self.last_wake_word}'"
            result.append("  Wake Word: ", style="dim white")
            result.append(f"'{self.last_wake_word}'", style="bold yellow")
            padding = inner_width - len(wake_line)
            result.append(" " * padding)
            result.append(" ║\n", style="bold yellow")

        # === SYSTEM METRICS ===
        result.append("║ ", style="bold yellow")
        result.append(" " * inner_width)
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        metrics_label = "▓▒░ SYSTEM METRICS ░▒▓"
        result.append(metrics_label, style="bold cyan")
        result.append(" " * (inner_width - len(metrics_label)))
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        uptime = self._get_uptime()
        uptime_line = f"  Uptime: {uptime}"
        result.append(f"  Uptime: ", style="dim white")
        result.append(f"{uptime}", style="bold green")
        padding = inner_width - len(uptime_line)
        result.append(" " * padding)
        result.append(" ║\n", style="bold yellow")

        # Neural link strength (simulated)
        result.append("║ ", style="bold yellow")
        link_percent = 0.95 if self.server_status == "connected" else 0.0
        link_bars = "█" * 8 if link_percent > 0.9 else "░" * 8
        link_pct = " 95%" if link_percent > 0.9 else "  0%"
        neural_line = f"  Neural Link: {link_bars}{link_pct}"
        result.append(f"  Neural Link: ", style="dim white")
        result.append(link_bars)
        result.append(link_pct, style="bold green" if link_percent > 0.9 else "dim red")
        padding = inner_width - len(neural_line)
        result.append(" " * padding)
        result.append(" ║\n", style="bold yellow")

        # === CONTROLS ===
        result.append("║ ", style="bold yellow")
        result.append(" " * inner_width)
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        controls_label = "▓▒░ CONTROLS ░▒▓"
        result.append(controls_label, style="bold magenta")
        result.append(" " * (inner_width - len(controls_label)))
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        space_control = "  [SPACE] Toggle Listening"
        result.append(space_control, style="dim cyan")
        result.append(" " * (inner_width - len(space_control)))
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        s_control = "  [S]     Settings"
        result.append(s_control, style="dim cyan")
        result.append(" " * (inner_width - len(s_control)))
        result.append(" ║\n", style="bold yellow")

        result.append("║ ", style="bold yellow")
        q_control = "  [Q]     Quit"
        result.append(q_control, style="dim cyan")
        result.append(" " * (inner_width - len(q_control)))
        result.append(" ║\n", style="bold yellow")

        # Footer
        result.append("╚" + "═" * border_width + "╝", style="bold yellow")

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
