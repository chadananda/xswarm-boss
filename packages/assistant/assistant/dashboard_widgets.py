"""
Consolidated dashboard widgets for the Voice Assistant.
Includes:
- PanelBase
- VoiceVisualizerPanel
- ActivityFeed
- Footer
- Header
- ProjectDashboard
- WorkerDashboard
- ScheduleWidget
- StatusWidget
- AudioVisualizer
"""

import asyncio
import math
import random
import re
import time
from abc import abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from importlib.metadata import version
from typing import Any, Dict, List, Optional

from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

# Import from sibling package
from .hardware import GPUCapability, detect_gpu_capability


class PanelBase(Static):
    """
    Base class for all TUI panels (Chat, Documents, Todo, Projects, etc.).

    Features:
    - Common border and title styling
    - Focus state management
    - Minimize/maximize support
    - Notification badges
    - Voice command handling
    - Responsive sizing
    """

    # Reactive properties
    is_focused = reactive(False)
    is_minimized = reactive(False)
    notification_count = reactive(0)

    def __init__(
        self,
        panel_id: str,
        title: str,
        min_width: int = 30,
        min_height: int = 10,
        **kwargs
    ):
        """
        Initialize panel.

        Args:
            panel_id: Unique panel identifier
            title: Panel display title
            min_width: Minimum panel width
            min_height: Minimum panel height
        """
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.panel_title = title
        self.min_width = min_width
        self.min_height = min_height

    @abstractmethod
    def render_content(self) -> Text:
        """
        Render panel-specific content.

        Must be implemented by subclasses.

        Returns:
            Rich Text object with panel content
        """
        pass

    def render(self) -> Text:
        """
        Render complete panel with border, title, and content.

        Returns:
            Rich Text object with full panel rendering
        """
        result = Text()

        # Get dimensions
        widget_width = max(self.size.width, self.min_width)
        widget_height = max(self.size.height, self.min_height)

        # Border style based on focus state
        border_style = "bold cyan" if self.is_focused else "dim cyan"
        title_style = f"bold {'yellow' if self.is_focused else 'white'}"

        # Top border with title
        title_text = f" {self.panel_title} "

        # Add notification badge if present
        if self.notification_count > 0:
            title_text += f"({self.notification_count}) "

        title_len = len(title_text)
        remaining_width = widget_width - title_len - 2  # -2 for border chars

        result.append("╔", style=border_style)
        result.append(title_text, style=title_style)
        result.append("═" * max(0, remaining_width), style=border_style)
        result.append("╗\n", style=border_style)

        # Content (if not minimized)
        if not self.is_minimized:
            content = self.render_content()
            content_lines = content.split("\n") if content else []

            # Calculate available content height
            available_height = widget_height - 2  # -2 for borders

            # Render content lines
            for i, line in enumerate(content_lines):
                if i >= available_height:
                    break

                result.append("║ ", style=border_style)

                # Truncate line if too long
                line_str = str(line)
                max_line_width = widget_width - 4  # -4 for "║ " and " ║"
                if len(line_str) > max_line_width:
                    line_str = line_str[:max_line_width-3] + "..."

                result.append(line_str)

                # Pad to width
                padding = max(0, max_line_width - len(line_str))
                result.append(" " * padding)
                result.append(" ║\n", style=border_style)

            # Fill remaining vertical space
            remaining_lines = available_height - len(content_lines)
            for _ in range(max(0, remaining_lines)):
                result.append("║", style=border_style)
                result.append(" " * (widget_width - 2))
                result.append("║\n", style=border_style)

        # Bottom border
        result.append("╚" + "═" * (widget_width - 2) + "╝", style=border_style)

        return result

    # State management methods

    def focus_panel(self):
        """Focus this panel (highlight border)"""
        self.is_focused = True

    def blur_panel(self):
        """Unfocus this panel (dim border)"""
        self.is_focused = False

    def toggle_minimize(self):
        """Toggle panel minimized state"""
        self.is_minimized = not self.is_minimized

    def set_notification_count(self, count: int):
        """
        Set notification badge count.

        Args:
            count: Number of notifications (0 to hide badge)
        """
        self.notification_count = count

    def increment_notification(self):
        """Increment notification count"""
        self.notification_count += 1

    def clear_notifications(self):
        """Clear notification badge"""
        self.notification_count = 0

    # Voice command integration

    def handle_voice_command(self, command: str, args: Dict[str, Any]) -> bool:
        """
        Handle voice command directed to this panel.

        Args:
            command: Command name (e.g., "add task", "search files")
            args: Command arguments

        Returns:
            True if command was handled, False if not recognized
        """
        # Default implementation - subclasses override for specific commands
        if command == "focus":
            self.focus_panel()
            return True
        elif command == "minimize":
            self.toggle_minimize()
            return True
        elif command == "clear notifications":
            self.clear_notifications()
            return True

        return False

    # Reactive watchers

    def watch_is_focused(self, is_focused: bool):
        """React to focus state change"""
        self.refresh()

    def watch_is_minimized(self, is_minimized: bool):
        """React to minimize state change"""
        self.refresh()

    def watch_notification_count(self, count: int):
        """React to notification count change"""
        self.refresh()

    # Helper methods

    def get_panel_info(self) -> Dict[str, Any]:
        """
        Get panel information for debugging/logging.

        Returns:
            Dict with panel state
        """
        return {
            "panel_id": self.panel_id,
            "title": self.panel_title,
            "focused": self.is_focused,
            "minimized": self.is_minimized,
            "notifications": self.notification_count,
            "size": (self.size.width, self.size.height),
        }



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
    VERTICAL_BARS = "vertical_bars"  # Classic audio waveform  ▂▃▄▅▆▇█
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
        self.mic_waveform: List[tuple[str, str]] = []  # Scrolling waveform data (char, color)
        self.assistant_amplitude: float = 0.0  # Current assistant speaking amplitude

        # Reactive state property - single source of truth for animation
        # 0.0 = Not connected, 1.0 = Idle (breathing), 2.0-100.0 = Speaking (amplitude)
        self.connection_amplitude = reactive(0.0)

        # Smoothed amplitudes for stable animation
        self._smooth_assistant_amplitude: float = 0.0
        self.smoothing_factor: float = 0.3  # 0.0 = no smoothing, 1.0 = instant

        # Buffer sizes
        self.waveform_buffer_size = 100
        # Initialize with small dots (not spaces) so waveform is visible even when silent
        self.mic_waveform = [("·", "#363d47")] * self.waveform_buffer_size  # shade_2 tiny dots

        # Animation state
        self.is_animating = False
        self._animation_timer = None

        # Simulation mode (for testing without real audio)
        # Set to False to use real audio data from mic/Moshi
        self.simulation_mode = False
        self._simulation_phase = 0.0

        # Persona name (rendered above divider line)
        self.persona_name = "JARVIS"  # Default persona name

        # Data callback - app provides this to let widget pull real-time data
        self.data_callback: Optional[Callable[[], Any]] = None  # Set by app after initialization

    def start_animation(self):
        """Start the visualization animation at 20 FPS."""
        if not self.is_animating:
            self.is_animating = True
            # Widget self-animates based on connection_amplitude state
            if not self.simulation_mode:
                self._animation_timer = self.set_interval(1 / self.fps, self._update_animation)

    def stop_animation(self):
        """Stop the visualization animation."""
        if self.is_animating and self._animation_timer:
            self._animation_timer.stop()
            self.is_animating = False

    def _update_animation(self):
        """
        Animation update callback (20 FPS) - pulls data from app and renders.
        This is the ONLY timer - no dual-timer race condition.
        """
        self.animation_frame += 1

        # Pull real-time data from app (if callback is set)
        if self.data_callback and not self.simulation_mode:
            try:
                data = self.data_callback()
                # Update mic waveform
                mic_amp = data.get("mic_amplitude", 0.0)
                if mic_amp > 0.0:
                    self.add_mic_sample(mic_amp)
                # Process batch samples if available
                if "mic_samples" in data:
                    for sample in data["mic_samples"]:
                        self.add_mic_sample(sample)
                # Update connection amplitude
                conn_amp = data.get("connection_amplitude")
                if conn_amp is not None:
                    self.connection_amplitude = conn_amp
            except Exception:
                pass  # Callback failed, use existing data

        if self.connection_amplitude == 0:
            # Not connected - no animation
            self._smooth_assistant_amplitude = 0.0
        elif self.connection_amplitude == 1:
            # Connected but idle - gentle breathing effect
            breath = math.sin(self.animation_frame * 0.05) * 0.1 + 0.15  # 0.05-0.25
            self._smooth_assistant_amplitude = breath
        else:
            # Speaking - use actual amplitude (2-100 mapped to 0.0-1.0)
            target = (self.connection_amplitude - 2) / 98.0  # Map 2-100 → 0-1
            # Apply smoothing for stable animation
            self._smooth_assistant_amplitude = (
                self.smoothing_factor * target +
                (1 - self.smoothing_factor) * self._smooth_assistant_amplitude
            )

        self.refresh()

    def _update_simulated_audio(self):
        """Generate simulated audio data for testing."""
        # Simulate microphone input (scrolling waveform)
        # Use sine wave with some randomness
        self._simulation_phase += 0.1
        amplitude = (math.sin(self._simulation_phase) + 1) / 2  # 0.0 to 1.0
        amplitude += random.uniform(-0.1, 0.1)  # Add noise
        amplitude = max(0.0, amplitude)  # Allow > 1.0 for clipping simulation

        # Use add_mic_sample() which has the granular size+color logic
        self.add_mic_sample(amplitude)

        # Simulate assistant speaking (pulsing amplitude)
        # Use different frequency for variety
        assistant_wave = (math.sin(self._simulation_phase * 2) + 1) / 2
        self.assistant_amplitude = assistant_wave * 0.8  # Scale to 0-0.8

    def add_mic_sample(self, amplitude: float):
        """
        Add a microphone amplitude sample to the waveform.
        Calculates dot character and color ONCE and stores as frozen tuple.
        Uses combined size+color for granular amplitude representation.

        Args:
            amplitude: Audio amplitude (0.0 to 1.0+, can exceed 1.0 for clipping warning)
        """
        amplitude = max(0.0, amplitude)

        # Get theme colors
        theme = getattr(self, 'theme_colors', None)
        s1, s2, s3, s4, s5 = (
            (theme["shade_1"], theme["shade_2"], theme["shade_3"], theme["shade_4"], theme["shade_5"])
            if theme else
            ("#252a33", "#363d47", "#4d5966", "#6b7a8a", "#8899aa")
        )

        # Amplitude thresholds mapped to (char, color)
        # Checked in descending order - first match wins
        # Red dots removed per user request. Thresholds adjusted for 2x scaling factor.
        amplitude_map = [
            (0.70, "⬤", s5),  (0.60, "⬤", s4),  (0.50, "⬤", s3),  (0.40, "⬤", s2),  # Large (loud speech)
            (0.35, "●", s5),  (0.28, "●", s4),  (0.21, "●", s3),  (0.14, "●", s2),  # Medium (normal speech)
            (0.10, "•", s4),  (0.07, "•", s3),  (0.04, "•", s2),                     # Small (quiet speech)
            (0.02, "·", s3),  (0.01, "·", s2),                                       # Tiny (breathing/ambient)
            (0.0,  "·", s2),                                                         # Silence (use smallest dot, not empty)
        ]

        # Find first matching threshold
        char, color = next((c, col) for thresh, c, col in amplitude_map if amplitude >= thresh)

        # Scroll waveform buffer (store frozen dot+color tuple)
        self.mic_waveform.pop(0)
        self.mic_waveform.append((char, color))

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
            " ",  # 0.1-0.2: Very quiet
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
        bar_chars = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

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
        line_chars = ["_", " ", "▂", "▃", "▄", "▅", "▆", "▇", "▔"]

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
        Reads frozen (char, color) tuples from buffer - no recalculation.
        Scrolls right (new data appears on left).

        Args:
            width: Available width for waveform

        Returns:
            Rich Text with waveform
        """
        result = Text()

        # For right-scrolling: start from END of buffer (newest) and work backwards
        buffer_len = len(self.mic_waveform)
        num_chars = min(width, buffer_len)

        for i in range(num_chars):
            # Read from end of buffer backwards (newest on left)
            idx = buffer_len - 1 - i

            if 0 <= idx < buffer_len:
                # Just read the frozen (char, color) tuple - no recalculation!
                char, color = self.mic_waveform[idx]
                result.append(char, style=color)

        return result

    def _render_simple_circle(self, width: int, height: int) -> List[str]:
        """Simple, fast circle rendering without per-pixel calculation."""
        lines = []

        # Don't show anything if amplitude is exactly 0.0 (before voice init)
        if self._smooth_assistant_amplitude == 0.0:
            return [" " * width for _ in range(height)]

        center_y = height // 2
        center_x = width // 2

        # Simple amplitude indicator - just a pulsing circle character
        pulse_chars = ["·", "o", "O", "◯", "⬤"]
        char_idx = int(self._smooth_assistant_amplitude * (len(pulse_chars) - 1))
        char = pulse_chars[char_idx]

        for y in range(height):
            if y == center_y:
                # Center line with character
                padding = " " * (center_x - 1)
                line = padding + char * 3 + padding
            else:
                # Empty line
                line = " " * width
            lines.append(line)

        return lines


    def render(self) -> Text:
        """
        Render voice visualizer with current style.

        Returns:
            Rich Text with visualization
        """
        result = Text()

        # SAFETY: Prevent render if size is invalid (prevents freeze)
        if self.size.width < 5 or self.size.height < 5:
            return Text("Loading...", style="dim")

        # Calculate available space
        widget_width = max(self.size.width, 20)
        widget_height = max(self.size.height, 8)
        content_width = widget_width
        available_lines = widget_height

        # Reserve 4 lines for bottom section: persona name + divider + mic icon + waveform
        # Persona name: 1 line
        # Divider: 1 line
        # Mic waveform: 1 line
        bottom_section_lines = 3
        circular_viz_lines = available_lines - bottom_section_lines

        if circular_viz_lines < 4:
            # Too small, just show waveform
            result.append("▓▒░", style="bold cyan")
            result.append("\n")
            waveform = self._render_waveform(content_width)
            result.append(waveform)
            return result

        # Use SIMPLE circle rendering (no expensive math) - all styles use same fast implementation
        viz_lines = self._render_simple_circle(content_width, circular_viz_lines)

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

        # Render persona name above divider line (centered)
        persona_text = f"◈ {self.persona_name} ◈"
        persona_padding = (content_width - len(persona_text)) // 2
        persona_line = " " * persona_padding + persona_text
        result.append(persona_line + "\n", style=shade_5)

        # Separator with subtle shade
        result.append("─" * content_width + "\n", style=shade_3)  # shade-3

        # Microphone waveform at bottom with cyan tint
        # Add mic icon (🎤) on the left, then the waveform
        # Note: 🎤 emoji takes 2 terminal cells + 1 space = 3 total width
        mic_icon = "🎤 "
        mic_icon_width = 3  # Account for wide emoji character (2 cells) + space
        waveform_width = max(1, content_width - mic_icon_width)
        waveform = self._render_waveform(waveform_width)
        result.append(mic_icon, style=shade_5)  # Use lightest shade for icon
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



class ActivityFeed(Static):
    """
    Scrolling activity log - HACKER TERMINAL STYLE.

    Features:
    - Color-coded message types (info, success, warning, error, system)
    - Timestamp with milliseconds
    - Line numbers
    - Terminal prompt style
    - Message type indicators
    """

    def __init__(self, max_messages: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.messages = deque(maxlen=max_messages)
        self._message_counter = 0

    def add_message(self, message: str, msg_type: str = "info"):
        """
        Add a message to the activity feed.

        Args:
            message: The message text
            msg_type: Type of message (info, success, warning, error, system)

        Returns:
            int: The message ID (for tracking/updating later)
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        self._message_counter += 1

        # DEBUG: Log to file for diagnosis
        try:
            with open("activity.log", "a") as f:
                f.write(f"[{timestamp}] [{msg_type.upper()}] {message}\n")
        except Exception:
            pass

        self.messages.append({
            "id": self._message_counter,
            "timestamp": timestamp,
            "message": message,
            "type": msg_type
        })
        self.refresh()
        return self._message_counter

    def update_last_message(self, message: str, msg_type: str = None):
        """Update the last message instead of adding a new one (useful for progress updates)"""
        if not self.messages:
            # No messages yet, add one
            self.add_message(message, msg_type)
            return

        # Auto-detect type if not specified
        if msg_type is None:
            msg_type = self._detect_message_type(message)

        # Update last message in place
        self.messages[-1] = {
            "id": self.messages[-1]["id"],  # Keep same ID
            "timestamp": self.messages[-1]["timestamp"],  # Keep original timestamp
            "message": message,
            "type": msg_type
        }
        self.refresh()

    def update_message_by_id(self, message_id: int, message: str, msg_type: str = None):
        """Update a specific message by its ID (useful for tracking specific progress messages)"""
        # Find message with this ID
        for i, msg in enumerate(self.messages):
            if msg["id"] == message_id:
                # Auto-detect type if not specified
                if msg_type is None:
                    msg_type = self._detect_message_type(message)

                # Update message in place
                self.messages[i] = {
                    "id": msg["id"],  # Keep same ID
                    "timestamp": msg["timestamp"],  # Keep original timestamp
                    "message": message,
                    "type": msg_type
                }
                self.refresh()
                return True

        # Message ID not found - add as new message
        self.add_message(message, msg_type)
        return False

    def _detect_message_type(self, message: str) -> str:
        """Auto-detect message type from keywords"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["error", "failed", "fail", "critical"]):
            return "error"
        elif any(word in message_lower for word in ["warning", "warn", "caution"]):
            return "warning"
        elif any(word in message_lower for word in ["success", "complete", "loaded", "ready", "connected"]):
            return "success"
        elif any(word in message_lower for word in ["initializing", "loading", "starting", "booting"]):
            return "system"
        else:
            return "info"

    def _format_message(self, msg: dict) -> Text:
        """Format a single message with subtle grayscale shades"""
        result = Text()

        # Use dynamic theme colors if available, otherwise fallback to defaults
        theme = getattr(self, 'theme_colors', None)
        if theme:
            shade_2 = theme["shade_2"]
            shade_3 = theme["shade_3"]
            shade_4 = theme["shade_4"]
            shade_5 = theme["shade_5"]
        else:
            # Fallback to default grayscale
            shade_2 = "#363d47"
            shade_3 = "#4d5966"
            shade_4 = "#6b7a8a"
            shade_5 = "#8899aa"

        # Message type indicator - subtle shade variations
        type_indicators = {
            "info": ("▓", shade_4),           # shade-4 (light)
            "success": ("✓", shade_5),        # shade-5 (lightest)
            "warning": ("⚠", shade_4),        # shade-4 (light)
            "error": ("✖", "#800000"),        # dark red/maroon for errors
            "system": ("◉", shade_3)          # shade-3 (medium)
        }

        indicator, color = type_indicators.get(msg["type"], ("▓", shade_4))

        # Line number (4 digits, zero-padded)
        result.append(f"{msg['id']:04d} ", style=shade_2)  # shade-2 (dark)

        # Timestamp
        result.append(f"[{msg['timestamp']}] ", style=shade_3)  # shade-3 (medium)

        # Type indicator
        result.append(f"{indicator} ", style=color)

        # Message text - subtle shade variations with dark red/maroon for errors
        if msg["type"] == "error":
            text_style = "#800000"  # dark red/maroon for error messages
        elif msg["type"] == "success":
            text_style = shade_4  # shade-4 (light)
        elif msg["type"] == "system":
            text_style = shade_3  # shade-3 (medium)
        else:
            text_style = shade_4  # shade-4 (light)

        result.append(msg["message"], style=text_style)

        return result

    def render(self) -> Text:
        """Render activity feed - simple list without inner border"""
        result = Text()

        if not self.messages:
            # Use theme colors if available
            theme = getattr(self, 'theme_colors', None)
            if theme:
                shade_4 = theme["shade_4"]
                shade_2 = theme["shade_2"]
            else:
                shade_4 = "#6b7a8a"
                shade_2 = "#363d47"
            result.append("▓▒░ AWAITING SYSTEM EVENTS ░▒▓\n", style=f"bold {shade_4}")
            result.append("No activity logged...\n", style=shade_2)
        else:
            # Show messages that fit in available height
            visible_messages = list(self.messages)

            for msg in visible_messages:
                # Format message
                msg_text = self._format_message(msg)
                result.append(msg_text)
                result.append("\n")

        return result


class CyberpunkActivityFeed(Static):
    """
    MAXIMUM CYBERPUNK activity feed.
    No borders, matrix-style scrolling log.
    """

    def __init__(self, max_messages: int = 200, **kwargs):
        super().__init__(**kwargs)
        self.messages = deque(maxlen=max_messages)
        self._message_counter = 0

    def add_message(self, message: str, msg_type: str = None):
        """Add a message with auto-detected type if not specified"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._message_counter += 1

        # Auto-detect type if not specified
        if msg_type is None:
            msg_type = self._detect_message_type(message)

        self.messages.append({
            "id": self._message_counter,
            "timestamp": timestamp,
            "message": message,
            "type": msg_type
        })
        self.refresh()

    def update_last_message(self, message: str, msg_type: str = None):
        """Update the last message instead of adding a new one (useful for progress updates)"""
        if not self.messages:
            # No messages yet, add one
            self.add_message(message, msg_type)
            return

        # Auto-detect type if not specified
        if msg_type is None:
            msg_type = self._detect_message_type(message)

        # Update last message in place
        self.messages[-1] = {
            "id": self.messages[-1]["id"],  # Keep same ID
            "timestamp": self.messages[-1]["timestamp"],  # Keep original timestamp
            "message": message,
            "type": msg_type
        }
        self.refresh()

    def _detect_message_type(self, message: str) -> str:
        """Auto-detect message type from keywords"""
        message_lower = message.lower()

        if any(word in message_lower for word in ["error", "failed", "fail", "critical", "crash"]):
            return "error"
        elif any(word in message_lower for word in ["warning", "warn", "caution"]):
            return "warning"
        elif any(word in message_lower for word in ["success", "complete", "loaded", "ready", "connected", "online"]):
            return "success"
        elif any(word in message_lower for word in ["initializing", "loading", "starting", "booting", "processing"]):
            return "system"
        else:
            return "info"

    def render(self) -> Text:
        """Render as pure scrolling terminal output"""
        result = Text()

        if not self.messages:
            result.append("▓▒░ TERMINAL LOG INITIALIZED ░▒▓\n", style="bold cyan")
            result.append("Awaiting system events...\n", style="dim cyan")
        else:
            # Show all messages that fit
            for msg in list(self.messages):
                # Type colors
                type_colors = {
                    "info": "cyan",
                    "success": "green",
                    "warning": "yellow",
                    "error": "red",
                    "system": "magenta"
                }
                color = type_colors.get(msg["type"], "white")

                # Type prefix
                type_prefix = {
                    "info": "[INFO]",
                    "success": "[OK]  ",
                    "warning": "[WARN]",
                    "error": "[ERR] ",
                    "system": "[SYS] "
                }
                prefix = type_prefix.get(msg["type"], "[LOG]")

                # Format line
                result.append(f"{msg['timestamp']} ", style="dim white")
                result.append(f"{prefix} ", style=f"bold {color}")
                result.append(f"{msg['message']}\n", style=color)

        return result



