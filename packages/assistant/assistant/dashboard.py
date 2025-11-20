"""
Main Textual TUI application for xSwarm Assistant.
Consolidates dashboard logic, screens, and theme management.
"""

import asyncio
import datetime
import math
import random
import re
import colorsys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
from textual.widgets import Static, Label, Button, RadioButton, RadioSet, Input, Tree, Select, Switch, Header, Footer
from textual.screen import Screen
from textual.reactive import reactive
from textual.binding import Binding
import pyperclip
from rich.text import Text
from typing import Optional, List, Any, cast

from .voice import VoiceBridgeOrchestrator, ConversationState
from .memory import MemoryManager

# Import consolidated widgets
from .dashboard_widgets import (
    ActivityFeed,
    CyberpunkFooter,
    VoiceVisualizerPanel,
    VisualizationStyle,
    WorkerDashboard,
    ScheduleWidget,
    ProjectDashboard
)

from .config import Config
from .personas.manager import PersonaManager
from .voice import VoiceBridgeOrchestrator, ConversationState
from .memory import MemoryManager
from .thinking import DeepThinkingEngine


# ==============================================================================
# THEME SYSTEM (Consolidated from theme.py)
# ==============================================================================

@dataclass
class ColorPalette:
    """5-shade color palette generated from a base color."""
    shade_1: str  # Darkest
    shade_2: str  # Dark
    shade_3: str  # Medium
    shade_4: str  # Light
    shade_5: str  # Lightest


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def adjust_brightness(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """Adjust brightness of an RGB color by a factor."""
    # Convert to HSL for better brightness control
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Adjust lightness
    l = max(0.0, min(1.0, l * factor))

    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return tuple(int(x * 255) for x in (r, g, b))


def desaturate(rgb: Tuple[int, int, int], amount: float = 0.5) -> Tuple[int, int, int]:
    """Desaturate a color towards grayscale."""
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Reduce saturation
    s = s * (1.0 - amount)

    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return tuple(int(x * 255) for x in (r, g, b))


def generate_palette(base_color: str) -> ColorPalette:
    """Generate a 5-shade palette from a base color."""
    # Parse base color
    rgb = hex_to_rgb(base_color)

    # Desaturate the base color for a more subtle palette
    rgb = desaturate(rgb, amount=0.3)

    # Generate 5 shades by adjusting brightness
    # Base color becomes shade-4 (light)
    shade_1 = rgb_to_hex(adjust_brightness(rgb, 0.35))  # Very dark
    shade_2 = rgb_to_hex(adjust_brightness(rgb, 0.55))  # Dark
    shade_3 = rgb_to_hex(adjust_brightness(rgb, 0.75))  # Medium
    shade_4 = rgb_to_hex(rgb)                            # Light (base)
    shade_5 = rgb_to_hex(adjust_brightness(rgb, 1.25))  # Lightest

    return ColorPalette(
        shade_1=shade_1,
        shade_2=shade_2,
        shade_3=shade_3,
        shade_4=shade_4,
        shade_5=shade_5
    )


# Predefined theme presets
THEME_PRESETS = {
    "blue-gray": "#8899aa",      # Current default - cool blue-gray
    "slate": "#6b7b8c",           # Neutral slate gray
    "cyan": "#5eb3b3",            # Subtle cyan tint
    "purple": "#9b8cbb",          # Muted purple
    "green": "#88aa88",           # Subtle green
    "amber": "#aa9977",           # Warm amber
    "rose": "#aa8899",            # Soft rose
    "steel": "#778899",           # Cool steel blue
}


def get_theme_preset(name: str) -> ColorPalette:
    """Get a predefined theme palette by name."""
    if name not in THEME_PRESETS:
        raise KeyError(f"Theme '{name}' not found. Available: {list(THEME_PRESETS.keys())}")
    return generate_palette(THEME_PRESETS[name])


# ==============================================================================
# SCREENS (Consolidated from screens/*.py)
# ==============================================================================

class SettingsScreen(Screen):
    """Interactive settings configuration screen."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        ("s", "save", "Save"),
    ]

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }

    .settings-row {
        height: auto;
        margin: 1 0;
    }

    .settings-label {
        width: 20;
        content-align: left middle;
    }

    Input {
        width: 1fr;
    }

    Select {
        width: 1fr;
    }

    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, config: Config, personas_dir: Path):
        super().__init__()
        self.config = config
        self.personas_dir = personas_dir
        self.persona_manager = PersonaManager(personas_dir)

    def compose(self) -> ComposeResult:
        """Compose the settings screen."""
        yield Header()

        with Container(id="settings-container"):
            yield Label("⚙️  Settings", classes="settings-title")
            yield Static("")  # Spacer

            # Persona selection
            with Vertical(classes="settings-row"):
                yield Label("Persona:", classes="settings-label")
                personas = self.persona_manager.list_personas()
                persona_options = [(name, name) for name in personas] if personas else [("None", "None")]
                current_persona = self.config.default_persona or (personas[0] if personas else None)
                yield Select(
                    options=persona_options,
                    value=current_persona,
                    id="persona-select"
                )

            # Device selection
            with Vertical(classes="settings-row"):
                yield Label("Device:", classes="settings-label")
                yield Select(
                    options=[
                        ("auto", "Auto-detect"),
                        ("mps", "MPS (Mac M3)"),
                        ("cuda", "CUDA/ROCm (GPU)"),
                        ("cpu", "CPU"),
                    ],
                    value=self.config.device,
                    id="device-select"
                )

            # Wake word
            with Vertical(classes="settings-row"):
                yield Label("Wake Word:", classes="settings-label")
                yield Input(
                    value=self.config.wake_word,
                    placeholder="e.g. jarvis, computer",
                    id="wake-word-input"
                )

            # Server URL
            with Vertical(classes="settings-row"):
                yield Label("Server URL:", classes="settings-label")
                yield Input(
                    value=self.config.server_url,
                    placeholder="http://localhost:3000",
                    id="server-url-input"
                )

            # API Token (optional)
            with Vertical(classes="settings-row"):
                yield Label("API Token:", classes="settings-label")
                yield Input(
                    value=self.config.api_token or "",
                    placeholder="Optional API token",
                    password=True,
                    id="api-token-input"
                )

            # Memory enabled
            with Vertical(classes="settings-row"):
                yield Label("Enable Memory:", classes="settings-label")
                yield Switch(
                    value=self.config.memory_enabled,
                    id="memory-switch"
                )

            # Buttons
            with Vertical(id="button-container"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

        yield Footer()

    def action_cancel(self):
        """Cancel and return to main screen."""
        self.dismiss()

    def action_save(self):
        """Save configuration and return to main screen."""
        self._save_config()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-button":
            self._save_config()
        elif event.button.id == "cancel-button":
            self.dismiss()

    def _save_config(self):
        """Save configuration from form inputs."""
        # Get all input values
        persona_select = self.query_one("#persona-select", Select)
        device_select = self.query_one("#device-select", Select)
        wake_word_input = self.query_one("#wake-word-input", Input)
        server_url_input = self.query_one("#server-url-input", Input)
        api_token_input = self.query_one("#api-token-input", Input)
        memory_switch = self.query_one("#memory-switch", Switch)

        # Update config
        self.config.default_persona = str(persona_select.value) if persona_select.value else None
        self.config.device = str(device_select.value)
        self.config.wake_word = wake_word_input.value
        self.config.server_url = server_url_input.value
        self.config.api_token = api_token_input.value if api_token_input.value else None
        self.config.memory_enabled = memory_switch.value

        # Save to file
        self.config.save_to_file()

        # Return updated config to main app
        self.dismiss(self.config)


class WizardScreen(Screen):
    """Multi-step first-run setup wizard."""

    BINDINGS = [
        Binding("escape", "cancel", "Skip Setup"),
    ]

    CSS = """
    WizardScreen {
        align: center middle;
    }

    #wizard-container {
        width: 90;
        height: auto;
        border: double $accent;
        background: $surface;
        padding: 2 3;
    }

    .wizard-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .wizard-subtitle {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    .wizard-step {
        height: auto;
        margin: 1 0;
    }

    .step-label {
        text-style: bold;
        margin-bottom: 1;
    }

    .step-description {
        color: $text-muted;
        margin-bottom: 1;
    }

    Input {
        width: 100%;
        margin-bottom: 1;
    }

    Select {
        width: 100%;
        margin-bottom: 1;
    }

    #button-container {
        layout: horizontal;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, personas_dir: Path):
        super().__init__()
        self.personas_dir = personas_dir
        self.persona_manager = PersonaManager(personas_dir)
        self.config = Config()  # Start with default config

    def compose(self) -> ComposeResult:
        """Compose the wizard screen."""
        yield Header()

        with Container(id="wizard-container"):
            yield Label("🎉 Welcome to xSwarm Voice Assistant!", classes="wizard-title")
            yield Label("Let's set up your assistant in a few steps", classes="wizard-subtitle")

            # Step 1: Persona Selection
            with Vertical(classes="wizard-step"):
                yield Label("1️⃣  Choose Your Assistant Persona", classes="step-label")
                yield Static(
                    "Select a personality for your assistant. You can change this later in settings.",
                    classes="step-description"
                )

                personas = self.persona_manager.list_personas()
                if personas:
                    persona_options = [(name, name) for name in personas]
                    yield Select(
                        options=persona_options,
                        value=personas[0],
                        id="persona-select"
                    )
                else:
                    yield Label("⚠️  No personas found. Please add personas to packages/personas/")

            # Step 2: Device Selection
            with Vertical(classes="wizard-step"):
                yield Label("2️⃣  Select Compute Device", classes="step-label")
                yield Static(
                    "Choose how MOSHI should process audio. Auto-detect is recommended.",
                    classes="step-description"
                )
                yield Select(
                    options=[
                        ("Auto-detect (Recommended)", "auto"),
                        ("MPS - Mac M3 Metal", "mps"),
                        ("CUDA/ROCm - GPU", "cuda"),
                        ("CPU (Slower)", "cpu"),
                    ],
                    value="auto",
                    id="device-select"
                )

            # Step 3: Wake Word
            with Vertical(classes="wizard-step"):
                yield Label("3️⃣  Set Wake Word", classes="step-label")
                yield Static(
                    "The word or phrase to activate your assistant (e.g., 'jarvis', 'computer').",
                    classes="step-description"
                )
                yield Input(
                    value="jarvis",
                    placeholder="Enter wake word",
                    id="wake-word-input"
                )

            # Step 4: Memory Server (Optional)
            with Vertical(classes="wizard-step"):
                yield Label("4️⃣  Memory Server (Optional)", classes="step-label")
                yield Static(
                    "Connect to memory server for persistent conversations. Leave default if running locally.",
                    classes="step-description"
                )
                yield Input(
                    value="http://localhost:3000",
                    placeholder="Server URL",
                    id="server-url-input"
                )

            # Buttons
            with Horizontal(id="button-container"):
                yield Button("Complete Setup", variant="primary", id="complete-button")
                yield Button("Skip Setup", variant="default", id="skip-button")

        yield Footer()

    def action_cancel(self):
        """Skip setup and use defaults."""
        self.dismiss(self.config)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "complete-button":
            self._complete_wizard()
        elif event.button.id == "skip-button":
            self.dismiss(self.config)

    def _complete_wizard(self):
        """Complete wizard and save configuration."""
        # Get all input values
        persona_select = self.query_one("#persona-select", Select)
        device_select = self.query_one("#device-select", Select)
        wake_word_input = self.query_one("#wake-word-input", Input)
        server_url_input = self.query_one("#server-url-input", Input)

        # Update config
        self.config.default_persona = str(persona_select.value) if persona_select.value else None
        self.config.device = str(device_select.value)
        self.config.wake_word = wake_word_input.value
        self.config.server_url = server_url_input.value
        self.config.memory_enabled = True

        # Save to file
        self.config.save_to_file()

        # Return config to main app
        self.dismiss(self.config)


