# xSwarm-boss Architecture

Technical system architecture and implementation details for xSwarm-boss.

---

## System Overview

xSwarm-boss is built as a distributed system with three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                      OVERLORD MACHINE                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Ratatui Dashboard (User Interface)                    │ │
│  │  • Hexagonal vassal grid                               │ │
│  │  • Real-time logs                                      │ │
│  │  • Voice conversation                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Core Orchestrator (Rust)                              │ │
│  │  • Task routing & scheduling                           │ │
│  │  • Memory system (LibSQL + Knowledge Graph)            │ │
│  │  • Voice interface (Anthropic/Local LLM)               │ │
│  │  • Semantic search (Meilisearch)                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  MCP Servers (Isolated Processes - Unix Sockets)       │ │
│  │  • API key vault                                       │ │
│  │  • LLM/API calls                                       │ │
│  │  • OAuth/Gmail access                                  │ │
│  │  • Secret audit logging                                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket (mTLS)
                            │ LAN only
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     VASSAL MACHINES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Brawny 💪  │  │  Speedy ⚡   │  │  Brainy 🧠   │      │
│  │  (Builder)   │  │  (Tester)    │  │  (Analyzer)  │      │
│  │              │  │              │  │              │      │
│  │  VNC Display │  │  VNC Display │  │  VNC Display │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Three-Tier Security Model

### Tier 1: Overlord (Mildly Secure)

```
┌─────────────────────────────────────┐
│  OVERLORD (Mildly Secure)           │
│  • Ratatui dashboard                │
│  • Voice interface (direct)         │
│  • Task routing                     │
│  • Memory summarization (filtered)  │
│  • Meilisearch queries              │
│  ✗ NO API keys                      │
│  ✗ NO secrets in memory             │
└─────────────────────────────────────┘
            │
            │ Unix Socket (localhost)
            ▼
```

**Purpose:** User interaction layer. Handles UI, voice, and task coordination.
**Security:** No secrets stored. All API access goes through MCP layer.

### Tier 2: MCP Servers (Highly Secure)

```
┌─────────────────────────────────────┐
│  MCP SERVERS (Highly Secure)        │
│  • Isolated processes               │
│  • Hold ALL API keys                │
│  • Execute LLM/API calls            │
│  • Gmail/OAuth access               │
│  • Secret audit logging             │
└─────────────────────────────────────┘
            │
            │ LAN WebSocket (mTLS)
            ▼
```

**Purpose:** Security boundary for all external API access.
**Security:** Encrypted secret vault, audit logging, isolated processes.

### Tier 3: Vassals (Trusted)

```
┌─────────────────────────────────────┐
│  VASSALS (Trusted)                  │
│  • Execute tasks                    │
│  • VNC displays                     │
│  • No secrets                       │
│  • LAN-only                         │
└─────────────────────────────────────┘
```

**Purpose:** Task execution workers.
**Security:** No secrets, LAN-only, mTLS authentication.

---

## 🧠 Memory System Architecture

### Four-Layer Memory Hierarchy

```
┌─────────────────────────────────────────┐
│  Layer 1: Working Memory                │
│  Duration: Current session              │
│  Size: 10-20 exchanges (~8K tokens)     │
│  Storage: In-memory VecDeque            │
│  Access: Instant                        │
└─────────────────────────────────────────┘
            ↓ Summarization
┌─────────────────────────────────────────┐
│  Layer 2: Episodic Memory               │
│  Duration: Recent sessions (30 days)    │
│  Size: ~1000 episodes                   │
│  Storage: LibSQL with vector embeddings │
│  Access: Semantic search (<100ms)       │
│  Compression: Hierarchical summaries    │
└─────────────────────────────────────────┘
            ↓ Entity extraction
┌─────────────────────────────────────────┐
│  Layer 3: Semantic Memory (KG)          │
│  Duration: Long-term (persistent)       │
│  Size: ~10K nodes, ~50K edges           │
│  Storage: Graph database                │
│  Access: Multi-hop queries (<50ms)      │
│  Content: Entities, relationships, facts│
└─────────────────────────────────────────┘
            ↓ Archival compression
┌─────────────────────────────────────────┐
│  Layer 4: Long-Term Archive             │
│  Duration: Historical (unlimited)       │
│  Size: Unlimited                        │
│  Storage: Compressed, cold storage      │
│  Access: Rare, bulk retrieval           │
│  Compression: 100:1 ratio               │
└─────────────────────────────────────────┘
```

