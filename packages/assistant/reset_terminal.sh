#!/bin/bash
# Reset terminal after TUI corruption

# Reset terminal to normal state
reset

# Alternative if reset doesn't work:
# printf "\033c"
# stty sane

echo "Terminal reset complete!"
