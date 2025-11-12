# xSwarm Development TODO - Next Steps

**Last Updated:** November 12, 2025
**Status:** Cleanup complete, ready for next phase of development

---

## ✅ Recently Completed (November 12, 2025)

### Rust Legacy Cleanup
- Deleted Rust example files (test_projects.rs, test_project_manager.rs)
- Updated README.md - replaced Rust badge with Python badge
- Updated roadmap to reflect Python/Textual TUI implementation
- Updated ARCHITECTURE.md - changed Rust Client references to Python Client
- Archived historical Rust documentation to docs/archive/
- Committed changes: `8003419 chore: remove Rust legacy code and update docs`

### GPU Capability System (November 2025)
- Implemented numeric scoring (0-100 scale) based on VRAM capacity
- Created automatic service selection (Moshi quality, thinking mode, embeddings)
- Added hybrid mode support (local voice + cloud thinking)
- Enhanced Moshi MLX with quality auto-detection
- Added debug mode with .env API key loading
- Created deep thinking engine interfaces (AnthropicThinking, OllamaThinking)

---

## 🎯 Immediate Next Steps (Priority Order)

### Phase 1: Complete Deep Thinking Implementation
**Priority:** HIGH
**Estimated Time:** 2-3 days

- [ ] Implement actual Anthropic API calls in `AnthropicThinking.think()`
  - Use `anthropic` Python SDK
  - Implement tool calling support
  - Add streaming for long responses
  - Handle rate limits and errors

- [ ] Implement actual Ollama API calls in `OllamaThinking.think()`
  - Use `requests` or `ollama` Python SDK
  - Support local 70B/13B/7B models
  - Implement streaming
  - Handle model availability checks

- [ ] Create "inner monologue" injection system
  - Design protocol for injecting thinking results into Moshi
  - Implement context window management
  - Test with different persona voices

- [ ] Implement tool calling framework
  - Memory search tool
  - File system search tool
  - Web search tool
  - Define tool calling protocol

**Files to modify:**
- `packages/assistant/assistant/thinking/deep_thinking.py`
- `packages/assistant/assistant/voice/moshi_mlx.py`
- Create `packages/assistant/assistant/tools/` directory

---

### Phase 2: Memory System (4-Layer Architecture)
**Priority:** HIGH
**Estimated Time:** 4-5 days

Based on docs/planning/ARCHITECTURE.md, implement:

- [ ] **Layer 1: Short-term (In-Memory)**
  - Current conversation context
  - Last N messages (configurable)
  - Fast retrieval for immediate context

- [ ] **Layer 2: Session Memory (SQLite)**
  - Conversation history per session
  - Persona-specific memory
  - User preferences and settings

- [ ] **Layer 3: Long-term Memory (libsql/Turso)**
  - Cross-session memory
  - Semantic search with embeddings
  - Project context and history

- [ ] **Layer 4: Knowledge Base (Meilisearch)**
  - File system indexing
  - Code search across projects
  - Documentation search
  - Integration with Docling for PDF processing

**Files to create:**
- `packages/assistant/assistant/memory/short_term.py`
- `packages/assistant/assistant/memory/session.py`
- `packages/assistant/assistant/memory/long_term.py`
- `packages/assistant/assistant/memory/knowledge_base.py`
- `packages/assistant/assistant/memory/embeddings.py`

---

### Phase 3: Multi-Machine Orchestration (Core Vision)
**Priority:** CRITICAL
**Estimated Time:** 2-3 weeks

**Status:** This is the CORE VALUE PROPOSITION but only ~10% implemented

Current gap:
- README describes "AI CTO" that coordinates machines
- Voice assistant can run on one machine
- NO multi-machine coordination yet
- NO Claude Code/Cursor/Aider integration yet

Implementation roadmap:

- [ ] **WebSocket Communication Layer**
  - Overlord ↔ Vassal protocol
  - Machine capability reporting
  - Task distribution protocol
  - Real-time status updates

- [ ] **Vassal Agent System**
  - Claude Code integration
  - Cursor integration
  - Aider integration
  - MCP (Model Context Protocol) isolation

- [ ] **Task Routing Logic**
  - Machine capability assessment
  - Intelligent task assignment
  - Load balancing
  - Failure handling and retry

- [ ] **VNC Integration**
  - Real-time vassal monitoring
  - Remote desktop display in TUI
  - "What is X machine doing?" queries

**Files to create:**
- `packages/orchestrator/` (new package)
- `packages/orchestrator/overlord.py`
- `packages/orchestrator/vassal.py`
- `packages/orchestrator/task_router.py`
- `packages/orchestrator/websocket_protocol.py`

**Reference:**
- See docs/planning/ARCHITECTURE.md for architecture
- See README.md "A Day with xSwarm" for UX vision

---

### Phase 4: Server Integration (Backend)
**Priority:** MEDIUM
**Estimated Time:** 1-2 weeks

Connect to Node.js/Cloudflare server:

