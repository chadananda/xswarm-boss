"""
Permanent tests for ConversationLoop - the full conversation pipeline.

Tests the complete voice conversation loop including:
- VAD → Audio Capture → STT → AI → TTS → Audio Output
- Conversation turn lifecycle
- State management (idle, listening, thinking, speaking)
- Memory integration
- Callback handling
- Error handling
"""

import pytest
import asyncio
import numpy as np
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch, call
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.voice.conversation import ConversationLoop, ConversationTurn, AIClient
from assistant.voice.moshi_mlx import MoshiBridge
from assistant.personas.manager import PersonaManager
from assistant.personas.config import PersonaConfig
from assistant.memory import MemoryManager


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_moshi():
    """Mock MoshiBridge for conversation loop"""
    moshi = Mock(spec=MoshiBridge)
    
    # Mock generate_response to return audio + text
    moshi.generate_response.return_value = (
        np.random.randn(24000).astype(np.float32),  # 1 second of audio
        "Hello! How can I help you today?"
    )
    
    # Mock amplitude methods
    moshi.get_amplitude.return_value = 0.5
    moshi.mic_amplitude = 0.0
    moshi.moshi_amplitude = 0.0
    
    return moshi


@pytest.fixture
def mock_persona_manager():
    """Mock PersonaManager with JARVIS persona"""
    manager = Mock(spec=PersonaManager)
    
    persona = PersonaConfig(
        name="JARVIS",
        description="Just A Rather Very Intelligent System",
        version="1.0.0",
        system_prompt="You are JARVIS, a helpful AI assistant.",
    )
    
    manager.get_current_persona.return_value = persona
    
    return manager


@pytest.fixture
def mock_memory_manager():
    """Mock MemoryManager with async methods"""
    manager = AsyncMock(spec=MemoryManager)
    manager.store_message = AsyncMock(return_value="msg-123")
    manager.get_recent_messages = AsyncMock(return_value=[])
    manager.get_conversation_history = AsyncMock(return_value="")
    
    return manager


@pytest.fixture
def mock_ai_client():
    """Mock AIClient"""
    client = AsyncMock(spec=AIClient)
    client.chat = AsyncMock(return_value="I understand. How can I assist you?")
    client.is_available.return_value = True
    client.provider = "anthropic"
    
    return client


@pytest.fixture
def mock_config():
    """Mock Config with API keys"""
    from assistant.config import Config
    config = Config()
    config.anthropic_api_key = "test-key-anthropic"
    config.openai_api_key = None
    return config


@pytest.fixture
def conversation_loop(mock_moshi, mock_persona_manager, mock_memory_manager, mock_ai_client):
    """Factory to create ConversationLoop instances with mocks"""
    loop = ConversationLoop(
        moshi_bridge=mock_moshi,
        persona_manager=mock_persona_manager,
        memory_manager=mock_memory_manager,
        ai_client=mock_ai_client,
        user_id="test_user"
    )
    return loop


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestConversationLoopInitialization:
    """Tests for ConversationLoop initialization."""
    
    def test_initialization_success(self, conversation_loop):
        """Test conversation loop initializes correctly."""
        assert conversation_loop.running is False
        assert conversation_loop.user_id == "test_user"
        assert conversation_loop.moshi is not None
        assert conversation_loop.persona is not None
        assert conversation_loop.memory is not None
        assert conversation_loop.ai is not None
    
    def test_audio_io_initialization(self, conversation_loop):
        """Test AudioIO is initialized with correct settings."""
        assert conversation_loop.audio_io is not None
        assert conversation_loop.audio_io.sample_rate == 24000
        assert conversation_loop.audio_io.frame_size == 1920
        assert conversation_loop.audio_io.channels == 1
    
    def test_vad_initialization(self, conversation_loop):
        """Test VAD is initialized with correct settings."""
        assert conversation_loop.vad is not None
        assert conversation_loop.vad.threshold == 0.02
        assert conversation_loop.vad.min_speech_duration == 5
        assert conversation_loop.vad.min_silence_duration == 10
    
    def test_state_initialization(self, conversation_loop):
        """Test initial state is correct."""
        assert conversation_loop.running is False
        assert conversation_loop._loop_task is None
        assert conversation_loop._audio_buffer == []
        assert conversation_loop._is_listening is False