### Memory Retrieval Pipeline

```
User Query: "How's the API server build?"
      │
      ▼
┌─────────────────────────────────────────┐
│ 1. Entity Extraction                    │
│    Entities: [API server, build]        │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 2. Parallel Retrieval                   │
│    ├─ Episodic: Recent build mentions   │
│    ├─ Semantic: API server dependencies │
│    └─ Working: Current conversation     │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 3. Context Assembly                     │
│    • Build started 2 hours ago on Brawny│
│    • API server = Rust project          │
│    • User asked about it yesterday      │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 4. LLM Response Generation              │
│    "The API server build on Brawny      │
│     completed 2 minutes ago. All 47     │
│     tests passed."                      │
└─────────────────────────────────────────┘
```

---

## 📚 Semantic Search System

### System-Wide Document Indexing

```
┌─────────────────────────────────────────┐
│  Filesystem Watcher (Chokidar)          │
│  Monitors: ~/Documents, ~/Dropbox, etc. │
│  Triggers: File add/modify/delete       │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  Document Parser (Docling)              │
│  PDF → Markdown                         │
│  DOCX → Markdown                        │
│  Code → Annotated text                  │
│  Metadata extraction                    │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  Embedding Generator                    │
│  Model: text-embedding-3-small          │
│  Dimensions: 1536                       │
│  Batch processing                       │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  Meilisearch Index                      │
│  Full-text + Vector search              │
│  ~10M documents supported               │
│  Hybrid search (keyword + semantic)     │
│  Filters: file type, date, path         │
└─────────────────────────────────────────┘
```

### Query Processing

```
Voice: "Find docs about quantum computing"
      │
      ▼
┌─────────────────────────────────────────┐
│ 1. Query Understanding                  │
│    • Extract keywords: quantum computing│
│    • Intent: document search            │
│    • Generate embedding                 │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 2. Hybrid Search                        │
│    • Keyword match: "quantum"           │
│    • Semantic match: vector similarity  │
│    • Filters: last 6 months, PDF only   │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ 3. Ranking & Results                    │
│    • Combine scores (BM25 + cosine)     │
│    • Top 10 documents                   │
│    • Snippet generation                 │
└─────────────────────────────────────────┘
      │
      ▼
Response: "Found 12 docs. Top 3:
  1. Quantum_Computing_Intro.pdf (2024-09)
  2. Notes_Quantum_Algorithms.md
  3. Research_Paper_Quantum.pdf"
```

---

## 🎯 Task Orchestration

### Task Routing Algorithm

```rust
struct Task {
  id: TaskId,
  task_type: TaskType,      // Build, Test, Deploy, etc.
  requirements: Requirements, // CPU, RAM, GPU, etc.
  priority: u8,              // 0-255
  dependencies: Vec<TaskId>,
}

struct Vassal {
  hostname: String,
  role: Role,                // Builder, Tester, Analyzer
  capabilities: Vec<String>, // ["rust", "docker", "gpu"]
  status: VassalStatus,      // Idle, Busy, Error
  cpu_usage: u8,             // 0-100%
  mem_usage: u8,             // 0-100%
}

fn select_vassal(task: &Task, vassals: &[Vassal]) -> Option<&Vassal> {
  vassals.iter()
    .filter(|v| {
      v.status == Idle &&
      v.role.matches(task.task_type) &&
      v.has_capabilities(&task.requirements)
    })
    .max_by_key(|v| score_vassal(v, task))
}

fn score_vassal(v: &Vassal, t: &Task) -> u32 {
  let mut score = 0;

  // Role match
  if v.role == t.task_type { score += 50; }

  // Available resources
  score += (100 - v.cpu_usage) / 3;
  score += (100 - v.mem_usage) / 5;

  // Capability bonus
  for cap in &t.requirements.capabilities {
    if v.capabilities.contains(cap) { score += 10; }
  }

  score
}
```

