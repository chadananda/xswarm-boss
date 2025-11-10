#!/usr/bin/env python3
"""
Test script for MOSHI bridge.
Verifies device detection and basic encoding/decoding.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.config import Config
from assistant.voice.moshi_pytorch import MoshiBridge
import numpy as np


def main():
    print("=== MOSHI Bridge Test ===\n")

    # Load config
    config = Config()
    device = config.detect_device()

    print(f"\nDetected device: {device}")
    print(f"Model directory: {config.model_dir}")

    # Test MOSHI loading
    try:
        print("\nLoading MOSHI models...")
        bridge = MoshiBridge(
            device=device,
            model_dir=config.model_dir
        )
        print("✅ MOSHI models loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load MOSHI: {e}")
        print("\nMake sure MOSHI is installed:")
        print("  cd /tmp/moshi-official/moshi && pip install -e .")
        return 1

    # Test audio encoding
    print("\nTesting audio encoding...")
    test_audio = np.random.randn(1920).astype(np.float32) * 0.1

    try:
        codes = bridge.encode_audio(test_audio)
        print(f"✅ Encoded audio to codes: {codes.shape}")

        decoded = bridge.decode_audio(codes)
        print(f"✅ Decoded codes to audio: {decoded.shape}")
    except Exception as e:
        print(f"❌ Encoding/decoding failed: {e}")
        return 1

    # Test amplitude calculation
    amplitude = bridge.get_amplitude(test_audio)
    print(f"✅ Amplitude: {amplitude:.3f}")

    print("\n=== All tests passed! ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