# =============================================================================
# START/STOP TESTS
# =============================================================================

class TestConversationLoopStartStop:
    """Tests for starting and stopping conversation loop."""
    
    @pytest.mark.asyncio
    async def test_start_conversation(self, conversation_loop):
        """Test starting conversation loop."""
        # Mock audio I/O methods
        conversation_loop.audio_io.start_input = Mock()
        conversation_loop.audio_io.start_output = Mock()
        
        # Start conversation
        await conversation_loop.start()
        
        # Verify state
        assert conversation_loop.running is True
        assert conversation_loop._loop_task is not None
        assert not conversation_loop._loop_task.done()
        
        # Verify audio I/O started
        conversation_loop.audio_io.start_input.assert_called_once()
        conversation_loop.audio_io.start_output.assert_called_once()
        
        # Cleanup
        await conversation_loop.stop()
    
    @pytest.mark.asyncio
    async def test_stop_conversation(self, conversation_loop):
        """Test stopping conversation loop."""
        # Mock audio I/O methods
        conversation_loop.audio_io.start_input = Mock()
        conversation_loop.audio_io.start_output = Mock()
        conversation_loop.audio_io.stop = Mock()
        
        # Start then stop
        await conversation_loop.start()
        await conversation_loop.stop()
        
        # Verify state
        assert conversation_loop.running is False
        conversation_loop.audio_io.stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_can_restart_after_stop(self, conversation_loop):
        """Test can restart conversation after stopping."""
        # Mock audio I/O
        conversation_loop.audio_io.start_input = Mock()
        conversation_loop.audio_io.start_output = Mock()
        conversation_loop.audio_io.stop = Mock()
        
        # Start → Stop → Start
        await conversation_loop.start()
        assert conversation_loop.running is True
        
        await conversation_loop.stop()
        assert conversation_loop.running is False
        
        await conversation_loop.start()
        assert conversation_loop.running is True
        
        # Cleanup
        await conversation_loop.stop()


# =============================================================================
# VAD AND AUDIO CAPTURE TESTS
# =============================================================================

class TestVADAndAudioCapture:
    """Tests for VAD and audio capture."""
    
    def test_audio_frame_callback_vad_processing(self, conversation_loop):
        """Test audio frame callback processes through VAD."""
        # Mock VAD
        conversation_loop.vad.process_frame = Mock(return_value=True)
        
        # Create audio frame
        audio_frame = np.random.randn(1920).astype(np.float32)
        
        # Process frame
        conversation_loop._on_audio_frame(audio_frame)
        
        # Verify VAD called
        conversation_loop.vad.process_frame.assert_called_once()
        
        # Verify audio buffered (speech detected)
        assert len(conversation_loop._audio_buffer) == 1
        assert conversation_loop._is_listening is True
    
    def test_audio_frame_callback_silence_detection(self, conversation_loop):
        """Test audio frame callback detects silence after speech."""
        # First frame: speech
        conversation_loop.vad.process_frame = Mock(return_value=True)
        audio_frame1 = np.random.randn(1920).astype(np.float32)
        conversation_loop._on_audio_frame(audio_frame1)
        
        assert conversation_loop._is_listening is True
        assert len(conversation_loop._audio_buffer) == 1
        
        # Second frame: silence
        conversation_loop.vad.process_frame = Mock(return_value=False)
        audio_frame2 = np.random.randn(1920).astype(np.float32)
        conversation_loop._on_audio_frame(audio_frame2)
        
        # Should mark buffer ready (stop listening)
        assert conversation_loop._is_listening is False
    
    @pytest.mark.asyncio
    async def test_capture_speech_segment(self, conversation_loop):
        """Test capturing complete speech segment."""
        # Add audio frames to buffer
        conversation_loop._audio_buffer = [
            np.random.randn(1920).astype(np.float32),
            np.random.randn(1920).astype(np.float32),
            np.random.randn(1920).astype(np.float32),
        ]
        
        # Mock VAD reset
        conversation_loop.vad.reset = Mock()
        
        # Capture segment
        segment = await conversation_loop._capture_speech_segment()
        
        # Verify segment
        assert segment is not None
        assert len(segment) == 1920 * 3  # 3 frames concatenated
        assert len(conversation_loop._audio_buffer) == 0  # Buffer cleared
        conversation_loop.vad.reset.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_capture_speech_segment_empty(self, conversation_loop):
        """Test capturing when buffer is empty."""
        conversation_loop._audio_buffer = []
        
        segment = await conversation_loop._capture_speech_segment()
        
        assert segment is None


