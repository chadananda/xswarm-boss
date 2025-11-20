"""
Test TUI Dashboard Rendering.
"""
import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock dependencies to avoid runtime errors
sys.modules['assistant.hardware'] = MagicMock()
sys.modules['assistant.voice'] = MagicMock()
sys.modules['assistant.voice_server'] = MagicMock()
# Ensure we don't mock numpy/torch if they are already loaded
# but we do want to mock MLX
sys.modules['mlx'] = MagicMock()

from assistant.dashboard import VoiceAssistantApp
from assistant.config import Config

@pytest.mark.asyncio
async def test_dashboard_rendering():
    """Test that the dashboard renders correctly."""
    config = Config()
    # Mock voice server process
    voice_process = MagicMock()
    
    app = VoiceAssistantApp(config, personas_dir=MagicMock(), voice_server_process=voice_process)
    
    async with app.run_test() as pilot:
        # Check for main widgets
        assert pilot.app.query_one("#header")
        assert pilot.app.query_one("#chat-panel")
        assert pilot.app.query_one("#status-panel")
        
        # Check initial state
        status = pilot.app.query_one("#status-text")
        assert "Ready" in str(status.render())
