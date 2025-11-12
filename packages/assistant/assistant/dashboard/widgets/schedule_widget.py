"""
Schedule widget for displaying weekly calendar with today's detailed view.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from typing import Dict, List
from datetime import datetime, timedelta


class ScheduleWidget(Static):
    """
    Weekly schedule widget with detailed today view and abbreviated future days.

    Shows:
    - Today: Full event details with time slots, descriptions, and type icons
    - Rest of week: Compact view with just event titles and counts
    - Color-coded by event type
    """
    # Reactive property for theme colors
    theme_colors = reactive({})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.today = datetime.now()
        self.events = self._get_mock_events()

    def _get_mock_events(self) -> Dict[str, List[Dict]]:
        """Generate mock event data for the week"""
        # Calculate dates for the week
        dates = {}
        for i in range(7):
            date = self.today + timedelta(days=i)
            day_name = date.strftime("%A")
            date_str = date.strftime("%b %d")
            dates[i] = (day_name, date_str, date)
        # Today's events (detailed)
        today_events = [
            {
                "time": "9:00 AM - 9:30 AM",
                "title": "Morning Standup",
                "description": "Daily team sync - Sprint review and blockers",
                "type": "meeting",
                "location": "Zoom Room A"
            },
            {
                "time": "10:00 AM - 11:30 AM",
                "title": "Client Strategy Call",
                "description": "Q4 planning with Acme Corp stakeholders",
                "type": "meeting",
                "attendees": "Sarah, Mike, Client Team"
            },
            {
                "time": "12:00 PM - 1:00 PM",
                "title": "Lunch Break",
                "description": "Team lunch at Italian place downtown",
                "type": "personal",
                "location": "Mario's Trattoria"
            },
            {
                "time": "1:30 PM - 4:00 PM",
                "title": "Deep Focus Block",
                "description": "Auth refactor - Complete JWT implementation",
                "type": "focus",
                "notes": "No interruptions"
            },
            {
                "time": "4:30 PM - 5:00 PM",
                "title": "1-on-1 with Jordan",
                "description": "Career development check-in",
                "type": "one-on-one",
                "location": "Office 3B"
            },
            {
                "time": "5:00 PM - 5:00 PM",
                "title": "Deploy to Staging",
                "description": "Auth system deployment deadline",
                "type": "deadline",
                "priority": "HIGH"
            },
            {
                "time": "6:00 PM - 7:00 PM",
                "title": "Team Retrospective",
                "description": "Sprint 3 retrospective - What went well?",
                "type": "meeting",
                "location": "Conference Room B"
            }
        ]
        # Rest of week (abbreviated - just titles)
        week_events = {
            0: today_events,  # Today
            1: [  # Tomorrow
                {"title": "Product Demo Prep", "type": "meeting"},
                {"title": "Code Review Session", "type": "focus"},
                {"title": "Marketing Sync", "type": "meeting"},
                {"title": "Gym Session", "type": "personal"}
            ],
            2: [  # Day 2
                {"title": "Architecture Planning", "type": "meeting"},
                {"title": "API Design Review", "type": "meeting"},
                {"title": "Documentation Update", "type": "focus"}
            ],
            3: [  # Day 3
                {"title": "All Hands Meeting", "type": "meeting"},
                {"title": "Feature Branch Merge", "type": "deadline"},
                {"title": "Customer Support Review", "type": "meeting"},
                {"title": "Lunch with Alex", "type": "personal"}
            ],
            4: [  # Day 4
                {"title": "Weekly Planning", "type": "meeting"},
                {"title": "Bug Bash Session", "type": "focus"},
                {"title": "Performance Testing", "type": "focus"}
            ],
            5: [  # Day 5 (Friday)
                {"title": "Sprint Demo", "type": "meeting"},
                {"title": "Code Freeze", "type": "deadline"},
                {"title": "Happy Hour", "type": "personal"}
            ],
            6: [  # Day 6 (Weekend)
                {"title": "Side Project Hacking", "type": "personal"},
                {"title": "Brunch with Friends", "type": "personal"}
            ]
        }
        return {
            "dates": dates,
            "events": week_events
        }

    def _get_event_icon_color(self, event_type: str) -> tuple:
        """Get icon and color for event type"""
        type_config = {
            "meeting": ("📅", "yellow"),
            "deadline": ("⏰", "red"),
            "personal": ("🍽️", "green"),
            "focus": ("🎯", "cyan"),
            "one-on-one": ("👤", "magenta")
        }
        return type_config.get(event_type, ("📌", "white"))

    def _render_today(self, text: Text, events: List[Dict], shade_5: str, shade_4: str, shade_3: str):
        """Render today's detailed schedule"""
        # Today header
        day_name, date_str, _ = self.events["dates"][0]
        text.append("━" * 60, style=shade_3)
        text.append("\n")
        text.append(f"  {day_name}, {date_str}", style=f"bold {shade_5}")
        text.append(" - TODAY\n", style=f"bold yellow")
        text.append("━" * 60, style=shade_3)
        text.append("\n\n")
        # Render each event with full details
        for event in events:
            icon, color = self._get_event_icon_color(event["type"])
            # Time and title
            text.append(f"  {icon}  ", style=color)
            text.append(f"{event['time']:<25}", style=f"bold {shade_4}")
            text.append("\n")
            text.append("      ", style=shade_3)
            text.append(f"{event['title']}", style=f"bold {shade_5}")
            text.append("\n")
            # Description
            text.append("      ", style=shade_3)
            text.append(f"{event['description']}", style=shade_4)
            text.append("\n")
            # Additional details (location, attendees, notes, priority)
            details = []
            if "location" in event:
                details.append(f"📍 {event['location']}")
            if "attendees" in event:
                details.append(f"👥 {event['attendees']}")
            if "notes" in event:
                details.append(f"📝 {event['notes']}")
            if "priority" in event:
                priority_color = "red" if event["priority"] == "HIGH" else shade_4
                details.append(f"⚠️  {event['priority']}")
                # Render priority in its color
                text.append("      ", style=shade_3)
                text.append(details[-1], style=priority_color)
                details = details[:-1]
                if details:
                    text.append(" │ ", style=shade_3)
            if details:
                text.append("      ", style=shade_3)
                text.append(" │ ".join(details), style="dim")
                text.append("\n")
            text.append("\n")

    def _render_rest_of_week(self, text: Text, shade_5: str, shade_4: str, shade_3: str):
        """Render abbreviated view for rest of week"""
        text.append("\n")
        text.append("━" * 60, style=shade_3)
        text.append("\n")
        text.append("  REST OF WEEK", style=f"bold {shade_5}")
        text.append("\n")
        text.append("━" * 60, style=shade_3)
        text.append("\n\n")
        # Render each day compactly
        for day_num in range(1, 7):
            day_name, date_str, _ = self.events["dates"][day_num]
            events = self.events["events"].get(day_num, [])
            # Day header with event count
            text.append(f"  {day_name}, {date_str}", style=f"bold {shade_4}")
            text.append(f"  ({len(events)} events)", style="dim")
            text.append("\n")
            # List event titles only (no times, no descriptions)
            for event in events:
                icon, color = self._get_event_icon_color(event["type"])
                text.append(f"    {icon} ", style=color)
                text.append(f"{event['title']}", style=shade_4)
                text.append("\n")
            text.append("\n")

    def render(self) -> Text:
        """Render weekly schedule"""
        text = Text()
        # Get theme colors or defaults
        shade_5 = self.theme_colors.get("shade_5", "white")
        shade_4 = self.theme_colors.get("shade_4", "#a0a0a0")
        shade_3 = self.theme_colors.get("shade_3", "#808080")
        # Render today's schedule (detailed)
        today_events = self.events["events"].get(0, [])
        self._render_today(text, today_events, shade_5, shade_4, shade_3)
        # Render rest of week (abbreviated)
        self._render_rest_of_week(text, shade_5, shade_4, shade_3)
        return text
