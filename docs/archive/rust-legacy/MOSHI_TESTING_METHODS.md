# MOSHI Audio Testing Methods (Without Whisper)

**Date**: 2025-11-09
**Status**: Recommendations for reliable audio quality testing

---

## Why Whisper Failed

**Problem**: Whisper API uses an AI approach that hallucinates plausible transcriptions from garbled audio, giving **false positives**.

**Example**: Garbled/backwards audio was transcribed as "and I'll see you next time, bye bye now" with reported "SUCCESS" ✅

**Conclusion**: Cannot use Whisper for automated testing - it masks broken audio.

---

## Better Testing Approaches

### Method 1: Waveform Analysis ⭐ RECOMMENDED

**Approach**: Analyze the audio waveform's statistical properties

**Good Audio Characteristics**:
- Amplitude varies (not constant noise)
- Contains silent periods between words
- Frequency distribution shows speech formants (300-3400 Hz)
- Energy distribution is uneven (speech has dynamics)
- Zero-crossing rate varies (speech has rhythm)

**Garbled Audio Characteristics**:
- Constant high-frequency noise
- No silent periods
- Uniform frequency distribution
- Even energy distribution
- Constant zero-crossing rate

**Implementation**:
```python
import numpy as np
import scipy.signal
from scipy.io import wavfile

def analyze_audio_quality(wav_path):
    """Analyze audio quality without transcription"""
    sample_rate, audio = wavfile.read(wav_path)

    # Convert to mono if stereo
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    # Normalize
    audio = audio.astype(float) / np.max(np.abs(audio))

    # 1. Check for silent periods (speech has pauses)
    frame_length = int(0.02 * sample_rate)  # 20ms frames
    frames = audio.reshape(-1, frame_length)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    silence_ratio = np.sum(rms < 0.01) / len(rms)

    # 2. Check frequency distribution (speech has formants)
    freqs, psd = scipy.signal.welch(audio, sample_rate, nperseg=1024)
    speech_band = (freqs >= 300) & (freqs <= 3400)
    speech_energy = np.sum(psd[speech_band])
    total_energy = np.sum(psd)
    speech_ratio = speech_energy / total_energy

    # 3. Check zero-crossing rate variability (speech varies)
    zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))

    # 4. Check amplitude modulation (speech has dynamics)
    envelope = np.abs(scipy.signal.hilbert(audio))
    envelope_std = np.std(envelope)

    # Quality score (0-100)
    score = 0

    # Good audio has 5-20% silence
    if 0.05 <= silence_ratio <= 0.20:
        score += 25

    # Good audio has 40-70% energy in speech band
    if 0.40 <= speech_ratio <= 0.70:
        score += 25

    # Good audio has moderate ZCR (0.05-0.15)
    if 0.05 <= zcr <= 0.15:
        score += 25

    # Good audio has high envelope variation
    if envelope_std > 0.1:
        score += 25

    return {
        'score': score,
        'silence_ratio': silence_ratio,
        'speech_ratio': speech_ratio,
        'zcr': zcr,
        'envelope_std': envelope_std,
        'is_speech': score >= 60
    }

# Usage
result = analyze_audio_quality('./tmp/moshi-response.wav')
if result['is_speech']:
    print(f"✅ Audio appears to be speech (score: {result['score']})")
else:
    print(f"❌ Audio appears garbled (score: {result['score']})")
```

**Advantages**:
- ✅ No AI hallucination
- ✅ Fast (milliseconds)
- ✅ Deterministic
- ✅ Catches garbled audio reliably

**Disadvantages**:
- ⚠️ Doesn't verify semantic correctness (what was said)
- ⚠️ Requires threshold tuning

---

### Method 2: Classic STT (Kaldi/Vosk) 🔧 FALLBACK

**Approach**: Use old-school HMM/GMM-based speech recognition

**Why Better Than Whisper**:
- Fails cleanly on garbled audio (no hallucination)
- Returns low confidence scores
- Errors are detectable

**Recommended Tools**:

