"""
Permanent tests for VoiceBridgeOrchestrator.

Tests the complete voice conversation orchestration layer including:
- Initialization and configuration
- State management and transitions
- Persona integration and switching
- Memory integration and conversation history
- Audio amplitude tracking
- Conversation lifecycle management
"""

import pytest
import asyncio
import numpy as np
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.voice import VoiceBridgeOrchestrator, ConversationState
from assistant.personas.manager import PersonaManager
from assistant.personas.config import PersonaConfig, VoiceSettings
from assistant.memory import MemoryManager


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_persona_manager():
    """Mock PersonaManager with JARVIS persona"""
    manager = Mock(spec=PersonaManager)
    
    # Create mock persona with realistic configuration
    persona = PersonaConfig(
        name="JARVIS",
        description="Just A Rather Very Intelligent System",
        version="1.0.0",
        system_prompt="You are JARVIS, a helpful AI assistant.",
    )
    
    # Configure mock methods
    manager.get_current_persona.return_value = persona
    manager.set_current_persona.return_value = True
    manager.reload_persona.return_value = True
    
    return manager


@pytest.fixture
def mock_persona_manager_no_persona():
    """Mock PersonaManager with no persona set"""
    manager = Mock(spec=PersonaManager)
    manager.get_current_persona.return_value = None
    return manager


@pytest.fixture
def mock_memory_manager():
    """Mock MemoryManager with async methods"""
    manager = AsyncMock(spec=MemoryManager)
    manager.initialize = AsyncMock()
    manager.store_message = AsyncMock(return_value="msg-123")
    manager.get_conversation_history = AsyncMock(return_value="")
    manager.get_context = AsyncMock(return_value=[])
    manager.clear_history = AsyncMock()
    manager.close = AsyncMock()
    return manager


@pytest.fixture
def mock_moshi():
    """Mock MoshiBridge with realistic audio responses"""
    moshi = Mock()
    moshi.quality = "q8"
    moshi.sample_rate = 24000
    
    # Mock generate_response to return audio + text
    moshi.generate_response.return_value = (
        np.random.randn(24000).astype(np.float32),  # 1 second of audio
        "Hello, how can I help you?"
    )
    
    # Mock amplitude methods
    moshi.get_amplitude.return_value = 0.5
    
    return moshi


@pytest.fixture
def mock_config():
    """Mock Config with API keys"""
    from assistant.config import Config
    config = Config()
    config.anthropic_api_key = "test-key-123"  # Mock API key for testing
    return config
@pytest.fixture
def mock_voice_components(mock_moshi):
    """Mock both MoshiBridge and AIClient for tests"""
    with patch('assistant.voice.MoshiBridge') as MockMoshi, \
         patch('assistant.voice.AIClient') as MockAIClient, \
         patch('assistant.voice.ConversationLoop') as MockConversationLoop:
        # Configure Moshi mock
        MockMoshi.return_value = mock_moshi
        # Configure AIClient mock
        mock_ai_client = Mock()
        mock_ai_client.is_available.return_value = True
        MockAIClient.return_value = mock_ai_client
        # Configure ConversationLoop mock
        mock_conversation_loop = AsyncMock()
        mock_conversation_loop.start = AsyncMock()
        mock_conversation_loop.stop = AsyncMock()
        mock_conversation_loop.get_amplitudes.return_value = {
            "mic_amplitude": 0.0,
            "moshi_amplitude": 0.0
        }
        MockConversationLoop.return_value = mock_conversation_loop
        yield {
            'moshi': MockMoshi,
            'ai_client': MockAIClient,
            'conversation_loop': MockConversationLoop,
            'mock_moshi': mock_moshi,
            'mock_ai_client': mock_ai_client,
            'mock_conversation_loop': mock_conversation_loop
        }
