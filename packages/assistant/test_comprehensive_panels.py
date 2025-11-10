#!/usr/bin/env python3
"""
Comprehensive visual testing for ALL TUI panels.

Tests every panel at every terminal size with realistic sample data
to ensure nothing breaks across different configurations.

Generates SVG screenshots for manual inspection.
"""

import asyncio
from pathlib import Path
from typing import List, Tuple
from datetime import datetime, timedelta, date
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.containers import Container

# Import all panels
from assistant.dashboard.widgets.panels import (
    ChatPanel,
    TodoPanel, Priority,
    NotificationsPanel, NotificationLevel,
    CalendarPanel,
    DocumentsPanel,
    ProjectsPanel, ProjectStatus,
)


# Define test terminal sizes
TERMINAL_SIZES = [
    (40, 15, "tiny"),       # Minimum supported
    (60, 20, "small"),      # Small terminal
    (80, 30, "medium"),     # Common size
    (100, 35, "large"),     # Large terminal
    (120, 40, "xlarge"),    # Extra large
    (160, 50, "xxlarge"),   # Ultra wide
]


def populate_chat_panel(panel: ChatPanel):
    """Add sample messages to chat panel."""
    panel.add_message("user", "Hey! Can you help me debug this Python error?")
    panel.add_message("assistant", "Of course! I'd be happy to help. What error are you seeing?")
    panel.add_message("user", "I'm getting 'KeyError: username' when accessing a dictionary.")
    panel.add_message(
        "assistant",
        "A KeyError means you're trying to access a dictionary key that doesn't exist. "
        "You can fix this by:\n1. Using dict.get('username', default_value)\n"
        "2. Checking if 'username' in dict first\n3. Using try/except KeyError"
    )
    panel.add_message("user", "Perfect! The .get() method worked. Thanks!")
    panel.add_message("assistant", "You're welcome! Happy coding! 🐍")
    panel.focus_panel()  # Show as focused
    panel.set_listening(False)


def populate_todo_panel(panel: TodoPanel):
    """Add sample tasks to todo panel."""
    # Add various tasks with different priorities and states
    task1 = panel.add_task(
        "Review pull request #42",
        priority=Priority.HIGH,
        due_date=date.today(),
        tags=["code-review", "urgent"]
    )

    panel.add_task(
        "Update documentation for API",
        priority=Priority.MEDIUM,
        due_date=date.today() + timedelta(days=2),
        tags=["docs"]
    )

    task3 = panel.add_task(
        "Fix bug in authentication",
        priority=Priority.URGENT,
        due_date=date.today() - timedelta(days=1),  # Overdue!
        tags=["bug", "security"]
    )

    panel.add_task(
        "Refactor database queries",
        priority=Priority.LOW,
        tags=["refactor", "performance"]
    )

    task5 = panel.add_task(
        "Write unit tests for new feature",
        priority=Priority.MEDIUM,
        due_date=date.today() + timedelta(days=5),
        tags=["testing"]
    )

    # Complete one task
    panel.toggle_task(task1.id)

    panel.focus_panel()


def populate_notifications_panel(panel: NotificationsPanel):
    """Add sample notifications."""
    panel.add_notification(
        "System Update",
        "New version 2.1.0 is available. Click to update.",
        level=NotificationLevel.INFO,
        action_label="Update Now"
    )

    panel.add_notification(
        "Build Failed",
        "CI/CD pipeline failed on branch 'feature/auth'. Check logs for details.",
        level=NotificationLevel.ERROR,
        dismissible=True
    )

    panel.add_notification(
        "Deployment Successful",
        "Application deployed to production successfully.",
        level=NotificationLevel.SUCCESS
    )

    panel.add_notification(
        "Low Disk Space",
        "Only 2GB remaining on /dev/sda1. Consider cleaning up.",
        level=NotificationLevel.WARNING,
        dismissible=False
    )

    panel.add_notification(
        "New Message",
        "You have 3 unread messages in #general channel.",
        level=NotificationLevel.INFO
    )

    # Mark first notification as read
    panel.mark_read(1)

    panel.focus_panel()


def populate_calendar_panel(panel: CalendarPanel):
    """Add sample events."""
    now = datetime.now()

    # Event happening soon
    panel.add_event(
        "Team Standup",
        start_time=now + timedelta(minutes=30),
        end_time=now + timedelta(minutes=45),
        reminder_minutes=10
    )

    # Later today
    panel.add_event(
        "Client Meeting",
        start_time=now.replace(hour=14, minute=0),
        end_time=now.replace(hour=15, minute=0),
        description="Discuss Q4 roadmap",
        reminder_minutes=15
    )

    # All-day event today
    panel.add_event(
        "Company Anniversary",
        start_time=now.replace(hour=0, minute=0),
        all_day=True
    )

    # Tomorrow
    tomorrow = now + timedelta(days=1)
    panel.add_event(
        "Code Review Session",
        start_time=tomorrow.replace(hour=10, minute=0),
        end_time=tomorrow.replace(hour=11, minute=0)
    )

    # Next week
    next_week = now + timedelta(days=5)
    panel.add_event(
        "Sprint Planning",
        start_time=next_week.replace(hour=9, minute=0),
        end_time=next_week.replace(hour=11, minute=0),
        description="Plan Sprint 23"
    )

    panel.focus_panel()


def populate_documents_panel(panel: DocumentsPanel):
    """Documents panel auto-loads from current directory."""
    panel.focus_panel()
    # Panel auto-loads documents from the directory
    # Just mark as focused


