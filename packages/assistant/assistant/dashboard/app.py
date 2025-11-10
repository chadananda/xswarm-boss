"""
Main Textual TUI application.
Replaces Rust Ratatui dashboard.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from textual import events
from rich.text import Text
import asyncio
from typing import Optional
from pathlib import Path

from .widgets.visualizer import AudioVisualizer
from .widgets.status import StatusWidget
from .widgets.activity_feed import ActivityFeed
from .screens import SettingsScreen, WizardScreen
from ..config import Config


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

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout"""
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="left-panel"):
                # Audio visualizer (pulsing circle)
                yield AudioVisualizer(id="visualizer")

                # Status information
                yield StatusWidget(id="status")

            with Vertical(id="right-panel"):
                # Activity feed / logs
                yield ActivityFeed(id="activity")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount"""
        self.set_interval(1/30, self.update_visualizer)  # 30 FPS

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

        except Exception as e:
            self.update_activity(f"Error loading voice models: {e}")
            self.state = "error"

            # Update status widget
            status = self.query_one("#status", StatusWidget)
            status.state = "error"

    def update_visualizer(self):
        """Update visualizer at 30 FPS"""
        visualizer = self.query_one("#visualizer", AudioVisualizer)
        visualizer.amplitude = self.amplitude
        visualizer.state = self.state

        # Also update status widget
        status = self.query_one("#status", StatusWidget)
        status.state = self.state

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
        elif event.key == "space":
            # Toggle listening
            if self.state == "idle" or self.state == "ready":
                self.start_listening()
            elif self.state == "listening":
                self.stop_listening()

    async def action_open_settings(self):
        """Open settings screen"""
        result = await self.push_screen(SettingsScreen(self.config, self.personas_dir), wait_for_dismiss=True)
        if result:
            # Update config if settings were saved
            self.config = result
            self.update_activity("Settings updated")

    def start_listening(self):
        """Start voice input"""
        self.state = "listening"
        self.update_activity("Listening...")

    def stop_listening(self):
        """Stop voice input"""
        self.state = "idle"
        self.update_activity("Stopped listening")
