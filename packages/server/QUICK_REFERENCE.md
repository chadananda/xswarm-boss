# Boss AI Unified API - Quick Reference

## Endpoints

### `/api/message` - CLI/API Messages
```bash
POST /api/message
Content-Type: application/json

{
  "from": "user@example.com",
  "content": "message text",
  "channel": "cli"  # optional
}
```

### `/sms/inbound` - SMS Messages
Twilio webhook (form data)

### `/email/inbound` - Email Messages
SendGrid webhook (form data)

## Response Formats

### Success (CLI)
```json
{
  "success": true,
  "message": "response text",
  "metadata": { "user": "Name" },
  "timestamp": "2025-10-29T16:30:00.000Z"
}
```

### Error (CLI)
```json
{
  "success": false,
  "message": "error description",
  "metadata": { "reason": "unauthorized" },
  "timestamp": "2025-10-29T16:30:00.000Z"
}
```

### SMS Response
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>response text</Message>
</Response>
```

## Quick Examples

### cURL
```bash
# Send message
curl -X POST http://localhost:8787/api/message \
  -H "Content-Type: application/json" \
  -d '{"from":"user@example.com","content":"help"}'

# Schedule meeting
curl -X POST http://localhost:8787/api/message \
  -H "Content-Type: application/json" \
  -d '{"from":"user@example.com","content":"schedule meeting tomorrow at 2pm"}'
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8787/api/message', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    from: 'user@example.com',
    content: 'What is my schedule today?'
  })
});
const data = await response.json();
console.log(data.message);
```

### CLI Client
```bash
node examples/cli-client.js "What's my schedule today?"
```

## Common Commands

- `help` - Get help
- `status` - Get current status
- `schedule [task] [when]` - Schedule appointment
- `remind me to [task] [when]` - Set reminder
- `what's on my schedule [when]?` - View calendar

## Testing

```bash
# Unit tests
node src/test-unified-api.js

# Integration tests
node test-integration.js

# Run CLI client
node examples/cli-client.js --help
```

## Files

- **Core:** `src/lib/unified-message.js`
- **Routes:** `src/index.js`
- **Tests:** `test-integration.js`, `src/test-unified-api.js`
- **Examples:** `examples/cli-client.js`
- **Docs:** `UNIFIED_API_ARCHITECTURE.md`

## Status Codes

- `200` - Success
- `400` - Bad request
- `403` - Unauthorized
- `404` - Not found
- `500` - Server error

## Environment Variables

```bash
# For CLI client
export BOSS_API_URL="http://localhost:8787/api/message"
export BOSS_USER_EMAIL="your-email@example.com"
```

## Development

```bash
# Start dev server
cd packages/server
wrangler dev

# In another terminal, test
node examples/cli-client.js "test message"
```

## Architecture

```
Request → Normalize → Authorize → Process → Format → Response
   ↓          ↓           ↓          ↓         ↓         ↓
  CLI       Unified    Validate   AI/DB   Channel    JSON/
  SMS       Format      User     Router   Specific   TwiML/
  Email                                              Email
```

## Key Functions

- `normalizeCLIMessage()` - Parse CLI request
- `normalizeSMSMessage()` - Parse SMS webhook
- `normalizeEmailMessage()` - Parse email webhook
- `processUnifiedMessage()` - Core processing
- `formatCLIResponse()` - Format JSON response
- `formatSMSResponse()` - Format TwiML response
- `findUserByIdentifier()` - Resolve user
- `validateMessageAuthorization()` - Check auth

## Adding New Channel

1. Create normalization function
2. Create response formatter
3. Create handler function
4. Add route in index.js

See `UNIFIED_API_ARCHITECTURE.md` for details.