def populate_projects_panel(panel: ProjectsPanel):
    """Add sample project with Kanban board."""
    # Create a project
    project = panel.create_project(
        "xswarm Voice Assistant",
        "AI-powered voice assistant with TUI"
    )

    # Add tasks to backlog
    panel.add_task(
        "Implement theme system",
        status=ProjectStatus.BACKLOG,
        priority=2,
        assignee="Alice",
        tags=["frontend", "design"]
    )

    panel.add_task(
        "Add voice wake word detection",
        status=ProjectStatus.BACKLOG,
        priority=3,
        assignee="Bob",
        tags=["voice", "ml"]
    )

    # Add tasks in progress
    panel.add_task(
        "Build multi-panel TUI",
        status=ProjectStatus.IN_PROGRESS,
        priority=4,
        assignee="Charlie",
        tags=["tui", "frontend"]
    )

    panel.add_task(
        "Integrate PostHog analytics",
        status=ProjectStatus.IN_PROGRESS,
        priority=2,
        assignee="Alice",
        tags=["analytics"]
    )

    # Add completed tasks
    panel.add_task(
        "Set up project structure",
        status=ProjectStatus.DONE,
        priority=2,
        tags=["setup"]
    )

    panel.add_task(
        "Configure CI/CD pipeline",
        status=ProjectStatus.DONE,
        priority=3,
        assignee="Bob",
        tags=["devops"]
    )

    panel.focus_panel()


# Test app templates for each panel
class ChatPanelTestApp(App):
    """Test app for ChatPanel."""
    CSS = """
    ChatPanel { width: 100%; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        panel = ChatPanel()
        populate_chat_panel(panel)
        yield panel
        yield Footer()


class TodoPanelTestApp(App):
    """Test app for TodoPanel."""
    CSS = """
    TodoPanel { width: 100%; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        panel = TodoPanel()
        populate_todo_panel(panel)
        yield panel
        yield Footer()


class NotificationsPanelTestApp(App):
    """Test app for NotificationsPanel."""
    CSS = """
    NotificationsPanel { width: 100%; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        panel = NotificationsPanel()
        populate_notifications_panel(panel)
        yield panel
        yield Footer()


class CalendarPanelTestApp(App):
    """Test app for CalendarPanel."""
    CSS = """
    CalendarPanel { width: 100%; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        panel = CalendarPanel()
        populate_calendar_panel(panel)
        yield panel
        yield Footer()


class DocumentsPanelTestApp(App):
    """Test app for DocumentsPanel."""
    CSS = """
    DocumentsPanel { width: 100%; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        panel = DocumentsPanel()
        populate_documents_panel(panel)
        yield panel
        yield Footer()


class ProjectsPanelTestApp(App):
    """Test app for ProjectsPanel."""
    CSS = """
    ProjectsPanel { width: 100%; height: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        panel = ProjectsPanel()
        populate_projects_panel(panel)
        yield panel
        yield Footer()


# Map panel names to test app classes
PANEL_TEST_APPS = {
    "chat": ChatPanelTestApp,
    "todo": TodoPanelTestApp,
    "notifications": NotificationsPanelTestApp,
    "calendar": CalendarPanelTestApp,
    "documents": DocumentsPanelTestApp,
    "projects": ProjectsPanelTestApp,
}


async def test_panel_at_size(
    panel_name: str,
    size: Tuple[int, int, str]
) -> str:
    """
    Test a specific panel at a specific size.

    Args:
        panel_name: Panel name (chat, todo, etc.)
        size: (width, height, label) tuple

    Returns:
        Path to generated SVG file
    """
    width, height, size_label = size

    # Get test app class
    app_class = PANEL_TEST_APPS[panel_name]
    app = app_class()

    # Set up output path
    output_dir = Path(__file__).parent / "tmp" / "panel_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{panel_name}_{size_label}_{width}x{height}.svg"

    # Run app in test mode
    async with app.run_test(size=(width, height)) as pilot:
        # Let the layout settle
        await pilot.pause(0.5)

        # Save screenshot
        app.save_screenshot(str(output_path))

    return str(output_path)


async def main():
    """Run complete comprehensive panel test suite."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE PANEL TEST SUITE")
    print("Testing ALL panels at ALL screen sizes with sample data")
    print("=" * 80 + "\n")

    # All panels to test
    panels = list(PANEL_TEST_APPS.keys())

    total_tests = len(TERMINAL_SIZES) * len(panels)
    current = 0
    generated_files = []

    for panel_name in panels:
        print(f"\n📋 Testing {panel_name.upper()} PANEL")
        print("-" * 80)

        for size in TERMINAL_SIZES:
            current += 1
            width, height, size_label = size

            print(f"  [{current:2d}/{total_tests}] {size_label:8s} ({width:3d}x{height:2d})...", end=" ")

            try:
                output_path = await test_panel_at_size(panel_name, size)
                generated_files.append(output_path)
                print("✓")

            except Exception as e:
                print(f"✗ FAILED: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"✅ Generated {len(generated_files)}/{total_tests} test screenshots")
    print(f"📁 View results in: tmp/panel_tests/")
    print("=" * 80 + "\n")

    # Print summary by panel
    print("Summary by panel:")
    for panel_name in panels:
        panel_files = [f for f in generated_files if f"/{panel_name}_" in f]
        status = "✅" if len(panel_files) == len(TERMINAL_SIZES) else "❌"
        print(f"  {status} {panel_name:15s}: {len(panel_files)}/{len(TERMINAL_SIZES)} screenshots")

    print()


if __name__ == "__main__":
    asyncio.run(main())
