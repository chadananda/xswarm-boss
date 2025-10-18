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
- **jarvis** 💙 - Sophisticated British butler AI (Iron Man)
- **dalek** 🤖 - Aggressive cyborg extermination units (Doctor Who)
- **c3po** 🤖 - Anxious protocol droid concerned about odds (Star Wars)
- **glados** 🔬 - Passive-aggressive science AI obsessed with testing (Portal)
- **tars** ◼️ - Honest, witty robot with configurable humor settings (Interstellar)
- **marvin** 😔 - Depressed paranoid android with massive intellect (Hitchhiker's Guide)
- **kitt** 🚗 - Professional AI car, technically proficient and protective (Knight Rider)

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
