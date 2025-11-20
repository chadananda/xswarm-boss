# Assistant Package

Main voice assistant application with TUI, AI intelligence, and conversation management.

## Structure

- `assistant/` - Application source code
- `pyproject.toml` - Package configuration
- `requirements.txt` - Python dependencies
- `scripts/` - Runtime scripts (model downloads, Twilio server)
- `voice_assistant.egg-info/` - Package metadata

## Installation

```bash
cd packages/tui
pip install -e .
```

## Running

```bash
# TUI
python -m assistant.main

# Voice server
python assistant/scripts/run_twilio_server.py
```

## Note

Tests, docs, examples, and personas are at project root, not in this package.
