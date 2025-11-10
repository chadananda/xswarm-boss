# xSwarm Pricing Tiers

**Voice-First AI Personal Assistant Ecosystem**

---

## 1. Free Tier ($0/month)

### 1.1 Voice-First Interaction (MOSHI + Suggestion System)
MOSHI base model (local or cloud). Wake words: "Hey xSwarm", "Jarvis", "Computer" (user-configurable). Self-activation for scheduled items, agent stalls, build completions. Background processes inject context via MOSHI suggestions: semantic memory, tasks, calendar, project status. Local preferred but requires GPU; Cloud Boost ($5/mo) fallback for underpowered hardware.

### 1.2 Visual Presence (Desktop Integration)
Animated icon in Waybar (Hyprland) or macOS menu bar showing state: idle (grey pulse), listening (blue ripple), thinking (orange spin), speaking (green wave). Translucent full-screen overlay (30-50% opacity) displays animated visualization synchronized with voice activity. Overlay dismissible via escape or voice "hide". Customizable themes per persona.

### 1.3 Chat Interface (Typing and History)
Text-based interface alongside voice. Type messages, paste content (text, code, URLs, paths), view conversation history. Searchable by keyword, date, speaker, project tag. Messages timestamped and speaker-labeled. Voice transcriptions appear immediately. Copy button per response. Export to markdown/PDF/text. Typing indicator, markdown rendering, keyboard shortcuts (Ctrl+T focus, Ctrl+H history, Ctrl+/ search).

### 1.4 Document Generation (AI-Capability Dependent)
Generate: reports, summaries, meeting notes, code files, markdown, PRDs, retrospectives. Free tier: simple docs with basic models (markdown, text, JSON, CSV). Auto-save to ~/xswarm/documents/ with timestamp. Optional email or Notion/Obsidian upload. Voice triggers: "write summary of today's work", "generate PRD for X", "export task list".

### 1.5 Email Integration (Dual System)
Unique @xswarm.ai address per user. Assistant sends: briefings, documents, reminders, digests. User emails commands/questions to @xswarm.ai. OAuth Gmail integration: Free tier read-only (summarize inbox, track follow-ups). All processing local-first with semantic memory. Requires SMTP/IMAP server (Postmark or self-hosted Postal), OAuth flow, email parsing, HTML-to-text conversion.

### 1.6 Dashboard (Project and Life Overview)
Real-time overview: active projects (status indicators), calendar events (countdown timers), high-priority tasks (color-coded urgency), recent notes, habit streaks, system status (agents running, builds, tests). Customizable: drag-to-reorder, show/hide widgets, filter by project/time. "Upgrade to unlock" badges hint at Personal tier features. Access via Ctrl+Space, menu bar icon, or voice "show dashboard". Live updates via WebSocket. Built with Electron or Tauri.

### 1.7 Personality System (Base + Persona + Built-In Voices)
Two-layer mandatory system: Base personality (core helpful behavior, constant across users) + Persona overlay (optional modifications: tone, vocabulary, formality, humor, energy). Personas created via AI interview extracting traits, then MOSHI fine-tuning with user audio samples (5-30 min) or built-in voices. Processing: 6-8h local GPU or 30-60min cloud (Personal tier). Free tier: max 3 custom personas. Built-in voices: professional male/female, multiple accents/ages, 200-500MB each, download-on-demand. Persona config JSON: formality level, humor style, energy, proactiveness, address style, verbosity, vocabulary, catchphrases, behavioral rules. Trait adjustments don't require voice re-training.

### 1.8 Semantic Long-Term Memory (Three-Tier + libsql)
Tier 1: Working memory (last 5-10 messages verbatim, in-context, ~1-2K tokens). Tier 2: Session summary (rolling compression every 10 messages, ~500 tokens, "Earlier in this conversation..."). Tier 3: Long-term (libsql with vector embeddings, permanent storage). Database tables: conversations (id, user_id, timestamps, messages jsonb, summary, entities jsonb, embedding vector 1536-dim), facts (id, user_id, fact_text, source_conversation, confidence, category, timestamps, access_count, embedding), entities (id, user_id, type person/project/task/date/preference/location, name, attributes jsonb, mention stats). Background processes: fact extraction (discrete facts with confidence), entity extraction (NER or LLM), embedding generation (sentence-transformers or OpenAI API), relevance scoring (recency_score = 1/(1+days_since_access), combined: 30% recency + 70% similarity). On each message: vector search similar conversations/facts, extract entities, get entity context, inject via MOSHI suggestions when score > threshold. User unaware of retrieval.

