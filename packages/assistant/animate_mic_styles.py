#!/usr/bin/env python3
"""
Animated Microphone Styles Demo
Shows #1 (Scrolling Fill) and #5 (Dots) animating in the terminal.
Uses ANSI escape codes to update in place - shows the ACTUAL scrolling effect!
"""

import time
import math
import sys


def render_scrolling_fill(data):
    """Render scrolling fill style with colors."""
    chars = ["─", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    result = ""

    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]

        # ANSI color codes
        if amp > 0.7:
            result += f"\033[1;31m{char}\033[0m"  # Bold red
        elif amp > 0.5:
            result += f"\033[1;33m{char}\033[0m"  # Bold yellow
        elif amp > 0.3:
            result += f"\033[1;32m{char}\033[0m"  # Bold green
        elif amp > 0.1:
            result += f"\033[36m{char}\033[0m"    # Cyan
        else:
            result += f"\033[2;37m{char}\033[0m"  # Dim white

    return result


def render_dots(data):
    """Render dots style with colors."""
    chars = [" ", "·", "•", "●", "⬤"]
    result = ""

    for amp in data:
        char_idx = int(amp * (len(chars) - 1))
        char = chars[char_idx]

        if amp > 0.7:
            result += f"\033[1;31m{char}\033[0m"  # Bold red
        elif amp > 0.4:
            result += f"\033[1;33m{char}\033[0m"  # Bold yellow
        elif amp > 0.1:
            result += f"\033[1;32m{char}\033[0m"  # Bold green
        else:
            result += f"\033[36m{char}\033[0m"    # Cyan

    return result


def main():
    """Animate the waveforms in real-time."""
    print("\n" + "=" * 80)
    print("ANIMATED MICROPHONE WAVEFORMS - Watch them scroll!")
    print("=" * 80)
    print("\nPress Ctrl+C to stop\n")

    # Buffer for amplitude data
    buffer_size = 70
    amplitude_buffer = [0.0] * buffer_size

    frame = 0

    try:
        # Hide cursor
        print("\033[?25l", end="")

        while True:
            # Generate new amplitude (sine wave with variation)
            phase = frame * 0.15
            amplitude = (math.sin(phase) + 1) / 2
            amplitude += (math.sin(phase * 2.5) * 0.3)
            amplitude = max(0.0, min(1.0, amplitude))

            # Scroll buffer (move everything left, add new value on right)
            amplitude_buffer.pop(0)
            amplitude_buffer.append(amplitude)

            # Clear previous lines and render
            print("\033[2K\r", end="")  # Clear line
            print("1. SCROLLING FILL (fills when loud, stays thin when quiet):")
            print("\033[2K\r   ", end="")
            print(render_scrolling_fill(amplitude_buffer))

            print("\033[2K\r")
            print("5. DOTS (larger dots when loud, small when quiet):")
            print("\033[2K\r   ", end="")
            print(render_dots(amplitude_buffer))

            # Move cursor back up to overwrite
            print("\033[5A", end="")  # Move up 5 lines

            frame += 1
            time.sleep(1/20)  # 20 FPS

    except KeyboardInterrupt:
        # Show cursor again
        print("\033[?25h")
        print("\n\n\n\n\n")  # Move past the animation area
        print("\n" + "=" * 80)
        print("Animation stopped.")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\nThis will show LIVE SCROLLING animation of styles #1 and #5.")
    print("Watch the waveforms scroll from RIGHT to LEFT as new data comes in!")
    print("\nReady? Press Enter to start (Ctrl+C to stop later)...")
    input()

    main()
