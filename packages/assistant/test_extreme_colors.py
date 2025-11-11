"""Test theme switching with EXTREME colors that are impossible to miss"""

import asyncio
from pathlib import Path
from assistant.dashboard.app import VoiceAssistantApp
from assistant.config import Config

# Override personas with extreme test colors
def setup_extreme_test():
    """Patch personas with extreme colors for testing"""
    personas_dir = Path(__file__).parent / "personas"
    config = Config()

    # Create app
    app = VoiceAssistantApp(config, personas_dir)

    # Override with extreme test colors
    for i, persona in enumerate(app.available_personas):
        extreme_colors = [
            "#FF0000",  # Pure red
            "#00FF00",  # Pure green
            "#0000FF",  # Pure blue
            "#FFFF00",  # Pure yellow
            "#FF00FF",  # Pure magenta
            "#00FFFF",  # Pure cyan
        ]
        if persona.theme:
            persona.theme.theme_color = extreme_colors[i % len(extreme_colors)]
            print(f"✓ Patched {persona.name} with {extreme_colors[i % len(extreme_colors)]}")

    # Speed up rotation for testing
    original_mount = app.on_mount
    def fast_mount():
        original_mount()
        app.set_interval(3.0, app.rotate_persona)  # Every 3 seconds
        print("\n🎨 Extreme color test mode: rotating every 3 seconds")
        print("Watch for DRAMATIC color changes: RED → GREEN → BLUE → YELLOW\n")

    app.on_mount = fast_mount

    return app

if __name__ == "__main__":
    app = setup_extreme_test()
    app.run()