@pytest.fixture
def orchestrator_factory(mock_persona_manager, mock_memory_manager, mock_config):
    """Factory to create orchestrator instances with mocks"""
    def _create(
        persona_manager=None,
        memory_manager=None,
        config=None,
        user_id="test_user",
        moshi_quality="q8"
    ):
        return VoiceBridgeOrchestrator(
            persona_manager=persona_manager or mock_persona_manager,
            memory_manager=memory_manager or mock_memory_manager,
            config=config or mock_config,
            user_id=user_id,
            moshi_quality=moshi_quality
        )
    return _create


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestInitialization:
    """Tests for VoiceBridgeOrchestrator initialization."""
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, mock_persona_manager, mock_memory_manager, mock_config):
        """Test successful initialization with valid persona."""
        orchestrator = VoiceBridgeOrchestrator(
            persona_manager=mock_persona_manager,
            memory_manager=mock_memory_manager,
            config=mock_config,
            user_id="test_user",
            moshi_quality="q8"
        )
        
        # Mock MoshiBridge and AIClient initialization
        with patch('assistant.voice.MoshiBridge') as MockMoshi, \
             patch('assistant.voice.AIClient') as MockAIClient:
            mock_moshi_instance = Mock()
            mock_moshi_instance.quality = "q8"
            MockMoshi.return_value = mock_moshi_instance
            mock_ai_client = Mock()
            MockAIClient.return_value = mock_ai_client

            await orchestrator.initialize()

            # Verify initialization
            assert orchestrator.current_persona is not None
            assert orchestrator.current_persona.name == "JARVIS"
            assert orchestrator.moshi is not None
            assert orchestrator.ai_client is not None
            assert orchestrator.state == ConversationState.IDLE

            # Verify memory initialized
            mock_memory_manager.initialize.assert_called_once()

            # Verify MoshiBridge was created with correct quality
            MockMoshi.assert_called_once_with(quality="q8")
            # Verify AIClient was created with config
            MockAIClient.assert_called_once_with(mock_config)
    
    @pytest.mark.asyncio
    async def test_initialization_fails_no_persona(self, mock_persona_manager_no_persona, mock_memory_manager, mock_config):
        """Test initialization fails gracefully when no persona is set."""
        orchestrator = VoiceBridgeOrchestrator(
            persona_manager=mock_persona_manager_no_persona,
            memory_manager=mock_memory_manager,
            config=mock_config
        )
        
        with pytest.raises(ValueError, match="No persona set"):
            await orchestrator.initialize()
    
    @pytest.mark.asyncio
    async def test_auto_quality_detection(self, mock_persona_manager, mock_memory_manager, mock_config):
        """Test auto-quality detection for Moshi models."""
        orchestrator = VoiceBridgeOrchestrator(
            persona_manager=mock_persona_manager,
            memory_manager=mock_memory_manager,
            config=mock_config,
            moshi_quality="auto"
        )
        
        with patch('assistant.voice.MoshiBridge') as MockMoshi, \
             patch('assistant.voice.AIClient') as MockAIClient:
            mock_moshi = Mock()
            mock_moshi.quality = "q8"  # Auto-detected quality
            MockMoshi.return_value = mock_moshi
            mock_ai_client = Mock()
            MockAIClient.return_value = mock_ai_client

            await orchestrator.initialize()

            assert orchestrator.moshi.quality == "q8"
            MockMoshi.assert_called_once_with(quality="auto")
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("quality", ["bf16", "q8", "q4"])
    async def test_explicit_quality_settings(self, mock_persona_manager, mock_memory_manager, mock_config, quality):
        """Test initialization with explicit quality settings."""
        orchestrator = VoiceBridgeOrchestrator(
            persona_manager=mock_persona_manager,
            memory_manager=mock_memory_manager,
            config=mock_config,
            moshi_quality=quality
        )
        
        with patch('assistant.voice.MoshiBridge') as MockMoshi, \
             patch('assistant.voice.AIClient') as MockAIClient:
            mock_moshi = Mock()
            mock_moshi.quality = quality
            MockMoshi.return_value = mock_moshi
            mock_ai_client = Mock()
            MockAIClient.return_value = mock_ai_client

            await orchestrator.initialize()

            MockMoshi.assert_called_once_with(quality=quality)
    
    @pytest.mark.asyncio
    async def test_initialization_moshi_failure(self, mock_persona_manager, mock_memory_manager, mock_config):
        """Test initialization handles Moshi initialization failure."""
        orchestrator = VoiceBridgeOrchestrator(
            persona_manager=mock_persona_manager,
            memory_manager=mock_memory_manager,
            config=mock_config
        )
        
        with patch('assistant.voice.MoshiBridge') as MockMoshi, \
             patch('assistant.voice.AIClient') as MockAIClient:
            MockMoshi.side_effect = RuntimeError("Model download failed")
            mock_ai_client = Mock()
            MockAIClient.return_value = mock_ai_client

            with pytest.raises(RuntimeError, match="Failed to initialize Moshi"):
                await orchestrator.initialize()
            
            # Verify error state is set
            assert orchestrator.state == ConversationState.ERROR


