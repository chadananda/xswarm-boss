#!/usr/bin/env python3
"""
Simple console demo showing all 5 microphone waveform styles.
No TUI, no microphone - just prints the different visualizations.
"""

import math
from rich.console import Console
from rich.text import Text

# Generate fake amplitude data (sine wave)
def generate_fake_audio(length=80):
    """Generate fake amplitude data for demo."""
    data = []
    for i in range(length):
        # Create a varying sine wave
        amplitude = (math.sin(i * 0.15) + 1) / 2  # 0.0 to 1.0
        amplitude += (math.sin(i * 0.4) * 0.3)  # Add variation
        amplitude = max(0.0, min(1.0, amplitude))  # Clamp
        data.append(amplitude)
    return data


def render_scrolling_fill(data):
    """Style 1: Scrolling Fill (timeline that fills when speaking)."""
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
        elif amp > 0.1:
            result.append(char, style="cyan")
        else:
            result.append(char, style="dim white")

    return result


def render_vertical_bars(data):
    """Style 2: Vertical Bars (classic waveform)."""
    chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    result = Text()

    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]

        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.4:
            result.append(char, style="bold yellow")
        elif amp > 0.1:
            result.append(char, style="bold green")
        else:
            result.append(char, style="dim cyan")

    return result


def render_wave_characters(data):
    """Style 3: Wave Characters (simple waves)."""
    chars = [" ", "◡", "◠", "◡", "◠"]
    result = Text()

    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]

        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.4:
            result.append(char, style="bold yellow")
        elif amp > 0.1:
            result.append(char, style="bold cyan")
        else:
            result.append(char, style="dim white")

    return result


def render_line_wave(data):
    """Style 4: Line Wave (continuous line)."""
    chars = ["_", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "▔"]
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
        elif amp > 0.1:
            result.append(char, style="cyan")
        else:
            result.append(char, style="dim white")

    return result


def render_dots(data):
    """Style 5: Dots (minimalist)."""
    chars = [" ", "·", "•", "●", "⬤"]
    result = Text()

    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]

        if amp > 0.7:
            result.append(char, style="bold red")
        elif amp > 0.4:
            result.append(char, style="bold yellow")
        elif amp > 0.1:
            result.append(char, style="bold green")
        else:
            result.append(char, style="dim cyan")

    return result


def main():
    """Show all microphone waveform styles."""
    console = Console()

    console.print("\n" + "=" * 80, style="bold cyan")
    console.print("Microphone Waveform Styles Comparison", style="bold cyan", justify="center")
    console.print("=" * 80 + "\n", style="bold cyan")

    console.print("Showing the same fake audio data rendered in 5 different styles:\n")

    # Generate fake audio data
    audio_data = generate_fake_audio(80)

    # Style 1: Scrolling Fill
    console.print("1. SCROLLING FILL (Timeline that fills when speaking)", style="bold yellow")
    console.print("   Characters: ─▁▂▃▄▅▆▇█")
    console.print("   ", end="")
    console.print(render_scrolling_fill(audio_data))
    console.print()

    # Style 2: Vertical Bars
    console.print("2. VERTICAL BARS (Classic audio waveform)", style="bold yellow")
    console.print("   Characters: ▁▂▃▄▅▆▇█")
    console.print("   ", end="")
    console.print(render_vertical_bars(audio_data))
    console.print()

    # Style 3: Wave Characters
    console.print("3. WAVE CHARACTERS (Simple waves)", style="bold yellow")
    console.print("   Characters: ◡◠")
    console.print("   ", end="")
    console.print(render_wave_characters(audio_data))
    console.print()

    # Style 4: Line Wave
    console.print("4. LINE WAVE (Continuous line)", style="bold yellow")
    console.print("   Characters: _▁▂▃▄▅▆▇▔")
    console.print("   ", end="")
    console.print(render_line_wave(audio_data))
    console.print()

    # Style 5: Dots
    console.print("5. DOTS (Minimalist)", style="bold yellow")
    console.print("   Characters: ·•●⬤")
    console.print("   ", end="")
    console.print(render_dots(audio_data))
    console.print()

    console.print("\n" + "=" * 80, style="bold cyan")
    console.print("\nKey Differences:", style="bold cyan")
    console.print("  • Scrolling Fill: Uses ─ for silence, fills up to █ for loud")
    console.print("  • Vertical Bars: Uses space for silence, classic equalizer bars")
    console.print("  • Wave Characters: Only uses ◡ and ◠ wave symbols")
    console.print("  • Line Wave: Smooth line from _ to ▔")
    console.print("  • Dots: Minimalist with just dot sizes")
    console.print("\nColors: Red=Loud, Yellow=Medium, Green=Quiet, Cyan=Very Quiet, White=Silent\n")


if __name__ == "__main__":
    main()
