# Thinking Service - AI-Powered Memory Filtering

The Thinking Service provides intelligent memory filtering using AI to evaluate memories for **relevance** and **importance** before injecting them into limited conversation context.

## 🎯 Purpose

Instead of simple top-k semantic search, the thinking service:

1. **Retrieves** top-k candidates using vector similarity
2. **Evaluates** each candidate with AI for relevance AND importance
3. **Injects** only approved memories (typically 1-3) as inner monologue
4. **Optimizes** cost by selecting the cheapest model for requested quality tier

This approach dramatically improves context efficiency: 1000s of stored memories → 15 candidates → 1-3 approved memories.

## 🏗️ Architecture

### Client-Side (Python)

```
packages/assistant/assistant/memory/
├── model_config.py         # Parse PROVIDER:model-name format
├── embedder.py             # Generate vector embeddings
├── memory_client.py        # Retrieve candidates + filter with thinking
├── memory_orchestrator.py  # High-level API for conversation loop
└── __init__.py
```

### Server-Side (Node.js)

```
packages/server/src/lib/
├── thinking-models.js      # Model database with cost-based selection
└── thinking.js             # API endpoints for thinking service
```

### Integration

```
packages/assistant/assistant/voice/
└── conversation.py         # Inject filtered memories into Moshi
```

## 📊 Data Flow

```
User speaks
    ↓
Conversation loop (conversation.py)
    ↓
Memory Orchestrator.get_memories()
    ├─→ Embedder.embed(query) → vector
    ├─→ MemoryClient.retrieve_candidates(vector) → 15 candidates
    └─→ MemoryClient.filter_memories(level, context, candidates)
        ├─ Dev mode: Local Ollama/Anthropic/OpenAI
        └─ Prod mode: Server thinking API
            ↓
        Server thinking.js
            ├─→ selectModelForThinking(level) → cheapest model
            ├─→ callAnthropic/callOpenAI(prompt)
            └─→ filterMemories() → 1-3 approved
    ↓
Inject as inner monologue → Moshi.generate_response(text_prompt)
```

## 🎚️ Thinking Levels

Three quality tiers with automatic cost optimization:

### Light (Fast & Cheap)

- **Models**: GPT-4o-mini ($0.15/M), Claude Haiku ($0.25/M)
- **Use case**: Simple filtering, frequent queries
- **Speed**: ~1-2 seconds
- **Quality**: Good for straightforward relevance checks

### Normal (Balanced)

- **Models**: Claude Sonnet 4 ($3/M), GPT-4 Turbo ($10/M)
- **Use case**: Balanced quality and cost
- **Speed**: ~2-4 seconds
- **Quality**: Excellent reasoning for most cases

### Deep (High Quality)

- **Models**: Claude Sonnet 4.5 ($3/M), GPT o1 ($30/M), Claude Opus 4 ($15/M)
- **Use case**: Complex reasoning, critical decisions
- **Speed**: ~4-8 seconds
- **Quality**: Maximum reasoning capability

## 💰 Cost Model

### Typical Query (5k tokens)

- **Light**: $0.00075 (< 1 cent)
- **Normal**: $0.015 (1.5 cents)
- **Deep**: $0.015 - $0.15 (1.5-15 cents)

### $5 Minimum Budget

With light tier, $5 provides:
- ~6,600 thinking queries
- Suitable for 1000s of memory recalls
- Most users won't exceed $5

### Pay-as-you-go

- $5 minimum top-up
- Charges only for actual usage
- Real-time cost tracking
- Separate from subscription tiers

## 🔧 Configuration

### Dev Mode (.env)

```env
# Thinking models (dev/--debug mode only)
THINKING_ENGINE_LIGHT="ANTHROPIC:claude-haiku-4-5"
THINKING_ENGINE_NORMAL="ANTHROPIC:claude-sonnet-4"
THINKING_ENGINE_DEEP="ANTHROPIC:sonnet-4-5"

# API keys for dev mode
ANTHROPIC_API_KEY="sk-ant-..."
OPENAI_API_KEY="sk-..."

# Embeddings (production uses OpenAI, dev can use local)
OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
```

### Production Mode

- **No .env** for end users
- All services via server API
- Server selects cheapest model at runtime
- Automatic failover between providers

## 🚀 Usage Examples

### Basic Usage (Python)

```python
from assistant.memory.memory_orchestrator import MemoryOrchestrator
from assistant.config import Config

# Initialize
config = Config()
orchestrator = MemoryOrchestrator(config, debug_mode=False)

# Get filtered memories
memories = await orchestrator.get_memories(
    user_id="user123",
    query="What was my favorite color?",
    context="User asking about preferences",
    thinking_level="light"  # or "normal", "deep"
)

# Inject into conversation
for memory in memories:
    print(f"Remember: {memory.text}")
```

### Conversation Integration (Automatic)

