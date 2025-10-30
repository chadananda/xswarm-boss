# Claude Code Message Routing System

## Overview

The xSwarm Boss system now includes intelligent message routing that enables Admin users to communicate with Claude Code sessions through any channel (SMS, Email, or Voice). When the Admin sends a message through Boss, it is automatically detected and routed to an active Claude Code session for processing, and responses are sent back through the same channel.

## Architecture

```
┌─────────────┐
│   Admin     │
│   User      │
└──────┬──────┘
       │
       │ (SMS/Email/Voice)
       ▼
┌─────────────────────────────────┐
│  Boss Communication Channels    │
│  - Twilio (SMS/Voice)          │
│  - SendGrid (Email)            │
│  - MOSHI (Voice Transcription) │
└──────┬──────────────────────────┘
       │
       │ Webhook/WS
       ▼
┌─────────────────────────────────┐
│  Supervisor System (Rust)       │
│  - Admin Detection              │
│  - Message Routing              │
│  - Session Management           │
└──────┬──────────────────────────┘
       │
       │ WebSocket
       ▼
┌─────────────────────────────────┐
│  Claude Code Connector          │
│  - Session Tracking             │
│  - Cost Monitoring              │
│  - Bidirectional Communication  │
└──────┬──────────────────────────┘
       │
       │ WebSocket
       ▼
┌─────────────────────────────────┐
│  Claude Code                    │
│  - Project Analysis             │
│  - Code Generation              │
│  - Task Execution               │
└─────────────────────────────────┘
```

## Key Components

### 1. Supervisor System (`packages/core/src/supervisor.rs`)

The supervisor handles incoming messages from all channels and routes them appropriately:

**Admin Detection:**
- Checks user identity via `ServerClient`
- Verifies `can_provision_numbers` permission (Admin-only)
- Matches phone/email against Admin user configuration

**Message Routing:**
- SMS: `handle_sms_received()` - Routes Admin SMS to Claude Code
- Email: `handle_email_received()` - Routes Admin emails to Claude Code
- Voice: `handle_voice_transcription()` - Routes Admin voice transcriptions to Claude Code

**Response Routing:**
- Returns `SupervisorEvent::SendSmsResponse` for SMS replies
- Returns `SupervisorEvent::SendEmailResponse` for email replies
- Returns text response for voice synthesis

### 2. Claude Code Connector (`packages/core/src/claude_code.rs`)

Manages WebSocket connections to Claude Code instances:

**Features:**
- Session creation and management
- Cost tracking per session and per user
- Message serialization/deserialization
- Connection lifecycle management
- Idle session cleanup

**Configuration:**
```rust
ClaudeCodeConfig {
    websocket_url: "ws://localhost:8080",
    auth_token: Option<String>,
    max_sessions: 10,
    idle_timeout_seconds: 300,
    track_costs: true,
}
```

### 3. Server Client (`packages/core/src/server_client.rs`)

Provides user identity validation:

- Fetches user identity from Node.js server
- Caches identity during session
- Validates Admin permissions
- Health checks and authentication

## Usage

### Starting the Voice Bridge with Claude Code Integration

```bash
# Start voice bridge with Claude Code routing enabled
cargo run --bin xswarm -- voice-bridge \
  --enable-claude-code \
  --claude-code-url ws://localhost:8080

# With custom ports
cargo run --bin xswarm -- voice-bridge \
  --host 0.0.0.0 \
  --port 9998 \
  --supervisor-port 9999 \
  --enable-claude-code \
  --claude-code-url ws://localhost:8080
```

### Environment Variables

```bash
# Optional: Claude Code authentication token
export CLAUDE_CODE_AUTH_TOKEN="your-token-here"

# Required: Server authentication for user identity
export XSWARM_AUTH_TOKEN="your-server-token"

# Optional: Supervisor authentication
export SUPERVISOR_TOKEN="your-supervisor-token"
```

### CLI Commands

**Check Session Status:**
```bash
# View all active Claude Code sessions
cargo run --bin xswarm -- claude status

# View specific session
cargo run --bin xswarm -- claude status --session-id <session-id>
```

**Track Costs:**
```bash
# View total costs across all users
cargo run --bin xswarm -- claude cost

# View costs for specific user
cargo run --bin xswarm -- claude cost --user-id admin
```

**Connect to Session:**
```bash
# Connect to existing Claude Code session
cargo run --bin xswarm -- claude connect --session-id <session-id>
```

## Message Flow Examples

### SMS Flow

1. **Admin sends SMS** to Boss phone number
2. **Twilio webhook** forwards to Node.js server
3. **Node.js** sends `SmsReceived` to Supervisor via WebSocket
4. **Supervisor** detects Admin user, routes to Claude Code
5. **Claude Code** processes message, returns response
6. **Supervisor** sends `SendSmsResponse` event
7. **Node.js** sends SMS via Twilio to Admin

