# HTTP API Documentation

## Overview

The HTTP API provides REST endpoints that enable the Node.js Cloudflare Workers server to communicate with the Rust client for SMS, Email, and task execution functionality.

**Base URL:** `http://127.0.0.1:9997`

**Architecture:**
- Node.js server receives webhooks from Twilio/SendGrid
- Node.js server forwards actions to Rust client via HTTP API
- Rust client executes tasks and sends notifications
- Rust client uses Claude AI for intelligent task processing

## Starting the API Server

```bash
# Start with default settings (127.0.0.1:9997)
cargo run --bin xswarm -- api-server

# Start with custom host/port
cargo run --bin xswarm -- api-server --host 0.0.0.0 --port 8080

# Set API token for authentication (optional)
export API_TOKEN="your-secure-token"
cargo run --bin xswarm -- api-server
```

## Authentication

Currently using simple token-based authentication (stored in environment variable):

```bash
export API_TOKEN="dev-api-token-12345"
```

**TODO:** Implement proper authentication middleware in future versions.

## Endpoints

### Health Check

**GET** `/health`

Health check endpoint to verify server is running.

**Response:**
```
OK
```

---

### Get Status

**GET** `/api/status`

Get current status of the Rust client including uptime, active components, and task count.

**Response:**
```json
{
  "status": "ready",
  "voice_bridge": "running",
  "supervisor": "running",
  "tasks": 2,
  "uptime": 3600
}
```

**Fields:**
- `status`: Current system status (ready, busy, error)
- `voice_bridge`: Status of MOSHI voice bridge (running, stopped)
- `supervisor`: Status of supervisor system (running, stopped)
- `tasks`: Number of active tasks
- `uptime`: System uptime in seconds

---

### Send SMS

**POST** `/api/sms/send`

Send an SMS message to a user via the Rust client.

**Request Body:**
```json
{
  "to": "+19167656913",
  "message": "Your task has been completed successfully!",
  "user": "chadananda"
}
```

**Response:**
```json
{
  "success": true,
  "message": "SMS queued for delivery to +19167656913",
  "message_sid": "SM12345678-1234-1234-1234-123456789012"
}
```

**Fields:**
- `to`: Recipient phone number (E.164 format)
- `message`: SMS message content (max 160 characters recommended)
- `user`: Username of the requesting user

**Integration Status:** ⚠️ Twilio integration pending

---

### Send Email

**POST** `/api/email/send`

Send an email to a user via the Rust client.

**Request Body:**
```json
{
  "to": "chad@example.com",
  "subject": "Task Completion Report",
  "body": "Your development task has been completed successfully!",
  "user": "chadananda"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email queued for delivery to chad@example.com",
  "message_id": "EM12345678-1234-1234-1234-123456789012"
}
```

**Fields:**
- `to`: Recipient email address
- `subject`: Email subject line
- `body`: Email body content (plain text)
- `user`: Username of the requesting user

**Integration Status:** ⚠️ SendGrid integration pending

---

### Execute Task

**POST** `/api/tasks/execute`

Execute a development task using AI and the supervisor system.

**Request Body:**
```json
{
  "task": "run tests on the authentication module",
  "user": "chadananda",
  "priority": "high",
  "channel": "sms"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task queued for execution: run tests on the authentication module",
  "task_id": "TASK12345678-1234-1234-1234-123456789012"
}
```

**Fields:**
- `task`: Task description (plain text)
- `user`: Username of the requesting user
- `priority`: Task priority (high, normal, low) - default: normal
- `channel`: Notification channel (email, sms, voice) - default: email

**Priority Levels:**
- `high`: Urgent tasks, immediate execution
- `normal`: Standard priority (default)
- `low`: Background tasks, deferred execution

**Notification Channels:**
- `email`: Send completion notification via email
- `sms`: Send completion notification via SMS
- `voice`: Call user when task completes

**Integration Status:** ⚠️ Task execution uses AI analysis, full supervisor integration pending

---

### Get User Config

**GET** `/api/users/:username/config`

Get configuration for a specific user.

**Path Parameters:**
- `username`: Username (e.g., "chadananda")

**Response:**
```json
{
  "username": "chadananda",
  "persona": "hal-9000",
  "voice_enabled": true,
  "wake_word": "hey hal",
  "email": "chad@example.com",
  "phone": "+19167656913",
  "subscription_tier": "premium"
}
```

**Fields:**
- `username`: Username
- `persona`: Active AI persona (hal-9000, jarvis, glados, etc.)
- `voice_enabled`: Whether voice features are enabled
- `wake_word`: Wake word for voice activation
- `email`: User's email address
- `phone`: User's phone number (optional)
- `subscription_tier`: Subscription level (free, premium, enterprise)

**Integration Status:** ⚠️ Currently returns default config, database integration pending

---

### Update User Config

**PUT** `/api/users/:username/config`

Update configuration for a specific user.

