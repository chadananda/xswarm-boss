"""
Settings screen for interactive configuration.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Label, Input, Select, Button, Switch, Static
from textual.binding import Binding

from ...config import Config
from ...personas import PersonaManager


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