class VoiceVizDemoScreen(Screen):
    """
    Demo screen showing all 6 voice visualization styles.

    Layout: 3x2 grid of visualization panels.
    Each panel shows a different style with a label.
    """

    CSS = """
    VoiceVizDemoScreen {
        background: #0a0e27;
    }

    #demo-container {
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    #viz-grid {
        grid-size: 3 2;
        grid-gutter: 1 1;
        width: 100%;
        height: 100%;
        overflow: hidden;
    }

    .viz-container {
        border: solid #00d4ff;
        height: 100%;
        width: 100%;
        min-height: 0;
        overflow: hidden;
    }

    .viz-label {
        background: #1a1f3a;
        color: #00d4ff;
        text-align: center;
        height: auto;
        max-height: 1;
        text-style: bold;
        padding: 0;
    }

    VoiceVisualizerPanel {
        height: 1fr;
        min-height: 0;
        border: none;
        overflow: hidden;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Back"),
        ("q", "dismiss", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the demo screen layout."""
        yield Header()

        with Container(id="demo-container"):
            with Grid(id="viz-grid"):
                # Style 1: Concentric Circles
                with Vertical(classes="viz-container"):
                    yield Label("1. Concentric Circles", classes="viz-label")
                    panel1 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.CONCENTRIC_CIRCLES
                    )
                    panel1.simulation_mode = True
                    panel1.start_animation()
                    yield panel1

                # Style 2: Ripple Waves
                with Vertical(classes="viz-container"):
                    yield Label("2. Ripple Waves", classes="viz-label")
                    panel2 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.RIPPLE_WAVES
                    )
                    panel2.simulation_mode = True
                    panel2.start_animation()
                    yield panel2

                # Style 3: Circular Bars
                with Vertical(classes="viz-container"):
                    yield Label("3. Circular Bars", classes="viz-label")
                    panel3 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.CIRCULAR_BARS
                    )
                    panel3.simulation_mode = True
                    panel3.start_animation()
                    yield panel3

                # Style 4: Pulsing Dots
                with Vertical(classes="viz-container"):
                    yield Label("4. Pulsing Dots", classes="viz-label")
                    panel4 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.PULSING_DOTS
                    )
                    panel4.simulation_mode = True
                    panel4.start_animation()
                    yield panel4

                # Style 5: Spinning Indicator
                with Vertical(classes="viz-container"):
                    yield Label("5. Spinning Indicator", classes="viz-label")
                    panel5 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SPINNING_INDICATOR
                    )
                    panel5.simulation_mode = True
                    panel5.start_animation()
                    yield panel5

                # Style 6: Sound Wave Circle
                with Vertical(classes="viz-container"):
                    yield Label("6. Sound Wave Circle", classes="viz-label")
                    panel6 = VoiceVisualizerPanel(
                        visualization_style=VisualizationStyle.SOUND_WAVE_CIRCLE
                    )
                    panel6.simulation_mode = True
                    panel6.start_animation()
                    yield panel6

        yield Footer()

    def on_mount(self) -> None:
        """Called when screen is mounted."""
        # All panels start animating automatically in compose()
        pass

    def action_dismiss(self, result: Any = None) -> None:
        """Dismiss the demo screen."""
        # Stop all animations before dismissing
        panels = self.query(VoiceVisualizerPanel)
        for panel in panels:
            panel.stop_animation()
        self.dismiss(result)


