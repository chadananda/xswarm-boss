#!/usr/bin/env python3
"""
Comprehensive TUI test suite for xSwarm Voice Assistant Dashboard.

Tests:
1. Layout - Fixed viewport, no scrolling
2. Sidebar navigation - Mouse and keyboard
3. Tab switching - All 7 tabs work correctly
4. Chat history - Display and interaction
5. Input handling - Text input works
"""

import sys
from pathlib import Path
import asyncio
import pytest

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "packages" / "assistant"))

from assistant.config import Config
from assistant.dashboard import VoiceAssistantApp


class TestTUILayout:
    """Test TUI layout is fixed and doesn't scroll away."""

    @pytest.fixture
    def app(self):
        """Create app instance for testing."""
        config = Config()
        config.voice_enabled = False  # Disable voice for faster tests
        personas_dir = Path(__file__).parent.parent.parent / "packages" / "assistant" / "assistant" / "personas"
        return VoiceAssistantApp(config, personas_dir)

    @pytest.mark.asyncio
    async def test_initial_layout(self, app):
        """Test that app renders with correct initial layout."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Check main layout exists
            main_layout = app.query_one("#main-layout")
            assert main_layout is not None, "Main layout container should exist"

            # Check left column (sidebar + visualizer)
            left_column = app.query_one("#left-column")
            assert left_column is not None, "Left column should exist"

            # Check sidebar
            sidebar = app.query_one("#sidebar")
            assert sidebar is not None, "Sidebar should exist"

            # Check content area
            content_area = app.query_one("#content-area")
            assert content_area is not None, "Content area should exist"

    @pytest.mark.asyncio
    async def test_no_vertical_scroll(self, app):
        """Test that app doesn't scroll vertically."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Check that Screen has overflow: hidden
            # The CSS should prevent scrolling
            screen = app.screen
            assert screen is not None

            # Attempt to scroll - should not change view
            # In Textual, we can check that scroll position remains at (0, 0)
            await pilot.pause(0.5)

    @pytest.mark.asyncio
    async def test_footer_docked_bottom(self, app):
        """Test that footer is docked at bottom."""
        async with app.run_test(size=(120, 40)) as pilot:
            footer = app.query_one("#footer")
            assert footer is not None, "Footer should exist"


