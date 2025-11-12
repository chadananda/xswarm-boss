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
    projects_progress = reactive([
        ("Authentication", 78),
        ("Marketing", 45),
        ("Product", 12)
    ])
    workers_online = reactive(2)
    workers_total = reactive(3)
    subscription_plan = reactive("Pro")
    # System monitoring stats
    cpu_percent = reactive(67)
    ram_used = reactive(28)
    ram_total = reactive(64)
    gpu_percent = reactive(82)
    network_up = reactive(245)  # KB/s
    network_down = reactive(1200)  # KB/s
    system_load = reactive(2.4)

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    def on_mount(self) -> None:
        """Initialize and start monitoring"""
        self.set_interval(2.0, self.update_stats)  # Update every 2 seconds

    def update_stats(self) -> None:
        """Update status with realistic fluctuations (mock data for now)"""
        import random
        # Simulate realistic system stat fluctuations
        # CPU: varies between 45-85%
        self.cpu_percent = min(95, max(35, self.cpu_percent + random.randint(-8, 8)))
        # RAM: slowly increases/decreases
        self.ram_used = min(self.ram_total - 2, max(16, self.ram_used + random.uniform(-0.5, 0.5)))
        # GPU: varies based on workload
        self.gpu_percent = min(98, max(60, self.gpu_percent + random.randint(-10, 10)))
        # Network: fluctuates significantly
        self.network_up = max(50, self.network_up + random.randint(-100, 150))
        self.network_down = max(100, self.network_down + random.randint(-300, 500))
        # System load: gradual changes
        self.system_load = max(0.5, min(6.0, self.system_load + random.uniform(-0.3, 0.3)))

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
        """Render footer with system stats, GPU, projects, workers, and subscription status"""
        result = Text()
        widget_width = self.size.width
        primary = self._get_theme_color("primary", "cyan")
        shade_3 = self._get_theme_color("shade_3", "#4d5966")
        shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
        # Top separator line
        result.append("═" * widget_width + "\n", style=shade_4)
        result.append("▓▒░ ", style=f"bold {primary}")
        # 1. System Monitoring Stats
        # CPU
        result.append("CPU:", style=shade_4)
        cpu_color = "red" if self.cpu_percent > 80 else "yellow" if self.cpu_percent > 60 else "green"
        result.append(f"{self.cpu_percent}%", style=f"bold {cpu_color}")
        result.append(" │ ", style=shade_3)
        # RAM
        result.append("RAM:", style=shade_4)
        ram_percent = (self.ram_used / self.ram_total) * 100
        ram_color = "red" if ram_percent > 80 else "yellow" if ram_percent > 60 else "green"
        result.append(f"{self.ram_used}/{self.ram_total}GB", style=f"bold {ram_color}")
        result.append(" │ ", style=shade_3)
        # GPU
        result.append("GPU:", style=shade_4)
        gpu_color = "red" if self.gpu_percent > 90 else "yellow" if self.gpu_percent > 70 else "green"
        result.append(f"{self.gpu_percent}%", style=f"bold {gpu_color}")
        result.append(" │ ", style=shade_3)
        # Network
        result.append("NET:", style=shade_4)
        # Format network speeds
        up_str = f"{self.network_up}KB/s" if self.network_up < 1024 else f"{self.network_up/1024:.1f}MB/s"
        down_str = f"{self.network_down}KB/s" if self.network_down < 1024 else f"{self.network_down/1024:.1f}MB/s"
        result.append(f"↑{up_str} ↓{down_str}", style="bold cyan")
        result.append(" │ ", style=shade_3)
        # System Load
        result.append("Load:", style=shade_4)
        load_color = "red" if self.system_load > 4 else "yellow" if self.system_load > 2 else "green"
        result.append(f"{self.system_load:.1f}", style=f"bold {load_color}")
        result.append(" ░▒▓ ", style=f"bold {primary}")
        # 2. Projects: count [name:percent% name:percent%]
        result.append(f"Projects:{self.total_projects} ", style=shade_4)
        # Build project progress list with shortened names
        project_parts = []
        for name, progress in self.projects_progress:
            # Shorten project names (first word or abbreviation, max 8 chars)
            short_name = name.split()[0][:8]
            color = self._get_progress_color(progress)
            project_parts.append(f"[{color}]{short_name}:{progress}%[/{color}]")
        projects_str = " ".join(project_parts) if project_parts else "None"
        result.append("[", style=shade_4)
        result.append_text(Text.from_markup(projects_str))
        result.append("]", style=shade_4)
        result.append(" │ ", style=shade_3)
        # 3. Workers: online/total count
        result.append("Workers:", style=shade_4)
        worker_color = "green" if self.workers_online > 0 else "red"
        result.append(f"{self.workers_online}/{self.workers_total}", style=f"bold {worker_color}")
        result.append(" │ ", style=shade_3)
        # 4. Subscription Plan
        result.append("Plan:", style=shade_4)
        plan_color = "cyan" if self.subscription_plan == "Pro" else "dim"
        result.append(self.subscription_plan, style=f"bold {plan_color}")
        result.append(" ░▒▓", style=f"bold {primary}")
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
