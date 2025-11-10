#!/bin/bash

# Test script to verify terminal cleanup after TUI exit
# This will test multiple exit scenarios

echo "=== Terminal Cleanup Test ==="
echo ""
echo "This script will test the xswarm-boss TUI terminal cleanup"
echo "by verifying the terminal state after quitting."
echo ""
echo "Test scenarios:"
echo "1. Press 'q' to quit"
echo "2. Press 'Esc' to quit"
echo "3. Press 'Ctrl+C' to quit"
echo ""

# Function to test terminal state
test_terminal() {
    local test_name="$1"
    echo "----------------------------------------"
    echo "Test: $test_name"
    echo "----------------------------------------"
    echo "Terminal state BEFORE running TUI:"

    # Check if terminal is in raw mode (should be normal)
    stty -a | grep -q 'icanon' && echo "✓ Canonical mode: ON (normal)" || echo "✗ Canonical mode: OFF (problem)"
    stty -a | grep -q 'echo' && echo "✓ Echo: ON (normal)" || echo "✗ Echo: OFF (problem)"

    echo ""
    echo "Now run xswarm-boss dashboard and quit using: $test_name"
    echo "Press Enter when ready to continue..."
    read

    echo ""
    echo "Terminal state AFTER quitting TUI:"

    # Check terminal state again
    stty -a | grep -q 'icanon' && echo "✓ Canonical mode: ON (restored)" || echo "✗ Canonical mode: OFF (PROBLEM - TERMINAL BROKEN)"
    stty -a | grep -q 'echo' && echo "✓ Echo: ON (restored)" || echo "✗ Echo: OFF (PROBLEM - TERMINAL BROKEN)"

    # Check if cursor is visible (we can't directly test this, but we can ask)
    echo ""
    echo "Visual checks:"
    echo "- Is the cursor visible? (You should see it blinking)"
    echo "- Does typing show characters normally?"
    echo "- Is the terminal prompt displayed correctly?"
    echo ""
}

echo "Press Enter to start testing..."
read

# Note: We can't automate the actual quitting, so we'll just check terminal state
echo ""
echo "Running dashboard in dev mode..."
echo "When the TUI appears:"
echo "  1. First test: Press 'q' to quit"
echo "  2. Then run this script again to test Ctrl+C"
echo ""
echo "After quitting, the terminal should:"
echo "  ✓ Show the cursor"
echo "  ✓ Display typed characters"
echo "  ✓ Have normal line editing"
echo ""

# Show current terminal state
echo "Current terminal state (should be normal):"
stty -a | grep -E 'icanon|echo'
echo ""

echo "Ready to launch xswarm-boss. The executable should be at:"
echo "/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/target/release/xswarm"
echo ""
echo "To test manually:"
echo "  cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss"
echo "  ./target/release/xswarm dashboard"
echo ""
echo "Then quit with 'q', 'Esc', or 'Ctrl+C' and verify terminal is normal."
