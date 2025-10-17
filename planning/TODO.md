# xSwarm-boss Development TODO

**Last Updated:** October 17, 2025
**Version:** 1.0
**Status:** Active Development

This document tracks all development tasks for xSwarm-boss. See [PRD.md](PRD.md) for full product requirements.

---

## Quick Links

- **[PRD](PRD.md)** - Complete product requirements
- **[Architecture](ARCHITECTURE.md)** - Technical system design
- **[Code Style](CODESTYLE.md)** - Coding standards
- **[Testing](TESTING.md)** - Test strategy

---

## Phase 1: Core Foundation (Q4 2025)

### Milestone 1.1: Project Setup

- [x] Repository initialization
- [x] README.md (user-facing story)
- [x] Planning documentation structure
- [ ] Cargo workspace structure
  - [ ] packages/core (Rust orchestrator)
  - [ ] packages/mcp-server (MCP isolation)
  - [ ] packages/indexer (Meilisearch/Docling)
  - [ ] packages/docs (Astro site)
  - [ ] packages/themes (personality themes)
- [ ] PNPM workspace configuration
  - [ ] pnpm-workspace.yaml
  - [ ] Root package.json
  - [ ] Package scripts for build/test/lint
- [ ] GitHub Actions skeleton
  - [ ] Build workflow
  - [ ] Test workflow
  - [ ] Lint workflow

### Milestone 1.2: Core Rust Binary

**Priority:** HIGH
**Depends on:** 1.1

- [ ] CLI framework (clap)
  - [ ] `xswarm setup` command
  - [ ] `xswarm dashboard` command
  - [ ] `xswarm daemon` command
  - [ ] `xswarm theme` command
  - [ ] `xswarm config` command
- [ ] Configuration system
  - [ ] TOML parsing (serde)
  - [ ] ~/.config/xswarm/config.toml
  - [ ] Vassal configuration
  - [ ] Theme configuration
- [ ] Logging system
  - [ ] tracing framework
  - [ ] Log levels
  - [ ] File rotation
- [ ] Error handling
  - [ ] anyhow/thiserror
  - [ ] User-friendly error messages
  - [ ] Error recovery strategies

### Milestone 1.3: Ratatui Dashboard

**Priority:** HIGH
**Depends on:** 1.2

- [ ] Main layout engine
  - [ ] Terminal size detection
  - [ ] Responsive layout
  - [ ] Window management
- [ ] Hexagonal worker grid widget
  - [ ] Vassal status display
  - [ ] CPU/RAM indicators
  - [ ] Active task display
  - [ ] Theme icon overlay
- [ ] Real-time log viewer
  - [ ] Scrolling buffer
  - [ ] Color-coded logs
  - [ ] Filter/search
- [ ] Chat interface
  - [ ] Input box
  - [ ] Conversation history
  - [ ] Theme-appropriate styling
- [ ] Status bar
  - [ ] System resources
  - [ ] Active theme indicator
  - [ ] Connection status
- [ ] Help overlay (F1)
- [ ] Keyboard navigation
- [ ] Mouse support (optional)

### Milestone 1.4: Networking Foundation

**Priority:** HIGH
**Depends on:** 1.2

- [ ] WebSocket server (tokio-tungstenite)
  - [ ] Connection handling
  - [ ] Message framing
  - [ ] Ping/pong heartbeat
- [ ] WebSocket client
  - [ ] Auto-reconnect logic
  - [ ] Backoff strategy
- [ ] mTLS implementation
  - [ ] Certificate generation
  - [ ] Certificate signing
  - [ ] Mutual authentication
- [ ] Connection pooling
  - [ ] Vassal connection pool
  - [ ] Resource limits
- [ ] Heartbeat system
  - [ ] Health checks
  - [ ] Timeout detection
  - [ ] Dead connection cleanup

### Milestone 1.5: Basic Task Management

**Priority:** HIGH
**Depends on:** 1.3, 1.4

- [ ] Task definition types
  - [ ] TaskType enum (Build, Test, Deploy, etc.)
  - [ ] Task struct with requirements
  - [ ] Task serialization
- [ ] Task queue implementation
  - [ ] Priority queue
  - [ ] FIFO ordering
  - [ ] Task deduplication
- [ ] Task routing logic
  - [ ] Vassal capability matching
  - [ ] Resource availability check
  - [ ] Scoring algorithm