# =============================================================================
# CONVERSATION TURN TESTS
# =============================================================================

class TestConversationTurn:
    """Tests for processing complete conversation turn."""
    
    @pytest.mark.asyncio
    async def test_process_turn_full_pipeline(self, conversation_loop, mock_moshi, mock_memory_manager, mock_persona_manager):
        """Test complete conversation turn pipeline."""
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Create user audio
        user_audio = np.random.randn(24000).astype(np.float32)
        
        # Mock state change callback
        state_changes = []
        conversation_loop.on_state_change = lambda s: state_changes.append(s)
        
        # Process turn
        await conversation_loop._process_turn(user_audio)
        
        # Verify Moshi generate_response called
        mock_moshi.generate_response.assert_called_once()
        
        # Verify memory storage (2 messages: user + assistant)
        assert mock_memory_manager.store_message.call_count == 2
        
        # Verify user message stored
        user_call = mock_memory_manager.store_message.call_args_list[0]
        assert user_call[1]["role"] == "user"
        assert user_call[1]["user_id"] == "test_user"
        
        # Verify assistant message stored
        assistant_call = mock_memory_manager.store_message.call_args_list[1]
        assert assistant_call[1]["role"] == "assistant"
        assert "Hello" in assistant_call[1]["message"]
        
        # Verify state transitions
        assert "thinking" in state_changes
        assert "speaking" in state_changes
        assert "listening" in state_changes
    
    @pytest.mark.asyncio
    async def test_process_turn_audio_playback(self, conversation_loop, mock_moshi):
        """Test audio playback during conversation turn."""
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Create user audio
        user_audio = np.random.randn(24000).astype(np.float32)
        
        # Process turn
        await conversation_loop._process_turn(user_audio)
        
        # Verify audio played
        conversation_loop.audio_io.play_audio.assert_called_once()
        
        # Verify audio data is correct
        played_audio = conversation_loop.audio_io.play_audio.call_args[0][0]
        assert len(played_audio) == 24000  # 1 second of audio from mock
    
    @pytest.mark.asyncio
    async def test_process_turn_callback_invoked(self, conversation_loop):
        """Test turn complete callback is invoked."""
        # Mock callback
        callback_calls = []
        
        def on_turn_complete(turn):
            callback_calls.append(turn)
        
        conversation_loop.on_turn_complete = on_turn_complete
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Verify callback called
        assert len(callback_calls) == 1
        
        # Verify turn object
        turn = callback_calls[0]
        assert isinstance(turn, ConversationTurn)
        assert turn.persona_name == "JARVIS"
        assert turn.assistant_text == "Hello! How can I help you today?"
        assert turn.user_audio is not None
        assert turn.assistant_audio is not None
    
    @pytest.mark.asyncio
    async def test_process_turn_amplitudes_tracked(self, conversation_loop, mock_moshi):
        """Test audio amplitudes are tracked during turn."""
        # Mock amplitude tracking
        mock_moshi.get_amplitude.side_effect = [0.3, 0.7]  # mic, then moshi
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Mock callback to capture metadata
        turns = []
        conversation_loop.on_turn_complete = lambda t: turns.append(t)
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Verify amplitudes in metadata
        turn = turns[0]
        assert turn.metadata["mic_amplitude"] == 0.3
        assert turn.metadata["moshi_amplitude"] == 0.7


