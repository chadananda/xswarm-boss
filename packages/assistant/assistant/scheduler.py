"""
Scheduler - Periodic task execution for the assistant.

Handles background monitoring tasks like checking email, project status,
planning/habit checks, and memory consolidation without requiring user interaction.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

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

        1. Gather context (if specific handler exists)
        2. Tickle thinking engine with task context
        """
        logger.debug(f"Running scheduled task: {task.name}")
        
        context = f"Scheduled task '{task.name}' is due."
        
        # If we had specific handlers to gather context, we'd call them here
        # e.g. if task.handler: context = await task.handler()
        
        # Tickle the thinking engine
        if self.thinking_engine:
            await self.thinking_engine.process_scheduled_task(task.name, context)
