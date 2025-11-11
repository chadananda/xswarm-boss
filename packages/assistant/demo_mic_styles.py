#!/usr/bin/env python3
"""
Microphone Waveform Styles Demo - Sequential View
Shows one microphone waveform style at a time in fullscreen.
Press 1-5 to switch between styles.
"""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)


class MicStylesDemoApp(App):
    """Demo showing microphone waveform styles one at a time."""

    TITLE = "Microphone Waveform Styles Demo"

    current_style = reactive(0)

    STYLES = [
        (MicrophoneWaveformStyle.SCROLLING_FILL, "1. Scrolling Fill ─▁▂▃▄▅▆▇█ (Timeline)"),
        (MicrophoneWaveformStyle.VERTICAL_BARS, "2. Vertical Bars ▁▂▃▄▅▆▇█ (Classic)"),
        (MicrophoneWaveformStyle.WAVE_CHARACTERS, "3. Wave Characters ◡◠ (Simple)"),
        (MicrophoneWaveformStyle.LINE_WAVE, "4. Line Wave (Continuous)"),
        (MicrophoneWaveformStyle.DOTS, "5. Dots ·•●⬤ (Minimalist)"),
    ]

    CSS = """
    MicStylesDemoApp {
        background: #0a0e27;
    }

    #container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #instructions {
        background: #1a1f3a;
        color: #00d4ff;
        text-align: center;
        height: 3;
        content-align: center middle;
        text-style: bold;
    }

    VoiceVisualizerPanel {
        width: 100%;
        height: 1fr;
        border: solid #00d4ff;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("escape", "quit", "Quit"),
        ("q", "quit", "Quit"),
        ("1", "style_1", "Style 1"),
        ("2", "style_2", "Style 2"),
        ("3", "style_3", "Style 3"),
        ("4", "style_4", "Style 4"),
        ("5", "style_5", "Style 5"),
        ("left", "prev_style", "Previous"),
        ("right", "next_style", "Next"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo."""
        yield Header()

        with Container(id="container"):
            yield Static(self._get_instructions(), id="instructions")
            yield self._create_panel(0)

        yield Footer()

    def _get_instructions(self) -> str:
        """Get instruction text for current style."""
        style_enum, style_name = self.STYLES[self.current_style]
        return f"{style_name}\n\nPress 1-5 to switch styles | ← → to navigate | Q to quit"

    def _create_panel(self, style_index: int) -> VoiceVisualizerPanel:
        """Create panel with given style."""
        style_enum, _ = self.STYLES[style_index]
        panel = VoiceVisualizerPanel(
            visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE,
            microphone_waveform_style=style_enum,
        )
        panel.simulation_mode = True
        panel.start_animation()
        return panel

    def watch_current_style(self, old_style: int, new_style: int) -> None:
        """React to style changes."""
        # Stop old panel
        try:
            old_panel = self.query_one(VoiceVisualizerPanel)
            old_panel.stop_animation()
            old_panel.remove()
        except:
            pass

        # Update instructions
        instructions = self.query_one("#instructions", Static)
        instructions.update(self._get_instructions())

        # Add new panel
        container = self.query_one("#container", Container)
        container.mount(self._create_panel(new_style))

    def action_style_1(self) -> None:
        """Switch to style 1."""
        self.current_style = 0

    def action_style_2(self) -> None:
        """Switch to style 2."""
        self.current_style = 1

    def action_style_3(self) -> None:
        """Switch to style 3."""
        self.current_style = 2

    def action_style_4(self) -> None:
        """Switch to style 4."""
        self.current_style = 3

    def action_style_5(self) -> None:
        """Switch to style 5."""
        self.current_style = 4

    def action_prev_style(self) -> None:
        """Go to previous style."""
        self.current_style = (self.current_style - 1) % len(self.STYLES)

    def action_next_style(self) -> None:
        """Go to next style."""
        self.current_style = (self.current_style + 1) % len(self.STYLES)

    def action_quit(self) -> None:
        """Quit the application."""
        try:
            panel = self.query_one(VoiceVisualizerPanel)
            panel.stop_animation()
        except:
            pass

        style_enum, style_name = self.STYLES[self.current_style]
        self.exit(message=f"\n✅ Last viewed: {style_name}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Microphone Waveform Styles Demo")
    print("=" * 70)
    print()
    print("This demo shows different microphone waveform visualizations.")
    print("Look at the BOTTOM of each panel - that's the microphone activity line!")
    print()
    print("Controls:")
    print("  1-5: Switch between styles")
    print("  ←→: Navigate prev/next")
    print("  Q: Quit")
    print()
    print("=" * 70 + "\n")

    app = MicStylesDemoApp()
    result = app.run()
    if result:
        print(result)
