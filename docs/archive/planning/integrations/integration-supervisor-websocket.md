# Supervisor WebSocket Integration

This document describes the WebSocket-based integration between the Node.js Cloudflare Workers server and the Rust supervisor system.

## Architecture Overview

```
SMS/Email Webhook → Node.js Server → WebSocket → Rust Supervisor → AI Processing
                                    ↓
                              WebSocket Response
                                    ↓
                          Twilio/SendGrid API → User
```

## Components

### 1. Rust Supervisor (`packages/core/src/supervisor.rs`)

**WebSocket Server:**
- Listens on: `ws://127.0.0.1:9999`
- Authentication: Token-based (`SUPERVISOR_TOKEN` or `dev-token-12345`)
- Protocol: JSON messages with `type` field for routing

**New Message Types (Incoming):**

```rust
SmsReceived {
    from: String,      // User phone number
    to: String,        // Boss phone number
    message: String,   // SMS text
    user: String,      // User identifier
}

EmailReceived {
    from: String,      // User email
    to: String,        // Boss email
    subject: String,   // Email subject
    body: String,      // Email body
    user: String,      // User identifier
}
```

**New Event Types (Outgoing):**

```rust
MessageAcknowledged {
    message_type: String,  // "sms" or "email"
    user: String,          // User identifier
    timestamp: String,     // ISO 8601 timestamp
}

SendSmsResponse {
    to: String,       // Phone number to send to
    message: String,  // SMS text response
    user: String,     // User identifier
}

SendEmailResponse {
    to: String,       // Email to send to
    subject: String,  // Email subject
    body: String,     // Email body
    user: String,     // User identifier
}
```

### 2. Node.js WebSocket Client (`packages/server/src/lib/supervisor-client.js`)

**Features:**
- Automatic connection and authentication
- Reconnection with exponential backoff
- Message routing with timeouts
- Promise-based API for request/response

**Public API:**

```javascript
// Get singleton instance
const supervisor = getSupervisorClient({ authToken: 'token' });

// Send SMS event
const response = await supervisor.sendSmsEvent({
  from: '+15551234567',
  to: '+15559876543',
  message: 'User message',
  user: 'username',
});

// Send Email event
const response = await supervisor.sendEmailEvent({
  from: 'user@example.com',
  to: 'boss@example.com',
  subject: 'Subject',
  body: 'Message body',
  user: 'username',
});

// Check connection status
if (supervisor.isReady()) {
  // Connected and authenticated
}
```

### 3. Webhook Integration

**SMS Handler (`packages/server/src/routes/sms.js`):**
1. Receives SMS webhook from Twilio
2. Validates user authorization
3. Tries to send to supervisor WebSocket
4. Falls back to local Claude AI processing if supervisor unavailable
5. Returns TwiML response to Twilio

**Email Handler (`packages/server/src/routes/email.js`):**
1. Receives email webhook from SendGrid
2. Validates user authorization
3. Tries to send to supervisor WebSocket
4. Falls back to local Claude AI processing if supervisor unavailable
5. Sends response via SendGrid API

## Event Flow

### SMS Event Flow

```
1. User sends SMS to Boss phone number
2. Twilio webhook → Node.js server
3. Node.js validates authorization
4. Node.js sends SmsReceived → Supervisor WebSocket
5. Supervisor processes (currently just acknowledges)
6. Supervisor sends MessageAcknowledged → Node.js
7. Node.js falls back to local Claude AI processing
8. Node.js returns TwiML response → Twilio
9. Twilio sends SMS to user
```

### Email Event Flow

```
1. User sends email to Boss email address
2. SendGrid webhook → Node.js server
3. Node.js validates authorization
4. Node.js sends EmailReceived → Supervisor WebSocket
5. Supervisor processes (currently just acknowledges)
6. Supervisor sends MessageAcknowledged → Node.js
7. Node.js falls back to local Claude AI processing
8. Node.js sends email via SendGrid API
9. User receives email response
```

## Current Implementation Status

### ✅ Completed

1. **Rust Supervisor Extensions:**
   - Added `SmsReceived` and `EmailReceived` message types
   - Added `SendSmsResponse` and `SendEmailResponse` event types
   - Added `MessageAcknowledged` event type
   - Implemented `handle_sms_received()` method
   - Implemented `handle_email_received()` method
   - Currently return acknowledgments (AI processing TBD)

2. **Node.js WebSocket Client:**
   - Full WebSocket client implementation with reconnection
   - Authentication flow
   - Promise-based request/response API
   - Message routing and timeout handling
   - Singleton pattern for shared connection