- [ ] Task execution engine
  - [ ] Remote execution
  - [ ] Result streaming
  - [ ] Error handling
- [ ] Result collection
  - [ ] Success/failure status
  - [ ] Log aggregation
  - [ ] Metrics collection

---

## Phase 2: Intelligence (Q1 2026)

### Milestone 2.1: AI Agent Integration

**Priority:** CRITICAL
**Depends on:** 1.5

**Purpose:** xSwarm's core functionality - coordinating AI coding assistants across projects.

- [ ] Project graph system
  - [ ] Project discovery and parsing
  - [ ] Dependency detection (package.json, Cargo.toml, etc.)
  - [ ] Dependency graph construction
  - [ ] Topological sort for update ordering
- [ ] Agent manager core
  - [ ] Agent type enum (ClaudeCode, Cursor, Aider)
  - [ ] Agent lifecycle (spawn, monitor, terminate)
  - [ ] Agent pool management
  - [ ] Resource allocation algorithm
- [ ] Claude Code integration
  - [ ] API client (when available)
  - [ ] CLI subprocess fallback
  - [ ] Progress monitoring
  - [ ] Result collection
- [ ] Aider integration
  - [ ] CLI subprocess spawning
  - [ ] Task specification format
  - [ ] Output parsing
- [ ] Cursor integration (TBD)
  - [ ] Research automation capabilities
  - [ ] Determine integration approach
- [ ] Cross-project coordination
  - [ ] Multi-project status queries
  - [ ] Dependency chain updates
  - [ ] Parallel agent execution
  - [ ] Wave-based updates
- [ ] Agent monitoring dashboard
  - [ ] Active agents display
  - [ ] Progress indicators
  - [ ] Resource usage per agent
  - [ ] Project status overview

### Milestone 2.2: Theme System

**Priority:** HIGH
**Depends on:** 1.3

- [ ] YAML theme parser
  - [ ] theme.yaml validation
  - [ ] Color scheme parsing
  - [ ] Voice parameters
- [ ] Markdown personality loader
  - [ ] personality.md parsing
  - [ ] Response examples loading
  - [ ] Vocabulary mapping
- [ ] Theme switcher
  - [ ] Live theme switching
  - [ ] Wake word update
  - [ ] UI re-rendering
- [ ] Theme implementations
  - [ ] Sauron (👁️)
    - [ ] Theme files
    - [ ] Personality guide
    - [ ] Vocabulary (orc regiments, etc.)
    - [ ] Audio clips
    - [ ] Animation icon
  - [ ] HAL 9000 (🔴)
    - [ ] Theme files
    - [ ] "I'm sorry Dave" clips
    - [ ] Auxiliary systems vocabulary
  - [ ] JARVIS (💙)
    - [ ] Theme files
    - [ ] British accent guidance
    - [ ] Household staff vocabulary
  - [ ] DALEK (⚡)
    - [ ] Theme files
    - [ ] EXTERMINATE clips
    - [ ] Inferior drones vocabulary
  - [ ] C-3PO (🌟)
    - [ ] Theme files
    - [ ] "Oh my" clips
    - [ ] Anxious vocabulary
  - [ ] GLaDOS (🧪)
    - [ ] Theme files
    - [ ] "For science" clips
    - [ ] Test subjects vocabulary
  - [ ] TARS (🤖)
    - [ ] Theme files
    - [ ] Humor settings
    - [ ] Fellow machines vocabulary

### Milestone 2.2: Voice Interface

**Priority:** HIGH
**Depends on:** 2.1

- [ ] Audio pipeline
  - [ ] WebRTC audio capture
  - [ ] Opus codec integration
  - [ ] Audio streaming
  - [ ] Playback system
- [ ] Wake word detection
  - [ ] Theme-specific wake words
  - [ ] "Hey Sauron", "Hey HAL", etc.
  - [ ] False positive filtering
- [ ] LLM integration
  - [ ] Anthropic voice API
  - [ ] OpenAI voice API (fallback)
  - [ ] Local LLM support (llama.cpp)
  - [ ] GPU detection & auto-config
- [ ] Response handling
  - [ ] Text-to-speech
  - [ ] Classic audio clip playback
  - [ ] Emotion/tone matching
- [ ] Error recovery
  - [ ] API failure handling
  - [ ] Timeout management

