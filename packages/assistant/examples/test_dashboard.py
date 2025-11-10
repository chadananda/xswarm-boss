#!/usr/bin/env python3
"""
Test the Textual dashboard.
Simulates amplitude changes to verify pulsing circle animation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.config import Config
from assistant.dashboard.app import VoiceAssistantApp
import math
import random


class TestVoiceAssistantApp(VoiceAssistantApp):
    """Extended app with simulated audio for testing"""

    def on_mount(self) -> None:
        """Override to add test simulation"""
        super().on_mount()

        # Add simulation timer
        self.set_interval(0.03, self.simulate_audio)  # ~30 FPS
        self._test_frame = 0
        self._test_mode = "demo"

        # Add initial test message
        self.update_activity("Test mode: Simulating audio amplitude")
        self.update_activity("Press SPACE to cycle through states")
        self.update_activity("Press Q to quit")

    def simulate_audio(self):
        """Simulate audio amplitude changes"""
        self._test_frame += 1

        if self.state == "speaking":
            # Simulate realistic speech amplitude
            # Combine sine wave with random variation
            base_amplitude = (math.sin(self._test_frame * 0.1) + 1) / 2  # 0-1 range
            noise = random.random() * 0.3  # Add some randomness
            self.amplitude = min(1.0, base_amplitude * 0.7 + noise)

        elif self.state == "listening":
            # Small amplitude from ambient noise
            self.amplitude = random.random() * 0.2

        else:
            # Idle state - no amplitude
            self.amplitude = 0.0

    def start_listening(self):
        """Override to cycle through demo states"""
        if self.state == "idle" or self.state == "ready":
            self.state = "listening"
            self.update_activity("Demo: Listening (simulated ambient noise)")
        elif self.state == "listening":
            self.state = "speaking"
            self.update_activity("Demo: Speaking (simulated amplitude changes)")
        elif self.state == "speaking":
            self.state = "thinking"
            self.update_activity("Demo: Thinking (processing)")
        elif self.state == "thinking":
            self.state = "ready"
            self.amplitude = 0.0
            self.update_activity("Demo: Ready")

    def stop_listening(self):
        """Reset to idle"""
        self.state = "idle"
        self.amplitude = 0.0
        self.update_activity("Demo: Idle")


def main():
    """Run the test dashboard"""
    print("Starting Voice Assistant Dashboard Test...")
    print("=" * 60)
    print("Controls:")
    print("  SPACE - Cycle through states (idle → listening → speaking → thinking → ready)")
    print("  Q     - Quit")
    print("=" * 60)
    print()

    config = Config()
    app = TestVoiceAssistantApp(config)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")


if __name__ == "__main__":
    main()
