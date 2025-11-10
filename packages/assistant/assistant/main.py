#!/usr/bin/env python3
"""
Voice Assistant - Main Entry Point

Brings together all components:
- MOSHI voice model
- Textual TUI dashboard
- Wake word detection
- Persona system
- Memory integration
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional
import argparse
import os

from .config import Config
from .dashboard.app import VoiceAssistantApp
from .dashboard.screens import WizardScreen
from .personas import PersonaManager
from .memory import MemoryManager
from .wake_word import WakeWordDetector


class VoiceAssistant:
    """
    Main voice assistant application.
    Integrates all components into cohesive system.
    """

    def __init__(self, config: Config, personas_dir: Path):
        self.config = config
        self.personas_dir = personas_dir
        self.app: Optional[VoiceAssistantApp] = None
        self.persona_manager: Optional[PersonaManager] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.wake_word_detector: Optional[WakeWordDetector] = None

        # State
        self.is_running = False
        self.user_id = "default-user"  # TODO: Get from auth

    async def initialize(self):
        """Initialize all components"""
        print("=== Voice Assistant Initialization ===\n")

        # 1. Load personas
        print("Loading personas...")
        if not self.personas_dir.exists():
            print(f"⚠️  Personas directory not found: {self.personas_dir}")
            print("   Creating default personas directory...")
            self.personas_dir.mkdir(parents=True, exist_ok=True)

        self.persona_manager = PersonaManager(self.personas_dir)

        available_personas = self.persona_manager.list_personas()
        if available_personas:
            # Set first persona as default or use specified persona
            if hasattr(self.config, 'default_persona') and self.config.default_persona:
                persona_name = self.config.default_persona
            else:
                persona_name = available_personas[0]

            self.persona_manager.set_current_persona(persona_name)
            current_persona = self.persona_manager.get_current_persona()

            if current_persona:
                print(f"✅ Active persona: {persona_name}")

                # Build comprehensive wake word list:
                # 1. All persona names (so user doesn't need to remember which is active)
                # 2. Common wake words (computer, alexa, boss, etc.)
                # 3. Persona-specific wake word if defined

                all_wake_words = []

                # Add all persona names (lowercase)
                persona_names = [name.lower() for name in available_personas]
                all_wake_words.extend(persona_names)

                # Add common wake words
                common_wake_words = Config.get_common_wake_words()
                all_wake_words.extend(common_wake_words)

                # Add persona-specific wake word if defined (avoid duplicates)
                if hasattr(current_persona, 'wake_word') and current_persona.wake_word:
                    persona_wake_word = current_persona.wake_word.lower()
                    if persona_wake_word not in all_wake_words:
                        all_wake_words.append(persona_wake_word)

                # Remove duplicates while preserving order
                seen = set()
                unique_wake_words = []
                for word in all_wake_words:
                    if word not in seen:
                        seen.add(word)
                        unique_wake_words.append(word)

                # Store the complete list in config
                self.config.wake_word = unique_wake_words

                # Show summary
                print(f"   Wake words: {len(unique_wake_words)} active")
                print(f"   - Persona names: {', '.join(persona_names)}")
                print(f"   - Common: {', '.join(common_wake_words)}")
        else:
            print("⚠️  No personas found - using default settings")

        # 2. Initialize memory
        if self.config.memory_enabled:
            print("\nInitializing memory...")
            self.memory_manager = MemoryManager(
                server_url=self.config.server_url,
                api_token=self.config.api_token
            )
            try:
                await self.memory_manager.initialize()
                print("✅ Memory system initialized")
            except Exception as e:
                print(f"⚠️  Memory initialization warning: {e}")
                print("   Continuing with local cache only...")
        else:
            print("\n⚠️  Memory system disabled (--no-memory)")

        # 3. Initialize dashboard (TUI)
        print("\nInitializing dashboard...")
        self.app = VoiceAssistantApp(self.config, self.personas_dir)

        # 4. Voice models will be loaded by dashboard
        print("\nVoice models will be loaded by dashboard...")

        print("\n✅ Initialization complete\n")

    async def run(self):
        """Run the application"""
        self.is_running = True

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            # Run TUI dashboard
            await self.app.run_async()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await self.cleanup()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}, shutting down...")
        self.is_running = False
        sys.exit(0)

    async def cleanup(self):
        """Cleanup resources"""
        print("Cleaning up...")

        if self.wake_word_detector:
            self.wake_word_detector.stop()

        if self.memory_manager:
            await self.memory_manager.close()

        print("✅ Cleanup complete")


async def show_wizard(personas_dir: Path) -> Config:
    """Show first-run wizard and return configured config"""
    from textual.app import App

    # Temporary minimal app just to show the wizard
    class WizardApp(App):
        def __init__(self):
            super().__init__()
            self.result_config = None

        async def on_mount(self):
            result = await self.push_screen(WizardScreen(personas_dir), wait_for_dismiss=True)
            self.result_config = result
            self.exit(result)

    wizard_app = WizardApp()
    return await wizard_app.run_async()


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="xSwarm Voice Assistant - Interactive TUI with flexible persona system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Launch interactive TUI
  %(prog)s --debug            # Launch with debug logging
  %(prog)s --config /path     # Use custom config file

Configuration:
  All settings are configured interactively in the TUI.
  Press 's' inside the app to open settings.
  Config saved to: ~/.config/xswarm/config.yaml
        """
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to custom config file"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    args = parser.parse_args()

    # Enable debug if requested
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Get personas directory
    personas_dir = Path(__file__).parent.parent.parent / "personas"

    # Load or create config
    config_path = args.config if args.config else None
    config = Config.load_from_file(config_path)

    # Check if first run (no config file exists)
    if not (args.config or Config.get_config_path().exists()):
        print("👋 Welcome! Let's set up your voice assistant...\n")
        try:
            # Show wizard in TUI
            config = asyncio.run(show_wizard(personas_dir))
            if not config:
                print("Setup cancelled. Using defaults.")
                config = Config()
        except Exception as e:
            print(f"Wizard error: {e}")
            print("Using default configuration.")
            config = Config()

    # Create and run assistant
    assistant = VoiceAssistant(config, personas_dir)

    try:
        asyncio.run(assistant.initialize())
        asyncio.run(assistant.run())
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