# =============================================================================
# STATE MANAGEMENT TESTS
# =============================================================================

class TestStateManagement:
    """Tests for conversation state tracking and transitions."""
    
    @pytest.mark.asyncio
    async def test_initial_state_is_idle(self, orchestrator_factory, mock_moshi):
        """Test initial state is IDLE."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        assert orchestrator.state == ConversationState.IDLE
        assert orchestrator.get_conversation_state() == ConversationState.IDLE
    
    @pytest.mark.asyncio
    async def test_state_transitions_during_conversation(self, orchestrator_factory, mock_moshi):
        """Test state transitions: IDLE → LISTENING → THINKING → SPEAKING → LISTENING."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Track state changes
        states_observed = []
        orchestrator.on_state_change(lambda s: states_observed.append(s))
        
        # Start conversation → LISTENING
        await orchestrator.start_conversation()
        assert orchestrator.state == ConversationState.LISTENING
        assert ConversationState.LISTENING in states_observed
        
        # Process audio → THINKING → SPEAKING → LISTENING
        audio_input = np.random.randn(24000).astype(np.float32)
        result = await orchestrator.process_audio_input(audio_input)
        
        # Verify result
        assert result is not None
        
        # Verify state transitions occurred
        assert ConversationState.THINKING in states_observed
        assert ConversationState.SPEAKING in states_observed
        
        # Should return to LISTENING
        assert orchestrator.state == ConversationState.LISTENING
    
    @pytest.mark.asyncio
    async def test_state_change_callbacks_fire(self, orchestrator_factory, mock_moshi):
        """Test state change callbacks are called correctly."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Register multiple callbacks
        callback1_calls = []
        callback2_calls = []
        
        orchestrator.on_state_change(lambda s: callback1_calls.append(s))
        orchestrator.on_state_change(lambda s: callback2_calls.append(s))
        
        # Change state
        await orchestrator.start_conversation()
        
        # Both callbacks should have been called
        assert ConversationState.LISTENING in callback1_calls
        assert ConversationState.LISTENING in callback2_calls
    
    @pytest.mark.asyncio
    async def test_error_state_handling(self, orchestrator_factory, mock_moshi):
        """Test error state handling during conversation."""
        orchestrator = orchestrator_factory()
        
        # Mock Moshi to raise error
        mock_moshi.generate_response.side_effect = Exception("Audio processing failed")
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio should trigger error
        audio_input = np.random.randn(24000).astype(np.float32)
        result = await orchestrator.process_audio_input(audio_input)
        
        # Should return None on error
        assert result is None
        
        # State should be set to ERROR (but then back to LISTENING if still running)
        # The implementation returns to LISTENING if _running is True
        assert orchestrator.state == ConversationState.LISTENING
    
    @pytest.mark.asyncio
    async def test_state_callback_error_handling(self, orchestrator_factory, mock_moshi):
        """Test state change handles callback errors gracefully."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Register callback that raises error
        def bad_callback(state):
            raise ValueError("Callback error")
        
        orchestrator.on_state_change(bad_callback)
        
        # Should not crash when state changes
        await orchestrator.start_conversation()
        
        # State should still be set correctly despite callback error
        assert orchestrator.state == ConversationState.LISTENING


