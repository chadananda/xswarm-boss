# Unified API Architecture for Boss AI

## Overview

The unified API layer provides a consistent interface for handling messages across all communication channels in Boss AI. This architecture eliminates code duplication, ensures consistent behavior, and makes it easy to add new channels.

## Architecture Principles

### 1. **Message Normalization**
All incoming messages, regardless of channel, are converted to a unified format:

```javascript
{
  channel: 'cli' | 'sms' | 'email' | 'voice',
  from: string,           // phone, email, or identifier
  to: string,             // recipient (optional for CLI)
  content: string,        // message content
  metadata: object,       // channel-specific data
  timestamp: string       // ISO timestamp
}
```

### 2. **Channel-Agnostic Processing**
Once normalized, all messages flow through the same processing logic:
- Authorization validation
- User resolution
- AI routing (Supervisor or Claude)
- Response generation

### 3. **Response Formatting**
Responses are formatted appropriately for each channel:
- **CLI/API**: JSON response
- **SMS**: TwiML XML
- **Email**: SendGrid API call
- **Voice**: TwiML or audio response

## File Structure

```
packages/server/src/
├── index.js                     # Main router (integrates unified API)
├── lib/
│   └── unified-message.js       # Unified message layer
├── routes/
│   ├── sms.js                   # Legacy SMS handler (for /sms/:userId)
│   ├── email.js                 # Legacy email handler (for outbound)
│   └── ...
└── test-unified-api.js          # Comprehensive test suite
```

## API Endpoints

### 1. `/api/message` - Unified CLI/API Endpoint

**Purpose**: Handle messages from CLI clients or direct API calls

**Request Format**:
```bash
POST /api/message
Content-Type: application/json

{
  "from": "user@example.com",
  "content": "What's my schedule today?",
  "channel": "cli"  # optional, defaults to 'cli'
}
```

**Response Format**:
```json
{
  "success": true,
  "message": "Here's your schedule for today...",
  "metadata": {
    "user": "Chad Jones",
    "processedAt": "2025-10-29T16:28:41.231Z"
  },
  "timestamp": "2025-10-29T16:28:41.231Z"
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid request
- `403`: Unauthorized
- `500`: Server error

### 2. `/sms/inbound` - SMS Webhook (Twilio)

**Purpose**: Handle incoming SMS messages from Twilio

**Request Format**: Twilio sends form-encoded data
```
From: +15551234567
To: +15559876543
Body: What's my schedule today?
MessageSid: SM123456
```

**Response Format**: TwiML XML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>Here's your schedule for today...</Message>
</Response>
```

**Status Codes**:
- `200`: Success
- `403`: Unauthorized sender

### 3. `/email/inbound` - Email Webhook (SendGrid)

**Purpose**: Handle incoming emails from SendGrid Parse API

**Request Format**: SendGrid sends form-encoded data
```
from: Chad Ananda <chad@example.com>
to: Boss <boss@example.com>
subject: Schedule request
text: What's my schedule today?
```

**Response Format**:
- Returns `200 OK` immediately
- Sends reply email via SendGrid API asynchronously

**Status Codes**:
- `200`: Email received and processed
- `400`: Invalid email format

## Implementation Details

### Message Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     INCOMING MESSAGE                        │
│        (CLI, SMS, Email, Voice)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              NORMALIZATION LAYER                            │
│  • normalizeCLIMessage()                                    │
│  • normalizeSMSMessage()                                    │
│  • normalizeEmailMessage()                                  │
│  • normalizeVoiceMessage()                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED MESSAGE FORMAT                         │
│  { channel, from, to, content, metadata, timestamp }        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              AUTHORIZATION & USER RESOLUTION                │
│  • findUserByIdentifier()                                   │
│  • validateMessageAuthorization()                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              PROCESSING LAYER                               │
│  • Try Supervisor WebSocket                                 │
│  • Fall back to local processing                            │
│  • Route to Claude AI                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED RESPONSE                               │
│  { success, message, metadata, channel }                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              RESPONSE FORMATTING                            │
│  • formatCLIResponse() → JSON                               │
│  • formatSMSResponse() → TwiML                              │
│  • formatEmailResponse() → SendGrid API call                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     RESPONSE SENT                           │
└─────────────────────────────────────────────────────────────┘
```

### Key Functions

#### Normalization Functions

```javascript
// CLI/API messages
normalizeCLIMessage(body, metadata = {})

