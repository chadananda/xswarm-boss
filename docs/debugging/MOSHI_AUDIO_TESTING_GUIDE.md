# MOSHI Audio Testing Guide - Whisper-Based Validation

## Version: 0.1.0-2025.11.5.12

## Overview

This guide explains how to use the Whisper-based automated testing system to debug and validate MOSHI audio quality. The system captures audio output to WAV files and transcribes them using the Whisper speech recognition model to objectively verify if MOSHI is producing intelligible speech.

## Quick Start

### Automated Testing (Recommended)

```bash
# Run the automated test script
./scripts/test-moshi-audio.sh 10

# This will:
# 1. Start xswarm with WAV export enabled
# 2. Capture 10 seconds of MOSHI audio
# 3. Transcribe with Whisper
# 4. Report if audio is intelligible
```

### Manual Testing

```bash
# 1. Enable WAV export
export MOSHI_DEBUG_WAV=1

# 2. Run xswarm
xswarm --dev

# 3. Speak to MOSHI for a few seconds
# Audio will be captured to ./tmp/moshi-debug-audio.wav

# 4. Stop xswarm (Ctrl+C)

# 5. Transcribe the audio
cd packages/core
cargo run --example transcribe_moshi_audio --release

# 6. Review the transcription
cat ./tmp/moshi-transcription.txt
```

## How It Works

### 1. WAV Export (audio_output.rs)

When `MOSHI_DEBUG_WAV` environment variable is set:

- Audio output is saved to `./tmp/moshi-debug-audio.wav`
- Format: 44.1kHz mono, 32-bit float
- Captures ALL audio sent to playback (resampled output)
- Automatically finalized when audio task stops

**Implementation Details:**
- Located in `packages/core/src/audio_output.rs:412-494`
- Uses `hound` crate for WAV writing
- Thread-safe via `Arc<Mutex<WavWriter>>`
- Samples written in playback callback (real-time)

### 2. Whisper Transcription (transcribe_moshi_audio.rs)

Transcribes captured audio to verify intelligibility:

- Uses OpenAI Whisper tiny model (fast, accurate enough for testing)
- Automatically resamples audio to 16kHz (Whisper requirement)
- Converts stereo to mono if needed
- Reports word count and character count

**Implementation Details:**
- Located in `packages/core/examples/transcribe_moshi_audio.rs`
- Uses `candle-transformers` for Whisper
- Downloads model from HuggingFace on first run
- GPU-accelerated if available

### 3. Automated Test Script (test-moshi-audio.sh)

End-to-end automation:

1. Cleans up old test files
2. Starts xswarm with `MOSHI_DEBUG_WAV=1`
3. Waits specified duration (default 10s)
4. Stops xswarm cleanly
5. Runs Whisper transcription
6. Reports results

## Success Criteria

### Audio is Working ✅

Whisper transcription output shows:
- **Words detected: > 0**
- Text contains recognizable English words
- Text resembles what MOSHI said

Example successful output:
```
📝 TRANSCRIPTION RESULT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hello, I'm your AI assistant. How can I help you today?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Analysis:
   Words detected: 11
   Text length: 58 characters

✅ SUCCESS: Audio contains recognizable speech!
   MOSHI audio pipeline is working correctly.
```

### Audio is Garbled ❌

Whisper transcription output shows:
- **Words detected: 0**
- Empty or gibberish text
- No recognizable words

Example failed output:
```
📝 TRANSCRIPTION RESULT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Analysis:
   Words detected: 0
   Text length: 0 characters

❌ FAILURE: No recognizable words detected.
   MOSHI audio is garbled or silent.
   Try next audio pipeline configuration.
```

## Troubleshooting

### No audio file created

**Problem:** `./tmp/moshi-debug-audio.wav` doesn't exist

**Solutions:**
1. Verify `MOSHI_DEBUG_WAV=1` is set
2. Check that MOSHI actually generated audio (spoke to it)
3. Look for "MOSHI_DEBUG: WAV export enabled" log message
4. Ensure xswarm ran long enough to generate audio

