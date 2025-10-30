# Database Schema

## User Architecture

**IMPORTANT**: The system has two types of users:

1. **Admin User** (Single, Config-based)
   - Configured in `config.toml` under `[admin]` section
   - Loaded via `ProjectConfig.admin` in Rust
   - Has full access to ALL features
   - NOT stored in database
   - Used for system administration and management

2. **Regular Users** (Multiple, Database-based)
   - Stored in Turso database
   - Limited permissions based on subscription tier
   - Managed via `users.js` module
   - Subject to feature limits and billing

## Users Table Schema

```sql
CREATE TABLE users (
  -- Identity
  id TEXT PRIMARY KEY,                    -- UUID v4
  username TEXT UNIQUE NOT NULL,          -- Unique username
  name TEXT,                              -- Display name (optional)

  -- Contact Information
  email TEXT UNIQUE NOT NULL,             -- User's real email
  user_phone TEXT NOT NULL,               -- User's real phone (E.164 format)

  -- xSwarm Assignments
  xswarm_email TEXT UNIQUE NOT NULL,      -- Assigned email (username@xswarm.ai)
  xswarm_phone TEXT UNIQUE,               -- Assigned phone (E.164 format, premium only)

  -- Subscription & Persona
  subscription_tier TEXT NOT NULL DEFAULT 'free',  -- free, premium, enterprise
  persona TEXT NOT NULL DEFAULT 'boss',            -- Selected AI persona
  wake_word TEXT,                                  -- Custom wake word (optional)

  -- Stripe Integration
  stripe_customer_id TEXT UNIQUE,         -- Stripe customer ID
  stripe_subscription_id TEXT,            -- Stripe subscription ID (if premium)

  -- Timestamps
  created_at TEXT NOT NULL,               -- ISO 8601 timestamp
  updated_at TEXT                         -- ISO 8601 timestamp
);

-- Indexes for fast lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_xswarm_email ON users(xswarm_email);
CREATE INDEX idx_users_xswarm_phone ON users(xswarm_phone);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);
CREATE INDEX idx_users_subscription_tier ON users(subscription_tier);
```

## Subscription Tiers

### Free Tier
- **Email**: 100 emails/day (unlimited receive)
- **Voice**: Not available
- **SMS**: Not available
- **Phone**: No assigned phone number
- **Price**: $0/month

### Premium Tier
- **Email**: Unlimited
- **Voice**: 100 minutes/month included, $0.013/min overage
- **SMS**: 100 messages/month included, $0.0075/msg overage
- **Phone**: 1 phone number included, $2/month per additional
- **Price**: $9.99/month

### Admin Tier (Config-based only)
- **Email**: Unlimited
- **Voice**: Unlimited
- **SMS**: Unlimited
- **Phone**: Assigned in config
- **Price**: N/A (system admin)
- **Special**: Full system access, can manage all users

## User Permissions

### Regular Users Can:
- Send/receive emails (based on tier)
- Send/receive SMS (premium+)
- Make/receive voice calls (premium+)
- Customize persona and wake word
- View their own usage and billing
- Manage their own subscription

### Regular Users CANNOT:
- Provision phone numbers for others
- View other users' data
- Manage other users' subscriptions
- Modify system configuration
- Access admin-only features

### Admin User Can (Config-based):
- Everything regular users can do
- Provision phone numbers for any user
- View all users' data
- Manage all subscriptions
- Modify system configuration
- Access all communication channels
- Override feature limits

## Example User Records

### Regular User (Free Tier)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "name": "John Doe",
  "email": "john@example.com",
  "user_phone": "+15551234567",
  "xswarm_email": "john_doe@xswarm.ai",
  "xswarm_phone": null,
  "subscription_tier": "free",
  "persona": "boss",
  "wake_word": "hey boss",
  "stripe_customer_id": "cus_xxxxxxxxxxxxx",
  "stripe_subscription_id": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Regular User (Premium Tier)
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "username": "jane_smith",
  "name": "Jane Smith",
  "email": "jane@example.com",
  "user_phone": "+15559876543",
  "xswarm_email": "jane_smith@xswarm.ai",
  "xswarm_phone": "+18005551234",
  "subscription_tier": "premium",
  "persona": "hal-9000",
  "wake_word": "hey hal",
  "stripe_customer_id": "cus_yyyyyyyyyyyyy",
  "stripe_subscription_id": "sub_zzzzzzzzzzzzz",
  "created_at": "2025-01-10T08:15:00Z",
  "updated_at": "2025-01-20T14:22:00Z"
}
```

### Admin User (Config-based, NOT in database)
```toml
[admin]
username = "admin"
name = "Admin User"
email = "admin@xswarm.dev"
phone = "+15559876543"
xswarm_email = "admin@xswarm.ai"
xswarm_phone = "+18005559876"
persona = "boss"
wake_word = "hey boss"
subscription_tier = "admin"

# Admin-only permissions
access_level = "superadmin"
can_provision_numbers = true
can_view_all_users = true
can_manage_subscriptions = true
can_manage_config = true
can_access_all_channels = true
```

## Migration Path

When implementing database integration:

1. **Admin User**:
   - Load from `config.toml` via `ProjectConfig::load()`
   - Access via `config.get_admin()`
   - Check admin status via `config.is_admin_by_email()` or `config.is_admin_by_phone()`

2. **Regular Users**:
   - Load from Turso database via `users.js` functions
   - Create new users via `createUser()`
   - Update via `updateUserTier()`, `updateUserPhone()`, etc.
   - Check permissions via `userHasFeature()`

3. **Authentication Flow**:
   ```javascript
   // First, check if admin user
   if (config.is_admin_by_email(email)) {
     user = config.get_admin();
     user.is_admin = true;
   } else {
     // Regular user from database
     user = await getUserByEmail(email, env);
     user.is_admin = false;
   }

   // Check feature access
   if (user.is_admin || userHasFeature(user, 'voice')) {
     // Allow voice access
   }
   ```

## Usage Tracking Table (Future)

For metered billing on premium tier:

```sql
CREATE TABLE usage_records (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id),
  period_start TEXT NOT NULL,     -- ISO 8601 billing period start
  period_end TEXT NOT NULL,       -- ISO 8601 billing period end
  voice_minutes INTEGER DEFAULT 0,
  sms_messages INTEGER DEFAULT 0,
  email_count INTEGER DEFAULT 0,
  phone_numbers INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT
);

CREATE INDEX idx_usage_user ON usage_records(user_id);
CREATE INDEX idx_usage_period ON usage_records(period_start, period_end);
```

## Notes

- **All phone numbers**: E.164 format (e.g., `+15551234567`)
- **All timestamps**: ISO 8601 format (e.g., `2025-01-15T10:30:00Z`)
- **UUIDs**: Version 4 (random)
- **Email domains**: xSwarm emails use `@xswarm.ai`
- **Admin user**: NEVER in database, always in config.toml
- **Regular users**: NEVER in config.toml, always in database
