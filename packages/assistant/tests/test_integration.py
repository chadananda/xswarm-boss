"""
Integration tests for voice assistant.
Tests that all components work together.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all modules
from assistant.config import Config
from assistant.personas import PersonaManager
from assistant.memory import MemoryManager, LocalMemoryCache

# Conditionally import modules that may not be available
try:
    from assistant.wake_word import WakeWordDetector
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False

try:
    from assistant.voice.audio_io import AudioIO
    from assistant.voice.vad import VoiceActivityDetector
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class TestPersonaIntegration:
    """Test persona system integration"""

    def test_persona_discovery(self):
        """Test persona discovery from filesystem"""
        # Use project personas directory
        personas_dir = Path(__file__).parent.parent.parent.parent / "personas"

        # Create test personas directory if needed
        test_personas_dir = Path(__file__).parent / "test_personas"
        test_personas_dir.mkdir(exist_ok=True)

        # Create a test persona file
        test_persona_file = test_personas_dir / "test_persona.yaml"
        test_persona_file.write_text("""
name: "Test Assistant"
wake_word: "test"

personality:
  traits:
    - helpful
    - concise
  formality: casual
  humor_level: medium

voice:
  speed: 1.0
  pitch: 1.0

capabilities:
  - general_conversation

system_prompt: "You are a test assistant."
""")

        manager = PersonaManager(test_personas_dir)
        personas = manager.list_personas()

        assert len(personas) > 0, "Should discover at least one persona"
        assert "test_persona" in personas

        # Cleanup
        test_persona_file.unlink()
        test_personas_dir.rmdir()

    def test_persona_loading(self):
        """Test persona loading and configuration"""
        # Create test personas directory
        test_personas_dir = Path(__file__).parent / "test_personas"
        test_personas_dir.mkdir(exist_ok=True)

        # Create a test persona file
        test_persona_file = test_personas_dir / "jarvis.yaml"
        test_persona_file.write_text("""
name: "JARVIS"
wake_word: "jarvis"

personality:
  traits:
    - professional
    - intelligent
  formality: formal
  humor_level: low

voice:
  speed: 1.0
  pitch: 1.0

capabilities:
  - general_conversation
  - calendar_management

system_prompt: "You are JARVIS, an intelligent assistant."
""")

        manager = PersonaManager(test_personas_dir)

        # Get persona
        persona = manager.get_persona("jarvis")

        assert persona is not None
        assert persona.name == "JARVIS"
        assert hasattr(persona, 'personality')
        assert hasattr(persona, 'voice')
        assert persona.wake_word == "jarvis"

        # Cleanup
        test_persona_file.unlink()
        test_personas_dir.rmdir()

    def test_system_prompt_generation(self):
        """Test system prompt generation from persona"""
        # Create test personas directory
        test_personas_dir = Path(__file__).parent / "test_personas"
        test_personas_dir.mkdir(exist_ok=True)

        # Create a test persona file
        test_persona_file = test_personas_dir / "assistant.yaml"
        test_persona_file.write_text("""
name: "Assistant"
wake_word: "assistant"

personality:
  traits:
    - helpful
  formality: casual
  humor_level: medium

voice:
  speed: 1.0
  pitch: 1.0

capabilities:
  - general_conversation

