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
from .personas import PersonaManager
from .memory import MemoryManager
from .wake_word import WakeWordDetector


class VoiceAssistant:
    """
    Main voice assistant application.
    Integrates all components into cohesive system.
    """

    def __init__(self, config: Config):
        self.config = config
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
        personas_dir = Path(__file__).parent.parent.parent / "personas"

        if not personas_dir.exists():
            print(f"⚠️  Personas directory not found: {personas_dir}")
            print("   Creating default personas directory...")
            personas_dir.mkdir(parents=True, exist_ok=True)

        self.persona_manager = PersonaManager(personas_dir)

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

                # Update wake word from persona if specified
                if hasattr(current_persona, 'wake_word') and current_persona.wake_word:
                    self.config.wake_word = current_persona.wake_word
                    print(f"   Wake word: {self.config.wake_word}")
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
        self.app = VoiceAssistantApp(self.config)

        # 4. MOSHI will be loaded by dashboard
        print("\nMOSHI will be loaded by dashboard...")

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


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Voice Assistant with MOSHI, Textual TUI, and persona system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Run with default settings
  %(prog)s --persona JARVIS             # Use specific persona
  %(prog)s --device mps                 # Force MPS device (Mac M3)
  %(prog)s --no-memory                  # Disable memory server
  %(prog)s --server-url http://prod:3000 --persona ASSISTANT
        """
    )

    parser.add_argument(
        "--server-url",
        default=os.environ.get("XSWARM_SERVER_URL", "http://localhost:3000"),
        help="Memory server URL (default: $XSWARM_SERVER_URL or http://localhost:3000)"
    )

    parser.add_argument(
        "--api-token",
        default=os.environ.get("XSWARM_API_TOKEN"),
        help="API token for server authentication (default: $XSWARM_API_TOKEN)"
    )

    parser.add_argument(
        "--persona",
        help="Persona to load (default: first available)"
    )

    parser.add_argument(
        "--wake-word",
        help="Custom wake word (overrides persona)"
    )

    parser.add_argument(
        "--device",
        choices=["auto", "mps", "cuda", "cpu"],
        default="auto",
        help="Device for MOSHI (auto, mps, cuda, cpu)"
    )

    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable memory server integration"
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

    # Create config
    config = Config()
    config.server_url = args.server_url
    config.device = args.device
    config.memory_enabled = not args.no_memory
    config.api_token = args.api_token

    if args.persona:
        config.default_persona = args.persona

    if args.wake_word:
        config.wake_word = args.wake_word

    # Enable debug if requested
    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Create and run assistant
    assistant = VoiceAssistant(config)

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
