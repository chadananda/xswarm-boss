#!/usr/bin/env python3
"""
Comprehensive test for Moshi audio pipeline.
Tests audio I/O, Moshi generation, and full conversation pipeline.
"""

import numpy as np
import asyncio
from pathlib import Path
import wave
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "assistant"))

from assistant.voice.audio_io import AudioIO
from assistant.voice.moshi_mlx import MoshiBridge


def save_wav(audio: np.ndarray, filename: str, sample_rate: int = 24000):
    """Save audio array to WAV file for manual verification."""
    # Ensure audio is in correct format
    audio = np.asarray(audio, dtype=np.float32)

    # Normalize to int16 range
    audio_int16 = (audio * 32767).astype(np.int16)

    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    print(f"✅ Saved WAV: {filename}")


def test_1_audio_io_chunking():
    """Test 1: Audio I/O chunking logic."""
    print("\n🧪 Test 1: Audio I/O Chunking Logic")
    print("=" * 60)

    audio_io = AudioIO(sample_rate=24000, frame_size=1920, channels=1)

    # Generate test audio (2 seconds of white noise)
    test_audio = np.random.randn(48000).astype(np.float32) * 0.1

    print(f"📊 Input audio shape: {test_audio.shape}")
    print(f"📊 Input audio dtype: {test_audio.dtype}")
    print(f"📊 Frame size: {audio_io.frame_size}")

    # Test play_audio chunking
    audio_io.play_audio(test_audio)

    # Verify chunks in queue
    chunk_count = audio_io.output_queue.qsize()
    expected_chunks = int(np.ceil(len(test_audio) / audio_io.frame_size))

    print(f"📊 Expected chunks: {expected_chunks}")
    print(f"📊 Actual chunks in queue: {chunk_count}")

    assert chunk_count == expected_chunks, f"Expected {expected_chunks} chunks, got {chunk_count}"

    # Verify chunk properties
    first_chunk = audio_io.output_queue.get()
    print(f"📊 First chunk shape: {first_chunk.shape}")
    print(f"📊 First chunk dtype: {first_chunk.dtype}")
    print(f"📊 First chunk contiguous: {first_chunk.flags['C_CONTIGUOUS']}")

    assert first_chunk.dtype == np.float32, f"Expected float32, got {first_chunk.dtype}"
    assert first_chunk.flags['C_CONTIGUOUS'], "Chunk not contiguous in memory"
    assert len(first_chunk) == audio_io.frame_size, f"Expected {audio_io.frame_size} samples, got {len(first_chunk)}"

    print("✅ Test 1 PASSED: Audio chunking works correctly")
    return True