### 1.9 Note-Taking Connectors (Notion, Obsidian)
Bidirectional sync. Notion: OAuth, read existing notes/databases, create new notes with hierarchy, update with summaries, search semantically. Obsidian: filesystem vault access, read markdown, create with naming convention/frontmatter, update daily notes, respect WikiLinks/backlinks, search via full-text/backlinks. Notes appear in semantic memory, searchable unified. Voice: "save to Notion under Projects/X", "add to daily note", "create note about Y", "find notes mentioning Z".

### 1.10 Desktop Notifications
OS notifications for time-sensitive events. Types: tasks due, calendar events, @xswarm.ai emails, project status changes, agent stalls, briefing reminders. Priority levels: critical (red, sound, persistent), high (yellow, sound, 30s auto-dismiss), normal (blue, silent, 10s), low (grey, silent, 5s). User config: per-type settings, Do Not Disturb, quiet hours, priority thresholds. Free tier: desktop only via native APIs (Windows toast, macOS notification center, Linux notify-send).

### 1.11 Task Management
Voice-based task CRUD. Create: "Remind me to call Mike tomorrow at 2pm". List/complete/priority/reschedule via voice. Data: id, user_id, title, description, priority high/normal/low, due_date, completed bool, timestamps, tags, recurring. Stored in local SQLite/libsql. Surface in briefings, proactive reminders, contextual mentions.

### 1.12 Note Taking ("Remember That...")
Instant capture during conversation. "Remember that Ocean Library uses Supabase", "Make note: Mike prefers email". Auto-categorization, semantic search, linkable to entities. Data: id, user_id, content, captured_at, category technical/idea/personal/decision, tags, linked_entities, embedding. Part of semantic memory, surfaced in context, exported on demand.

### 1.13 Calendar Viewing
Read-only integration. Supported: Google (OAuth), Outlook/365, iCloud, CalDAV. Voice: "What's on my calendar today?", "When's next meeting?", "Am I free Thursday?". Real-time sync via API polling (5-15 min), cache locally. Minimal data: title, time, location, attendee names. Surface in briefings, reminders, conflict detection.

### 1.14 Email Reading (Gmail Integration)
Read-only Gmail OAuth. Voice: "New emails?", "Read inbox", "Emails from Sarah?", "Emails about WholeReader?". Fetch recent (last 24h default), search by sender/subject/date, read content aloud (summary or full), mark read. Cannot send (use @xswarm.ai for outbound).

### 1.15 Daily Briefings
Morning (7-9am configurable): greeting, calendar, tasks due today, email unread/important, projects needing attention, weather, optional news. Evening (5-7pm configurable): accomplishments, carry-over tasks, tomorrow preview, optional reflection prompt. Delivery: voice (MOSHI if at computer), email (@xswarm.ai if not).

### 1.16 Simple Brainstorming
Idea capture during conversational thinking. "Let's brainstorm ideas for X", "Help me think through this". Active listening, idea clustering (keyword-based), pro/con analysis, prioritization, export to markdown outline. Free tier: local AI (limited creativity), basic clustering, simple structure.

### 1.17 Habit Tracking
Conversational logging. "I went for a run today", "Did I exercise this week?", "Remind me to drink water every 2h", "Show meditation streak". Binary habits (done/not), quantity habits (count/duration), streaks (consecutive days), patterns. Data: habit_id, name, type binary/quantity, goal, entries array with date/completed/value/unit, current_streak, longest_streak. Motivation: streak notifications, encouragement, pattern insights, gentle reminders.

### 1.18 Time Logging
Automatic project time tracking from conversation context. Passive: detect project discussed, log time. Active: "Start timer for WholeReader", "Stop timer", "How much time on xSwarm this week?". Data: entry_id, user_id, project, start/end timestamps, duration_minutes, activity_type coding/meeting/planning/research, auto_detected bool. Reports: daily/weekly/monthly, per-project, activity distribution, CSV export.

### 1.19 Decision Support
Quick tools. Coin flip: "Flip a coin" → Heads/Tails. Random choice: "Pick one: pizza, sushi, burgers" → Sushi. Dice roll: "Roll d20" → 14. Pro/con list: "Pros and cons of using React?" → AI generates balanced list, user adds items, weighted scoring optional. Free tier: simple logic.