### Email Flow

1. **Admin sends email** to Boss email address
2. **SendGrid webhook** forwards to Node.js server
3. **Node.js** sends `EmailReceived` to Supervisor via WebSocket
4. **Supervisor** detects Admin user, routes to Claude Code
5. **Claude Code** processes message, returns response
6. **Supervisor** sends `SendEmailResponse` event
7. **Node.js** sends email via SendGrid to Admin

### Voice Flow

1. **Admin calls** Boss phone number
2. **Twilio** connects to Voice Bridge WebSocket
3. **MOSHI** transcribes speech in real-time
4. **Voice Bridge** broadcasts `UserTranscription` to Supervisor
5. **Supervisor** detects Admin user, routes to Claude Code
6. **Claude Code** processes transcription, returns response
7. **Supervisor** synthesizes response to speech
8. **Voice Bridge** streams audio back to Twilio call

## Message Context

Each message includes channel-specific context:

**SMS Context:**
```json
{
  "channel": "sms",
  "from": "+15551234567",
  "to": "+18005551001"
}
```

**Email Context:**
```json
{
  "channel": "email",
  "from": "admin@example.com",
  "to": "boss@xswarm.ai",
  "subject": "Project Update Request"
}
```

**Voice Context:**
```json
{
  "channel": "voice",
  "user_id": "admin"
}
```

## Session Management

**Automatic Session Creation:**
- If no active session exists for the Admin user, one is created automatically
- Sessions use project path `/current/project` by default
- Each user can have multiple sessions (configurable max: 10)

**Session Lifecycle:**
- `Connecting` → `Active` → `Idle` → `Disconnected`
- Idle timeout: 300 seconds (5 minutes) by default
- Automatic cleanup of idle sessions

**Session Tracking:**
- Unique session ID (UUID)
- User ID association
- Project path
- Message count
- Total cost (USD)
- Start/end timestamps
- Last activity timestamp

## Cost Tracking

Each Claude Code interaction tracks:
- Per-message cost
- Per-session total cost
- Per-user total cost across all sessions

Cost information is included in responses and can be queried via CLI.

## Security

**Admin Detection:**
- Verified via server client user identity
- Requires `can_provision_numbers` permission
- Phone/email must match Admin user configuration

**Authentication:**
- Server client auth via `XSWARM_AUTH_TOKEN`
- Supervisor auth via `SUPERVISOR_TOKEN`
- Claude Code auth via `CLAUDE_CODE_AUTH_TOKEN` (optional)

**Non-Admin Messages:**
- Acknowledged but not routed to Claude Code
- Can be processed by other AI systems in the future
- Logged for monitoring

## Error Handling

**Graceful Degradation:**
- If Claude Code is unavailable, messages are acknowledged
- Connection failures are logged and retried
- Session errors don't crash the supervisor
- User receives error message via original channel

**Logging:**
- All routing decisions logged
- Session lifecycle events tracked
- Errors logged with context
- Cost tracking for monitoring

## Future Enhancements

**Planned Features:**
- Multi-project session support
- Session persistence across restarts
- Advanced cost limits per user
- Message queuing for offline Claude Code
- WebSocket reconnection with exponential backoff
- Admin notification when Claude Code is offline
- Voice response streaming for lower latency
- Context sharing across channels (cross-channel memory)

## Testing

**Manual Testing:**
```bash
# 1. Start voice bridge with Claude Code
cargo run --bin xswarm -- voice-bridge --enable-claude-code

# 2. In another terminal, test SMS routing
curl -X POST http://localhost:8787/api/webhooks/sms \
  -H "Content-Type: application/json" \
  -d '{
    "From": "+15551234567",
    "To": "+18005551001",
    "Body": "What is the status of the xswarm project?"
  }'

# 3. Check session status
cargo run --bin xswarm -- claude status

# 4. Monitor costs
cargo run --bin xswarm -- claude cost --user-id admin
```

## Debugging

**Enable verbose logging:**
```bash
RUST_LOG=debug cargo run --bin xswarm -- voice-bridge --enable-claude-code
```

**Common issues:**
- **No response from Claude Code**: Check WebSocket URL and ensure Claude Code is running
- **Admin not detected**: Verify server client connection and user identity
- **Session creation fails**: Check max_sessions limit and active session count
- **WebSocket connection fails**: Verify firewall rules and network connectivity

## Related Files

- `packages/core/src/supervisor.rs` - Message routing logic
- `packages/core/src/claude_code.rs` - Claude Code connector
- `packages/core/src/server_client.rs` - User identity validation
- `packages/core/src/main.rs` - CLI commands
- `packages/core/src/voice.rs` - Voice transcription broadcasting
- `packages/core/src/config.rs` - Configuration structures
