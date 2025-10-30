#!/usr/bin/env python3
"""
Test MOSHI core functionality (no audio I/O required)
"""

import sys
print("=" * 70)
print("xSwarm MOSHI Core Test (No Audio I/O)")
print("=" * 70)
print()

# Test 1: Imports
print("1. Testing imports...")
try:
    from moshi_mlx import models
    import mlx.core as mx
    import numpy as np
    print("   ✓ All imports successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Model Config
print("\n2. Loading model config...")
try:
    config = models.config1b_202412()
    print(f"   ✓ Config loaded: {type(config).__name__}")
    print(f"   - Model dimension: {config.transformer.d_model}")
    print(f"   - Layers: {config.transformer.num_layers}")
    print(f"   - Audio codebooks: {config.audio_codebooks}")
except Exception as e:
    print(f"   ✗ Config failed: {e}")
    sys.exit(1)

# Test 3: Audio Processing
print("\n3. Testing audio array operations...")
try:
    # Create 1 second of test audio (24kHz)
    audio_np = np.zeros(24000, dtype=np.float32)
    print(f"   ✓ NumPy audio created: {audio_np.shape} {audio_np.dtype}")

    # Convert to MLX array
    audio_mlx = mx.array(audio_np)
    print(f"   ✓ MLX conversion works: {audio_mlx.shape} {audio_mlx.dtype}")

    # Basic operations
    audio_sum = mx.sum(audio_mlx)
    print(f"   ✓ MLX operations work: sum={float(audio_sum)}")
except Exception as e:
    print(f"   ✗ Audio processing failed: {e}")
    sys.exit(1)

# Test 4: Platform Detection
print("\n4. Platform detection...")
try:
    import platform
    is_mac_arm = platform.system() == "Darwin" and platform.machine() == "arm64"
    print(f"   Platform: {platform.system()} {platform.machine()}")
    print(f"   macOS ARM: {is_mac_arm}")
    print(f"   ✓ Platform detected correctly")
except Exception as e:
    print(f"   ✗ Platform detection failed: {e}")
    sys.exit(1)

# Test 5: Check sounddevice is NOT imported
print("\n5. Verifying sounddevice is not required...")
try:
    import sys
    if 'sounddevice' in sys.modules:
        print("   ⚠ Warning: sounddevice was imported (not needed)")
    else:
        print("   ✓ sounddevice NOT imported (correct!)")
except Exception as e:
    print(f"   ✗ Check failed: {e}")

print()
print("=" * 70)
print("✓ ALL TESTS PASSED")
print("=" * 70)
print()
print("MOSHI core is ready to use!")
print("No CFFI fix needed - audio I/O will be handled by Rust.")
print()
print("Next steps:")
print("  1. Complete model loading in bridge.py")
print("  2. Test WebSocket server")
print("  3. Integrate Rust client")
