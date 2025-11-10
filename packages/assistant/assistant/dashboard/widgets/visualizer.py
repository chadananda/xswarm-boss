"""
Pulsing circle audio visualizer.
CRITICAL USER REQUIREMENT: Pulses based on MOSHI amplitude changes.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
import math
import random


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
    WAVEFORM_CHARS = " ▁▂▃▄▅▆▇█"
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
