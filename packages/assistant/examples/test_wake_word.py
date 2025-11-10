#!/usr/bin/env python3
"""
Test wake word detection with microphone input.
"""

import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.wake_word import WakeWordDetector
from assistant.voice.audio_io import AudioIO
import numpy as np


def on_wake_word_detected():
    """Callback when wake word is detected"""
    print("\n🔊 WAKE WORD DETECTED! 🔊\n")


def main():
    print("=== Wake Word Detection Test ===\n")

    # Find Vosk model
    model_path = Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us-0.15"

    if not model_path.exists():
        print(f"❌ Vosk model not found: {model_path}")
        print("\nRun: python scripts/download_vosk_model.py")
        return 1

    # Initialize detector
    print("Initializing wake word detector...")
    detector = WakeWordDetector(
        model_path=model_path,
        wake_word="jarvis",
        sample_rate=16000,
        sensitivity=0.7
    )

    # Start detection
    detector.start(callback=on_wake_word_detected)

    # Initialize audio input (16kHz for Vosk)
    print("Starting audio input (16kHz)...")
    audio_io = AudioIO(
        sample_rate=16000,
        frame_size=1600,  # 100ms frames
        channels=1
    )

    def audio_callback(audio):
        """Process each audio frame"""
        detector.process_audio(audio)

    audio_io.start_input(callback=audio_callback)

    # Run until interrupted
    print(f"\n✅ Listening for wake word: 'jarvis'")
    print("Speak into your microphone...")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nStopping...")

    # Cleanup
    detector.stop()
    audio_io.stop()

    print("✅ Test complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