1. **Vosk** (Offline, lightweight)
```python
from vosk import Model, KaldiRecognizer
import wave

model = Model("model")  # Download from alphacephei.com/vosk/models
wf = wave.open("./tmp/moshi-response.wav", "rb")
rec = KaldiRecognizer(model, wf.getframerate())

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    rec.AcceptWaveform(data)

result = json.loads(rec.FinalResult())
confidence = result.get('confidence', 0)

if confidence < 0.5:
    print("❌ Low confidence - likely garbled")
else:
    print(f"✅ Transcribed: {result['text']}")
```

2. **Kaldi** (More accurate, more complex)
- Industry-standard ASR toolkit
- HMM-GMM or DNN-HMM models
- Returns alignment and confidence scores

**Advantages**:
- ✅ Fails on garbled audio
- ✅ Confidence scores are reliable
- ✅ No hallucination

**Disadvantages**:
- ⚠️ Requires model download
- ⚠️ Slower than waveform analysis
- ⚠️ Still doesn't verify semantic correctness

---

### Method 3: Human-in-the-Loop (Current Best)

**Approach**: Generate audio and ask developer to listen

**Implementation**:
```bash
# Generate test audio
MOSHI_TEST_MODE=1 ./target/release/xswarm --dev

# Play for human verification
afplay ./tmp/moshi-response.wav

# Developer confirms:
# - Is it intelligible? (yes/no)
# - Does it sound natural? (yes/no)
# - Is it garbled/backwards? (yes/no)
```

**Advantages**:
- ✅ 100% accurate
- ✅ Catches all quality issues
- ✅ No false positives
- ✅ No setup required

**Disadvantages**:
- ❌ Not automated
- ❌ Requires manual intervention
- ❌ Can't run in CI/CD

**Best for**: Development iteration (current phase)

---

### Method 4: Reference Comparison ⭐ BEST FOR CI/CD

**Approach**: Compare against known-good audio from gen.rs

**Process**:

1. **Generate reference audio** (one-time):
```bash
# Use official gen.rs to create reference
cd packages/moshi/moshi-cli
cargo run --release --example gen -- \
  --lm-model-file ~/.cache/huggingface/.../model.q8.gguf \
  --lm-config-file ./tmp/moshi-official/rust/s2st-1b.toml \
  --mimi-model-file ~/.cache/huggingface/.../mimi.q8.gguf \
  --audio-input-file ./test-hello.wav \
  --text-tokenizer ./tokenizer.model \
  --audio-output-file ./reference-output.wav \
  --seed 12345

# Store reference audio
cp ./reference-output.wav ../../test-fixtures/moshi-reference.wav
```

2. **Compare test audio** (automated):
```python
import numpy as np
from scipy.io import wavfile
from scipy.signal import correlate

def compare_audio(test_path, reference_path, threshold=0.7):
    """Compare test audio with known-good reference"""

    # Load both files
    sr1, audio1 = wavfile.read(test_path)
    sr2, audio2 = wavfile.read(reference_path)

    assert sr1 == sr2, "Sample rates must match"

    # Normalize
    audio1 = audio1.astype(float) / np.max(np.abs(audio1))
    audio2 = audio2.astype(float) / np.max(np.abs(audio2))

    # Use same length
    min_len = min(len(audio1), len(audio2))
    audio1 = audio1[:min_len]
    audio2 = audio2[:min_len]

    # Compute cross-correlation
    correlation = np.corrcoef(audio1, audio2)[0, 1]

    # Compute spectral similarity
    fft1 = np.abs(np.fft.rfft(audio1))
    fft2 = np.abs(np.fft.rfft(audio2))
    spectral_sim = np.corrcoef(fft1, fft2)[0, 1]

    # Combined score
    score = (correlation + spectral_sim) / 2

    return {
        'score': score,
        'correlation': correlation,
        'spectral_similarity': spectral_sim,
        'matches_reference': score >= threshold
    }

# Usage
result = compare_audio('./tmp/moshi-response.wav',
                      './test-fixtures/moshi-reference.wav')

if result['matches_reference']:
    print(f"✅ Audio matches reference (score: {result['score']:.2f})")
else:
    print(f"❌ Audio differs from reference (score: {result['score']:.2f})")
```

