"""Status information widget"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text


class StatusWidget(Static):
    """Display connection status and current state"""

    device_name = reactive("Unknown")
    state = reactive("initializing")
    server_status = reactive("disconnected")
    last_wake_word = reactive(None)  # Track last detected wake word

    def render(self) -> Text:
        """Render status information"""
        result = Text()

        result.append("Status\n", style="bold underline")
        result.append("\n")

        # Device
        result.append("Device: ", style="bold")
        result.append(f"{self.device_name}\n")

        # State
        state_colors = {
            "idle": "cyan",
            "ready": "green",
            "listening": "yellow",
            "speaking": "magenta",
            "thinking": "blue",
            "error": "red"
        }
        state_color = state_colors.get(self.state, "white")
        result.append("State: ", style="bold")
        result.append(f"{self.state}\n", style=f"bold {state_color}")

        # Server
        server_color = "green" if self.server_status == "connected" else "red"
        result.append("Server: ", style="bold")
        result.append(f"{self.server_status}\n", style=server_color)

        # Wake word indicator (for testing)
        if self.last_wake_word:
            result.append("\nWake Word: ", style="bold")
            result.append(f"'{self.last_wake_word}'\n", style="bold yellow")

        result.append("\n")
        result.append("Controls:\n", style="bold underline")
        result.append("  SPACE  - Toggle listening\n", style="dim")
        result.append("  Q      - Quit\n", style="dim")
        result.append("  S      - Settings\n", style="dim")

        return result
