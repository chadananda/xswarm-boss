# MOSHI Supervisor System - Architecture & Usage

## Overview

The Supervisor System enables real-time monitoring and context injection into MOSHI voice conversations. This serves as both a development interface for testing voice interactions AND the production blueprint for RAG (Retrieval-Augmented Generation) and tool integration.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SUPERVISOR SYSTEM                     │
└─────────────────────────────────────────────────────────┘

    User speaks
        ↓
    Twilio Media Streams (WebSocket)
        ↓
    ┌──────────────────────────────┐
    │  Voice Bridge (Port 9998)     │
    │                              │
    │  ┌────────────────────────┐  │
    │  │   MOSHI Inference      │  │
    │  │                        │  │
    │  │  1. Audio → MIMI codes │  │
    │  │  2. Check suggestion_  │←─┼─── Shared MOSHI State
    │  │     queue              │  │
    │  │  3. Tokenize text      │  │
    │  │  4. Text conditioning  │  │
    │  │  5. LM forward pass    │  │
    │  │  6. Generate response  │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
                ↑
                │ Shared State (Arc<RwLock<MoshiState>>)
                ↓
    ┌──────────────────────────────┐
    │  Supervisor API (Port 9999)   │
    │                              │
    │  • WebSocket server          │
    │  • Authentication            │
    │  • Rate limiting (2s)        │
    │  • Queue management (5 max)  │
    └──────────────────────────────┘
                ↑
                │ WebSocket
                ↓
    ┌──────────────────────────────┐
    │  Supervisor CLI               │
    │                              │
    │  • Real-time monitoring      │
    │  • Interactive injection     │
    │  • Command: i <text>         │
    └──────────────────────────────┘
                ↑
                │
        Claude Code / Admin
```

## Components

### 1. Text Conditioning Core
**File**: `packages/core/src/voice.rs`

**Key Additions**:
- `suggestion_queue: Arc<Mutex<VecDeque<String>>>` in `MoshiState`
- Inference loop checks queue before each forward pass
- Text tokenization using SentencePiece (32K vocabulary)
- Suggestion text → token IDs → tensor → MOSHI's text conditioning

**Code Flow**:
```rust
// Check suggestion queue
let text_input = {
    let mut queue = state.suggestion_queue.lock().await;
    if let Some(suggestion) = queue.pop_front() {
        // Tokenize: "User mentioned X" → [token_ids]
        let pieces = state.text_tokenizer.encode(&suggestion)?;
        let token_ids: Vec<u32> = pieces.iter().map(|p| p.id).collect();

        // Create tensor for MOSHI
        Some(Tensor::from_vec(token_ids, (1, token_ids.len()), &state.device)?)
    } else {
        None
    }
};

// Forward pass with text conditioning
let (_text_token, audio_codes_out) = state.lm_model.forward(
    text_input,  // ← Text suggestion injected here
    vec![None; MIMI_NUM_CODEBOOKS],
    &().into(),
)?;
```

### 2. Supervisor WebSocket API
**File**: `packages/core/src/supervisor.rs` (374 lines)

**Features**:
- WebSocket server on port 9999 (configurable)
- Token-based authentication
- Rate limiting: 1 suggestion per 2 seconds (configurable)
- Queue management: Max 5 pending suggestions (configurable)

**Protocol**:

**Incoming (Claude → MOSHI)**:
```json
{
  "type": "auth",
  "token": "dev-token-12345"
}

{
  "type": "inject_suggestion",
  "text": "The user mentioned Stripe subscriptions. Explain usage-based billing.",
  "priority": "normal"
}

{
  "type": "ping"
}
```

**Outgoing (MOSHI → Claude)**:
```json
{
  "type": "auth_result",
  "success": true,
  "message": "Authenticated successfully"
}

{
  "type": "suggestion_applied",
  "text": "The user mentioned Stripe...",
  "timestamp": "2025-10-26T14:15:01Z"
}

{
  "type": "suggestion_rejected",
  "reason": "Rate limited. Wait 2000 ms between suggestions."
}

{
  "type": "user_speech",
  "duration_ms": 3200,
  "timestamp": "2025-10-26T14:15:00Z"
}

{
  "type": "error",
  "message": "Not authenticated"
}
```

**Configuration**:
```rust
pub struct SupervisorConfig {
    pub host: String,              // Default: "127.0.0.1"
    pub port: u16,                 // Default: 9999
    pub auth_token: String,        // Env: SUPERVISOR_TOKEN
    pub max_queue_size: usize,     // Default: 5
    pub rate_limit_ms: u64,        // Default: 2000 (2 seconds)
}
```

### 3. Supervisor CLI
**File**: `packages/core/src/bin/supervisor-cli.rs` (315 lines)

**Features**:
- Interactive terminal interface
- Real-time monitoring of injections and responses
- Beautiful formatted output with timestamps
- WebSocket client to supervisor API

**Commands**:
- `i <text>` - Inject suggestion into MOSHI
- `h` - Show help
- `q` - Quit
- `clear` - Clear screen

**Environment Variables**:
```bash
export SUPERVISOR_HOST="127.0.0.1"
export SUPERVISOR_PORT="9999"
export SUPERVISOR_TOKEN="dev-token-12345"
```

## Usage

### Starting the System

**Terminal 1: Start Voice Bridge + Supervisor**
```bash
cargo run --bin xswarm voice-bridge
```

Output:
```
╔══════════════════════════════════════════════════════════╗
║              MOSHI Voice Bridge + Supervisor            ║
╚══════════════════════════════════════════════════════════╝

