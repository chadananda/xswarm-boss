# HTTP API Quick Start Guide

## 5-Minute Setup

Get the HTTP API server running and test it in 5 minutes.

### Step 1: Start the API Server

```bash
cd /path/to/xswarm-boss
cargo run --bin xswarm -- api-server
```

You should see:

```
╔══════════════════════════════════════════════════════════╗
║                   HTTP API Server                        ║
╚══════════════════════════════════════════════════════════╝

🌐 API Server:
   Host: 127.0.0.1
   Port: 9997
   Base URL: http://127.0.0.1:9997
   API Token: dev-api-token-12345

📡 Available Endpoints:
   GET  /health
   GET  /api/status
   POST /api/sms/send
   POST /api/email/send
   POST /api/tasks/execute
   GET  /api/users/:username/config
   PUT  /api/users/:username/config

🚀 Server is ready!
   Waiting for requests from Node.js server...
```

### Step 2: Test the API

In another terminal, run the test script:

```bash
node scripts/test-api.js
```

Expected output:

```
╔══════════════════════════════════════════════════════════╗
║          HTTP API Test Suite                            ║
╚══════════════════════════════════════════════════════════╝

🔌 Testing API at: http://127.0.0.1:9997

🏥 Testing Health Check...
✅ Health check: OK

📊 Testing Status Endpoint...
✅ Status: {
  "status": "ready",
  "voice_bridge": "running",
  "supervisor": "running",
  "tasks": 0,
  "uptime": 42
}

📱 Testing SMS Send...
✅ SMS Response: {
  "success": true,
  "message": "SMS queued for delivery to +19167656913",
  "message_sid": "SM12345678-1234-1234-1234-123456789012"
}

... (more tests) ...

🎉 All tests passed!
```

### Step 3: Try It Yourself

Test with cURL:

```bash
# Health check
curl http://127.0.0.1:9997/health

# Get status
curl http://127.0.0.1:9997/api/status

# Send SMS
curl -X POST http://127.0.0.1:9997/api/sms/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "+19167656913",
    "message": "Hello from the API!",
    "user": "chadananda"
  }'

# Execute a task
curl -X POST http://127.0.0.1:9997/api/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "run unit tests",
    "user": "chadananda",
    "priority": "high",
    "channel": "email"
  }'
```

---

## Integration with Node.js Server

### From Cloudflare Workers

```javascript
// In your Cloudflare Worker
export default {
  async fetch(request, env) {
    // When you receive a webhook from Twilio/SendGrid
    const webhookData = await request.json();

    // Forward action to Rust client
    const response = await fetch('http://127.0.0.1:9997/api/tasks/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        task: webhookData.message,
        user: webhookData.from,
        priority: 'normal',
        channel: 'email'
      })
    });

    const result = await response.json();
    console.log('Task queued:', result.task_id);

    return new Response('OK', { status: 200 });
  }
};
```

### From Node.js Express

```javascript
const express = require('express');
const app = express();

app.post('/webhooks/twilio/sms', async (req, res) => {
  const { From, Body } = req.body;

  // Forward SMS to Rust client for processing
  const response = await fetch('http://127.0.0.1:9997/api/tasks/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      task: Body,
      user: From,
      priority: 'normal',
      channel: 'sms'
    })
  });

  const result = await response.json();

  res.send('<Response></Response>'); // TwiML response
});

app.listen(3000);
```

---

## Next Steps

1. **Read Full Docs:** See [HTTP_API.md](./HTTP_API.md) for complete API reference
2. **Add Authentication:** Set `API_TOKEN` environment variable
3. **Integrate Services:** Add Twilio/SendGrid credentials
4. **Deploy:** Run API server as systemd service or Docker container

---

## Troubleshooting

### API Server Won't Start

```bash
# Check if port is in use
lsof -i :9997

# Try a different port
cargo run --bin xswarm -- api-server --port 8080
```

### Tests Failing

```bash
# Make sure API server is running
curl http://127.0.0.1:9997/health

# Check server logs for errors
# (Server logs appear in terminal where you ran cargo run)

# Verify Node.js version
node --version  # Should be v18+
```

### Connection Refused

Make sure:
1. API server is running
2. Using correct host/port (default: 127.0.0.1:9997)
3. Firewall allows connections on port 9997

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    External Services                    │
│  Twilio (SMS/Voice)  │  SendGrid (Email)  │  Stripe    │
└─────────────────────┬───────────────────────────────────┘
                      │ Webhooks
                      ↓
┌─────────────────────────────────────────────────────────┐
│              Node.js Server (Cloudflare Workers)        │
│  • Receives webhooks from external services             │
│  • Routes to Rust client via HTTP API                   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP POST/GET
                      ↓
┌─────────────────────────────────────────────────────────┐
│                Rust Client (HTTP API Server)            │
│  • Processes tasks with Claude AI                       │
│  • Executes development commands                        │
│  • Manages MOSHI voice conversations                    │
│  • Sends notifications back to users                    │
└─────────────────────────────────────────────────────────┘
```

**Key Insight:** The Rust client exposes an HTTP API so the Node.js server can:
- Trigger SMS/Email sending via Rust client
- Execute development tasks
- Manage user configurations
- Get system status

This bridges the gap between webhook-based communication (Twilio/SendGrid) and the local development environment (Rust client).

---

## What's Working

✅ **HTTP API Server**
- Axum-based REST API
- JSON request/response
- Error handling
- Multiple endpoints

✅ **Core Endpoints**
- Health check
- Status reporting
- User configuration (get/update)

✅ **Task Integration**
- AI-powered task analysis
- Task execution planning
- Priority levels

✅ **Testing**
- Comprehensive test suite
- cURL examples
- Node.js integration examples

## What's Pending

⚠️ **Service Integration**
- Twilio SMS sending (stub implemented)
- SendGrid email sending (stub implemented)
- Database for user configs
- Authentication middleware

⚠️ **Advanced Features**
- WebSocket for real-time updates
- Task queue management
- Webhook callbacks
- Metrics/monitoring

---

## Need Help?

- **Full API Docs:** [HTTP_API.md](./HTTP_API.md)
- **Architecture:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Configuration:** [CONFIG_SECRETS.md](./CONFIG_SECRETS.md)

**Quick Test:**
```bash
# Terminal 1: Start server
cargo run --bin xswarm -- api-server

# Terminal 2: Run tests
node scripts/test-api.js
```

That's it! You now have a working HTTP API bridge between your Node.js server and Rust client. 🚀
