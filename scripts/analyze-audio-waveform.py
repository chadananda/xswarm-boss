#!/usr/bin/env python3
"""
Simple audio waveform analysis to detect if audio is garbled/noise vs structured.
Doesn't require ASR - just looks at the audio signal properties.
"""

import wave
import numpy as np
import sys
import os

def analyze_audio(audio_file):
    """Analyze audio waveform for structure vs noise."""
    print(f"\n🎤 Analyzing: {audio_file}")
    print("━" * 60)

    if not os.path.exists(audio_file):
        print(f"❌ File not found: {audio_file}")
        return None

    # Open WAV file
    try:
        wf = wave.open(audio_file, "rb")
    except Exception as e:
        print(f"❌ Error opening file: {e}")
        return None

    # Read audio data
    n_channels = wf.getnchannels()
    sample_width = wf.getsampwidth()
    framerate = wf.getframerate()
    n_frames = wf.getnframes()
    duration = n_frames / framerate

    print(f"Format: {n_channels} channel(s), {framerate} Hz, {sample_width * 8}-bit")
    print(f"Duration: {duration:.2f} seconds ({n_frames} frames)")

    # Read all frames
    frames = wf.readframes(n_frames)
    wf.close()

    # Convert to numpy array
    if sample_width == 2:  # 16-bit
        audio_data = np.frombuffer(frames, dtype=np.int16)
    elif sample_width == 1:  # 8-bit
        audio_data = np.frombuffer(frames, dtype=np.uint8)
    else:
        print(f"⚠️  Unsupported sample width: {sample_width}")
        return None

    # Convert to float for analysis
    audio_data = audio_data.astype(np.float32)

    # Basic statistics
    mean_val = np.mean(audio_data)
    std_val = np.std(audio_data)
    max_val = np.max(np.abs(audio_data))

    print(f"\n📊 Waveform Statistics:")
    print(f"   Mean: {mean_val:.2f}")
    print(f"   Std Dev: {std_val:.2f}")
    print(f"   Max Amplitude: {max_val:.2f}")

    # Zero crossing rate (sign changes) - speech has moderate ZCR
    zero_crossings = np.sum(np.diff(np.sign(audio_data)) != 0)
    zcr = zero_crossings / len(audio_data)
    print(f"   Zero Crossing Rate: {zcr:.4f}")

    # Energy distribution
    # Split into chunks and calculate RMS energy
    chunk_size = framerate // 10  # 100ms chunks
    chunks = [audio_data[i:i+chunk_size] for i in range(0, len(audio_data), chunk_size)]
    energies = [np.sqrt(np.mean(chunk**2)) for chunk in chunks if len(chunk) > 0]

    if len(energies) > 0:
        energy_mean = np.mean(energies)
        energy_std = np.std(energies)
        energy_variation = energy_std / energy_mean if energy_mean > 0 else 0

        print(f"   Energy Variation: {energy_variation:.4f}")
    else:
        energy_variation = 0

    # Analyze results
    print(f"\n🔍 Analysis:")

    is_silence = max_val < 100
    is_very_noisy = zcr > 0.3
    has_structure = 0.05 < zcr < 0.25 and energy_variation > 0.2

    if is_silence:
        print("   🔴 SILENCE - Audio amplitude is too low")
        print("   ⚠️  RESULT: Audio might be empty or extremely quiet")
        return "SILENCE"
    elif is_very_noisy:
        print("   🔴 HIGH NOISE - Very high zero crossing rate")
        print("   ⚠️  RESULT: Audio is likely white noise or garbled")
        return "GARBLED"
    elif has_structure:
        print("   🟢 STRUCTURED - Audio shows speech-like patterns")
        print("   ✅ RESULT: Audio appears to have structure (likely speech)")
        return "STRUCTURED"
    else:
        print("   🟡 UNCLEAR - Audio doesn't match typical speech patterns")
        print("   ⚠️  RESULT: Audio might be garbled or unusual")
        return "UNCLEAR"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze-audio-waveform.py <audio_file.wav> [audio_file2.wav ...]")
        print("\nExample:")
        print("  python3 analyze-audio-waveform.py ./tmp/moshi-response.wav")
        sys.exit(1)

    print("🧪 Audio Waveform Analysis")
    print("Analyzes audio signal structure without requiring ASR")
    print("=" * 60)

    results = {}
    for audio_file in sys.argv[1:]:
        result = analyze_audio(audio_file)
        results[audio_file] = result

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    for audio_file, result in results.items():
        filename = os.path.basename(audio_file)
        print(f"{filename}: {result}")