class CyberpunkFooter(Static):
    """
    Cyberpunk-styled footer with project and system status.

    Features:
    - GPU status (sufficient/insufficient)
    - Number of projects
    - Project progress with color coding
    - Worker status
    - Subscription tier
    """

    # Mock data (will be replaced with real data later)
    gpu_sufficient = reactive(True)
    total_projects = reactive(3)
    projects_progress = reactive([
        ("Authentication", 78),
        ("Marketing", 45),
        ("Product", 12)
    ])
    workers_online = reactive(2)
    workers_total = reactive(3)
    subscription_plan = reactive("Pro")
    # System monitoring stats
    cpu_percent = reactive(67)
    ram_used = reactive(28)
    ram_total = reactive(64)
    gpu_percent = reactive(82)
    network_up = reactive(245)  # KB/s
    network_down = reactive(1200)  # KB/s
    system_load = reactive(2.4)

    # GPU capability (real hardware detection)
    gpu_capability: GPUCapability = None

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    def on_mount(self) -> None:
        """Initialize and start monitoring"""
        # Detect GPU on startup
        self.gpu_capability = detect_gpu_capability()
        self.set_interval(2.0, self.update_stats)  # Update every 2 seconds

    def update_stats(self) -> None:
        """Update status with real GPU data and mock data for other stats"""
        import random
        # Update GPU capability (real hardware detection)
        self.gpu_capability = detect_gpu_capability()

        # Simulate realistic system stat fluctuations for other metrics (mock)
        # CPU: varies between 45-85%
        self.cpu_percent = min(95, max(35, self.cpu_percent + random.randint(-8, 8)))
        # RAM: slowly increases/decreases
        self.ram_used = min(self.ram_total - 2, max(16, self.ram_used + random.uniform(-0.5, 0.5)))
        # Network: fluctuates significantly
        self.network_up = max(50, self.network_up + random.randint(-100, 150))
        self.network_down = max(100, self.network_down + random.randint(-300, 500))
        # System load: gradual changes
        self.system_load = max(0.5, min(6.0, self.system_load + random.uniform(-0.3, 0.3)))

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback
    # Get progress color based on percentage
    def _get_progress_color(self, percent: float) -> str:
        """Get color for project progress percentage"""
        if percent < 30:
            return "red"
        elif percent < 70:
            return "yellow"
        else:
            return "green"

    def render(self) -> Text:
        """Render footer with system stats, GPU, projects, workers, and subscription status"""
        result = Text()
        widget_width = self.size.width
        primary = self._get_theme_color("primary", "cyan")
        shade_3 = self._get_theme_color("shade_3", "#4d5966")
        shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
        # Start directly with content (no inner border/box)
        result.append("▓▒░ ", style=f"bold {primary}")

        # 1. AI Capability Score - FIRST ITEM (most important for AI workloads)
        if self.gpu_capability:
            gpu = self.gpu_capability
            result.append("🤖AI:", style=shade_4)

            # Determine grade color (maroon for grades below C - unlikely to run AI)
            grade_colors = {
                "A++": primary, "A+": primary, "A": primary, "A-": primary,
                "B++": "green", "B+": "green", "B": "green", "B-": "green",
                "C": "yellow",
                "C-": "#8B0000", "D": "#8B0000", "F": "#8B0000"  # Maroon for AI-insufficient
            }
            grade_color = grade_colors.get(gpu.grade, "dim")

            # Override with thermal warning if GPU is hot (only for grades C and above)
            if gpu.temp_c and gpu.grade not in ["C-", "D", "F"]:
                if gpu.temp_c > 85:
                    grade_color = "red"
                elif gpu.temp_c > 75:
                    grade_color = "orange"

            # Format: 🤖AI: C- (19/100) [13GB/24GB] 62% [Hybrid]
            result.append(f"{gpu.grade}", style=f"bold {grade_color}")
            # Show numeric score
            result.append(f" ({gpu.compute_score:.0f}/100)", style=shade_4)
            vram_display = f" [{gpu.vram_used_gb:.0f}GB/{gpu.vram_total_gb:.0f}GB]"
            result.append(vram_display, style=shade_4)
            result.append(f" {gpu.util_percent:.0f}%", style=f"{grade_color}")
            result.append(" │ ", style=shade_3)

        # 2. Version Number
        # 2. Version Number
        try:
            from . import __version__
            app_version = __version__
            result.append(f"v{app_version}", style=f"bold {primary}")
            result.append(" │ ", style=shade_3)
        except Exception:
            pass  # Skip if version not available

        # 3. System Monitoring Stats
        # CPU
        result.append("CPU:", style=shade_4)
        cpu_color = "red" if self.cpu_percent > 80 else "yellow" if self.cpu_percent > 60 else "green"
        result.append(f"{self.cpu_percent}%", style=f"bold {cpu_color}")
        result.append(" │ ", style=shade_3)
        # RAM
        result.append("RAM:", style=shade_4)
        ram_percent = (self.ram_used / self.ram_total) * 100
        ram_color = "red" if ram_percent > 80 else "yellow" if ram_percent > 60 else "green"
        result.append(f"{self.ram_used:.1f}/{self.ram_total}GB", style=f"bold {ram_color}")
        result.append(" │ ", style=shade_3)
        # Network
        result.append("NET:", style=shade_4)
        # Format network speeds
        up_str = f"{self.network_up}KB/s" if self.network_up < 1024 else f"{self.network_up/1024:.1f}MB/s"
        down_str = f"{self.network_down}KB/s" if self.network_down < 1024 else f"{self.network_down/1024:.1f}MB/s"
        result.append(f"↑{up_str} ↓{down_str}", style="bold cyan")
        result.append(" │ ", style=shade_3)
        # System Load
        result.append("Load:", style=shade_4)
        load_color = "red" if self.system_load > 4 else "yellow" if self.system_load > 2 else "green"
        result.append(f"{self.system_load:.1f}", style=f"bold {load_color}")
        result.append(" ░▒▓ ", style=f"bold {primary}")
        # 3. Projects: count [name:percent% name:percent%]
        result.append(f"Projects:{self.total_projects} ", style=shade_4)
        # Build project progress list with shortened names
        project_parts = []
        for name, progress in self.projects_progress:
            # Shorten project names (first word or abbreviation, max 8 chars)
            short_name = name.split()[0][:8]
            color = self._get_progress_color(progress)
            project_parts.append(f"[{color}]{short_name}:{progress}%[/{color}]")
        projects_str = " ".join(project_parts) if project_parts else "None"
        result.append("[", style=shade_4)
        result.append_text(Text.from_markup(projects_str))
        result.append("]", style=shade_4)
        result.append(" │ ", style=shade_3)
        # 4. Workers: online/total count
        result.append("Workers:", style=shade_4)
        worker_color = "green" if self.workers_online > 0 else "red"
        result.append(f"{self.workers_online}/{self.workers_total}", style=f"bold {worker_color}")
        result.append(" │ ", style=shade_3)
        # 5. Subscription Plan
        result.append("Plan:", style=shade_4)
        plan_color = "cyan" if self.subscription_plan == "Pro" else "dim"
        result.append(self.subscription_plan, style=f"bold {plan_color}")
        result.append(" ░▒▓", style=f"bold {primary}")
        return result


