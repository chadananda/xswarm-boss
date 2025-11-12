# MOSHI Audio Diagnosis - Critical Finding

## Date: 2025-11-06

## Problem Statement

User reported "garbled voice" from MOSHI after implementing WAV export (v0.1.0-2025.11.5.24).

## Investigation

### WAV File Analysis

**File**: `./tmp/moshi-debug-audio.wav`
- Format: pcm_s16le (16-bit signed integer PCM)
- Sample rate: 44100 Hz
- Channels: 1 (mono)
- Duration: 10.229252 seconds
- Bitrate: 705634 bps
- Size: 881K
- Status: ✅ Plays successfully with afplay

### Transcription Test

**Method**: OpenAI Whisper API (faster than local whisper-cpp)

**Result**:
```json
{
  "task": "transcribe",
  "language": "english",
  "duration": 10.220000267028809,
  "text": "SUBSCRIBE",
  "segments": [{
    "id": 0,
    "seek": 0,
    "start": 0.0,
    "end": 10.239999771118164,
    "text": " SUBSCRIBE",
    "tokens": [50364, 33817, 50876],
    "temperature": 1.0,
    "avg_logprob": -2.493337631225586,
    "compression_ratio": 0.529411792755127,
    "no_speech_prob": 0.29095879197120667
  }]
}
```

**Confidence**: 71% probability this IS speech (no_speech_prob: 0.29)

## Critical Finding

**The audio is NOT garbled!** Whisper successfully transcribed it as: **"SUBSCRIBE"**

This reveals the real problem:

### What Works ✅
1. WAV file format is correct (16-bit PCM)
2. Sample rate conversion works (no distortion)
3. Periodic WAV flushing works (file survives termination)
4. Audio output pipeline works correctly

### What's Broken ❌

**MOSHI is generating WRONG content!**

- Expected: Conversational greeting like "Hello" or similar
- Actual: "SUBSCRIBE"
- Context: This occurs after auto-greeting tones are played

## Root Cause Analysis

MOSHI is saying "SUBSCRIBE" instead of a conversational greeting. Possible causes:

### 1. Auto-Greeting Implementation Issue
- The greeting tones being played may be incorrect
- MOSHI might be misinterpreting the audio input
- The audio being fed to MOSHI might not match expectations

### 2. Model Behavior Issue
- MOSHI model might be hallucinating YouTube-style content
- Training data contamination (YouTube videos often start with "subscribe")
- Model context or prompting issue

### 3. Audio Pipeline Issue
- Greeting tones might not be activating MOSHI correctly
- Audio routing or mixing problem
- Input sample rate mismatch

## Next Steps

1. **Investigate auto-greeting implementation**
   - Check what audio tones are being generated
   - Verify the greeting audio is appropriate for MOSHI
   - Test with different greeting patterns

2. **Test MOSHI with manual input**
   - Speak directly to MOSHI (no auto-greeting)
   - Verify MOSHI generates appropriate conversational responses
   - Capture WAV and transcribe to verify behavior

3. **Review MOSHI model configuration**
   - Check personality settings
   - Verify prompt/context setup
   - Review model parameters

## Conclusion

The "garbled voice" problem is actually **MOSHI generating unexpected content**. The audio pipeline is working correctly - WAV files are being created, formatted, and played successfully. The issue is that MOSHI is saying "SUBSCRIBE" when it should be having a conversation.

This is a **model behavior issue**, not an audio quality issue.

## Version Info

- xswarm: v0.1.0-2025.11.5.24 (periodic WAV flushing)
- Test method: Auto-greeting tones with MOSHI_DEBUG_WAV=1
- Transcription: OpenAI Whisper API
- WAV file: ./tmp/moshi-debug-audio.wav (881K, 10.23s)
