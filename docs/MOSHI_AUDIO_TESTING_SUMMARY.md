# MOSHI Audio Testing Summary

**Date**: 2025-11-08
**Status**: ❌ AUDIO QUALITY ISSUE - Contradictory Signals

## Test Results for `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tmp/moshi-response.wav`

### What Whisper API Says (Nov 8):
✅ **Transcription**: "I don't think I've ever seen anything like this before."
✅ **Word Count**: 10 words
✅ **Conclusion**: "Audio contains recognizable speech"

### What Waveform Analysis Says:
✅ **Result**: STRUCTURED audio
✅ **Zero Crossing Rate**: 0.0938 (speech-like)
✅ **Energy Variation**: 0.6488 (good variation)
✅ **Max Amplitude**: 20242 (strong signal)
✅ **Conclusion**: "Audio shows speech-like patterns"

### What User's Ears Say:
❌ **Result**: "Completely garbled"
❌ **Unintelligible** when played back

## Analysis

We have contradictory signals:

1. **Whisper API** → Transcribes coherent English
2. **Waveform Analysis** → Shows structured speech patterns
3. **Human Listening** → Completely unintelligible

### Possible Explanations:

1. **Audio Corruption with Structure Preserved**:
   - Reversed audio (structure intact, but backwards)
   - Wrong playback speed
   - Heavy spectral distortion
   - Formant shifting

2. **Whisper Hallucination**:
   - Whisper is generative and might invent plausible text
   - Even from garbled audio that has structure
   - Cannot be trusted for validation

3. **Waveform vs Spectral Issue**:
   - Time-domain analysis shows structure
   - But frequency-domain (what we hear) is garbled
   - Need spectral analysis to diagnose

## What We Know

### What Works:
- ✅ MLX (Python) produces clear, intelligible MOSHI audio
- ✅ moshi-cli gen.rs produces clear, intelligible audio
- ✅ Models load correctly, no crashes (after warmup fix)

### What Doesn't Work:
- ❌ Our voice.rs streaming implementation produces unintelligible audio
- ❌ Audio has structure but is garbled when heard

### Fixes Attempted:
1. ✅ **Warmup fix** - Fixed decoder crash, NOT audio quality
2. ❌ **Codebook extraction** - Changed to match gen.rs, still garbled

## Testing Tools Created

### 1. Vosk Test Script (Traditional ASR)
**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/scripts/test-audio-with-vosk.py`

**Status**: ⚠️ Not working (Python architecture mismatch)

**Purpose**: Traditional ASR that won't hallucinate like Whisper

### 2. Waveform Analysis Script
**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/scripts/analyze-audio-waveform.py`

**Status**: ✅ Working

**Purpose**: Analyze audio signal structure without ASR

**Result**: Shows STRUCTURED audio (contradicts user's listening experience)

## Next Investigation Steps

### 1. Spectral Analysis
Check frequency content - might reveal:
- Formant shifting
- Frequency inversion
- Spectral distortion

### 2. Playback Speed Test
Try playing audio at different speeds:
- 0.5x, 0.75x, 1.0x, 1.5x, 2.0x
- Might reveal speed mismatch

### 3. Reverse Audio Test
Try reversing the audio:
- If it sounds better reversed, we're generating backwards

### 4. Compare with gen.rs Output
Generate same test with gen.rs and compare:
- Waveform patterns
- Spectral content
- Duration

### 5. Deep LM State Investigation
Compare LM generator creation:
- `load_streaming` vs `load_lm_model`
- State initialization differences
- Token generation patterns

## Current Hypothesis

The audio likely has ONE of these issues:

1. **Reversed/Flipped** - Audio is backwards or upside-down
2. **Speed Mismatch** - Wrong sample rate during generation
3. **Spectral Corruption** - Frequency-domain distortion
4. **LM State Issue** - Streaming state corrupts audio tokens

It's NOT:
- ❌ MIMI configuration (matches gen.rs)
- ❌ Codebook count (verified as 8)
- ❌ Model warmup (fixed crash, not audio)
- ❌ Pure noise (waveform shows structure)

## Files Referenced

- **Test Audio**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tmp/moshi-response.wav`
- **Implementation**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs:1120-1310`
- **Reference**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/moshi/moshi-cli/src/gen.rs:100-125`
- **Status Doc**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/docs/MOSHI_GARBLED_AUDIO_STATUS.md`