**Path Parameters:**
- `username`: Username (e.g., "chadananda")

**Request Body:**
```json
{
  "persona": "jarvis",
  "voice_enabled": true,
  "wake_word": "hey jarvis"
}
```

**Response:**
```json
{
  "username": "chadananda",
  "persona": "jarvis",
  "voice_enabled": true,
  "wake_word": "hey jarvis",
  "email": "chad@example.com",
  "phone": "+19167656913",
  "subscription_tier": "premium"
}
```

**Fields (all optional):**
- `persona`: New AI persona
- `voice_enabled`: Enable/disable voice features
- `wake_word`: New wake word for voice activation

**Integration Status:** ✅ Saves to local config file, database sync pending

---

## Error Responses

All endpoints return errors in the following format:

```json
{
  "error": "Error message describing what went wrong"
}
```

**HTTP Status Codes:**
- `200 OK`: Request successful
- `400 Bad Request`: Invalid request format
- `401 Unauthorized`: Authentication failed
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Usage Examples

### Node.js / JavaScript

```javascript
// Send SMS
const response = await fetch('http://127.0.0.1:9997/api/sms/send', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    to: '+19167656913',
    message: 'Task completed!',
    user: 'chadananda'
  })
});
const data = await response.json();
console.log('SMS sent:', data.message_sid);
```

### cURL

```bash
# Check status
curl http://127.0.0.1:9997/api/status

# Send email
curl -X POST http://127.0.0.1:9997/api/email/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "chad@example.com",
    "subject": "Test Email",
    "body": "This is a test email from the API",
    "user": "chadananda"
  }'

# Execute task
curl -X POST http://127.0.0.1:9997/api/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task": "run linter on src/ directory",
    "user": "chadananda",
    "priority": "normal",
    "channel": "email"
  }'
```

---

## Testing

Use the provided test script to verify all endpoints:

```bash
# Start the API server in one terminal
cargo run --bin xswarm -- api-server

# Run tests in another terminal
node scripts/test-api.js
```

The test script will verify:
- ✅ Health check endpoint
- ✅ Status endpoint
- ✅ SMS sending
- ✅ Email sending
- ✅ Task execution
- ✅ Get user config
- ✅ Update user config

---

## Integration Roadmap

### Phase 1: Basic API ✅
- [x] HTTP server with axum
- [x] Core endpoints (status, health)
- [x] SMS/Email stub endpoints
- [x] Task execution with AI
- [x] User config endpoints

### Phase 2: Service Integration 🚧
- [ ] Twilio SMS integration
- [ ] SendGrid email integration
- [ ] Database integration for user configs
- [ ] Authentication middleware
- [ ] Rate limiting

### Phase 3: Advanced Features 📋
- [ ] WebSocket support for real-time updates
- [ ] Task queue management
- [ ] Task status tracking
- [ ] Webhook callbacks for task completion
- [ ] Metrics and monitoring

---

## Architecture Notes

**Current Architecture:**
```
Node.js Server (Cloudflare Workers)
    ↓ (webhooks from Twilio/SendGrid)
    ↓
    ↓ HTTP POST to Rust client
    ↓
Rust Client (HTTP API Server)
    ↓ (processes with AI)
    ↓
    ↓ (executes tasks via supervisor)
    ↓
Rust Client Response
```

**Future Architecture with WebSockets:**
```
Node.js Server ←→ WebSocket ←→ Rust Client
    ↓                             ↓
Webhooks                    Real-time execution
    ↓                             ↓
HTTP API                    Task updates via WS
```

---

## File Locations

- **API Implementation:** `packages/core/src/api.rs`
- **Main Entry Point:** `packages/core/src/main.rs`
- **Dependencies:** `packages/core/Cargo.toml`
- **Test Script:** `scripts/test-api.js`
- **Documentation:** `planning/HTTP_API.md`

---

## Development

### Adding New Endpoints

1. Add request/response types in `api.rs`:
   ```rust
   #[derive(Debug, Deserialize)]
   pub struct MyRequest {
       pub field: String,
   }

   #[derive(Debug, Serialize)]
   pub struct MyResponse {
       pub success: bool,
       pub data: String,
   }
   ```

2. Implement handler function:
   ```rust
   async fn my_handler(
       State(state): State<ApiState>,
       Json(payload): Json<MyRequest>,
   ) -> Result<Json<MyResponse>, ApiError> {
       // Implementation
       Ok(Json(MyResponse {
           success: true,
           data: "result".to_string(),
       }))
   }
   ```

3. Add route to router in `create_router()`:
   ```rust
   .route("/api/my-endpoint", post(my_handler))
   ```

4. Update tests in `scripts/test-api.js`
5. Update this documentation

---

## Support

For issues or questions:
- Check logs: The API server logs all requests
- Verify server is running: `curl http://127.0.0.1:9997/health`
- Run test suite: `node scripts/test-api.js`
- Review Rust logs for detailed error messages
