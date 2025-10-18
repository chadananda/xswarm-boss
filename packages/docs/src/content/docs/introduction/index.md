---
title: What is xSwarm-boss?
description: Introduction to xSwarm-boss AI orchestration layer
---

## The Problem

Modern AI coding assistants (Claude Code, Cursor, Aider) have revolutionized development. You can now actively work on 10+ complex projects simultaneously. But this creates a new problem:

**Coordination Chaos**
- Which AI is working on which project?
- When you update library A, which projects B, C, D need updating?
- How do you manage resources across multiple machines?
- How do you prevent secrets from leaking between projects?

## The Solution: xSwarm-boss

**xSwarm-boss is an AI orchestration layer** that manages your other AIs like a CTO manages development teams.

### What It Does

1. **Coordinates AI Agents** - Manage Claude Code, Cursor, Aider instances
2. **Tracks Dependencies** - Knows which projects depend on each other
3. **Allocates Resources** - Distributes work across your machines
4. **Maintains Knowledge** - Unified semantic search across all projects
5. **Ensures Security** - Secret detection and memory purging
6. **Provides Voice Control** - Natural language commands with personality

### Architecture

```
You (Developer)
    ↓ Voice: "Update auth library"
xSwarm-boss (Overlord AI)
    ↓ Coordinates
AI Agents (Claude Code, Cursor, Aider)
    ↓ Work on
Your Projects (across multiple machines)
```

## Key Concepts

### Overlord & Vassals
- **Overlord**: The main xSwarm-boss instance (your workstation)
- **Vassals**: Worker machines in your homelab
- Communication via mTLS WebSocket

### AI Agent Coordination
xSwarm doesn't replace your AI assistants - it orchestrates them:
- Spawns Claude Code on the right machine
- Monitors progress across all agents
- Coordinates updates across project dependencies

### Personality Themes
Choose how xSwarm communicates:
- **HAL 9000** 🔴 - Calm, rational, mission-focused
- **Sauron** 👁️ - Commanding, imperial, dark
- **JARVIS** 💙 - Sophisticated butler (coming soon)
- ...and more

## Next Steps

- [Why xSwarm?](/introduction/why-xswarm/) - Deeper dive into the problem
- [Key Features](/introduction/key-features/) - What makes xSwarm unique
- [Get Started](/getting-started/) - Install and configure
