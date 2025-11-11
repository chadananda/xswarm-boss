#!/usr/bin/env python3
"""
All Microphone Waveform Styles Demo
Shows all 5 microphone waveform styles with Sound Wave Circle assistant visualization.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Vertical
from textual.widgets import Header, Footer, Label

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)


class AllMicWaveformsDemoApp(App):
    """Demo app showing all 5 microphone waveform styles."""

    TITLE = "All Microphone Waveform Styles - Choose Your Favorite"

    CSS = """
    AllMicWaveformsDemoApp {
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
    """

    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("q", "quit", "Quit"),
        ("1", "choose_1", "Choose #1"),
        ("2", "choose_2", "Choose #2"),
        ("3", "choose_3", "Choose #3"),
        ("4", "choose_4", "Choose #4"),
        ("5", "choose_5", "Choose #5"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo screen layout."""
        yield Header()

        with Container(id="demo-container"):
            with Grid(id="viz-grid"):
                # Style 1: Scrolling Fill
                with Vertical(classes="viz-container"):
                    yield Label("1. Scrolling Fill ─▁▂▃▄▅▆▇█ (Timeline)", classes="viz-label")
                    panel1 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.SCROLLING_FILL,
                    )
                    panel1.simulation_mode = True
                    panel1.start_animation()
                    yield panel1

                # Style 2: Vertical Bars
                with Vertical(classes="viz-container"):
                    yield Label("2. Vertical Bars ▁▂▃▄▅▆▇█ (Classic)", classes="viz-label")
                    panel2 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.VERTICAL_BARS,
                    )
                    panel2.simulation_mode = True
                    panel2.start_animation()
                    yield panel2

                # Style 3: Wave Characters
                with Vertical(classes="viz-container"):
                    yield Label("3. Wave Characters ◡◠ (Simple)", classes="viz-label")
                    panel3 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.WAVE_CHARACTERS,
                    )
                    panel3.simulation_mode = True
                    panel3.start_animation()
                    yield panel3

                # Style 4: Line Wave
                with Vertical(classes="viz-container"):
                    yield Label("4. Line Wave (Continuous)", classes="viz-label")
                    panel4 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.LINE_WAVE,
                    )
                    panel4.simulation_mode = True
                    panel4.start_animation()
                    yield panel4

                # Style 5: Dots
                with Vertical(classes="viz-container"):
                    yield Label("5. Dots ·•●⬤ (Minimalist)", classes="viz-label")
                    panel5 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
                        microphone_waveform_style=MicrophoneWaveformStyle.DOTS,
                    )
                    panel5.simulation_mode = True
                    panel5.start_animation()
                    yield panel5

                # Empty cell (3x2 grid, only 5 items)
                with Vertical(classes="viz-container"):
                    yield Label("Press 1-5 to choose, Q to quit", classes="viz-label")

        yield Footer()

    def action_quit(self) -> None:
        """Quit the application."""
        panels = self.query(VoiceVisualizerPanel)
        for panel in panels:
            panel.stop_animation()
        self.exit()

    def action_choose_1(self) -> None:
        """User chose scrolling fill."""
        self.action_quit()
        print("\n✅ You chose: #1 Scrolling Fill (Timeline that fills when speaking)")

    def action_choose_2(self) -> None:
        """User chose vertical bars."""
        self.action_quit()
        print("\n✅ You chose: #2 Vertical Bars (Classic audio waveform)")

    def action_choose_3(self) -> None:
        """User chose wave characters."""
        self.action_quit()
        print("\n✅ You chose: #3 Wave Characters (Simple waves)")

    def action_choose_4(self) -> None:
        """User chose line wave."""
        self.action_quit()
        print("\n✅ You chose: #4 Line Wave (Continuous line)")

    def action_choose_5(self) -> None:
        """User chose dots."""
        self.action_quit()
        print("\n✅ You chose: #5 Dots (Minimalist visualization)")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("All Microphone Waveform Styles")
    print("=" * 70)
    print()
    print("Showing all 5 microphone waveform styles")
    print("Each paired with Sound Wave Circle for assistant speaking")
    print()
    print("1. Scrolling Fill - Timeline that fills when speaking")
    print("2. Vertical Bars - Classic ▁▂▃▄▅▆▇█ waveform")
    print("3. Wave Characters - Simple ◡◠ waves")
    print("4. Line Wave - Continuous line effect")
    print("5. Dots - Minimalist ·•●⬤ visualization")
    print()
    print("Press 1-5 to choose your favorite, or Q to quit")
    print("=" * 70 + "\n")

    app = AllMicWaveformsDemoApp()
    app.run()
