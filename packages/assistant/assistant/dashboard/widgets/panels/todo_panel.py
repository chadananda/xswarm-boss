"""
Todo panel for task management.

Quick task list with checkboxes, priorities, and voice control.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from rich.text import Text
from .panel_base import PanelBase


class Priority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """Represents a todo task."""
    id: int
    title: str
    completed: bool = False
    priority: Priority = Priority.MEDIUM
    due_date: Optional[date] = None
    tags: List[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date or self.completed:
            return False
        return date.today() > self.due_date

    def is_due_soon(self) -> bool:
        """Check if task is due within 3 days."""
        if not self.due_date or self.completed:
            return False
        days_until = (self.due_date - date.today()).days
        return 0 <= days_until <= 3


class TodoPanel(PanelBase):
    """
    Todo list panel for task management.

    Features:
    - Task list with checkboxes
    - Priority indicators (🔴 🟡 🟢)
    - Due dates with overdue highlighting
    - Tags/categories
    - Quick add via voice
    - Filter by status, priority, tags
    - Sort by priority, due date, created
    """

    def __init__(
        self,
        **kwargs
    ):
        """Initialize todo panel."""
        super().__init__(
            panel_id="todo",
            title="Todo List",
            min_width=30,
            min_height=10,
            **kwargs
        )
        self.tasks: List[Task] = []
        self.next_id = 1
        self.filter_completed = False  # Show uncompleted by default
        self.sort_by = "priority"  # priority, due_date, created

    def add_task(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        due_date: Optional[date] = None,
        tags: List[str] = None
    ) -> Task:
        """
        Add a new task.

        Args:
            title: Task title
            priority: Task priority
            due_date: Optional due date
            tags: Optional tags

        Returns:
            The created task
        """
        task = Task(
            id=self.next_id,
            title=title,
            priority=priority,
            due_date=due_date,
            tags=tags or []
        )
        self.tasks.append(task)
        self.next_id += 1

        # Update notification count (uncompleted tasks)
        self.set_notification_count(self._count_incomplete())

        self.refresh()
        return task

    def toggle_task(self, task_id: int) -> bool:
        """
        Toggle task completion status.

        Args:
            task_id: Task ID to toggle

        Returns:
            True if task was found and toggled
        """
        for task in self.tasks:
            if task.id == task_id:
                task.completed = not task.completed
                self.set_notification_count(self._count_incomplete())
                self.refresh()
                return True
        return False

    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID to delete

        Returns:
            True if task was found and deleted
        """
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                self.set_notification_count(self._count_incomplete())
                self.refresh()
                return True
        return False

    def _count_incomplete(self) -> int:
        """Count incomplete tasks."""
        return sum(1 for task in self.tasks if not task.completed)

    def _get_filtered_sorted_tasks(self) -> List[Task]:
        """
        Get tasks filtered and sorted according to current settings.

        Returns:
            Filtered and sorted task list
        """
        # Filter
        if self.filter_completed:
            tasks = [t for t in self.tasks if not t.completed]
        else:
            tasks = self.tasks

        # Sort
        if self.sort_by == "priority":
            tasks = sorted(tasks, key=lambda t: (-t.priority.value, t.created_at))
        elif self.sort_by == "due_date":
            # Tasks with due dates first, then by date
            tasks = sorted(
                tasks,
                key=lambda t: (t.due_date is None, t.due_date, t.created_at)
            )
        elif self.sort_by == "created":
            tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)

        return tasks

    def _get_priority_icon(self, priority: Priority) -> str:
        """Get icon for priority level."""
        return {
            Priority.LOW: "🟢",
            Priority.MEDIUM: "🟡",
            Priority.HIGH: "🟠",
            Priority.URGENT: "🔴",
        }[priority]

    def _format_due_date(self, task: Task) -> tuple[str, str]:
        """
        Format due date for display.

        Returns:
            (date_string, style) tuple
        """
        if not task.due_date:
            return "", "dim white"

        if task.is_overdue():
            return f"⚠ {task.due_date.strftime('%m/%d')}", "bold red"
        elif task.is_due_soon():
            return f"📅 {task.due_date.strftime('%m/%d')}", "bold yellow"
        else:
            return f"📅 {task.due_date.strftime('%m/%d')}", "dim white"

    def render_content(self) -> Text:
        """
        Render todo list.

        Returns:
            Rich Text with todo content
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)
        content_width = widget_width - 4  # Account for borders
        available_lines = widget_height - 2  # Account for borders

        tasks = self._get_filtered_sorted_tasks()

        if not tasks:
            # Show empty state
            result.append("\n")
            result.append("  No tasks! 🎉\n", style="dim green")
            result.append("\n")
            result.append("  Say 'add task' to create one\n", style="dim white")
            return result

        # Render tasks
        lines_used = 0
        for task in tasks:
            if lines_used >= available_lines:
                break

            # Checkbox
            checkbox = "[✓]" if task.completed else "[ ]"
            style = "dim white" if task.completed else "white"

            # Priority icon
            priority_icon = self._get_priority_icon(task.priority)

            # Title (potentially truncated)
            max_title_len = content_width - 15  # Space for checkbox, icons, etc.
            title = task.title
            if len(title) > max_title_len:
                title = title[:max_title_len - 3] + "..."

            # Due date
            due_str, due_style = self._format_due_date(task)

            # Build line
            line = f"{checkbox} {priority_icon} {title}"

            # Add due date if present
            if due_str:
                # Pad to width
                padding = content_width - len(line) - len(due_str) - 1
                if padding > 0:
                    line += " " * padding + " " + due_str
                else:
                    line += " " + due_str

            result.append(line + "\n", style=style)
            lines_used += 1

            # Show tags if present and there's space
            if task.tags and lines_used < available_lines:
                tags_str = " ".join(f"#{tag}" for tag in task.tags)
                if len(tags_str) > content_width - 6:
                    tags_str = tags_str[:content_width - 9] + "..."
                result.append(f"  {tags_str}\n", style="dim cyan")
                lines_used += 1

        # Fill remaining space
        while lines_used < available_lines:
            result.append("\n")
            lines_used += 1

        return result

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to todo panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands (focus, minimize, etc.)
        if super().handle_voice_command(command, args):
            return True

        # Todo-specific commands
        if command == "add task":
            title = args.get("title", "New task")
            priority_str = args.get("priority", "medium").upper()
            priority = Priority[priority_str] if priority_str in Priority.__members__ else Priority.MEDIUM

            self.add_task(title=title, priority=priority)
            return True

        elif command == "complete task":
            task_id = args.get("task_id")
            if task_id:
                self.toggle_task(task_id)
                return True

        elif command == "delete task":
            task_id = args.get("task_id")
            if task_id:
                self.delete_task(task_id)
                return True

        elif command == "show completed":
            self.filter_completed = False
            self.refresh()
            return True

        elif command == "hide completed":
            self.filter_completed = True
            self.refresh()
            return True

        elif command == "sort by priority":
            self.sort_by = "priority"
            self.refresh()
            return True

        elif command == "sort by due date":
            self.sort_by = "due_date"
            self.refresh()
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
            "task_count": len(self.tasks),
            "incomplete_count": self._count_incomplete(),
            "filter_completed": self.filter_completed,
            "sort_by": self.sort_by,
        })
        return info
