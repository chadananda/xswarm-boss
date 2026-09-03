# TUI Comprehensive Test - xSwarm Voice Assistant Dashboard
# Tests: Layout, sidebar navigation, tab switching, keyboard shortcuts
#
# Run with: vhs tests/assistant/tui_test.tape

Output tests/assistant/tui_test.svg
Output tests/assistant/tui_test.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set TypingSpeed 50ms
Set Padding 10

# Start the TUI without voice for faster testing
Type "python -m assistant.main --no-voice --debug"
Enter
Sleep 4s

# Screenshot 1: Initial state - should show Chat tab (default)
Screenshot tests/assistant/screenshots/01_initial_state.png
Sleep 500ms

# Test keyboard navigation - press 2 for Settings
Type "2"
Sleep 1s
Screenshot tests/assistant/screenshots/02_settings_tab.png

# Test keyboard navigation - press 3 for Status
Type "3"
Sleep 1s
Screenshot tests/assistant/screenshots/03_status_tab.png

# Test keyboard navigation - press 4 for Tools
Type "4"
Sleep 1s
Screenshot tests/assistant/screenshots/04_tools_tab.png

# Test keyboard navigation - press 1 to go back to Chat
Type "1"
Sleep 1s
Screenshot tests/assistant/screenshots/05_chat_tab.png

# Test Tab key to move focus to content area
Tab
Sleep 500ms
Screenshot tests/assistant/screenshots/06_content_focus.png

# Type in the chat input
Type "Hello, I am testing the TUI"
Sleep 500ms
Screenshot tests/assistant/screenshots/07_chat_typed.png

# Submit the message
Enter
Sleep 1s
Screenshot tests/assistant/screenshots/08_chat_submitted.png

# Exit the app
Ctrl+c
Sleep 1s
