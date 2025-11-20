"""E2E tests for the TUI dashboard using Textual Pilot."""
import pytest
from textual.pilot import Pilot
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

# Ensure package is in path
sys.path.append(str(Path(__file__).parent.parent.parent))

from assistant.dashboard import VoiceAssistantApp
from assistant.config import Config


@pytest.fixture
def mock_config():
    config = Config()
    config.is_debug_mode = True
    config.memory_enabled = False
    config.theme_base_color = "#8899aa"
    return config


@pytest.fixture
def mock_personas_dir(tmp_path):
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir()
    # Create a dummy persona
    persona_dir = personas_dir / "jarvis"
    persona_dir.mkdir()
    (persona_dir / "config.yaml").write_text("""
name: JARVIS
description: Just A Rather Very Intelligent System
system_prompt: You are Jarvis.
voice:
  speed: 1.0
theme:
  theme_color: "#00aaff"
""")
    return personas_dir


@pytest.mark.asyncio
async def test_initial_state(mock_config, mock_personas_dir):
    """Test that the application starts with the correct initial state."""
    # Mock heavy dependencies to avoid hardware initialization
    with patch("assistant.dashboard.VoiceBridgeOrchestrator"), \
         patch("assistant.dashboard.MemoryManager"), \
         patch("assistant.dashboard.DeepThinkingEngine"):
        
        app = VoiceAssistantApp(mock_config, mock_personas_dir)
        async with app.run_test() as pilot:
            assert app.is_running
            # Check Status is the default active tab
            assert app.active_tab == "status"
            # Check ActivityFeed is visible
            assert app.query_one("#activity")


@pytest.mark.asyncio
async def test_switching_to_settings(mock_config, mock_personas_dir):
    """Test navigation to the Settings tab."""
    with patch("assistant.dashboard.VoiceBridgeOrchestrator"), \
         patch("assistant.dashboard.MemoryManager"), \
         patch("assistant.dashboard.DeepThinkingEngine"):
        
        app = VoiceAssistantApp(mock_config, mock_personas_dir)
        async with app.run_test() as pilot:
            # Directly set active tab to test reactive behavior
            app.active_tab = "settings"
            await pilot.pause()  # Allow UI to update
            # Check reactive state changed to settings
            assert app.active_tab == "settings"
            # Verify settings pane is visible
            pane = app.query_one("#content-settings")
            assert "active-pane" in pane.classes


@pytest.mark.asyncio
async def test_switching_to_chat(mock_config, mock_personas_dir):
    """Test navigation to the Chat tab."""
    with patch("assistant.dashboard.VoiceBridgeOrchestrator"), \
         patch("assistant.dashboard.MemoryManager"), \
         patch("assistant.dashboard.DeepThinkingEngine"):
        
        app = VoiceAssistantApp(mock_config, mock_personas_dir)
        async with app.run_test() as pilot:
            # Directly set active tab to test reactive behavior
            app.active_tab = "chat"
            await pilot.pause()  # Allow UI to update
            # Check reactive state changed to chat
            assert app.active_tab == "chat"
            # Verify chat pane is visible
            pane = app.query_one("#content-chat")
            assert "active-pane" in pane.classes
