# Email Management System

Comprehensive Gmail integration with OAuth2, AI summarization, and natural language queries for xSwarm.

## Features

### 1. Gmail OAuth Integration
- **Incremental Authorization**: Request only necessary permissions based on user tier
- **Tier-based Permissions**:
  - **Free Tier**: Read-only access to emails
  - **Personal Tier+**: Read, compose, and send emails
- **Secure Token Management**: Automatic token refresh with database storage
- **Privacy-First**: Users control their data with easy disconnect option

### 2. AI-Powered Email Summarization
- **Intelligent Summaries**: 2-3 sentence summaries using OpenAI GPT-3.5
- **Action Item Extraction**: Automatically identifies tasks and requests
- **Importance Scoring**: 0-1 score based on keywords, sender, and content
- **Sentiment Analysis**: Positive, negative, or neutral tone detection
- **Reading Time Estimation**: Calculate time to read email

### 3. Natural Language Queries
- **Voice-Friendly**: Process queries like "show me unread emails from today"
- **Smart Parsing**: Extracts sender, timeframe, keywords, and filters
- **Query Types**:
  - From specific sender
  - Unread emails
  - Important/starred emails
  - With attachments
  - By date range
  - General keyword search

### 4. Email Briefings
- **Daily Digest**: Top unread and important emails
- **Action Items Summary**: Extracted tasks from top emails
- **Statistics**: Unread count, important count, needs response
- **Timeframe Options**: 24h, 48h, 7d, 30d

## Architecture

### Database Schema

```sql
-- OAuth tokens and settings
email_integrations
  - user_id, provider, email_address
  - access_token, refresh_token, token_expires_at
  - permissions (JSON), sync_enabled

-- Cached email messages
email_cache
  - provider_message_id, thread_id
  - subject, sender, recipients
  - body_text, body_html, body_preview
  - labels, is_read, is_important
  - importance_score

-- AI-generated summaries
email_summaries
  - email_id, summary
  - importance_score, action_items
  - key_points, sentiment, reading_time

-- Query analytics
email_query_history
  - query, query_type, result_count
```

### Module Structure

```
lib/email/
├── gmail-client.js       # Gmail API integration (fetch-based)
├── summarization.js      # AI email summarization
├── queries.js            # Natural language query processing
└── email-system.js       # Unified interface
```

## API Endpoints

### Authentication

**Start Gmail OAuth**
```bash
POST /api/email/auth/gmail
Authorization: Bearer <jwt_token>

Response:
{
  "authUrl": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "permissions": ["readonly"],
  "tier": "free"
}
```

**OAuth Callback**
```bash
GET /api/email/auth/callback?code=...&state=...

Response:
{
  "success": true,
  "message": "Gmail connected successfully",
  "email": "user@gmail.com",
  "permissions": ["readonly"]
}
```

**Check Integration Status**
```bash
GET /api/email/status
Authorization: Bearer <jwt_token>

Response:
{
  "connected": true,
  "email": "user@gmail.com",
  "permissions": ["readonly", "compose", "send"],
  "lastSync": "2025-10-30T12:00:00Z",
  "syncEnabled": true
}
```

**Disconnect Gmail**
```bash
DELETE /api/email/disconnect
Authorization: Bearer <jwt_token>

Response:
{
  "success": true,
  "message": "Gmail disconnected successfully"
}
```

### Email Operations

**Natural Language Query**
```bash
POST /api/email/query
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "query": "show me unread emails from john@example.com this week"
}

Response:
{
  "type": "email_results",
  "message": "I found 5 emails from john@example.com",
  "count": 5,
  "emails": [
    {
      "id": "msg_123",
      "subject": "Project Update",
      "from": "john@example.com",
      "date": "2025-10-29T14:30:00Z",
      "snippet": "Here's the latest on the project...",
      "isRead": false,
      "isImportant": true
    }
  ],
  "summary": {
    "totalEmails": 5,
    "unreadCount": 3,
    "importantCount": 2,
    "withAttachments": 1
  }
}
```

**Get Email Briefing**
```bash
GET /api/email/briefing?timeframe=24h
Authorization: Bearer <jwt_token>

Response:
{
  "timeframe": "24h",
  "stats": {
    "totalUnread": 12,
    "totalImportant": 5,
    "needsResponse": 3
  },
  "topEmails": [
    {
      "id": "msg_123",
      "subject": "Urgent: Review Required",
      "from": "boss@company.com",
      "summary": {
        "summary": "Review of Q4 report needed by EOD. Focus on revenue projections.",
        "importance": 0.9,
        "actionItems": ["Review Q4 report", "Check revenue projections"],
        "sentiment": "neutral",
        "readingTime": 3
      }
    }
  ],
  "actionItems": [
    {
      "email": {
        "subject": "Urgent: Review Required",
        "from": "boss@company.com"
      },
      "action": "Review Q4 report"
    }
  ]
}
```

