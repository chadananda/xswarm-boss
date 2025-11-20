"""
Test TUI Input Handling.
"""
import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock dependencies
sys.modules['assistant.hardware'] = MagicMock()
sys.modules['assistant.voice'] = MagicMock()
sys.modules['assistant.voice_server'] = MagicMock()
sys.modules['mlx'] = MagicMock()

from assistant.dashboard import VoiceAssistantApp
from assistant.config import Config

@pytest.mark.asyncio
async def test_input_handling():
    """Test handling user input in the TUI."""
    config = Config()
    voice_process = MagicMock()
    app = VoiceAssistantApp(config, personas_dir=MagicMock(), voice_server_process=voice_process)
    
    # Mock thinking engine
    app.thinking_engine = MagicMock()
    app.thinking_engine.process_user_input = MagicMock()
    
    async with app.run_test() as pilot:
        # Find input widget
        input_widget = pilot.app.query_one("#chat-input")
        
        # Type something
        await pilot.click("#chat-input")
        await pilot.press("h", "e", "l", "l", "o", "enter")
        
        # Wait for events to process
        await pilot.pause()
        
        # Verify input cleared (checking side effect of submission)
        assert input_widget.value == ""
