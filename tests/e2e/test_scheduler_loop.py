"""
E2E Test for Scheduler Loop.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock dependencies
sys.modules['assistant.hardware'] = MagicMock()
sys.modules['assistant.voice'] = MagicMock()
sys.modules['assistant.voice_server'] = MagicMock()

from assistant.scheduler import Scheduler, ScheduledTask
from assistant.thinking_engine import DeepThinkingEngine

@pytest.mark.asyncio
async def test_scheduler_loop_integration():
    """Test that scheduler triggers thinking engine."""
    
    # Mock thinking engine
    thinking_engine = MagicMock()
    thinking_engine.process_scheduled_task = AsyncMock()
    
    # Create scheduler with short intervals for testing
    scheduler = Scheduler(thinking_engine)
    scheduler.tasks['test_task'] = ScheduledTask(name='test_task', interval=0.1)
    
    # Start scheduler
    scheduler.start()
    
    try:
        # Wait for task to run
        await asyncio.sleep(0.2)
        
        # Verify thinking engine was called
        thinking_engine.process_scheduled_task.assert_called()
        args = thinking_engine.process_scheduled_task.call_args
        assert args[0][0] == 'test_task'
        
    finally:
        scheduler.stop()
