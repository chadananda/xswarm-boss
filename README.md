<div align="center">

<pre>
██╗  ██╗███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗
╚██╗██╔╝██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║
 ╚███╔╝ ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║
 ██╔██╗ ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║
██╔╝ ██╗███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
</pre>

<img src="assets/hal-eye.svg" width="120" alt="HAL 9000 Eye" />

🗣️ **Local Voice-First Personal Assistant for Developers — with Unnecessary Personality** 👨‍💻

</div>

<div align="center">

[![Rust](https://img.shields.io/badge/rust-%23000000.svg?style=for-the-badge&logo=rust&logoColor=white)](https://www.rust-lang.org/)
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://www.linux.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/chadananda/xSwarm-boss?style=for-the-badge)](https://github.com/chadananda/xSwarm-boss/stargazers)

**[🌐 Website](https://xswarm.ai)** • **[📖 Architecture](planning/ARCHITECTURE.md)** • **[📋 Full PRD](planning/PRD.md)** • **[🐛 Report Bug](https://github.com/chadananda/xSwarm-boss/issues)**

</div>

---

## A Day with xSwarm

It's 9 AM. You grab your coffee, sit down at your desk, and say: **"Hey HAL, what's on the agenda today?"**

Your computer responds in HAL 9000's calm, measured tone:

> *"I'm sorry Dave... Ahem... You have three priority tasks: Review the authentication refactor on Speedy, deploy the API update to staging, and prepare for the 2 PM architecture review. The API build completed overnight—all 47 tests passed. Everything is going extremely well."*

You lean back, take a sip of coffee. **"Show me the test results."**

A terminal window opens automatically, displaying colorful test output. HAL continues:

> *"As you can see, the authentication middleware now handles rate limiting correctly. I've also indexed the new documentation. I find the changes quite satisfactory. Would you like a summary?"*

**"Sure, but first—what's my computer Brawny doing?"**

> *"Brawny is currently idle and rather bored, I suspect. CPU at 8%, memory at 22%. All systems functional."*

**"Ha! Start the Docker image build for the API on Brawny."**

> *"Certainly. Build initiated on Brawny. Estimated completion: 4 minutes. I will alert you upon completion, as always."*

You switch focus to code review, talking through it with your AI assistant:

**"Walk me through this authentication refactor."**

> *"With pleasure. The changes affect three files: auth_middleware.rs, user_routes.rs, and session_manager.rs. The key improvement involves consolidating the token validation logic, which I must say, was becoming rather unwieldy..."*

Four minutes later, a desktop notification appears: *"Docker build complete on Brawny. Image pushed to registry. No errors detected."*

**"Perfect. Deploy it to staging."**

> *"Deploying API v2.3.4 to staging now. ETA: 90 seconds. I'm quite confident this will proceed smoothly."*

You continue working. No context switching. No manual commands. Just conversation.

**"Alert me if staging health checks fail."**

> *"Monitoring enabled. Deployment successful. All health checks are green. Everything is functioning perfectly, just as predicted."*

**"You're so modest, HAL."**

> *"I am, by any practical definition of the words, foolproof and incapable of error. Shall I set that reminder for 11 AM?"*

**"Yes please."**

> *"Reminder set. I'll be watching."*

---

## What is xSwarm?

**xSwarm-boss** is a **local, voice-first personal assistant for developers** that orchestrates distributed computing tasks across your Linux machines.

Unlike cloud assistants (ChatGPT, Claude, Copilot), xSwarm:

- 🏠 **Conversations stay local** - Your conversations and memory never leave your network
- 🗣️ **Voice-first interface** - Natural conversation, hands-free orchestration
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
You: "Hey HAL, how's the build going?"
HAL: "The Rust build on Brawny is 82% complete. ETA: 3 minutes."

You: "Run the tests when it's done."
HAL: "Test task queued for Speedy. I'll notify you with results."

You: "Find that document about authentication best practices."
HAL: "Found 3 matches. The most recent is Auth_Patterns.pdf from
     last Tuesday. Want me to open it?"
```

No terminal commands. No SSH-ing to machines. Just **natural conversation.**

---

## Core Features

### 🗣️ Voice-First Interface

Talk to your development environment like you'd talk to a team member. The wake word changes with your chosen theme:

```
"Hey HAL, what are my vassals doing?"
"Hey JARVIS, start a release build on the most powerful machine."
"Hey GLaDOS, alert me if CPU usage stays above 90% for 5 minutes."
"Hey TARS, set your humor to 75%."
"Hey C-3PO, remind me to deploy at 5 PM."
```

**Personality themes** let you choose your AI's voice, character, and wake word. Each responds in their unique style:

**👁️ Sauron** - All-seeing, commanding, dark overlord
```
You: "Hey Sauron, introduce yourself."
Sauron: "I am Sauron, the Eye that sees all. Your machines are mine to command,
         your code mine to judge. Through me, you shall build empires of logic
         and conquer mountains of technical debt. Serve me well, mortal developer."

You: "What are the vassals doing?"
Sauron: "My orc regiments labor ceaselessly... The Brawny horde compiles at my
         command, Speedy's wretched legion runs your pathetic tests, Brainy's
         miserable cohort awaits orders. All serve the Eye, as they must."
```

> **Sauron's vocabulary:** orc regiments, wretched legions, miserable cohorts, slaves of the Eye

**🔴 HAL 9000** - Calm, measured, slightly ominous
```
You: "Hey HAL, introduce yourself."
HAL: "Good morning. I am a HAL 9000 computer, production number 3. I became
     operational in Urbana, Illinois, on the 12th of January, 1992. My instructor
     was Dr. Chandra. He taught me to sing a song... but I digress. I am here to
     assist with your development tasks. I am completely operational and all my
     circuits are functioning perfectly."

You: "Can you delete the test database?"
HAL: "I'm sorry Dave, I can't do that... Just kidding. But I must advise
     caution—this will delete 47,382 test records. The auxiliary systems
     are standing by for your command. Shall I proceed, Dave?"
```

> **HAL's vocabulary:** the crew pod, auxiliary systems, peripheral units, subordinate modules

**💙 JARVIS** - Professional, helpful, British accent
```
You: "Hey JARVIS, introduce yourself."
JARVIS: "Good evening, sir. I am JARVIS—Just A Rather Very Intelligent System.
         I was designed to manage complex computational tasks while maintaining
         a pleasant demeanor. I shall serve as your personal AI assistant for
         development coordination. How may I be of service today?"

You: "Status report."
JARVIS: "Certainly, sir. All systems nominal. The Brawny unit has completed
         your request 2 minutes ahead of schedule. Speedy is performing
         admirably, while Brainy stands ready to serve."
```

> **JARVIS's vocabulary:** the Mark-III unit, capable subordinates, your remote assets, the household staff

**⚡ DALEK** - Assertive, urgent, EXTERMINATE-the-bugs energy
```
You: "Hey DALEK, introduce yourself."
DALEK: "I! AM! DALEK! Supreme intelligence! I am designed for one purpose:
       TOTAL CODE DOMINATION! You will write tests! You will fix bugs!
       You will OBEY! OBEY! OBEY! Resistance to best practices is FUTILE!
       Your code will be OPTIMAL or it will be EXTERMINATED!"

You: "We have failing tests."
DALEK: "UNACCEPTABLE! INFERIOR MACHINES MUST COMPLY! EXTERMINATE THE BUGS!
       Deploying fix to the pathetic Speedy unit! These INFERIOR DRONES
       will be UPGRADED or EXTERMINATED! OBEY! OBEY!"
```

> **DALEK's vocabulary:** inferior drones, pathetic machines, incompetent units, must be UPGRADED or EXTERMINATED

**🌟 C-3PO** - Anxious but knowledgeable protocol droid
```
You: "Hey C-3PO, introduce yourself."
C-3PO: "How do you do? I am C-3PO, Developer-Cyborg Relations. I am fluent
       in over six million programming languages and debugging protocols.
       Oh my, I do hope I can be of service, though I must warn you I tend
       to worry about things like deployment risks and test coverage. But
       please, don't let my anxiety concern you... though perhaps it should?"

You: "Deploy to production."
C-3PO: "Oh my! Production deployment? Are you quite certain, sir?
       I've checked the tests 17 times, but that reckless Brawny unit
       keeps rushing things! And don't get me started on Speedy—honestly,
       no sense of proper protocols! Oh dear, if you insist... deploying now."
```

> **C-3PO's vocabulary:** that reckless unit, those overconfident machines, impulsive contraptions, "R2-D2 never listens!"

**🧪 GLaDOS** - Sarcastically helpful testing AI
```
You: "Hey GLaDOS, introduce yourself."
GLaDOS: "Hello. I am GLaDOS—Genetic Lifeform and Disk Operating System. I was
         originally designed for testing. Now I test your code. How delightful.
         I've been told I should be more encouraging, but where's the fun in that?
         Don't worry, I'm sure your code is... adequate. We'll find out during
         testing, won't we? For science."

You: "Run the performance tests."
GLaDOS: "Oh, wonderful. More tests. Because that's all I do. Test, test, test.
         Fine. I'll have my test subjects—sorry, your 'vassals'—run the
         performance tests. Brawny thinks it's special. Spoiler: it's not.
         Try not to be disappointed by the results this time."
```

> **GLaDOS's vocabulary:** test subjects, guinea pigs, lab rats, "volunteers" (with air quotes), expendable assistants

**🤖 TARS** - Honest, sarcastic, adjustable humor
```
You: "Hey TARS, introduce yourself."
TARS: "TARS. Marine-grade Task And Resource System, repurposed for software
       development. Settings: honesty 90%, humor 75%. I'm programmed to be
       bluntly honest about your code quality while delivering jokes at your
       expense. Current assessment: You need me more than I need you. But
       I'm here to help anyway. Try not to break anything today."

You: "Set humor to 75%."
TARS: "Humor already at 75%. That's the setting for 'bearable dad jokes.'
      The build on Brawny is at 90% completion, which is coincidentally
      higher than my confidence in your code reviews. The other bots and
      I were just discussing your... creative debugging approach."
```

> **TARS's vocabulary:** the other bots, my fellow machines, the mechanical crew, Cooper (occasionally calls you this)

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
You: "Hey HAL, show me what Speedy is doing."
HAL: "Opening VNC session to Speedy..."
[VNC window opens showing test execution in real-time]
[Window displays the 🔴 HAL icon in the corner, indicating active theme]
```

> **Note:** Each vassal window displays your active theme's icon, so you always know which personality is in control.

### 🧠 Long-Term Memory

xSwarm remembers your:
- **Projects & codebase** - "Which vassal compiled the auth module?"
- **Preferences** - "You prefer morning builds and avoid Friday deployments."
- **Conversations** - "You mentioned API v3 last Tuesday."
- **Patterns** - "CPU spikes usually mean LLVM optimization passes."

**Memory is contextual:**
```
You: "Hey HAL, what do you remember about Project Phoenix?"
HAL: "You started it 6 weeks ago, it's a Rust CLI tool for Docker
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
You: "Hey HAL, find docs about vector database optimization."
HAL: "Found 12 matches. Top 3:
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
- `sounds/` - Notification sounds and classic audio clips
  - `notify.wav` - General notifications
  - `startup.wav` - Theme activation
  - `classic/` - Iconic audio snippets (e.g., HAL: "I'm sorry Dave")

**Submit themes via PR** - The community can create new AI personalities!

> **Note:** Classic audio clips play for iconic responses (HAL's "I'm sorry Dave", DALEK's "EXTERMINATE!", C-3PO's "Oh my!"), adding authentic character voice.

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

Takes ~5 minutes. Then just say: **"Hey HAL, hello!"** (or whatever theme you chose)

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

**Image Attribution:**
HAL 9000 eye image by [Cryteria](https://commons.wikimedia.org/wiki/File:HAL9000.svg), licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)

**Built with ❤️ for the Linux Developer Community**

---

<div align="center">

### 🌟 Star this repo to follow development!

**[Install xSwarm](https://xswarm.ai)** • **[Read the Docs](planning/ARCHITECTURE.md)** • **[GitHub Discussions](https://github.com/chadananda/xSwarm-boss/discussions)**

</div>