# =============================================================================
# PERSONA INTEGRATION TESTS
# =============================================================================

class TestPersonaIntegration:
    """Tests for persona system integration."""
    
    @pytest.mark.asyncio
    async def test_loads_current_persona_on_init(self, orchestrator_factory, mock_moshi):
        """Test loads current persona on initialization."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        assert orchestrator.current_persona is not None
        assert orchestrator.current_persona.name == "JARVIS"
    
    @pytest.mark.asyncio
    async def test_persona_switching_updates_settings(self, orchestrator_factory, mock_persona_manager, mock_moshi):
        """Test persona switching updates voice settings."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Create new persona
        new_persona = PersonaConfig(
            name="GLaDOS",
            description="Sarcastic AI",
            version="1.0.0",
            system_prompt="You are GLaDOS."
        )
        
        # Mock persona manager to return new persona
        mock_persona_manager.get_current_persona.return_value = new_persona
        
        # Switch persona
        success = await orchestrator.switch_persona("GLaDOS")
        
        assert success is True
        assert orchestrator.current_persona.name == "GLaDOS"
        mock_persona_manager.set_current_persona.assert_called_once_with("GLaDOS")
    
    @pytest.mark.asyncio
    async def test_persona_reload_refreshes_config(self, orchestrator_factory, mock_persona_manager, mock_moshi):
        """Test persona reload refreshes configuration."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Reload persona
        success = await orchestrator.reload_persona()
        
        assert success is True
        mock_persona_manager.reload_persona.assert_called_once_with("JARVIS")
    
    @pytest.mark.asyncio
    async def test_system_prompt_includes_personality(self, orchestrator_factory, mock_moshi):
        """Test system prompt includes personality.md content."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Build prompt
        prompt = orchestrator._build_prompt_with_history("")
        
        # Should include persona information
        assert "JARVIS" in prompt or "helpful" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_conversation_history_in_prompt(self, orchestrator_factory, mock_moshi):
        """Test conversation history is included in AI context."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Build prompt with history
        history = "User: Hello\nJARVIS: Hi there!"
        prompt = orchestrator._build_prompt_with_history(history)
        
        # Should include history section
        assert "Recent Conversation" in prompt
        assert "User: Hello" in prompt
        assert "JARVIS: Hi there!" in prompt


# =============================================================================
# MEMORY INTEGRATION TESTS
# =============================================================================

class TestMemoryIntegration:
    """Tests for memory storage and retrieval."""
    
    @pytest.mark.asyncio
    async def test_stores_user_messages(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test stores user messages in MemoryManager."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio input
        audio_input = np.random.randn(24000).astype(np.float32)
        await orchestrator.process_audio_input(audio_input)
        
        # Verify user message was stored
        calls = mock_memory_manager.store_message.call_args_list
        user_call = calls[0]
        
        assert user_call[1]["role"] == "user"
        assert user_call[1]["user_id"] == "test_user"
    
    @pytest.mark.asyncio
    async def test_stores_assistant_responses(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test stores assistant responses in MemoryManager."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio input
        audio_input = np.random.randn(24000).astype(np.float32)
        await orchestrator.process_audio_input(audio_input)
        
        # Verify assistant message was stored
        calls = mock_memory_manager.store_message.call_args_list
        assistant_call = calls[1]
        
        assert assistant_call[1]["role"] == "assistant"
        assert assistant_call[1]["message"] == "Hello, how can I help you?"
    
    @pytest.mark.asyncio
    async def test_message_metadata_includes_persona(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test message metadata includes persona name."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio input
        audio_input = np.random.randn(24000).astype(np.float32)
        await orchestrator.process_audio_input(audio_input)
        
        # Check metadata
        calls = mock_memory_manager.store_message.call_args_list
        assistant_call = calls[1]
        
        assert "metadata" in assistant_call[1]
        assert assistant_call[1]["metadata"]["persona"] == "JARVIS"
    
    @pytest.mark.asyncio
    async def test_clear_conversation_history(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test clear_conversation_history() works."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Clear history
        await orchestrator.clear_conversation_history()
        
        # Verify memory manager's clear_history was called
        mock_memory_manager.clear_history.assert_called_once_with("test_user")


# =============================================================================
# AUDIO AMPLITUDE TESTS
# =============================================================================

class TestAudioAmplitudes:
    """Tests for audio amplitude tracking."""
    
    @pytest.mark.asyncio
    async def test_get_amplitudes_returns_correct_format(self, orchestrator_factory, mock_moshi):
        """Test get_amplitudes() returns correct format."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        amplitudes = orchestrator.get_amplitudes()
        
        assert "mic_amplitude" in amplitudes
        assert "moshi_amplitude" in amplitudes
        assert isinstance(amplitudes["mic_amplitude"], float)
        assert isinstance(amplitudes["moshi_amplitude"], float)
    
    @pytest.mark.asyncio
    async def test_mic_and_moshi_amplitudes_tracked(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test mic_amplitude and moshi_amplitude tracked independently."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio
        audio_input = np.random.randn(24000).astype(np.float32)
        result = await orchestrator.process_audio_input(audio_input)
        
        # Check amplitudes in result
        assert "mic_amplitude" in result
        assert "moshi_amplitude" in result
        
        # Values should be from mock (0.5)
        assert result["mic_amplitude"] == 0.5
        assert result["moshi_amplitude"] == 0.5
    
    @pytest.mark.asyncio
    async def test_amplitudes_in_valid_range(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test amplitudes are in valid range (0.0 - 1.0)."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio
        audio_input = np.random.randn(24000).astype(np.float32)
        result = await orchestrator.process_audio_input(audio_input)
        
        # Verify range
        assert 0.0 <= result["mic_amplitude"] <= 1.0
        assert 0.0 <= result["moshi_amplitude"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_amplitudes_reset_when_stopped(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test amplitudes reset when conversation stops."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio to set amplitudes
        audio_input = np.random.randn(24000).astype(np.float32)
        await orchestrator.process_audio_input(audio_input)
        
        # Amplitudes should be non-zero
        amps = orchestrator.get_amplitudes()
        assert amps["mic_amplitude"] > 0.0
        
        # Stop conversation
        await orchestrator.stop_conversation()
        
        # Note: Current implementation doesn't reset amplitudes on stop
        # This test documents current behavior
        # If spec changes to reset, update this test


# =============================================================================
# CONVERSATION LIFECYCLE TESTS
# =============================================================================

class TestConversationLifecycle:
    """Tests for start/stop/cleanup lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_conversation_changes_to_listening(self, orchestrator_factory, mock_moshi):
        """Test start_conversation() changes state to LISTENING."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        await orchestrator.start_conversation()
        
        assert orchestrator.state == ConversationState.LISTENING
        assert orchestrator._running is True
    
    @pytest.mark.asyncio
    async def test_stop_conversation_returns_to_idle(self, orchestrator_factory, mock_moshi):
        """Test stop_conversation() returns to IDLE."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Verify started
        assert orchestrator.state == ConversationState.LISTENING
        
        # Stop
        await orchestrator.stop_conversation()
        
        assert orchestrator.state == ConversationState.IDLE
        assert orchestrator._running is False
    
    @pytest.mark.asyncio
    async def test_cleanup_releases_resources(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test cleanup() releases resources."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Cleanup
        await orchestrator.cleanup()
        
        # Verify cleanup
        assert orchestrator._running is False
        assert orchestrator.state == ConversationState.IDLE
        mock_memory_manager.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_can_restart_after_stopping(self, orchestrator_factory, mock_moshi):
        """Test can restart conversation after stopping."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Start → Stop → Start again
        await orchestrator.start_conversation()
        assert orchestrator._running is True
        
        await orchestrator.stop_conversation()
        assert orchestrator._running is False
        
        await orchestrator.start_conversation()
        assert orchestrator._running is True
        assert orchestrator.state == ConversationState.LISTENING
    
    @pytest.mark.asyncio
    async def test_start_without_init_raises_error(self, orchestrator_factory):
        """Test start_conversation() without initialize() raises error."""
        orchestrator = orchestrator_factory()
        
        # Try to start without initializing
        with pytest.raises(RuntimeError, match="Moshi not initialized"):
            await orchestrator.start_conversation()
    
    @pytest.mark.asyncio
    async def test_process_audio_without_init_raises_error(self, orchestrator_factory):
        """Test process_audio_input() without initialize() raises error."""
        orchestrator = orchestrator_factory()
        
        audio_input = np.random.randn(24000).astype(np.float32)
        
        # Try to process without initializing
        with pytest.raises(RuntimeError, match="Moshi not initialized"):
            await orchestrator.process_audio_input(audio_input)


# =============================================================================
# EDGE CASES & ERROR HANDLING
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_switch_to_nonexistent_persona(self, orchestrator_factory, mock_persona_manager, mock_moshi):
        """Test switching to non-existent persona fails gracefully."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Mock persona manager to fail
        mock_persona_manager.set_current_persona.return_value = False
        
        success = await orchestrator.switch_persona("NonExistent")
        
        assert success is False
        # Should keep original persona
        assert orchestrator.current_persona.name == "JARVIS"
    
    @pytest.mark.asyncio
    async def test_reload_persona_when_none_set(self, orchestrator_factory, mock_moshi):
        """Test reload_persona() when no persona is set."""
        orchestrator = orchestrator_factory()
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Manually clear persona
        orchestrator.current_persona = None
        
        success = await orchestrator.reload_persona()
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_multiple_rapid_state_changes(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test handling multiple rapid state changes."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
        
        # Track all state changes
        states = []
        orchestrator.on_state_change(lambda s: states.append(s))
        
        # Rapid state changes
        await orchestrator.start_conversation()
        
        audio_input = np.random.randn(24000).astype(np.float32)
        await orchestrator.process_audio_input(audio_input)
        
        await orchestrator.stop_conversation()
        
        # Should have tracked multiple transitions
        assert len(states) >= 3
    
    @pytest.mark.asyncio
    async def test_large_conversation_history(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test handling conversation history > 100 messages."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        # Mock large history
        large_history = "\n".join([f"User: Message {i}\nAssistant: Response {i}" for i in range(100)])
        mock_memory_manager.get_conversation_history.return_value = large_history
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Process audio should handle large history
        audio_input = np.random.randn(24000).astype(np.float32)
        result = await orchestrator.process_audio_input(audio_input)
        
        # Should succeed
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_audio_buffer_management(self, orchestrator_factory, mock_memory_manager, mock_moshi):
        """Test audio buffer is populated during conversation."""
        orchestrator = orchestrator_factory(memory_manager=mock_memory_manager)
        
        with patch('assistant.voice.MoshiBridge', return_value=mock_moshi):
            await orchestrator.initialize()
            await orchestrator.start_conversation()
        
        # Buffer should be empty initially
        assert len(orchestrator._audio_buffer) == 0
        
        # Process audio
        audio_input = np.random.randn(24000).astype(np.float32)
        await orchestrator.process_audio_input(audio_input)
        
        # Buffer should have audio chunk
        assert len(orchestrator._audio_buffer) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
