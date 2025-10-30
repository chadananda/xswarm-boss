#!/usr/bin/env python3
"""
Interactive voice test for MOSHI integration
Run this to test voice I/O without daemon complexity

Usage:
    .venv/bin/python packages/voice/test_voice_interactive.py
"""

import sys
import time
import numpy as np
import asyncio
from typing import Optional

print("=" * 70)
print("🎤 MOSHI Interactive Voice Test")
print("=" * 70)
print()

# Check if running in venv
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("⚠️  Warning: Not running in virtual environment!")
    print("   Run: .venv/bin/python packages/voice/test_voice_interactive.py")
    print()

# Test imports
print("1. Testing imports...")
try:
    from moshi_mlx import models
    import mlx.core as mx
    import sounddevice as sd
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    print()
    print("Install dependencies:")
    print("  .venv/bin/pip install -e packages/voice")
    sys.exit(1)

print()

# Configuration
SAMPLE_RATE = 24000  # MOSHI native rate
CHANNELS = 1  # Mono
DTYPE = np.float32
RECORD_DURATION = 3  # seconds
MODEL_NAME = "kyutai/moshika-mlx-q4"

print("2. Configuration:")
print(f"   Sample rate: {SAMPLE_RATE} Hz")
print(f"   Channels: {CHANNELS} (mono)")
print(f"   Record duration: {RECORD_DURATION}s per turn")
print(f"   Model: {MODEL_NAME}")
print()

# Test audio devices
print("3. Checking audio devices...")
try:
    devices = sd.query_devices()
    default_input = sd.query_devices(kind='input')
    default_output = sd.query_devices(kind='output')

    print(f"   ✓ Input device: {default_input['name']}")
    print(f"   ✓ Output device: {default_output['name']}")
    print()
except Exception as e:
    print(f"   ✗ Audio device check failed: {e}")
    sys.exit(1)

# Load MOSHI model
print("4. Loading MOSHI model...")
print(f"   Model: {MODEL_NAME}")
print(f"   (First run will download ~4GB - this may take a while)")
print()

model = None
config = None

try:
    # Load model configuration
    config = models.config1b_202412()
    print(f"   ✓ Config loaded")
    print(f"     - Model dimension: {config.transformer.d_model}")
    print(f"     - Layers: {config.transformer.num_layers}")
    print(f"     - Codebooks: {config.audio_codebooks}")

    # TODO: Actually load the model weights
    # This requires figuring out the correct API
    # For now, we'll test audio I/O without inference

    print(f"   ⚠️  Model structure loaded, weights not loaded yet")
    print(f"   ⚠️  Testing audio I/O only for now")
    print()

except Exception as e:
    print(f"   ✗ Model loading failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("🎤 Ready for Interactive Testing")
print("=" * 70)
print()
print("Mode: Audio loopback test (record → echo back)")
print("Press Ctrl+C to exit")
print()

def record_audio(duration: float = RECORD_DURATION) -> np.ndarray:
    """Record audio from microphone"""
    print(f"🎤 Recording for {duration} seconds...", end="", flush=True)

    recording = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE
    )
    sd.wait()  # Wait until recording is finished

    print(" ✓")
    return recording.flatten()

def play_audio(audio: np.ndarray):
    """Play audio to speakers"""
    print(f"🔊 Playing audio ({len(audio)} samples)...", end="", flush=True)

    sd.play(audio, samplerate=SAMPLE_RATE)
    sd.wait()  # Wait until playback is finished

    print(" ✓")

def analyze_audio(audio: np.ndarray) -> dict:
    """Analyze audio properties"""
    return {
        "duration": len(audio) / SAMPLE_RATE,
        "rms": float(np.sqrt(np.mean(audio**2))),
        "peak": float(np.max(np.abs(audio))),
        "samples": len(audio),
    }

# Interactive test loop
turn = 0
try:
    while True:
        turn += 1
        print(f"\n--- Turn {turn} ---")

        # Record audio
        audio_input = record_audio(RECORD_DURATION)

        # Analyze input
        stats = analyze_audio(audio_input)
        print(f"📊 Input: {stats['duration']:.1f}s, "
              f"RMS={stats['rms']:.3f}, Peak={stats['peak']:.3f}")

        # Check if audio is too quiet
        if stats['rms'] < 0.01:
            print("⚠️  Audio very quiet - speak louder or check microphone")

        # TODO: Process with MOSHI model
        # For now, just echo back the input
        print("🤖 MOSHI: [Model inference not yet implemented]")
        print("   Echoing input audio back...")

        # Play back
        play_audio(audio_input)

        print("✓ Turn complete")

except KeyboardInterrupt:
    print("\n\n👋 Stopping interactive test...")
    print()
    print("Summary:")
    print(f"  - Completed {turn} turns")
    print(f"  - Audio I/O: ✓ Working")
    print(f"  - MOSHI inference: ⏸️  Not yet implemented")
    print()
    print("Next steps:")
    print("  1. Implement MOSHI model loading (see moshi_mlx docs)")
    print("  2. Add inference: audio → model → response audio")
    print("  3. Test with actual voice commands")
    print()

except Exception as e:
    print(f"\n\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
