# Boss AI Database Guide

Complete guide to the Boss AI simple database schema.

## Overview

The Boss AI database uses a minimal 4-table design based on the SIMPLE_DESIGN.md philosophy:

1. **users** - Who can talk to Boss
2. **events** - Calendar appointments
3. **reminders** - Simple notifications
4. **messages** - Conversation log

**Total schema: ~50 lines of SQL** (excluding indexes and views)

## Quick Start

### Local Development (SQLite)

```bash
cd packages/server

# Setup database with sample data
TURSO_DATABASE_URL=file:./test.db npm run setup-db -- --sample

# Reset database (drop all tables and recreate)
TURSO_DATABASE_URL=file:./test.db npm run db:reset
```

### Production (Turso)

```bash
# Set environment variables in .env
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your-token

# Setup schema only
npm run setup-db

# Setup with sample data (for staging)
npm run db:sample

# Reset everything (DANGEROUS - use with caution!)
npm run db:reset
```

## Database Schema

### 1. Users Table

Who can interact with Boss AI.

```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    name TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
```

**Fields:**
- `id` - Unique user identifier (UUID)
- `phone` - Phone number (E.164 format: +1234567890)
- `email` - Email address
- `name` - User's full name
- `is_admin` - Admin flag (routes to Claude Code if true)
- `created_at` - Account creation timestamp (ISO 8601)
- `updated_at` - Last update timestamp (auto-updated)

**Indexes:**
- `idx_users_phone` - Fast phone lookup
- `idx_users_email` - Fast email lookup
- `idx_users_is_admin` - Filter admin users

**Example:**
```sql
INSERT INTO users (id, phone, email, name, is_admin)
VALUES (
    'usr_abc123',
    '+15551234567',
    'alice@example.com',
    'Alice Johnson',
    FALSE
);
```

### 2. Events Table

Calendar appointments and meetings.

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Fields:**
- `id` - Unique event identifier (UUID)
- `user_id` - Owner of this event
- `title` - Event title/description
- `start_time` - Start time (ISO 8601)
- `end_time` - End time (ISO 8601, optional)
- `created_at` - When event was created

**Indexes:**
- `idx_events_user_id` - User's events
- `idx_events_start_time` - Time-based queries
- `idx_events_user_time` - Combined user+time queries

**Example:**
```sql
INSERT INTO events (id, user_id, title, start_time, end_time)
VALUES (
    'evt_xyz789',
    'usr_abc123',
    'Team standup',
    '2025-10-29T09:00:00Z',
    '2025-10-29T09:30:00Z'
);
```

### 3. Reminders Table

Simple notifications to be sent via SMS or email.

