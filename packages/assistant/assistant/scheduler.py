"""
Scheduler - Periodic task execution for the assistant.

Handles background monitoring tasks like checking email, project status,
and memory consolidation without requiring user interaction.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

@dataclass
class ScheduledTask:
    name: str
    interval: int  # seconds
    last_run: float = 0.0
    handler: Optional[Callable] = None

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

    def start(self):
        """Start the scheduler loop."""
        self.running = True
        asyncio.create_task(self._loop())
        print("Scheduler started")

    def stop(self):
        """Stop the scheduler loop."""
        self.running = False

    async def _loop(self):
        """Main scheduler loop."""
        while self.running:
            current_time = time.time()
            
            for task in self.tasks.values():
                if current_time - task.last_run >= task.interval:
                    await self._execute_task(task)
                    task.last_run = current_time
            
            # Check every second
            await asyncio.sleep(1)

    async def _execute_task(self, task: ScheduledTask):
        """
        Execute a scheduled task.
        
        1. Gather context (if specific handler exists)
        2. Tickle thinking engine with task context
        """
        print(f"Running scheduled task: {task.name}")
        
        context = f"Scheduled task '{task.name}' is due."
        
        # If we had specific handlers to gather context, we'd call them here
        # e.g. if task.handler: context = await task.handler()
        
        # Tickle the thinking engine
        if self.thinking_engine:
            await self.thinking_engine.process_scheduled_task(task.name, context)
