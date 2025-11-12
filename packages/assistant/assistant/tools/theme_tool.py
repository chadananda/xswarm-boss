"""
Theme change tool for switching personas and theme colors.
"""

from typing import Dict, Any
from .registry import Tool, ToolParameter


class ThemeChangeTool:
    """Tool for changing assistant theme/persona."""

    @staticmethod
    def create_tool(app) -> Tool:
        """
        Create theme change tool bound to app instance.

        Args:
            app: VoiceAssistantApp instance for executing theme changes

        Returns:
            Tool instance ready for registration
        """

        async def change_theme_handler(persona_name: str) -> str:
            """
            Change the assistant's theme/persona.

            Args:
                persona_name: Name of persona to switch to (e.g., "JARVIS", "GLaDOS")

            Returns:
                Success message with new persona name
            """
            # Get persona object
            persona = app.persona_manager.get_persona(persona_name)
            if not persona:
                available = [p.name for p in app.available_personas]
                return f"Persona '{persona_name}' not found. Available personas: {', '.join(available)}"

            # Verify persona has theme color
            if not persona.theme or not persona.theme.theme_color:
                return f"Persona '{persona_name}' does not have a theme color defined."

            # Update app theme
            app.update_activity(f"🎨 Changing theme to {persona_name}...")
            app._theme_palette = app._load_theme(persona.theme.theme_color)

            # Update reactive colors - triggers watchers that update ALL UI elements
            app.theme_shade_1 = app._theme_palette.shade_1
            app.theme_shade_2 = app._theme_palette.shade_2
            app.theme_shade_3 = app._theme_palette.shade_3
            app.theme_shade_4 = app._theme_palette.shade_4
            app.theme_shade_5 = app._theme_palette.shade_5

            # Update current persona name reactive
            app.current_persona_name = persona.name

            # Update visualizer border title
            try:
                visualizer = app.query_one("#visualizer")
                visualizer.border_title = f"xSwarm - {persona.name}"
            except Exception:
                pass

            # Update config
            app.config.default_persona = persona.name

            app.update_activity(f"✓ Theme changed to {persona.name}")

            # Trigger re-introduction with new persona
            import asyncio
            asyncio.create_task(app.generate_greeting(re_introduction=True))

            return f"Successfully changed theme to {persona.name}. Theme color: {persona.theme.theme_color}. Re-introducing as {persona.name}..."

        # Get available persona names for enum
        available_personas = [p.name for p in app.available_personas if p.theme and p.theme.theme_color]

        return Tool(
            name="change_theme",
            description="Change the assistant's persona and theme colors. Use this when the user asks to switch personalities or change the appearance.",
            parameters=[
                ToolParameter(
                    name="persona_name",
                    type="string",
                    description="Name of the persona to switch to",
                    required=True,
                    enum=available_personas
                )
            ],
            handler=change_theme_handler
        )