class CompactCyberpunkFooter(Static):
    """
    Ultra-compact footer for small terminals.
    Single line with essential info.
    """

    state = reactive("ready")

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback

    def render(self) -> Text:
        """Render minimal footer"""
        result = Text()

        shade_3 = self._get_theme_color("shade_3", "#4d5966")
        shade_4 = self._get_theme_color("shade_4", "#6b7a8a")
        shade_5 = self._get_theme_color("shade_5", "#8899aa")

        result.append("▓▒░ ", style=shade_4)
        result.append("XSWARM v2.0", style=shade_5)
        result.append(" ░▒▓ ", style=shade_4)

        # State indicator - use theme colors with subtle shade variations
        state_colors = {
            "ready": shade_4,
            "idle": shade_3,
            "listening": shade_5,
            "speaking": shade_5,
            "error": shade_5
        }
        color = state_colors.get(self.state, shade_4)
        result.append(f"[{self.state.upper()}]", style=color)

        result.append(" ░▒▓", style=shade_4)

        return result



class CyberpunkHeader(Static):
    """
    Cyberpunk-styled header with ASCII art logo and boot sequence.

    Features:
    - ASCII art XSWARM logo
    - Animated boot sequence on startup
    - System status bar
    - Neon cyan aesthetic
    """

    boot_complete = reactive(False)
    boot_stage = reactive(0)
    persona_name = reactive("JARVIS")
    system_status = reactive("INITIALIZING")

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    # ASCII art logo using box-drawing characters
    LOGO = """
╔═══════════════════════════════════════════════════════════════════════════╗
║  ██╗  ██╗███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗                  ║
║  ╚██╗██╔╝██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║                  ║
║   ╚███╔╝ ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║                  ║
║   ██╔██╗ ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║                  ║
║  ██╔╝ ██╗███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║                  ║
║  ╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝                  ║
║                                                                           ║
║              ▓▒░  VOICE ASSISTANT INTERFACE v2.0  ░▒▓                    ║
║                   >> OVERABUNDANT PERSONALITY <<                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

    BOOT_STAGES = [
        "INITIALIZING NEURAL NETWORK",
        "LOADING PERSONA MATRIX",
        "ESTABLISHING VOICE LINK",
        "CALIBRATING AUDIO SYSTEMS",
        "CONNECTING TO SERVER",
        "SYSTEM READY"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.boot_messages = []

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback

    def on_mount(self) -> None:
        """Start boot sequence animation when mounted"""
        if not self.boot_complete:
            self.run_boot_sequence()

    async def run_boot_sequence(self) -> None:
        """Animate boot sequence"""
        for i, stage in enumerate(self.BOOT_STAGES):
            self.boot_stage = i
            self.boot_messages.append(stage)
            self.refresh()
            await asyncio.sleep(0.3)  # Fast cyberpunk boot

        self.boot_complete = True
        self.system_status = "ONLINE"
        self.refresh()

    def render(self) -> Text:
        """Render header with responsive layout based on terminal size"""
        result = Text()

        # RESPONSIVE: Adapt to terminal size
        widget_width = self.size.width

        # Tiny (< 40 cols): Ultra-minimal 1-line header
        if widget_width < 40:
            return self._render_minimal()

        # Small (40-79 cols): Compact 2-3 line header
        elif widget_width < 80:
            return self._render_compact()

        # Large (80+ cols): Full experience with ASCII art
        else:
            return self._render_full()

    def _render_minimal(self) -> Text:
        """Minimal 1-line header for tiny terminals"""
        result = Text()
        # Use theme colors with fallbacks
        primary = self._get_theme_color("shade_3", "cyan")
        accent = self._get_theme_color("shade_4", "yellow")
        highlight = self._get_theme_color("shade_5", "green")

        result.append("▓▒░ ", style=f"bold {primary}")
        result.append("XSWARM", style=f"bold {accent}")
        result.append(" ░▒▓", style=f"bold {primary}")

        if not self.boot_complete:
            result.append(" ", style="")
            result.append(self.boot_messages[-1] if self.boot_messages else "BOOTING", style=f"dim {highlight}")
        else:
            result.append(" ", style="")
            result.append(f"[{self.persona_name}]", style=f"bold {accent}")
            result.append(" ", style="")
            result.append(self.system_status, style=f"bold {highlight}")

        return result

    def _render_compact(self) -> Text:
        """Compact 2-3 line header for small terminals"""
        result = Text()
        widget_width = self.size.width
        border_width = widget_width - 2

        # Use theme colors with fallbacks
        primary = self._get_theme_color("shade_3", "cyan")
        accent = self._get_theme_color("shade_4", "yellow")
        highlight = self._get_theme_color("shade_5", "green")

        result.append("╔" + "═" * border_width + "╗\n", style=f"bold {primary}")
        result.append("║", style=f"bold {primary}")
        result.append(" XSWARM VOICE ASSISTANT ".center(border_width), style=f"bold {accent}")
        result.append("║\n", style=f"bold {primary}")

        if not self.boot_complete:
            # Show last boot message
            result.append("║", style=f"bold {primary}")
            msg = self.boot_messages[-1] if self.boot_messages else "INITIALIZING"
            result.append((" ▓▒░ " + msg).center(border_width), style=f"dim {highlight}")
            result.append("║\n", style=f"bold {primary}")

        result.append("╚" + "═" * border_width + "╝", style=f"bold {primary}")

        return result

    def _render_full(self) -> Text:
        """Full header with ASCII art for large terminals"""
        result = Text()

        widget_width = self.size.width
        border_width = widget_width - 2  # Account for ╔ and ╗
        inner_width = border_width - 2  # Account for "║ " and " ║"

        # Use theme colors with fallbacks
        primary = self._get_theme_color("shade_3", "cyan")
        accent = self._get_theme_color("shade_4", "yellow")
        highlight = self._get_theme_color("shade_5", "green")

        if not self.boot_complete:
            # Boot sequence display
            result.append("╔" + "═" * border_width + "╗\n", style=f"bold {primary}")
            result.append("║", style=f"bold {primary}")
            result.append(" XSWARM VOICE ASSISTANT ".center(border_width), style=f"bold {accent}")
            result.append("║\n", style=f"bold {primary}")
            result.append("║", style=f"bold {primary}")
            result.append(" SYSTEM BOOT SEQUENCE ".center(border_width), style=f"bold {accent}")
            result.append("║\n", style=f"bold {primary}")
            result.append("╠" + "═" * border_width + "╣\n", style=f"bold {primary}")

            # Show boot messages
            for msg in self.boot_messages[-5:]:  # Last 5 messages
                result.append("║ ", style=f"bold {primary}")
                result.append("▓▒░ ", style=f"dim {primary}")
                result.append(msg, style=highlight)
                # Pad to inner_width
                msg_len = len(msg) + 4  # "▓▒░ " prefix
                padding = inner_width - msg_len
                result.append(" " * padding)
                result.append(" ║\n", style=f"bold {primary}")

            # Fill remaining lines
            shown = len(self.boot_messages[-5:])
            for _ in range(5 - shown):
                result.append("║" + " " * border_width + "║\n", style=f"bold {primary}")

            result.append("╚" + "═" * border_width + "╝", style=f"bold {primary}")

        else:
            # Main logo display - use theme color
            result.append(self.LOGO, style=f"bold {primary}")

            # Status bar - responsive
            result.append("\n")
            result.append("╔" + "═" * border_width + "╗\n", style=f"bold {primary}")
            result.append("║ ", style=f"bold {primary}")

            # Build status line
            status_line = f"◉ PERSONA: {self.persona_name}  ◉ STATUS: {self.system_status}  ◉ NEURAL LINK: ACTIVE"

            # Left side: Persona
            result.append("◉ PERSONA: ", style="dim white")
            result.append(self.persona_name, style=f"bold {accent}")

            # Center: Status
            result.append("  ◉ STATUS: ", style="dim white")
            result.append(self.system_status, style=f"bold {highlight}" if self.system_status == "ONLINE" else "dim white")

            # Right side: System indicator
            result.append("  ◉ NEURAL LINK: ", style="dim white")
            result.append("ACTIVE", style=f"bold {highlight}")

            # Padding to fit width
            padding = inner_width - len(status_line)
            result.append(" " * padding)

            result.append(" ║\n", style=f"bold {primary}")
            result.append("╚" + "═" * border_width + "╝", style=f"bold {primary}")

        return result

    def update_persona(self, persona: str) -> None:
        """Update current persona display"""
        self.persona_name = persona.upper()

    def update_status(self, status: str) -> None:
        """Update system status"""
        self.system_status = status.upper()

    def trigger_glitch_effect(self) -> None:
        """Trigger a visual glitch effect (for drama)"""
        # TODO: Implement glitch animation in Phase 7
        pass


class CompactCyberpunkHeader(Static):
    """
    Compact version of header for smaller terminals.
    One-line banner with essential info.
    """

    persona_name = reactive("JARVIS")
    system_status = reactive("ONLINE")

    # Theme colors dictionary (set dynamically by app)
    theme_colors = None

    def _get_theme_color(self, shade: str, fallback: str) -> str:
        """Get theme color from palette or fallback to default."""
        if self.theme_colors and shade in self.theme_colors:
            return self.theme_colors[shade]
        return fallback

    def render(self) -> Text:
        """Render compact header"""
        result = Text()

        # Use theme colors with fallbacks
        primary = self._get_theme_color("shade_3", "cyan")
        accent = self._get_theme_color("shade_4", "yellow")
        highlight = self._get_theme_color("shade_5", "green")

        result.append("▓▒░ ", style=f"bold {primary}")
        result.append("XSWARM", style=f"bold {accent}")
        result.append(" ░▒▓ ", style=f"bold {primary}")
        result.append(f"[{self.persona_name}]", style=f"bold {accent}")
        result.append(" ◉ ", style="dim white")
        result.append(self.system_status, style=f"bold {highlight}")

        return result

    def update_persona(self, persona: str) -> None:
        """Update current persona display"""
        self.persona_name = persona.upper()

    def update_status(self, status: str) -> None:
        """Update system status"""
        self.system_status = status.upper()



class ProjectDashboard(Static):
    """
    Project status dashboard showing active projects and progress.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mock data
        self.projects = [
            {"name": "Authentication", "status": "In Progress", "progress": 78, "priority": "High"},
            {"name": "Marketing Site", "status": "Review", "progress": 92, "priority": "Medium"},
            {"name": "Mobile App", "status": "Planning", "progress": 15, "priority": "High"},
            {"name": "API Integration", "status": "Blocked", "progress": 45, "priority": "Critical"},
        ]

    def render(self) -> Text:
        """Render project list with progress bars"""
        result = Text()

        # Use theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            primary = theme["primary"]
            shade_2 = theme["shade_2"]
            shade_3 = theme["shade_3"]
            shade_4 = theme["shade_4"]
        else:
            primary = "cyan"
            shade_2 = "#363d47"
            shade_3 = "#4d5966"
            shade_4 = "#6b7a8a"

        result.append("ACTIVE PROJECTS\n", style=f"bold {primary}")
        result.append("─" * 30 + "\n", style=shade_3)

        for proj in self.projects:
            # Project Name and Status
            result.append(f" {proj['name']:<20}", style="bold white")
            
            status_colors = {
                "In Progress": "blue",
                "Review": "yellow",
                "Planning": "dim white",
                "Blocked": "red",
                "Done": "green"
            }
            color = status_colors.get(proj['status'], "white")
            result.append(f" {proj['status']:<12}", style=color)
            result.append("\n")

            # Progress Bar
            bar_width = 30
            filled = int(proj['progress'] / 100 * bar_width)
            
            # Progress color based on percentage
            if proj['progress'] < 30:
                prog_color = "red"
            elif proj['progress'] < 70:
                prog_color = "yellow"
            else:
                prog_color = "green"
                
            result.append(" [", style=shade_3)
            result.append("█" * filled, style=prog_color)
            result.append("░" * (bar_width - filled), style=shade_2)
            result.append(f"] {proj['progress']}%\n", style=shade_3)
            result.append("\n")

        return result


