#!/usr/bin/env python3
"""Test wizard screen in isolation"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, '.')

from textual.app import App
from assistant.dashboard.screens.wizard import WizardScreen

class TestApp(App):
    def on_mount(self):
        personas_dir = Path(__file__).parent.parent / "personas"
        print(f"Personas dir: {personas_dir}")
        print(f"Personas dir exists: {personas_dir.exists()}")

        try:
            self.push_screen(WizardScreen(personas_dir))
        except Exception as e:
            print(f"\n===ERROR===")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {e}")
            import traceback
            traceback.print_exc()
            self.exit()

if __name__ == "__main__":
    app = TestApp()
    app.run()
