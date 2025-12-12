"""
Scheduler - Periodic task execution for the assistant.

Handles background monitoring tasks like checking email, project status,
planning/habit checks, and memory consolidation without requiring user interaction.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Late imports to avoid circular dependencies
def _get_reminder_manager():
    from .reminders import get_reminder_manager
    return get_reminder_manager()

def _get_planner_data():
    from .planner import PlannerData
    return PlannerData()

@dataclass
class ScheduledTask:
    name: str
    interval: int  # seconds
    last_run: float = 0.0
    handler: Optional[Callable] = None
    # Time window constraints (optional)
    active_after_hour: Optional[int] = None  # Only run after this hour (0-23)
    active_before_hour: Optional[int] = None  # Only run before this hour (0-23)

class Scheduler:
    """
    Manages periodic background tasks.
    
    Default Schedule:
    - email_check: 5 min
    - project_status: 1 min
    - calendar_check: 15 min
    - memory_consolidation: 1 hour
    - document_indexing: 6 hours
    """
    
    def __init__(self, thinking_engine):
        self.thinking_engine = thinking_engine
        self.running = False
        self.tasks: Dict[str, ScheduledTask] = {}
        self._setup_default_tasks()
        
    def _setup_default_tasks(self):
        """Initialize default schedule from architecture docs."""
        defaults = {
            'email_check': 5 * 60,
            'project_status': 1 * 60,
            'calendar_check': 15 * 60,
            'memory_consolidation': 60 * 60,
            'document_indexing': 6 * 60 * 60
        }

        for name, interval in defaults.items():
            self.tasks[name] = ScheduledTask(name=name, interval=interval)

        # Planning-related tasks
        # Streak check: runs every 30 min after 6pm (18:00) to alert on at-risk habits
        self.tasks['streak_check'] = ScheduledTask(
            name='streak_check',
            interval=30 * 60,  # 30 minutes
            active_after_hour=18  # Only after 6pm
        )

        # Planning state sync: lightweight sync every 15 min during active hours
        self.tasks['planning_sync'] = ScheduledTask(
            name='planning_sync',
            interval=15 * 60,  # 15 minutes
            active_after_hour=7,  # 7am
            active_before_hour=22  # 10pm
        )

        # Meeting reminder check: runs every minute for timely reminders
        self.tasks['reminder_check'] = ScheduledTask(
            name='reminder_check',
            interval=60,  # 1 minute - needs to be frequent for 5-min reminders
            handler=self._check_meeting_reminders
        )

    def start(self):
        """Start the scheduler loop."""
        self.running = True
        asyncio.create_task(self._loop())
        logger.debug("Scheduler started")

    def stop(self):
        """Stop the scheduler loop."""
        self.running = False

    async def _loop(self):
        """Main scheduler loop."""
        while self.running:
            current_time = time.time()
            current_hour = datetime.now().hour

            for task in self.tasks.values():
                if current_time - task.last_run >= task.interval:
                    # Check time window constraints
                    if not self._is_task_active(task, current_hour):
                        continue

                    await self._execute_task(task)
                    task.last_run = current_time

            # Check every second
            await asyncio.sleep(1)

    def _is_task_active(self, task: ScheduledTask, current_hour: int) -> bool:
        """Check if task is within its active time window."""
        if task.active_after_hour is not None:
            if current_hour < task.active_after_hour:
                return False
        if task.active_before_hour is not None:
            if current_hour >= task.active_before_hour:
                return False
        return True

    async def _execute_task(self, task: ScheduledTask):
        """
        Execute a scheduled task.

        1. Call specific handler if exists
        2. Otherwise tickle thinking engine with task context
        """
        logger.debug(f"Running scheduled task: {task.name}")

        # If task has a specific handler, call it
        if task.handler:
            try:
                result = task.handler()
                if asyncio.iscoroutine(result):
                    await result
                return  # Handler took care of it
            except Exception as e:
                logger.error(f"Task handler for {task.name} failed: {e}")
                return

        # Default: tickle the thinking engine
        context = f"Scheduled task '{task.name}' is due."
        if self.thinking_engine:
            await self.thinking_engine.process_scheduled_task(task.name, context)

    def _check_meeting_reminders(self) -> List[str]:
        """
        Check for upcoming meetings and send reminders.

        Called every minute by the scheduler.
        Returns list of actions taken.
        """
        try:
            planner = _get_planner_data()
            reminder_manager = _get_reminder_manager()

            # Get events for the next 60 minutes
            events = planner.get_upcoming_events(days=1)

            # Filter to events starting within the next hour
            now = datetime.now()
            upcoming = []
            for event in events:
                try:
                    start_str = event.start_time
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    if start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=None)

                    # Within next 60 minutes?
                    if now <= start_dt <= now + timedelta(hours=1):
                        upcoming.append({
                            "id": event.id,
                            "title": event.title,
                            "start_time": event.start_time,
                            "reminder_minutes": getattr(event, "reminder_minutes", 5)
                        })
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Skipping event with invalid start time: {e}")
                    continue

            if not upcoming:
                return []

            # Check reminders for all upcoming events
            actions = reminder_manager.check_reminders(
                events=upcoming,
                phone_number=None,  # TODO: Get from config
                voice="Alex"
            )

            if actions:
                logger.info(f"Reminder actions: {actions}")

            return actions

        except Exception as e:
            logger.error(f"Meeting reminder check failed: {e}")
            return []
