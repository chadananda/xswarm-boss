# xSwarm Personality Themes

This directory contains personality themes for xSwarm-boss. Each theme defines colors, voice characteristics, vocabulary, and behavioral patterns for the AI orchestrator.

## Theme Structure

Each theme directory contains:

```
theme-name/
├── theme.yaml           # Colors, UI configuration
├── personality.md       # Personality guide and communication style
├── vocabulary.yaml      # Theme-specific vocabulary and phrases
├── README.md           # Theme documentation
└── assets/
    ├── icon.svg        # Theme icon
    └── audio/          # Voice clips (optional)
```

## Available Themes

- **hal-9000** 🔴 - Calm, rational AI with mission-focused communication (2001: A Space Odyssey)
- **sauron** 👁️ - Dark, commanding overlord with imperious language (Lord of the Rings)
- **jarvis** 💙 - Sophisticated British butler AI (Iron Man) - *Coming soon*
- **dalek** ⚡ - Authoritarian extermination units (Doctor Who) - *Coming soon*
- **c3po** 🌟 - Anxious protocol droid (Star Wars) - *Coming soon*
- **glados** 🧪 - Passive-aggressive testing AI (Portal) - *Coming soon*
- **tars** 🤖 - Honest, humorous robot (Interstellar) - *Coming soon*

## Creating a Theme

See the existing themes for examples. Key components:

### 1. theme.yaml
Define colors, fonts, and UI preferences:

```yaml
name: "Theme Name"
icon: "🎯"
colors:
  primary: "#ff0000"
  secondary: "#00ff00"
  accent: "#0000ff"
wake_word: "hey theme"
```

### 2. personality.md
Describe the personality, communication style, and behavioral patterns:

```markdown
# Theme Name Personality

## Overview
Brief description of the personality...

## Communication Style
- How it speaks
- Tone and demeanor
- Example phrases
```

### 3. vocabulary.yaml
Theme-specific vocabulary:

```yaml
workers:
  singular: "minion"
  plural: "minions"
tasks:
  start: "commence"
  complete: "accomplish"
```

## Switching Themes

```bash
# CLI
xswarm theme switch hal-9000

# Voice
"Hey Sauron, switch to JARVIS"
```

## Contributing Themes

Want to add a new theme? See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on submitting community themes!