```python
# conversation.py automatically retrieves and injects memories
# No manual intervention needed - just pass MemoryOrchestrator to ConversationOrchestrator

conversation = ConversationOrchestrator(
    moshi_bridge=moshi,
    persona_manager=persona,
    memory_manager=memory,
    ai_client=ai,
    memory_orchestrator=orchestrator,  # Enables AI-filtered memory
    user_id="user123"
)

# Now every conversation turn will:
# 1. Retrieve relevant memories
# 2. Filter with thinking service
# 3. Inject as inner monologue to Moshi
```

### Server API (Node.js)

```javascript
// POST /api/thinking/filter
const response = await fetch('http://localhost:3000/api/thinking/filter', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    level: 'light',  // or 'normal', 'deep'
    context: 'User asking about preferences',
    candidates: [
      { id: 'mem1', text: "User's favorite color is blue", user_id: 'u1', created_at: '2025-01-01' },
      { id: 'mem2', text: 'User likes pizza', user_id: 'u1', created_at: '2025-01-02' }
    ]
  })
});

const result = await response.json();
// {
//   approved: [{ id: 'mem1', text: "...", ... }],
//   cost: { tokensUsed: 1500, costUSD: 0.000225 },
//   model: "OPENAI:gpt-4o-mini"
// }
```

## 🔌 Ollama Support (Local Inference)

For users with powerful GPUs (16GB+ VRAM):

```python
# Dev mode only - uses local Ollama
config = Config()
config.thinking_models = {
    'light': ModelConfig('OLLAMA', 'llama3:8b'),
    'normal': ModelConfig('OLLAMA', 'mixtral:8x7b'),
    'deep': ModelConfig('OLLAMA', 'llama3:70b')
}

orchestrator = MemoryOrchestrator(config, debug_mode=True)
# Now uses local inference (FREE)
```

**Requirements**:
- Ollama installed (`brew install ollama`)
- Models pulled (`ollama pull llama3:8b`)
- 16GB+ GPU memory for 8B models
- 40GB+ for 70B models

## 🛡️ Graceful Fallback

The system never fails - it degrades gracefully:

1. **Primary**: AI-filtered memories (1-3 approved)
2. **Fallback 1**: Unfiltered top-3 candidates (if thinking unavailable)
3. **Fallback 2**: No memory injection (if embedding fails)

```python
# Automatic fallback hierarchy
try:
    memories = await orchestrator.get_memories(...)  # AI-filtered
except ThinkingServiceUnavailable:
    memories = candidates[:3]  # Unfiltered top-3
except EmbeddingFailure:
    memories = []  # Continue without memory
```

## 📈 Monitoring

### Cost Tracking

```javascript
// Server tracks all costs
const stats = await getThinkingStats();
// {
//   totalRequests: 1523,
//   totalCost: 1.14,
//   avgCostPerRequest: 0.00075,
//   modelUsage: {
//     'OPENAI:gpt-4o-mini': 1200,
//     'ANTHROPIC:claude-haiku-4-5': 323
//   }
// }
```

### Health Check

```bash
curl http://localhost:3000/api/thinking/health
# {
#   "available": true,
#   "providers": ["ANTHROPIC", "OPENAI"],
#   "message": "Thinking service available with ANTHROPIC, OPENAI"
# }
```

## 🧪 Testing

### Unit Tests

```bash
# Test embedder
python packages/assistant/assistant/memory/embedder.py

# Test memory client
python packages/assistant/assistant/memory/memory_client.py

# Test orchestrator
python packages/assistant/assistant/memory/memory_orchestrator.py

# Test model database
node packages/server/src/lib/thinking-models.js
```

### Integration Tests

```python
# Test full pipeline
pytest tests/test_memory_thinking_integration.py

# Test with real APIs (requires API keys)
pytest tests/test_memory_thinking_integration.py --real-apis
```

## 🔒 Security

### API Keys

- **Dev mode**: Stored in .env (gitignored, admin only)
- **Production**: Server-side only, never exposed to clients
- **Ollama**: No API keys needed (local inference)

### Rate Limiting

```javascript
// Server implements rate limiting
app.use('/api/thinking', rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 100  // 100 requests per 15 min
}));
```

## 📚 Related Documentation

- [DEV_MODE.md](./DEV_MODE.md) - Dev mode and server bypass
- [MOSHI_MEMORY.md](./MOSHI_MEMORY.md) - Memory architecture strategy
- [API.md](./API.md) - Complete server API reference

## 🚦 Status

**Phase 2 (Thinking Service)**: ✅ Complete

- [x] Model configuration parser
- [x] Memory client with thinking
- [x] Embedder (OpenAI + local)
- [x] Memory orchestrator
- [x] Conversation loop integration
- [x] Server model database
- [x] Server thinking API
- [ ] Settings UI with GPU detection (deferred to Phase 2.8)
- [ ] Comprehensive testing (deferred to Phase 2.9)

**Next**: Phase 3 (Persona Switching)
