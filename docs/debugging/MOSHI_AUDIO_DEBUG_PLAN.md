# MOSHI Audio Debugging Plan - Whisper-Based Testing

## Problem
Audio from MOSHI plays as "1-2 second garbled chunks with 1/2 second pause then the next garbled chunk"

## Attempted Fixes That Failed
- v0.1.0-2025.11.5.9: Buffer sizing changes - still garbled
- v0.1.0-2025.11.5.10: Added `.rev()` reversal - made it worse ("totally garbled")
- v0.1.0-2025.11.5.11: Official MOSHI pattern (push_front + pop_back) - still garbled

## Root Cause Hypothesis
The problem is not buffer ordering but something fundamental in how we're:
1. Processing audio samples from MOSHI
2. Resampling from 24kHz to 44.1kHz
3. Sending samples to CPAL for playback

## Whisper-Based Automated Testing Approach

### Phase 1: Capture Audio Output
1. Modify audio_output.rs to save raw audio to WAV file
2. Capture 5-10 seconds of MOSHI output
3. Save to `./tmp/moshi-test-audio.wav`

### Phase 2: Transcribe with Whisper
1. Use candle-transformers Whisper model (already in dependencies)
2. Transcribe the WAV file
3. Output transcription to see if ANY words are recognizable

### Phase 3: Systematic Testing
Test different audio pipeline configurations:

**Test 1: No resampling (native 24kHz)**
- Skip AudioResampler entirely
- Configure CPAL for 24kHz directly
- See if this produces intelligible audio

**Test 2: Simple FIFO (no reversal)**
- Use `queue.extend(samples.iter())` (add to end)
- Use `queue.pop_front()` (remove from front)
- No push_front, no pop_back, no reversal

**Test 3: Check sample values**
- Log min/max/avg sample values
- Ensure they're in valid f32 range [-1.0, 1.0]
- Check for NaN or Inf values

**Test 4: Verify channel configuration**
- Ensure we're treating audio as mono (MOSHI is mono)
- Check CPAL is configured for mono, not stereo

**Test 5: Bypass rubato entirely**
- Use simple linear interpolation for resampling
- Or use a different resampler

### Phase 4: Iteration Loop
```
for config in [test1, test2, test3, test4, test5]:
    1. Apply configuration
    2. Build and run
    3. Capture audio to WAV
    4. Transcribe with Whisper
    5. Check if transcription contains real words
    6. If YES -> SUCCESS!
    7. If NO -> Try next configuration
```

## Implementation Plan

### Step 1: Add WAV export to audio_output.rs
```rust
// Add WAV writing capability
use hound::{WavWriter, WavSpec};

// In continuous stream, save samples to WAV file
let wav_spec = WavSpec {
    channels: 1,
    sample_rate: 44100,
    bits_per_sample: 32,
    sample_format: hound::SampleFormat::Float,
};
let mut wav_writer = WavWriter::create("./tmp/moshi-test-audio.wav", wav_spec)?;

// Write each sample
for &sample in samples.iter() {
    wav_writer.write_sample(sample)?;
}
```

### Step 2: Create Whisper transcription tool
```rust
// Use candle-transformers Whisper
// Load tiny model for fast testing
// Transcribe WAV file
// Output text
```

### Step 3: Automated test runner script
```bash
#!/bin/bash
# test-moshi-audio.sh

# Build current version
cargo build --release --bin xswarm

# Run xswarm in background
xswarm --dev &
XSWARM_PID=$!

# Wait for audio capture (10 seconds)
sleep 10

# Kill xswarm
kill $XSWARM_PID

# Transcribe with Whisper
cargo run --example transcribe_moshi_audio

# Check results
cat ./tmp/moshi-transcription.txt
```

## Success Criteria
- Whisper transcription contains recognizable English words
- Audio plays smoothly without pauses
- Speech is intelligible when listened to

## Next Actions
1. Add hound crate for WAV export
2. Implement audio capture in audio_output.rs
3. Create Whisper transcription example
4. Run automated test loop
5. Iterate until transcription works

## Files to Modify
1. `packages/core/Cargo.toml` - Add hound dependency
2. `packages/core/src/audio_output.rs` - Add WAV export
3. `packages/core/examples/transcribe_moshi_audio.rs` - Whisper transcription
4. `scripts/test-moshi-audio.sh` - Automated test runner