### 1.20 Template Library
Community-contributed templates. Types: email (cold outreach, meeting request, follow-up), messages (Slack, Discord, social), documents (PRD, agenda, retrospective), code snippets. Usage: "Use cold email template", "Fill meeting agenda for WholeReader sync". AI fills placeholders with context. Storage: central repo (GitHub), community PR submissions, markdown with {{placeholders}}, metadata: category/tags/author/usage_count.

### 1.21 AI-Guided Personality Creator
Conversational interview replaces forms. Flow: 1) User initiates. 2) AI asks 5-10 questions extracting traits (formality, humor, proactiveness, detail level). 3) Voice sample collection (guide through options, legal disclaimer, validate: duration/quality/single speaker). 4) AI summarizes profile, user confirms/adjusts, names personality. 5) Background MOSHI fine-tuning, estimate time, notify when complete. Generates persona config JSON (see Personality System).

### 1.22 Voice Training
MOSHI fine-tuning with user audio. Requirements: 5-30 min clear speech, single speaker, clean audio, variety (emotions/contexts). Process: upload MP3/WAV/FLAC/M4A → validate quality/duration → convert to 16kHz mono WAV → optional phoneme alignment → fine-tune MOSHI → save checkpoint → test inference. Processing time: CPU 12-24h (not recommended), GPU 8GB 6-8h, GPU 16GB+ 3-5h, Personal tier cloud A100 30-60min. Storage: ~200-500MB per model, Free tier 3 models max (1.5GB limit), Personal unlimited.

### 1.23 Trait Customization
Direct manipulation without voice re-training. Editable: formality (slider 1-10), humor style (dropdown none/dry/playful/sarcastic), energy (slider 1-10), proactiveness (slider 1-10), address style (dropdown casual/sir/madam/custom), response length (short/medium/long), vocabulary (technical/casual/sophisticated). Effect on responses: word choice, sentence structure, joke injection, enthusiasm, suggestion frequency, user addressing, brevity vs elaboration. Live testing: try traits, adjust, retry. No re-training (config-only).

### 1.24 Local Processing
MOSHI fine-tuning on user's hardware (Free tier). Hardware: minimum 8GB RAM/4-core CPU (very slow), recommended 16GB RAM/8-core CPU/8GB VRAM, optimal 32GB RAM/12+ core/16GB+ VRAM. Process management: background job queue (idle/overnight), progress tracking, pause/resume, time estimation, resource throttling. Storage: models ~/.xswarm/models/, temp ~/.xswarm/temp/, auto-cleanup after success. Cloud upgrade prompt: "8 hours on your hardware. Upgrade to Personal for 1-hour cloud?"

### 1.25 Usage Guidelines
Legal disclaimers throughout. Key messages: 1) Must own rights or have permission for voice samples. 2) Personal use only - no distributing copyrighted personas. 3) xSwarm not responsible for your creations. 4) IP violation is your liability. Placement: voice sample selection, before audio upload, persona created confirmation, export. ToS: acceptance required before first creation, user warrants rights to all content, agrees not to distribute infringing, xSwarm disclaims liability.

### 1.26 Workflow Marketplace
Shareable automation recipes (high-level sequences, not code). Example "Morning Startup": check calendar → read emails → list tasks → summarize projects → generate briefing. Format: YAML with name, description, author, tags, steps (actions), triggers (voice/time). Sharing: export to YAML/JSON, upload to community repo (GitHub), import via URL/search.

### 1.27 Plugin Directory
Extend xSwarm via community plugins. Types: data sources (new services), actions (voice commands), integrations (Notion/Trello/Todoist), personality extensions (new traits). Format: JS/TS modules, manifest with metadata, sandboxed execution. Discovery: browse by category, search, popularity ranking, user reviews. Installation: one-click, permissions approval, optional auto-updates. Free tier: 5 plugins max, community only.

### 1.28 Tip Sharing
User-generated best practices. Content: persona creation tips, productivity hacks, workflow ideas, voice shortcuts. Format: short text posts (Twitter-style), links to tutorials/videos, tags. Platform: integrated forum (optional), link to Discord/Reddit, upvote/downvote, comments.

### 1.29 Theme Exchange
Visual customization (low priority). Customizable: color scheme (dark/light/custom), fonts, window transparency, waveform style, icon pack. Sharing: export theme JSON, upload to community, preview before install.

