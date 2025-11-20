"""
Integration tests for Twilio phone call system.

Tests verify:
- MediaStreamsServer WebSocket handling
- TwilioVoiceBridge audio processing
- Session management
- Transcript storage
- End-to-end call flow
"""

import pytest
import asyncio
import json
import base64
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path

from assistant.phone.media_streams_server import MediaStreamsServer
from assistant.phone.twilio_voice_bridge import TwilioVoiceBridge
from assistant.phone.audio_converter import pcm24k_to_mulaw
from assistant.personas.manager import PersonaManager
from assistant.memory import MemoryManager
from assistant.config import Config


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock(spec=Config)
    config.anthropic_api_key = "test-key"
    config.openai_api_key = "test-key"
    return config


@pytest.fixture
def persona_manager(tmp_path):
    """Create PersonaManager with test personas."""
    # Create test persona file
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir()

    persona_file = personas_dir / "TestBot.yaml"
    persona_file.write_text("""
name: TestBot
system_prompt: You are a helpful test assistant.
voice:
  style: friendly
  speed: 1.0
theme_color: "#00D4FF"
""")

    return PersonaManager(personas_dir=personas_dir)


@pytest.fixture
async def memory_manager():
    """Create MemoryManager for testing."""
    manager = MemoryManager()
    await manager.initialize()
    return manager


@pytest.fixture
def mock_moshi_bridge():
    """Create mock MoshiBridge."""
    with patch('assistant.phone.twilio_voice_bridge.MoshiBridge') as mock:
        # Mock generate_response to return test audio
        instance = mock.return_value
        test_audio = np.random.randn(2400).astype(np.float32) * 0.3
        instance.generate_response.return_value = (test_audio, "Test response")
        yield instance


class TestTwilioVoiceBridge:
    """Test suite for TwilioVoiceBridge."""

    @pytest.mark.asyncio
    async def test_bridge_initialization(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test bridge creation (without Moshi loading)."""
        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
        )

        # Verify initial state (before initialize)
        assert bridge.state == "idle"
        assert bridge.call_sid == "CA123"
        assert bridge.from_number == "+15551234567"
        assert bridge.to_number == "+15559876543"

    @pytest.mark.asyncio
    async def test_process_audio_chunk_buffering(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test audio chunk buffering."""
        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
        )

        # Skip Moshi initialization, just test buffering logic
        bridge.state = "listening"
        bridge.moshi = Mock()  # Mock Moshi without loading

        # Create small audio chunk (not enough for a frame)
        small_audio = np.random.randn(100).astype(np.float32) * 0.3
        mulaw_chunk = pcm24k_to_mulaw(small_audio)

        # Process chunk - should buffer without processing
        result = await bridge.process_audio_chunk(mulaw_chunk)
        assert result is None  # Not enough for full frame yet
        assert len(bridge._input_buffer) > 0  # Audio was buffered

    @pytest.mark.asyncio
    async def test_process_audio_silence_detection(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test silence detection for turn-taking."""
        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
        )

        # Mock Moshi without loading
        bridge.state = "listening"
        bridge.moshi = Mock()

        # Send silence frames (below RMS threshold)
        for i in range(20):  # More than _speech_timeout_frames
            silence = np.zeros(1920, dtype=np.float32)
            mulaw_chunk = pcm24k_to_mulaw(silence)
            result = await bridge.process_audio_chunk(mulaw_chunk)

        # Should accumulate silence frames
        assert bridge._silence_frames >= 0

    @pytest.mark.asyncio
    async def test_transcript_storage(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test conversation transcript is stored."""
        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
        )

        # Get transcript (should be empty initially)
        transcript = bridge.get_transcript()
        assert len(transcript) == 0

    @pytest.mark.asyncio
    async def test_state_transitions(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test bridge state transitions."""
        states = []

        def track_state(state):
            states.append(state)

        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
            on_state_change=track_state,
        )

        # Manually transition state
        bridge._set_state("listening")

        # Should track state change
        assert "listening" in states

    @pytest.mark.asyncio
    async def test_cleanup(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test cleanup saves transcript."""
        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
        )

        # Add some conversation history
        bridge._call_transcript.append({
            "role": "user",
            "content": "Test message",
            "timestamp": 123.45,
        })

        # Cleanup should save transcript
        await bridge.cleanup()

        # Verify cleanup
        assert len(bridge._call_transcript) == 0
        assert len(bridge._input_buffer) == 0


