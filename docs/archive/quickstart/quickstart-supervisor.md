# MOSHI Supervisor System - Quick Start Guide

## What Is This?

The Supervisor System lets you (Claude Code / Admin) inject suggestions into MOSHI's voice conversations in real-time. Think of it as giving MOSHI "telepathic hints" during phone calls.

## Quick Start (2 Terminals)

### Terminal 1: Start the Servers
```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss
cargo run --bin xswarm voice-bridge
```

You'll see:
```
╔══════════════════════════════════════════════════════════╗
║              MOSHI Voice Bridge + Supervisor            ║
╚══════════════════════════════════════════════════════════╝

🎤 Voice Bridge: ws://127.0.0.1:9998
🔍 Supervisor API: ws://127.0.0.1:9999
   Auth Token: dev-token-12345

🚀 Both servers are ready!
```

### Terminal 2: Start the Monitor
```bash
cargo run --bin supervisor-cli
```

You'll see:
```
╔══════════════════════════════════════════════════════════╗
║           MOSHI SUPERVISOR - CLI Monitor                 ║
╚══════════════════════════════════════════════════════════╝

✓ Authenticated successfully

> _
```

## Usage

### Inject a Suggestion
```
> i The user mentioned Stripe. Explain subscription billing.
```

MOSHI will receive this as text conditioning and incorporate it into the response.

### Other Commands
- `h` - Help
- `q` - Quit
- `clear` - Clear screen

## How It Works

```
You type:  i The user wants to know about pricing
    ↓
Supervisor API receives suggestion
    ↓
Queued in MOSHI's suggestion_queue
    ↓
MOSHI's next inference loop:
    1. Pops suggestion from queue
    2. Tokenizes: "The user wants..." → [token IDs]
    3. Creates tensor for text conditioning
    4. Injects into language model forward pass
    5. MOSHI generates response influenced by suggestion
    ↓
MOSHI speaks: "Let me explain our pricing structure..."
```

## Configuration

### Environment Variables
```bash
export SUPERVISOR_HOST="127.0.0.1"
export SUPERVISOR_PORT="9999"
export SUPERVISOR_TOKEN="dev-token-12345"
```

### Rate Limiting
- Default: 1 suggestion every 2 seconds
- Max queue: 5 pending suggestions
- Configurable in code

## Testing Without Phone Calls

You can test the system by:

1. Starting both servers (Terminal 1)
2. Starting the CLI (Terminal 2)
3. Injecting suggestions
4. Watching the voice bridge logs:
   ```bash
   # Terminal 3
   tail -f /tmp/voice-bridge.log | grep "Injecting"
   ```

You'll see:
```
INFO xswarm::voice: Injecting supervisor suggestion suggestion="..."
DEBUG xswarm::voice: Text tokenized successfully num_tokens=15
```

## Production RAG Pattern

In production, replace the CLI with a RAG service:

```rust
// When user asks a question MOSHI doesn't know:
let rag_context = query_vector_db(user_question).await?;
let api_data = fetch_stripe_api(user_id).await?;

let suggestion = format!(
    "User subscription: {}, Next billing: {}",
    api_data.plan,
    api_data.next_billing_date
);

supervisor_client.inject_suggestion(&suggestion).await?;
// MOSHI receives suggestion and incorporates into response
```

## Troubleshooting

### "Connection refused"
Make sure Terminal 1 (voice bridge) is running first.

### "Authentication failed"
Check that `SUPERVISOR_TOKEN` matches in both places.

### "Rate limited"
Wait 2 seconds between injections (or adjust rate limit).

### "Queue full"
Max 5 pending suggestions. Wait for MOSHI to process them.

## Files Modified/Created

- `packages/core/src/voice.rs` - Text conditioning core
- `packages/core/src/supervisor.rs` - WebSocket API (374 lines)
- `packages/core/src/bin/supervisor-cli.rs` - CLI interface (315 lines)
- `packages/core/src/main.rs` - Integration in voice-bridge command
- `packages/core/Cargo.toml` - Added chrono, url dependencies

## Next Steps

1. Test with a real phone call (Twilio → Voice Bridge)
2. Build a RAG service that uses the supervisor API
3. Add multi-channel communication (SMS, email)
4. Implement monitoring/metrics

## Full Documentation

See `/planning/SUPERVISOR_SYSTEM.md` for complete architecture details, API reference, and production patterns.

## Support

- GitHub Issues: https://github.com/your-repo/issues
- Architecture: `/planning/ARCHITECTURE.md`
- Features: `/planning/FEATURES.md`
