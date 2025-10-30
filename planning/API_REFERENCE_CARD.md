# HTTP API Quick Reference Card

## Start Server

```bash
cargo run --bin xswarm -- api-server
```

Default: `http://127.0.0.1:9997`

---

## Endpoints

### Health
```bash
GET /health
→ "OK"
```

### Status
```bash
GET /api/status
→ { status, voice_bridge, supervisor, tasks, uptime }
```

### Send SMS
```bash
POST /api/sms/send
{ to, message, user }
→ { success, message, message_sid }
```

### Send Email
```bash
POST /api/email/send
{ to, subject, body, user }
→ { success, message, message_id }
```

### Execute Task
```bash
POST /api/tasks/execute
{ task, user, priority?, channel? }
→ { success, message, task_id }
```

### Get User Config
```bash
GET /api/users/:username/config
→ { username, persona, voice_enabled, wake_word, email, phone, subscription_tier }
```

### Update User Config
```bash
PUT /api/users/:username/config
{ persona?, voice_enabled?, wake_word? }
→ { username, persona, ... }
```

---

## Quick Test

```bash
# Terminal 1
cargo run --bin xswarm -- api-server

# Terminal 2
node scripts/test-api.js
```

---

## cURL Examples

```bash
# Health
curl http://127.0.0.1:9997/health

# Status
curl http://127.0.0.1:9997/api/status

# SMS
curl -X POST http://127.0.0.1:9997/api/sms/send \
  -H "Content-Type: application/json" \
  -d '{"to":"+19167656913","message":"Hi!","user":"chad"}'

# Email
curl -X POST http://127.0.0.1:9997/api/email/send \
  -H "Content-Type: application/json" \
  -d '{"to":"chad@example.com","subject":"Test","body":"Hello","user":"chad"}'

# Task
curl -X POST http://127.0.0.1:9997/api/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{"task":"run tests","user":"chad","priority":"high"}'

# Get Config
curl http://127.0.0.1:9997/api/users/chad/config

# Update Config
curl -X PUT http://127.0.0.1:9997/api/users/chad/config \
  -H "Content-Type: application/json" \
  -d '{"persona":"jarvis","wake_word":"hey jarvis"}'
```

---

## Node.js Example

```javascript
// Send SMS
const response = await fetch('http://127.0.0.1:9997/api/sms/send', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    to: '+19167656913',
    message: 'Task completed!',
    user: 'chad'
  })
});
const data = await response.json();
console.log(data);
```

---

## Files

- **Implementation:** `packages/core/src/api.rs`
- **Main:** `packages/core/src/main.rs`
- **Tests:** `scripts/test-api.js`
- **Full Docs:** `planning/HTTP_API.md`
- **Quick Start:** `planning/API_QUICKSTART.md`

---

## Priority Levels

- `high` - Urgent, immediate execution
- `normal` - Standard (default)
- `low` - Background, deferred

## Notification Channels

- `email` - Email notification (default)
- `sms` - SMS notification
- `voice` - Voice call notification

---

## Common Issues

**Server won't start:**
```bash
# Check port
lsof -i :9997

# Use different port
cargo run --bin xswarm -- api-server --port 8080
```

**Tests failing:**
```bash
# Make sure server is running
curl http://127.0.0.1:9997/health
```

**Connection refused:**
- Server running?
- Correct host/port?
- Firewall blocking?

---

## Status Codes

- `200` - OK
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Server Error

---

## Next Steps

1. Start server
2. Run tests
3. Read full docs
4. Integrate with your app

**Full Documentation:** See `planning/HTTP_API.md`
