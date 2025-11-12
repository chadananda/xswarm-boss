"""
Main Textual TUI application.
Replaces Rust Ratatui dashboard.
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.widgets import Header, Footer, Static, Label, Button, RadioButton, RadioSet, Input, Tree
from textual.reactive import reactive
from textual import events
from rich.text import Text
import asyncio
from typing import Optional
from pathlib import Path
import pyperclip
import datetime

from .widgets.visualizer import AudioVisualizer, CyberpunkVisualizer
from .widgets.panels import VoiceVisualizerPanel, VisualizationStyle
from .widgets.activity_feed import ActivityFeed
from .widgets.footer import CyberpunkFooter
from .widgets.project_dashboard import ProjectDashboard
from .widgets.worker_dashboard import WorkerDashboard
from .widgets.schedule_widget import ScheduleWidget
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
    active_tab = reactive("status")  # status, settings, tools, chat, projects, schedule, workers

    # Reactive theme colors - automatically update UI when changed
    theme_shade_1 = reactive("#252a33")
    theme_shade_2 = reactive("#363d47")
    theme_shade_3 = reactive("#4d5966")
    theme_shade_4 = reactive("#6b7a8a")
    theme_shade_5 = reactive("#8899aa")

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
        """Compose the dashboard layout: left column (visualizer + tabs) + right column (content) + footer at bottom"""
        # Main content area with two columns
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
                    yield Button(" 📊  Status", id="tab-status", classes="tab-button active-tab")
                    yield Button(" ⚙️   Settings", id="tab-settings", classes="tab-button")
                    yield Button(" 🔧  Tools", id="tab-tools", classes="tab-button")
                    yield Button(" 💬  Chat", id="tab-chat", classes="tab-button")
                    yield Button(" 📁  Projects", id="tab-projects", classes="tab-button")
                    yield Button(" 📅  Schedule", id="tab-schedule", classes="tab-button")
                    yield Button(" 💻  Workers", id="tab-workers", classes="tab-button")

            # RIGHT COLUMN - Content area
            with Container(id="content-area"):
                # Status content - Activity feed only (event/error log)
                with Container(id="content-status", classes="content-pane active-pane"):
                    yield Static("[dim]📊[/dim] Status", classes="pane-header")
                    yield ActivityFeed(id="activity")

                # Settings content
                with Container(id="content-settings", classes="content-pane"):
                    yield Static("[dim]⚙️[/dim] Settings", classes="pane-header")

                    # Theme group box
                    with Container(classes="settings-group") as theme_group:
                        theme_group.border_title = "Theme"
                        with RadioSet(id="theme-selector"):
                            # Will be populated dynamically with available themes
                            pass

                    # OAuth Connectors group box
                    with Container(classes="settings-group", id="oauth-connectors-group") as oauth_group:
                        oauth_group.border_title = "Connected Services"
                        with ScrollableContainer(id="oauth-connectors-list"):
                            # Gmail - Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("📧", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Gmail", classes="oauth-name")
                                    yield Static("✅ Connected • user@example.com", classes="oauth-status connected")
                                    yield Static("Synced 5 minutes ago", classes="oauth-sync-time")
                                yield Button("Disconnect", id="oauth-gmail-btn", classes="oauth-button oauth-disconnect")
                            # Google Calendar - Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("📅", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Google Calendar", classes="oauth-name")
                                    yield Static("✅ Connected • user@example.com", classes="oauth-status connected")
                                    yield Static("Synced 2 minutes ago", classes="oauth-sync-time")
                                yield Button("Disconnect", id="oauth-gcal-btn", classes="oauth-button oauth-disconnect")
                            # Slack - Not Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("💬", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Slack", classes="oauth-name")
                                    yield Static("⭕ Not Connected", classes="oauth-status disconnected")
                                    yield Static("", classes="oauth-sync-time")
                                yield Button("Connect", id="oauth-slack-btn", classes="oauth-button oauth-connect")
                            # GitHub - Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("🐙", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("GitHub", classes="oauth-name")
                                    yield Static("✅ Connected • github_username", classes="oauth-status connected")
                                    yield Static("Synced 1 hour ago", classes="oauth-sync-time")
                                yield Button("Disconnect", id="oauth-github-btn", classes="oauth-button oauth-disconnect")
                            # Microsoft 365 - Not Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("📨", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Microsoft 365", classes="oauth-name")
                                    yield Static("⭕ Not Connected", classes="oauth-status disconnected")
                                    yield Static("", classes="oauth-sync-time")
                                yield Button("Connect", id="oauth-ms365-btn", classes="oauth-button oauth-connect")
                            # Notion - Not Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("📝", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Notion", classes="oauth-name")
                                    yield Static("⭕ Not Connected", classes="oauth-status disconnected")
                                    yield Static("", classes="oauth-sync-time")
                                yield Button("Connect", id="oauth-notion-btn", classes="oauth-button oauth-connect")
                            # Trello - Not Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("📋", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Trello", classes="oauth-name")
                                    yield Static("⭕ Not Connected", classes="oauth-status disconnected")
                                    yield Static("", classes="oauth-sync-time")
                                yield Button("Connect", id="oauth-trello-btn", classes="oauth-button oauth-connect")
                            # Zoom - Connected
                            with Horizontal(classes="oauth-connector"):
                                yield Static("🎥", classes="oauth-icon")
                                with Vertical(classes="oauth-info"):
                                    yield Static("Zoom", classes="oauth-name")
                                    yield Static("✅ Connected • user@example.com", classes="oauth-status connected")
                                    yield Static("Synced 30 minutes ago", classes="oauth-sync-time")
                                yield Button("Disconnect", id="oauth-zoom-btn", classes="oauth-button oauth-disconnect")

                    # Device group box (placeholder for future)
                    with Container(classes="settings-group") as device_group:
                        device_group.border_title = "Device"
                        yield Static("Device selection coming soon", classes="placeholder-text")

                # Tools content
                with Container(id="content-tools", classes="content-pane"):
                    yield Static("[dim]🔧[/dim] Tools", classes="pane-header")

                    # Create tools tree with feature groups
                    tree = Tree("", id="tools-tree")
                    tree.show_root = False
                    tree.root.expand()

                    # Email Management
                    email_node = tree.root.add("📧 Email Management", expand=True)
                    email_node.add_leaf("☑ Read Unread Email")
                    email_node.add_leaf("☐ Search Email Archive")
                    email_node.add_leaf("☐ Draft Email Response")
                    email_node.add_leaf("☐ Send Email")
                    email_node.add_leaf("☐ Prune Old Email")
                    email_node.add_leaf("☐ Email Analytics")

                    # xSwarm Theme & Persona
                    xswarm_node = tree.root.add("🎨 xSwarm Customization", expand=True)
                    xswarm_node.add_leaf("☑ Change Theme")
                    xswarm_node.add_leaf("☑ Switch Persona")
                    xswarm_node.add_leaf("☐ Customize Voice")
                    xswarm_node.add_leaf("☐ Adjust Wake Word")

                    # Project Management
                    project_node = tree.root.add("📋 Project Management", expand=True)
                    project_node.add_leaf("☑ View Projects")
                    project_node.add_leaf("☐ Create Project")
                    project_node.add_leaf("☐ Update Task Status")
                    project_node.add_leaf("☐ Assign Tasks")
                    project_node.add_leaf("☐ Generate Reports")
                    project_node.add_leaf("☐ Schedule Meetings")

                    # Worker Management
                    worker_node = tree.root.add("⚙️  Worker Management", expand=True)
                    worker_node.add_leaf("☑ View Workers")
                    worker_node.add_leaf("☐ Start Worker Task")
                    worker_node.add_leaf("☐ Stop Worker Task")
                    worker_node.add_leaf("☐ Worker Health Check")
                    worker_node.add_leaf("☐ Resource Monitoring")

                    # File Search & Management
                    file_node = tree.root.add("🔍 File Operations", expand=True)
                    file_node.add_leaf("☐ Index Local Files")
                    file_node.add_leaf("☐ Search Files")
                    file_node.add_leaf("☐ Find Duplicates")
                    file_node.add_leaf("☐ Organize Files")
                    file_node.add_leaf("☐ Backup Files")

                    # System Control
                    system_node = tree.root.add("💻 System Control", expand=True)
                    system_node.add_leaf("☐ Adjust Volume")
                    system_node.add_leaf("☐ Control Music Playback")
                    system_node.add_leaf("☐ Set System Preferences")
                    system_node.add_leaf("☐ Manage Applications")
                    system_node.add_leaf("☐ System Monitoring")

                    # Voice Commands
                    voice_node = tree.root.add("🎤 Voice Commands", expand=True)
                    voice_node.add_leaf("☑ Voice Recognition")
                    voice_node.add_leaf("☑ Voice Synthesis")
                    voice_node.add_leaf("☐ Custom Commands")
                    voice_node.add_leaf("☐ Command Shortcuts")

                    # AI & Automation
                    ai_node = tree.root.add("🤖 AI Capabilities", expand=True)
                    ai_node.add_leaf("☑ Natural Language Processing")
                    ai_node.add_leaf("☑ Context Understanding")
                    ai_node.add_leaf("☐ Task Automation")
                    ai_node.add_leaf("☐ Smart Suggestions")
                    ai_node.add_leaf("☐ Learning Mode")

                    yield tree

                # Chat content
                with Container(id="content-chat", classes="content-pane"):
                    yield Static("[dim]💬[/dim] Chat", classes="pane-header")
                    yield Static("", id="chat-history")
                    yield Input(placeholder="Type a message...", id="chat-input")

                # Projects content
                with Container(id="content-projects", classes="content-pane"):
                    yield Static("[dim]📁[/dim] Projects", classes="pane-header")
                    yield ProjectDashboard(id="projects-dashboard")

                # Schedule content
                with Container(id="content-schedule", classes="content-pane"):
                    yield Static("[dim]📅[/dim] Schedule", classes="pane-header")
                    yield ScheduleWidget(id="schedule-widget")

                # Workers content
                with Container(id="content-workers", classes="content-pane"):
                    yield Static("[dim]💻[/dim] Workers", classes="pane-header")
                    yield WorkerDashboard(id="workers-dashboard")
        # Footer outside main-layout to span full width at bottom
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

        # Add dummy chat messages
        self.add_dummy_chat_messages()

        # Load MOSHI and start immediately
        asyncio.create_task(self.initialize_moshi())

    def add_dummy_chat_messages(self):
        """Add dummy chat messages for demonstration"""
        current_time = datetime.datetime.now()
        # Add messages with timestamps going back in time
        dummy_messages = [
            ("assistant", "Hello! I'm your voice assistant. How can I help you today?", 8),
            ("user", "Can you tell me about the weather?", 7),
            ("assistant", "I'd be happy to help with that! However, I don't have access to live weather data at the moment. I can help you with other tasks like managing your schedule, answering questions, or controlling your smart home devices.", 6),
            ("user", "What can you do?", 5),
            ("assistant", "I can help you with a variety of tasks including:\n• Managing your schedule and reminders\n• Answering questions and providing information\n• Voice commands for smart home control\n• Natural conversation and assistance", 4),
            ("user", "That sounds great!", 3),
            ("assistant", "I'm glad you think so! Feel free to ask me anything or give me a command. Just press the SPACE bar to start talking.", 2),
            ("user", "How do I change the theme?", 1),
            ("assistant", "You can change the theme by clicking on the Settings tab in the sidebar, then selecting a theme from the available options. Each persona has its own unique color theme!", 0),
        ]
        # Add messages with calculated timestamps
        for role, message, minutes_ago in dummy_messages:
            timestamp = (current_time - datetime.timedelta(minutes=minutes_ago)).strftime("%H:%M:%S")
            self.chat_history.append({
                "role": role,
                "message": message,
                "timestamp": timestamp
            })
        # Update the display
        self.update_chat_display()
        # Add mock error events to activity feed
        activity = self.query_one("#activity", ActivityFeed)
        activity.add_message("Mock connection error - network timeout", "error")
        activity.add_message("Mock warning - high CPU usage detected", "warning")
        activity.add_message("Mock critical error - failed to load model checkpoint", "error")

    def populate_theme_selector(self):
        """Populate theme selector with available persona themes"""
        try:
            radio_set = self.query_one("#theme-selector", RadioSet)
            # Get personas with theme colors
            themed_personas = [p for p in self.available_personas if p.theme and p.theme.theme_color]
            # Add radio button for each themed persona
            for persona in themed_personas:
                radio_btn = RadioButton(persona.name)
                radio_btn.id = f"theme-{persona.name.lower().replace(' ', '-')}"
                # Note: RadioButton.value is a boolean (pressed state), not for custom data
                # We use label (persona.name) to identify which persona was selected
                radio_set.mount(radio_btn)
            # Log how many themes we loaded
            self.update_activity(f"Loaded {len(themed_personas)} themed personas")
        except Exception as e:
            self.update_activity(f"Error populating themes: {e}")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle tab button clicks and OAuth connector buttons"""
        button_id = event.button.id

        # Determine which tab was clicked
        if button_id == "tab-status":
            self.active_tab = "status"
        elif button_id == "tab-settings":
            self.active_tab = "settings"
        elif button_id == "tab-tools":
            self.active_tab = "tools"
        elif button_id == "tab-chat":
            self.active_tab = "chat"
        elif button_id == "tab-projects":
            self.active_tab = "projects"
        elif button_id == "tab-schedule":
            self.active_tab = "schedule"
        elif button_id == "tab-workers":
            self.active_tab = "workers"
        # Handle OAuth connector buttons
        elif button_id and button_id.startswith("oauth-"):
            self.handle_oauth_button(button_id, event.button)

    def handle_oauth_button(self, button_id: str, button: Button) -> None:
        """Handle OAuth connector button clicks (mock functionality)"""
        # Extract service name from button ID (e.g., "oauth-gmail-btn" -> "gmail")
        service = button_id.replace("oauth-", "").replace("-btn", "")
        # Service display names mapping
        service_names = {
            "gmail": "Gmail",
            "gcal": "Google Calendar",
            "slack": "Slack",
            "github": "GitHub",
            "ms365": "Microsoft 365",
            "notion": "Notion",
            "trello": "Trello",
            "zoom": "Zoom"
        }
        service_name = service_names.get(service, service)
        # Get the connector container
        try:
            connector = button.parent
            status_widget = connector.query_one(".oauth-status", Static)
            sync_time_widget = connector.query_one(".oauth-sync-time", Static)
            # Check current state
            is_connected = "connected" in status_widget.classes
            if is_connected:
                # Disconnect
                status_widget.update("⭕ Not Connected")
                status_widget.remove_class("connected")
                status_widget.add_class("disconnected")
                sync_time_widget.update("")
                button.label = "Connect"
                button.remove_class("oauth-disconnect")
                button.add_class("oauth-connect")
                self.update_activity(f"🔌 Disconnected from {service_name}")
            else:
                # Connect
                status_widget.update(f"✅ Connected • mock_user@example.com")
                status_widget.remove_class("disconnected")
                status_widget.add_class("connected")
                sync_time_widget.update("Synced just now")
                button.label = "Disconnect"
                button.remove_class("oauth-connect")
                button.add_class("oauth-disconnect")
                self.update_activity(f"✅ Connected to {service_name}")
        except Exception as e:
            self.update_activity(f"Error toggling {service_name}: {e}")

    def watch_active_tab(self, new_tab: str) -> None:
        """Reactive watcher - called when active_tab changes"""
        try:
            # Update button styles
            for button_id in ["tab-status", "tab-settings", "tab-tools", "tab-chat", "tab-projects", "tab-schedule", "tab-workers"]:
                button = self.query_one(f"#{button_id}", Button)
                if button_id == f"tab-{new_tab}":
                    button.add_class("active-tab")
                else:
                    button.remove_class("active-tab")

            # Update content pane visibility
            for content_id in ["content-status", "content-settings", "content-tools", "content-chat", "content-projects", "content-schedule", "content-workers"]:
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
        # Get selected persona name from RadioButton label
        # Note: RadioButton.value is a boolean (pressed state), not custom data
        # We use label which contains the persona.name
        selected_persona_name = event.pressed.label.plain if event.pressed else None
        if not selected_persona_name:
            return
        # Switch to selected persona theme
        persona = self.persona_manager.get_persona(selected_persona_name)
        if persona and persona.theme and persona.theme.theme_color:
            self.update_activity(f"🎨 Switching to {persona.name} theme ({persona.theme.theme_color})")
            # Regenerate theme palette
            self._theme_palette = self._load_theme(persona.theme.theme_color)
            # Update reactive colors - triggers watchers that update ALL UI elements
            self.theme_shade_1 = self._theme_palette.shade_1
            self.theme_shade_2 = self._theme_palette.shade_2
            self.theme_shade_3 = self._theme_palette.shade_3
            self.theme_shade_4 = self._theme_palette.shade_4
            self.theme_shade_5 = self._theme_palette.shade_5
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
            self.theme_shade_1 = self._theme_palette.shade_1
            self.theme_shade_2 = self._theme_palette.shade_2
            self.theme_shade_3 = self._theme_palette.shade_3
            self.theme_shade_4 = self._theme_palette.shade_4
            self.theme_shade_5 = self._theme_palette.shade_5

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

    def update_tools_tree_colors(self):
        """Rebuild tools tree with current theme colors"""
        try:
            tree = self.query_one("#tools-tree", Tree)
            tree.clear()
            # Get current theme shade for tree items
            shade_4 = self.theme_shade_4
            # Email Management
            email_node = tree.root.add(f"[{shade_4}]📧 Email Management[/{shade_4}]", expand=True)
            email_node.add_leaf(f"[{shade_4}]☑ Read Unread Email[/{shade_4}]")
            email_node.add_leaf(f"[{shade_4}]☐ Search Email Archive[/{shade_4}]")
            email_node.add_leaf(f"[{shade_4}]☐ Draft Email Response[/{shade_4}]")
            email_node.add_leaf(f"[{shade_4}]☐ Send Email[/{shade_4}]")
            email_node.add_leaf(f"[{shade_4}]☐ Prune Old Email[/{shade_4}]")
            email_node.add_leaf(f"[{shade_4}]☐ Email Analytics[/{shade_4}]")
            # xSwarm Theme & Persona
            xswarm_node = tree.root.add(f"[{shade_4}]🎨 xSwarm Customization[/{shade_4}]", expand=True)
            xswarm_node.add_leaf(f"[{shade_4}]☑ Change Theme[/{shade_4}]")
            xswarm_node.add_leaf(f"[{shade_4}]☑ Switch Persona[/{shade_4}]")
            xswarm_node.add_leaf(f"[{shade_4}]☐ Customize Voice[/{shade_4}]")
            xswarm_node.add_leaf(f"[{shade_4}]☐ Adjust Wake Word[/{shade_4}]")
            # Project Management
            project_node = tree.root.add(f"[{shade_4}]📋 Project Management[/{shade_4}]", expand=True)
            project_node.add_leaf(f"[{shade_4}]☑ View Projects[/{shade_4}]")
            project_node.add_leaf(f"[{shade_4}]☐ Create Project[/{shade_4}]")
            project_node.add_leaf(f"[{shade_4}]☐ Update Task Status[/{shade_4}]")
            project_node.add_leaf(f"[{shade_4}]☐ Assign Tasks[/{shade_4}]")
            project_node.add_leaf(f"[{shade_4}]☐ Generate Reports[/{shade_4}]")
            project_node.add_leaf(f"[{shade_4}]☐ Schedule Meetings[/{shade_4}]")
            # Worker Management
            worker_node = tree.root.add(f"[{shade_4}]⚙️  Worker Management[/{shade_4}]", expand=True)
            worker_node.add_leaf(f"[{shade_4}]☑ View Workers[/{shade_4}]")
            worker_node.add_leaf(f"[{shade_4}]☐ Start Worker Task[/{shade_4}]")
            worker_node.add_leaf(f"[{shade_4}]☐ Stop Worker Task[/{shade_4}]")
            worker_node.add_leaf(f"[{shade_4}]☐ Worker Health Check[/{shade_4}]")
            worker_node.add_leaf(f"[{shade_4}]☐ Resource Monitoring[/{shade_4}]")
            # File Search & Management
            file_node = tree.root.add(f"[{shade_4}]🔍 File Operations[/{shade_4}]", expand=True)
            file_node.add_leaf(f"[{shade_4}]☐ Index Local Files[/{shade_4}]")
            file_node.add_leaf(f"[{shade_4}]☐ Search Files[/{shade_4}]")
            file_node.add_leaf(f"[{shade_4}]☐ Find Duplicates[/{shade_4}]")
            file_node.add_leaf(f"[{shade_4}]☐ Organize Files[/{shade_4}]")
            file_node.add_leaf(f"[{shade_4}]☐ Backup Files[/{shade_4}]")
            # System Control
            system_node = tree.root.add(f"[{shade_4}]💻 System Control[/{shade_4}]", expand=True)
            system_node.add_leaf(f"[{shade_4}]☐ Adjust Volume[/{shade_4}]")
            system_node.add_leaf(f"[{shade_4}]☐ Control Music Playback[/{shade_4}]")
            system_node.add_leaf(f"[{shade_4}]☐ Set System Preferences[/{shade_4}]")
            system_node.add_leaf(f"[{shade_4}]☐ Manage Applications[/{shade_4}]")
            system_node.add_leaf(f"[{shade_4}]☐ System Monitoring[/{shade_4}]")
            # Voice Commands
            voice_node = tree.root.add(f"[{shade_4}]🎤 Voice Commands[/{shade_4}]", expand=True)
            voice_node.add_leaf(f"[{shade_4}]☑ Voice Recognition[/{shade_4}]")
            voice_node.add_leaf(f"[{shade_4}]☑ Voice Synthesis[/{shade_4}]")
            voice_node.add_leaf(f"[{shade_4}]☐ Custom Commands[/{shade_4}]")
            voice_node.add_leaf(f"[{shade_4}]☐ Command Shortcuts[/{shade_4}]")
            # AI & Automation
            ai_node = tree.root.add(f"[{shade_4}]🤖 AI Capabilities[/{shade_4}]", expand=True)
            ai_node.add_leaf(f"[{shade_4}]☑ Natural Language Processing[/{shade_4}]")
            ai_node.add_leaf(f"[{shade_4}]☑ Context Understanding[/{shade_4}]")
            ai_node.add_leaf(f"[{shade_4}]☐ Task Automation[/{shade_4}]")
            ai_node.add_leaf(f"[{shade_4}]☐ Smart Suggestions[/{shade_4}]")
            ai_node.add_leaf(f"[{shade_4}]☐ Learning Mode[/{shade_4}]")
        except Exception as e:
            pass

    def watch_theme_shade_3(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_3 changes"""
        try:
            from textual.color import Color
            color = Color.parse(new_color)
            # Get widgets
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            footer = self.query_one("#footer", CyberpunkFooter)
            # Update borders directly
            visualizer.styles.border = ("solid", color)
            # DO NOT set activity border - let CSS handle it to avoid double border
            footer.styles.border = ("solid", color)
            # Update pane borders
            for pane_id in ["content-status", "content-settings", "content-tools", "content-chat", "content-projects", "content-schedule", "content-workers"]:
                try:
                    pane = self.query_one(f"#{pane_id}", Container)
                    pane.styles.border = ("solid", color)
                except Exception:
                    pass
            # Update background colors with extremely subtle opacity (10-20%)
            bg_color = Color.parse(self._theme_palette.shade_1)
            vis_bg = bg_color.with_alpha(0.15)  # Barely visible tint
            act_bg = bg_color.with_alpha(0.12)  # Even more subtle
            visualizer.styles.background = vis_bg
            # Get activity feed for background and theme colors
            activity = self.query_one("#activity", ActivityFeed)
            activity.styles.background = act_bg
            # CRITICAL FIX: Pass theme palette to widgets so they render with dynamic colors
            # The widgets render Rich Text with explicit colors, so we need to give them
            # the palette to use instead of their hardcoded colors
            theme_colors_dict = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }
            visualizer.theme_colors = theme_colors_dict
            activity.theme_colors = theme_colors_dict
            footer.theme_colors = theme_colors_dict
            # Update project dashboard if available
            try:
                project_dashboard = self.query_one("#projects-dashboard", ProjectDashboard)
                project_dashboard.theme_colors = theme_colors_dict
                project_dashboard.refresh()
            except Exception:
                pass
            # Update worker dashboard if available
            try:
                worker_dashboard = self.query_one("#workers-dashboard", WorkerDashboard)
                worker_dashboard.theme_colors = theme_colors_dict
                worker_dashboard.refresh()
            except Exception:
                pass
            # Update schedule widget if available
            try:
                schedule_widget = self.query_one("#schedule-widget", ScheduleWidget)
                schedule_widget.theme_colors = theme_colors_dict
                schedule_widget.refresh()
            except Exception:
                pass
            # Force refresh to re-render with new colors
            visualizer.refresh()
            activity.refresh()
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
            visualizer.styles.border_title_color = color
            activity.styles.border_title_color = color
            # Update pane headers text color
            for header in self.query(".pane-header"):
                header.styles.color = color
                header.refresh()
            # Update tab button colors
            for button in self.query(".tab-button"):
                if button.has_class("active-tab"):
                    button.styles.color = Color.parse(self._theme_palette.shade_5)
                else:
                    button.styles.color = color
                button.refresh()
            # Update tools tree colors
            self.update_tools_tree_colors()
        except Exception:
            pass

    def watch_theme_shade_2(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_2 changes"""
        try:
            from textual.color import Color
            color = Color.parse(new_color)
            # Update footer border
            footer = self.query_one("#footer", CyberpunkFooter)
            footer.styles.border = ("solid", color)
            # Update active tab background
            for button in self.query(".tab-button.active-tab"):
                button.styles.background = color
                button.refresh()
            # Pass theme colors to footer for text rendering
            theme_colors_dict = {
                "shade_1": self._theme_palette.shade_1,
                "shade_2": self._theme_palette.shade_2,
                "shade_3": self._theme_palette.shade_3,
                "shade_4": self._theme_palette.shade_4,
                "shade_5": self._theme_palette.shade_5,
            }
            footer.theme_colors = theme_colors_dict
            # Force refresh to re-render with new colors
            footer.refresh()
        except Exception:
            pass

    def watch_theme_shade_1(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_1 changes"""
        try:
            from textual.color import Color
            # Update background colors with subtle opacity
            bg_color = Color.parse(new_color)
            try:
                visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                activity = self.query_one("#activity", ActivityFeed)
                vis_bg = bg_color.with_alpha(0.15)
                act_bg = bg_color.with_alpha(0.12)
                visualizer.styles.background = vis_bg
                activity.styles.background = act_bg
                visualizer.refresh()
                activity.refresh()
            except Exception:
                pass
        except Exception:
            pass

    def watch_theme_shade_5(self, new_color: str) -> None:
        """Reactive watcher - called when theme_shade_5 changes"""
        try:
            from textual.color import Color
            color = Color.parse(new_color)
            # Update active tab text color
            for button in self.query(".tab-button.active-tab"):
                button.styles.color = color
                button.refresh()
        except Exception:
            pass

    def update_visualizer(self):
        """Update visualizer at 30 FPS"""
        try:
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.amplitude = self.amplitude
            # VoiceVisualizerPanel doesn't have state - it animates automatically
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

            # Build chat text with theme colors
            lines = []
            for msg in self.chat_history[-20:]:  # Show last 20 messages
                timestamp = msg["timestamp"]
                role = msg["role"].upper()
                message = msg["message"]

                if role == "USER":
                    # User messages: bright, with dim timestamp
                    lines.append(f"[dim][{timestamp}][/dim] [bold {self.theme_shade_5}]YOU:[/bold {self.theme_shade_5}]")
                    lines.append(f"[{self.theme_shade_5}]  {message}[/{self.theme_shade_5}]\n")
                else:
                    # AI messages: medium color, with dim timestamp
                    lines.append(f"[dim][{timestamp}][/dim] [bold {self.theme_shade_4}]{self.current_persona_name}:[/bold {self.theme_shade_4}]")
                    lines.append(f"[{self.theme_shade_4}]  {message}[/{self.theme_shade_4}]\n")

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
