#!/usr/bin/env python3
"""
Working Microphone Waveform Demo
Simpler implementation that definitely shows the waveforms animating.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Static, Label
from rich.text import Text
import math
import asyncio


class WaveformDisplay(Static):
    """A single animated waveform line."""

    def __init__(self, style_name: str, render_func, **kwargs):
        super().__init__(**kwargs)
        self.style_name = style_name
        self.render_func = render_func
        self.frame = 0
        self.amplitude_buffer = [0.0] * 80

    def on_mount(self) -> None:
        """Start animation."""
        self.set_interval(1/20, self.update_waveform)

    def update_waveform(self) -> None:
        """Update the waveform display."""
        self.frame += 1

        # Generate new amplitude value
        phase = self.frame * 0.1
        amplitude = (math.sin(phase) + 1) / 2
        amplitude += (math.sin(phase * 2) * 0.2)
        amplitude = max(0.0, min(1.0, amplitude))

        # Scroll buffer left and add new value
        self.amplitude_buffer.pop(0)
        self.amplitude_buffer.append(amplitude)

        # Render and update
        text = self.render_func(self.amplitude_buffer)
        self.update(text)


def render_scrolling_fill(data):
    """Render scrolling fill style."""
    chars = ["─", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    result = Text()
    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]
        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.5:
            result.append(char, style="bold yellow")
        elif amp > 0.3:
            result.append(char, style="bold green")
        else:
            result.append(char, style="dim cyan")
    return result


def render_vertical_bars(data):
    """Render vertical bars style."""
    chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    result = Text()
    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]
        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.4:
            result.append(char, style="bold yellow")
        else:
            result.append(char, style="bold green")
    return result


def render_wave_chars(data):
    """Render wave characters style."""
    chars = [" ", "◡", "◠", "◡", "◠"]
    result = Text()
    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]
        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.4:
            result.append(char, style="bold yellow")
        else:
            result.append(char, style="bold cyan")
    return result


def render_line_wave(data):
    """Render line wave style."""
    chars = ["_", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "▔"]
    result = Text()
    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]
        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.5:
            result.append(char, style="bold yellow")
        else:
            result.append(char, style="bold green")
    return result


def render_dots(data):
    """Render dots style."""
    chars = [" ", "·", "•", "●", "⬤"]
    result = Text()
    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]
        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.4:
            result.append(char, style="bold yellow")
        else:
            result.append(char, style="bold green")
    return result


class MicWaveformDemoApp(App):
    """Demo app showing all waveform styles."""

    TITLE = "Microphone Waveform Styles - Live Animation"

    CSS = """
    Screen {
        background: #0a0e27;
    }

    VerticalScroll {
        width: 100%;
        height: 100%;
        padding: 2;
    }

    .wave-section {
        margin-bottom: 2;
        border: solid #00d4ff;
        padding: 1;
        height: auto;
    }

    .wave-label {
        color: #00ff00;
        text-style: bold;
        margin-bottom: 1;
    }

    WaveformDisplay {
        height: auto;
        background: #1a1f3a;
        padding: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo."""
        yield Header()

        with VerticalScroll():
            # Style 1: Scrolling Fill
            with Container(classes="wave-section"):
                yield Label("1. SCROLLING FILL (Timeline that fills)", classes="wave-label")
                yield WaveformDisplay("Scrolling Fill", render_scrolling_fill)

            # Style 2: Vertical Bars
            with Container(classes="wave-section"):
                yield Label("2. VERTICAL BARS (Classic waveform)", classes="wave-label")
                yield WaveformDisplay("Vertical Bars", render_vertical_bars)

            # Style 3: Wave Characters
            with Container(classes="wave-section"):
                yield Label("3. WAVE CHARACTERS (Simple waves)", classes="wave-label")
                yield WaveformDisplay("Wave Characters", render_wave_chars)

            # Style 4: Line Wave
            with Container(classes="wave-section"):
                yield Label("4. LINE WAVE (Continuous line)", classes="wave-label")
                yield WaveformDisplay("Line Wave", render_line_wave)

            # Style 5: Dots
            with Container(classes="wave-section"):
                yield Label("5. DOTS (Minimalist)", classes="wave-label")
                yield WaveformDisplay("Dots", render_dots)

        yield Footer()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Microphone Waveform Styles - Live Animation Demo")
    print("=" * 70)
    print()
    print("Watch all 5 styles animate with the same audio data.")
    print("See how each style visualizes amplitude differently.")
    print()
    print("Press Q or Escape to quit")
    print("=" * 70 + "\n")

    app = MicWaveformDemoApp()
    app.run()
