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
        """Create a progress bar with subtle shade variations"""
        filled = int((percent / 100) * width)
        bar = "█" * filled + "░" * (width - filled)

        # Color based on percentage - subtle shades
        if percent < 50:
            color = "#4d5966"  # shade-3 (medium)
        elif percent < 75:
            color = "#6b7a8a"  # shade-4 (light)
        else:
            color = "#8899aa"  # shade-5 (lightest)

        return bar, color

    def render(self) -> Text:
        """Render responsive cyberpunk footer"""
        result = Text()

        widget_width = self.size.width

        # RESPONSIVE: Adapt to terminal size
        # Tiny (< 40 cols): Minimal - just separator
        if widget_width < 40:
            result.append("═" * widget_width, style="#4d5966")  # shade-3
            return result

        # Small (40-60 cols): Show only CPU/MEM percentages
        elif widget_width < 60:
            result.append("═" * widget_width + "\n", style="#6b7a8a")  # shade-4
            result.append("▓▒░ ", style="#6b7a8a")  # shade-4

            # CPU (no bar, just percentage)
            _, cpu_color = self._get_bar(self.cpu_percent, 8)
            result.append(f"CPU:{self.cpu_percent:.0f}%", style=cpu_color)
            result.append(" ", style="")

            # Memory (no bar, just percentage)
            _, mem_color = self._get_bar(self.mem_percent, 8)
            result.append(f"MEM:{self.mem_percent:.0f}%", style=mem_color)

            result.append(" ░▒▓", style="#6b7a8a")  # shade-4
            return result

        # Medium (60-80 cols): Show bars but compact
        elif widget_width < 80:
            result.append("═" * widget_width + "\n", style="#6b7a8a")  # shade-4
            result.append("▓▒░ ", style="#6b7a8a")  # shade-4

            # CPU with smaller bar
            cpu_bar, cpu_color = self._get_bar(self.cpu_percent, 5)
            result.append("CPU:", style="#4d5966")  # shade-3
            result.append(f"[{cpu_bar}]", style=cpu_color)
            result.append(f"{self.cpu_percent:4.0f}%", style=cpu_color)

            result.append(" ", style="")

            # Memory with smaller bar
            mem_bar, mem_color = self._get_bar(self.mem_percent, 5)
            result.append("MEM:", style="#4d5966")  # shade-3
            result.append(f"[{mem_bar}]", style=mem_color)
            result.append(f"{self.mem_percent:4.0f}%", style=mem_color)

            result.append(" ░▒▓", style="#6b7a8a")  # shade-4
            return result

        # Large (80+ cols): Full stats with bars and network
        else:
            result.append("═" * widget_width + "\n", style="#6b7a8a")  # shade-4

            # First line: System stats
            result.append("▓▒░ ", style="#6b7a8a")  # shade-4

            # CPU
            cpu_bar, cpu_color = self._get_bar(self.cpu_percent, 8)
            result.append("CPU:", style="#4d5966")  # shade-3
            result.append(f"[{cpu_bar}]", style=cpu_color)
            result.append(f"{self.cpu_percent:5.1f}%", style=cpu_color)

            result.append(" │ ", style="#4d5966")  # shade-3

            # Memory
            mem_bar, mem_color = self._get_bar(self.mem_percent, 8)
            result.append("MEM:", style="#4d5966")  # shade-3
            result.append(f"[{mem_bar}]", style=mem_color)
            result.append(f"{self.mem_percent:5.1f}%", style=mem_color)

            result.append(" │ ", style="#4d5966")  # shade-3

            # Network status
            result.append("NET:", style="#4d5966")  # shade-3
            net_color = "#6b7a8a" if self.network_status == "online" else "#363d47"  # shade-4 or shade-2
            result.append(f"{self.network_status.upper()}", style=net_color)

            # Keyboard shortcuts (right side)
            result.append(" " * 5)
            result.append("│ ", style="#4d5966")  # shade-3
            result.append("SPACE:", style="#4d5966")  # shade-3
            result.append("Listen", style="#6b7a8a")  # shade-4
            result.append(" ", style="")
            result.append("Ctrl+C:", style="#4d5966")  # shade-3
            result.append("Copy", style="#6b7a8a")  # shade-4
            result.append(" ", style="")
            result.append("Ctrl+V:", style="#4d5966")  # shade-3
            result.append("Paste", style="#6b7a8a")  # shade-4
            result.append(" ", style="")
            result.append("Q:", style="#4d5966")  # shade-3
            result.append("Quit", style="#6b7a8a")  # shade-4

            result.append(" ░▒▓", style="#6b7a8a")  # shade-4

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

        result.append("▓▒░ ", style="#6b7a8a")  # shade-4
        result.append("XSWARM v2.0", style="#8899aa")  # shade-5
        result.append(" ░▒▓ ", style="#6b7a8a")  # shade-4

        # State indicator - subtle shade variations
        state_colors = {
            "ready": "#6b7a8a",    # shade-4
            "idle": "#4d5966",     # shade-3
            "listening": "#8899aa", # shade-5
            "speaking": "#8899aa",  # shade-5
            "error": "#8899aa"      # shade-5
        }
        color = state_colors.get(self.state, "#6b7a8a")
        result.append(f"[{self.state.upper()}]", style=color)

        result.append(" ░▒▓", style="#6b7a8a")  # shade-4

        return result
