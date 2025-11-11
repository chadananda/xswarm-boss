"""
Main Textual TUI application.
Replaces Rust Ratatui dashboard.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Header, Footer, Static, Label, Button, RadioButton, RadioSet
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
from ..personas.manager import PersonaManager
import re
import random


class VoiceAssistantApp(App):
    """Voice Assistant TUI Application"""

    TITLE = "Voice Assistant"

    # Reactive state
    state = reactive("idle")  # idle, listening, speaking, thinking
    amplitude = reactive(0.0)
    current_persona_name = reactive("Default")  # Current persona name
    active_tab = reactive("status")  # status, settings, chat

    # Reactive theme colors - automatically update UI when changed
    theme_shade_2 = reactive("#363d47")
    theme_shade_3 = reactive("#4d5966")
    theme_shade_4 = reactive("#6b7a8a")

    CSS_PATH = "styles.tcss"

    def __init__(self, config: Config, personas_dir: Path):
        super().__init__()
        self.config = config
        self.personas_dir = personas_dir
        self.moshi_bridge: Optional[object] = None
        self.audio_io: Optional[object] = None
        self.audio_buffer = []  # Buffer for capturing audio during listening
        self.chat_history = []  # Store chat messages (user + assistant)

        # Load personas
        self.persona_manager = PersonaManager(personas_dir)
        self.available_personas = list(self.persona_manager.personas.values())

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

    def compose(self) -> ComposeResult:
        """Compose the dashboard layout: left column (visualizer + tabs) + right column (content)"""
        with Horizontal(id="main-layout"):
            # LEFT COLUMN - Visualizer (top) + Tabs (bottom)
            with Vertical(id="left-column"):
                # Voice visualizer - small square at top
                viz_panel = VoiceVisualizerPanel(
                    visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE
                )
                viz_panel.id = "visualizer"
                viz_panel.simulation_mode = True
                yield viz_panel

                # Tab buttons below visualizer
                with Vertical(id="sidebar"):
                    yield Button("Status", id="tab-status", classes="tab-button active-tab")
                    yield Button("Settings", id="tab-settings", classes="tab-button")
                    yield Button("Chat", id="tab-chat", classes="tab-button")

            # RIGHT COLUMN - Content area
            with Container(id="content-area"):
                # Status content - Activity feed + Status widget
                with Container(id="content-status", classes="content-pane active-pane"):
                    yield ActivityFeed(id="activity")
                    yield StatusWidget(id="status")

                # Settings content
                with Container(id="content-settings", classes="content-pane"):
                    yield Label("Theme Selection", id="settings-title")
                    yield Label("Select a theme color:", id="theme-label")
                    with RadioSet(id="theme-selector"):
                        # Will be populated dynamically with available themes
                        pass

                # Chat content
                with Container(id="content-chat", classes="content-pane"):
                    yield Label("Conversation History", id="chat-title")
                    yield Static("", id="chat-history")

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

        # Populate theme selector with available themes
        self.populate_theme_selector()

        # Load MOSHI and start immediately
        asyncio.create_task(self.initialize_moshi())

    def populate_theme_selector(self):
        """Populate theme selector with available persona themes"""
        try:
            radio_set = self.query_one("#theme-selector", RadioSet)

            # Get personas with theme colors
            themed_personas = [p for p in self.available_personas if p.theme and p.theme.theme_color]

            # Add radio button for each themed persona
            for persona in themed_personas:
                radio_btn = RadioButton(
                    f"{persona.name} ({persona.theme.theme_color})",
                    value=persona.name
                )
                radio_set.mount(radio_btn)

            # Select current persona
            if self.current_persona_name:
                try:
                    radio_set.action_toggle()  # Will select first by default
                except:
                    pass

        except Exception as e:
            self.update_activity(f"Error populating themes: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle tab button clicks"""
        button_id = event.button.id

        # Determine which tab was clicked
        if button_id == "tab-status":
            self.active_tab = "status"
        elif button_id == "tab-settings":
            self.active_tab = "settings"
        elif button_id == "tab-chat":
            self.active_tab = "chat"

    def watch_active_tab(self, new_tab: str) -> None:
        """Reactive watcher - called when active_tab changes"""
        try:
            # Update button styles
            for button_id in ["tab-status", "tab-settings", "tab-chat"]:
                button = self.query_one(f"#{button_id}", Button)
                if button_id == f"tab-{new_tab}":
                    button.add_class("active-tab")
                else:
                    button.remove_class("active-tab")

            # Update content pane visibility
            for content_id in ["content-status", "content-settings", "content-chat"]:
                pane = self.query_one(f"#{content_id}", Container)
                if content_id == f"content-{new_tab}":
                    pane.add_class("active-pane")
                else:
                    pane.remove_class("active-pane")
        except Exception:
            pass  # Widgets not ready yet

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle theme selection change"""
        if event.radio_set.id != "theme-selector":
            return

        # Get selected persona name
        selected_persona_name = event.pressed.value if event.pressed else None
        if not selected_persona_name:
            return

        # Switch to selected persona theme
        persona = self.persona_manager.get_persona(selected_persona_name)
        if persona and persona.theme and persona.theme.theme_color:
            self.update_activity(f"🎨 Switching to {persona.name} theme ({persona.theme.theme_color})")

            # Regenerate theme palette
            self._theme_palette = self._load_theme(persona.theme.theme_color)

            # Update reactive colors - triggers watchers that update ALL UI elements
            self.theme_shade_2 = self._theme_palette.shade_2
            self.theme_shade_3 = self._theme_palette.shade_3
            self.theme_shade_4 = self._theme_palette.shade_4

            # Update current persona name
            self.current_persona_name = persona.name

            # Update title
            self.title = f"xSwarm Voice Assistant - {persona.name}"

            # Update visualizer border title
            try:
                visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                visualizer.border_title = f"xSwarm - {persona.name}"
            except Exception:
                pass

    def on_unmount(self) -> None:
        """Cleanup on exit"""
        # Stop audio streams
        if self.audio_io:
            self.audio_io.stop()
            self.update_activity("Audio streams stopped")

    async def initialize_moshi(self):
        """Load voice models and initialize audio"""
        try:
            self.update_activity("Initializing voice models...")
            device = self.config.detect_device()

            # Initialize MOSHI bridge
            from ..voice.moshi_pytorch import MoshiBridge
            from ..voice.audio_io import AudioIO

            self.update_activity(f"Loading MOSHI models on {device}...")
            self.moshi_bridge = MoshiBridge(
                device=device,
                model_dir=self.config.model_dir
            )
            self.update_activity("✓ MOSHI models loaded")

            # Initialize audio I/O
            self.update_activity("Starting audio streams...")
            self.audio_io = AudioIO(
                sample_rate=24000,
                frame_size=1920,
                channels=1
            )

            # Start audio input with callback for visualization
            def audio_callback(audio):
                # Update amplitude for visualizer
                amplitude = self.moshi_bridge.get_amplitude(audio)
                self.amplitude = amplitude

            self.audio_io.start_input(callback=audio_callback)
            self.audio_io.start_output()
            self.update_activity("✓ Audio streams started")

            # Update status widget
            status = self.query_one("#status", StatusWidget)
            status.device_name = str(device)
            status.state = "ready"

            # Update visualizer with persona name
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            persona_name = self.config.default_persona or "JARVIS"
            visualizer.border_title = f"xSwarm - {persona_name}"

            # Generate greeting immediately
            self.state = "ready"
            self.update_activity(f"✓ Voice assistant ready on {device}")
            await self.generate_greeting()

        except Exception as e:
            self.update_activity(f"Error loading voice models: {e}")
            self.state = "error"

            # Update status widget
            status = self.query_one("#status", StatusWidget)
            status.state = "error"

            # Update visualizer title to show error
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.border_title = "xSwarm - ERROR"

    async def generate_greeting(self):
        """Generate and play automatic greeting on startup"""
        import numpy as np

        try:
            self.state = "speaking"
            self.update_activity("👋 Generating greeting...")

            # Get current persona
            persona_name = self.config.default_persona or "JARVIS"
            persona = self.persona_manager.get_persona(persona_name)

            # Create greeting prompt
            greeting_prompt = f"Hello! I'm {persona_name}. How can I help you today?"
            if persona and persona.system_prompt:
                # Use first 150 chars of system prompt for context
                greeting_prompt = persona.system_prompt[:150] + "\n\nGreet the user warmly."

            # Generate silent audio input (MOSHI needs input audio)
            silent_audio = np.zeros(1920, dtype=np.float32)

            # Generate greeting through MOSHI
            response_audio, response_text = self.moshi_bridge.generate_response(
                silent_audio,
                text_prompt=greeting_prompt,
                max_tokens=200  # Shorter for greeting
            )

            # Log the greeting text
            if response_text:
                self.update_activity(f"💬 {response_text}")
                self.add_chat_message("assistant", response_text)

            # Play greeting with amplitude updates
            await self.play_audio_with_visualization(response_audio)

            self.state = "ready"
            self.update_activity("✓ Ready to listen (press SPACE)")

        except Exception as e:
            self.update_activity(f"Error generating greeting: {e}")
            self.state = "ready"

    async def play_audio_with_visualization(self, audio: "np.ndarray"):
        """Play audio and update visualizer amplitude during playback"""
        import numpy as np

        # Calculate frame size for chunking
        frame_size = 1920  # 80ms at 24kHz
        num_frames = len(audio) // frame_size

        # Queue audio for playback
        self.audio_io.play_audio(audio)

        # Update visualizer amplitude during playback
        for i in range(num_frames):
            frame = audio[i * frame_size:(i + 1) * frame_size]
            amplitude = self.moshi_bridge.get_amplitude(frame)
            self.amplitude = amplitude
            await asyncio.sleep(0.08)  # 80ms per frame

        # Reset amplitude after playback
        self.amplitude = 0.0

    def rotate_persona(self):
        """Randomly switch to a different persona"""
        if not self.available_personas:
            return

        # Only select personas that have theme_color defined
        themed_personas = [p for p in self.available_personas if p.theme and p.theme.theme_color]

        if not themed_personas:
            # Fallback to any persona if none have themes
            persona = random.choice(self.available_personas)
        else:
            # Pick a random persona with theme
            persona = random.choice(themed_personas)

        # Update theme if persona has a theme_color
        if persona.theme and persona.theme.theme_color:
            # Log what we're doing
            self.update_activity(f"🔄 Switching to {persona.name} theme color {persona.theme.theme_color}")

            # Regenerate theme palette
            self._theme_palette = self._load_theme(persona.theme.theme_color)

            # Update reactive colors - triggers watchers that update ALL UI elements
            self.theme_shade_2 = self._theme_palette.shade_2
            self.theme_shade_3 = self._theme_palette.shade_3
            self.theme_shade_4 = self._theme_palette.shade_4

            self.update_activity(f"   Colors: {self._theme_palette.shade_1} → {self._theme_palette.shade_5}")

        # Update current persona name
        self.current_persona_name = persona.name

        # Update title
        self.title = f"xSwarm Voice Assistant - {persona.name}"

        # Log the switch to activity feed
        self.update_activity(f"👤 Switched to persona: {persona.name}")

        # Update visualizer border title
        try:
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.border_title = f"xSwarm - {persona.name}"
        except Exception:
            pass

    def watch_theme_shade_3(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_3 changes"""
        try:
            from textual.color import Color
            color = Color.parse(new_color)

            # Get widgets
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            activity = self.query_one("#activity", ActivityFeed)
            status = self.query_one("#status", StatusWidget)
            footer = self.query_one("#footer", CyberpunkFooter)

            # Update borders
            visualizer.styles.border = ("solid", color)
            activity.styles.border = ("solid", color)
            status.styles.border = ("solid", color)
            footer.styles.border = ("solid", color)

            # Update background colors with extremely subtle opacity (10-20%)
            bg_color = Color.parse(self._theme_palette.shade_1)
            vis_bg = bg_color.with_alpha(0.15)  # Barely visible tint
            act_bg = bg_color.with_alpha(0.12)  # Even more subtle
            stat_bg = bg_color.with_alpha(0.15)  # Barely visible tint

            visualizer.styles.background = vis_bg
            activity.styles.background = act_bg
            status.styles.background = stat_bg

            # CRITICAL FIX: Pass theme palette to widgets so they render with dynamic colors
            # The widgets render Rich Text with explicit colors, so we need to give them
            # the palette to use instead of their hardcoded colors
            visualizer.theme_colors = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }
            activity.theme_colors = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }
            status.theme_colors = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }
            footer.theme_colors = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }

            # Force refresh to re-render with new colors
            visualizer.refresh()
            activity.refresh()
            status.refresh()
            footer.refresh()
        except Exception:
            pass  # Widget not ready yet

    def watch_theme_shade_4(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_4 changes"""
        try:
            from textual.color import Color
            color = Color.parse(new_color)

            # Update border titles
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            activity = self.query_one("#activity", ActivityFeed)
            status = self.query_one("#status", StatusWidget)

            visualizer.styles.border_title_color = color
            activity.styles.border_title_color = color
            status.styles.border_title_color = color
        except Exception:
            pass

    def watch_theme_shade_2(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_2 changes"""
        try:
            from textual.color import Color
            color = Color.parse(new_color)

            # Update header/footer borders
            header = self.query_one(CyberpunkHeader)
            footer = self.query_one("#footer", CyberpunkFooter)

            header.styles.border = ("solid", color)
            footer.styles.border = ("solid", color)

            # Pass theme colors to header and footer for text rendering
            theme_colors_dict = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }
            header.theme_colors = theme_colors_dict
            footer.theme_colors = theme_colors_dict

            # Force refresh to re-render with new colors
            header.refresh()
            footer.refresh()
        except Exception:
            pass

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

    def add_chat_message(self, role: str, message: str):
        """Add message to chat history and update display"""
        import datetime

        # Add to history
        self.chat_history.append({
            "role": role,  # "user" or "assistant"
            "message": message,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        })

        # Update chat display
        self.update_chat_display()

    def update_chat_display(self):
        """Update chat history display"""
        try:
            chat_display = self.query_one("#chat-history", Static)

            # Build chat text
            lines = []
            for msg in self.chat_history[-20:]:  # Show last 20 messages
                timestamp = msg["timestamp"]
                role = msg["role"].upper()
                message = msg["message"]

                if role == "USER":
                    lines.append(f"[bold cyan][{timestamp}] YOU:[/bold cyan]")
                else:
                    lines.append(f"[bold yellow][{timestamp}] {self.current_persona_name}:[/bold yellow]")

                lines.append(f"  {message}\n")

            chat_display.update("\n".join(lines))
        except Exception as e:
            pass  # Widget might not be ready

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
        """Start voice input - begin capturing audio"""
        if not self.audio_io or not self.moshi_bridge:
            self.update_activity("Voice models not loaded yet")
            return

        self.state = "listening"
        self.audio_buffer = []
        self.update_activity("🎤 Listening... (press SPACE again to stop)")

        # Start interval to capture audio frames
        self.set_interval(0.08, self.capture_audio_frame, name="audio_capture")

    def capture_audio_frame(self):
        """Capture audio frame into buffer (called every 80ms)"""
        if self.state != "listening":
            return

        frame = self.audio_io.read_frame(timeout=0.01)
        if frame is not None:
            self.audio_buffer.append(frame)

    def stop_listening(self):
        """Stop voice input and process audio through MOSHI"""
        if self.state != "listening":
            return

        # Stop capturing audio
        try:
            self.remove_interval("audio_capture")
        except:
            pass

        self.state = "thinking"
        self.update_activity("🤔 Processing...")

        # Process audio in background
        asyncio.create_task(self.process_voice_input())

    async def process_voice_input(self):
        """Process captured audio through MOSHI and play response"""
        import numpy as np

        try:
            if not self.audio_buffer:
                self.update_activity("No audio captured")
                self.state = "ready"
                return

            # Concatenate all audio frames
            user_audio = np.concatenate(self.audio_buffer)
            self.update_activity(f"Captured {len(user_audio)/24000:.1f}s of audio")
            self.add_chat_message("user", f"[Audio: {len(user_audio)/24000:.1f}s]")

            # Get current persona for prompt
            persona_name = self.current_persona_name
            persona = self.persona_manager.get_persona(persona_name)
            text_prompt = None
            if persona and persona.system_prompt:
                text_prompt = persona.system_prompt[:200]  # First 200 chars

            # Generate response through MOSHI
            self.state = "speaking"
            self.update_activity(f"🗣️ {persona_name} responding...")

            response_audio, response_text = self.moshi_bridge.generate_response(
                user_audio,
                text_prompt=text_prompt,
                max_tokens=500
            )

            # Log response text
            if response_text:
                self.update_activity(f"💬 {response_text[:100]}")
                self.add_chat_message("assistant", response_text)

            # Play response audio with visualization
            await self.play_audio_with_visualization(response_audio)
            self.update_activity("✓ Response complete")

            self.state = "ready"

        except Exception as e:
            self.update_activity(f"Error processing audio: {e}")
            self.state = "error"

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
