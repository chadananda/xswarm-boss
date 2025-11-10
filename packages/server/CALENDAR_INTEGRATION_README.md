# Calendar Integration System

Comprehensive calendar integration with Google Calendar OAuth, iCal support, natural language queries, and daily briefings with tier-based access control.

## Features

### Multi-Provider Support
- **Google Calendar**: OAuth2 with read/write access (Personal+ tiers)
- **iCal Subscriptions**: Read-only support for any iCal/ICS URL
- **Event Caching**: Local copy for fast queries and offline access
- **Auto-sync**: Configurable sync intervals with error handling

### Natural Language Queries
Process voice-friendly calendar queries using chrono-node:
- "What's on my calendar today?"
- "Am I free tomorrow at 2pm?"
- "When is my next meeting?"
- "Find me time for a 30-minute meeting"
- "Do I have any conflicts this week?"

### Daily Briefings
Intelligent briefings with:
- Total event count and meeting time
- Conflict detection
- Free time analysis
- Important event highlighting
- Preparation requirements

### Tier-Based Access
- **Free**: Read-only calendar integration
- **Personal+**: Full read/write access, event creation
- **Professional+**: Advanced features, team calendar sharing
- **Enterprise**: Custom integrations, API access

## Architecture

```
packages/server/src/lib/calendar/
├── mod.js          # Main calendar coordinator
├── google.js       # Google Calendar OAuth integration
├── ical.js         # iCal subscription support
├── queries.js      # Natural language query processing
└── briefings.js    # Daily briefing generation
```

## Database Schema

### Tables
- `calendar_integrations` - Provider connections (OAuth tokens, etc.)
- `calendar_events` - Cached events from all providers
- `ical_subscriptions` - iCal subscription URLs
- `calendar_queries` - Query history for ML improvements
- `calendar_briefings` - Cached daily briefings

### Views
- `calendar_today` - Today's events
- `calendar_upcoming` - Next 7 days
- `calendar_active_integrations` - Active connections

## API Endpoints

### OAuth Flow

**Start Google Calendar Authorization**
```http
POST /api/calendar/auth/google
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "scopes": "readwrite"  // or "readonly"
}

Response:
{
  "authUrl": "https://accounts.google.com/..."
}
```

**Handle OAuth Callback**
```http
GET /api/calendar/auth/callback?code=xxx&state=userId

Response:
{
  "success": true,
  "message": "Google Calendar connected successfully"
}
```

### Natural Language Queries

```http
POST /api/calendar/query
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "query": "What's on my calendar today?",
  "options": {}
}

Response:
{
  "type": "event_list",
  "message": "You have 3 events today",
  "events": [...],
  "summary": "Starting with Morning standup at 9:00 AM"
}
```

### Daily Briefing

```http
GET /api/calendar/briefing?date=2024-01-01
Authorization: Bearer <JWT>

Response:
{
  "type": "daily_briefing",
  "message": "You have 5 events today totaling 4h 30m of meetings...",
  "summary": "Moderately busy",
  "totalEvents": 5,
  "totalMeetingMinutes": 270,
  "conflicts": [],
  "freeTime": [60, 120, 45],
  "importantEvents": [...],
  "events": [...]
}
```

### Create Event (Personal+ tier)

```http
POST /api/calendar/events
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "title": "Team Meeting",
  "description": "Weekly sync",
  "startTime": "2024-01-15T14:00:00Z",
  "endTime": "2024-01-15T15:00:00Z",
  "attendees": ["team@example.com"],
  "location": "Conference Room A"
}

Response:
{
  "id": "event-123",
  "title": "Team Meeting",
  "startTime": "2024-01-15T14:00:00Z",
  "htmlLink": "https://calendar.google.com/...",
  "meetLink": "https://meet.google.com/..."
}
```

### iCal Subscription

```http
POST /api/calendar/ical
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "name": "Company Holidays",
  "url": "https://calendar.example.com/holidays.ics"
}

Response:
{
  "success": true,
  "subscriptionId": 42,
  "message": "iCal subscription added successfully"
}
```

### Sync Calendars

```http
POST /api/calendar/sync
Authorization: Bearer <JWT>

Response:
{
  "success": true,
  "synced": [
    { "provider": "google", "eventsCount": 127 },
    { "provider": "ical", "eventsCount": 23 }
  ],
  "errors": []
}
```

### Get Integrations

```http
GET /api/calendar/integrations
Authorization: Bearer <JWT>

Response:
{
  "integrations": [
    {
      "id": 1,
      "provider": "google",
      "syncEnabled": true,
      "lastSync": "2024-01-15T10:30:00Z",
      "syncError": null
    }
  ]
}
```

### Disconnect Provider

```http
DELETE /api/calendar/providers/google
Authorization: Bearer <JWT>

Response:
{
  "success": true,
  "message": "google calendar disconnected"
}
```

## Usage Examples

### JavaScript/Node.js