### 1.30 Tutorial Ecosystem
Community creates educational content (xSwarm curates only). Content: YouTube videos ("How to create Jarvis persona"), blog posts (persona guides), GitHub repos (example configs). Curation: community submissions, featured tutorials, searchable by topic, linked from in-app help. Viral strategy: encourage influencer tutorials, affiliate program, retweet/share community content, "Video of the Week" highlights.

### 1.31 Hardware Assessment & Cloud Boost
Hardware capability detection on install: System scan determines AI capability. Detection: CPU (cores/model/speed), RAM (total/available), GPU (presence/VRAM/CUDA/Metal), storage (free space). Scoring: Great (GPU + 16GB+ RAM), Good (GPU + 8GB), Limited (CPU only + 8GB+), Unable (<8GB or very old CPU). User communication: "Great! Advanced local AI", "Good, MOSHI locally, may be slower", "Limited performance. Consider Cloud Boost ($5/mo)", "Can't run local AI. Add Cloud Boost ($5/mo)".

Cloud Boost add-on ($5/mo optional): Remote AI for underpowered hardware. Provides: MOSHI inference + basic thinking layers on xSwarm servers (faster, any hardware). Audio captured locally, sent encrypted to cloud, response streamed back, voice data immediately deleted server-side (zero retention). All persistent data stays local: conversations/facts/entities/embeddings in local libsql. Cloud servers stateless (processing-only). Benefits: faster (server GPUs), no local GPU needed, minimal hardware (4GB RAM, integrated graphics), consistent performance. Pricing: $5/mo base includes ~$2.50 compute credits (~500 voice interactions), overages at actual cost + 50% margin ($0.005-0.01 per message). Upgrade path: Free (local AI, hardware-dependent) → Cloud Boost (basic cloud AI, $5/mo) → Personal (premium cloud AI + features, $20/mo).

### Free Tier Limitations
Local AI only: Performance limited by hardware, simple responses only (complex reasoning struggles), no GPT-4/Claude/Gemini, personality creation slower (6-8h vs 30-60min). No phone/SMS: Desktop and email notifications only, cannot text/call when away. No cloud models: Stuck with MOSHI capabilities, limited reasoning/creativity/knowledge. Basic email: Read-only Gmail, cannot draft sophisticated responses, no smart prioritization. Manual project tracking: No automatic development monitoring, no social media automation, no multi-agent orchestration. 3 persona limit: Can only have 3 custom personas at once, must delete to create new. No advanced features: No xSwarm-Build (development TUI), no xSwarm-Buzz (social automation), no drone worker coordination, no priority support.

---

## 2. Personal Tier ($20/month)

### Everything in Free Tier, Plus:

### 2.1 Cloud AI Models (OpenRouter)
Access to GPT-4, Claude, Gemini, and other premium models via OpenRouter. Intelligent model selection based on task complexity. $10/month AI credit included (~50-100 complex interactions). Overage at actual cost + 50% margin. Model preference settings per user.

### 2.2 Phone/SMS Communication
SMS alerts for critical events. Phone call escalation for urgent matters. Multi-channel notification hierarchy. Smart interruption based on context. Away-mode communication system. Includes 100 SMS + 10 phone calls per month. Overage: $0.05/SMS, $0.50/call.

### 2.3 Enhanced Email Management
Gmail read/write access: draft replies, send on user's behalf, smart inbox prioritization, thread summarization, follow-up tracking. Email triage and categorization. Automated response suggestions.

### 2.4 Advanced Document Generation
Complex documents with cloud models: DOCX via python-docx, PDF via reportlab, XLSX via openpyxl. Professional formatting, proper citations, multi-section structure. Template-based creation.

### 2.5 Personality Features
Unlimited custom personas (no 3-persona limit). Cloud processing for voice training (30-60min vs 6-8h local). Priority access to new built-in voices. Advanced trait combinations and behavioral rules.

### 2.6 Note-Taking Enhancement
Template-based note creation for Notion/Obsidian. Auto-categorization using AI. Cross-note synthesis generating summaries across multiple notes. Scheduled sync jobs for large vaults.

### 2.7 Calendar Write Access
Create/modify events via voice. Meeting intelligence: prep briefs, action items. Smart scheduling suggestions. Conflict resolution.

### 2.8 Advanced Tools
Pro/con analysis with LLM quality. Semantic brainstorming with cloud AI (more creative). Mind maps and comparative analysis. Advanced habit insights and predictions.