🎤 Voice Bridge:
   Host: 127.0.0.1
   Port: 9998
   WebSocket: ws://127.0.0.1:9998

🔍 Supervisor API:
   Host: 127.0.0.1
   Port: 9999
   WebSocket: ws://127.0.0.1:9999
   Auth Token: dev-token-12345

✓ Downloading MOSHI models from Hugging Face...
✓ Initializing MOSHI inference engine...

🚀 Both servers are ready!
   Voice bridge: Waiting for Twilio Media Streams
   Supervisor: Waiting for Claude Code connections

💡 To monitor and inject suggestions, run:
   cargo run --bin supervisor-cli
```

**Terminal 2: Start Supervisor CLI**
```bash
cargo run --bin supervisor-cli
```

Output:
```
╔══════════════════════════════════════════════════════════╗
║           MOSHI SUPERVISOR - CLI Monitor                 ║
║                                                          ║
║  Monitor and inject suggestions into MOSHI conversations ║
╚══════════════════════════════════════════════════════════╝

🔌 Connecting to supervisor at ws://127.0.0.1:9999
✓ Connected to supervisor WebSocket
🔐 Authenticating...
✓ Authenticated successfully

╔══════════════════════════════════════════════════════════╗
║                   SUPERVISOR ACTIVE                      ║
║                                                          ║
║  Monitoring MOSHI voice bridge on port 9998             ║
║  Type 'h' for help, 'q' to quit                         ║
╚══════════════════════════════════════════════════════════╝

>
```

### Interactive Usage

**Injecting a suggestion**:
```
> i The user mentioned Stripe. Explain subscription billing.

📤 Injecting: The user mentioned Stripe. Explain subscription billing.

[14:15:01] ✅ INJECTED: The user mentioned Stripe. Explain subscription billing.
```

**Rate limiting example**:
```
> i First suggestion

📤 Injecting: First suggestion

[14:15:01] ✅ INJECTED: First suggestion

> i Second suggestion immediately

📤 Injecting: Second suggestion immediately

❌ REJECTED: Rate limited. Wait 2000 ms between suggestions.
```

### Programmatic Usage (Production RAG)

```rust
use tokio_tungstenite::connect_async;
use futures_util::{SinkExt, StreamExt};
use serde_json::json;

async fn inject_rag_context(context: &str) -> Result<()> {
    let url = "ws://127.0.0.1:9999";
    let (ws_stream, _) = connect_async(url).await?;
    let (mut write, mut read) = ws_stream.split();

    // Authenticate
    let auth = json!({
        "type": "auth",
        "token": std::env::var("SUPERVISOR_TOKEN")?
    });
    write.send(Message::Text(auth.to_string())).await?;

    // Wait for auth response
    if let Some(Ok(Message::Text(response))) = read.next().await {
        // Parse auth result...
    }

    // Inject RAG context
    let injection = json!({
        "type": "inject_suggestion",
        "text": context,
        "priority": "high"
    });
    write.send(Message::Text(injection.to_string())).await?;

    // Wait for confirmation
    if let Some(Ok(Message::Text(response))) = read.next().await {
        // Parse suggestion_applied or suggestion_rejected...
    }

    Ok(())
}
```

## Production RAG Integration Pattern

### The Supervisor System AS RAG Infrastructure

```
User asks: "What's my Stripe subscription status?"
    ↓
MOSHI detects: Knowledge gap (needs external data)
    ↓
Trigger: Webhook/Event to RAG service
    ↓
RAG Service:
    1. Query vector database for relevant context
    2. Fetch from Stripe API: subscription details
    3. Format context: "User has Pro plan, $99/mo, renews Nov 1"
    ↓
RAG Service → Supervisor WebSocket:
    inject_suggestion({
        text: "User subscription: Pro plan, $99/month, auto-renews Nov 1, 2025",
        priority: "high"
    })
    ↓
MOSHI receives suggestion via text conditioning
    ↓
MOSHI: "I see you're on our Pro plan at $99 per month,
        which will automatically renew on November 1st."
```

### Integration Points

**1. Knowledge Gap Detection**
- Implement in MOSHI inference loop
- Detect when user asks for data MOSHI doesn't have
- Trigger RAG query

**2. RAG Service Architecture**
```rust
struct RagService {
    vector_db: VectorDB,
    api_clients: HashMap<String, Box<dyn ApiClient>>,
    supervisor_client: SupervisorClient,
}

