#!/bin/bash
# Fix terminal after TUI app corruption
# Run this in your corrupted terminal: source fix_terminal.sh

# Disable all mouse tracking modes
printf '\033[?1000l'  # Normal mouse tracking
printf '\033[?1002l'  # Button event tracking
printf '\033[?1003l'  # Any event tracking
printf '\033[?1005l'  # UTF-8 mouse mode
printf '\033[?1006l'  # SGR mouse mode
printf '\033[?1015l'  # urxvt mouse mode

# Reset other terminal modes
printf '\033[?25h'    # Show cursor
printf '\033[?1049l'  # Exit alternate screen
printf '\033[?7h'     # Enable auto-wrap
printf '\033[?2004l'  # Disable bracketed paste

# Clear screen and reset
clear

echo "Terminal reset complete!"
echo "Mouse tracking disabled, cursor restored, screen cleared."