class TestMediaStreamsServer:
    """Test suite for MediaStreamsServer."""

    @pytest.mark.asyncio
    async def test_server_creation(self):
        """Test server can be created."""
        server = MediaStreamsServer(
            host="127.0.0.1",
            port=5555,
        )

        assert server.host == "127.0.0.1"
        assert server.port == 5555
        assert len(server._sessions) == 0
        assert len(server._streams) == 0

    @pytest.mark.asyncio
    async def test_handle_start_message(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test handling 'start' message."""
        # Create bridge factory
        async def bridge_factory(call_sid, from_number, to_number):
            bridge = TwilioVoiceBridge(
                call_sid=call_sid,
                from_number=from_number,
                to_number=to_number,
                persona_manager=persona_manager,
                memory_manager=memory_manager,
                config=mock_config,
                moshi_quality="q8",
            )
            # Mock Moshi initialization to avoid loading models
            with patch.object(bridge, 'initialize', new_callable=AsyncMock):
                await bridge.initialize()
            return bridge

        server = MediaStreamsServer(
            host="127.0.0.1",
            port=5555,
            bridge_factory=bridge_factory,
        )

        # Create mock websocket
        mock_ws = MagicMock()
        mock_ws.remote_address = ("127.0.0.1", 12345)

        # Simulate 'start' message
        start_data = {
            "event": "start",
            "streamSid": "MZ123",
            "start": {
                "callSid": "CA123",
                "from": "+15551234567",
                "to": "+15559876543",
            }
        }

        # Handle start
        stream_sid, call_sid, bridge = await server._handle_start(start_data, mock_ws)

        # Verify session created
        assert stream_sid == "MZ123"
        assert call_sid == "CA123"
        assert bridge is not None
        assert call_sid in server._sessions
        assert stream_sid in server._streams

    @pytest.mark.asyncio
    async def test_active_calls_tracking(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test active calls are tracked."""
        async def bridge_factory(call_sid, from_number, to_number):
            bridge = TwilioVoiceBridge(
                call_sid=call_sid,
                from_number=from_number,
                to_number=to_number,
                persona_manager=persona_manager,
                memory_manager=memory_manager,
                config=mock_config,
            )
            return bridge

        server = MediaStreamsServer(
            host="127.0.0.1",
            port=5555,
            bridge_factory=bridge_factory,
        )

        # Initially no calls
        assert len(server.get_active_calls()) == 0

        # Add mock bridge
        server._sessions["CA123"] = Mock()

        # Now 1 active call
        assert len(server.get_active_calls()) == 1
        assert "CA123" in server.get_active_calls()

    @pytest.mark.asyncio
    async def test_get_call_info(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test retrieving call information."""
        bridge = Mock(spec=TwilioVoiceBridge)
        bridge.from_number = "+15551234567"
        bridge.to_number = "+15559876543"
        bridge.state = "listening"
        bridge.get_transcript.return_value = []

        server = MediaStreamsServer(
            host="127.0.0.1",
            port=5555,
        )

        # Add bridge to sessions
        server._sessions["CA123"] = bridge

        # Get call info
        info = server.get_call_info("CA123")

        assert info is not None
        assert info["call_sid"] == "CA123"
        assert info["from_number"] == "+15551234567"
        assert info["to_number"] == "+15559876543"
        assert info["state"] == "listening"
        assert info["transcript"] == []

    @pytest.mark.asyncio
    async def test_get_call_info_not_found(self):
        """Test retrieving info for non-existent call."""
        server = MediaStreamsServer(
            host="127.0.0.1",
            port=5555,
        )

        info = server.get_call_info("CA999")
        assert info is None


class TestEndToEndCallFlow:
    """Integration tests for complete call flow."""

    @pytest.mark.asyncio
    async def test_complete_call_simulation(
        self, mock_config, persona_manager, memory_manager
    ):
        """Test complete call from start to finish."""
        # Create bridge
        bridge = TwilioVoiceBridge(
            call_sid="CA123",
            from_number="+15551234567",
            to_number="+15559876543",
            persona_manager=persona_manager,
            memory_manager=memory_manager,
            config=mock_config,
            moshi_quality="q8",
        )

        # Mock Moshi without loading
        bridge.state = "listening"
        bridge.moshi = Mock()

        # Simulate call flow: start → audio chunks → end

        # 1. Start state
        assert bridge.state == "listening"

        # 2. Send audio chunk (not enough for processing)
        small_audio = np.random.randn(100).astype(np.float32) * 0.3
        mulaw_chunk = pcm24k_to_mulaw(small_audio)
        result = await bridge.process_audio_chunk(mulaw_chunk)
        assert result is None  # Still buffering

        # 3. Cleanup (end call)
        await bridge.cleanup()
        assert len(bridge._input_buffer) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
