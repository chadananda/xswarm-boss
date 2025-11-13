"""
Visual snapshot tests for TUI Voice Integration.

Tests that VoiceAssistantApp correctly displays voice states, visualizations,
and theme colors using pytest-textual-snapshot.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from assistant.dashboard.app import VoiceAssistantApp
from assistant.config import Config
from assistant.voice.bridge import ConversationState


# Test fixtures
@pytest.fixture
def mock_config():
    """Create a mock Config instance."""
    config = Mock(spec=Config)
    config.theme_base_color = "#8899aa"
    config.default_persona = "JARVIS"
    config.moshi_quality = "auto"
    config.detect_device = Mock(return_value="cpu")
    return config


@pytest.fixture
def mock_personas_dir(tmp_path):
    """Create a temporary personas directory."""
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir(exist_ok=True)
    
    # Create JARVIS persona YAML
    jarvis_yaml = personas_dir / "JARVIS.yaml"
    jarvis_yaml.write_text("""
name: JARVIS
system_prompt: "You are JARVIS, an AI assistant."
theme:
  theme_color: "#00D4FF"
personality:
  traits:
    - helpful
    - professional
""")
    
    # Create GLaDOS persona YAML
    glados_yaml = personas_dir / "GLaDOS.yaml"
    glados_yaml.write_text("""
name: GLaDOS
system_prompt: "You are GLaDOS, a sarcastic AI."
theme:
  theme_color: "#FFA500"
personality:
  traits:
    - sarcastic
    - testing
""")
    
    return personas_dir


@pytest.fixture
def test_app(mock_config, mock_personas_dir):
    """Create a VoiceAssistantApp instance for testing."""
    return VoiceAssistantApp(mock_config, mock_personas_dir)


# A. Voice State Display Tests

def test_voice_state_idle(snap_compare, mock_config, mock_personas_dir):
    """Test TUI displays IDLE voice state (default state)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    assert snap_compare(app, terminal_size=(80, 30))


def test_voice_state_listening(snap_compare, mock_config, mock_personas_dir):
    """Test TUI displays LISTENING voice state (mic active)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # Set state to listening
    app.state = "listening"
    assert snap_compare(app, terminal_size=(80, 30))


def test_voice_state_thinking(snap_compare, mock_config, mock_personas_dir):
    """Test TUI displays THINKING voice state (AI processing)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # Set state to thinking
    app.state = "thinking"
    assert snap_compare(app, terminal_size=(80, 30))


def test_voice_state_speaking(snap_compare, mock_config, mock_personas_dir):
    """Test TUI displays SPEAKING voice state (audio playing)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # Set state to speaking
    app.state = "speaking"
    assert snap_compare(app, terminal_size=(80, 30))


def test_voice_state_error(snap_compare, mock_config, mock_personas_dir):
    """Test TUI displays ERROR voice state."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # Set state to error
    app.state = "error"
    assert snap_compare(app, terminal_size=(80, 30))


# B. Responsive Layout Tests

