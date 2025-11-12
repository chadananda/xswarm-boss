"""
Worker dashboard widget for displaying worker/computer monitoring information.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from typing import Dict, List


class WorkerDashboard(Static):
    """
    Dashboard widget displaying worker cards with status, specs, and activity.

    Shows:
    - Worker name (hostname) and status badge ([ONLINE], [OFFLINE])
    - Activity state (⚡ BUSY, 💤 IDLE, ⭕ OFFLINE)
    - System specifications (OS, CPU, RAM, GPU)
    - Resource usage (CPU %, Memory usage, GPU %)
    - Current activity (active project/task or availability)
    - Stats (uptime, task completion counts)
    """
    # Reactive property for theme colors
    theme_colors = reactive({})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._workers = self._get_mock_workers()

    def _get_mock_workers(self) -> List[Dict]:
        """Generate mock worker data"""
        return [
            {
                "name": "MacBook-Pro-M3",
                "icon": "🖥️",
                "status": "ONLINE",
                "activity": "BUSY",
                "os": "macOS 14.2",
                "cpu": "M3 Max 16-core",
                "ram_total": 64,
                "ram_used": 45,
                "gpu": "40-core GPU",
                "cpu_percent": 78,
                "gpu_percent": 92,
                "current_task": "Authentication Refactor (compiling models)",
                "uptime": "3d 14h",
                "tasks_today": 12,
                "online": True
            },
            {
                "name": "Ubuntu-Workstation",
                "icon": "💻",
                "status": "ONLINE",
                "activity": "IDLE",
                "os": "Ubuntu 22.04",
                "cpu": "AMD Ryzen 9 5950X",
                "ram_total": 128,
                "ram_used": 8,
                "gpu": "RTX 4090",
                "cpu_percent": 12,
                "gpu_percent": 5,
                "current_task": None,
                "uptime": "7d 3h",
                "tasks_today": 8,
                "online": True
            },
            {
                "name": "Windows-Desktop",
                "icon": "🖥️",
                "status": "OFFLINE",
                "activity": "OFFLINE",
                "os": "Windows 11",
                "cpu": "Intel i9-13900K",
                "ram_total": 64,
                "ram_used": 0,
                "gpu": "RTX 4080",
                "cpu_percent": 0,
                "gpu_percent": 0,
                "current_task": "Marketing Campaign (video encoding)",
                "uptime": "12d 6h",
                "last_seen": "2h ago",
                "total_tasks": 145,
                "online": False
            }
        ]

    def _get_status_color(self, status: str) -> str:
        """Get color for status badge"""
        return "green" if status == "ONLINE" else "red"

    def _get_activity_icon_color(self, activity: str) -> str:
        """Get color for activity state"""
        colors = {
            "BUSY": "yellow",
            "IDLE": "dim",
            "OFFLINE": "red"
        }
        return colors.get(activity, "dim")

    def _get_resource_color(self, percent: int) -> str:
        """Get color for resource usage percentage"""
        if percent > 80:
            return "red"
        elif percent > 60:
            return "yellow"
        else:
            return "green"

    def render(self) -> Text:
        """Render worker dashboard"""
        text = Text()
        # Get theme colors or defaults
        shade_5 = self.theme_colors.get("shade_5", "white")
        shade_4 = self.theme_colors.get("shade_4", "#a0a0a0")
        shade_3 = self.theme_colors.get("shade_3", "#808080")
        # Render each worker
        for i, worker in enumerate(self._workers):
            # Add spacing between workers
            if i > 0:
                text.append("\n")
            # Worker name and status
            status_color = self._get_status_color(worker["status"])
            activity_color = self._get_activity_icon_color(worker["activity"])
            text.append(f"{worker['icon']}  ", style=shade_4)
            text.append(f"{worker['name']:<35}", style=f"bold {shade_5}")
            text.append(f"[{worker['status']}] ", style=f"bold {status_color}")
            # Activity icons
            activity_icons = {
                "BUSY": "⚡",
                "IDLE": "💤",
                "OFFLINE": "⭕"
            }
            activity_icon = activity_icons.get(worker["activity"], "")
            text.append(f"{activity_icon} {worker['activity']}", style=f"bold {activity_color}")
            text.append("\n")
            # Specs line
            text.append("  └─ ", style=shade_3)
            text.append(f"{worker['os']}", style=shade_4)
            text.append(" │ ", style=shade_3)
            text.append(f"{worker['cpu']}", style=shade_4)
            text.append(" │ ", style=shade_3)
            text.append(f"{worker['ram_total']}GB RAM", style=shade_4)
            text.append(" │ ", style=shade_3)
            text.append(f"{worker['gpu']}", style=shade_4)
            text.append("\n")
            # Online vs offline specific info
            if worker["online"]:
                # Resource usage (online workers)
                cpu_color = self._get_resource_color(worker["cpu_percent"])
                mem_percent = int((worker["ram_used"] / worker["ram_total"]) * 100)
                mem_color = self._get_resource_color(mem_percent)
                gpu_color = self._get_resource_color(worker["gpu_percent"])
                text.append("  📊 ", style=shade_3)
                text.append(f"CPU: {worker['cpu_percent']}%", style=cpu_color)
                text.append(" │ ", style=shade_3)
                text.append(f"Memory: {worker['ram_used']}GB/{worker['ram_total']}GB", style=mem_color)
                text.append(" │ ", style=shade_3)
                text.append(f"GPU: {worker['gpu_percent']}%", style=gpu_color)
                text.append("\n")
                # Current activity
                text.append("  🔨 ", style=shade_3)
                if worker["current_task"]:
                    text.append(f"Current: {worker['current_task']}", style=shade_4)
                else:
                    text.append("Available for tasks", style="green")
                text.append("\n")
                # Stats
                text.append("  ⏱️  ", style=shade_3)
                text.append(f"Uptime: {worker['uptime']}", style=shade_4)
                text.append(" │ ", style=shade_3)
                text.append(f"Tasks completed today: {worker['tasks_today']}", style=shade_4)
                text.append("\n")
            else:
                # Offline worker info
                text.append("  📊 ", style=shade_3)
                text.append(f"Last seen: {worker['last_seen']}", style="red")
                text.append("\n")
                text.append("  🔨 ", style=shade_3)
                text.append(f"Last task: {worker['current_task']}", style="dim")
                text.append("\n")
                text.append("  ⏱️  ", style=shade_3)
                text.append(f"Last uptime: {worker['uptime']}", style="dim")
                text.append(" │ ", style=shade_3)
                text.append(f"Total tasks: {worker['total_tasks']}", style="dim")
                text.append("\n")
        return text