**Advantages**:
- ✅ Automated and reliable
- ✅ Works in CI/CD
- ✅ Catches regressions
- ✅ No AI hallucination

**Disadvantages**:
- ⚠️ Requires known-good reference
- ⚠️ Sensitive to small changes (need good threshold)

---

## Recommended Testing Strategy

### Development Phase (NOW)
1. **Primary**: Human listening (Method 3)
2. **Secondary**: Waveform analysis (Method 1) for quick sanity checks

### Integration Phase (NEXT)
1. **Primary**: Reference comparison (Method 4)
2. **Secondary**: Waveform analysis (Method 1)
3. **Fallback**: Vosk STT (Method 2) with confidence thresholds

### CI/CD Pipeline
1. **Primary**: Reference comparison (Method 4) - fails if score < 0.7
2. **Secondary**: Waveform analysis (Method 1) - fails if score < 60
3. **Report**: Generate spectrograms for visual inspection

---

## Implementation Plan

### Phase 1: Remove Whisper
- ✅ Remove Whisper API calls from test harness
- ✅ Remove false "SUCCESS" messages based on Whisper
- ✅ Stop automated Whisper transcription

### Phase 2: Add Waveform Analysis
- [ ] Implement waveform quality analyzer (Python script)
- [ ] Add to test harness as primary check
- [ ] Set thresholds based on known-good audio

### Phase 3: Create Reference Audio
- [ ] Use gen.rs to generate reference outputs
- [ ] Store in `./test-fixtures/moshi-references/`
- [ ] Document how to regenerate if needed

### Phase 4: Add Reference Comparison
- [ ] Implement comparison script
- [ ] Integrate into test harness
- [ ] Add to CI/CD pipeline

---

## Quick Test Script (No Whisper)

```bash
#!/bin/bash
# scripts/test-moshi-audio-quality.sh

set -e

echo "🧪 MOSHI Audio Quality Test (No Whisper)"
echo "========================================"

# Generate audio
MOSHI_TEST_MODE=1 ./target/release/xswarm --dev

# Check file exists
if [ ! -f ./tmp/moshi-response.wav ]; then
    echo "❌ FAIL: No audio file generated"
    exit 1
fi

# Check file size (should be > 10KB for real audio)
FILE_SIZE=$(stat -f%z ./tmp/moshi-response.wav 2>/dev/null || stat -c%s ./tmp/moshi-response.wav)
if [ "$FILE_SIZE" -lt 10000 ]; then
    echo "❌ FAIL: Audio file too small ($FILE_SIZE bytes)"
    exit 1
fi

echo "✅ Audio file generated: $FILE_SIZE bytes"

# Analyze waveform (requires Python script)
if command -v python3 &> /dev/null; then
    SCORE=$(python3 scripts/analyze-waveform.py ./tmp/moshi-response.wav)
    if [ "$SCORE" -ge 60 ]; then
        echo "✅ PASS: Waveform analysis score: $SCORE/100"
    else
        echo "❌ FAIL: Waveform analysis score: $SCORE/100 (threshold: 60)"
        exit 1
    fi
fi

# Play audio for human verification
echo ""
echo "🔊 Playing audio for human verification..."
afplay ./tmp/moshi-response.wav

echo ""
read -p "Is the audio intelligible? (y/n): " answer
if [ "$answer" = "y" ]; then
    echo "✅ HUMAN VERIFICATION PASSED"
    exit 0
else
    echo "❌ HUMAN VERIFICATION FAILED"
    exit 1
fi
```

---

## Summary

**Stop using**: Whisper API (false positives)

**Start using**:
1. **Now**: Human listening + waveform analysis
2. **Next**: Reference comparison
3. **Later**: Classic STT (Vosk) as fallback

**Best approach**: Waveform analysis (Method 1) + Reference comparison (Method 4) + Human verification during dev

---

**Status**: Ready to implement waveform analysis script
**Next**: Test v13.0 audio with human listening to confirm fix worked