```javascript
import { CalendarSystem } from './lib/calendar/mod.js';

const calendar = new CalendarSystem(env);

// Connect Google Calendar
const authUrl = await calendar.google.getAuthUrl(userId, 'readwrite');
// User visits authUrl and authorizes
await calendar.google.handleCallback(code, userId);

// Natural language query
const result = await calendar.queryCalendar(
  userId,
  "What's on my calendar today?"
);
console.log(result.message);
// "You have 3 events today. Starting with Morning standup at 9:00 AM"

// Generate daily briefing
const briefing = await calendar.getDailyBriefing(userId);
console.log(briefing.message);
// "You have 5 events today totaling 4h 30m of meetings..."

// Create event (Personal+ tier)
const event = await calendar.createEvent(userId, {
  title: 'Team Meeting',
  startTime: '2024-01-15T14:00:00Z',
  endTime: '2024-01-15T15:00:00Z',
});

// Add iCal subscription
await calendar.ical.addSubscription(
  userId,
  'Company Holidays',
  'https://calendar.example.com/holidays.ics'
);
```

### Voice Integration

```javascript
async function handleCalendarQuery(userId, query) {
  const calendar = new CalendarSystem(env);

  try {
    const result = await calendar.queryCalendar(userId, query);

    // Return voice-friendly response
    return result.message;
  } catch (error) {
    return "I'm having trouble accessing your calendar right now.";
  }
}

// Usage with voice system
const response = await handleCalendarQuery(
  userId,
  "What's my next meeting?"
);
// Response: "Your next event is Client presentation in 2 hours"
```

## Setup

### 1. Install Dependencies

```bash
cd packages/server
npm install googleapis google-auth-library chrono-node node-ical
```

### 2. Configure Google OAuth

Create a Google Cloud project and enable the Calendar API:

1. Go to https://console.cloud.google.com/
2. Create new project or select existing
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `https://your-domain.com/api/calendar/auth/callback`

Add to `.env`:
```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/calendar/auth/callback
```

### 3. Run Database Migration

```bash
node scripts/migrate-calendar.js
```

### 4. Test Integration

```bash
cd packages/server
node test-calendar-integration.js
```

## Environment Variables

```env
# Required
TURSO_DATABASE_URL=libsql://your-database.turso.io
TURSO_AUTH_TOKEN=your-auth-token

# Google Calendar (optional, for OAuth)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/api/calendar/auth/callback
```

## Natural Language Query Types

The system automatically detects query intent:

### List Events
- "What's on my calendar today?"
- "Show me tomorrow's schedule"
- "What do I have this week?"

### Check Availability
- "Am I free at 2pm?"
- "Do I have time tomorrow afternoon?"
- "Is 3pm open?"

### Find Conflicts
- "Do I have any scheduling conflicts?"
- "Are any meetings overlapping?"
- "Show me double-booked times"

### Next Event
- "What's my next meeting?"
- "When is my next appointment?"
- "What's coming up?"

### Find Meeting Time
- "Find me time for a 30-minute meeting"
- "When can I schedule a 1-hour call?"
- "Find an open slot tomorrow"

## Tier-Based Feature Gating

```javascript
import { hasFeature } from './lib/features.js';

// Check if user can write to calendar
if (!hasFeature(tier, 'calendar_write_access')) {
  return {
    error: 'Calendar write access requires Personal tier or higher',
    upgrade_cta: {
      tier: 'personal',
      feature: 'calendar_write_access',
      benefit: 'Create and edit calendar events'
    }
  };
}
```

## Security

- OAuth tokens stored encrypted in database
- Automatic token refresh with retry logic
- Rate limiting on API endpoints
- User-scoped data access (users can only see their own events)
- HTTPS required for all OAuth redirects

## Performance

- Event caching reduces API calls
- Configurable sync intervals (default: 24 hours for iCal)
- Indexed database queries for fast lookups
- Lazy loading of event details

## Error Handling

- Automatic token refresh on 401 errors
- Graceful degradation when providers unavailable
- User-friendly error messages
- Sync error tracking in database

## Testing

Run the test suite:

```bash
cd packages/server
node test-calendar-integration.js
```

Tests cover:
- Database schema creation
- Event insertion and retrieval
- Natural language query parsing
- Daily briefing generation
- Time context parsing
- Conflict detection
- Free time analysis

## Future Enhancements

- [ ] Microsoft Outlook integration
- [ ] Apple Calendar integration
- [ ] CalDAV protocol support
- [ ] Team calendar sharing
- [ ] Meeting scheduling AI
- [ ] Travel time calculation
- [ ] Smart notifications
- [ ] Calendar analytics
- [ ] Recurring event expansion
- [ ] Timezone intelligence

## Troubleshooting

### "Google Calendar not connected"
Run OAuth flow to connect Google Calendar:
```javascript
const authUrl = await calendar.google.getAuthUrl(userId, 'readwrite');
// User visits authUrl
```

### "Token expired"
System automatically refreshes tokens. If refresh fails, reconnect:
```javascript
await calendar.disconnectProvider(userId, 'google');
// Then reconnect with OAuth flow
```

### "iCal feed not syncing"
Check subscription errors:
```javascript
const subs = await calendar.ical.getSubscriptions(userId);
console.log(subs[0].syncError);
```

## Support

For issues or questions:
- Create issue on GitHub
- Check troubleshooting guide
- Review API documentation
- Contact support@xswarm.dev