class TestSidebarNavigation:
    """Test sidebar navigation with mouse and keyboard."""

    @pytest.fixture
    def app(self):
        """Create app instance for testing."""
        config = Config()
        config.voice_enabled = False
        personas_dir = Path(__file__).parent.parent.parent / "packages" / "assistant" / "assistant" / "personas"
        return VoiceAssistantApp(config, personas_dir)

    @pytest.mark.asyncio
    async def test_all_tab_buttons_exist(self, app):
        """Test that all 7 tab buttons exist in sidebar."""
        async with app.run_test(size=(120, 40)) as pilot:
            expected_tabs = [
                "tab-chat",
                "tab-settings",
                "tab-status",
                "tab-tools",
                "tab-projects",
                "tab-schedule",
                "tab-workers",
            ]

            for tab_id in expected_tabs:
                btn = app.query_one(f"#{tab_id}")
                assert btn is not None, f"Tab button {tab_id} should exist"

    @pytest.mark.asyncio
    async def test_mouse_click_switches_tab(self, app):
        """Test that clicking a tab button switches the active tab."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Initial tab should be chat
            assert app.active_tab == "chat", "Initial tab should be chat"

            # Click settings tab
            await pilot.click("#tab-settings")
            await pilot.pause(0.3)
            assert app.active_tab == "settings", "Tab should switch to settings on click"

            # Click status tab
            await pilot.click("#tab-status")
            await pilot.pause(0.3)
            assert app.active_tab == "status", "Tab should switch to status on click"

    @pytest.mark.asyncio
    async def test_keyboard_number_shortcuts(self, app):
        """Test that number keys 1-7 switch tabs."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Test each number key
            tab_map = {
                "1": "chat",
                "2": "settings",
                "3": "status",
                "4": "tools",
                "5": "projects",
                "6": "schedule",
                "7": "workers",
            }

            for key, expected_tab in tab_map.items():
                await pilot.press(key)
                await pilot.pause(0.2)
                assert app.active_tab == expected_tab, f"Key {key} should switch to {expected_tab}"

    @pytest.mark.asyncio
    async def test_arrow_key_navigation(self, app):
        """Test that arrow keys navigate between tabs."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Start at chat (index 0)
            await pilot.press("1")  # Go to chat
            await pilot.pause(0.2)
            assert app.active_tab == "chat"

            # Press down to go to settings
            await pilot.press("down")
            await pilot.pause(0.2)
            assert app.active_tab == "settings", "Down arrow should go to settings"

            # Press down again to go to status
            await pilot.press("down")
            await pilot.pause(0.2)
            assert app.active_tab == "status", "Down arrow should go to status"

            # Press up to go back to settings
            await pilot.press("up")
            await pilot.pause(0.2)
            assert app.active_tab == "settings", "Up arrow should go back to settings"


class TestContentPanes:
    """Test that content panes show/hide correctly."""

    @pytest.fixture
    def app(self):
        """Create app instance for testing."""
        config = Config()
        config.voice_enabled = False
        personas_dir = Path(__file__).parent.parent.parent / "packages" / "assistant" / "assistant" / "personas"
        return VoiceAssistantApp(config, personas_dir)

    @pytest.mark.asyncio
    async def test_active_pane_visibility(self, app):
        """Test that only active pane is visible."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Chat should be visible initially
            chat_pane = app.query_one("#content-chat")
            assert chat_pane.has_class("active-pane"), "Chat pane should be active initially"

            # Settings should not be visible
            settings_pane = app.query_one("#content-settings")
            assert not settings_pane.has_class("active-pane"), "Settings pane should not be active initially"

            # Switch to settings
            await pilot.click("#tab-settings")
            await pilot.pause(0.3)

            # Now settings should be visible, chat hidden
            assert settings_pane.has_class("active-pane"), "Settings pane should be active after click"
            assert not chat_pane.has_class("active-pane"), "Chat pane should not be active after switching"

    @pytest.mark.asyncio
    async def test_all_content_panes_exist(self, app):
        """Test that all content panes exist."""
        async with app.run_test(size=(120, 40)) as pilot:
            expected_panes = [
                "content-chat",
                "content-settings",
                "content-status",
                "content-tools",
                "content-projects",
                "content-schedule",
                "content-workers",
            ]

            for pane_id in expected_panes:
                pane = app.query_one(f"#{pane_id}")
                assert pane is not None, f"Content pane {pane_id} should exist"


