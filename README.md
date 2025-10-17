```
██╗  ██╗███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
╚██╗██╔╝██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
 ╚███╔╝ ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
 ██╔██╗ ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
██╔╝ ██╗███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
                    ━━━━━━━━━━━━━━━━━━━━━━━
           🗣️ Local Voice-First Personal Assistant
                     for Developers 👨‍💻
```

<div align="center">

[![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://www.linux.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/chadananda/xSwarm-boss?style=for-the-badge)](https://github.com/chadananda/xSwarm-boss/stargazers)

**[🌐 Website](https://xswarm.ai)** • **[📖 Architecture](ARCHITECTURE.md)** • **[📋 Full PRD](PRD.md)** • **[🐛 Report Bug](https://github.com/chadananda/xSwarm-boss/issues)**

</div>

---

## A Day with xSwarm

It's 9 AM. You grab your coffee, sit down at your desk, and say: **"Hey Overlord, what's on the agenda today?"**

Your computer responds in HAL 9000's calm, measured tone:

> *"Good morning. You have three priority tasks: Review the authentication refactor on Speedy, deploy the API update to staging, and prepare for the 2 PM architecture review. The API build completed overnight—all 47 tests passed. Shall I walk you through the changes?"*

You lean back, take a sip of coffee. **"Yes, show me the test results."**

A terminal window opens automatically, displaying colorful test output. HAL continues:

> *"The authentication middleware now handles rate limiting correctly. I've also indexed the new documentation—would you like me to summarize the key changes?"*

**"Sure, but first—what's Brawny doing?"**

> *"Brawny is currently idle. CPU at 8%, memory at 22%. Ready for tasks."*

**"Great. Start the Docker image build for the API on Brawny."**

> *"Build initiated on Brawny. Estimated completion: 4 minutes. I'll notify you when it's ready."*

You switch focus to code review, talking through it with your AI assistant:

**"Walk me through this authentication refactor."**

> *"Certainly. The changes affect three files: auth_middleware.rs, user_routes.rs, and session_manager.rs. The key improvement is..."*

Four minutes later, a desktop notification appears: *"Docker build complete on Brawny. Image pushed to registry."*

**"Deploy it to staging."**

> *"Deploying API v2.3.4 to staging. ETA: 90 seconds."*

You continue working. No context switching. No manual commands. Just conversation.

**"Alert me if staging health checks fail."**

> *"Monitoring enabled. Deployment successful. All health checks green."*

**"Awesome. Remind me to check staging at 11 AM."**

> *"Reminder set."*

---

## What is xSwarm?

**xSwarm-boss** is a **local, voice-first personal assistant for developers** that orchestrates distributed computing tasks across your Linux machines.

Unlike cloud assistants (ChatGPT, Claude, Copilot), xSwarm:

- 🏠 **Runs completely local** - Your code never leaves your network
- 🗣️ **Voice-first interface** - Natural conversation, hands-free coding
- 👁️ **Multi-machine awareness** - Coordinates your homelab/build farm
- 🧠 **Long-term memory** - Remembers your projects, preferences, and patterns
- 🔒 **Secure by design** - API keys isolated, conversations PII-filtered
- 🎨 **Themeable personalities** - HAL, JARVIS, DALEK, C-3PO, GLaDOS, TARS

Think **JARVIS meets your homelab**—an AI that knows your entire development environment and speaks to you like a colleague.

---

## Why xSwarm?

### The Problem

As developers, we constantly context-switch between:
- Terminal windows for builds, tests, deployments
- Browser tabs for documentation, logs, monitoring
- Chat apps for team coordination
- Note-taking apps for TODOs and reminders
- Multiple machines (laptop, desktop, build servers)

Each switch costs cognitive load. Each command requires manual typing. Each machine operates in isolation.

### The Solution

**One voice-controlled AI that coordinates everything.**

```
You: "How's the build going?"
Overlord: "The Rust build on Brawny is 82% complete. ETA: 3 minutes."

You: "Run the tests when it's done."
Overlord: "Test task queued for Speedy. I'll notify you with results."

You: "Find that document about authentication best practices."
Overlord: "Found 3 matches. The most recent is Auth_Patterns.pdf from
         last Tuesday. Want me to open it?"
```

No terminal commands. No SSH-ing to machines. Just **natural conversation.**

---

## Core Features

### 🗣️ Voice-First Interface

Talk to your development environment like you'd talk to a team member.

```
"Hey Overlord, what are my vassals doing?"
"Start a release build on the most powerful machine."
"Alert me if CPU usage stays above 90% for 5 minutes."
"Switch your personality to JARVIS."
"Remind me to deploy at 5 PM."
```

**Personality themes** let you choose your AI's voice and character:
- 🔴 **HAL 9000** - Calm, measured, slightly ominous
- 💙 **JARVIS** - Professional, helpful, British accent
- ⚡ **DALEK** - Assertive, urgent, EXTERMINATE-the-bugs energy
- 🌟 **C-3PO** - Anxious but knowledgeable protocol droid
- 🧪 **GLaDOS** - Sarcastically helpful testing AI
- 🤖 **TARS** - Honest, sarcastic, adjustable humor settings

### 👁️ Multi-Machine Orchestration

xSwarm treats your machines as a coordinated team:

- **Overlord Machine** - Your main workstation with the voice interface
- **Vassal Machines** - Build servers, test runners, GPU boxes, etc.

The Overlord intelligently routes tasks:
```
Heavy Rust build? → Brawny (16-core builder)
Integration tests? → Speedy (fast SSD, lots of RAM)
Machine learning? → Brainy (GPU-equipped)
```

**Real-time monitoring:**
```
You: "Show me what Speedy is doing."
Overlord: "Opening VNC session to Speedy..."
[VNC window shows test execution in real-time]
```

### 🧠 Long-Term Memory

xSwarm remembers your:
- **Projects & codebase** - "Which vassal compiled the auth module?"
- **Preferences** - "You prefer morning builds and avoid Friday deployments."
- **Conversations** - "You mentioned API v3 last Tuesday."
- **Patterns** - "CPU spikes usually mean LLVM optimization passes."

**Memory is contextual:**
```
You: "What do you remember about Project Phoenix?"
Overlord: "You started it 6 weeks ago, it's a Rust CLI tool for Docker
         management. Currently 67% complete with 12 failing tests on
         Speedy. Last activity: yesterday at 4 PM."
```

### 🔍 System-Wide Semantic Search

xSwarm automatically indexes all your documents:
- PDFs in `~/Documents`
- Notes in `~/Dropbox`
- Code in `~/Projects`
- Markdown files everywhere

**Voice search:**
```
You: "Find docs about vector database optimization."
Overlord: "Found 12 matches. Top 3:
         1. Vector_DB_Performance.pdf (last month)
         2. Notes_Meilisearch_Setup.md (last week)
         3. HNSW_Algorithm_Paper.pdf (yesterday)"
```

### 🔒 Security by Design

Your secrets stay secret:

- **MCP Isolation** - API keys stored in isolated processes
- **PII Filtering** - Conversations automatically scrubbed before storage
- **Local-first** - No cloud dependency, full privacy
- **Audit logs** - Every secret access logged

```
You: "My Anthropic key is sk-ant-xyz123..."
[Stored in memory as]: "My Anthropic key is [REDACTED]"
```

### 🎨 Fully Themeable

Create custom AI personalities with:
- `theme.yaml` - Colors, voice settings
- `personality.md` - Character behavior guide
- `response-examples.md` - Example dialogue
- `toolbar-animation.apng` - Animated status icon
- `sounds/` - Notification sounds

**Submit themes via PR** - The community can create new AI personalities!

---

## Installation

### Quick Install

**Arch Linux / Omarchy:**
```bash
yay -S xswarm-boss
xswarm setup
```

**Ubuntu / Debian:**
```bash
wget https://xswarm.ai/latest.deb
sudo dpkg -i xswarm-boss_*.deb
xswarm setup
```

**Universal (AppImage):**
```bash
wget https://xswarm.ai/xswarm-boss.AppImage
chmod +x xswarm-boss.AppImage
./xswarm-boss.AppImage setup
```

### Setup Wizard

The setup wizard guides you through:

1. **Choose mode:** Overlord (main) or Vassal (worker)
2. **Select AI personality:** HAL, JARVIS, DALEK, etc.
3. **Configure vassals:** Add worker machines on your LAN
4. **Optional API keys:** For remote AI fallback (cloud LLMs)

Takes ~5 minutes. Then just say: **"Hey Overlord, hello!"**

---

## System Requirements

### Overlord (Main Machine)
- **OS:** Linux (any distro)
- **GPU:** 8GB+ VRAM recommended (CPU-only works but slower)
- **RAM:** 32GB minimum, 64GB recommended
- **Storage:** 500GB+ SSD
- **Network:** Gigabit LAN (for vassal coordination)

### Vassals (Worker Machines)
- **OS:** Linux (any distro)
- **GPU:** Not required
- **RAM:** 16GB+ (task-dependent)
- **Storage:** 256GB+ SSD
- **Network:** Gigabit LAN

---

## Roadmap

**Phase 1: Core Foundation** (Q4 2025)
- ✅ Rust orchestrator with Ratatui UI
- ✅ Voice interface (Anthropic/local LLM)
- ✅ Multi-machine WebSocket coordination
- ✅ Basic task routing
- 🚧 Security layer (MCP isolation)
- 🚧 Memory system (4-layer architecture)

**Phase 2: Intelligence** (Q1 2026)
- 🔜 Semantic search (Meilisearch + Docling)
- 🔜 Knowledge graph memory
- 🔜 Advanced task scheduling
- 🔜 VNC vassal monitoring

**Phase 3: Integration** (Q2 2026)
- 🔜 Desktop environment integration (Hyprland/Waybar)
- 🔜 WhatsApp notifications
- 🔜 Email reports
- 🔜 GitHub/GitLab integration

**Phase 4: Community** (Q2 2026)
- 🔜 Theme marketplace
- 🔜 Plugin system
- 🔜 Multi-user support
- 🔜 Web dashboard

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical system design
- **[PRD.md](PRD.md)** - Full product requirements document
- **[Website](https://xswarm.ai)** - Project homepage
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

---

## Community

- **[GitHub Discussions](https://github.com/chadananda/xSwarm-boss/discussions)** - Ask questions, share ideas
- **[Discord](https://discord.gg/xswarm)** - Real-time chat
- **[Issues](https://github.com/chadananda/xSwarm-boss/issues)** - Bug reports and feature requests

**Contributing:**
We welcome contributions! Especially:
- New AI personality themes
- Integration plugins
- Bug fixes and features
- Documentation improvements

---

## Why "xSwarm-boss"?

The name reflects the fantasy theme:
- **Overlord** - Your main AI (the boss)
- **Vassals** - Worker machines (the swarm)
- **x** - Because it's cool (and available on GitHub)

The fantasy terminology makes distributed computing feel less corporate and more like commanding an army of loyal minions. 🧙‍♂️

---

## License

MIT © [Chad Jones](https://github.com/chadananda)

**Built with ❤️ for the Linux Developer Community**

---

<div align="center">

### 🌟 Star this repo to follow development!

**[Install xSwarm](https://xswarm.ai)** • **[Read the Docs](ARCHITECTURE.md)** • **[Join Discord](https://discord.gg/xswarm)**

</div>