# =============================================================================
# STATE MANAGEMENT TESTS
# =============================================================================

class TestStateManagement:
    """Tests for state change callbacks."""
    
    def test_state_change_callback_invoked(self, conversation_loop):
        """Test state change callback is invoked."""
        states = []
        
        def on_state_change(state):
            states.append(state)
        
        conversation_loop.on_state_change = on_state_change
        
        # Trigger state changes
        conversation_loop._set_state("listening")
        conversation_loop._set_state("thinking")
        conversation_loop._set_state("speaking")
        
        # Verify states captured
        assert states == ["listening", "thinking", "speaking"]
    
    def test_state_change_callback_error_handling(self, conversation_loop):
        """Test state change handles callback errors gracefully."""
        def bad_callback(state):
            raise ValueError("Callback error")
        
        conversation_loop.on_state_change = bad_callback
        
        # Should not crash
        conversation_loop._set_state("listening")


# =============================================================================
# GET AMPLITUDES TESTS
# =============================================================================

class TestGetAmplitudes:
    """Tests for get_amplitudes method."""
    
    def test_get_amplitudes_returns_correct_format(self, conversation_loop, mock_moshi):
        """Test get_amplitudes returns correct format."""
        mock_moshi.mic_amplitude = 0.25
        mock_moshi.moshi_amplitude = 0.75
        
        amplitudes = conversation_loop.get_amplitudes()
        
        assert "mic_amplitude" in amplitudes
        assert "moshi_amplitude" in amplitudes
        assert amplitudes["mic_amplitude"] == 0.25
        assert amplitudes["moshi_amplitude"] == 0.75


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in conversation loop."""
    
    @pytest.mark.asyncio
    async def test_process_turn_handles_moshi_error(self, conversation_loop, mock_moshi):
        """Test process_turn handles Moshi errors gracefully."""
        # Mock Moshi to raise error
        mock_moshi.generate_response.side_effect = Exception("Moshi error")
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn should not crash
        user_audio = np.random.randn(24000).astype(np.float32)
        
        # This will raise, but _conversation_loop catches it
        with pytest.raises(Exception):
            await conversation_loop._process_turn(user_audio)
    
    @pytest.mark.asyncio
    async def test_callback_errors_dont_crash(self, conversation_loop):
        """Test callback errors don't crash the loop."""
        def bad_callback(turn):
            raise ValueError("Callback error")
        
        conversation_loop.on_turn_complete = bad_callback
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn should handle callback error gracefully
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)  # Should not crash


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestConversationLoopIntegration:
    """Integration tests for full conversation loop."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_loop_cycle(self, conversation_loop):
        """Test complete conversation cycle: start → turn → stop."""
        # Mock audio I/O
        conversation_loop.audio_io.start_input = Mock()
        conversation_loop.audio_io.start_output = Mock()
        conversation_loop.audio_io.stop = Mock()
        conversation_loop.audio_io.play_audio = Mock()
        
        # Track turns
        turns = []
        conversation_loop.on_turn_complete = lambda t: turns.append(t)
        
        # Start conversation
        await conversation_loop.start()
        assert conversation_loop.running is True
        
        # Simulate voice activity
        conversation_loop._is_listening = True
        conversation_loop._audio_buffer = [
            np.random.randn(1920).astype(np.float32) for _ in range(10)
        ]
        
        # Process turn
        user_audio = await conversation_loop._capture_speech_segment()
        await conversation_loop._process_turn(user_audio)
        
        # Verify turn completed
        assert len(turns) == 1
        assert turns[0].persona_name == "JARVIS"
        
        # Stop conversation
        await conversation_loop.stop()
        assert conversation_loop.running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