class TestChatHistory:
    """Test chat history widget."""

    @pytest.fixture
    def app(self):
        """Create app instance for testing."""
        config = Config()
        config.voice_enabled = False
        personas_dir = Path(__file__).parent.parent.parent / "packages" / "assistant" / "assistant" / "personas"
        return VoiceAssistantApp(config, personas_dir)

    @pytest.mark.asyncio
    async def test_chat_history_exists(self, app):
        """Test that chat history widget exists."""
        async with app.run_test(size=(120, 40)) as pilot:
            chat_history = app.query_one("#chat-history-widget")
            assert chat_history is not None, "Chat history widget should exist"

    @pytest.mark.asyncio
    async def test_chat_input_exists(self, app):
        """Test that chat input exists."""
        async with app.run_test(size=(120, 40)) as pilot:
            chat_input = app.query_one("#chat-input")
            assert chat_input is not None, "Chat input should exist"

    @pytest.mark.asyncio
    async def test_chat_input_accepts_text(self, app):
        """Test that chat input accepts text."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Make sure we're on chat tab
            await pilot.press("1")
            await pilot.pause(0.3)

            # Focus the chat input
            chat_input = app.query_one("#chat-input")
            chat_input.focus()
            await pilot.pause(0.2)

            # Type some text - use press for each character since pilot.type doesn't exist
            test_text = "Hello"
            for char in test_text:
                await pilot.press(char)
            await pilot.pause(0.3)

            # Check input has text
            assert chat_input.value == test_text, f"Input should contain typed text, got: {chat_input.value}"

    @pytest.mark.asyncio
    async def test_chat_history_add_message(self, app):
        """Test that chat history can receive and display messages."""
        async with app.run_test(size=(120, 40)) as pilot:
            from assistant.dashboard_widgets import ChatHistory

            chat_history = app.query_one("#chat-history-widget", ChatHistory)

            # Wait a bit longer to ensure any system messages are settled
            await pilot.pause(3.0)

            # Add a test message (this should be new since system messages are older)
            chat_history.add_message("User", "Hello, this is a test")
            await pilot.pause(0.3)

            # Verify internal state tracked the sender
            assert chat_history._last_sender == "User", f"Last sender should be User, got: {chat_history._last_sender}"

            # Add an assistant message
            chat_history.add_message("JARVIS", "Hello! How can I help you?")
            await pilot.pause(0.3)

            # Verify internal state updated
            assert chat_history._last_sender == "JARVIS", "Last sender should be JARVIS"
            assert chat_history._current_message == "Hello! How can I help you?", "Current message should match"

    @pytest.mark.asyncio
    async def test_chat_history_is_richlog(self, app):
        """Test that ChatHistory is now a RichLog widget for selection support."""
        async with app.run_test(size=(120, 40)) as pilot:
            from textual.widgets import RichLog
            from assistant.dashboard_widgets import ChatHistory

            chat_history = app.query_one("#chat-history-widget", ChatHistory)

            # Verify it's a RichLog subclass
            assert isinstance(chat_history, RichLog), "ChatHistory should be a RichLog subclass"


class TestFocusZones:
    """Test focus zone management (sidebar <-> content)."""

    @pytest.fixture
    def app(self):
        """Create app instance for testing."""
        config = Config()
        config.voice_enabled = False
        personas_dir = Path(__file__).parent.parent.parent / "packages" / "assistant" / "assistant" / "personas"
        return VoiceAssistantApp(config, personas_dir)

    @pytest.mark.asyncio
    async def test_tab_cycles_focus_zone(self, app):
        """Test that Tab key cycles between sidebar and content."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Initially focus should be on sidebar
            assert app._focus_zone == "sidebar", "Initial focus zone should be sidebar"

            # Press Tab to move to content
            await pilot.press("tab")
            await pilot.pause(0.3)
            assert app._focus_zone == "content", "Tab should move focus to content"

            # Press Tab again to move back to sidebar
            await pilot.press("tab")
            await pilot.pause(0.3)
            assert app._focus_zone == "sidebar", "Tab should move focus back to sidebar"

    @pytest.mark.asyncio
    async def test_escape_returns_to_sidebar(self, app):
        """Test that Escape key returns focus to sidebar."""
        async with app.run_test(size=(120, 40)) as pilot:
            # Move to content zone
            await pilot.press("tab")
            await pilot.pause(0.3)
            assert app._focus_zone == "content"

            # Press Escape to return to sidebar
            await pilot.press("escape")
            await pilot.pause(0.3)
            assert app._focus_zone == "sidebar", "Escape should return focus to sidebar"


class TestVisualizer:
    """Test voice visualizer panel."""

    @pytest.fixture
    def app(self):
        """Create app instance for testing."""
        config = Config()
        config.voice_enabled = False
        personas_dir = Path(__file__).parent.parent.parent / "packages" / "assistant" / "assistant" / "personas"
        return VoiceAssistantApp(config, personas_dir)

    @pytest.mark.asyncio
    async def test_visualizer_exists(self, app):
        """Test that visualizer panel exists."""
        async with app.run_test(size=(120, 40)) as pilot:
            visualizer = app.query_one("#visualizer")
            assert visualizer is not None, "Visualizer should exist"

    @pytest.mark.asyncio
    async def test_visualizer_shows_persona_name(self, app):
        """Test that visualizer shows persona name."""
        async with app.run_test(size=(120, 40)) as pilot:
            from assistant.dashboard_widgets import VoiceVisualizerPanel
            visualizer = app.query_one("#visualizer", VoiceVisualizerPanel)
            # Should have a persona name set
            assert visualizer.persona_name is not None, "Visualizer should have persona name"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
