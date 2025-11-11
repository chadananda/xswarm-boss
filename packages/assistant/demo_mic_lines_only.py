#!/usr/bin/env python3
"""
Microphone Waveform Lines ONLY - Direct Comparison
Shows just the microphone waveform lines without the circular visualization.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from rich.text import Text
import math

from assistant.dashboard.widgets.panels import MicrophoneWaveformStyle


class MicLinesDemoApp(App):
    """Demo showing just microphone waveform lines."""

    TITLE = "Microphone Waveform Lines - Direct Comparison"

    _frame = reactive(0)
    _amplitude_buffer = []

    CSS = """
    MicLinesDemoApp {
        background: #0a0e27;
    }

    #container {
        width: 100%;
        height: 100%;
        padding: 2;
    }

    .waveform-block {
        background: #1a1f3a;
        border: solid #00d4ff;
        height: 5;
        margin-bottom: 1;
        padding: 1;
    }

    .style-label {
        color: #00d4ff;
        text-style: bold;
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
            # Create blocks for each style
            for style in MicrophoneWaveformStyle:
                with Vertical(classes="waveform-block"):
                    yield Static(f"{style.name.replace('_', ' ').title()}", classes="style-label")
                    yield Static("", id=f"wave_{style.name}")

        yield Footer()

    def on_mount(self) -> None:
        """Start animation."""
        # Initialize amplitude buffer with 100 samples
        self._amplitude_buffer = [0.0] * 100
        self.set_interval(1/20, self.update_waveforms)

    def update_waveforms(self) -> None:
        """Update all waveform displays."""
        self._frame += 1

        # Generate simulated amplitude (sine wave with noise)
        phase = self._frame * 0.1
        amplitude = (math.sin(phase) + 1) / 2
        amplitude += (math.sin(phase * 2) * 0.2)
        amplitude = max(0.0, min(1.0, amplitude))

        # Update buffer (scroll left)
        self._amplitude_buffer.pop(0)
        self._amplitude_buffer.append(amplitude)

        # Update each waveform display
        for style in MicrophoneWaveformStyle:
            widget = self.query_one(f"#wave_{style.name}", Static)
            text = self.render_waveform(style, 70)  # 70 chars wide
            widget.update(text)

    def render_waveform(self, style: MicrophoneWaveformStyle, width: int) -> Text:
        """Render a waveform with the given style."""
        result = Text()

        samples_per_char = len(self._amplitude_buffer) // width
        if samples_per_char == 0:
            samples_per_char = 1

        for i in range(min(width, len(self._amplitude_buffer))):
            start_idx = i * samples_per_char
            end_idx = min(start_idx + samples_per_char, len(self._amplitude_buffer))

            if start_idx < len(self._amplitude_buffer):
                avg_amp = sum(self._amplitude_buffer[start_idx:end_idx]) / max(1, end_idx - start_idx)

                # Render based on style
                if style == MicrophoneWaveformStyle.SCROLLING_FILL:
                    chars = ["─", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                    char_idx = int(avg_amp * (len(chars) - 1))
                    char = chars[char_idx]

                elif style == MicrophoneWaveformStyle.VERTICAL_BARS:
                    chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                    char_idx = int(avg_amp * (len(chars) - 1))
                    char = chars[char_idx]

                elif style == MicrophoneWaveformStyle.WAVE_CHARACTERS:
                    chars = [" ", "◡", "◠", "◡", "◠"]
                    char_idx = int(avg_amp * (len(chars) - 1))
                    char = chars[char_idx]

                elif style == MicrophoneWaveformStyle.LINE_WAVE:
                    chars = ["_", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "▔"]
                    char_idx = int(avg_amp * (len(chars) - 1))
                    char = chars[char_idx]

                elif style == MicrophoneWaveformStyle.DOTS:
                    chars = [" ", "·", "•", "●", "⬤"]
                    char_idx = int(avg_amp * (len(chars) - 1))
                    char = chars[char_idx]
                else:
                    char = "?"

                # Color based on amplitude
                if avg_amp > 0.7:
                    result.append(char, style="bold red")
                elif avg_amp > 0.5:
                    result.append(char, style="bold yellow")
                elif avg_amp > 0.3:
                    result.append(char, style="bold green")
                elif avg_amp > 0.1:
                    result.append(char, style="cyan")
                else:
                    result.append(char, style="dim white")

        return result

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Microphone Waveform Lines - Direct Comparison")
    print("=" * 70)
    print()
    print("This shows ONLY the microphone waveform lines.")
    print("Watch how each style visualizes the same audio data differently:")
    print()
    print("1. SCROLLING FILL - Timeline with fill levels (─▁▂▃▄▅▆▇█)")
    print("2. VERTICAL BARS - Classic audio waveform (▁▂▃▄▅▆▇█)")
    print("3. WAVE CHARACTERS - Simple wave symbols (◡◠)")
    print("4. LINE WAVE - Continuous line (_▁▂▃▄▅▆▇▔)")
    print("5. DOTS - Minimalist dots (·•●⬤)")
    print()
    print("Press Q to quit")
    print("=" * 70 + "\n")

    app = MicLinesDemoApp()
    app.run()
