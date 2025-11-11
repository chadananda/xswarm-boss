"""
Main Textual TUI application.
Replaces Rust Ratatui dashboard.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from textual import events
from rich.text import Text
import asyncio
from typing import Optional
from pathlib import Path
import pyperclip

from .widgets.visualizer import AudioVisualizer, CyberpunkVisualizer
from .widgets.panels import VoiceVisualizerPanel, VisualizationStyle
from .widgets.status import StatusWidget
from .widgets.activity_feed import ActivityFeed
from .widgets.header import CyberpunkHeader
from .widgets.footer import CyberpunkFooter
from .screens import SettingsScreen, WizardScreen, VoiceVizDemoScreen
from ..config import Config
from .theme import generate_palette, get_theme_preset, THEME_PRESETS
import re


class VoiceAssistantApp(App):
    """Voice Assistant TUI Application"""

    CSS_PATH = "styles.tcss"
    TITLE = "Voice Assistant"

    # Reactive state
    state = reactive("idle")  # idle, listening, speaking, thinking
    amplitude = reactive(0.0)

    def __init__(self, config: Config, personas_dir: Path):
        super().__init__()
        self.config = config
        self.personas_dir = personas_dir
        self.moshi_bridge: Optional[object] = None
        self.audio_io: Optional[object] = None

        # Generate dynamic theme colors
        self._theme_palette = self._load_theme(config.theme_base_color)

    def _load_theme(self, theme_input: str):
        """
        Load theme palette from config.

        Args:
            theme_input: Either a hex color ("#8899aa") or preset name ("blue-gray")

        Returns:
            ColorPalette instance
        """
        # Check if it's a preset name
        if theme_input in THEME_PRESETS:
            return get_theme_preset(theme_input)

        # Otherwise treat as hex color
        return generate_palette(theme_input)

    @property
    def CSS(self) -> str:
        """
        Generate CSS with dynamic theme colors.

        Reads the base styles.tcss and replaces shade variables with theme colors.
        """
        # Read base CSS file
        css_path = Path(__file__).parent / "styles.tcss"
        base_css = css_path.read_text()

        # Replace shade variable definitions with theme colors
        # Match the entire palette block and replace it
        palette_pattern = r'/\* ▓▒░ SUBTLE GRAYSCALE PALETTE ░▒▓ \*/.*?\$shade-1: #[0-9a-fA-F]{6};'

        replacement = f"""/* ▓▒░ DYNAMIC THEME PALETTE ░▒▓ */
