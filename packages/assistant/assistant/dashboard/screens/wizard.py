"""
First-run wizard for initial setup.
"""

from pathlib import Path
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Label, Input, Select, Button, Static
from textual.binding import Binding

from ...config import Config
from ...personas import PersonaManager


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

    .persona-grid {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        height: auto;
        margin-bottom: 1;
    }

    .persona-card {
        border: solid $primary;
        padding: 1;
        margin: 0 1 1 0;
        height: auto;
    }

    .persona-name {
        text-style: bold;
    }

    .persona-description {
        color: $text-muted;
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
