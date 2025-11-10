"""
Pulsing circle audio visualizer.
CRITICAL USER REQUIREMENT: Pulses based on MOSHI amplitude changes.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
import math


class AudioVisualizer(Static):
    """
    Pulsing circle that responds to audio amplitude.

    States:
    - idle: Cyan, small radius, slow pulse
    - listening: Green, medium radius, fast pulse
    - speaking: Yellow, large radius, amplitude-driven pulse
    - thinking: Magenta, medium radius, rotating
    - error: Red, small radius, no pulse
    """

    amplitude = reactive(0.0)  # 0.0 - 1.0
    state = reactive("idle")
    _frame = reactive(0)

    def on_mount(self) -> None:
        """Start animation timer"""
        self.set_interval(1/30, self.tick)  # 30 FPS animation

    def tick(self) -> None:
        """Update animation frame"""
        self._frame = (self._frame + 1) % 360
        self.refresh()

    def render(self) -> Text:
        """Render the pulsing circle"""
        width = self.size.width
        height = self.size.height

        if width < 20 or height < 10:
            return Text("(window too small)", style="dim")

        # Calculate center
        cx = width // 2
        cy = height // 2

        # Base radius (scales with window size)
        base_radius = min(width // 4, height // 2 - 2)

        # State-specific behavior
        if self.state == "idle":
            # Small, slow breathing
            pulse = math.sin(self._frame * 0.02) * 0.2 + 1.0
            radius = int(base_radius * 0.5 * pulse)
            color = "cyan"
            char = "●"

        elif self.state == "listening":
            # Medium, fast breathing
            pulse = math.sin(self._frame * 0.1) * 0.3 + 1.0
            radius = int(base_radius * 0.7 * pulse)
            color = "green"
            char = "●"

        elif self.state == "speaking":
            # Large, amplitude-driven
            # Map amplitude (0-1) to radius multiplier (0.5-1.5)
            amplitude_scale = 0.5 + self.amplitude * 1.0
            radius = int(base_radius * amplitude_scale)
            color = "yellow"
            char = "●"

        elif self.state == "thinking":
            # Rotating arc
            pulse = math.sin(self._frame * 0.05) * 0.2 + 1.0
            radius = int(base_radius * 0.8 * pulse)
            color = "magenta"
            char = "◐◓◑◒"[self._frame % 4]  # Rotating

        elif self.state == "error":
            # Static, small
            radius = int(base_radius * 0.4)
            color = "red"
            char = "✖"

        else:  # ready, etc.
            radius = int(base_radius * 0.6)
            color = "blue"
            char = "●"

        # Render circle
        lines = []
        for y in range(height):
            line = ""
            for x in range(width):
                dx = x - cx
                dy = (y - cy) * 2  # Compensate for character aspect ratio
                dist = math.sqrt(dx*dx + dy*dy)

                if abs(dist - radius) < 2:
                    # On the circle edge
                    line += char
                elif dist < radius:
                    # Inside circle (optional fill)
                    line += "·" if self.state == "speaking" else " "
                else:
                    line += " "
            lines.append(line)

        # Create styled text
        result = Text()
        for line in lines:
            result.append(line + "\n", style=f"bold {color}")

        return result


class AudioVisualizerAdvanced(Static):
    """
    Advanced pulsing circle with smooth gradients and better animations.
    Uses Unicode box drawing characters for smoother circles.
    """

    amplitude = reactive(0.0)
    state = reactive("idle")
    _frame = reactive(0)
    _history = []  # Amplitude history for smoothing

    def on_mount(self) -> None:
        self.set_interval(1/30, self.tick)
        self._history = [0.0] * 10  # 10-frame smoothing

    def tick(self) -> None:
        self._frame = (self._frame + 1) % 360

        # Update amplitude history
        self._history.append(self.amplitude)
        if len(self._history) > 10:
            self._history.pop(0)

        self.refresh()

    def render(self) -> Text:
        """Render with smooth amplitude response"""
        width = self.size.width
        height = self.size.height

        if width < 30 or height < 15:
            return Text("Resize window for better visualization", style="dim")

        cx = width // 2
        cy = height // 2

        # Smooth amplitude (average of recent frames)
        smooth_amplitude = sum(self._history) / len(self._history) if self._history else 0.0

        # Calculate radius based on state and amplitude
        base_radius = min(width // 4, height // 2 - 2)

        if self.state == "idle":
            pulse = math.sin(self._frame * 0.03) * 0.15 + 1.0
            radius = base_radius * 0.5 * pulse
            color = "cyan"

        elif self.state == "listening":
            pulse = math.sin(self._frame * 0.08) * 0.25 + 1.0
            radius = base_radius * 0.7 * pulse
            color = "green"

        elif self.state == "speaking":
            # Responsive to amplitude with smoothing
            amplitude_scale = 0.6 + smooth_amplitude * 0.8
            radius = base_radius * amplitude_scale
            color = "yellow"

        elif self.state == "thinking":
            angle = self._frame * 0.05
            pulse = math.sin(angle) * 0.2 + 1.0
            radius = base_radius * 0.75 * pulse
            color = "magenta"

        else:
            radius = base_radius * 0.6
            color = "blue"

        # Render with gradient effect
        result = Text()

        for y in range(height):
            line = []
            for x in range(width):
                dx = x - cx
                dy = (y - cy) * 2
                dist = math.sqrt(dx*dx + dy*dy)

                # Distance from circle edge
                edge_dist = abs(dist - radius)

                if edge_dist < 1.5:
                    # On edge - bright
                    line.append(("●", f"bold {color}"))
                elif edge_dist < 3:
                    # Near edge - medium
                    line.append(("○", color))
                elif dist < radius and self.state == "speaking":
                    # Inside when speaking - faint fill
                    if edge_dist < radius * 0.3:
                        line.append(("·", f"dim {color}"))
                    else:
                        line.append((" ", ""))
                else:
                    line.append((" ", ""))

            # Construct line with styles
            for char, style in line:
                result.append(char, style=style)
            result.append("\n")

        return result
