# xSwarm Assistant

**Your AI-powered personal productivity system** — GTD task management, adaptive scheduling, habit tracking, and goal monitoring with the personality of your favorite sci-fi AI.

![TUI Demo](../../assets/tui-demo.gif)

## Why xSwarm?

The new breed of local AI tools should optimize your life, not just answer questions. xSwarm is a **proactive AI assistant** that:

- **Learns about you** — remembers your name, preferences, and context across sessions
- **Plans your day** — morning briefings, adaptive scheduling, evening reviews
- **Protects your habits** — streak tracking, at-risk warnings, accountability
- **Manages your tasks** — GTD-style inbox processing with smart prioritization
- **Tracks your goals** — weight loss, savings, reading goals with progress visualization

Think of it as your personal chief of staff, powered by Claude, with the personality of JARVIS, HAL-9000, or GLaDOS.

---

## Key Features

### 📅 Adaptive Daily Scheduling (GPS-style)

Your schedule constantly adjusts to reality, like a GPS rerouting when you miss a turn:

```
📅 SCHEDULED - Tuesday, December 03
──────────────────────────────────────────────────
 [ ] 09:00 Team standup (60min)
▶[ ] 10:30 Review PR (30min)        ← Current
 [ ] 14:00 Deep work block (90min)

📋 BACKLOG (by priority)
──────────────────────────────────────────────────
 ⚡ Quick wins (<15min)
   [ ] Reply to email (10min)
   [ ] Update config (5min)
 🔴 Critical
   [ ] Fix production bug (60min)
```

**How it works:**
- Tasks auto-schedule into available time slots
- Short tasks bubble up (GTD 2-minute rule)
- Priorities adjust based on urgency, age, and history
- Tasks that keep getting deferred → auto-moved to Someday/Maybe
- Complete a task → remaining tasks reschedule instantly

### 🧠 Memory & Context

The assistant **remembers you**:

```yaml
# Automatically extracted from conversations
name: "Chad"
preferences:
  - "Prefers morning deep work"
  - "Uses vim keybindings"
  - "Working on xSwarm project"
timezone: "America/Los_Angeles"
```

- **UserProfile**: Facts about you, extracted by AI from natural conversation
- **Session Memory**: Recent conversations inform context
- **Planning History**: Knows your patterns, protects your streaks

### 🎯 GTD Task Management

Full Getting Things Done workflow:

| Status | Purpose |
|--------|---------|
| **Inbox** | Capture everything, process later |
| **Next** | Ready to do when time allows |
| **Scheduled** | Assigned to specific time today |
| **Waiting** | Blocked on someone/something |
| **Someday** | Maybe later, not now |
| **Complete** | Done! |

**Smart Scoring** — tasks prioritized by:
- Priority (Critical > High > Medium > Low)
- Duration (short tasks +30 points — clear the queue!)
- Urgency (overdue +60, due today +40)
- Age (2+ week old tasks get attention)
- Defer history (repeatedly bumped → deprioritized)

### 📊 Habit Tracking (Atomic Habits)

Build better habits with streak accountability:

```
Daily Habits                          Streak
──────────────────────────────────────────────────
 [✓] Exercise                         23 days 🔥
 [✓] Read 30 minutes                  15 days
 [ ] Meditate                         At risk!
 [ ] Journal                          0 days
```

- **Daily/Weekly/Weekday** frequency options
- **Preferred time**: Morning, Afternoon, Evening
- **Streak protection**: Warnings when streaks at risk
- **Visual history**: See your consistency over weeks

### 🎯 Goal Tracking

Track measurable goals with progress visualization:

```
Weight Goal: 180 → 165 lbs
████████████░░░░░░░░ 60% (-9 lbs)
Trend: ↓ improving

Savings Goal: $0 → $10,000
██████░░░░░░░░░░░░░░ 30% (+$3,000)
Trend: → stable
```

- **Directional goals**: Down (weight loss) or Up (savings)
- **Check-ins**: Log progress anytime via conversation
- **Trend analysis**: Improving, stable, or declining
- **Target dates**: Optional deadline tracking

