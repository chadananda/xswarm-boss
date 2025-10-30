# Supervisor WebSocket Integration - Quick Start

This guide shows how to use the WebSocket integration between the Node.js server and Rust supervisor.

## Quick Start

### 1. Start the Rust Supervisor

```bash
cd packages/core
cargo run --bin xswarm
```

You should see:
```
Supervisor WebSocket server listening on 127.0.0.1:9999
```

### 2. Test the Integration

```bash
node scripts/test-supervisor-integration.js
```

Expected output:
```
✨ All tests passed! Supervisor integration is working.
```

### 3. Start the Node.js Server

```bash
cd packages/server
npm run dev
```

## Usage in Code

### SMS Webhook (Automatic)

The SMS webhook handler automatically tries the supervisor:

```javascript
// packages/server/src/routes/sms.js
import { getSupervisorClient } from '../lib/supervisor-client.js';

async function processCommand(user, message, env) {
  const supervisor = getSupervisorClient({
    authToken: env.SUPERVISOR_TOKEN || 'dev-token-12345',
  });

  if (supervisor.isReady()) {
    // Send to supervisor
    const response = await supervisor.sendSmsEvent({
      from: user.phone,
      to: user.bossPhone,
      message: message,
      user: user.username,
    });

    // Use supervisor response if available
    if (response.type === 'send_sms_response') {
      return response.message;
    }
  }

  // Fallback to local processing
  return await getClaudeResponse(user, message, 'sms', env);
}
```

### Email Webhook (Automatic)

The email webhook handler automatically tries the supervisor:

```javascript
// packages/server/src/routes/email.js
import { getSupervisorClient } from '../lib/supervisor-client.js';

async function processEmailWithAI(user, subject, content, env) {
  const supervisor = getSupervisorClient({
    authToken: env.SUPERVISOR_TOKEN || 'dev-token-12345',
  });

  if (supervisor.isReady()) {
    // Send to supervisor
    const response = await supervisor.sendEmailEvent({
      from: user.email,
      to: user.bossEmail,
      subject: subject,
      body: content,
      user: user.username,
    });

    // Use supervisor response if available
    if (response.type === 'send_email_response') {
      return response.body;
    }
  }

  // Fallback to local processing
  return await getClaudeResponse(user, fullMessage, 'email', env);
}
```

## Message Flow

### SMS Flow

```
User → Twilio → Node.js Webhook → Supervisor WebSocket → Rust AI
                    ↓                       ↓
                TwiML Response ← Node.js ← WebSocket Response
                    ↓
              Twilio → User
```

### Email Flow

```
User → SendGrid → Node.js Webhook → Supervisor WebSocket → Rust AI
                      ↓                       ↓
             SendGrid API ← Node.js ← WebSocket Response
                      ↓
                    User
```

## Configuration

### Environment Variables

Create `.env.local` or set in Wrangler secrets:

```bash
# Supervisor WebSocket Configuration
SUPERVISOR_URL=ws://127.0.0.1:9999
SUPERVISOR_TOKEN=dev-token-12345
ENVIRONMENT=local
```

### Wrangler Configuration

```toml
# wrangler.toml
[vars]
SUPERVISOR_URL = "ws://127.0.0.1:9999"
SUPERVISOR_TOKEN = "dev-token-12345"
ENVIRONMENT = "local"
```

## API Reference

### SupervisorClient

```javascript
import { getSupervisorClient } from './lib/supervisor-client.js';

const client = getSupervisorClient({
  url: 'ws://127.0.0.1:9999',
  authToken: 'dev-token-12345',
});
```

#### Methods

**`connect()`**
Connect to supervisor WebSocket and authenticate.

```javascript
await client.connect();
```

**`sendSmsEvent(data)`**
Send SMS event to supervisor.

```javascript
const response = await client.sendSmsEvent({
  from: '+15551234567',
  to: '+15559876543',
  message: 'Hello Boss!',
  user: 'username',
});
```

**`sendEmailEvent(data)`**
Send Email event to supervisor.

```javascript
const response = await client.sendEmailEvent({
  from: 'user@example.com',
  to: 'boss@example.com',
  subject: 'Question about project',
  body: 'Can you help me with...?',
  user: 'username',
});
```

**`isReady()`**
Check if connected and authenticated.

```javascript
if (client.isReady()) {
  // Safe to send messages
}
```

**`disconnect()`**
Close WebSocket connection.

```javascript
client.disconnect();
```

## Event Types

### Incoming Events (Node.js → Rust)

**SmsReceived**
```json
{
  "type": "sms_received",
  "from": "+15551234567",
  "to": "+15559876543",
  "message": "User message",
  "user": "username"
}
```

**EmailReceived**
```json
{
  "type": "email_received",
  "from": "user@example.com",
  "to": "boss@example.com",
  "subject": "Question",
  "body": "Message body",
  "user": "username"
}
```

### Outgoing Events (Rust → Node.js)

**MessageAcknowledged**
```json
{
  "type": "message_acknowledged",
  "message_type": "sms",
  "user": "username",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**SendSmsResponse** (TODO: Not yet implemented in Rust)
```json
{
  "type": "send_sms_response",
  "to": "+15551234567",
  "message": "AI-generated response",
  "user": "username"
}
```

**SendEmailResponse** (TODO: Not yet implemented in Rust)
```json
{
  "type": "send_email_response",
  "to": "user@example.com",
  "subject": "Re: Question",
  "body": "AI-generated response",
  "user": "username"
}
```

## Error Handling

The integration includes automatic fallback:

1. **Supervisor unavailable:** Falls back to local Claude AI
2. **Connection lost:** Automatic reconnection with exponential backoff
3. **Timeout:** 10-second timeout, then fallback
4. **Authentication failure:** Clear error message

No user-facing errors occur when supervisor is down.

## Troubleshooting

### "WebSocket not connected"

Make sure Rust supervisor is running:
```bash
cd packages/core
cargo run --bin xswarm
```

### "Authentication failed"

Check that auth tokens match:
- Rust: `SUPERVISOR_TOKEN` env var or default `dev-token-12345`
- Node.js: Pass same token to `getSupervisorClient()`

### "Connection refused"

Check supervisor is listening on correct port:
```bash
lsof -i :9999
```

Should show:
```
COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
xswarm  12345 user   10u  IPv4 123456      0t0  TCP localhost:9999 (LISTEN)
```

### Supervisor not responding

Check Rust logs for errors:
```
tail -f logs/supervisor.log
```

## Production Notes

**⚠️ Important:** Cloudflare Workers do not support WebSocket clients in production.

This integration only works in local development with Node.js.

For production deployment on Cloudflare Workers, consider:
1. HTTP API instead of WebSocket
2. Message queue (Redis, RabbitMQ)
3. Direct Claude API calls from Workers

## Next Steps

1. **Implement AI Processing in Rust:** Add Claude API integration
2. **Return Smart Responses:** Change from acknowledgments to actual AI responses
3. **Add Response Handlers:** Handle `SendSmsResponse` and `SendEmailResponse` in Node.js
4. **Production Architecture:** Design HTTP API or alternative for Cloudflare Workers

## See Also

- [Full Documentation](../../planning/SUPERVISOR_WEBSOCKET_INTEGRATION.md)
- [Supervisor Implementation](../core/src/supervisor.rs)
- [WebSocket Client](./src/lib/supervisor-client.js)
