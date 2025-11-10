"""
Snapshot tests for Chat Panel.

These tests use pytest-textual-snapshot to capture visual snapshots of the
chat panel at different states and terminal sizes. Tests run in headless
mode (no terminal corruption).

Run tests: pytest tests/test_chat_panel_snapshots.py
Update baselines: pytest tests/test_chat_panel_snapshots.py --snapshot-update
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.widgets.panels.chat_panel import ChatPanel
from textual.app import App, ComposeResult


class ChatTestApp(App):
    """Test app that displays a single ChatPanel."""

    def __init__(self, messages=None):
        super().__init__()
        self.messages = messages or []

    def compose(self) -> ComposeResult:
        chat = ChatPanel()
        for role, content in self.messages:
            chat.add_message(role, content)
        yield chat


class TestChatPanelSnapshots:
    """Test chat panel visual output with snapshots."""

    def test_chat_panel_empty(self, snap_compare):
        """Test empty chat panel."""
        assert snap_compare(ChatTestApp(), terminal_size=(80, 30))

    def test_chat_panel_single_user_message(self, snap_compare):
        """Test chat panel with a single user message."""
        messages = [("user", "Hello, assistant!")]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))

    def test_chat_panel_single_assistant_message(self, snap_compare):
        """Test chat panel with a single assistant message."""
        messages = [("assistant", "Hello! How can I help you today?")]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))

    def test_chat_panel_conversation(self, snap_compare):
        """Test chat panel with a full conversation."""
        messages = [
            ("user", "What's the weather like?"),
            ("assistant", "I don't have access to real-time weather data, but I can help you find weather information."),
            ("user", "That's okay, thanks!"),
            ("assistant", "You're welcome! Is there anything else I can help with?"),
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))

    def test_chat_panel_long_message(self, snap_compare):
        """Test chat panel with a long message that wraps."""
        messages = [
            ("user", "Can you explain what quantum computing is and how it differs from classical computing in a detailed way?"),
            ("assistant", "Quantum computing is a type of computation that harnesses quantum mechanical phenomena like superposition and entanglement. Unlike classical computers that use bits (0 or 1), quantum computers use qubits that can exist in multiple states simultaneously."),
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))

    def test_chat_panel_many_messages(self, snap_compare):
        """Test chat panel with many messages (scrolling)."""
        messages = [
            ("user", f"Message {i}") for i in range(15)
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))

    @pytest.mark.parametrize(
        "size,size_name",
        [
            ((40, 15), "small"),
            ((80, 30), "standard"),
            ((120, 40), "large"),
        ],
    )
    def test_chat_panel_responsive_sizes(self, snap_compare, size, size_name):
        """Test chat panel at multiple terminal sizes."""
        messages = [
            ("user", "Hello!"),
            ("assistant", "Hi there! How can I help you?"),
            ("user", "Just testing the UI."),
            ("assistant", "Looks great! The chat panel is responsive."),
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=size)

    def test_chat_panel_narrow_terminal(self, snap_compare):
        """Test chat panel in a very narrow terminal (word wrapping)."""
        messages = [
            ("user", "This is a longer message that will need to wrap in a narrow terminal window."),
            ("assistant", "I understand. The chat panel should handle narrow terminals gracefully with proper word wrapping."),
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=(40, 20))

    def test_chat_panel_code_block(self, snap_compare):
        """Test chat panel with code-like content."""
        messages = [
            ("user", "Can you show me a Python function?"),
            ("assistant", "Sure! Here's an example:\n\ndef hello(name):\n    return f'Hello, {name}!'\n\nprint(hello('World'))"),
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))

    def test_chat_panel_special_characters(self, snap_compare):
        """Test chat panel with special characters and emojis."""
        messages = [
            ("user", "Hello! 👋"),
            ("assistant", "Hi! 😊 How can I help you today?"),
            ("user", "Testing special chars: @#$%^&*()"),
            ("assistant", "All characters render correctly! ✓"),
        ]
        assert snap_compare(ChatTestApp(messages), terminal_size=(80, 30))


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--snapshot-update"])
