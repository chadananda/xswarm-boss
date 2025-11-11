#!/usr/bin/env python3
"""
Microphone Waveform Style Demo - Compare all 4 styles.

Shows Sound Wave Circle (your chosen assistant visualization)
with all 4 microphone waveform styles to choose from.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Vertical
from textual.widgets import Header, Footer, Label

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)


class MicWaveformDemoApp(App):
    """Demo app showing all 4 microphone waveform styles."""

    TITLE = "Microphone Waveform Styles - Choose Your Favorite"

    CSS = """
    MicWaveformDemoApp {
        background: #0a0e27;
    }

    #demo-container {
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    #viz-grid {
        grid-size: 2 2;
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
    """

    BINDINGS = [
        ("escape", "dismiss", "Quit"),
        ("q", "dismiss", "Quit"),
        ("1", "choose_vertical_bars", "Choose #1"),
        ("2", "choose_wave_chars", "Choose #2"),
        ("3", "choose_line", "Choose #3"),
        ("4", "choose_dots", "Choose #4"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo screen layout."""
        yield Header()

        with Container(id="demo-container"):
            with Grid(id="viz-grid"):
                # Style 1: Vertical Bars (RECOMMENDED)
                with Vertical(classes="viz-container"):
                    yield Label("1. Vertical Bars ▁▂▃▄▅▆▇█ (RECOMMENDED)", classes="viz-label")
                    panel1 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.VERTICAL_BARS,
                    )
                    panel1.simulation_mode = True
                    panel1.start_animation()
                    yield panel1

                # Style 2: Wave Characters
                with Vertical(classes="viz-container"):
                    yield Label("2. Wave Characters ◡◠", classes="viz-label")
                    panel2 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.WAVE_CHARACTERS,
                    )
                    panel2.simulation_mode = True
                    panel2.start_animation()
                    yield panel2

                # Style 3: Line Wave
                with Vertical(classes="viz-container"):
                    yield Label("3. Line Wave", classes="viz-label")
                    panel3 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.LINE_WAVE,
                    )
                    panel3.simulation_mode = True
                    panel3.start_animation()
                    yield panel3

                # Style 4: Dots
                with Vertical(classes="viz-container"):
                    yield Label("4. Dots ·•●⬤", classes="viz-label")
                    panel4 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.DOTS,
                    )
                    panel4.simulation_mode = True
                    panel4.start_animation()
                    yield panel4

        yield Footer()

    def action_dismiss(self) -> None:
        """Dismiss the demo screen."""
        panels = self.query(VoiceVisualizerPanel)
        for panel in panels:
            panel.stop_animation()
        self.exit()

    def action_choose_vertical_bars(self) -> None:
        """User chose vertical bars."""
        self.exit(message="You chose: Vertical Bars (Classic audio waveform)")

    def action_choose_wave_chars(self) -> None:
        """User chose wave characters."""
        self.exit(message="You chose: Wave Characters")

    def action_choose_line(self) -> None:
        """User chose line wave."""
        self.exit(message="You chose: Line Wave")

    def action_choose_dots(self) -> None:
        """User chose dots."""
        self.exit(message="You chose: Dots")


if __name__ == "__main__":
    app = MicWaveformDemoApp()
    result = app.run()
    if result:
        print(f"\n{result}")
