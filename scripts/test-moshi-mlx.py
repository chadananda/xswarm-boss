#!/usr/bin/env python3
"""
Test MOSHI MLX Python implementation
Equivalent to our Rust MOSHI test - generates audio from text input
"""

import numpy as np
import soundfile as sf
import sys
from pathlib import Path

try:
    import moshi_mlx
    from moshi_mlx import MimiModel, LMModel
except ImportError:
    print("ERROR: moshi_mlx not installed. Run: pip3 install -U moshi_mlx")
    sys.exit(1)

def main():
    print("🧪 MOSHI MLX TEST (Python + Apple MLX)")
    print("=" * 60)
    print()

    # Paths
    input_wav = Path("./tmp/test-user-hello.wav")
    output_wav = Path("./tmp/moshi-mlx-output.wav")

    if not input_wav.exists():
        print(f"ERROR: Test input not found: {input_wav}")
        print("Run the Rust test first to generate test-user-hello.wav")
        sys.exit(1)

    print("1️⃣  Loading MOSHI MLX models...")
    print("   (This may take 30-60 seconds for first-time download)")

    try:
        # Load models with 4-bit quantization (faster, less memory)
        # Note: MLX will use Apple Silicon GPU automatically
        mimi = MimiModel(quantization=4)
        lm = LMModel(quantization=4)
        print("   ✅ Models loaded (4-bit quantized)\n")
    except Exception as e:
        print(f"   ❌ Model loading failed: {e}")
        sys.exit(1)

    print("2️⃣  Loading test audio...")
    try:
        audio, sample_rate = sf.read(input_wav)
        print(f"   ✅ Loaded {len(audio)} samples at {sample_rate}Hz\n")
    except Exception as e:
        print(f"   ❌ Failed to load audio: {e}")
        sys.exit(1)

    print("3️⃣  Encoding audio with MIMI...")
    try:
        # Encode input audio to codes
        # MIMI expects shape: (1, samples)
        audio_tensor = audio.reshape(1, -1).astype(np.float32)
        codes = mimi.encode(audio_tensor)
        print(f"   ✅ Encoded to {codes.shape[1]} code frames\n")
    except Exception as e:
        print(f"   ❌ Encoding failed: {e}")
        sys.exit(1)

    print("4️⃣  Generating response with Language Model...")
    try:
        # Generate response tokens (similar duration to Rust test)
        # Feed input codes, generate ~62 frames of output
        response_codes = lm.generate(
            codes,
            num_steps=62,
            temperature=0.8,
        )
        print(f"   ✅ Generated {response_codes.shape[1]} response frames\n")
    except Exception as e:
        print(f"   ❌ LM generation failed: {e}")
        sys.exit(1)

    print("5️⃣  Decoding audio with MIMI...")
    try:
        # Decode codes back to audio
        output_audio = mimi.decode(response_codes)
        # Remove batch dimension: (1, samples) -> (samples,)
        output_audio = output_audio.squeeze()
        print(f"   ✅ Decoded {len(output_audio)} samples\n")
    except Exception as e:
        print(f"   ❌ Decoding failed: {e}")
        sys.exit(1)

    print("6️⃣  Saving WAV file...")
    try:
        sf.write(output_wav, output_audio, 24000)  # MOSHI uses 24kHz
        print(f"   ✅ Saved to: {output_wav}\n")
    except Exception as e:
        print(f"   ❌ Failed to save: {e}")
        sys.exit(1)

    print("=" * 60)
    print("✅ TEST COMPLETE!")
    print()
    print("🎧 Listen to output:")
    print(f"   afplay {output_wav}")
    print()
    print("📊 Compare with Rust version:")
    print("   afplay ./tmp/moshi-response.wav  # Rust (garbled)")
    print(f"   afplay {output_wav}             # Python MLX")
    print()
    print("If Python MLX audio is intelligible but Rust is garbled,")
    print("the issue is in Rust/Candle Metal implementation.")
    print()

if __name__ == "__main__":
    main()
