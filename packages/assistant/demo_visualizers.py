#!/usr/bin/env python3
"""
Quick launcher for voice visualizer demo.
Shows all 6 visualization styles in a 3x2 grid.
"""

from textual.app import App, ComposeResult
from assistant.dashboard.screens.voice_viz_demo import VoiceVizDemoScreen


class VisualizerDemoApp(App):
    """Simple app to demo the voice visualizers."""

    TITLE = "xSwarm Voice Visualizer Demo - All 6 Styles"

    def on_mount(self) -> None:
        """Push demo screen on mount."""
        self.push_screen(VoiceVizDemoScreen())


if __name__ == "__main__":
    app = VisualizerDemoApp()
    app.run()