### Milestone 2.3: Memory System (4-Layer)

**Priority:** HIGH
**Depends on:** 2.2

- [ ] LibSQL integration
  - [ ] Database initialization
  - [ ] Schema creation
  - [ ] Connection pooling
- [ ] Working Memory (Layer 1)
  - [ ] VecDeque<Message> in-memory
  - [ ] Last 10-20 exchanges
  - [ ] Real-time access
- [ ] Episodic Memory (Layer 2)
  - [ ] Conversation logging
  - [ ] Hierarchical summarization
  - [ ] Vector embeddings
  - [ ] Semantic search (<100ms)
- [ ] Semantic Memory (Layer 3)
  - [ ] Knowledge graph implementation
  - [ ] Entity extraction
  - [ ] Relationship mapping
  - [ ] Multi-hop queries (<50ms)
- [ ] Long-Term Archive (Layer 4)
  - [ ] Compression (100:1 ratio)
  - [ ] Cold storage
  - [ ] Bulk retrieval
- [ ] PII filtering
  - [ ] Regex patterns (API keys, emails, SSH keys)
  - [ ] Pre-storage filtering
  - [ ] Audit logging
- [ ] Context retrieval
  - [ ] Parallel search (episodic + semantic + working)
  - [ ] Context assembly
  - [ ] Relevance scoring

### Milestone 2.4: Semantic Search

**Priority:** MEDIUM
**Depends on:** None

- [ ] Meilisearch integration
  - [ ] Server management
  - [ ] Index creation
  - [ ] Document ingestion
  - [ ] Hybrid search (text + vector)
- [ ] Document processing
  - [ ] Docling parser integration
  - [ ] PDF → Markdown
  - [ ] DOCX → Markdown
  - [ ] Metadata extraction
- [ ] Filesystem indexer
  - [ ] Chokidar watcher
  - [ ] ~/Documents monitoring
  - [ ] ~/Dropbox monitoring
  - [ ] Change detection
  - [ ] Incremental updates
- [ ] Embedding pipeline
  - [ ] OpenAI embeddings API
  - [ ] Batch processing
  - [ ] Vector storage
- [ ] Query interface
  - [ ] Voice search
  - [ ] CLI search
  - [ ] Filter/facet support

---

## Phase 3: Integration (Q2 2026)

### Milestone 3.1: Security Layer (MCP)

**Priority:** CRITICAL
**Depends on:** 1.2

- [ ] MCP server (separate binary)
  - [ ] Unix socket listener
  - [ ] Request authentication
  - [ ] Process isolation
- [ ] Secret vault
  - [ ] Encrypted storage
  - [ ] API key management
  - [ ] OAuth token handling
- [ ] Audit logging
  - [ ] Secret access logs
  - [ ] Timestamp + action
  - [ ] Tamper detection
- [ ] API integrations
  - [ ] Anthropic API
  - [ ] OpenAI API
  - [ ] Gmail/OAuth
  - [ ] GitHub/GitLab

### Milestone 3.2: Desktop Integration

**Priority:** HIGH
**Depends on:** 1.3

- [ ] Universal (DE-agnostic)
  - [ ] XDG Desktop Entry
  - [ ] systemd user service
  - [ ] D-Bus notifications
  - [ ] Application icon
  - [ ] MIME handlers
- [ ] Omarchy-specific (Hyprland)
  - [ ] Workspace 9 config
  - [ ] Window rules
  - [ ] Keybindings (SUPER+9)
  - [ ] Waybar module
    - [ ] Animated APNG icon
    - [ ] Status text
    - [ ] Click handler
  - [ ] Auto-start setup

### Milestone 3.3: VNC Integration

**Priority:** MEDIUM
**Depends on:** 1.5

- [ ] Vassal VNC setup
  - [ ] Xvfb virtual display
  - [ ] x11vnc server
  - [ ] Per-task isolation
  - [ ] Theme icon overlay
- [ ] Overlord viewer
  - [ ] SSH tunnel creation
  - [ ] VNC viewer launcher
  - [ ] Fullscreen mode
  - [ ] View-only enforcement

### Milestone 3.4: Multi-Modal Interaction

**Priority:** LOW
**Depends on:** 2.2, 3.1

