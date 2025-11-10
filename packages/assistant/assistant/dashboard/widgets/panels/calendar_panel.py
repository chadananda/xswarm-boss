"""
Calendar panel for schedule management and reminders.

Displays events, reminders, and provides quick event creation.
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from rich.text import Text
from .panel_base import PanelBase


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: int
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    description: str = ""
    reminder_minutes: Optional[int] = None
    all_day: bool = False

    def is_today(self) -> bool:
        """Check if event is today."""
        return self.start_time.date() == date.today()

    def is_upcoming(self, hours: int = 24) -> bool:
        """Check if event is upcoming within given hours."""
        now = datetime.now()
        return now < self.start_time < now + timedelta(hours=hours)

    def is_past(self) -> bool:
        """Check if event is in the past."""
        return self.start_time < datetime.now()

    def duration_str(self) -> str:
        """Get duration as string."""
        if self.all_day:
            return "All day"
        if self.end_time:
            duration = self.end_time - self.start_time
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return ""


class CalendarPanel(PanelBase):
    """
    Calendar panel for schedule management.

    Features:
    - Event list (today + upcoming)
    - Time-sensitive highlighting
    - Reminder notifications
    - All-day event support
    - Quick event creation via voice
    - Day/week/month view toggle (future)
    """

    def __init__(
        self,
        **kwargs
    ):
        """Initialize calendar panel."""
        super().__init__(
            panel_id="calendar",
            title="Calendar",
            min_width=30,
            min_height=10,
            **kwargs
        )
        self.events: List[CalendarEvent] = []
        self.next_id = 1
        self.view_mode = "day"  # day, week, month (future enhancement)
        self.show_past = False

    def add_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: str = "",
        reminder_minutes: Optional[int] = None,
        all_day: bool = False
    ) -> CalendarEvent:
        """
        Add a new calendar event.

        Args:
            title: Event title
            start_time: Start date/time
            end_time: Optional end date/time
            description: Event description
            reminder_minutes: Minutes before event to remind
            all_day: Whether event is all-day

        Returns:
            The created event
        """
        event = CalendarEvent(
            id=self.next_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            reminder_minutes=reminder_minutes,
            all_day=all_day
        )
        self.events.append(event)
        self.next_id += 1

        # Sort events by start time
        self.events.sort(key=lambda e: e.start_time)

        # Update notification count (upcoming events)
        self._update_badge()
        self.refresh()

        return event

    def delete_event(self, event_id: int) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event ID to delete

        Returns:
            True if event was found and deleted
        """
        for i, event in enumerate(self.events):
            if event.id == event_id:
                self.events.pop(i)
                self._update_badge()
                self.refresh()
                return True
        return False

    def _update_badge(self):
        """Update notification badge count (upcoming events today)."""
        today_upcoming = sum(
            1 for e in self.events
            if e.is_today() and not e.is_past()
        )
        self.set_notification_count(today_upcoming)

    def _get_filtered_events(self) -> List[CalendarEvent]:
        """
        Get events filtered by current settings.

        Returns:
            Filtered event list
        """
        events = self.events

        # Filter past events if not showing them
        if not self.show_past:
            events = [e for e in events if not e.is_past()]

        # For day view, show today + next 7 days
        if self.view_mode == "day":
            cutoff = datetime.now() + timedelta(days=7)
            events = [e for e in events if e.start_time < cutoff]

        return events

    def render_content(self) -> Text:
        """
        Render calendar events.

        Returns:
            Rich Text with calendar content
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)
        content_width = widget_width - 4  # Account for borders
        available_lines = widget_height - 2  # Account for borders

        events = self._get_filtered_events()

        if not events:
            # Show empty state
            result.append("\n")
            result.append("  No upcoming events 📅\n", style="dim white")
            result.append("\n")
            result.append("  Say 'add event' to create one\n", style="dim white")
            return result

        # Group events by day
        today = date.today()
        tomorrow = today + timedelta(days=1)

        lines_used = 0

        # Current day header
        result.append(f"Today ({today.strftime('%a, %b %d')})\n", style="bold cyan")
        lines_used += 1

        # Today's events
        today_events = [e for e in events if e.is_today()]
        if today_events:
            for event in today_events:
                if lines_used >= available_lines:
                    break

                # Time
                if event.all_day:
                    time_str = "All day"
                    style = "green"
                else:
                    time_str = event.start_time.strftime("%H:%M")
                    # Highlight if happening soon
                    if event.is_upcoming(hours=1):
                        style = "bold yellow"
                    else:
                        style = "green"

                # Title
                max_title_len = content_width - len(time_str) - 3
                title = event.title
                if len(title) > max_title_len:
                    title = title[:max_title_len - 3] + "..."

                # Duration
                duration = f" ({event.duration_str()})" if event.duration_str() else ""

                line = f"  {time_str} {title}{duration}"
                result.append(line + "\n", style=style)
                lines_used += 1
        else:
            if lines_used < available_lines:
                result.append("  No events today\n", style="dim white")
                lines_used += 1

        # Tomorrow's events
        if lines_used < available_lines:
            result.append("\n")
            lines_used += 1

        if lines_used < available_lines:
            result.append(f"Tomorrow ({tomorrow.strftime('%a, %b %d')})\n", style="bold cyan")
            lines_used += 1

        tomorrow_events = [
            e for e in events
            if e.start_time.date() == tomorrow
        ]

        if tomorrow_events and lines_used < available_lines:
            for event in tomorrow_events:
                if lines_used >= available_lines:
                    break

                time_str = "All day" if event.all_day else event.start_time.strftime("%H:%M")
                max_title_len = content_width - len(time_str) - 3
                title = event.title
                if len(title) > max_title_len:
                    title = title[:max_title_len - 3] + "..."

                duration = f" ({event.duration_str()})" if event.duration_str() else ""

                line = f"  {time_str} {title}{duration}"
                result.append(line + "\n", style="white")
                lines_used += 1

        # Later events
        later_events = [
            e for e in events
            if e.start_time.date() > tomorrow
        ]

        if later_events and lines_used < available_lines - 2:
            result.append("\n")
            lines_used += 1

            result.append("Upcoming\n", style="bold cyan")
            lines_used += 1

            for event in later_events:
                if lines_used >= available_lines:
                    break

                date_str = event.start_time.strftime("%m/%d")
                time_str = "All day" if event.all_day else event.start_time.strftime("%H:%M")
                max_title_len = content_width - len(date_str) - len(time_str) - 4
                title = event.title
                if len(title) > max_title_len:
                    title = title[:max_title_len - 3] + "..."

                line = f"  {date_str} {time_str} {title}"
                result.append(line + "\n", style="dim white")
                lines_used += 1

        # Fill remaining space
        while lines_used < available_lines:
            result.append("\n")
            lines_used += 1

        return result

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to calendar panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands
        if super().handle_voice_command(command, args):
            return True

        # Calendar-specific commands
        if command == "add event":
            title = args.get("title", "New event")
            # TODO: Parse natural language time
            start_time = datetime.now() + timedelta(hours=1)
            self.add_event(title=title, start_time=start_time)
            return True

        elif command == "delete event":
            event_id = args.get("event_id")
            if event_id:
                self.delete_event(event_id)
                return True

        elif command == "show past events":
            self.show_past = True
            self.refresh()
            return True

        elif command == "hide past events":
            self.show_past = False
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
            "event_count": len(self.events),
            "today_count": sum(1 for e in self.events if e.is_today()),
            "upcoming_count": sum(1 for e in self.events if e.is_upcoming()),
            "view_mode": self.view_mode,
            "show_past": self.show_past,
        })
        return info
