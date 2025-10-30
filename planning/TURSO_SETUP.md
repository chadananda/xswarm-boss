# Turso Database Setup Guide

Complete guide for setting up Turso database with automated backups and edge replication.

---

## Overview

Turso is a distributed SQLite database built on libSQL. It provides:
- **Edge replication** - Deploy database close to users globally
- **Automatic backups** - Built-in point-in-time recovery
- **Embedded replicas** - Local SQLite file with cloud sync
- **FREE tier** - 9GB storage, 1B row reads/month

**xSwarm uses Turso for:**
- User accounts and authentication
- Subscription data (tier, Stripe IDs)
- xSwarm phone/email assignments
- User preferences (persona, wake word)

---

## Initial Setup

### 1. Install Turso CLI

```bash
# macOS/Linux
curl -sSfL https://get.tur.so/install.sh | bash

# Verify installation
turso --version
```

### 2. Create Account

```bash
# Sign up (opens browser)
turso auth signup

# Or login if you have account
turso auth login
```

### 3. Create Database

```bash
# Create database in primary region
turso db create xswarm-users --location sjc

# Output:
# Created database xswarm-users in sjc in 2 seconds
# Database URL: libsql://xswarm-users-[your-org].turso.io
```

**Regions:**
- `sjc` - San Jose (US West)
- `iad` - Virginia (US East)
- `fra` - Frankfurt (Europe)
- `lhr` - London (Europe)
- `nrt` - Tokyo (Asia)
- `syd` - Sydney (Australia)

### 4. Add Edge Replicas (Optional, for global apps)

```bash
# Add replicas in other regions
turso db replicate xswarm-users iad   # US East
turso db replicate xswarm-users fra   # Europe
turso db replicate xswarm-users nrt   # Asia

# View replicas
turso db show xswarm-users
```

### 5. Get Connection Details

```bash
# Get database URL
turso db show xswarm-users --url

# Get auth token
turso db tokens create xswarm-users
```

---

## Configuration

### Update config.toml

```toml
[turso]
database_name = "xswarm-users"
organization = "your-org"  # From database URL
database_url = "libsql://xswarm-users-your-org.turso.io"
primary_region = "sjc"
replica_regions = ["iad", "fra", "nrt"]

[turso.local_replica]
enabled = true
sync_interval_seconds = 60
local_db_path = "~/.local/share/xswarm/users.db"

[turso.backup]
enabled = true
retention_days = 30
```

### Add Secrets to .env

```bash
# .env
TURSO_AUTH_TOKEN=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...
```

**Important:** Never commit `.env` with your auth token!

---

## Database Schema

### Create Tables

```bash
# Open database shell
turso db shell xswarm-users
```

```sql
-- Users table
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  phone TEXT,
  xswarm_email TEXT NOT NULL UNIQUE,
  xswarm_phone TEXT,
  subscription_tier TEXT DEFAULT 'free',
  persona TEXT DEFAULT 'hal-9000',
  wake_word TEXT DEFAULT 'hey hal',
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_xswarm_phone ON users(xswarm_phone);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);

-- Subscription items table (for metered billing)
CREATE TABLE subscription_items (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  subscription_id TEXT NOT NULL,
  voice_item_id TEXT,
  sms_item_id TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Usage tracking table (current billing period)
CREATE TABLE usage (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  period_start TIMESTAMP NOT NULL,
  period_end TIMESTAMP NOT NULL,
  voice_minutes INTEGER DEFAULT 0,
  sms_messages INTEGER DEFAULT 0,
  phone_numbers INTEGER DEFAULT 0,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_usage_user_period ON usage(user_id, period_start);
```

### Insert Test Data

```sql
-- Test user
INSERT INTO users (
  id,
  email,
  phone,
  xswarm_email,
  xswarm_phone,
  subscription_tier
) VALUES (
  'test-123',
  'test@example.com',
  '+15551234567',
  'test@xswarm.ai',
  '+18005551001',
  'premium'
);

-- Admin user
INSERT INTO users (
  id,
  email,
  phone,
  xswarm_email,
  subscription_tier
) VALUES (
  'admin-456',
  'admin@xswarm.dev',
  '+15559876543',
  'admin@xswarm.ai',
  'enterprise'
);
```

---

## Automated Backups

### Built-in Backups

Turso automatically backs up your database:
- **Continuous**: Every write is replicated
- **Point-in-time recovery**: Restore to any point in last 30 days (Pro plan)
- **Free tier**: 24-hour point-in-time recovery

### View Backups

```bash
# List available recovery points
turso db show xswarm-users --recovery-points
```

### Restore from Backup

```bash
# Restore to specific timestamp
turso db restore xswarm-users --timestamp "2025-10-22T10:30:00Z"

# Or restore to new database
turso db create xswarm-users-restored --from-backup xswarm-users --timestamp "2025-10-22T10:30:00Z"
```

### Manual Backups (Extra Safety)

```bash
# Export entire database
turso db dump xswarm-users > backup-$(date +%Y%m%d).sql

# Schedule with cron (optional)
# Add to crontab: crontab -e
0 2 * * * cd ~/backups && turso db dump xswarm-users > xswarm-backup-$(date +\%Y\%m\%d).sql
```

---

## Local Embedded Replica

Turso supports embedded replicas - a local SQLite file that syncs with cloud.

### Enable in Code