```sql
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    due_time TEXT NOT NULL,
    method TEXT DEFAULT 'sms' CHECK(method IN ('sms', 'email')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Fields:**
- `id` - Unique reminder identifier (UUID)
- `user_id` - Who to remind
- `text` - Reminder message
- `due_time` - When to send (ISO 8601)
- `method` - How to send ('sms' or 'email')
- `status` - Current status ('pending', 'sent', 'failed')
- `created_at` - When reminder was created

**Indexes:**
- `idx_reminders_user_id` - User's reminders
- `idx_reminders_status` - Filter by status
- `idx_reminders_due_time` - Time-based queries
- `idx_reminders_pending` - Find reminders to send

**Example:**
```sql
INSERT INTO reminders (id, user_id, text, due_time, method, status)
VALUES (
    'rem_def456',
    'usr_abc123',
    'Review Q4 budget',
    '2025-10-29T14:00:00Z',
    'sms',
    'pending'
);
```

### 4. Messages Table

Conversation log for all channels.

```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel TEXT CHECK(channel IN ('sms', 'email', 'voice', 'api')),
    direction TEXT CHECK(direction IN ('in', 'out')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Fields:**
- `id` - Unique message identifier (UUID)
- `user_id` - User who sent/received message
- `channel` - Communication channel ('sms', 'email', 'voice', 'api')
- `direction` - Message direction ('in' or 'out')
- `content` - Message content
- `created_at` - Timestamp (ISO 8601)

**Indexes:**
- `idx_messages_user_id` - User's messages
- `idx_messages_channel` - Filter by channel
- `idx_messages_created_at` - Time-based queries
- `idx_messages_user_channel` - Combined queries

**Example:**
```sql
INSERT INTO messages (id, user_id, channel, direction, content)
VALUES (
    'msg_ghi789',
    'usr_abc123',
    'sms',
    'in',
    'What is on my schedule today?'
);
```

## Helpful Views

The schema includes several pre-built views for common queries:

### todays_events
Today's scheduled events with user details.

```sql
SELECT * FROM todays_events;
```

### upcoming_events
Events in the next 7 days with countdown.

```sql
SELECT * FROM upcoming_events;
-- Returns: id, user_id, user_name, title, start_time, end_time, hours_until
```

### pending_reminders
All pending reminders with user contact info.

```sql
SELECT * FROM pending_reminders;
-- Returns: id, user_id, user_name, phone, email, text, due_time, method, minutes_until
```

### overdue_reminders
Reminders that need to be sent immediately.

```sql
SELECT * FROM overdue_reminders;
-- Returns: id, user_id, user_name, phone, email, text, due_time, method
```

### recent_messages
Messages from the last 24 hours.

```sql
SELECT * FROM recent_messages;
-- Returns: id, user_id, user_name, channel, direction, content, created_at
```

### conversation_threads
Summary of conversations by user and channel.

```sql
SELECT * FROM conversation_threads;
-- Returns: user_id, user_name, channel, message_count, last_message_at, first_message_at
```

## Common Queries

### Find user by phone or email

```sql
-- By phone
SELECT * FROM users WHERE phone = '+15551234567';

-- By email
SELECT * FROM users WHERE email = 'alice@example.com';
```

### Get user's today's schedule

```sql
SELECT * FROM events
WHERE user_id = 'usr_abc123'
  AND date(start_time) = date('now')
ORDER BY start_time;
```

### Find reminders to send now

```sql
SELECT * FROM reminders
WHERE status = 'pending'
  AND datetime(due_time) <= datetime('now')
ORDER BY due_time;
```

### Get conversation history

```sql
SELECT * FROM messages
WHERE user_id = 'usr_abc123'
  AND channel = 'sms'
ORDER BY created_at DESC
LIMIT 50;
```

### Count messages by channel

```sql
SELECT
    channel,
    direction,
    COUNT(*) as count
FROM messages
GROUP BY channel, direction
ORDER BY count DESC;
```

## Integration with simple-index.js

The schema matches the database interface in `src/simple-index.js`:

```javascript
import { db } from './simple-index.js';

// Find user
const user = await db.findUser('+15551234567', env);

// Log message
await db.logMessage(user.id, 'sms', 'in', 'Hello Boss!', env);

// Create appointment
await db.createAppointment(
    user.id,
    'Team meeting',
    '2025-10-29T14:00:00Z',
    '2025-10-29T15:00:00Z',
    env
);

// Create reminder
await db.createReminder(
    user.id,
    'Call supplier',
    '2025-10-29T16:00:00Z',
    env
);
```

## Migration Strategy

### From Existing Schema

If you have existing data in the old `appointments` and `reminders` tables:

```sql
-- Migrate appointments to events
INSERT INTO events (id, user_id, title, start_time, end_time, created_at)
SELECT id, user_id, title, start_time, end_time, created_at
FROM appointments
WHERE status = 'scheduled';

-- Migrate reminders (keep only pending)
INSERT INTO reminders (id, user_id, text, due_time, method, status, created_at)
SELECT
    id,
    user_id,
    title as text,
    due_time,
    CASE
        WHEN notification_channels LIKE '%sms%' THEN 'sms'
        ELSE 'email'
    END as method,
    CASE
        WHEN completed = TRUE THEN 'sent'
        ELSE 'pending'
    END as status,
    created_at
FROM reminders
WHERE completed = FALSE;
```

## Maintenance

### Cleanup old messages

```sql
-- Delete messages older than 30 days
DELETE FROM messages
WHERE datetime(created_at) < datetime('now', '-30 days');
```

### Archive completed reminders

```sql
-- Mark sent reminders as complete
UPDATE reminders
SET status = 'sent'
WHERE status = 'pending'
  AND datetime(due_time) < datetime('now', '-1 day');
```

### Database statistics

```sql
-- Row counts
SELECT 'Users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Events', COUNT(*) FROM events
UNION ALL
SELECT 'Reminders', COUNT(*) FROM reminders
UNION ALL
SELECT 'Messages', COUNT(*) FROM messages;
```

## Backup and Restore

### Backup (SQLite)

```bash
# Backup local database
sqlite3 test.db ".backup backup.db"

# Export to SQL
sqlite3 test.db ".dump" > backup.sql
```

### Restore (SQLite)

```bash
# Restore from backup
sqlite3 test.db ".restore backup.db"

# Restore from SQL
sqlite3 test.db < backup.sql
```

### Backup (Turso)

```bash
# Use Turso CLI
turso db backup create your-db

# List backups
turso db backup list your-db
```

## Troubleshooting

### "Table already exists" error

This is normal if you run setup multiple times. Use `--reset` to drop all tables first:

```bash
npm run db:reset
```

### "No such table" error

The table hasn't been created. Run setup:

```bash
npm run setup-db
```

### Foreign key constraint failed

Make sure the referenced user exists before creating events/reminders/messages:

```sql
-- Check if user exists
SELECT * FROM users WHERE id = 'usr_abc123';

-- Create user if needed
INSERT INTO users (id, phone, email, name) VALUES (...);
```

### Date/time queries not working

Always use ISO 8601 format and SQLite datetime functions:

```sql
-- Good
WHERE datetime(due_time) <= datetime('now')

-- Bad
WHERE due_time <= NOW()
```

## Performance Tips

1. **Use indexes** - All common queries are indexed
2. **Use views** - Pre-built views are optimized
3. **Batch operations** - Use transactions for multiple inserts
4. **Cleanup old data** - Archive messages older than 30 days
5. **Analyze queries** - Use `EXPLAIN QUERY PLAN` to optimize

## Security

1. **Never store passwords** - Use external auth (Turso handles this)
2. **Sanitize inputs** - Use parameterized queries (already done in simple-index.js)
3. **Limit access** - Set proper Turso permissions
4. **Encrypt tokens** - Keep TURSO_AUTH_TOKEN secret
5. **Audit logs** - Messages table provides audit trail

## Next Steps

- Read [SIMPLE_DESIGN.md](../../SIMPLE_DESIGN.md) for architecture overview
- Check [SIMPLE_ROUTER_README.md](./SIMPLE_ROUTER_README.md) for API usage
- Review [src/simple-index.js](./src/simple-index.js) for implementation
- Test with [test-simple-router.js](./test-simple-router.js)
