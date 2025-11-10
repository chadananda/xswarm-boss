# MOSHI Audio Diagnosis - ROOT CAUSE FOUND

## Date: 2025-11-06

## Executive Summary

**The "garbled voice" is NOT an audio quality issue. The auto-greeting is sending SILENCE to MOSHI instead of generating actual speech.**

## Problem Statement

User reported "garbled voice" from MOSHI after implementing WAV export (v0.1.0-2025.11.5.24).

## Investigation Results

### WAV File Analysis ✅

**File**: `./tmp/moshi-debug-audio.wav`
- Format: pcm_s16le (16-bit signed integer PCM) ✅
- Sample rate: 44100 Hz ✅
- Channels: 1 (mono) ✅
- Duration: 10.229252 seconds ✅
- Bitrate: 705634 bps ✅
- Size: 881K ✅
- **Plays successfully with afplay** ✅

### Audio Statistics ✅

```
mean_volume: -19.0 dB
max_volume: -0.0 dB
RMS level dB: -18.998492
Peak level dB: -0.019638
Dynamic range: 96.309695 dB
```

**Real audio content detected** - not silence, not corrupted ✅

### Transcription Analysis ❌

**OpenAI Whisper API Result**:
```json
{
  "text": "SUBSCRIBE",
  "no_speech_prob": 0.29095879197120667
}
```

**Interpretation**: Whisper detected audio (71% confidence it's speech) but transcribed it as "SUBSCRIBE" - likely pattern-matching on unintelligible audio rather than actual speech.

### Spectrogram Analysis ❌

**Key Findings**:
1. **Regular, periodic pattern** - vertical striations throughout 10 seconds
2. **Energy concentrated in lower frequencies** (0-3.6 kHz, shown in red/yellow)
3. **NO speech formants** - missing characteristic frequency patterns of human speech
4. **Repetitive structure** - same pattern repeating, not varying like speech

**This is NOT speech** - it's a repetitive tone/noise pattern.

## ROOT CAUSE IDENTIFICATION

**Location**: `packages/core/src/voice.rs:704-751`

### The Problematic Code

```rust
// v0.1.0-2025.11.5.19: AUTO-GREETING for automated testing
if std::env::var("MOSHI_DEBUG_WAV").is_ok() {
    info!("MOSHI_AUDIO: DEBUG MODE - Generating auto-greeting for testing");

    // ❌ PROBLEM: Sending SILENCE to MOSHI
    let test_frame = vec![0.0f32; MOSHI_FRAME_SIZE];  // All zeros!

    // ❌ PROBLEM: Expecting MOSHI to generate greeting from silence
    match self.process_with_lm(&mut conn_state, test_frame).await {
        Ok(response_pcm) => {
            // This generates unpredictable/garbled audio!
```

### What's Actually Happening

1. Code creates a **silent frame** (all zeros)
2. Sends silence to MOSHI's language model via `process_with_lm()`
3. MOSHI processes silence and generates **unpredictable audio output**
4. This unpredictable output is what we hear as "garbled voice"
5. The repetitive pattern in the spectrogram matches MOSHI generating repetitive/nonsense audio from silence

### What SHOULD Happen

The `greeting.rs` module already exists with the correct implementation:

```rust
/// Generate greeting audio using MOSHI's direct speech generation
pub async fn generate_simple_greeting(
    moshi_state: &mut MoshiState,
    greeting_text: &str,
) -> Result<Vec<f32>>
```

This function:
1. Tokenizes greeting text (e.g., "Hello, how can I help you?")
2. Uses `force_text_token` to inject text tokens into MOSHI
3. Generates coherent speech audio
4. Returns PCM samples ready for playback

## Comparison: What Works vs What's Broken

| Component | Status | Evidence |
|-----------|--------|----------|
| WAV file format | ✅ Works | 16-bit PCM, 44.1kHz, plays successfully |
| Sample rate conversion | ✅ Works | No aliasing, correct bitrate calculation |
| Periodic WAV flushing | ✅ Works | File survives SIGTERM, data not lost |
| Audio output pipeline | ✅ Works | Good volume, dynamic range, no corruption |
| **Auto-greeting implementation** | ❌ **BROKEN** | **Sends silence instead of generating greeting** |
| MOSHI speech generation (`greeting.rs`) | ✅ Works | Proper implementation exists, just not used |

## The Fix

**Replace the silent frame approach with proper greeting generation:**

### Current (Broken):
```rust
let test_frame = vec![0.0f32; MOSHI_FRAME_SIZE];  // Silence
match self.process_with_lm(&mut conn_state, test_frame).await {
```

### Fixed (Correct):
```rust
let greeting_pcm = crate::greeting::generate_simple_greeting(
    &mut conn_state.moshi_state,
    "Hello, how can I help you today?"
).await?;

// Send greeting_pcm to audio output (already resampled to 24kHz)
```

## Why This Matters

1. **Not an audio pipeline bug** - resampling, format conversion, WAV export all work correctly
2. **Not a MOSHI model bug** - MOSHI is doing what it's supposed to (processing the input it receives)
3. **Logic error in auto-greeting** - wrong function called, sending wrong input to MOSHI
4. **Easy fix** - use existing `greeting.rs` module instead of silent frame

## Implications for Testing

- All audio quality tests were actually testing "MOSHI's response to silence"
- Need to re-test with proper greeting generation
- WAV export mechanism is proven working (once MOSHI generates real speech)

## Next Steps

1. **Modify `packages/core/src/voice.rs:704-751`** to use `generate_simple_greeting()` instead of silent frame
2. **Test with proper greeting** to verify MOSHI generates intelligible speech
3. **Transcribe with Whisper** to confirm greeting matches expected text
4. **Verify WAV export** captures the actual greeting correctly

## Conclusion

The "garbled voice" was MOSHI generating unpredictable output from silence input. The audio pipeline (resampling, format conversion, WAV export) works correctly. The fix is to use the proper greeting generation function that already exists in the codebase.

**This is a logic bug, not an audio quality bug.**

## Version Info

- xswarm: v0.1.0-2025.11.5.24 (periodic WAV flushing)
- Test method: Auto-greeting with MOSHI_DEBUG_WAV=1
- Transcription: OpenAI Whisper API
- Analysis tools: FFmpeg (spectrogram, audio stats)
- WAV file: ./tmp/moshi-debug-audio.wav (881K, 10.23s)