class WorkerDashboard(Static):
    """
    Worker status dashboard showing AI agents/workers.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mock data
        self.agent_workers = [
            {"name": "Coder-Alpha", "status": "Coding", "task": "Refactoring auth module", "uptime": "4h 12m"},
            {"name": "Reviewer-Beta", "status": "Idle", "task": "Waiting for PR", "uptime": "2h 05m"},
            {"name": "Tester-Gamma", "status": "Running", "task": "Running integration tests", "uptime": "6h 30m"},
        ]

    def render(self) -> Text:
        """Render worker list"""
        result = Text()

        # Use theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            primary = theme["primary"]
            shade_3 = theme["shade_3"]
        else:
            primary = "cyan"
            shade_3 = "#4d5966"

        result.append("AI WORKERS ONLINE\n", style=f"bold {primary}")
        result.append("─" * 40 + "\n", style=shade_3)

        for worker in self.agent_workers:
            # Name
            result.append(f" 🤖 {worker['name']}", style="bold white")
            
            # Status badge
            status_colors = {
                "Coding": "blue",
                "Idle": "dim white",
                "Running": "green",
                "Error": "red"
            }
            color = status_colors.get(worker['status'], "white")
            result.append(f" [{worker['status']}]", style=f"bold {color}")
            result.append("\n")
            
            # Current Task
            result.append(f"    └─ {worker['task']}", style="dim white")
            result.append(f" ({worker['uptime']})\n", style=shade_3)
            result.append("\n")

        return result


class ScheduleWidget(Static):
    """
    Schedule/Calendar widget showing upcoming events.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mock data
        self.events = [
            {"time": "10:00", "title": "Daily Standup", "type": "meeting"},
            {"time": "11:30", "title": "Code Review: Auth", "type": "work"},
            {"time": "14:00", "title": "Client Demo", "type": "meeting"},
            {"time": "16:00", "title": "Deep Work Block", "type": "focus"},
        ]

    def render(self) -> Text:
        """Render schedule"""
        result = Text()

        # Use theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            primary = theme["primary"]
            shade_3 = theme["shade_3"]
        else:
            primary = "cyan"
            shade_3 = "#4d5966"

        result.append("TODAY'S SCHEDULE\n", style=f"bold {primary}")
        result.append("─" * 30 + "\n", style=shade_3)

        current_hour = datetime.now().hour

        for event in self.events:
            # Parse hour for simple highlighting
            event_hour = int(event['time'].split(':')[0])
            is_past = event_hour < current_hour
            is_next = event_hour >= current_hour and event_hour < current_hour + 2

            time_style = "dim white" if is_past else "bold yellow" if is_next else "white"
            title_style = "dim white" if is_past else "bold white" if is_next else "white"
            
            # Icon based on type
            icons = {"meeting": "👥", "work": "💻", "focus": "🧠", "break": "☕"}
            icon = icons.get(event['type'], "📅")

            result.append(f" {event['time']} ", style=time_style)
            result.append(f"{icon} ", style="white")
            result.append(f"{event['title']}\n", style=title_style)
            
            if is_next:
                result.append(" " * 30 + "\n", style=shade_3) # Spacer

        return result



