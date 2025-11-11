#!/usr/bin/env python3
"""
Final Voice Visualizer Demo
Your Chosen Configuration:
- Assistant Speaking: Sound Wave Circle (#6)
- Microphone Input: Scrolling Fill (constantly scrolling timeline)
"""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)


class FinalVisualizerApp(App):
    """Demo of your final chosen visualizer configuration."""

    TITLE = "xSwarm Voice Visualizer - Final Configuration"

    CSS = """
    FinalVisualizerApp {
        background: #0a0e27;
    }

    #container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    VoiceVisualizerPanel {
        width: 100%;
        height: 100%;
        border: solid #00d4ff;
    }
    """

    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the final visualizer."""
        yield Header()

        with Container(id="container"):
            # Your chosen configuration
            panel = VoiceVisualizerPanel(
                visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                microphone_waveform_style=MicrophoneWaveformStyle.SCROLLING_FILL,
            )
            panel.simulation_mode = True
            panel.start_animation()
            yield panel

        yield Footer()

    def action_quit(self) -> None:
        """Quit the application."""
        panel = self.query_one(VoiceVisualizerPanel)
        panel.stop_animation()
        self.exit()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("xSwarm Voice Visualizer - Your Final Configuration")
    print("=" * 70)
    print()
    print("Assistant Speaking: Sound Wave Circle")
    print("  - Organic wave pattern around circle perimeter")
    print("  - Radius modulates with voice amplitude")
    print()
    print("Microphone Input: Scrolling Fill")
    print("  - Constantly scrolling timeline (right to left)")
    print("  - Fills in (thick bars) when you speak")
    print("  - Stays thin during silence")
    print("  - Filled bits scroll off the screen")
    print()
    print("Press 'q' or 'Escape' to exit")
    print("=" * 70 + "\n")

    app = FinalVisualizerApp()
    app.run()
