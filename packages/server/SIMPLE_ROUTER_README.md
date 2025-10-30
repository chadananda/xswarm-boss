# Boss AI - Simple Message Router

This is the simplified message router implementation based on the `SIMPLE_DESIGN.md` specification.

## Philosophy

**Minimal, testable, easy to understand, easy to extend**

## Files

- `src/simple-index.js` - Main router (~600 lines including comprehensive documentation)
- `migrations/messages.sql` - Messages table schema
- `test-simple-router.js` - Test suite

## What It Does

1. **Receives messages** from any channel (SMS/Email/API)
2. **Routes admin messages** to Claude Code
3. **Handles simple commands** for regular users:
   - Schedule appointments
   - Set reminders
   - View calendar
4. **Responds** back through the same channel

## Core Features

### User Management

- Finds users by phone or email
- Supports admin user from config.toml
- Falls back to database for regular users

### Message Routing

- Admin messages → Claude Code
- Regular users → Command handler
- All messages logged to database

### Commands

1. **Schedule**: `schedule meeting tomorrow at 2pm`
2. **Reminder**: `remind me to call John at 3pm`
3. **Calendar**: `show my calendar today`
4. **Help**: Any unrecognized message shows help

### Natural Language Parsing

- Understands "tomorrow", "today", "next week"
- Parses time formats: "2pm", "14:00", "2:30pm"
- Extracts titles and reminder text automatically

## API Endpoints

### 1. SMS Webhook
```
POST /sms
Content-Type: application/x-www-form-urlencoded

From=+15551234567&Body=schedule meeting tomorrow at 2pm
```

Response: TwiML with message

### 2. Email Webhook
```
POST /email
Content-Type: application/json

{
  "from": "user@example.com",
  "text": "show my calendar today"
}
```

Response: 200 OK (sends email reply via SendGrid)

### 3. API Message
```
POST /api/message
Content-Type: application/json

{
  "from": "+15551234567",
  "content": "remind me to call John",
  "channel": "api"
}
```

Response:
```json
{
  "message": "Reminder set: call John at 12/25/2024 3:00:00 PM"
}
```

## Database Tables Used

### Required Tables

1. **users** - User records (from existing schema)
2. **appointments** - Calendar events (from scheduler.sql)
3. **reminders** - Reminder notifications (from scheduler.sql)
4. **messages** - Conversation logs (from messages.sql)

### Optional: Create Messages Table

Run the migration if it doesn't exist:

```bash
wrangler d1 execute xswarm --file=migrations/messages.sql
```

## Testing

### Run Test Suite

```bash
node test-simple-router.js
```

### Manual Testing

```bash
# Test SMS endpoint
curl -X POST http://localhost:8787/sms \
  -d "From=+15551234567&Body=schedule meeting tomorrow at 2pm"

# Test API endpoint
curl -X POST http://localhost:8787/api/message \
  -H "Content-Type: application/json" \
  -d '{"from":"+15551234567","content":"show my calendar"}'
```

## Deployment

### Option 1: Replace Main Router

To use this as the main router, update `wrangler.toml`:

```toml
main = "src/simple-index.js"
```

### Option 2: Run Alongside Existing Router

Deploy to a different worker:

```bash
wrangler deploy --name boss-ai-simple src/simple-index.js
```

## Environment Variables

Required in `wrangler.toml` or `.env`:

```bash
TURSO_DATABASE_URL=libsql://your-database.turso.io
TURSO_AUTH_TOKEN=your-auth-token
ADMIN_PHONE=+15559876543
ADMIN_EMAIL=admin@xswarm.dev
ADMIN_XSWARM_EMAIL=admin@xswarm.ai
SENDGRID_API_KEY=SG.xxx (optional, for email responses)
```

## Extending the Router

### Add a New Command

Edit `handleCommand()` function:

```javascript
if (text.includes('your-command')) {
  return await handleYourCommand(userId, content, env);
}
```

### Add a New Channel

Edit the main `fetch()` handler:

```javascript
if (path === '/your-channel' && request.method === 'POST') {
  const body = await request.json();
  return await handleYourChannel(body, env);
}
```

### Add New NLP Patterns

Edit parsing functions:

- `parseDateTime()` - Date/time parsing
- `extractTitle()` - Title extraction
- `extractReminderText()` - Reminder text extraction

## Architecture Benefits

1. **Single file** - Easy to understand and debug
2. **Pure functions** - Easy to test
3. **Clear data flow** - Message in → Route → Process → Respond
4. **Minimal dependencies** - Just @libsql/client
5. **Easy to extend** - Add functions, don't change architecture

## Comparison with Complex Router

| Feature | Simple Router | Complex Router |
|---------|--------------|----------------|
| Lines of code | ~600 | ~2000+ |
| Files | 1 | 15+ |
| Core functionality | ✅ | ✅ |
| Easy to understand | ✅ | ❌ |
| Easy to debug | ✅ | ❌ |
| Production ready | ✅ | ✅ |

## Next Steps

1. Test with real SMS/Email endpoints
2. Deploy to Cloudflare Workers
3. Monitor message logs
4. Add more commands as needed

## Philosophy Reminder

> "80% of the functionality with 20% of the complexity"

We start simple and add sophistication only when truly needed. This router handles all core functionality while remaining maintainable and debuggable.
