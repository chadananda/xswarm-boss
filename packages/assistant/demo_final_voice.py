#!/usr/bin/env python3
"""
Final Voice Visualizer Demo
Shows the final configuration:
- Assistant: Sound Wave Circle (#6)
- Microphone: Dots (#5) with grayscale, scrolling right
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static, Label
from rich.text import Text
import math

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle
)


class FinalVoiceDemo(App):
    """Demo showing the final voice visualizer configuration."""

    TITLE = "Final Voice Visualizer - Sound Wave Circle + Dots (Grayscale)"

    CSS = """
    Screen {
        background: #0a0e27;
    }

    #container {
        width: 100%;
        height: 100%;
        align: center middle;
        padding: 2;
    }

    #info {
        width: 100%;
        height: auto;
        background: #1a1f3a;
        border: solid #00d4ff;
        padding: 1;
        margin-bottom: 1;
    }

    .info-text {
        color: #00d4ff;
        text-style: bold;
    }

    VoiceVisualizerPanel {
        width: 100%;
        height: 100%;
    }
    """

    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo."""
        yield Header()

        with Container(id="container"):
            # Info panel
            with Vertical(id="info"):
                yield Label("Final Configuration:", classes="info-text")
                yield Label("  Assistant Speaking: Sound Wave Circle (#6)", classes="info-text")
                yield Label("  Microphone Input: Dots (#5) - Grayscale, Right-Scrolling", classes="info-text")
                yield Label("  (Simulated audio data)", classes="info-text")

            # The visualizer with final configuration
            yield VoiceVisualizerPanel(
                visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                microphone_waveform_style=MicrophoneWaveformStyle.DOTS
            )

        yield Footer()

    def on_mount(self) -> None:
        """Start the visualizer animation."""
        # Get the visualizer panel and start its built-in animation
        visualizer = self.query_one(VoiceVisualizerPanel)
        visualizer.start_animation()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Final Voice Visualizer Configuration")
    print("=" * 70)
    print()
    print("This shows the final chosen configuration:")
    print("  • Assistant: Sound Wave Circle - wave pattern around perimeter")
    print("  • Microphone: Dots with grayscale intensity, scrolling right")
    print()
    print("The dots scroll RIGHT (new data appears on LEFT)")
    print("Grayscale levels: bright → white → medium gray → light gray → dark")
    print()
    print("Press Q or Escape to quit")
    print("=" * 70 + "\n")

    app = FinalVoiceDemo()
    app.run()
