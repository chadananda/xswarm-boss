# Schema Compatibility Fix - Complete

## Problem
The message router code (`simple-index.js`) was using complex column names that didn't match the simple database schema:
- Router expected: `user_phone`, `xswarm_phone`, `user_email`, `xswarm_email`, `subscription_tier`
- Database had: `phone`, `email`, `is_admin`
- This caused "SQLITE_ERROR: no such column: user_phone" errors

## Solution
Updated the router to match the SIMPLE_DESIGN.md philosophy and use simple column names.

## Changes Made

### 1. Updated `formatUser()` function
**Before:**
```javascript
export function formatUser(row) {
  return {
    id: row.id,
    name: row.name,
    email: row.email || row.xswarm_email,
    phone: row.user_phone || row.xswarm_phone,
    is_admin: row.subscription_tier === 'admin',
    subscription_tier: row.subscription_tier,
  };
}
```

**After:**
```javascript
export function formatUser(row) {
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    phone: row.phone,
    is_admin: row.is_admin === 1 || row.is_admin === true,
  };
}
```

### 2. Updated `db.findUser()` function
**Before:**
```javascript
const result = await client.execute({
  sql: isPhone
    ? 'SELECT * FROM users WHERE user_phone = ? OR xswarm_phone = ?'
    : 'SELECT * FROM users WHERE email = ? OR xswarm_email = ?',
  args: [identifier, identifier],
});
```

**After:**
```javascript
const result = await client.execute({
  sql: isPhone
    ? 'SELECT * FROM users WHERE phone = ?'
    : 'SELECT * FROM users WHERE email = ?',
  args: [identifier],
});
```

### 3. Updated email sender
**Before:**
```javascript
from: { email: env.ADMIN_XSWARM_EMAIL || 'boss@xswarm.ai' }
```

**After:**
```javascript
from: { email: env.ADMIN_EMAIL || 'boss@xswarm.ai' }
```

### 4. Updated admin user config fallback
**Before:**
```javascript
const adminPhone = env.ADMIN_PHONE || env.ADMIN_XSWARM_PHONE;
const adminEmail = env.ADMIN_EMAIL || env.ADMIN_XSWARM_EMAIL;
```

**After:**
```javascript
const adminPhone = env.ADMIN_PHONE;
const adminEmail = env.ADMIN_EMAIL;
```

### 5. Fixed table names to match schema
- Changed `appointments` table to `events` table
- Updated `createAppointment()` to insert into `events` table
- Updated `getAppointments()` to query from `events` table
- Removed unused columns: `timezone`, `status` from events
- Updated `createReminder()` to use correct columns: `text`, `method`, `status` instead of `title`, `completed`, `priority`

### 6. Updated all test data
Updated test cases to use simple column names:
- Changed `user_phone` to `phone`
- Changed `xswarm_phone` to `phone`
- Changed `subscription_tier` to `is_admin`
- Removed `subscription_tier` from test data
- Added test for SQLite numeric boolean handling (`is_admin: 1`)

## Test Results

### Unit Tests
All 47 pure function tests pass:
```
✔ tests 47
✔ pass 47
✔ fail 0
```

### Database Integration Tests
All database tests pass:
```
✓ Schema verification passed
✓ Users: 4 records
✓ Events: 6 records  
✓ Reminders: 6 records
✓ Messages: 10 records
✓ Found admin user: Boss Admin (is_admin: Yes)
✓ Found regular user: Alice Johnson (is_admin: No)
```

### Router Integration Tests
All message routing tests pass:
```
✓ Schedule command processed successfully
✓ Reminder command processed successfully  
✓ Calendar command processed successfully
✓ Admin message routed successfully
✓ Unknown user rejected correctly
✓ Messages are being logged to database
```

## Database Schema
The simple schema now being used:

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

CREATE TABLE events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    text TEXT NOT NULL,
    due_time TEXT NOT NULL,
    method TEXT DEFAULT 'sms',
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    channel TEXT,
    direction TEXT,
    content TEXT,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Benefits
1. **Simplicity**: Code now follows SIMPLE_DESIGN.md philosophy
2. **Compatibility**: Router works with simple database schema
3. **Maintainability**: Fewer column names to track
4. **Testability**: All tests updated and passing
5. **Clarity**: Single source of truth for user data (no xswarm vs user distinction)

## Files Modified
- `/packages/server/src/simple-index.js` - Router implementation
- `/packages/server/src/simple-index.test.js` - Unit tests
- `/packages/server/test-simple-router.js` - Integration test (created)

## Verification Commands
```bash
# Run unit tests
cd packages/server
npm test

# Create test database
TURSO_DATABASE_URL=file:./test-integration.db node scripts/setup-db.js --reset --sample

# Run database tests
TURSO_DATABASE_URL=file:./test-integration.db node test-database.js

# Run integration tests
TURSO_DATABASE_URL=file:./test-integration.db node test-simple-router.js
```

All tests pass successfully! ✓
