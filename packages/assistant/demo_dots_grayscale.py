#!/usr/bin/env python3
"""
Microphone Dots - Grayscale, Right-Scrolling Demo
Shows the final microphone visualization scrolling in real-time.
Uses ANSI escape codes to animate in the terminal.
"""

import time
import math
import sys


def render_dots_grayscale(data):
    """Render dots with grayscale intensity, newest on left (right-scrolling)."""
    dot_chars = [" ", "·", "•", "●", "⬤"]
    result = ""

    # Render from end of buffer backwards for right-scrolling (newest on left)
    for amp in reversed(data):
        char_idx = int(amp * (len(dot_chars) - 1))
        char = dot_chars[char_idx]

        # Grayscale intensity based on amplitude
        if amp > 0.8:
            result += f"\033[1;37m{char}\033[0m"  # Bold bright white
        elif amp > 0.6:
            result += f"\033[37m{char}\033[0m"    # Bright white
        elif amp > 0.4:
            result += f"\033[90m{char}\033[0m"    # Medium gray (bright black)
        elif amp > 0.2:
            result += f"\033[2;37m{char}\033[0m"  # Light gray (dim white)
        else:
            result += f"\033[2;90m{char}\033[0m"  # Dark gray (dim bright black)

    return result


def main():
    """Animate the microphone dots waveform."""
    print("\n" + "=" * 80)
    print("MICROPHONE DOTS - Grayscale, Right-Scrolling")
    print("=" * 80)
    print("\nWatch the dots scroll RIGHT as new audio data comes in on the LEFT!")
    print("Intensity: Bright white (loud) → White → Gray → Light gray → Dark (quiet)")
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

            # Scroll buffer (new data goes on right, we reverse when rendering)
            amplitude_buffer.pop(0)
            amplitude_buffer.append(amplitude)

            # Clear line and render
            print("\033[2K\r", end="")  # Clear line
            print("Mic Input: ", end="")
            print(render_dots_grayscale(amplitude_buffer), end="")

            # Show current amplitude
            amp_bar = "█" * int(amplitude * 20)
            print(f"  [{amp_bar:<20}] {amplitude:.2f}", end="")

            sys.stdout.flush()

            frame += 1
            time.sleep(1/20)  # 20 FPS

    except KeyboardInterrupt:
        # Show cursor again
        print("\033[?25h")
        print("\n\n" + "=" * 80)
        print("Animation stopped.")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    print("\nThis will show the FINAL microphone visualization:")
    print("  • Dots with grayscale intensity")
    print("  • Scrolls RIGHT (new data appears on LEFT)")
    print("  • 5 intensity levels from bright white to dark gray")
    print("\nReady? Press Enter to start (Ctrl+C to stop later)...")
    input()

    main()
