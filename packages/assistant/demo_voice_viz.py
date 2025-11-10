#!/usr/bin/env python3
"""
Voice Visualizer Demo App

Shows all 6 visualization styles in a 3x2 grid for easy comparison.
Run this to see all the styles in action and decide which to keep!

Usage:
    python demo_voice_viz.py

Press 'q' or 'Escape' to exit.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Vertical
from textual.widgets import Header, Footer, Label

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
)


class VoiceVizDemoApp(App):
    """Demo app showing all 6 voice visualization styles."""

    TITLE = "Voice Visualizer Style Comparison"

    CSS = """
    Screen {
        background: #0a0e27;
    }

    #demo-container {
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    #viz-grid {
        grid-size: 3 2;
        grid-gutter: 1 1;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    .viz-container {
        border: solid #00d4ff;
        height: 100%;
        width: 100%;
        min-height: 0;
        overflow: hidden;
    }

    .viz-label {
        background: #1a1f3a;
        color: #00d4ff;
        text-align: center;
        height: auto;
        max-height: 1;
        text-style: bold;
        padding: 0;
    }

    VoiceVisualizerPanel {
        height: 1fr;
        min-height: 0;
        border: none;
        overflow: hidden;
    }

    Footer {
        background: #1a1f3a;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo layout."""
        yield Header()

        with Container(id="demo-container"):
            with Grid(id="viz-grid"):
                # Style 1: Concentric Circles
                with Vertical(classes="viz-container"):
                    yield Label("1. CONCENTRIC CIRCLES", classes="viz-label")
                    panel1 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.CONCENTRIC_CIRCLES
                    )
                    panel1.simulation_mode = True
                    panel1.start_animation()
                    yield panel1

                # Style 2: Ripple Waves
                with Vertical(classes="viz-container"):
                    yield Label("2. RIPPLE WAVES", classes="viz-label")
                    panel2 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.RIPPLE_WAVES
                    )
                    panel2.simulation_mode = True
                    panel2.start_animation()
                    yield panel2

                # Style 3: Circular Bars
                with Vertical(classes="viz-container"):
                    yield Label("3. CIRCULAR BARS", classes="viz-label")
                    panel3 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.CIRCULAR_BARS
                    )
                    panel3.simulation_mode = True
                    panel3.start_animation()
                    yield panel3

                # Style 4: Pulsing Dots
                with Vertical(classes="viz-container"):
                    yield Label("4. PULSING DOTS", classes="viz-label")
                    panel4 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.PULSING_DOTS
                    )
                    panel4.simulation_mode = True
                    panel4.start_animation()
                    yield panel4

                # Style 5: Spinning Indicator
                with Vertical(classes="viz-container"):
                    yield Label("5. SPINNING INDICATOR", classes="viz-label")
                    panel5 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SPINNING_INDICATOR
                    )
                    panel5.simulation_mode = True
                    panel5.start_animation()
                    yield panel5

                # Style 6: Sound Wave Circle
                with Vertical(classes="viz-container"):
                    yield Label("6. SOUND WAVE CIRCLE", classes="viz-label")
                    panel6 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE
                    )
                    panel6.simulation_mode = True
                    panel6.start_animation()
                    yield panel6

        yield Footer()

    def on_unmount(self) -> None:
        """Stop animations when unmounting."""
        panels = self.query(VoiceVisualizerPanel)
        for panel in panels:
            panel.stop_animation()


def main():
    """Run the demo app."""
    app = VoiceVizDemoApp()
    app.run()


if __name__ == "__main__":
    main()