// SMS messages (Twilio webhook)
normalizeSMSMessage(formData, metadata = {})

// Email messages (SendGrid webhook)
normalizeEmailMessage(formData, metadata = {})

// Voice messages (future)
normalizeVoiceMessage(callData, metadata = {})
```

#### User Management

```javascript
// Find user by any identifier
findUserByIdentifier(identifier)  // phone, email, or username

// Validate authorization
validateMessageAuthorization(unifiedMessage)
```

#### Core Processing

```javascript
// Process unified message (channel-agnostic)
processUnifiedMessage(message, env)
```

#### Response Formatting

```javascript
// Format for CLI/API (JSON)
formatCLIResponse(unifiedResponse)

// Format for SMS (TwiML)
formatSMSResponse(unifiedResponse)

// Format for Email (SendGrid + 200 OK)
formatEmailResponse(unifiedResponse, originalMessage, env)
```

#### High-Level Handlers

```javascript
// Simplified handlers for route integration
handleCLIMessage(body, env)
handleSMSMessage(formData, env)
handleEmailMessage(formData, env)
```

## Adding New Channels

To add a new channel (e.g., Discord, Slack):

### 1. Create Normalization Function

```javascript
export function normalizeDiscordMessage(discordData, metadata = {}) {
  return {
    channel: 'discord',
    from: discordData.author.id,
    to: discordData.channel.id,
    content: discordData.content,
    metadata: {
      ...metadata,
      serverId: discordData.guild?.id,
      messageId: discordData.id,
    },
    timestamp: new Date(discordData.timestamp).toISOString(),
  };
}
```

### 2. Create Response Formatter

```javascript
export function formatDiscordResponse(unifiedResponse) {
  return {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    body: {
      content: unifiedResponse.message,
      // Discord-specific formatting
    },
  };
}
```

### 3. Create High-Level Handler

```javascript
export async function handleDiscordMessage(discordData, env) {
  const unifiedMessage = normalizeDiscordMessage(discordData);
  const unifiedResponse = await processUnifiedMessage(unifiedMessage, env);
  const formattedResponse = formatDiscordResponse(unifiedResponse);

  return new Response(
    JSON.stringify(formattedResponse.body),
    { status: formattedResponse.status, headers: formattedResponse.headers }
  );
}
```

### 4. Add Route in index.js

```javascript
if (path === '/discord/webhook' && request.method === 'POST') {
  const body = await request.json();
  return await handleDiscordMessage(body, env);
}
```

## Testing

### Run Tests

```bash
cd packages/server
node src/test-unified-api.js
```

### Test Coverage

The test suite covers:
- ✅ Message normalization (CLI, SMS, Email)
- ✅ User resolution (email, phone, username)
- ✅ Authorization validation
- ✅ Response formatting (JSON, TwiML)
- ✅ Error handling
- ✅ XML escaping for TwiML
- ✅ Full message flow integration

## Security

### Authorization Model

1. **CLI/API**: Any known user (by email/phone/username) is authorized
2. **SMS**: Sender must be known user, recipient must be their boss number
3. **Email**: Sender must be known user, recipient must be their boss email

### Validation Steps

1. Extract sender identifier from message
2. Look up user in config
3. Validate sender-receiver relationship (for SMS/Email)
4. Process only authorized messages
5. Silently reject unauthorized messages (no bounce)

## Error Handling

### Error Response Format

```javascript
{
  success: false,
  message: "Channel-appropriate error message",
  metadata: {
    reason: "unauthorized" | "empty_content" | "processing_error",
    error: "Error details"
  },
  channel: "cli" | "sms" | "email"
}
```

### Channel-Specific Error Messages

- **CLI**: Detailed error with technical info
- **SMS**: Brief error message from Boss
- **Email**: Friendly email response with apology

## Performance Considerations

### Efficiency Features

1. **User lookup caching**: Could be added for high-volume scenarios
2. **Connection pooling**: Supervisor WebSocket reused across requests
3. **Async processing**: Email responses sent asynchronously
4. **Minimal dependencies**: No heavy libraries in normalization layer

### Scalability

- **Stateless design**: Each request is independent
- **Cloudflare Workers**: Edge computing for low latency
- **Supervisor failover**: Falls back to local processing if supervisor unavailable

## Backward Compatibility

### Legacy Endpoints

The following legacy endpoints are maintained for backward compatibility:

- `/sms/:userId` - Legacy SMS webhook (redirects to unified handler)
- `/api/boss/email` - Outbound email sending (unchanged)

### Migration Path

1. **Phase 1**: Add unified API layer (✅ Complete)
2. **Phase 2**: Update integrations to use `/api/message`
3. **Phase 3**: Deprecate legacy endpoints
4. **Phase 4**: Remove legacy code

## Future Enhancements

### Planned Features

1. **Voice integration**: Add voice call transcription support
2. **Discord/Slack**: Add chat platform support
3. **Message queuing**: Add message queue for high-volume scenarios
4. **Rate limiting**: Add per-user rate limits
5. **Analytics**: Track message volume by channel
6. **Webhooks**: Allow third-party webhooks for message events

### Extensibility

The unified API layer is designed to be easily extended:
- Add new channels without touching core logic
- Add new message types without changing normalization
- Add new AI providers without changing routing

## Examples

### Example 1: CLI Message

```bash
curl -X POST https://boss.xswarm.ai/api/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "chad@example.com",
    "content": "What is my schedule today?"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Here's your schedule for today:\n- 9:00 AM: Team standup\n- 2:00 PM: Client meeting",
  "metadata": {
    "user": "Chad Jones",
    "processedAt": "2025-10-29T16:30:00.000Z"
  },
  "timestamp": "2025-10-29T16:30:00.000Z"
}
```

### Example 2: SMS Message

User sends SMS to Boss number:
```
From: +15551234567
To: +15559876543
Body: Schedule meeting tomorrow at 2pm
```

Boss responds via SMS:
```
Scheduled: Meeting on 10/30/2025 at 2:00 PM
```

### Example 3: Email Message

User sends email to boss@example.com:
```
From: chad@example.com
To: boss@example.com
Subject: Project update request
Body: Can you give me an update on the xSwarm project?
```

Boss replies via email:
```
From: boss@example.com
To: chad@example.com
Subject: Re: Project update request
Body: The xSwarm project is progressing well. We've completed...
```

## Monitoring & Logging

### Log Format

All unified API logs follow this format:
```
[Unified] <action> <details>
```

Examples:
```
[Unified] Processing cli message from chad@example.com
[Unified] CLI/API user authorized: Chad Jones
[Unified] Sending to supervisor for Chad Jones
[Unified] Getting Claude response for Chad Jones
```

### Error Logs

```
[Unified] Unknown sender: hacker@example.com
[Unified] Processing error: Error message
[Unified] Supervisor error, falling back: Connection refused
```

## Conclusion

The unified API layer provides a robust, scalable, and maintainable solution for multi-channel communication in Boss AI. By normalizing all messages to a common format, we eliminate code duplication and ensure consistent behavior across all channels.

### Key Benefits

- **Single source of truth**: One place for all message processing logic
- **Easy to extend**: Add new channels without touching core code
- **Consistent behavior**: All channels behave the same way
- **Better testing**: Test once, works everywhere
- **Improved maintainability**: Less code, fewer bugs

### Next Steps

1. Update CLI client to use `/api/message`
2. Add voice transcription support
3. Add Discord/Slack integrations
4. Implement message analytics
5. Add rate limiting and abuse prevention
