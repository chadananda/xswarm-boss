"""
Projects panel for project management with Kanban board.

Task management with columns (Backlog, In Progress, Done).
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from rich.text import Text
from .panel_base import PanelBase


class ProjectStatus(Enum):
    """Project task status."""
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class ProjectTask:
    """Represents a project task."""
    id: int
    title: str
    status: ProjectStatus = ProjectStatus.BACKLOG
    assignee: Optional[str] = None
    priority: int = 2  # 1=low, 2=medium, 3=high, 4=urgent
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def get_priority_icon(self) -> str:
        """Get icon for priority."""
        return {
            1: "🟢",
            2: "🟡",
            3: "🟠",
            4: "🔴",
        }.get(self.priority, "⚪")


@dataclass
class Project:
    """Represents a project."""
    id: int
    name: str
    description: str = ""
    tasks: List[ProjectTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def get_task_counts(self) -> Dict[str, int]:
        """Get count of tasks in each status."""
        return {
            "backlog": sum(1 for t in self.tasks if t.status == ProjectStatus.BACKLOG),
            "in_progress": sum(1 for t in self.tasks if t.status == ProjectStatus.IN_PROGRESS),
            "done": sum(1 for t in self.tasks if t.status == ProjectStatus.DONE),
        }


class ProjectsPanel(PanelBase):
    """
    Projects panel with Kanban board.

    Features:
    - Project list
    - Kanban board (Backlog | In Progress | Done)
    - Task cards
    - Priority indicators
    - Filter by tags, assignee, priority
    - Project statistics
    """

    def __init__(
        self,
        **kwargs
    ):
        """Initialize projects panel."""
        super().__init__(
            panel_id="projects",
            title="Projects",
            min_width=40,
            min_height=12,
            **kwargs
        )
        self.projects: List[Project] = []
        self.active_project: Optional[Project] = None
        self.next_project_id = 1
        self.next_task_id = 1
        self.view_mode = "board"  # board, list
        self.filter_assignee: Optional[str] = None

    def create_project(
        self,
        name: str,
        description: str = ""
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name
            description: Project description

        Returns:
            The created project
        """
        project = Project(
            id=self.next_project_id,
            name=name,
            description=description
        )
        self.projects.append(project)
        self.next_project_id += 1

        # Set as active if no active project
        if not self.active_project:
            self.active_project = project

        self._update_badge()
        self.refresh()
        return project

    def add_task(
        self,
        title: str,
        project: Optional[Project] = None,
        status: ProjectStatus = ProjectStatus.BACKLOG,
        priority: int = 2,
        assignee: Optional[str] = None,
        tags: List[str] = None
    ) -> ProjectTask:
        """
        Add a task to a project.

        Args:
            title: Task title
            project: Project (defaults to active project)
            status: Initial status
            priority: Priority level (1-4)
            assignee: Assigned person
            tags: Task tags

        Returns:
            The created task
        """
        if project is None:
            project = self.active_project

        if not project:
            raise ValueError("No active project")

        task = ProjectTask(
            id=self.next_task_id,
            title=title,
            status=status,
            assignee=assignee,
            priority=priority,
            tags=tags or []
        )
        project.tasks.append(task)
        self.next_task_id += 1

        self._update_badge()
        self.refresh()
        return task

    def move_task(self, task_id: int, new_status: ProjectStatus) -> bool:
        """
        Move task to new status column.

        Args:
            task_id: Task ID
            new_status: New status

        Returns:
            True if task was found and moved
        """
        if not self.active_project:
            return False

        for task in self.active_project.tasks:
            if task.id == task_id:
                task.status = new_status
                if new_status == ProjectStatus.DONE and not task.completed_at:
                    task.completed_at = datetime.now()
                self._update_badge()
                self.refresh()
                return True
        return False

    def _update_badge(self):
        """Update notification badge count (in-progress tasks)."""
        if self.active_project:
            counts = self.active_project.get_task_counts()
            self.set_notification_count(counts["in_progress"])

    def _get_filtered_tasks(self, status: Optional[ProjectStatus] = None) -> List[ProjectTask]:
        """
        Get tasks filtered by current settings.

        Args:
            status: Optional status filter

        Returns:
            Filtered task list
        """
        if not self.active_project:
            return []

        tasks = self.active_project.tasks

        # Filter by status
        if status:
            tasks = [t for t in tasks if t.status == status]

        # Filter by assignee
        if self.filter_assignee:
            tasks = [t for t in tasks if t.assignee == self.filter_assignee]

        # Sort by priority (highest first), then created date
        tasks = sorted(tasks, key=lambda t: (-t.priority, t.created_at))

        return tasks

    def render_content(self) -> Text:
        """
        Render Kanban board.

        Returns:
            Rich Text with board content
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)
        content_width = widget_width - 4  # Account for borders
        available_lines = widget_height - 2  # Account for borders

        if not self.projects:
            # No projects state
            result.append("\n")
            result.append("  No projects yet 📋\n", style="dim white")
            result.append("\n")
            result.append("  Say 'create project' to start\n", style="dim white")
            return result

        if not self.active_project:
            # Show project list
            result.append("Select a project:\n", style="bold cyan")
            lines_used = 1

            for project in self.projects:
                if lines_used >= available_lines:
                    break

                counts = project.get_task_counts()
                total = sum(counts.values())

                line = f"  📁 {project.name} ({total} tasks)"
                result.append(line + "\n", style="white")
                lines_used += 1

            while lines_used < available_lines:
                result.append("\n")
                lines_used += 1

            return result

        # Render Kanban board for active project
        # Header with project name
        result.append(f"{self.active_project.name}\n", style="bold cyan")
        lines_used = 1

        # Column headers
        col_width = content_width // 3
        header = f"{'Backlog':<{col_width}} {'In Progress':<{col_width}} {'Done':<{col_width}}"
        result.append(header + "\n", style="bold white")
        lines_used += 1

        # Separator
        result.append("─" * content_width + "\n", style="dim cyan")
        lines_used += 1

        # Get tasks for each column
        backlog_tasks = self._get_filtered_tasks(ProjectStatus.BACKLOG)
        in_progress_tasks = self._get_filtered_tasks(ProjectStatus.IN_PROGRESS)
        done_tasks = self._get_filtered_tasks(ProjectStatus.DONE)

        max_tasks = max(len(backlog_tasks), len(in_progress_tasks), len(done_tasks))

        # Render rows
        for i in range(max_tasks):
            if lines_used >= available_lines:
                break

            row_parts = []

            # Backlog column
            if i < len(backlog_tasks):
                task = backlog_tasks[i]
                icon = task.get_priority_icon()
                # Truncate task title to fit column
                max_len = col_width - 4
                title = task.title[:max_len - 3] + "..." if len(task.title) > max_len else task.title
                row_parts.append(f"{icon} {title}")
            else:
                row_parts.append("")

            # In Progress column
            if i < len(in_progress_tasks):
                task = in_progress_tasks[i]
                icon = task.get_priority_icon()
                max_len = col_width - 4
                title = task.title[:max_len - 3] + "..." if len(task.title) > max_len else task.title
                row_parts.append(f"{icon} {title}")
            else:
                row_parts.append("")

            # Done column
            if i < len(done_tasks):
                task = done_tasks[i]
                max_len = col_width - 4
                title = task.title[:max_len - 3] + "..." if len(task.title) > max_len else task.title
                row_parts.append(f"✓ {title}")
            else:
                row_parts.append("")

            # Build row
            line = ""
            for j, part in enumerate(row_parts):
                # Pad each column
                padded = part.ljust(col_width)
                line += padded

            result.append(line + "\n", style="white")
            lines_used += 1

        # Fill remaining space
        while lines_used < available_lines:
            result.append("\n")
            lines_used += 1

        return result

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to projects panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands
        if super().handle_voice_command(command, args):
            return True

        # Projects-specific commands
        if command == "create project":
            name = args.get("name", "New Project")
            description = args.get("description", "")
            self.create_project(name=name, description=description)
            return True

        elif command == "add task":
            title = args.get("title", "New task")
            priority = args.get("priority", 2)
            self.add_task(title=title, priority=priority)
            return True

        elif command == "move to backlog":
            task_id = args.get("task_id")
            if task_id:
                self.move_task(task_id, ProjectStatus.BACKLOG)
                return True

        elif command == "move to in progress":
            task_id = args.get("task_id")
            if task_id:
                self.move_task(task_id, ProjectStatus.IN_PROGRESS)
                return True

        elif command == "move to done":
            task_id = args.get("task_id")
            if task_id:
                self.move_task(task_id, ProjectStatus.DONE)
                return True

        return False

    def get_panel_info(self) -> Dict[str, Any]:
        """
        Get panel information for debugging.

        Returns:
            Dict with panel state
        """
        info = super().get_panel_info()
        info.update({
            "project_count": len(self.projects),
            "active_project": self.active_project.name if self.active_project else None,
            "view_mode": self.view_mode,
        })
        if self.active_project:
            info.update(self.active_project.get_task_counts())
        return info