3. **Webhook Integration:**
   - SMS webhook tries supervisor first, falls back to local
   - Email webhook tries supervisor first, falls back to local
   - Graceful degradation when supervisor unavailable

### 🚧 TODO (Future Enhancements)

1. **AI Processing in Supervisor:**
   - Integrate Claude API calls in Rust supervisor
   - Generate intelligent responses for SMS/Email
   - Return `SendSmsResponse` / `SendEmailResponse` instead of acknowledgments

2. **Response Handling in Node.js:**
   - Handle `SendSmsResponse` events (send SMS via Twilio)
   - Handle `SendEmailResponse` events (send email via SendGrid)

3. **Production Deployment:**
   - Note: Cloudflare Workers don't support WebSocket clients
   - This integration only works in local development mode
   - For production, consider HTTP API or alternative architecture

## Testing

### Prerequisites

1. Start Rust supervisor:
   ```bash
   cd packages/core
   cargo run --bin xswarm
   ```

2. Supervisor should show:
   ```
   Supervisor WebSocket server listening on 127.0.0.1:9999
   ```

### Run Integration Test

```bash
node scripts/test-supervisor-integration.js
```

Expected output:
```
🧪 Testing Supervisor WebSocket Integration

📡 Test 1: Connecting to supervisor...
✅ Connected and authenticated

📱 Test 2: Sending SMS event...
✅ SMS event sent successfully

📧 Test 3: Sending Email event...
✅ Email event sent successfully

🏓 Test 4: Sending ping...
✅ Ping sent

🔍 Test 5: Checking connection status...
✅ Connection status: Ready

✨ All tests passed! Supervisor integration is working.
```

### Manual Testing

1. **Test SMS Integration:**
   ```bash
   # Send test SMS webhook (requires ngrok and Twilio setup)
   curl -X POST http://localhost:8787/sms/inbound \
     -d "From=+15551234567" \
     -d "To=+15559876543" \
     -d "Body=Test message"
   ```

2. **Test Email Integration:**
   ```bash
   # Send test email webhook (requires SendGrid setup)
   curl -X POST http://localhost:8787/email/inbound \
     -d "from=user@example.com" \
     -d "to=boss@example.com" \
     -d "subject=Test" \
     -d "text=Test message"
   ```

3. **Monitor Supervisor Logs:**
   The Rust supervisor will show incoming events:
   ```
   SMS received from webhook: user=testuser, from=+15551234567, message="Test message"
   SMS processing not yet implemented - returning acknowledgment
   ```

## Configuration

### Environment Variables

**Rust Supervisor:**
- `SUPERVISOR_TOKEN`: Authentication token (default: `dev-token-12345`)

**Node.js Server:**
- `SUPERVISOR_URL`: WebSocket URL (default: `ws://127.0.0.1:9999`)
- `SUPERVISOR_TOKEN`: Authentication token (default: `dev-token-12345`)
- `ENVIRONMENT`: Set to `local` to enable supervisor integration

## Error Handling

The integration includes multiple layers of error handling:

1. **Connection Errors:**
   - Automatic reconnection with exponential backoff
   - Falls back to local processing if supervisor unavailable

2. **Authentication Errors:**
   - Clear error messages
   - Prevents requests until authenticated

3. **Message Timeouts:**
   - 10-second timeout for each request
   - Returns error if supervisor doesn't respond

4. **Graceful Degradation:**
   - If supervisor unavailable, webhooks still work with local Claude AI
   - No user-facing errors when supervisor is down

## Benefits of WebSocket Approach

1. **Real-time Communication:** Bidirectional, event-driven
2. **Persistent Connection:** No connection overhead per request
3. **Event Broadcasting:** Supervisor can push events to Node.js
4. **Reuses Existing Infrastructure:** Same supervisor used for voice calls
5. **Clean Separation:** Rust handles AI/processing, Node.js handles HTTP/webhooks

## Limitations

1. **Cloudflare Workers:** Don't support WebSocket clients in production
2. **Local Development Only:** Integration works in local dev environment
3. **Single Connection:** Singleton pattern means one shared connection
4. **No Load Balancing:** Direct connection to single supervisor instance

## Future Directions

1. **HTTP API Option:** For production Cloudflare Workers deployment
2. **Message Queue:** For async processing and better scalability
3. **Multiple Supervisors:** Load balancing across supervisor instances
4. **Production Architecture:** Consider alternatives for Cloudflare Workers environment
