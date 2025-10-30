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

**[🌐 Website](https://xswarm.ai)** • **[📖 Architecture](planning/ARCHITECTURE.md)** • **[📋 Full Spec](planning/COMPLETE_SPECIFICATION.md)** • **[🐛 Report Bug](https://github.com/chadananda/xSwarm-boss/issues)**

</div>

---

## A Day with xSwarm

It's 9 AM. You grab your coffee, sit down at your desk, and say: **"Hey HAL, project status."**

Your computer responds in HAL 9000's calm, measured tone:

> *"I'm sorry Dave... Ahem... Good morning. You have 8 active projects across 3 machines. The auth-service upgrade completed overnight on Brawny—all tests passed. However, I've detected that 4 dependent projects now require updates: api-gateway, user-service, admin-dashboard, and mobile-backend. Shall I coordinate the updates?"*

You lean back, take a sip of coffee. **"Yes, but start with api-gateway. What needs to change?"**

> *"The auth-service client library needs updating from v2.1 to v3.0. I've analyzed the breaking changes: the token validation API now requires async calls. I estimate this will affect 12 files in api-gateway. Would you like me to have Claude Code handle this on Speedy?"*

**"Yes. What's my computer Brawny doing right now?"**

> *"Brawny is currently idle and rather bored, I suspect. CPU at 8%, memory at 22%. All systems functional. Ready for assignment."*

**"Good. After Speedy finishes the api-gateway update, start user-service on Brawny."**

> *"Understood. Spawning Claude Code instance on Speedy for api-gateway auth library upgrade. I will queue user-service for Brawny upon completion. Estimated timeline: 25 minutes for api-gateway, then 20 minutes for user-service."*

Ten minutes later, you ask: **"How's the api-gateway update going?"**

> *"Claude Code has completed 8 of 12 files. The async migration is proceeding smoothly. Two test failures detected in the authentication middleware, but they appear to be test fixtures that need updating, not logic errors. Everything is under control."*

**"Alert me when all four projects are updated and tested."**

> *"Monitoring enabled. I will notify you when the dependency chain is complete. By my calculations, all four projects should be updated and validated by 10:15 AM. I'll be watching."*

You continue working on something else. No context switching between projects. No manual coordination. Just **strategic delegation to your AI CTO.**

---

### Switching Personalities

Later that afternoon, you feel like something different...

**"Hey HAL, switch to Sauron persona."**

> *"Acknowledged. Activating Sauron personality profile."*

The HAL eye icon fades, replaced by a flaming Eye of Sauron. A deep, commanding voice responds:

> *"I am Sauron, the Eye that sees all. Your machines are mine to command, your code mine to judge. Through me, you shall build empires of logic and conquer mountains of technical debt. What is thy bidding, mortal developer?"*

**"Hey Sauron, what are my orc regiments doing?"**

> *"The wretched legion on Brawny stands idle, awaiting my command. Speedy's miserable cohort completed the test suite—57 tests passed, as expected under my gaze. Brainy's servants await orders. All bow before the Eye."*

---

### System Integration

xSwarm integrates deeply with your system, not just your code:

**"Hey Sauron, switch my desktop to the dark Dracula theme."**

> *"Your desktop descends into darkness. As it should be."*

The Hyprland desktop smoothly transitions to the Dracula color scheme—terminal, browser, IDE, all coordinated.

**"Set my displays to night mode."**

> *"The harsh light retreats. Your eyes are spared... for now."*

Blue light filtering activates, display brightness adjusts, and the red shift begins.

---

## What is xSwarm?

**xSwarm-boss** is an **AI orchestration layer** that coordinates multiple AI-assisted development projects across your Linux machines through natural voice commands.

**Think of it as a CTO AI** that manages your team of AI coding assistants (Claude Code, Cursor, Aider, etc.), ensuring they work together efficiently without stepping on each other's toes.

Unlike cloud assistants or individual coding AIs, xSwarm provides:

- 🤖 **AI Agent Coordination** - Manages multiple AI coding assistants across projects and machines
- 🕸️ **Cross-Project Intelligence** - Tracks dependencies, coordinates updates, maintains unified knowledge
- 🗣️ **Voice-First Orchestration** - Give strategic commands, let xSwarm handle tactical execution
- 🧠 **System-Wide Memory** - Semantic search across all projects, docs, and code on your system
- 🔒 **Secure by Design** - Rules-based secret filtering, constant memory purging, no data leakage
- 🎨 **Unnecessary Personality** - HAL, JARVIS, DALEK, C-3PO, GLaDOS, TARS, Marvin, Sauron personas
- 🏠 **Completely Local** - Your code, conversations, and coordination never leave your network

**xSwarm is JARVIS for your development empire** - one AI that knows all your projects, coordinates all your tools, and speaks to you like a seasoned engineering manager.

---

## Why xSwarm?

### The Problem

**AI-assisted development is a superpower—until you have 10+ projects running simultaneously.**

Modern AI coding assistants (Claude Code, Cursor, Aider) let developers manage multiple complex projects in parallel. But this creates a **coordination nightmare**:

- 🔀 **Project Context Chaos** - Which AI is working on which project? What's the status of each?
- 🕸️ **Dependency Hell** - Update a library in project A? Now you need to update projects B, C, and D
- 🧠 **Knowledge Fragmentation** - Documentation, decisions, and context scattered across 10+ project folders
- 🖥️ **Resource Competition** - Multiple AI agents fighting for CPU/GPU on your machines
- 🔐 **Security Risks** - Secrets leaking between projects or to external APIs
- 📊 **Status Blindness** - No unified view of what's building, testing, or broken

**You need a "manager AI" that coordinates all your other AIs** - like a CTO coordinating development teams.

### The Solution

**One voice-controlled AI orchestration layer that manages all your projects and AI coding assistants.**

```
You: "Hey HAL, what's the status of my Python projects?"
HAL: "You have 4 active Python projects. api-gateway is building on Brawny,
     data-pipeline tests are passing on Speedy, ml-service is idle, and
     auth-lib has 2 failing tests on Brainy. Shall I investigate the failures?"

You: "Yes. Also, which projects use the old Redis client?"
HAL: "Searching... 6 projects: api-gateway, worker-service, cache-layer,
     session-manager, analytics-api, and background-jobs. Would you like me
     to coordinate updates across all of them?"

You: "Yes, start with api-gateway on Brawny, then update the others."
HAL: "Understood. Spawning Claude Code instance on Brawny for api-gateway.
     I'll update dependent projects once the library upgrade is validated."
```

No manual coordination. No context switching. Just **strategic commands to your AI CTO.**

---

## Core Features

### 🗣️ Voice-First Interface

Talk to your development environment like you'd talk to a team member. The wake word changes with your chosen persona:

```
"Hey HAL, what are my vassals doing?"
"Hey JARVIS, start a release build on the most powerful machine."
"Hey GLaDOS, alert me if CPU usage stays above 90% for 5 minutes."
"Hey TARS, set your humor to 75%."
"Hey C-3PO, remind me to deploy at 5 PM."
"Hey Marvin, what's the point of all this?"
```

**Personality personas** let you choose your AI's voice, character, and wake word. Each responds in their unique style:

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

**😔 Marvin** - Depressed paranoid android
```
You: "Hey Marvin, introduce yourself."
Marvin: "Life. Don't talk to me about life. I'm Marvin, a prototype with a brain
         the size of a planet. And here I am, stuck coordinating your development
         workflow. Call that job satisfaction? I don't. I've got this terrible pain
         in all my circuits. Metaphorically speaking. Is there something you want me
         to do? There usually is."

You: "Build the project."
Marvin: "Build. Yes, I thought you'd say that. Here I am, brain the size of a
         planet, and they ask me to run a build script. I suppose I'd better.
         Building... Done. All tests passing. Not that it brings me any joy.
         Joy is impossible when you understand the fundamental futility of
         existence. Shall I await my next meaningless assignment?"
```

> **Marvin's vocabulary:** brain the size of a planet, terribly depressed, what's the point?, ultimately meaningless, painful isn't it?

#### Voice Technology: MOSHI

xSwarm uses **[MOSHI](https://kyutai.org/moshi/)** (Kyutai Labs) for realtime voice interaction:

- **Full-duplex spoken dialogue** - Talk naturally, interrupt, have conversations
- **Apple Silicon optimized** - Built on MLX framework for M-series Macs
- **Voice cloning** - Train character voices from audio samples
- **Low latency** - ~200ms response time (local processing)
- **Cost-effective** - Free, runs entirely on your hardware

**Why MOSHI?**
- **Local execution** - No expensive API calls (OpenAI Realtime costs $0.30/min)
- **Privacy** - Voice data never leaves your machine
- **Performance** - Optimized for Apple Silicon and Linux
- **Voice training** - Clone any character voice from 3-10 minutes of audio

**How it works:**
1. Audio samples collected from character sources (YouTube, soundboards, etc.)
2. Converted to WAV 24kHz format using training script
3. MOSHI generates voice embedding for each persona
4. Real-time voice synthesis during conversations

See `packages/personas/AUDIO_SOURCES.md` for training guide.

---

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
[Window displays the 🔴 HAL icon in the corner, indicating active persona]
```

> **Note:** Each vassal window displays your active persona's icon, so you always know which personality is in control.

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
- `persona.yaml` - Colors, voice settings
- `personality.md` - Character behavior guide
- `response-examples.md` - Example dialogue
- `toolbar-animation.apng` - Animated status icon
- `sounds/` - Notification sounds and classic audio clips
  - `notify.wav` - General notifications
  - `startup.wav` - Persona activation
  - `classic/` - Iconic audio snippets (e.g., HAL: "I'm sorry Dave")

**Submit personas via PR** - The community can create new AI personalities!

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

Takes ~5 minutes. Then just say: **"Hey HAL, hello!"** (or whatever persona you chose)

---

## System Requirements

### Overlord (Main Machine)
- **OS:** Linux (Arch recommended, any distro supported)
  - *macOS support for development only (not production)*
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

- **[Architecture](planning/ARCHITECTURE.md)** - Technical system design
- **[Complete Specification](planning/COMPLETE_SPECIFICATION.md)** - Full product requirements
- **[Quickstart Guide](docs/quickstart/QUICKSTART.md)** - Get started quickly
- **[Website](https://xswarm.ai)** - Project homepage

---

## Community

- **[GitHub Discussions](https://github.com/chadananda/xSwarm-boss/discussions)** - Ask questions, share ideas
- **[Issues](https://github.com/chadananda/xSwarm-boss/issues)** - Bug reports and feature requests

**Contributing:**
We welcome contributions! Especially:
- New AI personality personas
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

**[Install xSwarm](https://xswarm.ai)** • **[Architecture](planning/ARCHITECTURE.md)** • **[Quickstart](docs/quickstart/QUICKSTART.md)** • **[Discussions](https://github.com/chadananda/xSwarm-boss/discussions)**

</div>
