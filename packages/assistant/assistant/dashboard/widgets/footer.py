"""Cyberpunk footer widget with system stats"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
import psutil
import platform


class CyberpunkFooter(Static):
    """
    Cyberpunk-styled footer with system statistics.

    Features:
    - CPU/Memory usage
    - Network status
    - System info
    - Dramatic cyberpunk styling
    """

    cpu_percent = reactive(0.0)
    mem_percent = reactive(0.0)
    network_status = reactive("online")

    def on_mount(self) -> None:
        """Initialize and start monitoring"""
        self.set_interval(2.0, self.update_stats)  # Update every 2 seconds

    def update_stats(self) -> None:
        """Update system statistics"""
        try:
            self.cpu_percent = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            self.mem_percent = mem.percent
        except Exception:
            # Fallback if psutil not available
            self.cpu_percent = 0.0
            self.mem_percent = 0.0

    def _get_bar(self, percent: float, width: int = 10) -> tuple[str, str]:
        """Create a progress bar"""
        filled = int((percent / 100) * width)
        bar = "█" * filled + "░" * (width - filled)

        # Color based on percentage
        if percent < 50:
            color = "green"
        elif percent < 75:
            color = "yellow"
        else:
            color = "red"

        return bar, color

    def render(self) -> Text:
        """Render cyberpunk footer"""
        result = Text()

        result.append("═" * 79 + "\n", style="bold green")

        # Left section: System stats
        result.append("▓▒░ ", style="bold cyan")

        # CPU
        cpu_bar, cpu_color = self._get_bar(self.cpu_percent, 8)
        result.append("CPU:", style="dim white")
        result.append(f"[{cpu_bar}]", style=f"bold {cpu_color}")
        result.append(f"{self.cpu_percent:5.1f}%", style=f"bold {cpu_color}")

        result.append(" │ ", style="dim white")

        # Memory
        mem_bar, mem_color = self._get_bar(self.mem_percent, 8)
        result.append("MEM:", style="dim white")
        result.append(f"[{mem_bar}]", style=f"bold {mem_color}")
        result.append(f"{self.mem_percent:5.1f}%", style=f"bold {mem_color}")

        result.append(" │ ", style="dim white")

        # Network status
        result.append("NET:", style="dim white")
        net_color = "green" if self.network_status == "online" else "red"
        result.append(f"{self.network_status.upper()}", style=f"bold {net_color}")

        # Right section: System info
        result.append(" " * 10)
        result.append("░▒▓ ", style="bold cyan")

        # Platform
        os_name = platform.system()
        result.append(f"{os_name}", style="bold magenta")

        result.append(" ░▒▓", style="bold cyan")

        return result


class CompactCyberpunkFooter(Static):
    """
    Ultra-compact footer for small terminals.
    Single line with essential info.
    """

    state = reactive("ready")

    def render(self) -> Text:
        """Render minimal footer"""
        result = Text()

        result.append("▓▒░ ", style="bold cyan")
        result.append("XSWARM v2.0", style="bold yellow")
        result.append(" ░▒▓ ", style="bold cyan")

        # State indicator
        state_colors = {
            "ready": "green",
            "idle": "cyan",
            "listening": "yellow",
            "speaking": "magenta",
            "error": "red"
        }
        color = state_colors.get(self.state, "white")
        result.append(f"[{self.state.upper()}]", style=f"bold {color}")

        result.append(" ░▒▓", style="bold cyan")

        return result
