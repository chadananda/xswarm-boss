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
import sys
from pathlib import Path
from typing import Optional, cast
import argparse
import os
import atexit

from .config import Config
from .dashboard import VoiceAssistantApp, WizardScreen
from .personas import PersonaManager
from .memory import MemoryManager
from .wake_word import WakeWordDetector
from .scheduler import Scheduler


class SingletonLock:
    """Ensures only one instance of the assistant runs at a time"""

    def __init__(self, lockfile: Path):
        self.lockfile = lockfile
        self.locked = False

    def acquire(self) -> bool:
        """Try to acquire lock. Kills existing instance if found."""
        import signal
        import time

        if self.lockfile.exists():
            # Check if the process is actually running
            try:
                pid = int(self.lockfile.read_text().strip())
                # Check if process exists
                os.kill(pid, 0)  # Doesn't actually kill, just checks existence

                # Process exists - kill it to free GPU
                print(f"Found existing instance (PID {pid}). Killing...")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)
                    # If still alive, force kill
                    try:
                        os.kill(pid, 0)
                        os.kill(pid, signal.SIGKILL)
                        time.sleep(0.2)
                    except OSError:
                        pass  # Already dead
                except OSError:
                    pass  # Process already gone

                # Remove stale lock
                self.lockfile.unlink()

            except (OSError, ValueError):
                # Process doesn't exist or invalid PID - stale lock
                self.lockfile.unlink()

        # Create lock file with current PID
        self.lockfile.parent.mkdir(parents=True, exist_ok=True)
        self.lockfile.write_text(str(os.getpid()))
        self.locked = True

        # Register cleanup on exit
        atexit.register(self.release)
        return True

    def release(self):
        """Release the lock"""
        if self.locked and self.lockfile.exists():
            try:
                self.lockfile.unlink()
            except:
                pass  # Ignore errors during cleanup
            self.locked = False


class VoiceAssistant:
    """
    Main voice assistant application.
    Integrates all components into cohesive system.
    """

    def __init__(self, config: Config, personas_dir: Path, voice_server_process=None, voice_queues=None):
        self.config = config
        self.personas_dir = personas_dir
        self.voice_server_process = voice_server_process
        self.voice_queues = voice_queues
        self.app: Optional[VoiceAssistantApp] = None
        self.persona_manager: Optional[PersonaManager] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.wake_word_detector: Optional[WakeWordDetector] = None
        self.scheduler: Optional['Scheduler'] = None

        # State
        self.is_running = False
        self.user_id = "default-user"  # TODO: Get from auth

    async def initialize(self):
        """Initialize all components"""
        # 1. Load personas
        if not self.personas_dir.exists():
            self.personas_dir.mkdir(parents=True, exist_ok=True)

        self.persona_manager = PersonaManager(self.personas_dir)

        available_personas = self.persona_manager.list_personas()
        if available_personas:
            # Set first persona as default or use specified persona
            if hasattr(self.config, 'default_persona') and self.config.default_persona:
                persona_name = self.config.default_persona
            else:
                import random
                persona_name = random.choice(available_personas)
                print(f"🎲 Randomly selected persona: {persona_name}")

            self.persona_manager.set_current_persona(persona_name)
            current_persona = self.persona_manager.get_current_persona()

            if current_persona:
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

        # 2. Initialize memory
        # Skip memory initialization in debug mode to avoid connection errors
        if self.config.memory_enabled and not self.config.is_debug_mode:
            self.memory_manager = MemoryManager(
                server_url=self.config.server_url,
                api_token=self.config.api_token
            )
            try:
                await self.memory_manager.initialize()
            except Exception:
                pass  # Continue with local cache only

        # 3. Initialize dashboard (TUI)
        # 3. Initialize dashboard (TUI)
        self.app = VoiceAssistantApp(self.config, self.personas_dir, voice_server_process=self.voice_server_process, voice_queues=self.voice_queues)

        # 4. Initialize Scheduler (connects to Thinking Engine)
        # Note: Thinking Engine is created inside VoiceAssistantApp, so we access it there
        if hasattr(self.app, 'thinking_engine'):
            self.scheduler = Scheduler(self.app.thinking_engine)
            self.scheduler.start()

    async def run(self):
        """Run the application"""
        self.is_running = True

        try:
            # Run TUI dashboard (Textual handles SIGINT/SIGTERM internally)
            await self.app.run_async()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        if self.wake_word_detector:
            self.wake_word_detector.stop()

        if self.scheduler:
            self.scheduler.stop()

        if self.memory_manager:
            await self.memory_manager.close()


