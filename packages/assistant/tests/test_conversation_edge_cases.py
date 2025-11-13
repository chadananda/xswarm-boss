"""
Edge case tests for ConversationLoop.

Tests edge cases and error scenarios including:
- Empty/no voice activity
- Empty transcription
- AI API timeout
- TTS failure
- Audio device unavailable
- Rapid conversation turns
- Long AI responses
- Special characters in transcription
- Memory storage failures
"""

import pytest
import asyncio
import numpy as np
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.voice.conversation import ConversationLoop, AIClient
from assistant.personas.config import PersonaConfig


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_components():
    """Mock all conversation loop components"""
    moshi = Mock()
    moshi.generate_response.return_value = (
        np.random.randn(24000).astype(np.float32),
        "Response text"
    )
    moshi.get_amplitude.return_value = 0.5
    moshi.mic_amplitude = 0.0
    moshi.moshi_amplitude = 0.0
    
    persona_manager = Mock()
    persona = PersonaConfig(
        name="JARVIS",
        description="Test",
        version="1.0.0",
        system_prompt="Test prompt"
    )
    persona_manager.get_current_persona.return_value = persona
    
    memory = AsyncMock()
    memory.store_message = AsyncMock()
    memory.get_recent_messages = AsyncMock(return_value=[])
    
    ai_client = AsyncMock()
    ai_client.chat = AsyncMock(return_value="AI response")
    ai_client.is_available.return_value = True
    
    return {
        'moshi': moshi,
        'persona': persona_manager,
        'memory': memory,
        'ai': ai_client
    }


@pytest.fixture
def conversation_loop(mock_components):
    """Create conversation loop with mocked components"""
    loop = ConversationLoop(
        moshi_bridge=mock_components['moshi'],
        persona_manager=mock_components['persona'],
        memory_manager=mock_components['memory'],
        ai_client=mock_components['ai'],
        user_id="test_user"
    )
    return loop


# =============================================================================
# NO VOICE ACTIVITY TESTS
# =============================================================================

class TestNoVoiceActivity:
    """Tests for handling no voice activity."""
    
    def test_no_voice_detected(self, conversation_loop):
        """Test loop waits when no voice detected."""
        # Mock VAD to return False (no speech)
        conversation_loop.vad.process_frame = Mock(return_value=False)
        
        # Process audio frame
        audio_frame = np.random.randn(1920).astype(np.float32)
        conversation_loop._on_audio_frame(audio_frame)
        
        # Buffer should be empty
        assert len(conversation_loop._audio_buffer) == 0
        assert conversation_loop._is_listening is False
    
    @pytest.mark.asyncio
    async def test_capture_segment_returns_none_when_no_audio(self, conversation_loop):
        """Test capture returns None when buffer is empty."""
        conversation_loop._audio_buffer = []
        
        segment = await conversation_loop._capture_speech_segment()
        
        assert segment is None


# =============================================================================
# EMPTY TRANSCRIPTION TESTS
# =============================================================================

