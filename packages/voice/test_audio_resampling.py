#!/usr/bin/env python3
"""
Test audio resampling for Twilio ↔ MOSHI conversion

Verifies that audio can be converted between:
- Twilio: 8kHz PCM int16
- MOSHI: 24kHz PCM float32
"""

import sys
import numpy as np

print("=" * 70)
print("xSwarm Audio Resampling Test (Twilio ↔ MOSHI)")
print("=" * 70)
print()

# Test 1: Imports
print("1. Testing imports...")
try:
    from xswarm_voice.audio import (
        twilio_to_moshi,
        moshi_to_twilio,
        validate_audio_format,
        estimate_duration,
        convert_for_moshi,
        convert_for_twilio,
        TWILIO_SAMPLE_RATE,
        MOSHI_SAMPLE_RATE,
    )
    from scipy import signal
    print("   ✓ All imports successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Constants
print("\n2. Checking audio format constants...")
try:
    assert TWILIO_SAMPLE_RATE == 8000, "Twilio rate should be 8kHz"
    assert MOSHI_SAMPLE_RATE == 24000, "MOSHI rate should be 24kHz"
    print(f"   ✓ Twilio: {TWILIO_SAMPLE_RATE} Hz")
    print(f"   ✓ MOSHI: {MOSHI_SAMPLE_RATE} Hz")
    print(f"   ✓ Resample ratio: {MOSHI_SAMPLE_RATE // TWILIO_SAMPLE_RATE}x")
except AssertionError as e:
    print(f"   ✗ Constant check failed: {e}")
    sys.exit(1)

# Test 3: Create Test Audio (1 second of 440Hz sine wave at 8kHz)
print("\n3. Creating test audio (440Hz sine wave)...")
try:
    duration = 1.0  # seconds
    frequency = 440.0  # Hz (A4 note)

    # Generate 1 second at 8kHz
    num_samples_8k = int(TWILIO_SAMPLE_RATE * duration)
    t_8k = np.linspace(0, duration, num_samples_8k, endpoint=False)
    audio_8k_float = np.sin(2 * np.pi * frequency * t_8k).astype(np.float32)

    # Convert to int16 (Twilio format)
    audio_8k_int16 = (audio_8k_float * 32767).astype(np.int16)

    print(f"   ✓ Created {duration}s test signal at {frequency}Hz")
    print(f"   ✓ Format: {num_samples_8k} samples, 8kHz, int16")
    print(f"   ✓ Range: [{audio_8k_int16.min()}, {audio_8k_int16.max()}]")
except Exception as e:
    print(f"   ✗ Test audio creation failed: {e}")
    sys.exit(1)

# Test 4: Upsample 8kHz → 24kHz
print("\n4. Testing upsampling (8kHz → 24kHz)...")
try:
    audio_24k = twilio_to_moshi(audio_8k_int16)

    # Verify format
    assert audio_24k.dtype == np.float32, "Should be float32"
    assert len(audio_24k) == num_samples_8k * 3, "Should be 3x longer"
    assert audio_24k.min() >= -1.0 and audio_24k.max() <= 1.0, "Should be in [-1, 1]"

    print(f"   ✓ Upsampled: {len(audio_8k_int16)} → {len(audio_24k)} samples")
    print(f"   ✓ Format: {audio_24k.dtype}, range [{audio_24k.min():.3f}, {audio_24k.max():.3f}]")
    print(f"   ✓ Duration: {estimate_duration(len(audio_24k), MOSHI_SAMPLE_RATE):.1f}s")
except Exception as e:
    print(f"   ✗ Upsampling failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Downsample 24kHz → 8kHz
print("\n5. Testing downsampling (24kHz → 8kHz)...")
try:
    audio_8k_recovered = moshi_to_twilio(audio_24k)

    # Verify format
    assert audio_8k_recovered.dtype == np.int16, "Should be int16"
    assert len(audio_8k_recovered) == len(audio_8k_int16), "Should match original length"

    print(f"   ✓ Downsampled: {len(audio_24k)} → {len(audio_8k_recovered)} samples")
    print(f"   ✓ Format: {audio_8k_recovered.dtype}")
    print(f"   ✓ Duration: {estimate_duration(len(audio_8k_recovered), TWILIO_SAMPLE_RATE):.1f}s")
except Exception as e:
    print(f"   ✗ Downsampling failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Verify Round-Trip Quality
print("\n6. Testing round-trip conversion (8k → 24k → 8k)...")
try:
    # Compare original vs recovered
    # Allow some error due to resampling
    max_diff = np.abs(audio_8k_int16 - audio_8k_recovered).max()
    mean_diff = np.abs(audio_8k_int16 - audio_8k_recovered).mean()

    # Calculate correlation (should be close to 1.0)
    correlation = np.corrcoef(
        audio_8k_int16.astype(float),
        audio_8k_recovered.astype(float)
    )[0, 1]

    print(f"   ✓ Max sample difference: {max_diff}")
    print(f"   ✓ Mean sample difference: {mean_diff:.1f}")
    print(f"   ✓ Correlation: {correlation:.6f}")

    # Quality thresholds
    assert max_diff < 5000, "Max difference too large"
    assert correlation > 0.99, "Correlation too low"

    print(f"   ✓ Round-trip quality: EXCELLENT")
except Exception as e:
    print(f"   ✗ Round-trip test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Edge Cases
print("\n7. Testing edge cases...")
try:
    # Empty array
    empty_8k = np.array([], dtype=np.int16)
    empty_24k = twilio_to_moshi(empty_8k)
    assert len(empty_24k) == 0, "Empty input should give empty output"
    print("   ✓ Empty array handling works")

    # Short audio (10 samples)
    short_8k = np.zeros(10, dtype=np.int16)
    short_24k = twilio_to_moshi(short_8k)
    assert len(short_24k) == 30, "10 samples @ 8kHz should become 30 @ 24kHz"
    print("   ✓ Short audio handling works")

    # Max values
    max_8k = np.array([32767, -32768], dtype=np.int16)
    max_24k = twilio_to_moshi(max_8k)
    assert max_24k.max() <= 1.0 and max_24k.min() >= -1.0, "Should stay in bounds"
    print("   ✓ Max value handling works")

except Exception as e:
    print(f"   ✗ Edge case test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Convenience Functions
print("\n8. Testing convenience functions...")
try:
    # Test convert_for_moshi with 8kHz input
    moshi_from_8k = convert_for_moshi(audio_8k_int16, TWILIO_SAMPLE_RATE)
    assert len(moshi_from_8k) == len(audio_24k), "Should match twilio_to_moshi"
    print("   ✓ convert_for_moshi(8kHz) works")

    # Test convert_for_twilio with 24kHz input
    twilio_from_24k = convert_for_twilio(audio_24k, MOSHI_SAMPLE_RATE)
    assert len(twilio_from_24k) == len(audio_8k_int16), "Should match moshi_to_twilio"
    print("   ✓ convert_for_twilio(24kHz) works")

    # Test with already-correct rates
    already_24k = convert_for_moshi(audio_24k, MOSHI_SAMPLE_RATE)
    assert len(already_24k) == len(audio_24k), "Should be same length"
    print("   ✓ No-op conversions work")

except Exception as e:
    print(f"   ✗ Convenience function test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 9: Performance Benchmark
print("\n9. Performance benchmark...")
try:
    import time

    # Test with 10 seconds of audio
    long_audio_8k = np.random.randint(-32768, 32767,
                                      TWILIO_SAMPLE_RATE * 10,
                                      dtype=np.int16)

    # Upsample benchmark
    start = time.time()
    long_audio_24k = twilio_to_moshi(long_audio_8k)
    upsample_time = time.time() - start

    # Downsample benchmark
    start = time.time()
    long_audio_8k_back = moshi_to_twilio(long_audio_24k)
    downsample_time = time.time() - start

    print(f"   ✓ 10s upsample (8→24kHz): {upsample_time*1000:.1f}ms")
    print(f"   ✓ 10s downsample (24→8kHz): {downsample_time*1000:.1f}ms")
    print(f"   ✓ Total round-trip: {(upsample_time + downsample_time)*1000:.1f}ms")

    # Performance threshold (should be fast)
    assert upsample_time < 0.1, "Upsampling too slow"
    assert downsample_time < 0.1, "Downsampling too slow"

except Exception as e:
    print(f"   ✗ Performance test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 70)
print("✓ ALL TESTS PASSED")
print("=" * 70)
print()
print("Audio resampling is working correctly!")
print()
print("Summary:")
print("  - Twilio format: 8kHz PCM int16 ✓")
print("  - MOSHI format: 24kHz PCM float32 ✓")
print("  - Upsampling (3x): Working ✓")
print("  - Downsampling (1/3x): Working ✓")
print("  - Round-trip quality: Excellent ✓")
print("  - Performance: Good ✓")
print()
print("Next steps:")
print("  1. Integrate into bridge.py for phone call handling")
print("  2. Add μ-law encoding/decoding to Cloudflare Worker")
print("  3. Test with actual Twilio phone call")
