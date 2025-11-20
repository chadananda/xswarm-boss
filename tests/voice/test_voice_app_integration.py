"""
Integration tests for Voice Bridge integration with VoiceAssistantApp.

Tests voice bridge initialization, state callbacks, conversation control,
and error handling without visual snapshots.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
from assistant.dashboard import VoiceAssistantApp
from assistant.config import Config
from assistant.voice import ConversationState, VoiceBridgeOrchestrator


# Test fixtures
@pytest.fixture
def mock_config():
    """Create a mock Config instance."""
    config = Mock(spec=Config)
    config.theme_base_color = "#8899aa"
    config.default_persona = "JARVIS"
    config.moshi_quality = "auto"
    config.server_url = "http://localhost:3000"
    config.detect_device = Mock(return_value="cpu")
    return config


@pytest.fixture
def mock_personas_dir(tmp_path):
    """Create a temporary personas directory with test personas."""
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir(exist_ok=True)
    
    # Create JARVIS persona
    jarvis_yaml = personas_dir / "JARVIS.yaml"
    jarvis_yaml.write_text("""
name: JARVIS
system_prompt: "You are JARVIS, a helpful AI assistant."
theme:
  theme_color: "#00D4FF"
personality:
  traits:
    - helpful
    - professional
""")
    
    return personas_dir


@pytest.fixture
def test_app(mock_config, mock_personas_dir):
    """Create a VoiceAssistantApp instance for testing."""
    return VoiceAssistantApp(mock_config, mock_personas_dir)


# Test: Voice Initialization

@pytest.mark.asyncio
async def test_voice_initialization_success(test_app):
    """Test voice bridge initializes successfully."""
    # Mock update_activity to avoid screen stack error
    with patch.object(test_app, 'update_activity'):
        # Mock VoiceBridgeOrchestrator
        with patch("assistant.dashboard.app.VoiceBridgeOrchestrator") as MockBridge:
            # Create mock instance
            mock_bridge = MockBridge.return_value
            mock_bridge.initialize = AsyncMock()
            mock_bridge.on_state_change = Mock()
            
            # Mock memory manager
            test_app.memory_manager = Mock()
            
            # Initialize voice
            success = await test_app.initialize_voice()
            
            # Verify initialization
            assert success is True
            assert test_app.voice_initialized is True
            assert test_app.voice_bridge is not None
            
            # Verify initialize was called
            mock_bridge.initialize.assert_called_once()
            
            # Verify state callback was registered
            mock_bridge.on_state_change.assert_called_once()


@pytest.mark.asyncio
async def test_voice_initialization_already_initialized(test_app):
    """Test voice initialization when already initialized."""
    # Mark as already initialized
    test_app.voice_initialized = True
    
    # Try to initialize again
    success = await test_app.initialize_voice()
    
    # Should return True without re-initializing
    assert success is True


@pytest.mark.asyncio
async def test_voice_initialization_failure(test_app):
    """Test app handles voice initialization failure gracefully."""
    # Mock update_activity to avoid screen stack error
    with patch.object(test_app, 'update_activity'):
        # Mock VoiceBridgeOrchestrator to raise error
        with patch("assistant.dashboard.app.VoiceBridgeOrchestrator") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.initialize = AsyncMock(side_effect=RuntimeError("Moshi models not found"))
            
            # Mock memory manager
            test_app.memory_manager = Mock()
            
            # Initialize voice (should fail gracefully)
            success = await test_app.initialize_voice()
            
            # Verify failure is handled
            assert success is False
            assert test_app.voice_initialized is False


# Test: State Change Callbacks

def test_voice_state_callback_idle(test_app):
    """Test state change callback updates app to IDLE."""
    # Mock update_activity to avoid screen stack error
    with patch.object(test_app, 'update_activity'):
        # Trigger state change callback
        test_app._on_voice_state_change(ConversationState.IDLE)
        
        # Verify state updated
        assert test_app.state == "idle"


def test_voice_state_callback_listening(test_app):
    """Test state change callback updates app to LISTENING."""
    with patch.object(test_app, 'update_activity'):
        test_app._on_voice_state_change(ConversationState.LISTENING)
        assert test_app.state == "listening"


def test_voice_state_callback_thinking(test_app):
    """Test state change callback updates app to THINKING."""
    with patch.object(test_app, 'update_activity'):
        test_app._on_voice_state_change(ConversationState.THINKING)
        assert test_app.state == "thinking"


def test_voice_state_callback_speaking(test_app):
    """Test state change callback updates app to SPEAKING."""
    with patch.object(test_app, 'update_activity'):
        test_app._on_voice_state_change(ConversationState.SPEAKING)
        assert test_app.state == "speaking"


def test_voice_state_callback_error(test_app):
    """Test state change callback updates app to ERROR."""
    with patch.object(test_app, 'update_activity'):
        test_app._on_voice_state_change(ConversationState.ERROR)
        assert test_app.state == "error"


# Test: Voice Conversation Control

@pytest.mark.asyncio
async def test_voice_toggle_starts_conversation(test_app):
    """Test _start_voice() starts conversation when idle."""
    # Set up mock voice bridge
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.start_conversation = AsyncMock()
    
    # Mock update_activity
    with patch.object(test_app, 'update_activity'):
        # Start voice
        await test_app._start_voice()
        
        # Verify start_conversation was called
        test_app.voice_bridge.start_conversation.assert_called_once()


@pytest.mark.asyncio
async def test_voice_toggle_stops_conversation(test_app):
    """Test _stop_voice() stops conversation when active."""
    # Set up mock voice bridge
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.stop_conversation = AsyncMock()
    
    # Mock update_activity
    with patch.object(test_app, 'update_activity'):
        # Stop voice
        await test_app._stop_voice()
        
        # Verify stop_conversation was called
        test_app.voice_bridge.stop_conversation.assert_called_once()


@pytest.mark.asyncio
async def test_voice_start_error_handling(test_app):
    """Test _start_voice handles errors gracefully."""
    # Set up mock voice bridge that fails
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.start_conversation = AsyncMock(side_effect=RuntimeError("Audio device error"))
    
    # Mock update_activity
    with patch.object(test_app, 'update_activity') as mock_activity:
        # Try to start voice (should not raise exception)
        await test_app._start_voice()
        
        # Verify error was logged to activity feed
        mock_activity.assert_called()
        # Check that error message was passed
        call_args = [str(call) for call in mock_activity.call_args_list]
        assert any("Failed to start voice" in str(call) for call in call_args)


@pytest.mark.asyncio
async def test_voice_stop_error_handling(test_app):
    """Test _stop_voice handles errors gracefully."""
    # Set up mock voice bridge that fails
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.stop_conversation = AsyncMock(side_effect=RuntimeError("Stop failed"))
    
    # Mock update_activity
    with patch.object(test_app, 'update_activity') as mock_activity:
        # Try to stop voice (should not raise exception)
        await test_app._stop_voice()
        
        # Verify error was logged
        mock_activity.assert_called()
        call_args = [str(call) for call in mock_activity.call_args_list]
        assert any("Failed to stop voice" in str(call) for call in call_args)


# Test: Visualizer Updates with Voice Bridge

def test_update_visualizer_with_voice_bridge(test_app):
    """Test visualizer receives real-time amplitudes from voice bridge."""
    # Set up voice bridge with amplitudes
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.get_amplitudes = Mock(return_value={
        "mic_amplitude": 0.7,
        "moshi_amplitude": 0.3
    })
    
    # Mock visualizer
    mock_visualizer = Mock()
    mock_visualizer.add_mic_sample = Mock()
    mock_visualizer.set_assistant_amplitude = Mock()
    mock_visualizer.amplitude = 0.0
    
    with patch.object(test_app, 'query_one', return_value=mock_visualizer):
        # Call update_visualizer
        test_app.update_visualizer()
        
        # Verify amplitudes were retrieved
        test_app.voice_bridge.get_amplitudes.assert_called()
        
        # Verify visualizer was updated
        mock_visualizer.add_mic_sample.assert_called_with(0.7)
        mock_visualizer.set_assistant_amplitude.assert_called_with(0.3)


def test_update_visualizer_without_voice_bridge(test_app):
    """Test visualizer works when voice bridge not initialized."""
    # Voice not initialized
    test_app.voice_initialized = False
    test_app.voice_bridge = None
    
    # Mock visualizer
    mock_visualizer = Mock()
    mock_visualizer.amplitude = 0.0
    
    with patch.object(test_app, 'query_one', return_value=mock_visualizer):
        # Call update_visualizer (should not crash)
        test_app.update_visualizer()
        
        # Should complete without error


def test_update_visualizer_with_legacy_queue(test_app):
    """Test visualizer falls back to legacy audio queue."""
    # Voice not initialized
    test_app.voice_initialized = False
    test_app.voice_bridge = None
    
    # Set up legacy amplitude queue
    test_app._mic_amplitude_queue = [0.5, 0.6, 0.7]
    
    # Mock visualizer
    mock_visualizer = Mock()
    mock_visualizer.add_mic_sample = Mock()
    mock_visualizer.amplitude = 0.0
    
    with patch.object(test_app, 'query_one', return_value=mock_visualizer):
        # Call update_visualizer
        test_app.update_visualizer()
        
        # Verify samples were processed
        assert len(test_app._mic_amplitude_queue) == 0  # Queue should be emptied
        assert mock_visualizer.add_mic_sample.call_count == 3


# Test: Voice Bridge Quality Settings

@pytest.mark.asyncio
async def test_voice_initialization_with_quality_setting(mock_config, mock_personas_dir):
    """Test voice bridge initializes with correct quality setting."""
    # Set quality in config
    mock_config.moshi_quality = "q8"
    
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    
    # Mock update_activity
    with patch.object(app, 'update_activity'):
        with patch("assistant.dashboard.app.VoiceBridgeOrchestrator") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.initialize = AsyncMock()
            mock_bridge.on_state_change = Mock()
            
            # Mock memory manager
            app.memory_manager = Mock()
            
            # Initialize voice
            await app.initialize_voice()
            
            # Verify VoiceBridgeOrchestrator was created with correct quality
            MockBridge.assert_called_once()
            call_kwargs = MockBridge.call_args[1]
            assert call_kwargs["moshi_quality"] == "q8"


# Test: Memory Manager Integration

@pytest.mark.asyncio
async def test_voice_initialization_waits_for_memory(test_app):
    """Test voice initialization ensures memory manager exists."""
    # Memory not initialized
    test_app.memory_manager = None
    
    # Mock update_activity
    with patch.object(test_app, 'update_activity'):
        with patch("assistant.dashboard.app.VoiceBridgeOrchestrator") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.initialize = AsyncMock()
            mock_bridge.on_state_change = Mock()
            
            # Mock initialize_memory
            with patch.object(test_app, 'initialize_memory', new_callable=AsyncMock) as mock_init_memory:
                # Initialize voice
                await test_app.initialize_voice()
                
                # Verify memory was initialized first
                mock_init_memory.assert_called_once()


# Test: Amplitude Retrieval

def test_get_amplitudes_when_initialized(test_app):
    """Test get_amplitudes returns values when voice initialized."""
    # Set up voice bridge
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.get_amplitudes = Mock(return_value={
        "mic_amplitude": 0.8,
        "moshi_amplitude": 0.4
    })
    
    # Get amplitudes
    amplitudes = test_app.voice_bridge.get_amplitudes()
    
    # Verify values
    assert amplitudes["mic_amplitude"] == 0.8
    assert amplitudes["moshi_amplitude"] == 0.4


def test_get_amplitudes_when_not_initialized(test_app):
    """Test amplitudes are 0 when voice not initialized."""
    # Voice not initialized
    test_app.voice_initialized = False
    test_app.voice_bridge = None
    
    # In this case, visualizer should use default amplitude
    assert test_app.amplitude == 0.0


# Test: State Change Before Mount

def test_state_callback_before_mount(test_app):
    """Test state callback before app is mounted doesn't crash."""
    # Simulate state change before mount (query_one will fail)
    with patch.object(test_app, 'query_one', side_effect=Exception("App not mounted")):
        # This should not raise an exception due to try/except in _on_voice_state_change
        test_app._on_voice_state_change(ConversationState.LISTENING)
        
        # State should still be updated
        assert test_app.state == "listening"