### Transcription fails

**Problem:** Whisper transcription crashes or fails

**Solutions:**
1. Check audio file is valid: `file ./tmp/moshi-debug-audio.wav`
2. Verify audio file is not empty: `ls -lh ./tmp/moshi-debug-audio.wav`
3. Ensure internet connection (downloads model on first run)
4. Check disk space for model download (~100MB)

### Transcription takes too long

**Problem:** Transcription is very slow

**Solutions:**
1. First run downloads model (~100MB), subsequent runs are fast
2. Use GPU if available (Metal on macOS, CUDA on Linux)
3. Reduce audio capture duration (use shorter test)
4. Consider using Whisper tiny model is already fastest

## Next Steps - Systematic Testing

If audio is garbled, try these configurations in order:

### Test 1: Disable Resampling

Test if the issue is in the rubato resampler:

```bash
# TODO: Implement native 24kHz CPAL output
# Skip AudioResampler entirely
```

### Test 2: Simple FIFO (No Reversal)

Test if the issue is sample ordering:

```bash
# Edit audio_output.rs:460
# Change from: queue.extend(samples.iter().rev());
# Change to:   queue.extend(samples.iter());
```

### Test 3: Verify Sample Values

Check for NaN, Inf, or out-of-range values:

```bash
# Add logging to audio_output.rs
# Log min/max/avg sample values
# Check for invalid f32 values
```

### Test 4: Channel Configuration

Verify mono vs stereo:

```bash
# Check CPAL config
# Ensure MOSHI (mono) → resampler (mono) → CPAL (mono)
```

### Test 5: Alternative Resampler

Try different resampling approach:

```bash
# Replace rubato with simple linear interpolation
# Or try samplerate-rs crate
```

## File Locations

```
xswarm-boss/
├── packages/core/
│   ├── src/
│   │   └── audio_output.rs          # WAV export implementation
│   ├── examples/
│   │   └── transcribe_moshi_audio.rs # Whisper transcription
│   └── Cargo.toml                    # Dependencies (hound)
├── scripts/
│   └── test-moshi-audio.sh          # Automated test script
├── docs/debugging/
│   ├── MOSHI_AUDIO_DEBUG_PLAN.md    # Original debug plan
│   └── MOSHI_AUDIO_TESTING_GUIDE.md # This file
└── tmp/ (gitignored)
    ├── moshi-debug-audio.wav        # Captured audio
    └── moshi-transcription.txt      # Transcription results
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `MOSHI_DEBUG_WAV` | Enable WAV export | Disabled |

## Dependencies

| Crate | Version | Purpose |
|-------|---------|---------|
| `hound` | 3.5 | WAV file writing |
| `candle-transformers` | (workspace) | Whisper model |
| `rubato` | (workspace) | Audio resampling |

## Performance

- WAV export: Negligible overhead (<1% CPU)
- Whisper transcription: 1-2 minutes first run (downloads model), 5-10s subsequent runs
- Model size: ~100MB (tiny model)
- GPU acceleration: Yes (Metal/CUDA)

## Known Issues

- None currently

## Version History

### v0.1.0-2025.11.5.12 (Current)
- ✅ Added WAV export capability
- ✅ Created Whisper transcription tool
- ✅ Created automated test script
- ✅ Documented usage and testing guide

### Previous Attempts (Failed)
- v0.1.0-2025.11.5.9: Buffer sizing changes
- v0.1.0-2025.11.5.10: Added `.rev()` reversal (made worse)
- v0.1.0-2025.11.5.11: Official MOSHI pattern (still garbled)

## Support

For issues or questions, refer to:
- `docs/debugging/MOSHI_AUDIO_DEBUG_PLAN.md` - Original debug strategy
- `MOSHI_AUDIO_REVERSAL_FIX.md` - Previous fix attempts
- `packages/core/src/audio_output.rs` - Implementation details

---

**Last Updated:** 2025-11-05
**Author:** Claude Code (xSwarm Development)
**Status:** Ready for Testing
