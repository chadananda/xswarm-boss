"""
Multi-panel system for comprehensive TUI.

All panels inherit from PanelBase for consistent behavior.
"""

from .panel_base import PanelBase
from .chat_panel import ChatPanel, Message
from .todo_panel import TodoPanel, Task, Priority
from .notifications_panel import NotificationsPanel, Notification, NotificationLevel
from .calendar_panel import CalendarPanel, CalendarEvent
from .documents_panel import DocumentsPanel, Document
from .projects_panel import ProjectsPanel, Project, ProjectTask, ProjectStatus

__all__ = [
    # Base
    "PanelBase",
    # Chat
    "ChatPanel",
    "Message",
    # Todo
    "TodoPanel",
    "Task",
    "Priority",
    # Notifications
    "NotificationsPanel",
    "Notification",
    "NotificationLevel",
    # Calendar
    "CalendarPanel",
    "CalendarEvent",
    # Documents
    "DocumentsPanel",
    "Document",
    # Projects
    "ProjectsPanel",
    "Project",
    "ProjectTask",
    "ProjectStatus",
]