class StatusWidget(Static):
    """
    Status widget showing current system state.
    """

    state = reactive("ready")
    
    def render(self) -> Text:
        """Render status"""
        result = Text()

        # Use theme colors if available
        theme = getattr(self, 'theme_colors', None)
        if theme:
            primary = theme["primary"]
            shade_3 = theme["shade_3"]
        else:
            primary = "cyan"
            shade_3 = "#4d5966"

        # Status indicator
        status_colors = {
            "ready": "green",
            "idle": "dim white",
            "listening": "cyan",
            "thinking": "yellow",
            "speaking": "magenta",
            "error": "red"
        }
        color = status_colors.get(self.state, "white")
        
        result.append("SYSTEM STATUS\n", style=f"bold {primary}")
        result.append("─" * 20 + "\n", style=shade_3)
        
        result.append("Current State: ", style="white")
        result.append(f"{self.state.upper()}\n", style=f"bold {color}")
        
        return result


class CompactStatusWidget(Static):
    """
    Compact status widget for small screens.
    """

    state = reactive("ready")
    
    def render(self) -> Text:
        """Render compact status"""
        result = Text()

        # Status indicator
        status_colors = {
            "ready": "green",
            "idle": "dim white",
            "listening": "cyan",
            "thinking": "yellow",
            "speaking": "magenta",
            "error": "red"
        }
        color = status_colors.get(self.state, "white")
        
        result.append(f"[{self.state.upper()}]", style=f"bold {color}")
        
        return result




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