```rust
use libsql::{Builder, Database};

// Create embedded replica
let db = Builder::new_remote_replica(
    "~/.local/share/xswarm/users.db",  // Local file
    "libsql://xswarm-users-your-org.turso.io",  // Remote URL
    env::var("TURSO_AUTH_TOKEN")?
)
.sync_interval(std::time::Duration::from_secs(60))
.build()
.await?;

// All queries hit local file (fast!)
let rows = db.query("SELECT * FROM users", ()).await?;

// Changes sync to cloud every 60 seconds
```

### Benefits

- **Zero-latency reads** - Local SQLite file
- **Automatic sync** - Changes replicate to cloud
- **Offline support** - Works without internet
- **Backup** - Cloud backup even if local disk fails

---

## Monitoring

### Database Stats

```bash
# View database info
turso db show xswarm-users

# Output:
# Name: xswarm-users
# URL: libsql://xswarm-users-your-org.turso.io
# Locations: sjc (primary), iad, fra, nrt
# Size: 42.3 MB
# Tables: 3
# Rows: 1,247
```

### Usage Metrics

```bash
# View usage
turso db usage xswarm-users

# Output:
# Rows read: 125,342 / 1,000,000,000 (FREE tier limit)
# Rows written: 4,231 / 1,000,000,000
# Storage: 42.3 MB / 9 GB
```

### Logs

```bash
# View recent queries (Pro plan)
turso db logs xswarm-users
```

---

## Performance Optimization

### Indexes

Already created above, but important ones:

```sql
-- Fast email lookups (for login)
CREATE INDEX idx_users_email ON users(email);

-- Fast phone lookups (for incoming calls/SMS)
CREATE INDEX idx_users_xswarm_phone ON users(xswarm_phone);

-- Fast Stripe customer lookups (for webhooks)
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);
```

### Connection Pooling

```rust
// Reuse database connection
static DB: OnceCell<Database> = OnceCell::new();

pub fn get_db() -> &'static Database {
    DB.get_or_init(|| {
        // Initialize once, reuse forever
        Builder::new_remote(
            "libsql://xswarm-users-your-org.turso.io",
            env::var("TURSO_AUTH_TOKEN").unwrap()
        ).build().await.unwrap()
    })
}
```

### Edge Replication

Deploy replicas in regions where users are:

```bash
# Check latency from user's location
turso db show xswarm-users --latency

# Add replica if needed
turso db replicate xswarm-users [region]
```

---

## Security

### Auth Tokens

```bash
# Create token with expiration (recommended)
turso db tokens create xswarm-users --expiration 90d

# Rotate token
turso db tokens create xswarm-users  # New token
# Update .env with new token
# Delete old token after rotation
turso db tokens revoke xswarm-users [old-token-id]
```

### Access Control

```sql
-- Turso supports row-level security (RLS) on Pro plan
-- Example: Users can only see their own data

CREATE POLICY user_isolation ON users
  USING (auth.user_id() = id);
```

### Encryption

- **In transit**: TLS 1.3 for all connections
- **At rest**: AES-256 encryption for all data

---

## Costs

### FREE Tier (Perfect for MVP)

- **Storage**: 9 GB
- **Row reads**: 1 billion/month
- **Row writes**: 1 billion/month
- **Locations**: 3 regions
- **Databases**: 500
- **Point-in-time recovery**: 24 hours

**Estimated xSwarm usage (1,000 users):**
- Storage: ~100 MB (well under 9 GB)
- Reads: ~10M/month (1% of limit)
- Writes: ~500K/month (0.05% of limit)

**Cost: $0/month**

### Scaler Plan ($29/month)

If you exceed free tier:
- **Storage**: 50 GB
- **Row operations**: Unlimited
- **Point-in-time recovery**: 30 days
- **Priority support**

---

## Troubleshooting

### Connection Errors

```bash
# Test connection
turso db shell xswarm-users

# If fails, check:
turso auth whoami  # Verify logged in
turso db show xswarm-users  # Verify database exists
```

### Sync Issues

```bash
# Force sync local replica
turso db sync xswarm-users

# Reset local replica
rm ~/.local/share/xswarm/users.db
# Will re-sync from cloud on next connection
```

### Performance Issues

```sql
-- Check slow queries
EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'alice@example.com';

-- Verify indexes exist
SELECT name FROM sqlite_master WHERE type='index';
```

---

## Migration from SQLite

If you're moving from local SQLite:

```bash
# 1. Export existing database
sqlite3 old-database.db .dump > data.sql

# 2. Import to Turso
turso db shell xswarm-users < data.sql

# 3. Verify data
turso db shell xswarm-users
sqlite> SELECT COUNT(*) FROM users;
```

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [Turso Docs](https://docs.turso.tech/) - Official documentation

---

## Quick Setup Checklist

- [ ] Install Turso CLI
- [ ] Create account: `turso auth signup`
- [ ] Create database: `turso db create xswarm-users --location sjc`
- [ ] Add replicas (optional): `turso db replicate xswarm-users [region]`
- [ ] Get auth token: `turso db tokens create xswarm-users`
- [ ] Add to `.env`: `TURSO_AUTH_TOKEN=...`
- [ ] Update `config.toml` with database URL and org
- [ ] Create schema: Run SQL commands above
- [ ] Test connection: `turso db shell xswarm-users`
- [ ] Enable local replica in code
- [ ] Set up backup schedule (optional)

---

**Next:** Set up Cloudflare Workers and webhook server
