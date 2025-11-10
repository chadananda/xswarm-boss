#!/usr/bin/env python3
"""
Test reversing audio at different chunk sizes to diagnose corruption pattern.
If audio sounds "choppy with bits reversed but in right order",
this will help find the exact reversal granularity.
"""

import wave
import numpy as np
import sys
import os

def reverse_chunks(audio_data, chunk_size):
    """Reverse audio at chunk_size granularity."""
    chunks = []
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i+chunk_size]
        # Reverse this chunk
        reversed_chunk = chunk[::-1]
        chunks.append(reversed_chunk)
    return np.concatenate(chunks)

def process_audio(input_file, output_dir):
    """Create multiple versions with different chunk reversal sizes."""
    print(f"\n🎤 Processing: {input_file}")
    print("━" * 60)

    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Open input WAV file
    with wave.open(input_file, "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()

        print(f"Format: {n_channels} channel(s), {framerate} Hz, {sample_width * 8}-bit")
        print(f"Frames: {n_frames} ({n_frames / framerate:.2f} seconds)")

        # Read all frames
        frames = wf.readframes(n_frames)

        # Convert to numpy array
        if sample_width == 2:  # 16-bit
            audio_data = np.frombuffer(frames, dtype=np.int16)
        else:
            print(f"⚠️  Unsupported sample width: {sample_width}")
            return

    print(f"\n📝 Creating reversed versions...")

    # Test different chunk sizes based on MOSHI's processing:
    # - 12ms per step at 24kHz = 288 samples
    # - 1920 samples per MIMI frame (80ms at 24kHz)
    # - Other common sizes

    test_configs = [
        ("full", len(audio_data), "Fully reversed audio"),
        ("1920", 1920, "MIMI frame size (80ms, one MIMI decode step)"),
        ("960", 960, "Half MIMI frame (40ms)"),
        ("480", 480, "Quarter MIMI frame (20ms)"),
        ("288", 288, "LM step size (12ms at 24kHz)"),
        ("240", 240, "10ms chunks"),
        ("120", 120, "5ms chunks"),
    ]

    for name, chunk_size, description in test_configs:
        if chunk_size > len(audio_data):
            continue

        print(f"\n  {name}: {description}")
        print(f"       Chunk size: {chunk_size} samples ({chunk_size / framerate * 1000:.1f}ms)")

        # Reverse at this chunk size
        reversed_audio = reverse_chunks(audio_data, chunk_size)

        # Save to file
        output_file = os.path.join(output_dir, f"reversed_{name}.wav")
        with wave.open(output_file, "wb") as wf_out:
            wf_out.setnchannels(n_channels)
            wf_out.setsampwidth(sample_width)
            wf_out.setframerate(framerate)
            wf_out.writeframes(reversed_audio.tobytes())

        print(f"       ✅ Saved: {output_file}")

    print(f"\n✅ Created {len(test_configs)} reversed versions")
    print(f"\n📂 Output directory: {output_dir}")
    print(f"\n🎧 Listen to each version to find which sounds most intelligible:")
    for name, _, description in test_configs:
        if chunk_size > len(audio_data):
            continue
        print(f"   - reversed_{name}.wav: {description}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 reverse-audio-chunks.py <input.wav> [output_dir]")
        print("\nExample:")
        print("  python3 reverse-audio-chunks.py ./tmp/moshi-response.wav ./tmp/reversed-tests/")
        print("\nThis creates multiple versions with different chunk reversal sizes")
        print("to diagnose the exact reversal pattern in garbled audio.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./tmp/reversed-tests"

    print("🧪 Audio Chunk Reversal Test")
    print("Testing different chunk sizes to find reversal pattern")
    print("=" * 60)

    process_audio(input_file, output_dir)

    print("\n" + "=" * 60)
    print("🎧 NEXT STEPS:")
    print("=" * 60)
    print("1. Listen to each reversed_*.wav file")
    print("2. Find which one sounds most intelligible")
    print("3. That tells us the exact chunk size being reversed")
    print("4. We can then fix the buffer ordering in the code")