# Test: Rapid State Changes

def test_rapid_state_changes(test_app):
    """Test app handles rapid state changes correctly."""
    # Mock update_activity to avoid screen stack errors
    with patch.object(test_app, 'update_activity'):
        # Simulate rapid state changes
        test_app._on_voice_state_change(ConversationState.LISTENING)
        assert test_app.state == "listening"
        
        test_app._on_voice_state_change(ConversationState.THINKING)
        assert test_app.state == "thinking"
        
        test_app._on_voice_state_change(ConversationState.SPEAKING)
        assert test_app.state == "speaking"
        
        test_app._on_voice_state_change(ConversationState.IDLE)
        assert test_app.state == "idle"
        
        # All transitions should work without issues


# Test: Voice Toggle Keybinding

def test_action_toggle_voice_when_not_initialized(test_app):
    """Test Ctrl+V when voice not initialized triggers initialization."""
    # Voice not initialized
    test_app.voice_initialized = False
    
    with patch.object(test_app, 'run_worker') as mock_run_worker:
        # Trigger action
        test_app.action_toggle_voice()
        
        # Verify initialization was started
        mock_run_worker.assert_called_once()


def test_action_toggle_voice_when_idle(test_app):
    """Test Ctrl+V when IDLE starts conversation."""
    # Voice initialized and idle
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.get_conversation_state = Mock(return_value=ConversationState.IDLE)
    
    with patch.object(test_app, 'run_worker') as mock_run_worker:
        # Trigger action
        test_app.action_toggle_voice()
        
        # Verify start was called
        mock_run_worker.assert_called_once()


def test_action_toggle_voice_when_listening(test_app):
    """Test Ctrl+V when LISTENING stops conversation."""
    # Voice initialized and listening
    test_app.voice_initialized = True
    test_app.voice_bridge = Mock()
    test_app.voice_bridge.get_conversation_state = Mock(return_value=ConversationState.LISTENING)
    
    with patch.object(test_app, 'run_worker') as mock_run_worker:
        # Trigger action
        test_app.action_toggle_voice()
        
        # Verify stop was called
        mock_run_worker.assert_called_once()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