---

## 3. Professional Tier ($190/month)

### Everything in Personal Tier, Plus:

### 3.1 xSwarm-Build (Development TUI)
Automated development monitoring across 10 active projects. Real-time TUI dashboard with project status, build pipelines, test results, deployment status, error logs. Git integration: commit monitoring, PR tracking, branch status. CI/CD monitoring: Jenkins, GitHub Actions, GitLab CI. Container monitoring: Docker, Kubernetes. Agent coordination: Claude Code, Cursor, Copilot activity tracking. Voice commands: "What's the status of WholeReader?", "Why did the build fail?", "Deploy to staging".

### 3.2 xSwarm-Buzz (Social Media Automation)
Multi-platform posting: Twitter/X, LinkedIn, Reddit, Hacker News, Discord, Slack communities. Content generation: tweets, threads, technical posts, community responses. Scheduling and optimization: best times to post, A/B testing, engagement tracking. Cross-promotion: "Ocean Library users might like WholeReader". Content gap analysis: "We haven't posted technical content lately". Timing optimization, competitive insights.

### 3.3 Drone Worker Coordination
Orchestrate 5 computers as specialized workers. Distributed computing: compile on powerful desktop, test on laptop, deploy from server. Resource management: CPU/GPU allocation, task routing. Status monitoring: health checks, performance metrics. Voice control: "Deploy WholeReader on drone-2", "What's the load on drone-3?".

### 3.4 Project Management
10 active managed projects simultaneously. Automated status tracking. Build/test/deploy monitoring. Issue tracking integration (GitHub Issues, Jira). Sprint planning assistance. Velocity tracking and predictions.

### 3.5 Enhanced Support
Email support with 24-hour response time. Documentation library: professional guides and best practices. Community forum: priority access and featured support. Monthly check-in: optional strategy call.

### 3.6 Usage & Limits
$50 monthly AI credit (generous budget for development work). Pay-as-you-go: additional AI at cost + 20% (billed monthly). Unlimited SMS/calls: no overage charges. Fair use API rate limits.

---

## 4. Enterprise Tier ($940/month)

### Everything in Professional Tier, Plus:

### 4.1 Unlimited Scale
Unlimited active projects. Unlimited drone workers (coordinate entire fleets). $500 monthly AI credit (massive budget for heavy workloads). No rate limits: maximum performance and throughput. Priority infrastructure: dedicated resources, faster processing. High-volume posting: unlimited social media posts/responses. Bulk operations: process hundreds of projects/drones efficiently.

### 4.2 Team Collaboration (Roadmap)
Multiple users sharing one xSwarm account. Role-based permissions (admin, developer, marketer). Shared project access with private notes. Collaborative planning sessions. Activity audit trail per user.

### 4.3 Custom Integration
API access: build xSwarm into your tools. Webhook integration: connect to your infrastructure. Custom drone roles: specialized worker configurations. Database connectors: direct integration with your databases. CI/CD integration: hook into your deployment pipeline. Slack/Discord bots: xSwarm in your team chat.

### 4.4 Workflow Customization
Custom automation: tailored workflows for your process. Advanced orchestration: complex multi-step operations. Priority processing: your jobs run first. Dedicated resources: isolated compute for your workloads.

### 4.5 Premium Support
Phone support: direct line to technical team. 4-hour response time (24/7 availability). Dedicated account manager: quarterly business reviews, strategic planning, feature requests prioritized. Implementation assistance: onboarding, training, custom setup. SLA guarantee: 99.5% uptime commitment.

### 4.6 Enterprise Features (Roadmap)
SSO/SAML authentication. Audit logging and compliance reports. Data residency options. Custom deployment (on-premise/VPC). White-label options. Custom training data isolation.

---

## Upgrade Paths

**Free → Personal ($20/mo):** "Your local AI is struggling - upgrade for GPT-4?", "Want me to text you when this completes?", "This document is too complex for local AI - try cloud models?", After 3 weeks of daily use.

**Personal → Professional ($190/mo):** "You're managing 3+ coding projects - want automated monitoring?", "Starting to post on social media? xSwarm-Buzz can automate that", "Your projects could benefit from xSwarm-Build's workflows", When juggling multiple projects.

**Professional → Enterprise ($940/mo):** Managing >10 projects consistently, Hitting API rate limits frequently, Need for team collaboration, Consistent use of support.

---

This completes the 4-tier xSwarm feature specification.