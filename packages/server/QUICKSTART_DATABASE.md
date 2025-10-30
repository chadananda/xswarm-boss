# Database Quick Start Guide

Get the Boss AI database up and running in 60 seconds.

## TL;DR

```bash
cd packages/server

# Local development with sample data
TURSO_DATABASE_URL=file:./test.db npm run setup-db -- --sample

# Verify it worked
sqlite3 test.db "SELECT * FROM users;"
```

## Setup Commands

### Initial Setup

```bash
# Setup schema only (no data)
TURSO_DATABASE_URL=file:./test.db npm run setup-db

# Setup with sample data (recommended for development)
TURSO_DATABASE_URL=file:./test.db npm run setup-db -- --sample

# Reset everything (drop all tables and recreate)
TURSO_DATABASE_URL=file:./test.db npm run db:reset
```

### Production Setup (Turso)

```bash
# Set environment variables
export TURSO_DATABASE_URL=libsql://your-db.turso.io
export TURSO_AUTH_TOKEN=your-token

# Setup schema
npm run setup-db

# Or setup with sample data (staging environment)
npm run db:sample
```

## Sample Data Included

After running `--sample`, you'll have:

**Users:**
- Admin: `+1234567890` / `admin@example.com` (is_admin: true)
- Alice: `+1234567891` / `alice@example.com`
- Bob: `+1234567892` / `bob@example.com`
- Carol: `+1234567893` / `carol@example.com`

**Events:**
- 3 events today
- 2 events tomorrow
- 1 event next week

**Reminders:**
- 3 pending reminders (upcoming)
- 1 overdue reminder (should trigger)
- 2 sent reminders (historical)

**Messages:**
- 10 sample messages across SMS, email, and API channels

## Quick Queries

```bash
# View all users
sqlite3 test.db "SELECT name, phone, email, is_admin FROM users;"

# View today's schedule
sqlite3 test.db "SELECT * FROM todays_events;"

# View pending reminders
sqlite3 test.db "SELECT user_name, text, due_time, method FROM pending_reminders;"

# View conversation threads
sqlite3 test.db "SELECT * FROM conversation_threads;"

# View recent messages
sqlite3 test.db "SELECT user_name, channel, direction, content FROM recent_messages LIMIT 10;"
```

## Testing the Router

Once the database is set up, test the message router:

```bash
# Run the simple router tests
npm test

# Test with the test script
node test-simple-router.js
```

## Resetting the Database

```bash
# Quick reset with sample data
npm run db:reset

# Manual reset
rm test.db
TURSO_DATABASE_URL=file:./test.db npm run setup-db -- --sample
```

## Troubleshooting

### "No such table" error

The database hasn't been initialized. Run:

```bash
TURSO_DATABASE_URL=file:./test.db npm run setup-db
```

### "Table already exists" warning

This is normal. The script uses `CREATE TABLE IF NOT EXISTS`. To start fresh:

```bash
npm run db:reset
```

### Want to see what's in the database?

```bash
# Open SQLite interactive shell
sqlite3 test.db

# Then run queries
sqlite> .tables
sqlite> .schema users
sqlite> SELECT * FROM users;
sqlite> .quit
```

## Database Schema

4 simple tables:

1. **users** - Who can talk to Boss
2. **events** - Calendar appointments
3. **reminders** - Simple notifications
4. **messages** - Conversation log

Plus helpful views:
- `todays_events` - Today's schedule
- `upcoming_events` - Next 7 days
- `pending_reminders` - Reminders to send
- `overdue_reminders` - Reminders past due
- `recent_messages` - Last 24 hours
- `conversation_threads` - Conversation summary

## Next Steps

1. Read [DATABASE.md](./DATABASE.md) for complete schema documentation
2. Read [SIMPLE_DESIGN.md](../../SIMPLE_DESIGN.md) for architecture overview
3. Check [src/simple-index.js](./src/simple-index.js) for database interface
4. Run tests with `npm test`

---

**Need help?** Check [DATABASE.md](./DATABASE.md) for detailed documentation.