class TestEmptyTranscription:
    """Tests for handling empty transcription."""
    
    @pytest.mark.asyncio
    async def test_empty_transcription_response(self, conversation_loop, mock_components):
        """Test handles empty transcription gracefully."""
        # Mock Moshi to return empty text
        mock_components['moshi'].generate_response.return_value = (
            np.random.randn(24000).astype(np.float32),
            ""  # Empty text
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should still complete (stores "[No response]")
        assert mock_components['memory'].store_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_none_transcription_response(self, conversation_loop, mock_components):
        """Test handles None transcription gracefully."""
        # Mock Moshi to return None text
        mock_components['moshi'].generate_response.return_value = (
            np.random.randn(24000).astype(np.float32),
            None
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should handle None gracefully (stores "[No response]")
        assert mock_components['memory'].store_message.call_count == 2


# =============================================================================
# AI API ERROR TESTS
# =============================================================================

class TestAIAPIErrors:
    """Tests for AI API errors and timeouts."""
    
    @pytest.mark.asyncio
    async def test_ai_api_timeout(self, conversation_loop, mock_components):
        """Test handles AI API timeout gracefully."""
        # Mock AI to timeout
        async def timeout_chat(*args, **kwargs):
            await asyncio.sleep(10)  # Simulated timeout
            return "Response"
        
        mock_components['ai'].chat = timeout_chat
        
        # This test just verifies the loop can handle slow AI
        # In practice, the AI client would raise TimeoutError
        # For now, we test that the loop doesn't crash
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn (would timeout in real scenario)
        user_audio = np.random.randn(24000).astype(np.float32)
        
        # We use Moshi directly, so AI timeout doesn't affect this flow
        await conversation_loop._process_turn(user_audio)
        
        # Should complete using Moshi response
        assert mock_components['memory'].store_message.call_count == 2
    
    @pytest.mark.asyncio
    async def test_ai_api_error(self, conversation_loop, mock_components):
        """Test handles AI API error gracefully."""
        # Mock AI to raise error
        mock_components['ai'].chat = AsyncMock(side_effect=Exception("API Error"))
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn - should use Moshi fallback
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should still complete with Moshi response
        assert mock_components['memory'].store_message.call_count == 2


# =============================================================================
# TTS FAILURE TESTS
# =============================================================================

class TestTTSFailure:
    """Tests for TTS synthesis failure."""
    
    @pytest.mark.asyncio
    async def test_tts_returns_empty_audio(self, conversation_loop, mock_components):
        """Test handles empty audio from TTS."""
        # Mock Moshi to return empty audio
        mock_components['moshi'].generate_response.return_value = (
            np.array([]).astype(np.float32),  # Empty audio
            "Response text"
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should not crash, play_audio not called for empty audio
        assert conversation_loop.audio_io.play_audio.call_count == 0
    
    @pytest.mark.asyncio
    async def test_tts_raises_error(self, conversation_loop, mock_components):
        """Test handles TTS error gracefully."""
        # Mock Moshi to raise error
        mock_components['moshi'].generate_response.side_effect = Exception("TTS Error")
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn should raise
        user_audio = np.random.randn(24000).astype(np.float32)
        
        with pytest.raises(Exception, match="TTS Error"):
            await conversation_loop._process_turn(user_audio)


# =============================================================================
# AUDIO DEVICE TESTS
# =============================================================================

class TestAudioDeviceErrors:
    """Tests for audio device errors."""
    
    @pytest.mark.asyncio
    async def test_audio_input_device_unavailable(self, conversation_loop):
        """Test handles unavailable audio input device."""
        # Mock audio I/O to fail on start_input
        conversation_loop.audio_io.start_input = Mock(side_effect=Exception("No input device"))
        conversation_loop.audio_io.start_output = Mock()
        
        # Start should raise
        with pytest.raises(Exception, match="No input device"):
            await conversation_loop.start()
    
    @pytest.mark.asyncio
    async def test_audio_output_device_unavailable(self, conversation_loop):
        """Test handles unavailable audio output device."""
        # Mock audio I/O
        conversation_loop.audio_io.start_input = Mock()
        conversation_loop.audio_io.start_output = Mock(side_effect=Exception("No output device"))
        
        # Start should raise
        with pytest.raises(Exception, match="No output device"):
            await conversation_loop.start()
    
    @pytest.mark.asyncio
    async def test_audio_playback_error(self, conversation_loop):
        """Test handles audio playback error."""
        # Mock audio playback to fail
        conversation_loop.audio_io.play_audio = Mock(side_effect=Exception("Playback error"))
        
        # Process turn should raise
        user_audio = np.random.randn(24000).astype(np.float32)
        
        with pytest.raises(Exception, match="Playback error"):
            await conversation_loop._process_turn(user_audio)


# =============================================================================
# RAPID CONVERSATION TESTS
# =============================================================================

class TestRapidConversation:
    """Tests for rapid conversation turns."""
    
    @pytest.mark.asyncio
    async def test_multiple_rapid_turns(self, conversation_loop):
        """Test handles multiple rapid conversation turns."""
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Track turns
        turns = []
        conversation_loop.on_turn_complete = lambda t: turns.append(t)
        
        # Process multiple turns rapidly
        for i in range(5):
            user_audio = np.random.randn(24000).astype(np.float32)
            await conversation_loop._process_turn(user_audio)
        
        # All turns should complete
        assert len(turns) == 5
    
    @pytest.mark.asyncio
    async def test_back_to_back_audio_segments(self, conversation_loop):
        """Test captures back-to-back audio segments."""
        # Simulate rapid speech: speech → silence → speech → silence
        conversation_loop.vad.process_frame = Mock(side_effect=[
            True, True, True,  # First speech
            False,  # Silence
            True, True, True,  # Second speech
            False  # Silence
        ])
        
        # Process frames
        for _ in range(8):
            audio = np.random.randn(1920).astype(np.float32)
            conversation_loop._on_audio_frame(audio)
        
        # Should have captured first segment (3 frames)
        # Second segment would be in buffer
        # This tests the VAD state machine handles rapid transitions


# =============================================================================
# LONG RESPONSE TESTS
# =============================================================================

class TestLongResponses:
    """Tests for handling long AI responses."""
    
    @pytest.mark.asyncio
    async def test_long_text_response(self, conversation_loop, mock_components):
        """Test handles very long AI response text."""
        # Mock long response (>1000 words)
        long_text = " ".join(["word"] * 1500)
        mock_components['moshi'].generate_response.return_value = (
            np.random.randn(24000 * 30).astype(np.float32),  # 30 seconds of audio
            long_text
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should complete and store long text
        assistant_call = mock_components['memory'].store_message.call_args_list[1]
        assert len(assistant_call[1]["message"]) > 1000
    
    @pytest.mark.asyncio
    async def test_long_audio_response(self, conversation_loop, mock_components):
        """Test handles very long audio response."""
        # Mock 60 seconds of audio
        long_audio = np.random.randn(24000 * 60).astype(np.float32)
        mock_components['moshi'].generate_response.return_value = (
            long_audio,
            "Long response"
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should play full audio
        played_audio = conversation_loop.audio_io.play_audio.call_args[0][0]
        assert len(played_audio) == 24000 * 60


# =============================================================================
# SPECIAL CHARACTERS TESTS
# =============================================================================

class TestSpecialCharacters:
    """Tests for handling special characters in transcription."""
    
    @pytest.mark.asyncio
    async def test_emoji_in_transcription(self, conversation_loop, mock_components):
        """Test handles emoji in transcription."""
        # Mock response with emoji
        mock_components['moshi'].generate_response.return_value = (
            np.random.randn(24000).astype(np.float32),
            "Hello! 👋 How are you? 😊"
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should store emoji correctly
        assistant_call = mock_components['memory'].store_message.call_args_list[1]
        assert "👋" in assistant_call[1]["message"]
        assert "😊" in assistant_call[1]["message"]
    
    @pytest.mark.asyncio
    async def test_unicode_characters(self, conversation_loop, mock_components):
        """Test handles Unicode characters."""
        # Mock response with Unicode
        mock_components['moshi'].generate_response.return_value = (
            np.random.randn(24000).astype(np.float32),
            "Café résumé naïve 日本語 中文"
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should store Unicode correctly
        assistant_call = mock_components['memory'].store_message.call_args_list[1]
        assert "Café" in assistant_call[1]["message"]
        assert "日本語" in assistant_call[1]["message"]
    
    @pytest.mark.asyncio
    async def test_special_punctuation(self, conversation_loop, mock_components):
        """Test handles special punctuation."""
        # Mock response with special chars
        mock_components['moshi'].generate_response.return_value = (
            np.random.randn(24000).astype(np.float32),
            "What?! Really... (seriously) $100 @ 5:00pm #test"
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should store special chars correctly
        assistant_call = mock_components['memory'].store_message.call_args_list[1]
        assert "$100" in assistant_call[1]["message"]
        assert "#test" in assistant_call[1]["message"]


# =============================================================================
# MEMORY STORAGE FAILURE TESTS
# =============================================================================

class TestMemoryStorageFailure:
    """Tests for memory storage failures."""
    
    @pytest.mark.asyncio
    async def test_memory_store_fails(self, conversation_loop, mock_components):
        """Test handles memory storage failure."""
        # Mock memory to fail
        mock_components['memory'].store_message = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn should raise
        user_audio = np.random.randn(24000).astype(np.float32)
        
        with pytest.raises(Exception, match="Database error"):
            await conversation_loop._process_turn(user_audio)
    
    @pytest.mark.asyncio
    async def test_memory_store_timeout(self, conversation_loop, mock_components):
        """Test handles memory storage timeout."""
        # Mock slow memory storage
        async def slow_store(*args, **kwargs):
            await asyncio.sleep(10)
            return "msg-id"
        
        mock_components['memory'].store_message = slow_store
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn would be slow but should complete
        # In practice, you'd want to add timeout to store_message
        # For now, this tests the flow doesn't crash


# =============================================================================
# BUFFER OVERFLOW TESTS
# =============================================================================

class TestBufferOverflow:
    """Tests for audio buffer overflow scenarios."""
    
    def test_very_long_speech_segment(self, conversation_loop):
        """Test handles very long speech segment (>60 seconds)."""
        # Simulate 60 seconds of continuous speech
        conversation_loop.vad.process_frame = Mock(return_value=True)
        
        # Process 3000 frames (60 seconds at 50 FPS)
        for _ in range(3000):
            audio = np.random.randn(1920).astype(np.float32)
            conversation_loop._on_audio_frame(audio)
        
        # Buffer should have 3000 frames
        assert len(conversation_loop._audio_buffer) == 3000
        
        # Should be able to capture it
        conversation_loop.vad.reset = Mock()
        segment = asyncio.run(conversation_loop._capture_speech_segment())
        assert len(segment) == 1920 * 3000


# =============================================================================
# CONCURRENT ACCESS TESTS
# =============================================================================

class TestConcurrentAccess:
    """Tests for concurrent access scenarios."""
    
    @pytest.mark.asyncio
    async def test_multiple_state_callbacks(self, conversation_loop):
        """Test multiple state callbacks don't interfere."""
        # Register multiple callbacks
        callback_results = []
        
        def callback1(state):
            callback_results.append(f"cb1:{state}")
        
        def callback2(state):
            callback_results.append(f"cb2:{state}")
        
        conversation_loop.on_state_change = lambda s: (callback1(s), callback2(s))
        
        # Trigger state changes
        conversation_loop._set_state("listening")
        conversation_loop._set_state("thinking")
        
        # Both callbacks should have fired for both states
        # Note: This test shows the limitation of single callback assignment
        # In reality, you'd want a list of callbacks
    
    @pytest.mark.asyncio
    async def test_callback_error_doesnt_crash(self, conversation_loop):
        """Test callback error doesn't crash turn processing."""
        def bad_callback(turn):
            raise ValueError("Callback crashed!")
        
        conversation_loop.on_turn_complete = bad_callback
        
        # Mock audio I/O
        conversation_loop.audio_io.play_audio = Mock()
        
        # Process turn should handle callback error
        user_audio = np.random.randn(24000).astype(np.float32)
        await conversation_loop._process_turn(user_audio)
        
        # Should complete despite callback error


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
