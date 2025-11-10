#!/bin/bash
# Safe TUI runner that ensures terminal cleanup

# Enable terminal reset on exit
trap 'printf "\033[?1000l\033[?1003l\033[?1006l\033[?1015l\033[?1049l\033[?25h\033[?1004l"' EXIT

# Run the TUI app
python -m assistant.main "$@"
