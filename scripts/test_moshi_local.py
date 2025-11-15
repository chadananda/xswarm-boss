#!/usr/bin/env python3
"""
Test Moshi voice interaction locally (no phone required).

Usage:
    python scripts/test_moshi_local.py [--persona JARVIS] [--quality q8]

Controls:
    - Speak naturally into your microphone
    - Press Ctrl+C to exit
"""

import asyncio
import sys
import argparse
import numpy as np
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/assistant"))

from assistant.voice.moshi_mlx import MoshiBridge
from assistant.personas.manager import PersonaManager
from assistant.memory import MemoryManager
from assistant.config import Config
import sounddevice as sd


class LocalMoshiTester:
    """Test Moshi voice interaction locally."""

    def __init__(self, persona_name: str = "JARVIS", quality: str = "q8"):
        """
        Initialize local Moshi tester.

        Args:
            persona_name: Name of persona to use
            quality: Moshi quality (bf16, q8, q4)
        """
        self.persona_name = persona_name
        self.quality = quality
        self.sample_rate = 24000  # Moshi uses 24kHz
        self.chunk_size = 1920  # 80ms at 24kHz
        self.is_running = False

        # Components (lazy loaded)
        self.moshi = None
        self.persona_manager = None
        self.memory_manager = None
        self.config = None
        self.persona = None

    async def initialize(self):
        """Initialize all components."""
        print("🎤 Initializing Moshi Local Tester...")
        print()

        # Load config
        self.config = Config()

        # Load personas
        personas_dir = Path(__file__).parent.parent / "packages/personas"
        self.persona_manager = PersonaManager(personas_dir=personas_dir)
        self.persona = self.persona_manager.get_persona(self.persona_name)

        if not self.persona:
            print(f"❌ Persona '{self.persona_name}' not found!")
            print(f"Available: {', '.join(self.persona_manager.list_personas())}")
            sys.exit(1)

        print(f"🎭 Persona: {self.persona.name}")
        print(f"💬 System prompt: {self.persona.system_prompt[:100]}...")
        print()

        # Initialize memory
        self.memory_manager = MemoryManager()
        await self.memory_manager.initialize()

        # Load Moshi
        print(f"🔄 Loading Moshi models ({self.quality})...")
        print("   This may take a minute on first run...")
        print()

        self.moshi = MoshiBridge(
            hf_repo=f"kyutai/moshiko-mlx-{self.quality}",
            quantized=int(self.quality[1]) if self.quality.startswith("q") else None,
            max_steps=500
        )

        print("✅ Moshi loaded and ready!")
        print()

    async def run_conversation(self):
        """Run interactive conversation loop."""
        print("=" * 60)
        print(f"🎙️  Moshi Local Voice Test - {self.persona.name}")
        print("=" * 60)
        print()
        print("Instructions:")
        print("  1. Speak into your microphone")
        print("  2. Wait for Moshi to respond (audio will play)")
        print("  3. Press Ctrl+C to exit")
        print()
        print("Controls:")
        print("  - Press SPACE to manually trigger response")
        print("  - Press Ctrl+C to exit")
        print()
        print("=" * 60)
        print()

        self.is_running = True
        audio_buffer = []

        try:
            # Audio callback for recording
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"⚠️  Audio status: {status}")

                # Convert to float32 mono
                audio = indata[:, 0].astype(np.float32)
                audio_buffer.append(audio)

            # Start recording
            print("🎤 Listening... (speak now)")
            print()

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                callback=audio_callback,
                blocksize=self.chunk_size,
            ):
                while self.is_running:
                    # Wait for enough audio (5 seconds worth)
                    await asyncio.sleep(5.0)

                    if len(audio_buffer) == 0:
                        continue

                    # Get accumulated audio
                    user_audio = np.concatenate(audio_buffer)
                    audio_buffer.clear()

                    # Check if there's actual speech (simple RMS check)
                    rms = np.sqrt(np.mean(user_audio ** 2))
                    if rms < 0.01:  # Too quiet, skip
                        print("🔇 (silence detected, waiting for speech...)")
                        continue

                    print(f"🎙️  Processing {len(user_audio)} samples (RMS: {rms:.4f})...")

                    # Build prompt with persona
                    prompt = self.persona.system_prompt or f"You are {self.persona.name}."
                    prompt += "\n\nRespond naturally to what the user just said. Keep it conversational and concise."

                    # Generate Moshi response
                    print("🤖 Moshi is thinking...")
                    try:
                        response_audio, response_text = self.moshi.generate_response(
                            user_audio,
                            text_prompt=prompt,
                            max_tokens=300
                        )

                        print(f"💬 {self.persona.name}: {response_text or '[Audio response]'}")
                        print()

                        # Play response audio
                        print("🔊 Playing response...")
                        sd.play(response_audio, samplerate=self.sample_rate)
                        sd.wait()  # Wait for playback to finish

                        print("✅ Response complete")
                        print("🎤 Listening... (speak now)")
                        print()

                    except Exception as e:
                        print(f"❌ Error generating response: {e}")
                        print()

        except KeyboardInterrupt:
            print()
            print("🛑 Stopping...")
            self.is_running = False

    async def cleanup(self):
        """Cleanup resources."""
        print()
        print("👋 Goodbye!")


async def main():
    """Run local Moshi test."""
    parser = argparse.ArgumentParser(description="Test Moshi voice locally")
    parser.add_argument(
        "--persona",
        default="JARVIS",
        help="Persona to use (default: JARVIS)"
    )
    parser.add_argument(
        "--quality",
        default="q8",
        choices=["bf16", "q8", "q4"],
        help="Moshi quality (default: q8)"
    )
    args = parser.parse_args()

    # Create tester
    tester = LocalMoshiTester(
        persona_name=args.persona,
        quality=args.quality
    )

    try:
        # Initialize
        await tester.initialize()

        # Run conversation
        await tester.run_conversation()

    finally:
        # Cleanup
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
