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

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

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

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback

    def _get_bar(self, percent: float, width: int = 10) -> tuple[str, str]:
        """Create a progress bar with subtle shade variations"""
        filled = int((percent / 100) * width)
        bar = "█" * filled + "░" * (width - filled)

        # Color based on percentage - use theme colors with fallbacks
        if percent < 50:
            color = self._get_theme_color("shade_3", "#4d5966")  # shade-3 (medium)
        elif percent < 75:
            color = self._get_theme_color("shade_4", "#6b7a8a")  # shade-4 (light)
        else:
            color = self._get_theme_color("shade_5", "#8899aa")  # shade-5 (lightest)

        return bar, color

    def render(self) -> Text:
        """Render responsive cyberpunk footer"""
        result = Text()

        widget_width = self.size.width

        # RESPONSIVE: Adapt to terminal size
        # Tiny (< 40 cols): Minimal - just separator
        if widget_width < 40:
            shade_3 = self._get_theme_color("shade_3", "#4d5966")
            result.append("═" * widget_width, style=shade_3)
            return result

        # Small (40-60 cols): Show only CPU/MEM percentages
        elif widget_width < 60:
            shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
            result.append("═" * widget_width + "\n", style=shade_4)
            result.append("▓▒░ ", style=shade_4)

            # CPU (no bar, just percentage)
            _, cpu_color = self._get_bar(self.cpu_percent, 8)
            result.append(f"CPU:{self.cpu_percent:.0f}%", style=cpu_color)
            result.append(" ", style="")

            # Memory (no bar, just percentage)
            _, mem_color = self._get_bar(self.mem_percent, 8)
            result.append(f"MEM:{self.mem_percent:.0f}%", style=mem_color)

            result.append(" ░▒▓", style=shade_4)
            return result

        # Medium (60-80 cols): Show bars but compact
        elif widget_width < 80:
            shade_3 = self._get_theme_color("shade_3", "#4d5966")
            shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
            result.append("═" * widget_width + "\n", style=shade_4)
            result.append("▓▒░ ", style=shade_4)

            # CPU with smaller bar
            cpu_bar, cpu_color = self._get_bar(self.cpu_percent, 5)
            result.append("CPU:", style=shade_3)
            result.append(f"[{cpu_bar}]", style=cpu_color)
            result.append(f"{self.cpu_percent:4.0f}%", style=cpu_color)

            result.append(" ", style="")

            # Memory with smaller bar
            mem_bar, mem_color = self._get_bar(self.mem_percent, 5)
            result.append("MEM:", style=shade_3)
            result.append(f"[{mem_bar}]", style=mem_color)
            result.append(f"{self.mem_percent:4.0f}%", style=mem_color)

            result.append(" ░▒▓", style=shade_4)
            return result

        # Large (80+ cols): Full stats with bars and network
        else:
            shade_2 = self._get_theme_color("shade_2", "#363d47")
            shade_3 = self._get_theme_color("shade_3", "#4d5966")
            shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
            result.append("═" * widget_width + "\n", style=shade_4)

            # First line: System stats
            result.append("▓▒░ ", style=shade_4)

            # CPU
            cpu_bar, cpu_color = self._get_bar(self.cpu_percent, 8)
            result.append("CPU:", style=shade_3)
            result.append(f"[{cpu_bar}]", style=cpu_color)
            result.append(f"{self.cpu_percent:5.1f}%", style=cpu_color)

            result.append(" │ ", style=shade_3)

            # Memory
            mem_bar, mem_color = self._get_bar(self.mem_percent, 8)
            result.append("MEM:", style=shade_3)
            result.append(f"[{mem_bar}]", style=mem_color)
            result.append(f"{self.mem_percent:5.1f}%", style=mem_color)

            result.append(" │ ", style=shade_3)

            # Network status
            result.append("NET:", style=shade_3)
            net_color = shade_4 if self.network_status == "online" else shade_2
            result.append(f"{self.network_status.upper()}", style=net_color)

            # Keyboard shortcuts (right side)
            result.append(" " * 5)
            result.append("│ ", style=shade_3)
            result.append("SPACE:", style=shade_3)
            result.append("Listen", style=shade_4)
            result.append(" ", style="")
            result.append("Ctrl+C:", style=shade_3)
            result.append("Copy", style=shade_4)
            result.append(" ", style="")
            result.append("Ctrl+V:", style=shade_3)
            result.append("Paste", style=shade_4)
            result.append(" ", style="")
            result.append("Q:", style=shade_3)
            result.append("Quit", style=shade_4)

            result.append(" ░▒▓", style=shade_4)

            return result


class CompactCyberpunkFooter(Static):
    """
    Ultra-compact footer for small terminals.
    Single line with essential info.
    """

    state = reactive("ready")

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback

    def render(self) -> Text:
        """Render minimal footer"""
        result = Text()

        shade_3 = self._get_theme_color("shade_3", "#4d5966")
        shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
        shade_5 = self._get_theme_color("shade_5", "#8899aa")

        result.append("▓▒░ ", style=shade_4)
        result.append("XSWARM v2.0", style=shade_5)
        result.append(" ░▒▓ ", style=shade_4)

        # State indicator - use theme colors with subtle shade variations
        state_colors = {
            "ready": shade_4,
            "idle": shade_3,
            "listening": shade_5,
            "speaking": shade_5,
            "error": shade_5
        }
        color = state_colors.get(self.state, shade_4)
        result.append(f"[{self.state.upper()}]", style=color)

        result.append(" ░▒▓", style=shade_4)

        return result
