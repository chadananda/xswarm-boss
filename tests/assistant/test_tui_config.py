#!/usr/bin/env python3
"""
Test script for TUI configuration system.
Verifies:
- Config persistence (load/save)
- Screen imports work
- First-run wizard logic
- Settings screen logic
"""

import sys
import asyncio
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.config import Config
from assistant.dashboard.screens import SettingsScreen, WizardScreen
from assistant.personas import PersonaManager


def test_config_persistence():
    """Test config load/save functionality"""
    print("\n=== Test 1: Config Persistence ===")

    # Create temporary config file
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test_config.yaml"

        # Create and save config
        config = Config(
            default_persona="JARVIS",
            device="mps",
            wake_word="computer",
            server_url="http://test:3000",
            api_token="test-token",
            memory_enabled=True
        )
        config.save_to_file(config_path)
        print(f"✓ Config saved to {config_path}")

        # Load config back
        loaded_config = Config.load_from_file(config_path)
        print(f"✓ Config loaded from {config_path}")

        # Verify values
        assert loaded_config.default_persona == "JARVIS", "Persona mismatch"
        assert loaded_config.device == "mps", "Device mismatch"
        assert loaded_config.wake_word == "computer", "Wake word mismatch"
        assert loaded_config.server_url == "http://test:3000", "Server URL mismatch"
        assert loaded_config.api_token == "test-token", "API token mismatch"
        assert loaded_config.memory_enabled == True, "Memory enabled mismatch"
        print("✓ All config values match after load")

    print("✅ Config persistence test PASSED\n")


def test_screen_imports():
    """Test that screen imports work correctly"""
    print("=== Test 2: Screen Imports ===")

    try:
        from assistant.dashboard.screens import SettingsScreen, WizardScreen
        print("✓ SettingsScreen imported")
        print("✓ WizardScreen imported")
        print("✅ Screen imports test PASSED\n")
    except ImportError as e:
        print(f"❌ Import failed: {e}\n")
        raise


def test_wizard_screen_instantiation():
    """Test wizard screen can be instantiated"""
    print("=== Test 3: Wizard Screen Instantiation ===")

    # Create personas directory for testing
    personas_dir = Path(__file__).parent.parent.parent.parent / "personas"

    try:
        wizard = WizardScreen(personas_dir)
        print("✓ WizardScreen instantiated")

        # Check initial config
        assert wizard.config is not None, "Config not initialized"
        print("✓ Initial config created")

        print("✅ Wizard screen instantiation test PASSED\n")
    except Exception as e:
        print(f"❌ Wizard instantiation failed: {e}\n")
        raise


def test_settings_screen_instantiation():
    """Test settings screen can be instantiated"""
    print("=== Test 4: Settings Screen Instantiation ===")

    # Create test config and personas directory
    config = Config()
    personas_dir = Path(__file__).parent.parent.parent.parent / "personas"

    try:
        settings = SettingsScreen(config, personas_dir)
        print("✓ SettingsScreen instantiated")

        # Check config reference
        assert settings.config is config, "Config reference mismatch"
        print("✓ Config reference correct")

        print("✅ Settings screen instantiation test PASSED\n")
    except Exception as e:
        print(f"❌ Settings instantiation failed: {e}\n")
        raise


def test_persona_manager_integration():
    """Test persona manager works with config"""
    print("=== Test 5: Persona Manager Integration ===")

    personas_dir = Path(__file__).parent.parent.parent.parent / "personas"

    try:
        manager = PersonaManager(personas_dir)
        print("✓ PersonaManager instantiated")

        personas = manager.list_personas()
        print(f"✓ Found {len(personas)} personas: {personas}")

        if personas:
            # Test setting current persona
            manager.set_current_persona(personas[0])
            print(f"✓ Set current persona to {personas[0]}")

            current = manager.get_current_persona()
            assert current is not None, "Current persona not set"
            print(f"✓ Current persona: {current.name}")
        else:
            print("⚠️  No personas found (this is okay for testing)")

        print("✅ Persona manager integration test PASSED\n")
    except Exception as e:
        print(f"❌ Persona manager test failed: {e}\n")
        raise


def test_config_defaults():
    """Test config has sensible defaults"""
    print("=== Test 6: Config Defaults ===")

    config = Config()

    # Check defaults
    assert config.device == "auto", f"Default device should be 'auto', got '{config.device}'"
    print(f"✓ Default device: {config.device}")

    assert config.wake_word == "jarvis", f"Default wake word should be 'jarvis', got '{config.wake_word}'"
    print(f"✓ Default wake word: {config.wake_word}")

    assert config.server_url == "http://localhost:3000", f"Default server URL mismatch"
    print(f"✓ Default server URL: {config.server_url}")

    assert config.memory_enabled == True, "Memory should be enabled by default"
    print(f"✓ Memory enabled by default: {config.memory_enabled}")

    print("✅ Config defaults test PASSED\n")


def test_first_run_detection():
    """Test that first-run is detected correctly"""
    print("=== Test 7: First-Run Detection ===")

    # Test with non-existent config path
    config_path = Path("/tmp/nonexistent_config_12345.yaml")

    # First run should return default config
    config = Config.load_from_file(config_path)
    assert config is not None, "Should return default config on first run"
    assert config.device == "auto", "Should have default values on first run"
    print("✓ First run detected, default config returned")

    # Test that config path method works
    default_path = Config.get_config_path()
    assert default_path == Path.home() / ".config" / "xswarm" / "config.yaml"
    print(f"✓ Default config path: {default_path}")

    print("✅ First-run detection test PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TUI Configuration System Test Suite")
    print("=" * 60)

    try:
        test_config_persistence()
        test_screen_imports()
        test_wizard_screen_instantiation()
        test_settings_screen_instantiation()
        test_persona_manager_integration()
        test_config_defaults()
        test_first_run_detection()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED (7/7)")
        print("=" * 60 + "\n")

        print("TUI configuration system is ready for use!")
        print("\nNext steps:")
        print("1. Run 'assistant' to see the first-run wizard")
        print("2. Press 's' in the TUI to open settings")
        print("3. Config will be saved to ~/.config/xswarm/config.yaml")

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST SUITE FAILED")
        print(f"Error: {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