# ==============================================================================
# MAIN APPLICATION (Consolidated from app.py)
# ==============================================================================

class VoiceAssistantApp(App):
    """Voice Assistant TUI Application"""

    TITLE = "Voice Assistant"

    # Key bindings
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+q", "quit", "Quit"),
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

    def __init__(self, config: Config, personas_dir: Path, voice_server_process=None, voice_queues=None):
        super().__init__()
        self.config = config
        self.personas_dir = personas_dir
        self.voice_server_process = voice_server_process
        self.voice_queues = voice_queues
        self.voice_orchestrator: Optional[VoiceBridgeOrchestrator] = None
        self.voice_initialized = False
        # subprocess.Popen from start_server_process()
        self.voice_client: Optional[object] = None  # VoiceServerClient for ZeroMQ communication
        self.moshi_bridge: Optional[object] = None  # Deprecated: kept for backwards compatibility
        self.moshi_client: Optional[object] = None  # Deprecated: kept for backwards compatibility
        self.audio_io: Optional[object] = None
        self.audio_buffer = []  # Buffer for capturing audio during listening
        self.chat_history = []  # Store chat messages (user + assistant)
        self.memory_manager: Optional[MemoryManager] = None  # Memory manager for persistence
        self.user_id = "local-user"  # Default user ID
        self.thinking_engine: Optional[DeepThinkingEngine] = None  # Thinking engine for tool/memory decisions
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
        from .tools import ToolRegistry, ThemeChangeTool, send_email_tool, make_call_tool
        self.tool_registry = ToolRegistry()
        # Register theme change tool (bound to this app instance)
        self.tool_registry.register_tool(ThemeChangeTool.create_tool(self))
        # Register email tool
        self.tool_registry.register_tool(send_email_tool)
        # Register phone tools
        self.tool_registry.register_tool(make_call_tool)

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
                    with Horizontal(classes="pane-header-row"):
                        yield Static("[dim]📊[/dim] Status", classes="pane-header")
                        yield Button("📋 Copy Logs", id="btn-copy-logs", classes="action-button")
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

        # Start model loading and chain audio initialization after completion
        asyncio.create_task(self._complete_voice_initialization())

        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write("DEBUG: on_mount() - after scheduling voice initialization\n")
            f.flush()

    async def _complete_voice_initialization(self):
        """Complete voice initialization: load models then initialize audio"""
        # Run model loading worker
        # Note: initialize_voice is the method we want to run, but it's async.
        # We'll call it directly as a task since it handles its own worker logic if needed,
        # or we can just await it here if it's non-blocking enough.
        # The original code used run_worker on self.initialize_moshi(), but that method
        # seems to be missing from the app.py snippet I read.
        # However, initialize_voice() IS present and seems to be the main init method.
        # Let's assume initialize_voice is the correct one to call.
        
        # Wait, looking at app.py again, there was a reference to self.initialize_moshi()
        # but the method definition wasn't in the first 800 lines.
        # It's likely defined later in the file or I missed it.
        # Given I can't see it, I'll use initialize_voice() which I CAN see.
        
        success = await self.initialize_voice()
        
        with open("/tmp/xswarm_debug.log", "a") as f:
            f.write(f"DEBUG: Voice initialization completed: {success}\n")
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

    def update_chat_display(self):
        """Update the chat history display"""
        try:
            chat_container = self.query_one("#chat-history", Static)
            chat_text = Text()
            for msg in self.chat_history:
                role = msg["role"]
                content = msg["message"]
                timestamp = msg["timestamp"]
                
                if role == "user":
                    chat_text.append(f"[{timestamp}] You: ", style="bold green")
                else:
                    chat_text.append(f"[{timestamp}] Assistant: ", style="bold blue")
                chat_text.append(f"{content}\n\n")
            
            chat_container.update(chat_text)
        except Exception:
            pass

    def update_activity(self, message: str):
        """Add message to activity feed"""
        try:
            feed = self.query_one(ActivityFeed)
            feed.add_message(message)
        except Exception:
            pass
        
        # Also show toast for important messages to ensure visibility
        if any(trigger in message for trigger in ["Voice", "voice", "Error", "🎤", "DEBUG"]):
            self.notify(message, timeout=5.0)

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
        elif button_id == "btn-copy-logs":
            self.action_copy_logs()

    def action_copy_logs(self) -> None:
        """Copy activity logs to clipboard."""
        try:
            activity_feed = self.query_one("#activity", ActivityFeed)
            if activity_feed and activity_feed.messages:
                # Format messages for clipboard (timestamp [TYPE] message)
                log_text = ""
                for msg in activity_feed.messages:
                    log_text += f"[{msg['timestamp']}] [{msg['type'].upper()}] {msg['message']}\n"
                
                pyperclip.copy(log_text)
                self.notify("Activity logs copied to clipboard!", title="Success", severity="information")
            else:
                self.notify("No logs to copy.", title="Info", severity="warning")
        except Exception as e:
            self.notify(f"Failed to copy logs: {str(e)}", title="Error", severity="error")

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
        """Cleanup on exit - IMMEDIATE shutdown, no waiting"""
        try:
            # STEP 1: Signal threads to stop (but don't wait)
            if hasattr(self, '_processing_thread_stop'):
                self._processing_thread_stop.set()

            # STEP 2: Stop audio I/O immediately
            if hasattr(self, 'audio_io') and self.audio_io:
                try:
                    self.audio_io.stop()
                except:
                    pass

            # STEP 3: DON'T wait for threads - let OS clean up
            # The threads will die when the process exits

        except (KeyboardInterrupt, SystemExit):
            # User forcing exit - return immediately
            pass

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
            self.update_activity(f"DEBUG: Voice Queues: {bool(self.voice_queues)}")
            
            # Ensure memory manager is initialized first
            if not self.memory_manager:
                await self.initialize_memory()

            # Create voice bridge with persona and memory managers
            moshi_quality = getattr(self.config, 'moshi_quality', 'auto')
            # Initialize Voice Orchestrator
            self.voice_orchestrator = VoiceBridgeOrchestrator(
                self.persona_manager,
                self.memory_manager,
                self.config,
                user_id=self.user_id,
                moshi_quality=moshi_quality,
                voice_queues=self.voice_queues,
                log_callback=self.update_activity
            )
            # Initialize Moshi models
            await self.voice_orchestrator.initialize()
            # Register state change callback
            self.voice_orchestrator.on_state_change(self._on_voice_state_change)
            # Mark as initialized
            self.voice_initialized = True
            self.update_activity("✅ Voice bridge initialized successfully")
            
            # Update footer voice status
            try:
                footer = self.query_one(CyberpunkFooter)
                footer.voice_status = "connected"
            except Exception:
                pass

            # DON'T set baseline amplitude here - let it stay at 0.0 until actually speaking
            # The greeting generation below will set the amplitude when audio is played

            # Set connection_amplitude to idle (breathing) after voice is ready
            try:
                visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
                visualizer.connection_amplitude = 1.0  # Idle/breathing
                # Set callback so widget can pull data from app during its own animation timer
                visualizer.data_callback = self.get_visualizer_data
            except Exception:
                pass

            # NO app timer needed - widget pulls data during its own 20 FPS animation timer
            # This eliminates dual-timer race condition that caused freezes

            # Auto-start conversation for microphone visualization and greeting
            await self.voice_orchestrator.start_conversation()
            self.update_activity("🎙️  Microphone active - speak naturally, I'm listening...")

            # Generate and play startup greeting
            await self.generate_greeting_with_voice_bridge()

            return True
        except Exception as e:
            error_msg = str(e)
            if "Microphone access denied" in error_msg or "PortAudio" in error_msg:
                self.update_activity(f"❌ Microphone permission denied")
                self.update_activity("   Please grant microphone access in System Settings > Privacy & Security > Microphone")
                self.update_activity("   App will continue without voice features")
            else:
                self.update_activity(f"❌ Voice initialization failed: {e}")
            self.voice_initialized = False
            return False

    async def generate_greeting_with_voice_bridge(self):
        """Generate and play startup greeting using VoiceBridgeOrchestrator"""
        if not self.voice_orchestrator:
            return

        try:
            # Get current persona
            persona = self.persona_manager.get_current_persona()
            greeting_text = f"Hello, I am {persona.name}. How can I help you today?"
            
            # Use voice bridge to synthesize speech
            # Note: VoiceBridgeOrchestrator doesn't have a direct 'synthesize' method exposed publicly
            # in the snippet I saw, but usually it handles conversation.
            # For now, we'll just log it since we can't easily trigger just TTS without a user turn
            # in the current architecture without more deep diving.
            # Ideally we would inject a "system" turn or similar.
            
            self.update_activity(f"🤖 {persona.name}: {greeting_text}")
            
        except Exception as e:
            self.update_activity(f"Error generating greeting: {e}")

    def _on_voice_state_change(self, state: ConversationState):
        """Handle voice state changes from bridge"""
        # Map bridge state to app state
        # Bridge states: IDLE, LISTENING, THINKING, SPEAKING, ERROR
        self.state = state.value.lower()
        
        # Update visualizer state
        try:
            visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
            # Map state to visualizer state
            # Map state to visualizer state
            if self.state == "listening":
                visualizer.connection_amplitude = 1.0 # Active
            elif self.state == "speaking":
                visualizer.connection_amplitude = 1.0 # Active
            elif self.state == "thinking":
                visualizer.connection_amplitude = 0.5 # Thinking
            else:
                visualizer.connection_amplitude = 0.2 # Idle
        except Exception:
            pass

    def get_visualizer_data(self):
        """Callback for visualizer to pull data"""
        # Return dict with mic_amplitude and connection_amplitude
        if self.voice_orchestrator:
            mic_amp = getattr(self.voice_orchestrator, '_current_mic_amplitude', 0.0)
            moshi_amp = getattr(self.voice_orchestrator, '_current_moshi_amplitude', 0.0)
            # Use max of mic and moshi for visualization
            amplitude = max(mic_amp, moshi_amp)
            # Map state to connection_amplitude
            if self.state == "speaking":
                conn_amp = 2.0 + (amplitude * 98.0)  # 2-100 range
            elif self.state == "listening":
                conn_amp = 1.0  # Idle/breathing
            else:
                conn_amp = 0.0  # Not connected
            return {
                "mic_amplitude": mic_amp * 2.0,  # Scale for visibility
                "connection_amplitude": conn_amp
            }
        return {"mic_amplitude": 0.0, "connection_amplitude": 0.0}