$shade-5: {self._theme_palette.shade_5};  /* Lightest */
$shade-4: {self._theme_palette.shade_4};  /* Light */
$shade-3: {self._theme_palette.shade_3};  /* Medium */
$shade-2: {self._theme_palette.shade_2};  /* Dark */
$shade-1: {self._theme_palette.shade_1};  /* Darkest */"""

        themed_css = re.sub(palette_pattern, replacement, base_css, flags=re.DOTALL)

        return themed_css

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout - activity is main focus"""
        with Container(id="main-container"):
            # Top row: Voice visualizer (left corner) + Activity (main)
            with Horizontal(id="top-row"):
                # Voice visualizer - small square in LEFT corner
                viz_panel = VoiceVisualizerPanel(
                    visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE
                )
                viz_panel.id = "visualizer"
                viz_panel.simulation_mode = True
                yield viz_panel

                # Main activity feed / chat - takes most space
                yield ActivityFeed(id="activity")

            # Bottom row: Status (compact)
            yield StatusWidget(id="status")

        yield CyberpunkFooter(id="footer")

    def on_mount(self) -> None:
        """Initialize on mount"""
        self.set_interval(1/30, self.update_visualizer)  # 30 FPS

        # Start visualizer animation
        try:
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.start_animation()
        except Exception:
            pass

        # Load MOSHI in background
        asyncio.create_task(self.initialize_moshi())

    async def initialize_moshi(self):
        """Load voice models"""
        try:
            self.update_activity("Initializing voice models...")
            device = self.config.detect_device()

            # Note: MoshiBridge and AudioIO will be implemented in Phase 2
            # For now, we'll simulate the initialization
            self.update_activity(f"Voice models loaded on {device}")
            self.state = "ready"

            # Update status widget
            status = self.query_one("#status", StatusWidget)
            status.device_name = str(device)
            status.state = "ready"

            # Update visualizer with persona name
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            persona_name = self.config.default_persona or "JARVIS"
            visualizer.border_title = f"xSwarm - {persona_name}"

        except Exception as e:
            self.update_activity(f"Error loading voice models: {e}")
            self.state = "error"

            # Update status widget
            status = self.query_one("#status", StatusWidget)
            status.state = "error"

            # Update visualizer title to show error
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.border_title = "xSwarm - ERROR"

    def update_visualizer(self):
        """Update visualizer at 30 FPS"""
        try:
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.amplitude = self.amplitude
            # VoiceVisualizerPanel doesn't have state - it animates automatically

            # Update status widget
            status = self.query_one("#status", StatusWidget)
            status.state = self.state
        except Exception:
            pass  # Widget not ready yet

    def update_activity(self, message: str):
        """Add message to activity feed"""
        activity = self.query_one("#activity", ActivityFeed)
        activity.add_message(message)

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard input"""
        if event.key == "q":
            self.exit()
        elif event.key == "s":
            # Open settings
            self.action_open_settings()
        elif event.key == "v":
            # Open voice visualizer demo
            self.action_open_viz_demo()
        elif event.key == "space":
            # Toggle listening
            if self.state == "idle" or self.state == "ready":
                self.start_listening()
            elif self.state == "listening":
                self.stop_listening()
        elif event.key == "ctrl+c":
            # Copy recent activity to clipboard
            self.action_copy_activity()
        elif event.key == "ctrl+v":
            # Paste from clipboard (shows what's in clipboard)
            self.action_paste()

    async def action_open_settings(self):
        """Open settings screen"""
        result = await self.push_screen(SettingsScreen(self.config, self.personas_dir), wait_for_dismiss=True)
        if result:
            # Update config if settings were saved
            self.config = result
            self.update_activity("Settings updated")

    async def action_open_viz_demo(self):
        """Open voice visualizer demo screen"""
        await self.push_screen(VoiceVizDemoScreen(), wait_for_dismiss=True)
        self.update_activity("Opened voice visualizer demo")

    def start_listening(self):
        """Start voice input"""
        self.state = "listening"
        self.update_activity("Listening...")

    def stop_listening(self):
        """Stop voice input"""
        self.state = "idle"
        self.update_activity("Stopped listening")

    def action_copy_activity(self):
        """Copy recent activity messages to clipboard"""
        try:
            activity = self.query_one("#activity", ActivityFeed)

            # Get last 20 messages (or all if less than 20)
            messages = list(activity.messages)[-20:]

            if not messages:
                self.update_activity("No messages to copy")
                return

            # Format messages as plain text
            lines = []
            for msg in messages:
                timestamp = msg["timestamp"]
                msg_type = msg["type"].upper()
                message = msg["message"]
                lines.append(f"[{timestamp}] {msg_type}: {message}")

            # Copy to clipboard
            text = "\n".join(lines)
            pyperclip.copy(text)

            self.update_activity(f"Copied {len(messages)} messages to clipboard")
        except Exception as e:
            self.update_activity(f"Error copying to clipboard: {e}")

    def action_paste(self):
        """Show clipboard contents in activity feed"""
        try:
            clipboard_text = pyperclip.paste()

            if not clipboard_text:
                self.update_activity("Clipboard is empty")
                return

            # Show first 200 chars of clipboard
            preview = clipboard_text[:200]
            if len(clipboard_text) > 200:
                preview += "..."

            self.update_activity(f"Clipboard: {preview}")

            # If it's multi-line, show line count
            lines = clipboard_text.split("\n")
            if len(lines) > 1:
                self.update_activity(f"Clipboard contains {len(lines)} lines, {len(clipboard_text)} chars")
        except Exception as e:
            self.update_activity(f"Error reading clipboard: {e}")