def test_2_moshi_audio_generation():
    """Test 2: Moshi audio generation with synthetic input."""
    print("\n🧪 Test 2: Moshi Audio Generation")
    print("=" * 60)

    try:
        # Initialize Moshi
        print("🔄 Initializing Moshi bridge...")
        moshi = MoshiBridge(quality="q4")

        # Generate synthetic "speech" input (1 second of modulated sine wave to simulate voice)
        duration = 1.0  # 1 second
        sample_rate = 24000
        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples)

        # Create voice-like signal: mix of frequencies with amplitude modulation
        fundamental = 200  # Hz (typical male voice)
        speech_signal = (
            np.sin(2 * np.pi * fundamental * t) * 0.3 +
            np.sin(2 * np.pi * fundamental * 2 * t) * 0.2 +  # Harmonic
            np.sin(2 * np.pi * fundamental * 3 * t) * 0.1    # Harmonic
        )

        # Add amplitude modulation to simulate speech patterns
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 3 * t)  # 3 Hz modulation
        synthetic_speech = (speech_signal * modulation).astype(np.float32)

        print(f"📊 Synthetic input shape: {synthetic_speech.shape}")
        print(f"📊 Synthetic input dtype: {synthetic_speech.dtype}")
        print(f"📊 Synthetic input range: [{synthetic_speech.min():.3f}, {synthetic_speech.max():.3f}]")

        # Save input for comparison
        output_dir = Path(__file__).parent.parent / "tmp"
        output_dir.mkdir(exist_ok=True)
        save_wav(synthetic_speech, str(output_dir / "test_input.wav"))

        # Generate Moshi response using working pattern
        print("🔄 Generating Moshi response...")
        lm_gen = moshi.create_lm_generator(max_steps=50)

        # Feed input audio first
        num_input_frames = len(synthetic_speech) // 1920
        for i in range(num_input_frames):
            frame = synthetic_speech[i*1920:(i+1)*1920]
            moshi.step_frame(lm_gen, frame)

        # Then generate response frames
        moshi_chunks = []
        moshi_text_pieces = []
        for _ in range(50):  # Generate 50 frames (~4 seconds)
            silence = np.zeros(1920, dtype=np.float32)
            audio, text = moshi.step_frame(lm_gen, silence)
            if audio is not None and len(audio) > 0:
                moshi_chunks.append(audio)
                if text:
                    moshi_text_pieces.append(text)

        moshi_audio = np.concatenate(moshi_chunks) if moshi_chunks else None
        moshi_text = "".join(moshi_text_pieces) if moshi_text_pieces else ""

        print(f"📊 Moshi output shape: {moshi_audio.shape if moshi_audio is not None else 'None'}")
        print(f"📊 Moshi output dtype: {moshi_audio.dtype if moshi_audio is not None else 'N/A'}")
        print(f"📊 Moshi text: {moshi_text}")

        # Verify output
        assert moshi_audio is not None, "Moshi returned None for audio"
        assert len(moshi_audio) > 0, "Moshi returned empty audio"
        assert moshi_audio.dtype == np.float32, f"Expected float32, got {moshi_audio.dtype}"
        assert moshi_audio.min() >= -1.0 and moshi_audio.max() <= 1.0, "Audio values out of range"

        # Save output for manual verification
        save_wav(moshi_audio, str(output_dir / "test_moshi_output.wav"))

        print("✅ Test 2 PASSED: Moshi generates valid audio")
        return True

    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_full_pipeline_integration():
    """Test 3: Full pipeline integration (AudioIO + Moshi)."""
    print("\n🧪 Test 3: Full Pipeline Integration")
    print("=" * 60)

    try:
        # Initialize components
        audio_io = AudioIO(sample_rate=24000, frame_size=1920, channels=1)
        moshi = MoshiBridge(quality="q4")

        # Generate synthetic input
        duration = 0.5  # 0.5 seconds
        samples = int(duration * 24000)
        t = np.linspace(0, duration, samples)
        synthetic_speech = (np.sin(2 * np.pi * 200 * t) * 0.3).astype(np.float32)

        print(f"📊 Input audio: {samples} samples")

        # Process through Moshi using working pattern
        lm_gen = moshi.create_lm_generator(max_steps=30)

        # Feed input audio
        num_input_frames = len(synthetic_speech) // 1920
        for i in range(num_input_frames):
            frame = synthetic_speech[i*1920:(i+1)*1920]
            moshi.step_frame(lm_gen, frame)

        # Generate response
        moshi_chunks = []
        for _ in range(30):
            silence = np.zeros(1920, dtype=np.float32)
            audio, text = moshi.step_frame(lm_gen, silence)
            if audio is not None and len(audio) > 0:
                moshi_chunks.append(audio)

        moshi_audio = np.concatenate(moshi_chunks) if moshi_chunks else None
        moshi_text = ""  # Not testing text in this test

        assert moshi_audio is not None and len(moshi_audio) > 0, "Moshi returned empty audio"

        print(f"📊 Moshi output: {len(moshi_audio)} samples")

        # Queue for playback (test chunking)
        audio_io.play_audio(moshi_audio)

        # Verify chunks
        chunk_count = audio_io.output_queue.qsize()
        expected_chunks = int(np.ceil(len(moshi_audio) / audio_io.frame_size))

        print(f"📊 Chunks queued: {chunk_count} (expected {expected_chunks})")

        assert chunk_count == expected_chunks, f"Chunking mismatch: {chunk_count} vs {expected_chunks}"

        # Verify chunk format
        for i in range(chunk_count):
            chunk = audio_io.output_queue.get()
            assert chunk.dtype == np.float32, f"Chunk {i} wrong dtype"
            assert chunk.flags['C_CONTIGUOUS'], f"Chunk {i} not contiguous"
            assert len(chunk) <= audio_io.frame_size, f"Chunk {i} too large"

        print("✅ Test 3 PASSED: Full pipeline integration works")
        return True

    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_error_handling():
    """Test 4: Error handling edge cases."""
    print("\n🧪 Test 4: Error Handling")
    print("=" * 60)

    audio_io = AudioIO(sample_rate=24000, frame_size=1920, channels=1)

    # Test 1: Empty audio
    print("🔄 Testing empty audio...")
    audio_io.play_audio(np.array([], dtype=np.float32))
    assert audio_io.output_queue.qsize() == 0, "Empty audio should not queue chunks"
    print("✅ Empty audio handled correctly")

    # Test 2: Non-contiguous audio
    print("🔄 Testing non-contiguous audio...")
    non_contiguous = np.random.randn(5000).astype(np.float32)[::2]  # Every other sample
    assert not non_contiguous.flags['C_CONTIGUOUS'], "Test audio should be non-contiguous"

    audio_io.play_audio(non_contiguous)
    chunk = audio_io.output_queue.get()
    assert chunk.flags['C_CONTIGUOUS'], "play_audio should make audio contiguous"
    print("✅ Non-contiguous audio converted correctly")

    # Test 3: Wrong dtype
    print("🔄 Testing wrong dtype conversion...")
    wrong_dtype = np.random.randn(1920).astype(np.float64)
    audio_io.play_audio(wrong_dtype)
    chunk = audio_io.output_queue.get()
    assert chunk.dtype == np.float32, "play_audio should convert to float32"
    print("✅ Dtype conversion works correctly")

    print("✅ Test 4 PASSED: Error handling works correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 Moshi Audio Pipeline Comprehensive Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Audio I/O Chunking", test_1_audio_io_chunking()))
    results.append(("Moshi Audio Generation", test_2_moshi_audio_generation()))
    results.append(("Full Pipeline Integration", test_3_full_pipeline_integration()))
    results.append(("Error Handling", test_4_error_handling()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📁 Generated files (for manual verification):")
        print("   - tmp/test_input.wav (synthetic speech input)")
        print("   - tmp/test_moshi_output.wav (Moshi's response)")
        print("\n💡 You can play these WAV files to verify audio quality")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
