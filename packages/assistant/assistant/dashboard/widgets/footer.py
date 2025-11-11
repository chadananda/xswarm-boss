"""Cyberpunk footer widget with GPU, projects, workers, and subscription status"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text


class CyberpunkFooter(Static):
    """
    Cyberpunk-styled footer with project and system status.

    Features:
    - GPU status (sufficient/insufficient)
    - Number of projects
    - Project progress with color coding
    - Worker status
    - Subscription tier
    """

    # Mock data (will be replaced with real data later)
    gpu_sufficient = reactive(True)
    total_projects = reactive(3)
    projects_progress = reactive({"Alpha": 45, "Beta": 78, "Gamma": 12})
    workers_online = reactive(2)
    workers_total = reactive(3)
    subscription_plan = reactive("Pro")

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    def on_mount(self) -> None:
        """Initialize and start monitoring"""
        self.set_interval(2.0, self.update_stats)  # Update every 2 seconds

    def update_stats(self) -> None:
        """Update status (mock data for now)"""
        # TODO: Replace with real data sources
        pass

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback
    # Get progress color based on percentage
    def _get_progress_color(self, percent: float) -> str:
        """Get color for project progress percentage"""
        if percent < 30:
            return "red"
        elif percent < 70:
            return "yellow"
        else:
            return "green"

    def render(self) -> Text:
        """Render footer with GPU, projects, workers, and subscription status"""
        result = Text()
        widget_width = self.size.width
        shade_3 = self._get_theme_color("shade_3", "#4d5966")
        shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
        # Top separator line
        result.append("═" * widget_width + "\n", style=shade_4)
        result.append("▓▒░ ", style=shade_4)
        # 1. GPU Status
        result.append("GPU: ", style=shade_3)
        if self.gpu_sufficient:
            result.append("✓", style="green")
        else:
            result.append("✗", style="red")
        result.append(" │ ", style=shade_3)
        # 2. Number of Projects
        result.append(f"Projects: {self.total_projects}", style=shade_4)
        result.append(" │ ", style=shade_3)
        # 3. Project Progress (each with color coding)
        project_parts = []
        for name, progress in self.projects_progress.items():
            color = self._get_progress_color(progress)
            project_parts.append(f"[{color}]{name}: {progress}%[/{color}]")
        result.append_text(Text.from_markup(" ".join(project_parts)))
        result.append(" │ ", style=shade_3)
        # 4. Number of Workers
        result.append("Workers: ", style=shade_3)
        worker_color = "green" if self.workers_online > 0 else "red"
        result.append(f"{self.workers_online}/{self.workers_total}", style=worker_color)
        result.append(" │ ", style=shade_3)
        # 5. Subscription Mode
        result.append("Plan: ", style=shade_3)
        plan_color = "cyan" if self.subscription_plan == "Pro" else "dim"
        result.append(self.subscription_plan, style=plan_color)
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
