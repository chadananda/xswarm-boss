# Voice Tests

This directory contains tests for the **Moshi voice** and audio processing components.

## Test Files

- `test_voice_bridge.py` - Tests for the voice bridge orchestrator
- `test_audio_converter.py` - Tests for audio format conversion
- `test_audio_functionality.py` - Tests for audio I/O and processing
- `test_common_wake_words.py` - Tests for wake word detection
- `test_multi_wake_words.py` - Tests for multiple wake word support
- `test_voice_app_integration.py` - Integration tests for voice app

## Running Tests

```bash
# Run all voice tests
pytest packages/assistant/tests/voice/

# Run specific test file
pytest packages/assistant/tests/voice/test_voice_bridge.py -v
```

## Documentation

See `README_AUDIO_TESTS.md` in this directory for detailed audio testing information.