### 🗓️ Daily Planning Sessions

The AI initiates planning conversations:

**Morning Briefing** (auto-triggered on first contact):
> "Good morning, Chad. You have 3 tasks from yesterday, 2 meetings today, and your exercise streak is at 23 days. Your biggest priority is the PR review due at noon. What's your energy level today?"

**Evening Review** (after 8pm):
> "Let's wrap up the day. You completed 5 of 7 tasks. Your meditation streak is at risk — even 5 minutes would save it. Tomorrow you have a 9am meeting. Anything to capture before bed?"

**Check-ins** (when urgent):
> "Quick interruption — your commitment to Sarah is overdue (was due Monday). Should we reschedule or tackle it now?"

### 🤖 AI Personas

Choose your AI personality:

| Persona | Style | From |
|---------|-------|------|
| **JARVIS** | Sophisticated British butler | Iron Man |
| **HAL-9000** | Calm, methodical, slightly ominous | 2001 |
| **GLaDOS** | Passive-aggressive testing coordinator | Portal |
| **KITT** | Friendly, helpful, enthusiastic | Knight Rider |
| **C-3PO** | Protocol-obsessed, anxious | Star Wars |
| **TARS** | Witty, adjustable humor (0-100%) | Interstellar |
| **Marvin** | Chronically depressed genius | Hitchhiker's Guide |
| **Dalek** | EXTERMINATE your procrastination | Doctor Who |

Each persona has custom:
- System prompts that maintain character
- Themed color schemes
- Conversation style and vocabulary

### 🔐 Flexible Authentication

Works with your existing AI subscription:

- **Claude Code Bridge**: Reuse your Claude Pro/Max subscription (no extra API costs!)
- **API Keys**: Direct Anthropic, OpenAI, Google, OpenRouter, Groq
- **Local AI**: Ollama and LMStudio for offline/private use

---

## Installation

```bash
# Clone and install
git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss/packages/assistant
pip install -e .

# Launch
xswarm
```

### Requirements

- Python 3.11+
- macOS, Linux, or Windows
- One of:
  - Claude Pro/Max subscription (via Claude Code)
  - Anthropic API key
  - Local AI (Ollama/LMStudio)

---

## Quick Start

1. **Launch**: `xswarm`
2. **Choose persona**: Settings → Default Persona
3. **Start talking**: "Plan my day" or "Add a task to review the PR"
4. **Build habits**: "Add a daily habit for exercise"
5. **Track goals**: "Create a weight goal from 185 to 170 pounds"

The AI will learn your name, preferences, and patterns over time.

---

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | Next pane |
| `Shift+Tab` | Previous pane |
| `1-5` | Jump to pane (Schedule, Projects, Settings, etc.) |
| `Enter` | Send message |
| `Ctrl+C` | Exit (double-tap to force) |

---

## Architecture

```
assistant/
├── planner.py        # GTD task engine, scheduling, habits, goals
├── chat_engine.py    # AI conversation with persona injection
├── memory.py         # User profile & session persistence
├── dashboard.py      # TUI application (Textual)
├── dashboard_widgets.py  # Schedule, habits, goals widgets
├── personas/         # AI personality configurations
│   ├── jarvis/       # System prompt + theme
│   ├── hal-9000/
│   └── ...
└── thinking_engine.py    # Local AI reasoning
```

---

## Philosophy

**GTD Principles**:
- Capture everything → process later
- If <2 min → do it now
- One next action per project
- Weekly review to stay current

**Atomic Habits**:
- Small daily actions compound
- Never miss twice
- Streaks create momentum

**Adaptive Scheduling**:
- Plans are estimates, not commitments
- Reality changes, schedule adapts
- Clear small tasks to reduce mental overhead

---

## Version

Current: **0.32.1**

## License

MIT — Use freely, contribute back!

---

<p align="center">
  <i>"The best productivity system is one that thinks with you, not for you."</i>
</p>
