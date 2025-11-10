#!/usr/bin/env python3
"""
Simple waveform analysis for MOSHI audio quality testing
Does NOT use AI/ML - just signal processing to detect garbled audio

Usage:
    python3 scripts/analyze-waveform.py ./tmp/moshi-response.wav

Returns:
    - Exit code 0 if audio appears to be speech
    - Exit code 1 if audio appears garbled
    - Prints quality score (0-100)
"""

import sys
import numpy as np
import scipy.signal
from scipy.io import wavfile

def analyze_audio_quality(wav_path):
    """Analyze audio quality without transcription"""

    try:
        sample_rate, audio = wavfile.read(wav_path)
    except Exception as e:
        print(f"ERROR: Could not read WAV file: {e}", file=sys.stderr)
        return None

    # Convert to mono if stereo
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    # Convert to float and normalize
    audio = audio.astype(float)
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))
    else:
        return {'score': 0, 'is_speech': False, 'reason': 'silent audio'}

    # 1. Check for silent periods (speech has pauses between words)
    frame_length = int(0.02 * sample_rate)  # 20ms frames
    if len(audio) < frame_length:
        return {'score': 0, 'is_speech': False, 'reason': 'audio too short'}

    # Pad audio to make it divisible by frame_length
    remainder = len(audio) % frame_length
    if remainder > 0:
        audio = np.pad(audio, (0, frame_length - remainder), 'constant')

    frames = audio.reshape(-1, frame_length)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    silence_ratio = np.sum(rms < 0.01) / len(rms)

    # 2. Check frequency distribution (speech has energy in 300-3400 Hz band)
    freqs, psd = scipy.signal.welch(audio, sample_rate, nperseg=min(1024, len(audio)))
    speech_band = (freqs >= 300) & (freqs <= 3400)
    speech_energy = np.sum(psd[speech_band])
    total_energy = np.sum(psd)
    speech_ratio = speech_energy / total_energy if total_energy > 0 else 0

    # 3. Check zero-crossing rate variability (speech varies in rhythm)
    zcr = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))

    # 4. Check amplitude modulation (speech has dynamics)
    try:
        envelope = np.abs(scipy.signal.hilbert(audio))
        envelope_std = np.std(envelope)
    except:
        envelope_std = 0

    # Quality score (0-100)
    score = 0
    reasons = []

    # Good audio has 5-20% silence (pauses between words)
    if 0.05 <= silence_ratio <= 0.20:
        score += 25
        reasons.append(f"✓ silence_ratio={silence_ratio:.2f}")
    else:
        reasons.append(f"✗ silence_ratio={silence_ratio:.2f} (expect 0.05-0.20)")

    # Good audio has 40-70% energy in speech band
    if 0.40 <= speech_ratio <= 0.70:
        score += 25
        reasons.append(f"✓ speech_ratio={speech_ratio:.2f}")
    else:
        reasons.append(f"✗ speech_ratio={speech_ratio:.2f} (expect 0.40-0.70)")

    # Good audio has moderate ZCR (0.05-0.15)
    if 0.05 <= zcr <= 0.15:
        score += 25
        reasons.append(f"✓ zcr={zcr:.3f}")
    else:
        reasons.append(f"✗ zcr={zcr:.3f} (expect 0.05-0.15)")

    # Good audio has high envelope variation (dynamics)
    if envelope_std > 0.1:
        score += 25
        reasons.append(f"✓ envelope_std={envelope_std:.3f}")
    else:
        reasons.append(f"✗ envelope_std={envelope_std:.3f} (expect > 0.1)")

    return {
        'score': score,
        'silence_ratio': silence_ratio,
        'speech_ratio': speech_ratio,
        'zcr': zcr,
        'envelope_std': envelope_std,
        'is_speech': score >= 60,
        'reasons': reasons
    }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 analyze-waveform.py <audio.wav>", file=sys.stderr)
        sys.exit(1)

    wav_path = sys.argv[1]
    result = analyze_audio_quality(wav_path)

    if result is None:
        sys.exit(1)

    # Print results
    print(f"Score: {result['score']}/100")
    print(f"Status: {'✅ Appears to be SPEECH' if result['is_speech'] else '❌ Appears to be GARBLED'}")
    print()
    print("Analysis:")
    for reason in result['reasons']:
        print(f"  {reason}")

    # Exit code
    sys.exit(0 if result['is_speech'] else 1)