impl RagService {
    async fn handle_query(&self, query: &str) -> Result<()> {
        // 1. Semantic search in vector DB
        let relevant_docs = self.vector_db.search(query, limit=5).await?;

        // 2. API calls if needed (Stripe, database, etc.)
        let live_data = self.fetch_live_data(query).await?;

        // 3. Combine and format context
        let context = self.format_context(relevant_docs, live_data)?;

        // 4. Inject into MOSHI
        self.supervisor_client.inject_suggestion(&context).await?;

        Ok(())
    }
}
```

**3. Tool Execution Pattern**
```rust
// User: "Create a new Stripe subscription"
// MOSHI detects: Tool call needed

// Tool execution service
let result = stripe_client.create_subscription(params).await?;

// Inject result into MOSHI
supervisor_client.inject_suggestion(
    &format!("Subscription created: ID {}, Status: active", result.id)
).await?;

// MOSHI: "I've created your subscription. It's now active with ID sub_abc123."
```

## Testing

### Manual Testing

1. **Start servers**:
   ```bash
   cargo run --bin xswarm voice-bridge
   ```

2. **Start CLI in separate terminal**:
   ```bash
   cargo run --bin supervisor-cli
   ```

3. **Test injection**:
   ```
   > i Say the word "banana"
   ```

4. **Verify in voice bridge logs**:
   ```
   INFO xswarm::voice: Injecting supervisor suggestion suggestion="Say the word \"banana\""
   DEBUG xswarm::voice: Text tokenized successfully num_tokens=5
   ```

### Automated Testing

**Unit Tests** (packages/core/src/supervisor.rs):
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_supervisor_config_default() {
        let config = SupervisorConfig::default();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 9999);
        assert_eq!(config.max_queue_size, 5);
    }

    #[test]
    fn test_priority_default() {
        assert_eq!(Priority::default(), Priority::Normal);
    }
}
```

**Integration Tests** (TODO):
1. Start voice bridge
2. Connect supervisor CLI programmatically
3. Inject known suggestion
4. Verify it appears in MOSHI's next inference
5. Check rate limiting works
6. Check queue management

## Configuration

### Environment Variables

```bash
# Supervisor API
export SUPERVISOR_HOST="127.0.0.1"
export SUPERVISOR_PORT="9999"
export SUPERVISOR_TOKEN="your-secret-token-here"

# Voice Bridge
export VOICE_BRIDGE_HOST="127.0.0.1"
export VOICE_BRIDGE_PORT="9998"

# MOSHI Models (optional, uses defaults)
export MOSHI_LM_MODEL="/path/to/model.q8.gguf"
export MOSHI_MIMI_MODEL="/path/to/mimi/model.safetensors"
export MOSHI_TOKENIZER="/path/to/tokenizer_spm_32k_3.model"
```

### Cargo.toml

```toml
[[bin]]
name = "xswarm"
path = "src/main.rs"

[[bin]]
name = "supervisor-cli"
path = "src/bin/supervisor-cli.rs"
```

### Dependencies Added

```toml
chrono = "0.4"  # Timestamps
url = "2.5"     # WebSocket URLs
```

## Performance Characteristics

- **Latency**: Text conditioning adds ~5-10ms per injection
- **Throughput**: Rate limited to 1 suggestion/2s (configurable)
- **Queue**: Max 5 pending suggestions (configurable)
- **Memory**: Minimal overhead (~100 bytes per queued suggestion)
- **Concurrency**: Both servers run in parallel using tokio

## Security Considerations

1. **Authentication**: Token-based auth required for supervisor connections
2. **Rate Limiting**: Prevents injection flooding
3. **Queue Management**: Prevents memory exhaustion
4. **Localhost Only**: Default config binds to 127.0.0.1
5. **Production**: Use strong tokens, HTTPS proxies, and firewall rules

## Troubleshooting

### Supervisor won't connect
```bash
# Check if voice bridge is running
lsof -i :9998
lsof -i :9999

# Check auth token matches
echo $SUPERVISOR_TOKEN
```

### Suggestions not appearing
```bash
# Check voice bridge logs
tail -f /tmp/voice-bridge.log | grep "Injecting supervisor"

# Check queue isn't full
# (CLI will show "REJECTED: Queue full" message)
```

### Rate limiting too aggressive
```rust
// Adjust in main.rs
let mut supervisor_config = supervisor::SupervisorConfig::default();
supervisor_config.rate_limit_ms = 500;  // 500ms instead of 2000ms
```

## Future Enhancements

1. **Multi-channel Communication** (Phase 4)
   - SMS integration (Twilio)
   - Email integration (SendGrid)
   - Phone call metadata injection

2. **Advanced RAG Features**
   - Streaming context injection
   - Priority-based queue sorting
   - Context caching
   - Semantic deduplication

3. **Monitoring & Metrics**
   - Prometheus metrics endpoint
   - Grafana dashboards
   - Injection success rates
   - Latency histograms

4. **Production Hardening**
   - TLS/SSL support
   - JWT authentication
   - Rate limiting per client
   - Audit logging

## References

- MOSHI Paper: https://arxiv.org/abs/2410.00037
- MIMI Codec: https://github.com/kyutai-labs/moshi
- Architecture Doc: `/planning/ARCHITECTURE.md`
- Feature Roadmap: `/planning/FEATURES.md`

## License

MIT License - See LICENSE file for details.