- [ ] Implement Turso database client
  - User management
  - Subscription tier handling
  - Memory storage and retrieval

- [ ] Implement Stripe payment integration
  - Usage tracking
  - API key encapsulation
  - Pay-as-you-go for cloud AI

- [ ] Implement multi-channel support
  - SMS (Twilio)
  - Email (SendGrid)
  - API endpoints

**Files to create:**
- `packages/assistant/assistant/server/client.py`
- `packages/assistant/assistant/server/auth.py`
- `packages/assistant/assistant/server/subscription.py`

---

## 🚧 In Progress (Partially Complete)

### Voice Interface
- ✅ Moshi MLX integration (Q8 quantization working)
- ✅ Wake word detection (VOSK)
- ✅ GPU capability detection
- ✅ Quality auto-selection
- 🚧 PyTorch fallback for non-Apple platforms
- ❌ Cloud Moshi API (not yet implemented)

### Persona System
- ✅ YAML-based persona definitions
- ✅ Theme color support
- ✅ Multiple wake words per persona
- ❌ Big Five personality trait integration
- ❌ Per-persona memory isolation

### TUI (Textual Dashboard)
- ✅ Cyberpunk theme with customizable colors
- ✅ GPU monitoring widget
- ✅ Voice visualizer
- ✅ Settings screen
- ❌ Multi-machine status dashboard
- ❌ VNC integration for vassal monitoring

---

## 📊 Current Project Status

### What's Built (~ 40% complete)
1. ✅ Python voice assistant with Textual TUI
2. ✅ GPU capability detection and service selection
3. ✅ Moshi voice interface (local MLX)
4. ✅ Persona system with theme support
5. ✅ Wake word detection
6. ✅ Hybrid mode (local voice + cloud thinking)
7. ✅ Deep thinking engine interfaces (stubs)

### What's Missing (~ 60% remaining)
1. ❌ Actual deep thinking API implementations
2. ❌ 4-layer memory system
3. ❌ Multi-machine orchestration (CRITICAL - core value prop)
4. ❌ Claude Code/Cursor/Aider integration
5. ❌ WebSocket communication layer
6. ❌ Server backend integration
7. ❌ Stripe payment system
8. ❌ Multi-channel support (SMS, Email, API)

---

## 🎯 Architecture Decision Needed

**Question:** How to implement multi-machine orchestration?

**Options:**
1. **Pure Python approach** (current direction)
   - Overlord: Python + Textual TUI
   - Vassals: Python agents on remote machines
   - Communication: WebSockets (asyncio)
   - Pros: Single language, easier to maintain
   - Cons: Python performance for high concurrency

2. **Hybrid approach** (original vision)
   - Overlord: Python + Textual TUI (voice interface)
   - Orchestrator: Rust service (performance)
   - Communication: gRPC or WebSockets
   - Pros: Better performance, clearer separation
   - Cons: Two languages to maintain

**Current lean:** Option 1 (Pure Python) unless performance becomes an issue.

---

## 🔍 Technical Debt & Cleanup

- [ ] Add comprehensive test suite for GPU detection
- [ ] Add integration tests for service selection
- [ ] Document all API endpoints
- [ ] Add error handling for Moshi initialization
- [ ] Improve wake word detection accuracy
- [ ] Add logging framework (structured logs)
- [ ] Add configuration validation

---

## 📚 Documentation Needs

- [ ] Update README with current implementation status
- [ ] Create CONTRIBUTING.md
- [ ] Document API protocol for vassal communication
- [ ] Create developer setup guide
- [ ] Document persona creation guide
- [ ] Add architecture diagrams (PlantUML or Mermaid)

---

## 🚀 Getting Started After Restart

When you return to this project:

1. **Review this document** for current status
2. **Check git log** for recent changes:
   ```bash
   git log --oneline -10
   ```
3. **Start with Phase 1** (Deep Thinking Implementation) - highest priority
4. **Run tests** to verify nothing broke:
   ```bash
   pytest packages/assistant/tests/ -v
   ```
5. **Check GPU capability system** works:
   ```bash
   python3 -c "from packages.assistant.assistant.hardware.gpu_detector import detect_gpu_capability; print(detect_gpu_capability())"
   ```

---

## 📝 Notes for Future Development

### Key Design Principles
1. **Voice-first UX** - Everything accessible via voice commands
2. **Persona-driven interaction** - Different personalities for different contexts
3. **Hybrid AI** - Mix local and cloud intelligently based on GPU capability
4. **Multi-machine coordination** - Core value prop, highest priority
5. **Developer-focused** - Built for software engineers managing multiple projects

### Success Metrics
- Time to coordinate multi-machine task < 30 seconds
- Voice command recognition accuracy > 95%
- GPU utilization optimized based on capability
- User can switch between 5+ machines seamlessly
- "AI CTO" vision fully realized

---

**Last commit:** `8003419` - Rust cleanup complete
**Next session:** Start Phase 1 (Deep Thinking Implementation)