### Task Lifecycle

```
1. Task Created
   ↓
2. Check Dependencies
   ↓
3. Select Vassal (scoring algorithm)
   ↓
4. Send to Vassal (WebSocket)
   ↓
5. Execute Task
   ↓
6. Stream Results (real-time logs)
   ↓
7. Task Complete / Failed
   ↓
8. Update Memory & Trigger Dependents
```

---

## 🔒 Security Architecture

### PII Filter Pipeline

```
Input: "My API key is sk-ant-abc123xyz..."
      │
      ▼
┌─────────────────────────────────────────┐
│  Regex Pattern Matching                 │
│  • OpenAI keys: sk-[A-Za-z0-9]{48}      │
│  • Anthropic: sk-ant-[A-Za-z0-9-]{95}   │
│  • GitHub: ghp_[A-Za-z0-9]{36}          │
│  • Email: [email regex]                 │
│  • SSH keys: -----BEGIN.*KEY-----       │
└─────────────────────────────────────────┘
      │
      ▼
Output: "My API key is [REDACTED]"
      │
      ▼
Stored in Memory/Logs (safe)
```

### Secret Audit Trail

Every secret access is logged:

```rust
struct SecretAccess {
  timestamp: DateTime,
  key_name: String,        // "anthropic_api_key"
  action: String,          // "voice_call", "embedding"
  caller: String,          // "overlord", "mcp-server"
  success: bool,
}

// All accesses logged to secure audit database
async fn audit_secret_access(key: &str, action: &str) {
  audit_db.insert(SecretAccess {
    timestamp: now(),
    key_name: key.to_string(),
    action: action.to_string(),
    caller: get_caller(),
    success: true,
  }).await;
}
```

---

## 🖥️ Desktop Integration

### Universal (DE-Agnostic)

xSwarm integrates with any desktop environment through standard protocols:

- **XDG Desktop Entry** - Application launcher
- **systemd user service** - Background daemon
- **D-Bus** - Notifications
- **Unix sockets** - IPC

### Omarchy-Specific (Hyprland)

Enhanced integration for Omarchy users:

- **Workspace 9** - Dedicated xSwarm workspace
- **Waybar module** - Animated status indicator
- **Keybindings** - Quick access (SUPER+9)
- **Window rules** - Auto-placement

---

## 📊 Performance Targets

| Component | Target | Notes |
|-----------|--------|-------|
| Voice latency | <1s | From speech to response |
| Semantic search | <100ms | Document retrieval |
| Graph traversal | <50ms | 2-hop queries |
| Dashboard FPS | 60fps | Ratatui rendering |
| Memory per hour | ~10KB | After compression |
| WebSocket latency | <10ms | Overlord ↔ Vassal |
| Task scheduling | <1ms | Selection algorithm |

---

## 🏗️ Technology Stack Summary

### Core (Rust)
- **ratatui** - Terminal UI
- **tokio** - Async runtime
- **tokio-tungstenite** - WebSocket
- **libsql** - Embedded database
- **serde** - Serialization

### AI/ML
- **Anthropic API** - Voice & LLM (remote fallback)
- **llama.cpp** - Local LLM inference
- **OpenAI Embeddings** - Semantic search
- **Meilisearch** - Vector database

### Security
- **rustls** - mTLS implementation
- **secrecy** - Secret management
- **argon2** - Password hashing

### Desktop
- **zbus** - D-Bus integration
- **systemd** - Service management
- **XDG** - Desktop standards

---

For full implementation details, see [PRD.md](PRD.md).
