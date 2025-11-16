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
from ..voice.bridge import VoiceBridgeOrchestrator, ConversationState
from ..memory import MemoryManager
import re
import random


class VoiceAssistantApp(App):
    """Voice Assistant TUI Application"""

    TITLE = "Voice Assistant"

    # Key bindings
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

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
        self.memory_manager: Optional[MemoryManager] = None  # Memory manager for persistence
        self.user_id = "local-user"  # Default user ID
        # Voice bridge orchestrator (initialized later)
        self.voice_bridge: Optional[VoiceBridgeOrchestrator] = None
        self.voice_initialized = False
        # Load personas
        self.persona_manager = PersonaManager(personas_dir)
        self.available_personas = list(self.persona_manager.personas.values())

        # Set default persona on startup
        default_persona_name = config.default_persona or "JARVIS"
        if not self.persona_manager.set_current_persona(default_persona_name):
            # Fallback to first available persona if default not found
            if self.available_personas:
                self.persona_manager.set_current_persona(self.available_personas[0].name)

        # Initialize tool registry
        from ..tools import ToolRegistry, ThemeChangeTool
        from ..tools.email_tool import send_email_tool
        from ..tools.phone_tool import make_call_tool, feedback_call_tool
        self.tool_registry = ToolRegistry()
        # Register theme change tool (bound to this app instance)
        self.tool_registry.register_tool(ThemeChangeTool.create_tool(self))
        # Register email tool
        self.tool_registry.register_tool(send_email_tool)
        # Register phone tools
        self.tool_registry.register_tool(make_call_tool)
        self.tool_registry.register_tool(feedback_call_tool)

        # Generate dynamic theme colors
        self._theme_palette = self._load_theme(config.theme_base_color)

        # Keyboard navigation state
        self._nav_buttons = ["tab-status", "tab-settings", "tab-tools", "tab-chat",
                            "tab-projects", "tab-schedule", "tab-workers"]
        self._focused_nav_index = 0  # Track which nav button has keyboard focus

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
                # Voice visualizer - small square at top (visible but with 0 amplitude until voice initialized)
                viz_panel = VoiceVisualizerPanel(
                    visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE
                )
                viz_panel.id = "visualizer"
                viz_panel.simulation_mode = False  # Use real audio, not simulation
                # Don't hide the widget - keep it visible with 0 amplitude (will be set in on_mount)
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

                    # Persona selector group box
                    with Container(classes="settings-group") as persona_group:
                        persona_group.border_title = "Persona"
                        with RadioSet(id="theme-selector"):
                            # Will be populated dynamically with available personas
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
        with open("/tmp/xswarm_debug.log", "w") as f:
            f.write("DEBUG: on_mount() ENTRY\n")
            f.flush()
        # DON'T start update_visualizer() yet - wait until voice is initialized
        # This prevents Moshi animation from showing before models load

        # Start visualizer animation and set title to static "xSwarm Assistant"
        try:
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            visualizer.simulation_mode = False  # Ensure we use real audio, not simulation
            visualizer.start_animation()  # This starts the widget's internal 20 FPS loop

            # Set title to static "xSwarm Assistant" (not persona-specific)
            visualizer.border_title = "xSwarm Assistant"

            # Initialize with 0 connection_amplitude (not connected yet)
            visualizer.connection_amplitude = 0
        except Exception:
            pass

        # Set persona name inside visualizer (will be rendered above divider line)
        try:
            persona_name = self.config.default_persona or "JARVIS"
            visualizer.persona_name = persona_name
        except Exception:
            pass

        # Populate theme selector with available themes
        self.populate_theme_selector()

        # Initialize memory manager
        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write("DEBUG: on_mount() - before initialize_memory()\n")
            f.flush()
        asyncio.create_task(self.initialize_memory())
        # Add dummy chat messages
        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write("DEBUG: on_mount() - before add_dummy_chat_messages()\n")
            f.flush()
        self.add_dummy_chat_messages()
        # Initialize Moshi models in background with proper async loading
        # This uses threading + async polling to keep TUI responsive
        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write("DEBUG: on_mount() - before run_worker(initialize_moshi)\n")
            f.flush()
        self.run_worker(self.initialize_moshi(), exclusive=True, group="moshi_init")
        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write("DEBUG: on_mount() - after run_worker(initialize_moshi)\n")
            f.flush()


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

    def populate_theme_selector(self):
        """Populate persona selector with available personas"""
        try:
            radio_set = self.query_one("#theme-selector", RadioSet)
            # Get personas with theme colors
            themed_personas = [p for p in self.available_personas if p.theme and p.theme.theme_color]
            # Add radio button for each persona
            for persona in themed_personas:
                radio_btn = RadioButton(persona.name)
                radio_btn.id = f"theme-{persona.name.lower().replace(' ', '-')}"
                # Note: RadioButton.value is a boolean (pressed state), not for custom data
                # We use label (persona.name) to identify which persona was selected
                radio_set.mount(radio_btn)
            # Log how many personas we loaded
            self.update_activity(f"Loaded {len(themed_personas)} personas")
        except Exception as e:
            self.update_activity(f"Error populating personas: {e}")


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
            # Update button styles - remove active-tab from ALL buttons first
            all_tab_buttons = self.query(".tab-button")
            for button in all_tab_buttons:
                button.remove_class("active-tab")

            # Then add active-tab to the selected button
            try:
                active_button = self.query_one(f"#tab-{new_tab}", Button)
                active_button.add_class("active-tab")
                # Update focused index to match active tab for keyboard navigation
                button_id = f"tab-{new_tab}"
                if button_id in self._nav_buttons:
                    self._focused_nav_index = self._nav_buttons.index(button_id)
            except Exception:
                pass  # Button not found

            # Update content pane visibility - hide all first
            all_panes = self.query(".content-pane")
            for pane in all_panes:
                pane.remove_class("active-pane")

            # Then show the active pane
            try:
                active_pane = self.query_one(f"#content-{new_tab}", Container)
                active_pane.add_class("active-pane")
            except Exception:
                pass  # Pane not found
        except Exception:
            pass  # Widgets not ready yet

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle persona selection change"""
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
            # Update persona name inside visualizer (rendered above divider line)
            try:
                viz_panel = self.query_one("#visualizer", VoiceVisualizerPanel)
                viz_panel.persona_name = persona.name
            except Exception:
                pass
            # Keep visualizer title as static "xSwarm Assistant" (don't change it)

    def on_unmount(self) -> None:
        """Cleanup on exit"""
        # Stop audio streams
        if self.audio_io:
            self.audio_io.stop()
            try:
                self.update_activity("Audio streams stopped")
            except:
                pass  # Widget already removed during shutdown

        # Close memory manager (create task to run async close)
        if self.memory_manager:
            asyncio.create_task(self.memory_manager.close())

    async def initialize_memory(self):
        """Initialize memory manager for conversation history"""
        try:
            self.memory_manager = MemoryManager(
                server_url=self.config.server_url if hasattr(self.config, 'server_url') else "http://localhost:3000",
                max_history=100
            )
            await self.memory_manager.initialize()
            self.update_activity("✅ Memory system initialized")
        except Exception as e:
            self.update_activity(f"⚠️  Memory init failed: {e}, using chat history only")
            self.memory_manager = None

    async def initialize_voice(self) -> bool:
        """
        Initialize voice bridge (load Moshi models and connect to orchestrator).

        Returns:
            True if initialization successful, False otherwise
        """
        if self.voice_initialized:
            return True

        try:
            self.update_activity("Initializing voice bridge...")
            # Ensure memory manager is initialized first
            if not self.memory_manager:
                await self.initialize_memory()

            # Create voice bridge with persona and memory managers
            moshi_quality = getattr(self.config, 'moshi_quality', 'auto')
            self.voice_bridge = VoiceBridgeOrchestrator(
                persona_manager=self.persona_manager,
                memory_manager=self.memory_manager,
                config=self.config,
                user_id=self.user_id,
                moshi_quality=moshi_quality
            )
            # Initialize Moshi models
            await self.voice_bridge.initialize()
            # Register state change callback
            self.voice_bridge.on_state_change(self._on_voice_state_change)
            # Mark as initialized
            self.voice_initialized = True
            self.update_activity("✅ Voice bridge initialized successfully")

            # DON'T set baseline amplitude here - let it stay at 0.0 until actually speaking
            # The greeting generation below will set the amplitude when audio is played

            # Set connection_amplitude to idle (breathing) after voice is ready
            try:
                visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                visualizer.connection_amplitude = 1  # Idle/breathing
                # Set callback so widget can pull data from app during its own animation timer
                visualizer.data_callback = self.get_visualizer_data
            except Exception:
                pass

            # NO app timer needed - widget pulls data during its own 20 FPS animation timer
            # This eliminates dual-timer race condition that caused freezes

            # Auto-start conversation for microphone visualization and greeting
            await self.voice_bridge.start_conversation()
            self.update_activity("🎙️  Microphone active - speak naturally, I'm listening...")

            # Generate and play startup greeting
            await self.generate_greeting_with_voice_bridge()

            return True
        except Exception as e:
            self.update_activity(f"❌ Voice initialization failed: {e}")
            self.voice_initialized = False
            return False

    async def initialize_moshi(self):
        """Load voice models and initialize audio"""
        try:
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: initialize_moshi() called\n")
                f.flush()
            self.update_activity("Initializing voice models...")
            device = self.config.detect_device()
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write(f"DEBUG: Device detected: {device}\n")
                f.flush()


            # Initialize MOSHI bridge (MLX for Apple Silicon)
            from ..voice.moshi_mlx import MoshiBridge
            from ..voice.audio_io import AudioIO
            import asyncio
            import threading

            # Show loading progress with animation
            moshi_quality = getattr(self.config, 'moshi_quality', 'q4')
            self.update_activity(f"Loading MOSHI MLX models ({moshi_quality}, ~30-60s on M1/M2/M3)...")

            # Load Moshi in background thread to allow progress updates
            moshi_bridge_result = [None]  # List to store result from thread

            def moshi_thread_main():
                """
                Dedicated Moshi thread - loads model then processes frames.
                This thread owns ALL MLX operations (loading + processing).
                """
                with open("/tmp/xswarm_debug.log", "a") as f:
                    f.write("DEBUG: Moshi thread started - loading model\n")
                    f.flush()

                # PHASE 1: Load model
                try:
                    with open("/tmp/xswarm_debug.log", "a") as f:
                        f.write(f"DEBUG: Starting MoshiBridge({moshi_quality})...\n")
                        f.flush()
                    moshi_bridge_result[0] = MoshiBridge(quality=moshi_quality)
                    with open("/tmp/xswarm_debug.log", "a") as f:
                        f.write("DEBUG: MoshiBridge loaded successfully\n")
                        f.flush()
                except Exception as e:
                    with open("/tmp/xswarm_debug.log", "a") as f:
                        f.write(f"DEBUG: MoshiBridge failed: {e}\n")
                        import traceback
                        f.write(traceback.format_exc())
                        f.flush()
                    moshi_bridge_result[0] = e
                    return  # Exit thread on load failure

                # PHASE 2: Process frames (after model loads)
                # Wait for signal that processing should start
                import time
                while not hasattr(self, '_moshi_thread_ready'):
                    time.sleep(0.1)

                with open("/tmp/xswarm_debug.log", "a") as f:
                    f.write("DEBUG: Moshi thread entering processing loop\n")
                    f.flush()

                # Processing loop (runs until app closes)
                self._moshi_processing_thread()

            # Start dedicated Moshi thread (NOT daemon - we need it to stay alive)
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Starting Moshi thread\n")
                f.flush()
            loading_thread = threading.Thread(target=moshi_thread_main, daemon=False, name="MoshiMain")
            loading_thread.start()
            self._moshi_thread = loading_thread
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Moshi thread started\n")
                f.flush()


            # Use set_interval for non-blocking progress updates
            progress_counter = 0
            progress_message_added = False

            def update_progress_tick():
                """Update loading progress on each timer tick"""
                nonlocal progress_counter, progress_message_added
                elapsed_seconds = progress_counter // 10
                dots = "." * ((progress_counter // 5) % 4)
                spaces = " " * (3 - ((progress_counter // 5) % 4))
                bar_chars = "▁▂▃▄▅▆▇█"
                bar_idx = (progress_counter // 3) % len(bar_chars)

                progress_msg = (
                    f"{bar_chars[bar_idx]} Loading MOSHI MLX models ({moshi_quality}){dots}{spaces} "
                    f"{elapsed_seconds}s elapsed - please wait..."
                )

                # First tick: add message, subsequent ticks: update it
                activity = self.query_one("#activity", ActivityFeed)
                if not progress_message_added:
                    activity.add_message(progress_msg)
                    progress_message_added = True
                else:
                    activity.update_last_message(progress_msg)

                progress_counter += 1

            # Start repeating timer for progress updates (every 100ms)
            progress_timer = self.set_interval(0.1, update_progress_tick)

            # Wait for loading thread to complete using async polling
            while loading_thread.is_alive():
                await asyncio.sleep(0.1)

            # Stop progress timer
            progress_timer.stop()

            # Check result
            if isinstance(moshi_bridge_result[0], Exception):
                error = moshi_bridge_result[0]
                self.update_activity(f"❌ ERROR loading Moshi: {error}")
                import traceback
                traceback.print_exc()
                raise error

            self.moshi_bridge = moshi_bridge_result[0]
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Moshi bridge assigned successfully\n")
                f.flush()
            self.update_activity("✓ MOSHI MLX models loaded")

            # Create LM generator for full-duplex streaming
            self.lm_generator = self.moshi_bridge.create_lm_generator(max_steps=1000)
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: LM generator created\n")
                f.flush()
            self.update_activity("✓ Full-duplex stream ready")

            # Initialize audio I/O
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: About to create AudioIO\n")
                f.flush()
            self.update_activity("Starting audio streams...")
            self.audio_io = AudioIO(
                sample_rate=24000,
                frame_size=1920,
                channels=1
            )
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: AudioIO created\n")
                f.flush()

            # Start audio input with callback for full-duplex Moshi processing
            self._audio_callback_counter = 0  # For debug logging
            self._mic_amplitude_queue = []  # Queue for thread-safe amplitude updates
            self._smoothed_amplitude = 0.0  # Smoothed amplitude to prevent jitter
            self._moshi_input_queue = []  # Queue for incoming audio frames to process
            self._moshi_output_queue = []  # Queue for Moshi output audio chunks

            def audio_callback(audio):
                """
                Audio callback runs in separate thread - ONLY queue data, NO processing.
                MLX operations are NOT thread-safe and will cause segfaults if called here.
                Processing happens in moshi_processing_loop() on the main async event loop.
                """
                # Update mic amplitude for bottom waveform visualizer
                self.moshi_bridge.update_mic_amplitude(audio)
                raw_amplitude = self.moshi_bridge.mic_amplitude

                # Boost mic amplitude by 3x for better low-level visibility
                boosted_amplitude = min(raw_amplitude * 3.0, 1.0)  # Cap at 1.0

                # Apply exponential smoothing to prevent jitter
                # Higher alpha = more responsive but jittery, lower alpha = smoother but laggy
                alpha = 0.3  # Balance between responsiveness and smoothness
                self._smoothed_amplitude = alpha * boosted_amplitude + (1 - alpha) * self._smoothed_amplitude

                self._audio_callback_counter += 1

                # Queue smoothed amplitude for main thread to process
                self._mic_amplitude_queue.append(self._smoothed_amplitude)
                # Keep queue small to avoid memory buildup
                if len(self._mic_amplitude_queue) > 100:
                    self._mic_amplitude_queue.pop(0)

                # CRITICAL: Only queue audio, do NOT call step_frame() here
                # MLX GPU operations must run on main thread to avoid segfaults
                self._moshi_input_queue.append(audio.copy())  # Copy to avoid data race
                # Keep queue small to avoid latency buildup
                if len(self._moshi_input_queue) > 10:
                    self._moshi_input_queue.pop(0)  # Drop oldest frame if queue backs up

            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Starting audio input\n")
                f.flush()
            self.audio_io.start_input(callback=audio_callback)
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Starting audio output\n")
                f.flush()
            self.audio_io.start_output()
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Audio started successfully\n")
                f.flush()

            # Signal Moshi thread to start processing (it's been waiting after model load)
            self._processing_thread_stop = threading.Event()
            self._moshi_thread_ready = True  # Signal to start processing loop

            # Playback loop: consumes output queue, plays audio to speakers
            self.run_worker(self.moshi_playback_loop(), exclusive=False, group="moshi_playback")

            self.update_activity("🎙️  Microphone active - speak naturally, I'm listening...")

            # Set voice as initialized so visualizer can show mic input
            self.voice_initialized = True
            with open("/tmp/xswarm_debug.log", "a") as f:
                f.write("DEBUG: Voice initialized = True\n")
                f.flush()

            # Set connection_amplitude to idle (breathing) after voice is ready
            try:
                visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                visualizer.connection_amplitude = 1  # Idle/breathing
                # Set callback so widget can pull data from app during its own animation timer
                visualizer.data_callback = self.get_visualizer_data
            except Exception:
                pass

            # Generate greeting immediately
            self.state = "ready"
            self.update_activity(f"✓ Voice assistant ready on {device}")
            await self.generate_greeting()

        except Exception as e:
            self.update_activity(f"Error loading voice models: {e}")
            self.state = "error"
            # Don't overwrite visualizer title - keep the default persona name that was set in on_mount()

    async def generate_greeting(self, re_introduction: bool = False):
        """
        Generate and play automatic greeting on startup or after theme change.

        Args:
            re_introduction: If True, introduce with new persona after theme change
        """
        import numpy as np

        try:
            self.state = "speaking"
            self.update_activity("👋 Generating greeting...")

            # Get current persona (use reactive property, falls back to config)
            persona_name = self.current_persona_name if self.current_persona_name != "Default" else (self.config.default_persona or "JARVIS")
            persona = self.persona_manager.get_persona(persona_name)

            # Create greeting prompt with tool context
            if re_introduction:
                # Re-introduction after theme change
                greeting_prompt = f"You just changed your persona to {persona_name}. Introduce yourself in character with your new personality. Be enthusiastic about the change!"
            else:
                # Initial startup greeting
                greeting_prompt = f"You are {persona_name}. Greet the user warmly and introduce yourself in character."

            # Add persona system prompt for context
            if persona and persona.system_prompt:
                greeting_prompt = persona.system_prompt + "\n\n" + greeting_prompt

            # Add tool descriptions so Moshi knows what it can do
            tool_descriptions = self.tool_registry.get_tool_descriptions()
            greeting_prompt += f"\n\n{tool_descriptions}"

            # Generate silent audio input (MOSHI needs input audio)
            silent_audio = np.zeros(1920, dtype=np.float32)

            # Generate greeting through MOSHI
            response_audio, response_text = self.moshi_bridge.generate_response(
                silent_audio,
                text_prompt=greeting_prompt,
                max_frames=50  # Shorter greeting (~4 seconds at 12.5 Hz)
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

    async def generate_greeting_with_voice_bridge(self):
        """
        Generate and play startup greeting using VoiceBridgeOrchestrator.

        This is called after initialize_voice() completes to introduce the assistant.
        """
        import numpy as np

        try:
            self.state = "speaking"
            self.update_activity("👋 Generating startup greeting...")

            # Get current persona name
            persona_name = self.current_persona_name if self.current_persona_name != "Default" else (self.config.default_persona or "JARVIS")

            # Create greeting text prompt
            greeting_text = f"You are {persona_name}. Greet the user warmly and introduce yourself in character in 1-2 sentences."

            # Use voice bridge's generate_response method for text input
            # This will create audio through Moshi
            result = await self.voice_bridge.generate_response(greeting_text)

            if result and result.get("response_text"):
                self.update_activity(f"💬 {result['response_text']}")
                self.add_chat_message("assistant", result['response_text'])

            self.state = "idle"
            self.update_activity("✓ Ready - listening for your voice...")

        except Exception as e:
            self.update_activity(f"Error generating greeting: {e}")
            self.state = "idle"

    def _moshi_processing_thread(self):
        """
        Dedicated thread for Moshi processing. Runs independently of:
        - Audio callback thread (avoids segfaults)
        - Async event loop (avoids blocking UI)

        This is the ONLY thread that calls MLX operations (thread-safe design).
        Consumes from _moshi_input_queue, produces to _moshi_output_queue.
        """
        import time

        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write("DEBUG: Moshi processing thread started\n")
            f.flush()

        while not self._processing_thread_stop.is_set():
            try:
                # Check if there's audio to process
                if len(self._moshi_input_queue) > 0:
                    # Get next audio frame
                    audio_frame = self._moshi_input_queue.pop(0)

                    # Process through Moshi (MLX operations safe in this dedicated thread)
                    audio_chunk, text_piece = self.moshi_bridge.step_frame(self.lm_generator, audio_frame)

                    # Queue output audio for playback
                    if audio_chunk is not None and len(audio_chunk) > 0:
                        self._moshi_output_queue.append(audio_chunk)
                        # Update Moshi amplitude for visualization
                        self.moshi_bridge.update_moshi_amplitude(audio_chunk)

                    # Log text output (for debugging)
                    if text_piece and text_piece.strip():
                        with open("/tmp/moshi_text.log", "a") as f:
                            f.write(text_piece)
                            f.flush()

                    # No sleep needed - processing naturally takes time
                else:
                    # No frames to process, sleep briefly
                    time.sleep(0.001)  # 1ms when idle

            except Exception as e:
                # Log errors but keep thread running
                with open("/tmp/xswarm_debug.log", "a") as f:
                    f.write(f"ERROR in moshi_processing_thread: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
                    f.flush()
                time.sleep(0.1)

    async def moshi_playback_loop(self):
        """Continuous loop to play Moshi output audio from queue"""
        import asyncio
        import numpy as np

        while True:
            try:
                # Check if there's audio in the queue
                if len(self._moshi_output_queue) > 0:
                    # Get next chunk
                    audio_chunk = self._moshi_output_queue.pop(0)

                    # Play it
                    self.audio_io.play_audio(audio_chunk)

                    # Update visualizer to show Moshi is speaking
                    try:
                        visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                        visualizer.connection_amplitude = 2  # Speaking
                    except Exception:
                        pass

                    # Small delay to prevent tight loop
                    await asyncio.sleep(0.01)
                else:
                    # No audio, idle state
                    try:
                        visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                        if visualizer.connection_amplitude == 2:
                            visualizer.connection_amplitude = 1  # Idle/breathing
                    except Exception:
                        pass

                    # Longer delay when idle to save CPU
                    await asyncio.sleep(0.05)

            except Exception as e:
                # Log errors but keep loop running
                with open("/tmp/xswarm_debug.log", "a") as f:
                    f.write(f"ERROR in moshi_playback_loop: {e}\n")
                    f.flush()
                await asyncio.sleep(0.1)

    async def play_audio_with_visualization(self, audio: "np.ndarray"):
        """Play audio and update visualizer amplitude during playback"""
        import numpy as np

        # Calculate frame size for chunking
        frame_size = 1920  # 80ms at 24kHz
        num_frames = len(audio) // frame_size

        # Queue audio for playback
        self.audio_io.play_audio(audio)

        # Update connection_amplitude for top circle visualizer during playback
        visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
        for i in range(num_frames):
            frame = audio[i * frame_size:(i + 1) * frame_size]
            self.moshi_bridge.update_moshi_amplitude(frame)
            amplitude = self.moshi_bridge.moshi_amplitude

            # Update top circle with Moshi output amplitude (map 0-1 to 2-100)
            visualizer.connection_amplitude = int(amplitude * 98) + 2
            await asyncio.sleep(0.08)  # 80ms per frame

        # Reset to idle (breathing) after playback
        visualizer.connection_amplitude = 1

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

        # Update persona name inside visualizer (rendered above divider line)
        try:
            viz_panel = self.query_one("#visualizer", VoiceVisualizerPanel)
            viz_panel.persona_name = persona.name
        except Exception:
            pass
        # Keep visualizer title as static "xSwarm Assistant" (don't change it)

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

    def get_visualizer_data(self):
        """
        Get current visualizer data for the widget to consume.
        Called by the widget's animation timer (20 FPS) - NO app timer needed.

        Returns:
            Dict with mic_amplitude, connection_amplitude
        """
        try:
            # Use voice bridge amplitudes if available
            if self.voice_initialized and self.voice_bridge:
                amplitudes = self.voice_bridge.get_amplitudes()
                mic_amp = amplitudes.get("mic_amplitude", 0.0)
                moshi_amp = amplitudes.get("moshi_amplitude", 0.0)

                # Apply minimal baseline to mic_amp to show microphone is active
                if self.state == "idle" or self.state == "ready":
                    mic_amp = max(mic_amp, 0.05)

                # Determine connection_amplitude based on voice state
                if moshi_amp > 0.02:
                    # Speaking - map amplitude to 2-100 range
                    connection_amp = int(moshi_amp * 98) + 2
                else:
                    # Idle - breathing animation
                    connection_amp = 1

                return {
                    "mic_amplitude": mic_amp,
                    "connection_amplitude": connection_amp
                }

            # Fallback to legacy audio callback method
            elif hasattr(self, '_mic_amplitude_queue') and self._mic_amplitude_queue:
                # Process queued amplitudes with iteration limit
                MAX_SAMPLES_PER_UPDATE = 10
                samples_processed = 0
                mic_samples = []

                while self._mic_amplitude_queue and samples_processed < MAX_SAMPLES_PER_UPDATE:
                    amplitude = self._mic_amplitude_queue.pop(0)

                    # Apply minimal baseline when idle
                    if self.state == "idle" or self.state == "ready":
                        amplitude = max(amplitude, 0.05)

                    mic_samples.append(amplitude)
                    samples_processed += 1

                # Drain excess samples if queue is too full
                if len(self._mic_amplitude_queue) > 100:
                    self._mic_amplitude_queue = self._mic_amplitude_queue[-50:]

                # Return average amplitude and idle connection
                avg_mic = sum(mic_samples) / len(mic_samples) if mic_samples else 0.0
                return {
                    "mic_amplitude": avg_mic,
                    "mic_samples": mic_samples,  # For batch processing
                    "connection_amplitude": 1  # Idle
                }

        except Exception as e:
            # Log exception to help debug issues
            self.update_activity(f"Visualizer data error: {e}")

        # Fallback: return zero data
        return {
            "mic_amplitude": 0.0,
            "connection_amplitude": 0
        }

    def _on_voice_state_change(self, new_state: ConversationState):
        """
        Callback when voice bridge state changes.

        Args:
            new_state: New conversation state
        """
        # Map ConversationState to app state string
        state_map = {
            ConversationState.IDLE: "idle",
            ConversationState.LISTENING: "listening",
            ConversationState.THINKING: "thinking",
            ConversationState.SPEAKING: "speaking",
            ConversationState.ERROR: "error"
        }
        # Update app state (reactive property)
        self.state = state_map.get(new_state, "idle")
        # Log state change to activity feed (only if app is mounted)
        try:
            state_emojis = {
                ConversationState.IDLE: "⚪",
                ConversationState.LISTENING: "🎤",
                ConversationState.THINKING: "🤔",
                ConversationState.SPEAKING: "🗣️",
                ConversationState.ERROR: "❌"
            }
            emoji = state_emojis.get(new_state, "⚪")
            self.update_activity(f"{emoji} Voice state: {new_state.value}")
        except Exception:
            pass  # App not mounted yet, skip activity feed update

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

        # Store in memory manager (if available)
        if self.memory_manager:
            # Get current persona name for metadata
            persona_name = self.config.default_persona or "JARVIS"
            metadata = {"persona": persona_name} if role == "assistant" else {}

            asyncio.create_task(
                self.memory_manager.store_message(
                    user_id=self.user_id,
                    message=message,
                    role=role,
                    metadata=metadata
                )
            )

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

    def _navigate_nav_menu(self, direction: int) -> None:
        """Navigate nav menu with keyboard (direction: -1 for up, 1 for down)"""
        try:
            # Update focused index with wraparound
            self._focused_nav_index = (self._focused_nav_index + direction) % len(self._nav_buttons)
            # Get the button to focus
            button_id = self._nav_buttons[self._focused_nav_index]
            button = self.query_one(f"#{button_id}", Button)
            # Set focus to the button
            button.focus()
        except Exception:
            pass  # Button not found or not ready

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard input"""
        # Arrow key navigation for nav menu
        if event.key in ("up", "k"):
            self._navigate_nav_menu(-1)
            event.prevent_default()
        elif event.key in ("down", "j"):
            self._navigate_nav_menu(1)
            event.prevent_default()
        elif event.key == "enter":
            # Enter key: Activate the currently focused nav button
            if self._focused_nav_index >= 0 and self._focused_nav_index < len(self._nav_buttons):
                button_id = self._nav_buttons[self._focused_nav_index]
                tab_name = button_id.replace("tab-", "")
                self.active_tab = tab_name
                event.prevent_default()
        elif event.key == "space":
            # Space key: Check if a nav button has focus
            # If nav button is focused AND not the active tab, switch to it
            # Otherwise, use space for voice toggle (via VoiceBridge)
            if self._focused_nav_index >= 0 and self._focused_nav_index < len(self._nav_buttons):
                button_id = self._nav_buttons[self._focused_nav_index]
                tab_name = button_id.replace("tab-", "")
                if tab_name != self.active_tab:
                    # Nav button focused but not active - switch to it
                    self.active_tab = tab_name
                    event.prevent_default()
                else:
                    # Nav button focused AND active - use space for voice (VoiceBridge)
                    self.action_toggle_voice()
                    event.prevent_default()
            else:
                # No nav button focused - use space for voice (VoiceBridge)
                self.action_toggle_voice()
                event.prevent_default()
        elif event.key == "q":
            self.exit()
        elif event.key == "s":
            # Open settings
            self.action_open_settings()
        elif event.key == "v":
            # Open voice visualizer demo
            self.action_open_viz_demo()
        elif event.key == "ctrl+c":
            # Copy recent activity to clipboard
            self.action_copy_activity()
        elif event.key == "ctrl+v":
            # Toggle voice conversation on/off
            self.action_toggle_voice()

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

    def action_toggle_voice(self):
        """Toggle voice conversation on/off (Ctrl+V keybinding)"""
        # Initialize voice if not already done
        if not self.voice_initialized:
            self.run_worker(self.initialize_voice)
            return
        # Toggle conversation state
        if self.voice_bridge.get_conversation_state() == ConversationState.IDLE:
            self.run_worker(self._start_voice)
        else:
            self.run_worker(self._stop_voice)

    async def _start_voice(self):
        """Start voice conversation (worker method)"""
        try:
            await self.voice_bridge.start_conversation()
            self.update_activity("🎙️  Voice conversation started (Ctrl+V to stop)")
        except Exception as e:
            self.update_activity(f"❌ Failed to start voice: {e}")

    async def _stop_voice(self):
        """Stop voice conversation (worker method)"""
        try:
            await self.voice_bridge.stop_conversation()
            self.update_activity("🛑 Voice conversation stopped")
        except Exception as e:
            self.update_activity(f"❌ Failed to stop voice: {e}")

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
        """Process captured audio through MOSHI with tool calling support"""
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
            persona_name = self.current_persona_name if self.current_persona_name != "Default" else (self.config.default_persona or "JARVIS")
            persona = self.persona_manager.get_persona(persona_name)

            # Build comprehensive prompt with persona, memory, and tools
            text_prompt = await self._build_conversation_prompt(persona)

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

            # Check for tool calls in response
            tool_call = self.tool_registry.parse_tool_call(response_text) if response_text else None

            if tool_call:
                # Execute tool call
                self.update_activity(f"🔧 Executing tool: {tool_call.get('name', 'unknown')}")
                tool_result = await self.tool_registry.execute_tool(
                    tool_call.get("name", ""),
                    tool_call.get("arguments", {})
                )

                if tool_result["success"]:
                    self.update_activity(f"✓ Tool executed: {tool_result['result']}")
                    # Note: generate_greeting will handle re-introduction for theme changes
                else:
                    self.update_activity(f"❌ Tool failed: {tool_result['error']}")

            # Play response audio with visualization
            await self.play_audio_with_visualization(response_audio)
            self.update_activity("✓ Response complete")

            self.state = "ready"

        except Exception as e:
            self.update_activity(f"Error processing audio: {e}")
            self.state = "error"

    async def _build_conversation_prompt(self, persona) -> str:
        """
        Build comprehensive prompt with persona, memory, and tools.

        Args:
            persona: Current persona object

        Returns:
            Complete prompt string for Moshi
        """
        prompt_parts = []

        # 1. Persona identity
        persona_name = persona.name if persona else "Assistant"
        prompt_parts.append(f"You are {persona_name}.")

        # 2. Persona system prompt (character/personality)
        if persona and persona.system_prompt:
            prompt_parts.append(persona.system_prompt)

        # 3. Conversation history from memory (if available)
        if self.memory_manager:
            try:
                history = await self.memory_manager.get_conversation_history(self.user_id, limit=10)
                if history:
                    prompt_parts.append("\nRecent conversation history:")
                    prompt_parts.append(history)
            except Exception as e:
                # Memory retrieval failed, continue without history
                self.update_activity(f"⚠️ Could not retrieve history: {e}")

        # 4. Tool descriptions
        tool_descriptions = self.tool_registry.get_tool_descriptions()
        if tool_descriptions and tool_descriptions != "No tools available.":
            prompt_parts.append("\n" + tool_descriptions)
            prompt_parts.append("\nTo use a tool, respond with: TOOL_CALL: {\"name\": \"tool_name\", \"arguments\": {...}}")

        return "\n\n".join(prompt_parts)

    def action_quit(self):
        """Quit the application (triggered by q/ctrl+q/ctrl+c keybindings)"""
        self.exit()

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