async def show_wizard(personas_dir: Path) -> Config:
    """Show first-run wizard and return configured config"""
    from textual.app import App

    # Temporary minimal app just to show the wizard
    class WizardApp(App):
        def __init__(self):
            super().__init__()
            self.result_config = None

        def on_mount(self):
            # Use call_later to run in a worker context
            self.call_later(self._show_wizard)

        def _show_wizard(self):
            # Use run_worker to create proper worker context
            self.run_worker(self._show_wizard_async())

        async def _show_wizard_async(self):
            result = await self.push_screen(WizardScreen(personas_dir), wait_for_dismiss=True)
            self.result_config = result
            self.exit(result)

    wizard_app = WizardApp()
    return cast(Config, await wizard_app.run_async())


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

    # Determine default personas directory
    # Try root personas directory first (development mode)
    root_personas = Path(__file__).parents[3] / "personas"
    local_personas = Path(__file__).parent / "personas"
    
    default_personas_dir = root_personas if root_personas.exists() else local_personas

    parser.add_argument(
        "--personas-dir",
        type=Path,
        default=default_personas_dir,
        help="Directory containing personas"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    from . import __version__
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # Ensure only one instance runs at a time
    config_dir = Path.home() / ".config" / "xswarm"
    lockfile = config_dir / "assistant.lock"
    lock = SingletonLock(lockfile)

    if not lock.acquire():
        # Another instance is already running
        pid = lockfile.read_text().strip()
        print(f"❌ Voice assistant is already running (PID {pid})")
        print("💡 Use 'pkill -f assistant.main' to kill the running instance if needed")
        sys.exit(1)

    # Get personas directory
    personas_dir = Path(__file__).parent.parent.parent.parent / "personas"

    # GPU detection and service selection
    from .hardware import detect_gpu_capability, select_services

    gpu = detect_gpu_capability()
    service_config = select_services(gpu)

    # Load or create config
    config_path = args.config if args.config else None
    config = Config.load_from_file(config_path)

    # Set debug mode flag
    config.is_debug_mode = args.debug

    # Load API keys from .env if in debug mode
    if args.debug:
        config = Config.load_env_keys(config)

    # Apply service selection to config
    config.moshi_quality = service_config.moshi_quality
    config.thinking_mode = service_config.thinking_mode
    config.thinking_model = service_config.thinking_model
    config.embedding_mode = service_config.embedding_mode

    # Check if first run (no config file exists)
    # Skip wizard in debug mode for faster local testing
    if not args.debug and not (args.config or Config.get_config_path().exists()):
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
    elif args.debug and not (args.config or Config.get_config_path().exists()):
        config = Config()

    # Start Moshi voice server BEFORE Textual to avoid multiprocessing issues
    # The server runs MLX inference in a separate process for proper Metal GPU utilization
    voice_server_process = None
    voice_queues = None
    
    print(f"DEBUG: Moshi Mode: {service_config.moshi_mode}")
    if service_config.moshi_mode == "local":
        print(f"🚀 Starting voice server (quality={service_config.moshi_quality})...")
        try:
            from .voice_server import start_server_process
            # Unpack the tuple returned by start_server_process
            process, c2s, s2c, status = start_server_process(quality=service_config.moshi_quality)
            voice_server_process = process
            voice_queues = (c2s, s2c, status)
            print("✅ Voice server process started")
        except Exception as e:
            print(f"⚠️  Failed to start voice server: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()

    # Create and run assistant
    assistant = VoiceAssistant(config, personas_dir, voice_server_process=voice_server_process, voice_queues=voice_queues)

    try:
        asyncio.run(assistant.initialize())
        asyncio.run(assistant.run())
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup voice server
        if voice_server_process:
            voice_server_process.terminate()
            voice_server_process.join(timeout=2)


if __name__ == "__main__":
    main()
