"""
Voice visualizer panel for real-time audio visualization.

Features:
- Scrolling waveform for microphone input
- Multiple circular amplitude visualization styles for assistant speaking
- Smooth 20 FPS animation
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
import math
import random
from dataclasses import dataclass, field
from rich.text import Text
from textual.widgets import Static


class VisualizationStyle(Enum):
    """Circular visualization styles for assistant speaking."""
    CONCENTRIC_CIRCLES = "concentric_circles"
    RIPPLE_WAVES = "ripple_waves"
    CIRCULAR_BARS = "circular_bars"
    PULSING_DOTS = "pulsing_dots"
    SPINNING_INDICATOR = "spinning_indicator"
    SOUND_WAVE_CIRCLE = "sound_wave_circle"


class MicrophoneWaveformStyle(Enum):
    """Microphone waveform visualization styles."""
    SCROLLING_FILL = "scrolling_fill"  # Scrolling timeline that fills when speaking
    VERTICAL_BARS = "vertical_bars"  # Classic audio waveform ▁▂▃▄▅▆▇█
    WAVE_CHARACTERS = "wave_characters"  # Simple wave chars ◡◠
    LINE_WAVE = "line_wave"  # Continuous line wave
    DOTS = "dots"  # Dot pattern visualization


@dataclass
class AudioFrame:
    """Represents a single audio amplitude sample."""
    amplitude: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)


class VoiceVisualizerPanel(Static):
    """
    Voice visualizer panel with real-time audio visualization.

    Features:
    - Scrolling waveform for microphone input (using wave characters ◠ ◡)
    - 6 different circular visualization styles for assistant speaking
    - Smooth 20 FPS animation using set_interval()
    - Simulated audio data for testing
    """

    def __init__(
        self,
        visualization_style: VisualizationStyle = VisualizationStyle.CONCENTRIC_CIRCLES,
        microphone_waveform_style: MicrophoneWaveformStyle = MicrophoneWaveformStyle.DOTS,
        **kwargs
    ):
        """Initialize voice visualizer panel."""
        super().__init__(**kwargs)

        # Visualization settings
        self.visualization_style = visualization_style
        self.microphone_waveform_style = microphone_waveform_style
        self.animation_frame = 0
        self.fps = 20

        # Audio data buffers
        self.mic_waveform: List[float] = []  # Scrolling waveform data
        self.assistant_amplitude: float = 0.0  # Current assistant speaking amplitude

        # Smoothed amplitudes for stable animation
        self._smooth_assistant_amplitude: float = 0.0
        self.smoothing_factor: float = 0.3  # 0.0 = no smoothing, 1.0 = instant

        # Buffer sizes
        self.waveform_buffer_size = 100
        self.mic_waveform = [0.0] * self.waveform_buffer_size

        # Animation state
        self.is_animating = False
        self._animation_timer = None

        # Simulation mode (for testing without real audio)
        # Set to False to use real audio data from mic/Moshi
        self.simulation_mode = False
        self._simulation_phase = 0.0

    def start_animation(self):
        """Start the visualization animation at 20 FPS."""
        if not self.is_animating:
            self.is_animating = True
            self._animation_timer = self.set_interval(1 / self.fps, self._update_animation)

    def stop_animation(self):
        """Stop the visualization animation."""
        if self.is_animating and self._animation_timer:
            self._animation_timer.stop()
            self.is_animating = False

    def _update_animation(self):
        """Animation update callback (called at 20 FPS)."""
        self.animation_frame += 1

        # In simulation mode, generate fake audio data
        if self.simulation_mode:
            self._update_simulated_audio()

        # Apply exponential smoothing to assistant amplitude for stable visuals
        self._smooth_assistant_amplitude = (
            self.smoothing_factor * self.assistant_amplitude +
            (1 - self.smoothing_factor) * self._smooth_assistant_amplitude
        )

        # Refresh the display
        self.refresh()

    def _update_simulated_audio(self):
        """Generate simulated audio data for testing."""
        # Simulate microphone input (scrolling waveform)
        # Use sine wave with some randomness
        self._simulation_phase += 0.1
        amplitude = (math.sin(self._simulation_phase) + 1) / 2  # 0.0 to 1.0
        amplitude += random.uniform(-0.1, 0.1)  # Add noise
        amplitude = max(0.0, min(1.0, amplitude))  # Clamp

        # Scroll waveform buffer
        self.mic_waveform.pop(0)
        self.mic_waveform.append(amplitude)

        # Simulate assistant speaking (pulsing amplitude)
        # Use different frequency for variety
        assistant_wave = (math.sin(self._simulation_phase * 2) + 1) / 2
        self.assistant_amplitude = assistant_wave * 0.8  # Scale to 0-0.8

    def add_mic_sample(self, amplitude: float):
        """
        Add a microphone amplitude sample to the waveform.

        Args:
            amplitude: Audio amplitude (0.0 to 1.0)
        """
        self.mic_waveform.pop(0)
        self.mic_waveform.append(max(0.0, min(1.0, amplitude)))

    def set_assistant_amplitude(self, amplitude: float):
        """
        Set the assistant speaking amplitude.

        Args:
            amplitude: Audio amplitude (0.0 to 1.0)
        """
        self.assistant_amplitude = max(0.0, min(1.0, amplitude))

    def set_visualization_style(self, style: VisualizationStyle):
        """
        Change the visualization style.

        Args:
            style: New visualization style
        """
        self.visualization_style = style
        self.refresh()

    def _render_waveform(self, width: int) -> Text:
        """
        Render scrolling waveform using selected style.

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with waveform
        """
        if self.microphone_waveform_style == MicrophoneWaveformStyle.SCROLLING_FILL:
            return self._render_waveform_scrolling_fill(width)
        elif self.microphone_waveform_style == MicrophoneWaveformStyle.VERTICAL_BARS:
            return self._render_waveform_vertical_bars(width)
        elif self.microphone_waveform_style == MicrophoneWaveformStyle.WAVE_CHARACTERS:
            return self._render_waveform_wave_chars(width)
        elif self.microphone_waveform_style == MicrophoneWaveformStyle.LINE_WAVE:
            return self._render_waveform_line(width)
        elif self.microphone_waveform_style == MicrophoneWaveformStyle.DOTS:
            return self._render_waveform_dots(width)
        else:
            return self._render_waveform_scrolling_fill(width)

    def _render_waveform_scrolling_fill(self, width: int) -> Text:
        """
        Render scrolling timeline that fills when speaking.
        Creates a constantly scrolling line from right to left.
        When you speak, the line fills in (thick bars).
        When silent, the line stays thin.
        The filled bits scroll off the screen to the left.

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with scrolling fill effect
        """
        result = Text()

        # Use dynamic theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            shade_1 = theme["shade_1"]
            shade_2 = theme["shade_2"]
            shade_3 = theme["shade_3"]
            shade_4 = theme["shade_4"]
            shade_5 = theme["shade_5"]
        else:
            # Fallback to default grayscale
            shade_1 = "#252a33"
            shade_2 = "#363d47"
            shade_3 = "#4d5966"
            shade_4 = "#6b7a8a"
            shade_5 = "#8899aa"

        # Characters for different amplitude levels
        # Low amplitude = thin line, high amplitude = filled block
        fill_chars = [
            "─",  # 0.0-0.1: Silent (thin line)
            "▁",  # 0.1-0.2: Very quiet
            "▂",  # 0.2-0.3: Quiet
            "▃",  # 0.3-0.4: Low
            "▄",  # 0.4-0.5: Medium-low
            "▅",  # 0.5-0.6: Medium
            "▆",  # 0.6-0.7: Medium-high
            "▇",  # 0.7-0.8: Loud
            "█",  # 0.8-1.0: Very loud (filled)
        ]

        # Sample waveform data to fit width
        samples_per_char = len(self.mic_waveform) // width
        if samples_per_char == 0:
            samples_per_char = 1

        for i in range(min(width, len(self.mic_waveform))):
            # Get average amplitude for this position
            start_idx = i * samples_per_char
            end_idx = min(start_idx + samples_per_char, len(self.mic_waveform))

            if start_idx < len(self.mic_waveform):
                avg_amplitude = sum(self.mic_waveform[start_idx:end_idx]) / max(1, end_idx - start_idx)

                # Map amplitude to fill character
                char_idx = int(avg_amplitude * (len(fill_chars) - 1))
                char = fill_chars[char_idx]

                # Color based on amplitude - subtle shade variations
                if avg_amplitude > 0.7:
                    result.append(char, style=shade_5)  # shade-5 (lightest)
                elif avg_amplitude > 0.5:
                    result.append(char, style=shade_4)  # shade-4 (light)
                elif avg_amplitude > 0.3:
                    result.append(char, style=shade_3)  # shade-3 (medium)
                elif avg_amplitude > 0.1:
                    result.append(char, style=shade_2)  # shade-2 (dark)
                else:
                    result.append(char, style=shade_1)  # shade-1 (darkest)

        return result

    def _render_waveform_vertical_bars(self, width: int) -> Text:
        """
        Render scrolling waveform using vertical bar characters.
        This is the classic audio waveform visualization.

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with waveform
        """
        result = Text()

        # Vertical bar characters for different amplitudes (8 levels)
        bar_chars = [" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        # Sample waveform data to fit width
        samples_per_char = len(self.mic_waveform) // width
        if samples_per_char == 0:
            samples_per_char = 1

        for i in range(min(width, len(self.mic_waveform))):
            # Get average amplitude for this position
            start_idx = i * samples_per_char
            end_idx = min(start_idx + samples_per_char, len(self.mic_waveform))

            if start_idx < len(self.mic_waveform):
                avg_amplitude = sum(self.mic_waveform[start_idx:end_idx]) / max(1, end_idx - start_idx)

                # Map amplitude to bar character (0-8 range)
                char_idx = int(avg_amplitude * (len(bar_chars) - 1))
                char = bar_chars[char_idx]

                # Color based on amplitude - subtle shade variations
                if avg_amplitude > 0.7:
                    result.append(char, style="#8899aa")  # shade-5 (lightest)
                elif avg_amplitude > 0.4:
                    result.append(char, style="#6b7a8a")  # shade-4 (light)
                elif avg_amplitude > 0.1:
                    result.append(char, style="#4d5966")  # shade-3 (medium)
                else:
                    result.append(char, style="#363d47")  # shade-2 (dark)

        return result

    def _render_waveform_wave_chars(self, width: int) -> Text:
        """
        Render scrolling waveform using simple wave characters.
        Original implementation with ◡◠ characters.

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with waveform
        """
        result = Text()

        # Wave characters for different amplitudes
        wave_chars = [" ", "◡", "◠", "◡", "◠"]  # Low to high

        # Sample waveform data to fit width
        samples_per_char = len(self.mic_waveform) // width
        if samples_per_char == 0:
            samples_per_char = 1

        for i in range(min(width, len(self.mic_waveform))):
            # Get average amplitude for this position
            start_idx = i * samples_per_char
            end_idx = min(start_idx + samples_per_char, len(self.mic_waveform))

            if start_idx < len(self.mic_waveform):
                avg_amplitude = sum(self.mic_waveform[start_idx:end_idx]) / max(1, end_idx - start_idx)

                # Map amplitude to wave character
                char_idx = int(avg_amplitude * (len(wave_chars) - 1))
                char = wave_chars[char_idx]

                # Color based on amplitude - subtle shade variations
                if avg_amplitude > 0.7:
                    result.append(char, style="#8899aa")  # shade-5 (lightest)
                elif avg_amplitude > 0.4:
                    result.append(char, style="#6b7a8a")  # shade-4 (light)
                elif avg_amplitude > 0.1:
                    result.append(char, style="#4d5966")  # shade-3 (medium)
                else:
                    result.append(char, style="#363d47")  # shade-2 (dark)

        return result

    def _render_waveform_line(self, width: int) -> Text:
        """
        Render scrolling waveform as a continuous line.
        Uses box drawing characters for smooth line.

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with waveform
        """
        result = Text()

        # Box drawing characters for line segments
        line_chars = ["_", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "▔"]

        # Sample waveform data to fit width
        samples_per_char = len(self.mic_waveform) // width
        if samples_per_char == 0:
            samples_per_char = 1

        for i in range(min(width, len(self.mic_waveform))):
            # Get average amplitude for this position
            start_idx = i * samples_per_char
            end_idx = min(start_idx + samples_per_char, len(self.mic_waveform))

            if start_idx < len(self.mic_waveform):
                avg_amplitude = sum(self.mic_waveform[start_idx:end_idx]) / max(1, end_idx - start_idx)

                # Map amplitude to line height
                char_idx = int(avg_amplitude * (len(line_chars) - 1))
                char = line_chars[char_idx]

                # Color gradient based on amplitude - subtle shade variations
                if avg_amplitude > 0.7:
                    result.append(char, style="#8899aa")  # shade-5 (lightest)
                elif avg_amplitude > 0.5:
                    result.append(char, style="#6b7a8a")  # shade-4 (light)
                elif avg_amplitude > 0.3:
                    result.append(char, style="#4d5966")  # shade-3 (medium)
                elif avg_amplitude > 0.1:
                    result.append(char, style="#363d47")  # shade-2 (dark)
                else:
                    result.append(char, style="#252a33")  # shade-1 (darkest)

        return result

    def _render_waveform_dots(self, width: int) -> Text:
        """
        Render scrolling waveform using dots of varying sizes.
        Minimalist dot pattern visualization with grayscale intensity.
        Scrolls right (new data appears on left).

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with waveform
        """
        result = Text()

        # Use dynamic theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            shade_1 = theme["shade_1"]
            shade_2 = theme["shade_2"]
            shade_3 = theme["shade_3"]
            shade_4 = theme["shade_4"]
            shade_5 = theme["shade_5"]
        else:
            # Fallback to default grayscale
            shade_1 = "#252a33"
            shade_2 = "#363d47"
            shade_3 = "#4d5966"
            shade_4 = "#6b7a8a"
            shade_5 = "#8899aa"

        # Dot characters for different amplitudes
        dot_chars = [" ", "·", "•", "●", "⬤"]

        # Sample waveform data to fit width
        samples_per_char = len(self.mic_waveform) // width
        if samples_per_char == 0:
            samples_per_char = 1

        # For right-scrolling: start from END of buffer (newest) and work backwards
        buffer_len = len(self.mic_waveform)
        num_chars = min(width, buffer_len // samples_per_char)

        for i in range(num_chars):
            # Sample from end of buffer backwards (newest first)
            end_idx = buffer_len - (i * samples_per_char)
            start_idx = max(0, end_idx - samples_per_char)

            if start_idx < buffer_len and end_idx > 0:
                avg_amplitude = sum(self.mic_waveform[start_idx:end_idx]) / max(1, end_idx - start_idx)

                # Map amplitude to dot size
                char_idx = int(avg_amplitude * (len(dot_chars) - 1))
                char = dot_chars[char_idx]

                # Grayscale intensity based on amplitude - subtle shades
                if avg_amplitude > 0.8:
                    result.append(char, style=shade_5)  # shade-5 (lightest)
                elif avg_amplitude > 0.6:
                    result.append(char, style=shade_4)  # shade-4 (light)
                elif avg_amplitude > 0.4:
                    result.append(char, style=shade_3)  # shade-3 (medium)
                elif avg_amplitude > 0.2:
                    result.append(char, style=shade_2)  # shade-2 (dark)
                else:
                    result.append(char, style=shade_1)  # shade-1 (darkest)

        return result

    def _render_concentric_circles(self, width: int, height: int) -> List[str]:
        """Style 1: Concentric circles that expand based on amplitude."""
        lines = []
        center_x = width // 2
        center_y = height // 2

        # Density characters for circles
        chars = [" ", "░", "▒", "▓", "█"]

        for y in range(height):
            line = ""
            for x in range(width):
                # Calculate distance from center
                dx = x - center_x
                dy = (y - center_y) * 2  # Adjust for character aspect ratio
                distance = math.sqrt(dx * dx + dy * dy)

                # Map distance to amplitude rings (using smoothed amplitude)
                ring_size = 5 * self._smooth_assistant_amplitude
                ring_phase = (distance - self.animation_frame * 0.5) % (ring_size + 1)

                if ring_phase < ring_size:
                    intensity = 1.0 - (ring_phase / ring_size)
                    char_idx = int(intensity * (len(chars) - 1))
                    line += chars[char_idx]
                else:
                    line += " "

            lines.append(line)

        return lines

    def _render_ripple_waves(self, width: int, height: int) -> List[str]:
        """Style 2: Ripple effect with wave characters."""
        lines = []
        center_x = width // 2
        center_y = height // 2

        wave_chars = ["◠", "◡", "◝", "◞"]

        for y in range(height):
            line = ""
            for x in range(width):
                dx = x - center_x
                dy = (y - center_y) * 2
                distance = math.sqrt(dx * dx + dy * dy)

                # Create ripple effect (using smoothed amplitude)
                ripple = math.sin(distance * 0.5 - self.animation_frame * 0.3) * self._smooth_assistant_amplitude

                if ripple > 0.3:
                    char_idx = int((distance + self.animation_frame) % len(wave_chars))
                    line += wave_chars[char_idx]
                else:
                    line += " "

            lines.append(line)

        return lines

    def _render_circular_bars(self, width: int, height: int) -> List[str]:
        """Style 3: Vertical bars arranged in a circle."""
        lines = []
        center_x = width // 2
        center_y = height // 2

        bar_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        # Number of bars around circle
        num_bars = 12
        radius = min(width, height * 2) // 3

        for y in range(height):
            line = ""
            for x in range(width):
                dx = x - center_x
                dy = (y - center_y) * 2

                # Calculate angle and distance
                angle = math.atan2(dy, dx)
                distance = math.sqrt(dx * dx + dy * dy)

                # Check if we're near a bar position
                bar_idx = int((angle + math.pi) / (2 * math.pi) * num_bars)
                bar_angle = (bar_idx / num_bars) * 2 * math.pi - math.pi

                # Calculate amplitude for this bar (varies by bar and time, using smoothed amplitude)
                bar_amplitude = math.sin(self.animation_frame * 0.2 + bar_idx) * self._smooth_assistant_amplitude
                bar_height = radius * (0.5 + bar_amplitude)

                # Check if point is within this bar
                angle_diff = abs(angle - bar_angle)
                if angle_diff < 0.3 and distance < bar_height:
                    # Height of bar at this point
                    bar_intensity = 1.0 - (distance / bar_height)
                    char_idx = int(bar_intensity * (len(bar_chars) - 1))
                    line += bar_chars[char_idx]
                else:
                    line += " "

            lines.append(line)

        return lines

    def _render_pulsing_dots(self, width: int, height: int) -> List[str]:
        """Style 4: Pulsing dot pattern."""
        lines = []
        center_x = width // 2
        center_y = height // 2

        dot_chars = ["·", "•", "●", "⬤"]

        # Multiple rings of dots
        num_rings = 3
        dots_per_ring = [8, 12, 16]

        for y in range(height):
            line = ""
            for x in range(width):
                dx = x - center_x
                dy = (y - center_y) * 2
                distance = math.sqrt(dx * dx + dy * dy)

                found_dot = False

                # Check each ring
                for ring_idx in range(num_rings):
                    ring_radius = (ring_idx + 1) * 5 * self._smooth_assistant_amplitude

                    if abs(distance - ring_radius) < 1.5:
                        # Check if we're near a dot position
                        angle = math.atan2(dy, dx)
                        num_dots = dots_per_ring[ring_idx]
                        dot_idx = int((angle + math.pi) / (2 * math.pi) * num_dots)
                        dot_angle = (dot_idx / num_dots) * 2 * math.pi - math.pi

                        angle_diff = abs(angle - dot_angle)
                        if angle_diff < 0.3:
                            # Pulse effect
                            pulse = math.sin(self.animation_frame * 0.2 + ring_idx) * 0.5 + 0.5
                            char_idx = int(pulse * (len(dot_chars) - 1))
                            line += dot_chars[char_idx]
                            found_dot = True
                            break

                if not found_dot:
                    line += " "

            lines.append(line)

        return lines

    def _render_spinning_indicator(self, width: int, height: int) -> List[str]:
        """Style 5: Spinning/rotating indicator."""
        lines = []
        center_x = width // 2
        center_y = height // 2

        spinner_chars = ["◜", "◝", "◞", "◟"]

        # Spinning radius based on smoothed amplitude
        radius = 8 * self._smooth_assistant_amplitude

        for y in range(height):
            line = ""
            for x in range(width):
                dx = x - center_x
                dy = (y - center_y) * 2
                distance = math.sqrt(dx * dx + dy * dy)

                # Rotating effect
                angle = math.atan2(dy, dx)
                spin_angle = self.animation_frame * 0.3

                # Draw spiral
                target_distance = (angle + spin_angle) % (2 * math.pi) * radius / (2 * math.pi)

                if abs(distance - target_distance) < 2:
                    char_idx = int(self.animation_frame / 5) % len(spinner_chars)
                    line += spinner_chars[char_idx]
                else:
                    line += " "

            lines.append(line)

        return lines

    def _render_sound_wave_circle(self, width: int, height: int) -> List[str]:
        """Style 6: Sound wave pattern in circular arrangement."""
        lines = []
        center_x = width // 2
        center_y = height // 2

        wave_chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

        base_radius = min(width, height * 2) // 3

        for y in range(height):
            line = ""
            for x in range(width):
                dx = x - center_x
                dy = (y - center_y) * 2
                distance = math.sqrt(dx * dx + dy * dy)
                angle = math.atan2(dy, dx)

                # Create wave pattern around circle (using smoothed amplitude)
                wave_offset = math.sin(angle * 5 + self.animation_frame * 0.3) * self._smooth_assistant_amplitude * 5
                target_radius = base_radius + wave_offset

                if abs(distance - target_radius) < 2:
                    # Intensity based on wave
                    intensity = (math.sin(angle * 5 + self.animation_frame * 0.3) + 1) / 2
                    char_idx = int(intensity * (len(wave_chars) - 1))
                    line += wave_chars[char_idx]
                else:
                    line += " "

            lines.append(line)

        return lines

    def render(self) -> Text:
        """
        Render voice visualizer with current style.

        Returns:
            Rich Text with visualization
        """
        result = Text()

        # Calculate available space
        widget_width = max(self.size.width, 20)
        widget_height = max(self.size.height, 8)
        content_width = widget_width
        available_lines = widget_height

        # Reserve 2 lines for waveform section at bottom (mic label + waveform)
        waveform_lines = 2
        circular_viz_lines = available_lines - waveform_lines

        if circular_viz_lines < 4:
            # Too small, just show waveform
            result.append("▓▒░", style="bold cyan")
            result.append("\n")
            waveform = self._render_waveform(content_width)
            result.append(waveform)
            return result

        # Render circular visualization based on style
        if self.visualization_style == VisualizationStyle.CONCENTRIC_CIRCLES:
            viz_lines = self._render_concentric_circles(content_width, circular_viz_lines)
        elif self.visualization_style == VisualizationStyle.RIPPLE_WAVES:
            viz_lines = self._render_ripple_waves(content_width, circular_viz_lines)
        elif self.visualization_style == VisualizationStyle.CIRCULAR_BARS:
            viz_lines = self._render_circular_bars(content_width, circular_viz_lines)
        elif self.visualization_style == VisualizationStyle.PULSING_DOTS:
            viz_lines = self._render_pulsing_dots(content_width, circular_viz_lines)
        elif self.visualization_style == VisualizationStyle.SPINNING_INDICATOR:
            viz_lines = self._render_spinning_indicator(content_width, circular_viz_lines)
        elif self.visualization_style == VisualizationStyle.SOUND_WAVE_CIRCLE:
            viz_lines = self._render_sound_wave_circle(content_width, circular_viz_lines)
        else:
            viz_lines = [""] * circular_viz_lines

        # Use dynamic theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            shade_3 = theme["shade_3"]
            shade_4 = theme["shade_4"]
            shade_5 = theme["shade_5"]
        else:
            # Fallback to default grayscale
            shade_3 = "#4d5966"
            shade_4 = "#6b7a8a"
            shade_5 = "#8899aa"

        # Add circular visualization with gradient effect (subtle shades)
        for i, line in enumerate(viz_lines):
            # Create gradient from top (dim) to center (bright) to bottom (dim)
            center = len(viz_lines) / 2
            distance_from_center = abs(i - center) / center

            # Apply gradient based on distance from center - subtle shade variations
            if distance_from_center < 0.3:
                style = shade_5  # shade-5 (lightest) - Brightest in center
            elif distance_from_center < 0.6:
                style = shade_4  # shade-4 (light) - Medium
            else:
                style = shade_3  # shade-3 (medium) - Dimmer at edges

            result.append(line + "\n", style=style)

        # Separator with subtle shade
        result.append("─" * content_width + "\n", style=shade_3)  # shade-3

        # Microphone waveform at bottom with cyan tint
        waveform = self._render_waveform(content_width)
        result.append(waveform)

        return result

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to visualizer panel.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            True if command was handled
        """
        # Handle base commands
        if super().handle_voice_command(command, args):
            return True

        # Visualizer-specific commands
        if command == "change visualization style":
            style_name = args.get("style", "")
            try:
                style = VisualizationStyle[style_name.upper()]
                self.set_visualization_style(style)
                return True
            except KeyError:
                pass

        elif command == "start animation":
            self.start_animation()
            return True

        elif command == "stop animation":
            self.stop_animation()
            return True

        return False

    def get_panel_info(self) -> Dict[str, Any]:
        """
        Get panel information for debugging.

        Returns:
            Dict with panel state
        """
        info = super().get_panel_info()
        info.update({
            "visualization_style": self.visualization_style.value,
            "is_animating": self.is_animating,
            "animation_frame": self.animation_frame,
            "assistant_amplitude": self.assistant_amplitude,
            "simulation_mode": self.simulation_mode,
        })
        return info