system_prompt: "You are a helpful assistant."
""")

        manager = PersonaManager(test_personas_dir)
        persona = manager.get_persona("assistant")

        prompt = persona.build_system_prompt()
        assert len(prompt) > 0
        assert isinstance(prompt, str)
        assert "helpful assistant" in prompt.lower()

        # Cleanup
        test_persona_file.unlink()
        test_personas_dir.rmdir()


class TestMemoryIntegration:
    """Test memory system integration"""

    def test_local_cache(self):
        """Test local memory cache"""
        cache = LocalMemoryCache()

        # Store messages
        cache.store_message("user-1", "Hello", "user")
        cache.store_message("user-1", "Hi there!", "assistant")

        # Retrieve history
        history = cache.get_history("user-1")
        assert len(history) == 2
        assert history[0]["message"] == "Hello"
        assert history[1]["message"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_memory_manager_offline(self):
        """Test memory manager with server offline"""
        # Use invalid URL to force offline mode
        manager = MemoryManager(server_url="http://localhost:9999")
        await manager.initialize()

        # Should fall back to local cache
        assert manager._server_available == False

        # Store and retrieve should still work
        await manager.store_message("user-1", "Test message", "user")
        context = await manager.get_context("user-1")

        assert len(context) > 0

        await manager.close()


@pytest.mark.skipif(not AUDIO_AVAILABLE, reason="Audio modules not available")
class TestAudioIntegration:
    """Test audio system integration"""

    def test_audio_io_initialization(self):
        """Test AudioIO can be initialized"""
        audio_io = AudioIO(
            sample_rate=16000,
            frame_size=1600,
            channels=1
        )

        assert audio_io.sample_rate == 16000
        assert audio_io.frame_size == 1600

    def test_vad_detection(self):
        """Test Voice Activity Detection"""
        vad = VoiceActivityDetector(threshold=0.02)

        # Silent audio
        silent = np.zeros(1920, dtype=np.float32)
        is_speech = vad.process_frame(silent)
        assert is_speech == False

        # Loud audio (simulated speech)
        loud = np.random.randn(1920).astype(np.float32) * 0.1
        for _ in range(10):  # Need multiple frames to trigger
            is_speech = vad.process_frame(loud)

        # Should eventually detect speech
        assert vad.speech_frames > 0


class TestConfigIntegration:
    """Test configuration system"""

    def test_config_defaults(self):
        """Test default configuration"""
        config = Config()

        assert config.sample_rate == 24000
        assert config.frame_size == 1920
        assert config.device == "auto"
        assert config.wake_word == "jarvis"

    def test_device_detection(self):
        """Test device detection"""
        config = Config()
        device = config.detect_device()

        # Should return valid device
        assert device is not None
        print(f"Detected device: {device}")

    def test_config_with_env_vars(self):
        """Test configuration with environment variables"""
        import os

        # Set test env vars
        os.environ["XSWARM_SERVER_URL"] = "http://test:3000"
        os.environ["XSWARM_API_TOKEN"] = "test-token"

        config = Config()
        config.server_url = os.environ.get("XSWARM_SERVER_URL", "http://localhost:3000")

        assert config.server_url == "http://test:3000"

        # Cleanup
        del os.environ["XSWARM_SERVER_URL"]
        del os.environ["XSWARM_API_TOKEN"]


class TestEndToEndIntegration:
    """Test end-to-end integration scenarios"""

    @pytest.mark.asyncio
    async def test_assistant_initialization(self):
        """Test full assistant initialization"""
        from assistant.main import VoiceAssistant

        config = Config()
        config.memory_enabled = False  # Disable for test

        assistant = VoiceAssistant(config)
        await assistant.initialize()

        # Check components initialized
        assert assistant.config is not None
        assert assistant.persona_manager is not None

        await assistant.cleanup()

    def test_persona_to_config_integration(self):
        """Test persona settings propagate to config"""
        # Create test personas directory
        test_personas_dir = Path(__file__).parent / "test_personas"
        test_personas_dir.mkdir(exist_ok=True)

        # Create a test persona with custom wake word
        test_persona_file = test_personas_dir / "custom.yaml"
        test_persona_file.write_text("""
name: "Custom"
wake_word: "computer"

personality:
  traits:
    - helpful
  formality: casual
  humor_level: medium

voice:
  speed: 1.0
  pitch: 1.0

capabilities:
  - general_conversation

system_prompt: "You are a custom assistant."
""")

        config = Config()
        manager = PersonaManager(test_personas_dir)

        # Get persona
        persona = manager.get_persona("custom")
        assert persona.wake_word == "computer"

        # Wake word should be updatable from persona
        config.wake_word = persona.wake_word
        assert config.wake_word == "computer"

        # Cleanup
        test_persona_file.unlink()
        test_personas_dir.rmdir()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
