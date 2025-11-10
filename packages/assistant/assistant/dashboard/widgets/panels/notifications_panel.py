"""
Notifications panel for system alerts and updates.

Displays feed of notifications with priority levels and actions.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from rich.text import Text
from .panel_base import PanelBase


class NotificationLevel(Enum):
    """Notification priority levels."""
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4


@dataclass
class Notification:
    """Represents a notification."""
    id: int
    title: str
    message: str
    level: NotificationLevel
    timestamp: datetime
    read: bool = False
    dismissible: bool = True
    action_label: Optional[str] = None

    def get_icon(self) -> str:
        """Get icon for notification level."""
        return {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
        }[self.level]

    def get_style(self) -> str:
        """Get style for notification level."""
        return {
            NotificationLevel.INFO: "cyan",
            NotificationLevel.SUCCESS: "green",
            NotificationLevel.WARNING: "yellow",
            NotificationLevel.ERROR: "red",
        }[self.level]


class NotificationsPanel(PanelBase):
    """
    Notifications panel for alerts and updates.

    Features:
    - Notification feed with priority levels
    - Badge count (unread notifications)
    - Priority indicators (ℹ️ ✅ ⚠️ ❌)
    - Read/unread status
    - Dismiss actions
    - Filter by level
    - Auto-scroll to newest
    """

    def __init__(
        self,
        max_notifications: int = 50,
        **kwargs
    ):
        """
        Initialize notifications panel.

        Args:
            max_notifications: Maximum notifications to keep
        """
        super().__init__(
            panel_id="notifications",
            title="Notifications",
            min_width=30,
            min_height=10,
            **kwargs
        )
        self.notifications: List[Notification] = []
        self.next_id = 1
        self.max_notifications = max_notifications
        self.filter_level: Optional[NotificationLevel] = None
        self.show_read = True

    def add_notification(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        dismissible: bool = True,
        action_label: Optional[str] = None
    ) -> Notification:
        """
        Add a new notification.

        Args:
            title: Notification title
            message: Notification message
            level: Priority level
            dismissible: Whether notification can be dismissed
            action_label: Optional action button label

        Returns:
            The created notification
        """
        notification = Notification(
            id=self.next_id,
            title=title,
            message=message,
            level=level,
            timestamp=datetime.now(),
            dismissible=dismissible,
            action_label=action_label
        )

        # Add to front (newest first)
        self.notifications.insert(0, notification)
        self.next_id += 1

        # Trim if exceeds max
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[:self.max_notifications]

        # Update badge count
        self._update_badge()
        self.refresh()

        return notification

    def mark_read(self, notification_id: int) -> bool:
        """
        Mark notification as read.

        Args:
            notification_id: Notification ID

        Returns:
            True if notification was found
        """
        for notif in self.notifications:
            if notif.id == notification_id:
                notif.read = True
                self._update_badge()
                self.refresh()
                return True
        return False

    def mark_all_read(self):
        """Mark all notifications as read."""
        for notif in self.notifications:
            notif.read = True
        self._update_badge()
        self.refresh()

    def dismiss(self, notification_id: int) -> bool:
        """
        Dismiss a notification.

        Args:
            notification_id: Notification ID

        Returns:
            True if notification was found and dismissed
        """
        for i, notif in enumerate(self.notifications):
            if notif.id == notification_id and notif.dismissible:
                self.notifications.pop(i)
                self._update_badge()
                self.refresh()
                return True
        return False

    def dismiss_all(self):
        """Dismiss all dismissible notifications."""
        self.notifications = [n for n in self.notifications if not n.dismissible]
        self._update_badge()
        self.refresh()

    def _update_badge(self):
        """Update notification badge count."""
        unread_count = sum(1 for n in self.notifications if not n.read)
        self.set_notification_count(unread_count)

    def _get_filtered_notifications(self) -> List[Notification]:
        """
        Get notifications filtered by current settings.

        Returns:
            Filtered notification list
        """
        notifications = self.notifications

        # Filter by level
        if self.filter_level:
            notifications = [n for n in notifications if n.level == self.filter_level]

        # Filter by read status
        if not self.show_read:
            notifications = [n for n in notifications if not n.read]

        return notifications

    def render_content(self) -> Text:
        """
        Render notifications feed.

        Returns:
            Rich Text with notifications
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)
        content_width = widget_width - 4  # Account for borders
        available_lines = widget_height - 2  # Account for borders

        notifications = self._get_filtered_notifications()

        if not notifications:
            # Show empty state
            result.append("\n")
            result.append("  No notifications 🔕\n", style="dim white")
            result.append("\n")
            result.append("  You're all caught up!\n", style="dim green")
            return result

        # Render notifications
        lines_used = 0
        for notif in notifications:
            if lines_used >= available_lines:
                break

            # Icon and title
            icon = notif.get_icon()
            style = notif.get_style()

            # Dim if read
            if notif.read:
                style = f"dim {style}"

            # Format timestamp
            now = datetime.now()
            time_diff = now - notif.timestamp
            if time_diff.seconds < 60:
                time_str = "just now"
            elif time_diff.seconds < 3600:
                time_str = f"{time_diff.seconds // 60}m ago"
            elif time_diff.days == 0:
                time_str = notif.timestamp.strftime("%H:%M")
            else:
                time_str = notif.timestamp.strftime("%m/%d")

            # Title line
            max_title_len = content_width - 15  # Space for icon, time, etc.
            title = notif.title
            if len(title) > max_title_len:
                title = title[:max_title_len - 3] + "..."

            title_line = f"{icon} {title}"

            # Pad and add timestamp
            padding = content_width - len(title_line) - len(time_str) - 1
            if padding > 0:
                title_line += " " * padding + " " + time_str
            else:
                title_line += " " + time_str

            result.append(title_line + "\n", style=f"bold {style}")
            lines_used += 1

            if lines_used >= available_lines:
                break

            # Message line (wrapped)
            max_msg_len = content_width - 2
            message = notif.message
            if len(message) > max_msg_len:
                message = message[:max_msg_len - 3] + "..."

            result.append(f"  {message}\n", style=style)
            lines_used += 1

            if lines_used >= available_lines:
                break

            # Action line (if present)
            if notif.action_label:
                result.append(f"  [{notif.action_label}]\n", style=f"bold {style}")
                lines_used += 1

            # Separator
            if lines_used < available_lines and notif != notifications[-1]:
                result.append("\n")
                lines_used += 1

        # Fill remaining space
        while lines_used < available_lines:
            result.append("\n")
            lines_used += 1

        return result

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to notifications panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands
        if super().handle_voice_command(command, args):
            return True

        # Notifications-specific commands
        if command == "mark all read":
            self.mark_all_read()
            return True

        elif command == "dismiss all":
            self.dismiss_all()
            return True

        elif command == "show only unread":
            self.show_read = False
            self.refresh()
            return True

        elif command == "show all":
            self.show_read = True
            self.refresh()
            return True

        elif command == "filter by level":
            level_str = args.get("level", "").upper()
            if level_str in NotificationLevel.__members__:
                self.filter_level = NotificationLevel[level_str]
                self.refresh()
                return True

        elif command == "clear filter":
            self.filter_level = None
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
            "notification_count": len(self.notifications),
            "unread_count": sum(1 for n in self.notifications if not n.read),
            "filter_level": self.filter_level.name if self.filter_level else None,
            "show_read": self.show_read,
        })
        return info
