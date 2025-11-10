"""Cyberpunk ASCII art header with boot sequence"""

import asyncio
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.align import Align


class CyberpunkHeader(Static):
    """
    Cyberpunk-styled header with ASCII art logo and boot sequence.

    Features:
    - ASCII art XSWARM logo
    - Animated boot sequence on startup
    - System status bar
    - Neon cyan aesthetic
    """

    boot_complete = reactive(False)
    boot_stage = reactive(0)
    persona_name = reactive("JARVIS")
    system_status = reactive("INITIALIZING")

    # ASCII art logo using box-drawing characters
    LOGO = """
╔═══════════════════════════════════════════════════════════════════════════╗
║  ██╗  ██╗███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗                  ║
║  ╚██╗██╔╝██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║                  ║
║   ╚███╔╝ ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║                  ║
║   ██╔██╗ ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║                  ║
║  ██╔╝ ██╗███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║                  ║
║  ╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝                  ║
║                                                                           ║
║              ▓▒░  VOICE ASSISTANT INTERFACE v2.0  ░▒▓                    ║
║                   >> OVERABUNDANT PERSONALITY <<                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

    BOOT_STAGES = [
        "INITIALIZING NEURAL NETWORK",
        "LOADING PERSONA MATRIX",
        "ESTABLISHING VOICE LINK",
        "CALIBRATING AUDIO SYSTEMS",
        "CONNECTING TO SERVER",
        "SYSTEM READY"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.boot_messages = []

    def on_mount(self) -> None:
        """Start boot sequence animation when mounted"""
        if not self.boot_complete:
            self.run_boot_sequence()

    async def run_boot_sequence(self) -> None:
        """Animate boot sequence"""
        for i, stage in enumerate(self.BOOT_STAGES):
            self.boot_stage = i
            self.boot_messages.append(stage)
            self.refresh()
            await asyncio.sleep(0.3)  # Fast cyberpunk boot

        self.boot_complete = True
        self.system_status = "ONLINE"
        self.refresh()

    def render(self) -> Text:
        """Render header with logo and boot sequence"""
        result = Text()

        # Get actual widget width (fallback to 79 if too small)
        widget_width = max(self.size.width, 79)
        border_width = widget_width - 2  # Account for ╔ and ╗
        inner_width = border_width - 2  # Account for "║ " and " ║"

        if not self.boot_complete:
            # Boot sequence display
            result.append("╔" + "═" * border_width + "╗\n", style="bold cyan")
            result.append("║", style="bold cyan")
            result.append(" XSWARM VOICE ASSISTANT ".center(border_width), style="bold yellow")
            result.append("║\n", style="bold cyan")
            result.append("║", style="bold cyan")
            result.append(" SYSTEM BOOT SEQUENCE ".center(border_width), style="bold magenta")
            result.append("║\n", style="bold cyan")
            result.append("╠" + "═" * border_width + "╣\n", style="bold cyan")

            # Show boot messages
            for msg in self.boot_messages[-5:]:  # Last 5 messages
                result.append("║ ", style="bold cyan")
                result.append("▓▒░ ", style="dim cyan")
                result.append(msg, style="green")
                # Pad to inner_width
                msg_len = len(msg) + 4  # "▓▒░ " prefix
                padding = inner_width - msg_len
                result.append(" " * padding)
                result.append(" ║\n", style="bold cyan")

            # Fill remaining lines
            shown = len(self.boot_messages[-5:])
            for _ in range(5 - shown):
                result.append("║" + " " * border_width + "║\n", style="bold cyan")

            result.append("╚" + "═" * border_width + "╝", style="bold cyan")

        else:
            # Main logo display - fixed width ASCII art
            result.append(self.LOGO, style="bold cyan")

            # Status bar - responsive
            result.append("\n")
            result.append("╔" + "═" * border_width + "╗\n", style="bold magenta")
            result.append("║ ", style="bold magenta")

            # Build status line
            status_line = f"◉ PERSONA: {self.persona_name}  ◉ STATUS: {self.system_status}  ◉ NEURAL LINK: ACTIVE"

            # Left side: Persona
            result.append("◉ PERSONA: ", style="dim white")
            result.append(self.persona_name, style="bold yellow")

            # Center: Status
            result.append("  ◉ STATUS: ", style="dim white")
            result.append(self.system_status, style="bold green" if self.system_status == "ONLINE" else "dim white")

            # Right side: System indicator
            result.append("  ◉ NEURAL LINK: ", style="dim white")
            result.append("ACTIVE", style="bold green")

            # Padding to fit width
            padding = inner_width - len(status_line)
            result.append(" " * padding)

            result.append(" ║\n", style="bold magenta")
            result.append("╚" + "═" * border_width + "╝", style="bold magenta")

        return result

    def update_persona(self, persona: str) -> None:
        """Update current persona display"""
        self.persona_name = persona.upper()

    def update_status(self, status: str) -> None:
        """Update system status"""
        self.system_status = status.upper()

    def trigger_glitch_effect(self) -> None:
        """Trigger a visual glitch effect (for drama)"""
        # TODO: Implement glitch animation in Phase 7
        pass


class CompactCyberpunkHeader(Static):
    """
    Compact version of header for smaller terminals.
    One-line banner with essential info.
    """

    persona_name = reactive("JARVIS")
    system_status = reactive("ONLINE")

    def render(self) -> Text:
        """Render compact header"""
        result = Text()

        result.append("▓▒░ ", style="bold cyan")
        result.append("XSWARM", style="bold yellow")
        result.append(" ░▒▓ ", style="bold cyan")
        result.append(f"[{self.persona_name}]", style="bold magenta")
        result.append(" ◉ ", style="dim white")
        result.append(self.system_status, style="bold green")

        return result

    def update_persona(self, persona: str) -> None:
        """Update current persona display"""
        self.persona_name = persona.upper()

    def update_status(self, status: str) -> None:
        """Update system status"""
        self.system_status = status.upper()
