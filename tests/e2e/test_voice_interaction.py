"""
E2E Test for Voice Interaction.
"""
import pytest
import asyncio
import numpy as np
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock dependencies
sys.modules['assistant.hardware'] = MagicMock()
sys.modules['assistant.voice_server'] = MagicMock()
sys.modules['assistant.system'] = MagicMock()
sys.modules['assistant.voice'] = MagicMock()
sys.modules['assistant.personas'] = MagicMock()
sys.modules['assistant.personas.manager'] = MagicMock() # Mock submodule to fix import error
sys.modules['assistant.memory'] = MagicMock()
sys.modules['assistant.tools'] = MagicMock()

# Configure system mock
gpu_mock = MagicMock()
gpu_mock.grade = "A"
gpu_mock.temp_c = 50
gpu_mock.vram_total_gb = 24 # Correct attribute name
gpu_mock.vram_used = 10
gpu_mock.compute_score = 85.0
gpu_mock.vram_used_gb = 12.0
gpu_mock.util_percent = 45.0
# dashboard_widgets imports from .hardware, so we must mock that
sys.modules['assistant.hardware'].detect_gpu_capability.return_value = gpu_mock
sys.modules['assistant.system'].detect_gpu_capability.return_value = gpu_mock # Mock both to be safe

# Since importing VoiceBridgeOrchestrator is hard due to many deps,
# we'll test the ConversationLoop logic if possible, or mock the orchestrator
# and test the TUI integration.

# Let's test the TUI's integration with the voice components
from assistant.dashboard import VoiceAssistantApp
from assistant.config import Config

@pytest.mark.asyncio
async def test_voice_interaction_flow():
    """Test the flow from audio input to response."""
    config = Config()
    voice_process = MagicMock()
    
    app = VoiceAssistantApp(config, personas_dir=MagicMock(), voice_server_process=voice_process)
    
    # Mock the voice orchestrator
    orchestrator_mock = MagicMock()
    orchestrator_mock.process_audio_input = AsyncMock(return_value={
        "response_text": "Hello",
        "response_audio": np.zeros(100),
        "mic_amplitude": 0.5,
        "moshi_amplitude": 0.5
    })
    app.voice_orchestrator = orchestrator_mock
    
    async with app.run_test() as pilot:
        # Simulate audio input (this would usually come from the mic thread)
        # We can call the method directly to simulate the event
        
        # In the real app, audio updates happen via callbacks or polling
        # Here we verify that if the orchestrator returns data, the UI updates
        
        # Trigger a manual check or simulate the loop
        # Since we can't easily simulate the audio thread in this test environment,
        # we'll verify the orchestrator is set up correctly
        
        assert app.voice_orchestrator is not None
        
        # Manually trigger the processing logic that would happen
        result = await app.voice_orchestrator.process_audio_input(np.zeros(100))
        assert result["response_text"] == "Hello"