@pytest.mark.parametrize("size", [
    (40, 15),   # Small terminal
    (80, 30),   # Standard terminal
    (120, 40),  # Large terminal
])
def test_voice_ui_responsive(snap_compare, mock_config, mock_personas_dir, size):
    """Test voice UI renders correctly at different terminal sizes."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    assert snap_compare(app, terminal_size=size)


# C. Theme Integration Tests

@pytest.mark.parametrize("persona_config", [
    ("JARVIS", "#00D4FF"),   # Cyan
    ("GLaDOS", "#FFA500"),   # Orange
])
def test_voice_ui_themes(snap_compare, mock_config, mock_personas_dir, persona_config):
    """Test voice UI applies persona theme colors correctly."""
    persona_name, theme_color = persona_config
    
    # Set default persona in config
    mock_config.default_persona = persona_name
    
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    
    # Load the persona theme
    persona = app.persona_manager.get_persona(persona_name)
    if persona and persona.theme and persona.theme.theme_color:
        app._theme_palette = app._load_theme(persona.theme.theme_color)
        app.theme_shade_1 = app._theme_palette.shade_1
        app.theme_shade_2 = app._theme_palette.shade_2
        app.theme_shade_3 = app._theme_palette.shade_3
        app.theme_shade_4 = app._theme_palette.shade_4
        app.theme_shade_5 = app._theme_palette.shade_5
        app.current_persona_name = persona.name
    
    assert snap_compare(app, terminal_size=(80, 30))


# D. Visualizer with Different Amplitudes

def test_visualizer_quiet(snap_compare, mock_config, mock_personas_dir):
    """Test visualizer with no audio (0% amplitude)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    
    # Set amplitude to 0
    app.amplitude = 0.0
    
    # Mock voice bridge to return zero amplitudes
    if app.voice_initialized and app.voice_bridge:
        with patch.object(app.voice_bridge, 'get_amplitudes', return_value={
            "mic_amplitude": 0.0,
            "moshi_amplitude": 0.0
        }):
            assert snap_compare(app, terminal_size=(80, 30))
    else:
        assert snap_compare(app, terminal_size=(80, 30))


def test_visualizer_loud(snap_compare, mock_config, mock_personas_dir):
    """Test visualizer with high audio (100% amplitude)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    
    # Set amplitude to maximum
    app.amplitude = 1.0
    
    # Mock voice bridge to return high amplitudes
    if app.voice_initialized and app.voice_bridge:
        with patch.object(app.voice_bridge, 'get_amplitudes', return_value={
            "mic_amplitude": 1.0,
            "moshi_amplitude": 1.0
        }):
            assert snap_compare(app, terminal_size=(80, 30))
    else:
        assert snap_compare(app, terminal_size=(80, 30))


def test_visualizer_mixed(snap_compare, mock_config, mock_personas_dir):
    """Test visualizer with mixed levels (mic:50%, moshi:75%)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    
    # Set amplitude to medium
    app.amplitude = 0.5
    
    # Mock voice bridge to return mixed amplitudes
    if app.voice_initialized and app.voice_bridge:
        with patch.object(app.voice_bridge, 'get_amplitudes', return_value={
            "mic_amplitude": 0.5,
            "moshi_amplitude": 0.75
        }):
            assert snap_compare(app, terminal_size=(80, 30))
    else:
        assert snap_compare(app, terminal_size=(80, 30))


# E. Keybinding Tests

def test_ctrl_v_keybinding_shown(snap_compare, mock_config, mock_personas_dir):
    """Test that Ctrl+V keybinding is shown in footer."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # The footer should show Ctrl+V binding
    assert snap_compare(app, terminal_size=(80, 30))


# F. Edge Cases

def test_voice_ui_empty_state(snap_compare, mock_config, mock_personas_dir):
    """Test TUI with no voice bridge initialized."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # Ensure voice is not initialized
    app.voice_initialized = False
    app.voice_bridge = None
    assert snap_compare(app, terminal_size=(80, 30))


def test_voice_ui_with_long_persona_name(snap_compare, mock_config, mock_personas_dir):
    """Test TUI handles long persona names without overflow."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    # Set a very long persona name
    app.current_persona_name = "Very Long Persona Name That Should Not Overflow"
    assert snap_compare(app, terminal_size=(80, 30))


# G. Tab Navigation with Voice Active

def test_voice_ui_settings_tab(snap_compare, mock_config, mock_personas_dir):
    """Test voice UI in settings tab."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    app.active_tab = "settings"
    assert snap_compare(app, terminal_size=(80, 30))


def test_voice_ui_chat_tab(snap_compare, mock_config, mock_personas_dir):
    """Test voice UI in chat tab (shows chat history)."""
    app = VoiceAssistantApp(mock_config, mock_personas_dir)
    app.active_tab = "chat"
    assert snap_compare(app, terminal_size=(80, 30))


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
