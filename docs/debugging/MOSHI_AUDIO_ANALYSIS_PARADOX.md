# MOSHI Audio Analysis Paradox

**Date:** 2025-11-08
**Status:** 🚨 CRITICAL FINDING

---

## The Paradox

Our MOSHI audio output exhibits **perfect audio metrics** but sounds **completely garbled** when listening.

### Audio Metrics Analysis

**File analyzed:** `./tmp/determinism-test/output-1.wav`

```
✅ Mean volume: -21.4 dB (Perfect! Within -20 to -30 dB speech range)
✅ Peak level: -4.1 dB (Good headroom)
✅ Dynamic range: 92.2 dB (Excellent! Way above 30 dB threshold)
✅ Zero crossing rate: 0.092 (Perfect! Within 0.05-0.15 speech range)
✅ Spectral flatness: 0.000 (Excellent! Structured sound, not noise)
✅ Crest factor: 7.3 (Good signal variation)
✅ RMS level: -21.4 dB (Consistent with mean)
✅ No significant silence (continuous speech-like signal)
```

**All metrics indicate HIGH QUALITY SPEECH AUDIO!**

### User Verification

User confirmed: **"perfectly garbled"** when actually listening to the audio.

### Whisper API Hallucination

Whisper transcribed the garbled audio as: *"and I'll see you in the next video. Take care."*

This proves Whisper can "transcribe" unintelligible audio.

---

## What This Means

This is NOT:
- ❌ A resampling quality issue
- ❌ A volume/loudness problem
- ❌ A noise problem
- ❌ A silence/truncation issue
- ❌ An audio format problem (24kHz, mono, 16-bit is correct)

This IS:
- ✅ A **data corruption** issue
- ✅ A **semantic** problem (structure is valid, content is wrong)
- ✅ Likely a **MIMI decoder** bug
- ✅ Possibly a **token processing** error

---

## Technical Analysis

### Why Metrics Look Good But Audio Is Garbled

The audio has:
1. **Correct amplitude distribution** - Signal levels are appropriate for speech
2. **Excellent dynamic range** - Varying loudness like natural speech
3. **Speech-like zero crossing rate** - Frequency content similar to voice
4. **Structured spectral content** - Not random noise

But these metrics only measure **signal characteristics**, not **semantic correctness**.

**Analogy:**
It's like having a book with correct sentence structure, punctuation, and word length, but every word is scrambled letters. Grammatically valid, semantically meaningless.

### The Real Problem

The MIMI decoder is generating audio samples that:
- Have valid statistical properties (amplitude, frequency, dynamics)
- Are deterministic (same every time with seed 299792458)
- Follow speech-like patterns
- But don't correspond to actual speech

**This suggests:**
1. **Codebook token decoding bug** - Tokens being interpreted incorrectly
2. **Phase/timing corruption** - Samples in wrong temporal order
3. **Channel mapping issue** - Data being written to wrong locations
4. **Decoder state corruption** - Internal state not matching expected values

---

## Evidence Timeline

### v7.7: TopK Sampling Implementation
- Matched official MOSHI CLI parameters
- Added seed 299792458 for determinism
- Result: 10% success rate, mostly failures

### v8.0: Cubic Interpolation "Fix"
- Changed from Linear to Cubic interpolation
- Test framework reported SUCCESS
- Whisper transcribed 10 words
- **User confirmed: STILL GARBLED**

### Determinism Test
- 3 runs with same seed
- Output files are **byte-for-byte IDENTICAL**
- Whisper consistently transcribed same text
- User confirmed all 3 sound garbled

### Audio Analysis (This Discovery)
- All audio metrics indicate perfect speech
- Spectrogram pending visual inspection
- Paradox: Good metrics + Garbled sound = Data corruption

---

## Next Steps

### Immediate Investigation

1. **Inspect spectrogram** - `./tmp/determinism-test/spectrum-analysis.png`
   - Look for: Formant patterns, harmonic structure
   - Compare to: Known good speech spectrograms

2. **Compare with official MOSHI CLI output**
   - Generate reference audio with same seed
   - Compare spectrograms side-by-side
   - Analyze waveform differences

3. **Raw audio data inspection**
   - Dump first 1000 samples from WAV
   - Check for: Patterns, anomalies, byte order issues

### Code Investigation Targets

Based on this paradox, focus on:

1. **`packages/core/src/voice.rs`**
   - MIMI decoder usage (lines ~1100-1200)
   - Audio token processing
   - Codebook lookup/decoding

2. **MIMI Codec Implementation**
   - Check if we're using correct codebook count (8 not 32)
   - Verify token shape expectations
   - Validate decoder step calls

3. **Audio Pipeline**
   - Sample format conversions (i16 vs f32)
   - Channel handling (mono conversion)
   - Buffer management

### Diagnostic Tests

1. **Test with official MOSHI CLI**
   ```bash
   # Generate reference with same seed
   packages/moshi/moshi-cli/target/release/moshi-cli \
     --input ./tmp/test-user-hello.wav \
     --output ./tmp/moshi-official.wav \
     --seed 299792458
   ```

2. **Binary comparison**
   ```bash
   # Compare our output vs official
   cmp ./tmp/moshi-response.wav ./tmp/moshi-official.wav
   ```

3. **Hexdump inspection**
   ```bash
   # Look at raw audio data
   hexdump -C ./tmp/moshi-response.wav | head -100
   ```

---

## Hypothesis

**Primary hypothesis:** The MIMI decoder is receiving correct tokens but decoding them incorrectly, producing audio that has valid statistical properties but wrong semantic content.

**Why this explains everything:**
- ✅ Metrics look perfect (decoder output has speech-like characteristics)
- ✅ Output is deterministic (same tokens → same wrong output)
- ✅ Whisper hallucinates (tries to make sense of garbled but structured audio)
- ✅ Sounds garbled (semantic content is wrong)
- ✅ No resampling artifacts (the problem is upstream in decoder)

**Test this hypothesis:**
Compare the audio tokens (before decoder) between our implementation and official CLI to see if they differ.

---

## Files Created

- `scripts/analyze-moshi-audio.sh` - FFmpeg-based audio analysis (no STT)
- `./tmp/determinism-test/spectrum-analysis.png` - Spectrogram for visual inspection

---

## Key Insight

**You can't test semantic audio correctness with signal metrics alone.**

We need:
1. Human listening ✅ (user confirmed garbled)
2. Visual inspection (spectrogram) - PENDING
3. Reference comparison (vs official CLI) - TODO
4. Token-level analysis (decoder input/output) - TODO

---

## Status

**The v8.0 "fix" did NOT work.** The Cubic interpolation change had no effect on the actual problem.

**Root cause:** Still under investigation, but strongly points to MIMI decoder issue.

**Next action:** Inspect spectrogram and compare with official MOSHI CLI output.
