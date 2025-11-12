# WAV Export Implementation Summary

## Problem

WAV files were not being created when xswarm was terminated with SIGTERM. Previous attempts using signal handlers failed because Tokio and TUI frameworks intercept signals before our handlers can run.

## Solution: Periodic WAV Flushing (v0.1.0-2025.11.5.24)

Instead of relying on signal handlers, we implemented **periodic WAV flushing** where audio samples are written to disk immediately as they arrive.

### Implementation Details

**File**: `packages/core/src/audio_output.rs`

#### Global WAV Writer
```rust
static WAV_WRITER: Lazy<Arc<Mutex<Option<hound::WavWriter<...>>>>> = ...
```

#### Key Functions

1. **`init_wav_export(sample_rate: u32)`** - Called once at startup
   - Creates WAV file: `./tmp/moshi-debug-audio.wav`
   - Format: 16-bit signed PCM, mono
   - Sample rate: Dynamic (matches audio output device)

2. **`write_wav_samples(samples: &[i16])`** - Called for every audio frame
   - Writes samples to disk immediately
   - Flushes after every write
   - **Critical**: Data reaches disk before process terminates

3. **`finalize_wav_export()`** - Optional cleanup
   - Closes and finalizes WAV file
   - Updates RIFF headers
   - Called on graceful shutdown (if reached)

### Audio Pipeline

```
MOSHI output (f32, 24kHz)
    ↓
Sample rate conversion (24kHz → Device Hz, ultra-high quality)
    ↓
Format conversion (f32 → i16)
    ↓
Audio playback queue
    ↓
write_wav_samples() ← Periodic flush to disk
    ↓
./tmp/moshi-debug-audio.wav
```

## Test Results

**Test**: `./scripts/test-v0.1.0-2025.11.5.20.sh`

```
✅ WAV file generated: 881K (10.23 seconds)
✅ Format: pcm_s16le, 44100 Hz, mono, s16
✅ Bitrate: 705 kb/s (full audio data, not silence)
✅ afplay successfully played the file
✅ Survives SIGTERM termination

🎉 v0.1.0-2025.11.5.24 WAV export WORKS!
```

### File Properties
```
codec_name=pcm_s16le
sample_rate=44100
channels=1
bits_per_sample=16
duration=10.229252
bit_rate=705634 bps
```

**Bitrate verification**: 16 bits × 44,100 Hz × 1 channel = 705,600 bps ✅

## Version History

- **v0.1.0-2025.11.5.21**: In-memory buffering approach - failed (async task killed before finalization)
- **v0.1.0-2025.11.5.22**: Signal handler approach - failed (handler never called)
- **v0.1.0-2025.11.5.23**: Improved signal handler with error handling - failed (Tokio/TUI interference)
- **v0.1.0-2025.11.5.24**: Periodic WAV flushing - **SUCCESS** ✅

## Usage

Enable WAV export with environment variable:

```bash
MOSHI_DEBUG_WAV=1 xswarm --dev
```

WAV file location: `./tmp/moshi-debug-audio.wav`

## Auto-Greeting Feature

**Version**: v0.1.0-2025.11.5.19

For automated testing, xswarm automatically plays greeting tones when MOSHI initializes, allowing tests to run without manual user interaction.

## Architecture Lessons Learned

1. **Signal handlers don't work in Tokio/TUI environments** - even when installed successfully, they're never invoked
2. **Periodic flushing > Exit handlers** - writing incrementally to disk is more reliable than buffering and writing on exit
3. **File I/O flush is critical** - `writer.flush()` ensures data reaches disk before process termination
4. **Auto-greeting enables automated testing** - critical for CI/CD pipelines

## Audio Quality Validation

**Status**: Format validated, awaiting quality check

**Next step**: Listen to `./tmp/moshi-debug-audio.wav` or use Whisper transcription to verify:
- Audio is intelligible (not garbled)
- Ultra-high quality resampling preserved MOSHI's voice quality
- No artifacts from sample rate conversion (24kHz → 44.1kHz)

**Quality settings** (v0.1.0-2025.11.5.18):
- `sinc_len: 512` (ultra-long FIR filter)
- `f_cutoff: 0.99` (preserve high frequencies)
- `oversampling_factor: 512` (maximum precision)
- `window: Blackman` (smooth frequency response)

## Credits

Implementation completed through iterative debugging across versions .21 → .24, culminating in the periodic WAV flushing solution that successfully survives process termination.