class CyberpunkVisualizer(Static):
    """
    CYBERPUNK EDITION: Dramatic audio visualizer with overabundant personality.

    Features:
    - Matrix-style digital rain background
    - Waveform display based on amplitude history
    - Scanline effects
    - Dramatic state indicators
    - Audio level meters
    - Frequency spectrum bars
    """

    amplitude = reactive(0.0)
    state = reactive("idle")
    _frame = reactive(0)
    _amplitude_history = []  # Last 60 frames of amplitude
    _matrix_cols = []  # Matrix rain columns

    # Cyberpunk ASCII characters
    MATRIX_CHARS = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ01"
    WAVEFORM_CHARS = "  ▂▃▄▅▆▇█"
    LEVEL_CHARS = "░▒▓█"

    def on_mount(self) -> None:
        """Initialize dramatic cyberpunk effects"""
        self.set_interval(1/30, self.tick)
        self._amplitude_history = [0.0] * 60  # 2 seconds at 30fps
        self._matrix_cols = []

    def tick(self) -> None:
        """Update animation frame"""
        self._frame = (self._frame + 1) % 3600  # 120 seconds at 30fps

        # Update amplitude history
        self._amplitude_history.append(self.amplitude)
        if len(self._amplitude_history) > 60:
            self._amplitude_history.pop(0)

        self.refresh()

    def _initialize_matrix(self, width: int, height: int):
        """Initialize matrix rain columns"""
        if not self._matrix_cols or len(self._matrix_cols) != width:
            self._matrix_cols = []
            for x in range(width):
                self._matrix_cols.append({
                    'pos': random.randint(0, height),
                    'speed': random.choice([1, 2, 3]),
                    'length': random.randint(3, 8)
                })

    def _update_matrix(self, height: int):
        """Update matrix rain positions"""
        for col in self._matrix_cols:
            col['pos'] += col['speed']
            if col['pos'] > height + col['length']:
                col['pos'] = -col['length']
                col['speed'] = random.choice([1, 2, 3])

    def render(self) -> Text:
        """Render DRAMATIC cyberpunk visualizer with responsive degradation"""
        width = self.size.width
        height = self.size.height

        # RESPONSIVE: Work at ANY size with progressive degradation
        # Tiny (< 20 cols): Just show state text
        if width < 20 or height < 5:
            return self._render_minimal(width, height)

        # Small (20-39 cols): Simple pulse circle only
        elif width < 40 or height < 15:
            return self._render_compact(width, height)

        # Medium (40-59 cols): Pulse + waveform, no side meters or matrix rain
        elif width < 60:
            return self._render_medium(width, height)

        # Large (60+ cols): Full cyberpunk experience
        else:
            return self._render_full(width, height)

    def _render_minimal(self, width: int, height: int) -> Text:
        """Minimal render for tiny terminals (< 20 cols)"""
        result = Text()

        # Just show state as simple text
        state_chars = {
            "idle": "●",
            "listening": "◉",
            "speaking": "◉",
            "thinking": "◐",
            "error": "✖",
            "ready": "●"
        }

        state_colors = {
            "idle": "cyan",
            "listening": "green",
            "speaking": "yellow",
            "thinking": "magenta",
            "error": "red",
            "ready": "blue"
        }

        char = state_chars.get(self.state, "●")
        color = state_colors.get(self.state, "cyan")

        # Center the state indicator
        line = char + " " + self.state.upper()
        padding = (width - len(line)) // 2
        result.append(" " * padding + line, style=f"bold {color}")

        return result

    def _render_compact(self, width: int, height: int) -> Text:
        """Compact render for small terminals (20-39 cols): Simple pulse only"""
        cx = width // 2
        cy = height // 2
        base_radius = min(width // 4, height // 3)

        # Get state-specific pulse and color
        color, radius, state_msg = self._get_state_params(base_radius)

        # Create canvas
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        styles = [['' for _ in range(width)] for _ in range(height)]

        # Draw simple pulse circle
        for y in range(max(0, cy - radius - 1), min(height, cy + radius + 1)):
            for x in range(max(0, cx - radius - 1), min(width, cx + radius + 1)):
                dx = x - cx
                dy = (y - cy) * 2
                dist = math.sqrt(dx*dx + dy*dy)

                if abs(dist - radius) < 1.5:
                    canvas[y][x] = "●"
                    styles[y][x] = f"bold {color}"

        # Render to Text
        result = Text()
        for y in range(height):
            for x in range(width):
                char = canvas[y][x]
                style = styles[y][x] or ""
                result.append(char, style=style)
            result.append("\n")

        return result

    def _render_medium(self, width: int, height: int) -> Text:
        """Medium render (40-59 cols): Pulse + waveform, no side meters"""
        cx = width // 2
        cy = height // 2
        base_radius = min(width // 6, height // 3)

        color, radius, state_msg = self._get_state_params(base_radius)

        # Create canvas
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        styles = [['' for _ in range(width)] for _ in range(height)]

        # LAYER 1: WAVEFORM (if listening/speaking)
        if self.state in ["listening", "speaking"]:
            waveform_y = height // 3
            history_step = max(1, len(self._amplitude_history) // (width - 4))
            for x in range(2, min(width - 2, len(self._amplitude_history) // history_step + 2)):
                idx = (x - 2) * history_step
                if idx < len(self._amplitude_history):
                    amp = self._amplitude_history[idx]
                    char_idx = min(len(self.WAVEFORM_CHARS) - 1, int(amp * (len(self.WAVEFORM_CHARS) - 1)))
                    char = self.WAVEFORM_CHARS[char_idx]
                    wave_y = waveform_y
                    if 0 <= wave_y < height:
                        canvas[wave_y][x] = char
                        styles[wave_y][x] = "bold yellow" if self.state == "speaking" else "bold green"

        # LAYER 2: PULSE CIRCLE
        for y in range(max(0, cy - radius - 2), min(height, cy + radius + 2)):
            for x in range(max(0, cx - radius - 2), min(width, cx + radius + 2)):
                dx = x - cx
                dy = (y - cy) * 2
                dist = math.sqrt(dx*dx + dy*dy)

                if abs(dist - radius) < 1.5:
                    canvas[y][x] = "●"
                    styles[y][x] = f"bold {color}"
                elif abs(dist - radius) < 3:
                    canvas[y][x] = "○"
                    styles[y][x] = color

        # LAYER 3: STATE MESSAGE
        msg_y = min(height - 1, cy + (radius // 2) + 2)
        if 0 <= msg_y < height and len(state_msg) <= width:
            msg_x = max(0, cx - len(state_msg) // 2)
            for i, char in enumerate(state_msg):
                if 0 <= msg_x + i < width:
                    canvas[msg_y][msg_x + i] = char
                    styles[msg_y][msg_x + i] = f"bold {color}"

        # Render
        result = Text()
        for y in range(height):
            for x in range(width):
                char = canvas[y][x]
                style = styles[y][x] or ""
                result.append(char, style=style)
            result.append("\n")

        return result

    def _render_full(self, width: int, height: int) -> Text:
        """Full cyberpunk render (60+ cols): All effects"""
        # Initialize/update matrix rain
        self._initialize_matrix(width, height)
        if self._frame % 2 == 0:
            self._update_matrix(height)

        # Create canvas
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        styles = [['' for _ in range(width)] for _ in range(height)]

        # === LAYER 1: MATRIX RAIN BACKGROUND ===
        if self.state in ["idle", "ready"]:
            for x, col in enumerate(self._matrix_cols[:width]):
                for i in range(col['length']):
                    y = col['pos'] - i
                    if 0 <= y < height:
                        char = random.choice(self.MATRIX_CHARS)
                        canvas[y][x] = char
                        if i == 0:
                            styles[y][x] = "bold green"
                        elif i < 3:
                            styles[y][x] = "green"
                        else:
                            styles[y][x] = "dim green"

        # === LAYER 2: WAVEFORM DISPLAY ===
        if self.state in ["listening", "speaking"]:
            waveform_y = height // 3
            history_step = max(1, len(self._amplitude_history) // (width - 4))
            for x in range(2, min(width - 2, len(self._amplitude_history) // history_step + 2)):
                idx = (x - 2) * history_step
                if idx < len(self._amplitude_history):
                    amp = self._amplitude_history[idx]
                    char_idx = min(len(self.WAVEFORM_CHARS) - 1, int(amp * (len(self.WAVEFORM_CHARS) - 1)))
                    char = self.WAVEFORM_CHARS[char_idx]
                    wave_offset = int((amp - 0.5) * 4)
                    wave_y = waveform_y + wave_offset
                    if 0 <= wave_y < height:
                        canvas[wave_y][x] = char
                        styles[wave_y][x] = "bold yellow" if self.state == "speaking" else "bold green"

        # === LAYER 3: CENTRAL PULSE CIRCLE ===
        cx = width // 2
        cy = height // 2
        base_radius = min(width // 6, height // 3)
        color, radius, state_msg = self._get_state_params(base_radius)

        # Draw pulse circle
        for y in range(max(0, cy - radius - 2), min(height, cy + radius + 2)):
            for x in range(max(0, cx - radius - 2), min(width, cx + radius + 2)):
                dx = x - cx
                dy = (y - cy) * 2
                dist = math.sqrt(dx*dx + dy*dy)

                if abs(dist - radius) < 1.5:
                    canvas[y][x] = "●"
                    styles[y][x] = f"bold {color}"
                elif abs(dist - radius) < 3:
                    canvas[y][x] = "○"
                    styles[y][x] = color

        # Draw state message
        msg_y = cy + (radius // 2) + 3
        if 0 <= msg_y < height:
            msg_x = cx - len(state_msg) // 2
            for i, char in enumerate(state_msg):
                if 0 <= msg_x + i < width:
                    canvas[msg_y][msg_x + i] = char
                    styles[msg_y][msg_x + i] = f"bold {color}"

        # === LAYER 4: AUDIO LEVEL METERS ===
        if self.state in ["listening", "speaking"]:
            meter_height = height - 4
            meter_level = int(self.amplitude * meter_height)

            # Left meter
            for y in range(2, height - 2):
                level_y = height - 2 - y
                if level_y < meter_level:
                    char = self.LEVEL_CHARS[3]
                    style = "bold green" if level_y < meter_height * 0.7 else "bold yellow"
                else:
                    char = self.LEVEL_CHARS[0]
                    style = "dim cyan"
                canvas[y][1] = char
                styles[y][1] = style

            # Right meter
            for y in range(2, height - 2):
                level_y = height - 2 - y
                if level_y < meter_level:
                    char = self.LEVEL_CHARS[3]
                    style = "bold green" if level_y < meter_height * 0.7 else "bold yellow"
                else:
                    char = self.LEVEL_CHARS[0]
                    style = "dim cyan"
                canvas[y][width - 2] = char
                styles[y][width - 2] = style

        # === LAYER 5: SCANLINES ===
        if self._frame % 3 == 0:
            scanline_y = (self._frame // 3) % height
            for x in range(width):
                if canvas[scanline_y][x] == ' ':
                    canvas[scanline_y][x] = '─'
                    styles[scanline_y][x] = "dim cyan"

        # === RENDER FINAL OUTPUT ===
        result = Text()
        for y in range(height):
            for x in range(width):
                char = canvas[y][x]
                style = styles[y][x] or "dim white"
                result.append(char, style=style)
            result.append("\n")

        return result

    def _get_state_params(self, base_radius: int):
        """Get color, radius, and message for current state"""
        if self.state == "idle":
            pulse = math.sin(self._frame * 0.02) * 0.3 + 1.0
            radius = int(base_radius * 0.4 * pulse)
            color = "cyan"
            state_msg = "◉ IDLE ◉"
        elif self.state == "listening":
            pulse = math.sin(self._frame * 0.15) * 0.4 + 1.0
            radius = int(base_radius * 0.6 * pulse)
            color = "green"
            state_msg = "◉ LISTENING ◉"
        elif self.state == "speaking":
            smooth_amp = sum(self._amplitude_history[-10:]) / 10 if len(self._amplitude_history) >= 10 else 0.5
            radius = int(base_radius * (0.5 + smooth_amp * 1.0))
            color = "yellow"
            state_msg = "◉ SPEAKING ◉"
        elif self.state == "thinking":
            pulse = math.sin(self._frame * 0.1) * 0.3 + 1.0
            radius = int(base_radius * 0.7 * pulse)
            color = "magenta"
            state_msg = "◉ THINKING ◉"
        elif self.state == "error":
            radius = int(base_radius * 0.3)
            color = "red"
            state_msg = "✖ ERROR ✖"
        else:
            radius = int(base_radius * 0.5)
            color = "blue"
            state_msg = "◉ READY ◉"

        return color, radius, state_msg


# END OF FILE








