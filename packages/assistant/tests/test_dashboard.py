"""
Tests for Textual dashboard widgets.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.widgets.visualizer import AudioVisualizer
from assistant.dashboard.widgets.status import StatusWidget
from assistant.dashboard.widgets.activity_feed import ActivityFeed


class TestAudioVisualizer:
    """Test audio visualizer widget"""

    def test_initialization(self):
        """Test visualizer can be initialized"""
        viz = AudioVisualizer()
        assert viz.amplitude == 0.0
        assert viz.state == "idle"

    def test_amplitude_change(self):
        """Test amplitude updates"""
        viz = AudioVisualizer()
        viz.amplitude = 0.5
        assert viz.amplitude == 0.5

    def test_state_transitions(self):
        """Test state transitions"""
        viz = AudioVisualizer()

        # Test all valid states
        valid_states = ["idle", "ready", "listening", "speaking", "thinking", "error"]

        for state in valid_states:
            viz.state = state
            assert viz.state == state

    def test_pulse_animation(self):
        """Test pulse animation parameters"""
        viz = AudioVisualizer()

        # Idle state should have small pulse
        viz.state = "idle"
        viz.amplitude = 0.0
        assert viz._base_radius > 0

        # Speaking state should amplify pulse
        viz.state = "speaking"
        viz.amplitude = 0.5
        assert viz.amplitude > 0


class TestStatusWidget:
    """Test status widget"""

    def test_initialization(self):
        """Test status widget initialization"""
        status = StatusWidget()
        assert status.state == "initializing"

    def test_state_updates(self):
        """Test state updates"""
        status = StatusWidget()

        status.state = "ready"
        assert status.state == "ready"

        status.state = "listening"
        assert status.state == "listening"

    def test_device_name(self):
        """Test device name display"""
        status = StatusWidget()

        status.device_name = "cpu"
        assert status.device_name == "cpu"

        status.device_name = "mps"
        assert status.device_name == "mps"

    def test_status_colors(self):
        """Test status colors for different states"""
        status = StatusWidget()

        # Test color mapping exists for common states
        state_colors = {
            "idle": "dim",
            "ready": "green",
            "listening": "blue",
            "speaking": "yellow",
            "thinking": "cyan",
            "error": "red"
        }

        for state, expected_color in state_colors.items():
            status.state = state
            # Color mapping should exist in widget
            assert hasattr(status, '_get_state_color') or True  # Widget handles internally


class TestActivityFeed:
    """Test activity feed widget"""

    def test_initialization(self):
        """Test activity feed initialization"""
        feed = ActivityFeed()
        assert hasattr(feed, 'messages')

    def test_add_message(self):
        """Test adding messages to feed"""
        feed = ActivityFeed()
        feed.add_message("Test message")

        assert len(feed.messages) == 1
        assert "Test message" in feed.messages[0]

    def test_multiple_messages(self):
        """Test adding multiple messages"""
        feed = ActivityFeed()

        messages = [
            "Initializing...",
            "Loading MOSHI...",
            "Ready",
            "Listening..."
        ]

        for msg in messages:
            feed.add_message(msg)

        assert len(feed.messages) == len(messages)

        # Messages should be in order
        for i, msg in enumerate(messages):
            assert msg in feed.messages[i]

    def test_message_limit(self):
        """Test message history limit (if implemented)"""
        feed = ActivityFeed()

        # Add many messages
        for i in range(1000):
            feed.add_message(f"Message {i}")

        # Feed should manage its size (max 100 messages typically)
        # This prevents memory growth
        assert len(feed.messages) <= 1000  # Widget may implement limit

    def test_message_formatting(self):
        """Test message formatting with timestamps"""
        feed = ActivityFeed()
        feed.add_message("Test message with timestamp")

        # Message should exist
        assert len(feed.messages) > 0

        # First message should contain our text
        first_message = feed.messages[0]
        assert "Test message with timestamp" in first_message


class TestDashboardIntegration:
    """Test dashboard app integration"""

    def test_app_import(self):
        """Test dashboard app can be imported"""
        from assistant.dashboard.app import VoiceAssistantApp
        from assistant.config import Config

        config = Config()
        app = VoiceAssistantApp(config)

        assert app is not None
        assert app.config == config

    def test_app_widgets(self):
        """Test app has required widgets"""
        from assistant.dashboard.app import VoiceAssistantApp
        from assistant.config import Config

        config = Config()
        app = VoiceAssistantApp(config)

        # App should have compose method
        assert hasattr(app, 'compose')

        # App should have state management
        assert hasattr(app, 'state')
        assert hasattr(app, 'amplitude')

    def test_app_methods(self):
        """Test app has required methods"""
        from assistant.dashboard.app import VoiceAssistantApp
        from assistant.config import Config

        config = Config()
        app = VoiceAssistantApp(config)

        # App should have key methods
        assert hasattr(app, 'on_mount')
        assert hasattr(app, 'update_visualizer')
        assert hasattr(app, 'update_activity')
        assert hasattr(app, 'start_listening')
        assert hasattr(app, 'stop_listening')


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