- [ ] WhatsApp integration
  - [ ] Webhook server
  - [ ] Message parsing
  - [ ] Response formatting
  - [ ] Media handling
  - [ ] Voice note support
- [ ] Email integration
  - [ ] SMTP client
  - [ ] Daily reports
  - [ ] Alert notifications
  - [ ] Template system

---

## Phase 4: Community & Polish (Q2-Q3 2026)

### Milestone 4.1: Packaging & Distribution

**Priority:** HIGH
**Depends on:** All Phase 1-3

- [ ] AUR package (Arch)
  - [ ] PKGBUILD
  - [ ] .SRCINFO
  - [ ] Install scripts
  - [ ] Package testing
  - [ ] AUR submission
- [ ] Debian package
  - [ ] debian/control
  - [ ] debian/rules
  - [ ] postinst script
  - [ ] Lintian checks
- [ ] AppImage
  - [ ] AppImage recipe
  - [ ] Desktop integration
  - [ ] Auto-update support
- [ ] GitHub Actions
  - [ ] Build workflow
  - [ ] Test workflow
  - [ ] Package workflow
  - [ ] Release workflow
  - [ ] Docs deployment

### Milestone 4.2: Documentation

**Priority:** MEDIUM
**Depends on:** 4.1

- [ ] Astro documentation site
  - [ ] Landing page
  - [ ] Installation guide
  - [ ] Configuration guide
  - [ ] API reference
  - [ ] Troubleshooting
  - [ ] FAQ
  - [ ] Theme creation guide
- [ ] Repository docs
  - [ ] CONTRIBUTING.md
  - [ ] CODE_OF_CONDUCT.md
  - [ ] SECURITY.md
  - [ ] Architecture diagrams
  - [ ] Development guide

### Milestone 4.3: Community Features

**Priority:** LOW
**Depends on:** 4.1, 4.2

- [ ] Theme marketplace
  - [ ] Theme submission process
  - [ ] PR templates
  - [ ] Review guidelines
  - [ ] Community voting
- [ ] Plugin system
  - [ ] Plugin API
  - [ ] Plugin loader
  - [ ] Security sandboxing
- [ ] Multi-user support
  - [ ] User accounts
  - [ ] Permission system
  - [ ] Shared vassals
- [ ] Web dashboard
  - [ ] Web UI
  - [ ] Remote access
  - [ ] Mobile responsive

---

## Testing Checklist

See [TESTING.md](TESTING.md) for detailed test strategy.

- [ ] Unit tests (>80% coverage)
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Performance benchmarks
- [ ] Security audits
- [ ] Voice interface testing
- [ ] Theme switching tests
- [ ] Memory system tests

---

## Documentation Checklist

- [x] README.md (user story)
- [x] planning/PRD.md (product requirements)
- [x] planning/ARCHITECTURE.md (technical design)
- [x] planning/TODO.md (this file)
- [ ] planning/CODESTYLE.md (coding standards)
- [ ] planning/TESTING.md (test strategy)
- [ ] CONTRIBUTING.md
- [ ] CODE_OF_CONDUCT.md
- [ ] SECURITY.md

---

## Success Metrics

### Performance Targets

- [ ] Install time: <2 minutes
- [ ] Setup wizard: <5 minutes
- [ ] Voice latency: <1s
- [ ] Search results: <100ms
- [ ] Dashboard: 60fps
- [ ] Memory per hour: ~10KB (compressed)

### Security Targets

- [ ] Zero secret leaks in memory
- [ ] 100% MCP isolation
- [ ] PII filter >99% effective
- [ ] All secret access logged

### Usability Targets

- [ ] Theme switch: instant
- [ ] Voice accuracy: >90%
- [ ] DE compatibility: 100%
- [ ] Theme PR approval: <24h

### Community Targets

- [ ] 100 GitHub stars (6 months)
- [ ] 10 community themes (1 year)
- [ ] 500 active installs (1 year)

---

## Current Sprint

**Sprint:** Foundation Sprint 1
**Duration:** 2 weeks
**Goal:** Complete Milestone 1.1 & 1.2

**Active Tasks:**
- [ ] Cargo workspace structure
- [ ] PNPM workspace configuration
- [ ] CLI framework with clap
- [ ] Configuration system

**Blocked:**
- None

**Next Sprint:**
- Milestone 1.3 (Ratatui Dashboard)
- Milestone 1.4 (Networking)
