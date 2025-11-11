# Audio Functionality Test Suite

## Overview

`test_audio_functionality.py` is a comprehensive test suite that verifies the complete audio pipeline for the xSwarm assistant, ensuring microphone input, audio output, and Moshi integration are working correctly.

## What It Tests

### 1. AudioIO Initialization
- Verifies AudioIO class can be instantiated with correct parameters
- Checks sample rate (24kHz), frame size (1920 samples), and channel configuration
- Validates input/output queue initialization

### 2. Microphone Input Stream
- Tests that microphone input stream starts without errors
- Captures 1 second of audio frames from the microphone
- Verifies frame shape and properties
- Validates callback mechanism for real-time processing

### 3. Amplitude Detection
- Tests amplitude calculation for audio visualization
- Validates that amplitude levels correctly distinguish between:
  - Silent audio (0.0)
  - Quiet audio (~0.01)
  - Loud audio (~0.5)
- Tests both mean absolute value and RMS amplitude methods

### 4. Moshi Integration
- Detects best available compute device (MPS/CUDA/CPU)
- Attempts to import Moshi module (gracefully skips if not installed)
- Reports GPU acceleration status

### 5. Audio Output Stream
- Tests audio output playback functionality
- Generates a 440Hz test tone (musical note A)
- Queues audio for playback through speakers/headphones
- Verifies output stream starts and completes without errors

### 6. Full Integration Test
- Tests complete pipeline: microphone → processing → output
- Runs both input and output streams simultaneously for 2 seconds
- Validates frame rate (~25 frames/sec at 24kHz with 1920 samples/frame)
- Tests real-time audio processing callback

### 7. Read Frame Method
- Tests queue-based frame reading (alternative to callbacks)
- Validates blocking/timeout behavior
- Verifies frame buffering

## Running the Tests

```bash
# From the packages/assistant directory
python tests/test_audio_functionality.py
```

## Expected Output

```
======================================================================
AUDIO FUNCTIONALITY TEST SUITE
======================================================================

=== TEST 1: AudioIO Initialization ===
✓ AudioIO initialized successfully
  Sample rate: 24000Hz
  Frame size: 1920 samples
  Channels: 1
✓ All attributes verified

... (more tests) ...

======================================================================
TEST RESULTS SUMMARY
======================================================================
✓ PASS: AudioIO Initialization
✓ PASS: Microphone Input
✓ PASS: Amplitude Detection
✓ PASS: Moshi Integration
✓ PASS: Audio Output
✓ PASS: Full Integration
✓ PASS: Read Frame Method
======================================================================
✅ ALL AUDIO TESTS PASSED!

Audio system is working correctly:
  • Microphone input: ✓
  • Audio output: ✓
  • Amplitude detection: ✓
  • Frame processing: ✓
  • Moshi integration: ✓
======================================================================
```

## Requirements

- **sounddevice**: Cross-platform audio I/O library
- **numpy**: Audio data processing
- **torch**: Device detection (MPS/CUDA/CPU)
- **Working microphone**: System microphone access required
- **Working speakers/headphones**: Audio output required

## Troubleshooting

### No audio frames captured
- Check microphone permissions in system settings
- Verify microphone is not being used by another application
- Run `python -m sounddevice` to list available audio devices

### Audio output test fails
- Check speaker/headphone volume
- Verify audio output device is selected in system settings
- Check if audio device is in use by another application

### Moshi integration test fails
- This is expected if Moshi is not installed yet
- Test will SKIP gracefully and still pass
- To install Moshi, follow instructions in project documentation

### Frame rate lower than expected
- High CPU usage from other applications can affect frame rate
- GPU acceleration (MPS/CUDA) recommended for best performance
- Test still passes with 80% tolerance (20/25 frames acceptable)

## Technical Details

### Audio Configuration
- **Sample Rate**: 24,000 Hz (24kHz) - optimized for Moshi model
- **Frame Size**: 1,920 samples = 80ms of audio at 24kHz
- **Channels**: 1 (mono)
- **Frame Rate**: ~25 frames per second (1920 samples / 24000 Hz)

### Amplitude Calculation
Two methods are tested:
1. **Mean Absolute Amplitude**: `np.abs(audio).mean()`
2. **RMS Amplitude**: `np.sqrt(np.mean(audio**2))`

Both methods are used in the voice visualizer for real-time audio level display.

### Device Detection Priority
1. **CUDA/ROCm** (NVIDIA/AMD GPUs) - best for Moshi inference
2. **MPS** (Apple Metal on M-series chips) - good for Moshi inference
3. **CPU** (fallback) - works but slow for Moshi

## Integration with xSwarm Assistant

This test validates the core audio pipeline used by:
- **Voice Visualizer**: Real-time amplitude detection and waveform display
- **Wake Word Detection**: Microphone input stream processing
- **Moshi Voice Assistant**: Audio I/O for voice conversations
- **Audio Feedback**: System sounds and TTS output

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed
- **130**: Tests interrupted by user (Ctrl+C)

## Contributing

When adding new audio features, update this test suite to include:
1. New test function following the naming convention `test_*`
2. Add test to `run_all_tests()` results list
3. Update this README with test description
4. Ensure test can run independently of Moshi installation

---

**Last Updated**: 2025-11-11
**Test Count**: 7 tests
**Coverage**: AudioIO, amplitude detection, device detection, integration

## Quick Start

```bash
# Run the full audio test suite
python tests/test_audio_functionality.py

# Expected runtime: ~5-6 seconds
# Expected result: All 7 tests should pass
```

## What Gets Tested

1. ✓ **AudioIO can initialize** with correct configuration
2. ✓ **Microphone captures audio** for 1 second
3. ✓ **Amplitude detection works** for visualizer
4. ✓ **Device detection** finds MPS/CUDA/CPU correctly
5. ✓ **Audio output plays** a test tone
6. ✓ **Full pipeline** processes mic input → output for 2 seconds
7. ✓ **Frame reading** from queue works with timeouts

## CI/CD Integration

This test can be run in CI/CD pipelines with audio devices:

```yaml
# Example GitHub Actions
- name: Test Audio Functionality
  run: python tests/test_audio_functionality.py
```

**Note**: CI environments without audio devices will fail tests 2, 5, 6, and 7. Consider skipping these tests in headless CI environments by checking for audio device availability.

## See Also

- **AudioIO Documentation**: `assistant/voice/audio_io.py`
- **Voice Visualizer**: `assistant/dashboard/widgets/voice_visualizer.py`
- **Moshi Integration**: `assistant/voice/moshi_pytorch.py`
- **Config System**: `assistant/config.py`

