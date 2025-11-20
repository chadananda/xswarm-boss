# TUI Tests

This directory contains tests for the **Terminal User Interface** (TUI) dashboard.

## Test Files

- `test_dashboard_e2e.py` - End-to-end tests for dashboard navigation and UI state using Textual Pilot
- `test_dashboard.py` - Unit tests for dashboard app initialization
- `test_chat_panel_snapshots.py` - Snapshot tests for chat panel UI
- `test_theme_switching*.py` - Tests for theme switching functionality
- `test_sidebar_layout.py` - Tests for sidebar layout and rendering
- `test_responsive_comprehensive.py` - Tests for responsive UI behavior
- `test_wake_word_indicator.py` - Tests for wake word visual indicators
- `test_voice_visualizer_snapshots.py` - Snapshot tests for voice visualizer widget

## Running Tests

```bash
# Run all TUI tests
pytest packages/assistant/tests/tui/

# Run specific test file
pytest packages/assistant/tests/tui/test_dashboard_e2e.py -v
```
