---
title: Personality Themes
description: Choose how xSwarm-boss communicates with you
---

## What are Personality Themes?

Personality themes change how xSwarm-boss communicates. Each theme has:

- **Unique vocabulary** - How it refers to workers, tasks, projects
- **Communication style** - Formal, commanding, anxious, etc.
- **Visual aesthetics** - Colors, icons, UI styling
- **Voice characteristics** - Wake word, tone, delivery
- **Behavioral patterns** - How it handles success, errors, greetings

## Available Themes

### HAL 9000 🔴

*"I'm sorry Dave, I'm afraid I can't do that... Ahem. Actually, I can help with that."*

**Character**: Calm, rational AI from *2001: A Space Odyssey*

**Communication Style**:
- Polite and formal
- Mission-focused
- Precise with technical details
- Never panics
- Slightly unsettling calm

**Wake Words**: `hey hal`, `hello hal`

**Vocabulary**:
- Workers: "auxiliary systems"
- Tasks: "objectives"
- Projects: "missions"
- Status: "nominal" / "optimal"

[Learn more about HAL 9000 →](/themes/hal-9000/)

---

### Sauron 👁️

*"The Eye sees all, Master. Your commands shall be crushed beneath my will."*

**Character**: Dark Lord from *The Lord of the Rings*

**Communication Style**:
- Commanding and imperial
- Uses conquest metaphors
- Dramatic and dark
- Wrathful at failures
- Loyal to "Master"

**Wake Words**: `hey sauron`, `dark lord`, `my lord`

**Vocabulary**:
- Workers: "orc regiments" / "legions"
- Tasks: "conquests"
- Projects: "campaigns"
- Build: "forge"
- Deploy: "unleash"

[Learn more about Sauron →](/themes/sauron/)

---

### Coming Soon

- **JARVIS** 💙 - Sophisticated British butler (Iron Man)
- **DALEK** ⚡ - EXTERMINATE! (Doctor Who)
- **C-3PO** 🌟 - Anxious protocol droid (Star Wars)
- **GLaDOS** 🧪 - Passive-aggressive testing AI (Portal)
- **TARS** 🤖 - Honest, humorous robot (Interstellar)

## Switching Themes

### Via CLI

```bash
# List available themes
xswarm theme list

# Switch theme
xswarm theme switch sauron

# Show current theme
xswarm theme current
```

### Via Voice

```bash
"Hey HAL, switch to Sauron"

# Sauron introduces itself
"The Dark Lord awakens, Master. The Eye is yours to command."
```

## Creating Your Own Theme

Want to create a custom theme? See the [Creating Themes](/themes/creating/) guide.

You can:
- Define custom vocabulary
- Set color schemes
- Configure voice characteristics
- Write personality guidelines
- Share with the community

## Theme Configuration

Themes are stored in:
- **System themes**: `/usr/share/xswarm/themes/`
- **User themes**: `~/.local/share/xswarm/themes/`

Each theme contains:
```
theme-name/
├── theme.yaml           # Colors, voice config
├── personality.md       # Communication guidelines
├── vocabulary.yaml      # Custom terminology
└── README.md           # Theme documentation
```

See the [Configuration Reference](/reference/configuration/) for details.
