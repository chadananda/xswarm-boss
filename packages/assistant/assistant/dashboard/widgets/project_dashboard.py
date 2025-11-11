"""
Project dashboard widget for displaying project management information.
"""

from textual.widgets import Static
from textual.widget import Widget
from textual.reactive import reactive
from rich.text import Text
from typing import Dict, List


class ProjectDashboard(Static):
    """
    Dashboard widget displaying project cards with status, progress, and metrics.

    Shows:
    - Project name and status badge ([ACTIVE], [PLANNED], [PAUSED], [COMPLETED])
    - Progress percentage and visual bar
    - Sprint/phase name
    - Task counts (total, completed, blocked)
    - Team lead
    - Last activity timestamp
    """

    # Reactive property for theme colors
    theme_colors = reactive({})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.projects = self._get_mock_projects()

    def _get_mock_projects(self) -> List[Dict]:
        """Generate mock project data"""
        return [
            {
                "name": "Authentication Refactor",
                "status": "ACTIVE",
                "progress": 78,
                "sprint": "Sprint 3",
                "tasks_total": 12,
                "tasks_completed": 9,
                "tasks_blocked": 3,
                "lead": "sarah",
                "last_activity": "2m ago"
            },
            {
                "name": "Marketing Campaign Q4",
                "status": "ACTIVE",
                "progress": 45,
                "sprint": "Phase 2",
                "tasks_total": 8,
                "tasks_completed": 4,
                "tasks_blocked": 1,
                "lead": "mike",
                "last_activity": "1h ago"
            },
            {
                "name": "Product V2 Launch",
                "status": "PLANNED",
                "progress": 12,
                "sprint": "Planning",
                "tasks_total": 20,
                "tasks_completed": 2,
                "tasks_blocked": 0,
                "lead": "alex",
                "last_activity": "1d ago"
            },
            {
                "name": "Mobile App Redesign",
                "status": "ACTIVE",
                "progress": 34,
                "sprint": "Sprint 1",
                "tasks_total": 15,
                "tasks_completed": 5,
                "tasks_blocked": 2,
                "lead": "jordan",
                "last_activity": "15m ago"
            }
        ]

    def _get_status_color(self, status: str) -> str:
        """Get color for status badge"""
        colors = {
            "ACTIVE": "green",
            "PLANNED": "yellow",
            "PAUSED": "dim",
            "COMPLETED": "cyan"
        }
        return colors.get(status, "white")

    def _get_progress_color(self, progress: int) -> str:
        """Get color for progress based on percentage"""
        if progress < 30:
            return "red"
        elif progress < 70:
            return "yellow"
        else:
            return "green"

    def _create_progress_bar(self, progress: int, width: int = 22) -> str:
        """Create visual progress bar using block characters"""
        filled = int((progress / 100) * width)
        empty = width - filled
        return "▓" * filled + "░" * empty

    def render(self) -> Text:
        """Render project dashboard"""
        text = Text()

        # Get theme colors or defaults
        shade_5 = self.theme_colors.get("shade_5", "white")
        shade_4 = self.theme_colors.get("shade_4", "#a0a0a0")
        shade_3 = self.theme_colors.get("shade_3", "#808080")

        for i, project in enumerate(self.projects):
            # Add spacing between projects
            if i > 0:
                text.append("\n")

            # Project name and status badge
            status_color = self._get_status_color(project["status"])
            progress_color = self._get_progress_color(project["progress"])

            text.append("■ ", style=f"bold {shade_4}")
            text.append(f"{project['name']:<40}", style=f"bold {shade_5}")
            text.append(f"[{project['status']}] ", style=f"bold {status_color}")
            text.append(f"{project['progress']}%", style=f"bold {progress_color}")
            text.append("\n")

            # Project details line
            text.append("  └─ ", style=shade_3)
            text.append(f"{project['sprint']}", style=shade_4)
            text.append(" │ ", style=shade_3)
            text.append(f"{project['tasks_total']} tasks", style=shade_4)
            text.append(" │ ", style=shade_3)

            # Blocked tasks (highlight if any)
            if project['tasks_blocked'] > 0:
                text.append(f"{project['tasks_blocked']} blocked", style="bold red")
            else:
                text.append("0 blocked", style=shade_4)

            text.append(" │ ", style=shade_3)
            text.append(f"Lead: @{project['lead']}", style=shade_4)
            text.append("\n")

            # Progress bar
            progress_bar = self._create_progress_bar(project['progress'])
            text.append("  ", style=shade_3)
            text.append(progress_bar, style=progress_color)
            text.append("\n")

            # Last activity
            text.append("  ", style=shade_3)
            text.append(f"Last activity: {project['last_activity']}", style="dim")
            text.append("\n")

        return text