**Summarize Email**
```bash
POST /api/email/summarize/:emailId
Authorization: Bearer <jwt_token>

Response:
{
  "email": {
    "id": "msg_123",
    "subject": "Project Proposal",
    "from": "client@company.com",
    "date": "2025-10-29T14:30:00Z"
  },
  "summary": "Client proposes new features for Q1. Budget estimate $50k.",
  "importance": 0.8,
  "actionItems": [
    "Review proposal details",
    "Prepare budget analysis",
    "Schedule follow-up call"
  ],
  "keyPoints": [
    "New features requested for Q1 2026",
    "Estimated budget is $50,000",
    "Deadline for response is next Friday"
  ],
  "sentiment": "positive",
  "readingTime": 5
}
```

**Compose Email** (Personal Tier+)
```bash
POST /api/email/compose
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "to": "client@example.com",
  "subject": "Re: Project Proposal",
  "body": "Thank you for your proposal. I've reviewed the details...",
  "cc": "team@company.com",
  "isHtml": false
}

Response:
{
  "success": true,
  "messageId": "msg_456",
  "threadId": "thread_789"
}
```

## Setup Instructions

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Gmail API:
   - Go to APIs & Services → Library
   - Search for "Gmail API"
   - Click Enable

4. Create OAuth credentials:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: Web application
   - Name: "xSwarm Email Integration"
   - Authorized redirect URIs:
     - Development: `http://localhost:8787/api/email/auth/callback`
     - Production: `https://your-domain.com/api/email/auth/callback`

5. Copy Client ID and Client Secret to `.env`:
```bash
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_client_secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/email/auth/callback
```

### 2. Run Database Migration

```bash
cd packages/server
turso db shell xswarm-users < migrations/email-integration.sql
```

### 3. Deploy to Cloudflare Workers

```bash
# Set secrets
wrangler secret put GOOGLE_CLIENT_ID
wrangler secret put GOOGLE_CLIENT_SECRET
wrangler secret put GOOGLE_REDIRECT_URI

# Deploy
pnpm deploy
```

## Usage Examples

### Voice Command Flow

1. User: "Check my emails"
2. System connects to Gmail via stored OAuth tokens
3. Retrieves recent unread emails
4. AI summarizes top emails
5. Voice response: "You have 5 unread emails. The most important is from your boss about the Q4 review..."

### Email Query Flow

1. User: "Show me emails from Sarah about the project"
2. Query parser extracts:
   - Sender: "Sarah"
   - Keywords: "project"
3. Builds Gmail query: `from:sarah project`
4. Returns formatted results with summaries

### Daily Briefing Flow

1. Scheduled task triggers briefing generation
2. Fetches unread emails from last 24h
3. AI summarizes top 10 most important
4. Extracts action items
5. Sends briefing via SMS/email/voice

## Tier-Based Features

### Free Tier
- ✅ Gmail OAuth (read-only)
- ✅ Email queries
- ✅ AI summaries
- ✅ Daily briefings
- ❌ Email composition

### Personal Tier ($29/mo)
- ✅ All Free features
- ✅ Email composition and sending
- ✅ Draft creation
- ✅ Email templates

### Professional Tier ($99/mo)
- ✅ All Personal features
- ✅ Advanced AI models
- ✅ Team email delegation
- ✅ Email analytics

## Security & Privacy

- **Secure Storage**: OAuth tokens encrypted in database
- **Automatic Refresh**: Tokens refreshed before expiration
- **User Control**: Easy disconnect with full data deletion
- **Minimal Permissions**: Request only necessary scopes
- **GDPR Compliant**: Full data deletion on disconnect
- **No Email Storage**: Only metadata cached, full bodies on-demand

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Gmail not connected. Please connect your Gmail account.",
  "action": "connect_gmail"
}
```

Common errors:
- `not_connected`: User needs to connect Gmail
- `permission_denied`: Missing required OAuth scope
- `token_expired`: Need to reconnect account
- `feature_locked`: Tier upgrade required

## Performance Optimization

- **Message Caching**: Store metadata in database for fast queries
- **Batch Requests**: Fetch multiple emails in parallel
- **Lazy Loading**: Full email bodies loaded on-demand
- **Token Reuse**: Single access token across requests
- **Smart Sync**: Incremental updates, not full refresh

## Future Enhancements

- [ ] Email templates for common responses
- [ ] Smart reply suggestions
- [ ] Email scheduling
- [ ] Follow-up reminders
- [ ] Contact management integration
- [ ] Email thread analysis
- [ ] Spam detection and filtering
- [ ] Email categorization (personal, work, promotions)
- [ ] Multi-provider support (Outlook, iCloud)
- [ ] Advanced search with filters
