# xSwarm Architecture - Config & User Data

## Three-Layer System

xSwarm uses a clean separation between secrets, configuration, and user data:

```
┌─────────────────────────────────────────────────────────┐
│                    Project Config                        │
│                   (config.toml)                          │
│  ✅ Committed to git                                    │
│  • Feature flags                                         │
│  • Service account IDs                                   │
│  • Test user settings                                    │
│  • Admin user settings                                   │
│  • Default configurations                                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      Secrets                             │
│                      (.env)                              │
│  ❌ NEVER committed                                      │
│  • API keys                                              │
│  • Auth tokens                                           │
│  • Webhook secrets                                       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    User Data                             │
│                 (Turso Database)                         │
│  💾 Stored in cloud                                      │
│  • User email & phone                                    │
│  • Subscription tier                                     │
│  • xSwarm phone/email assignments                        │
│  • Persona preferences                                   │
│  • Stripe customer IDs                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Why This Architecture?

### ❌ What We DON'T Do

**No individual user config files:**
- ❌ No `~/.config/xswarm/config.toml` per user
- ❌ No local user preferences
- ❌ No per-user configuration files

**Why not?**
- Not scalable (imagine 10,000 users)
- Hard to sync across devices
- Can't be managed centrally
- No backups or replication

### ✅ What We DO Instead

**Database-centric user data:**
- ✅ All user settings in Turso database
- ✅ Centralized and synced automatically
- ✅ Backed up by Turso
- ✅ Accessible from anywhere

**Config file for test/admin only:**
- ✅ Test user for local development
- ✅ Admin user for management
- ✅ Safe to commit to git

---

## config.toml Structure

```toml
environment = "production"

# Service Configuration (non-secret)
[twilio]
account_sid = "AC1234567890"  # Not secret, just an ID

[stripe]
publishable_key = "pk_test_xxx"  # Safe for client-side

[stripe.prices]
premium = "price_1234567890"
voice = "price_0987654321"
sms = "price_1122334455"

# Test User (for local development)
[test_user]
email = "test@example.com"
phone = "+15551234567"
subscription_tier = "premium"
persona = "hal-9000"
xswarm_email = "test@xswarm.ai"
xswarm_phone = "+18005551001"

# Admin User (for management)
[admin]
email = "admin@xswarm.dev"
phone = "+15559876543"
access_level = "superadmin"
can_provision_numbers = true
can_view_all_users = true

# Feature Flags
[features]
voice_enabled = true
sms_enabled = true
stripe_enabled = true
```

---

## Database Schema

```sql
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
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_xswarm_phone ON users(xswarm_phone);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);
```

---

## User Lifecycle

### 1. User Signs Up

```
User enters email on website
    ↓
POST /api/signup { email, phone }
    ↓
INSERT INTO users (id, email, phone, xswarm_email)
VALUES (uuid(), 'alice@example.com', '+15551234567', 'alice@xswarm.ai')
    ↓
Return user_id to client
```

### 2. User Upgrades to Premium

```
User clicks "Upgrade" button
    ↓
Redirect to Stripe Checkout
    ↓
User enters payment info
    ↓
Stripe webhook: subscription.created
    ↓
UPDATE users SET
  subscription_tier = 'premium',
  stripe_customer_id = 'cus_xxx',
  stripe_subscription_id = 'sub_xxx'
WHERE id = 'user_id'
    ↓
Provision toll-free number
    ↓
UPDATE users SET xswarm_phone = '+18005551234'
WHERE id = 'user_id'
```

### 3. User Changes Persona

```
User runs: xswarm config set persona jarvis
    ↓
UPDATE users SET persona = 'jarvis'
WHERE id = 'user_id'
    ↓
Settings synced automatically
```

---

## Code Examples

### Rust: Access User Data

```rust
use xswarm::config::ProjectConfig;
use xswarm::database::User;

// Load project config
let config = ProjectConfig::load()?;

// For testing: use test user from config
let test_user = &config.test_user;
println!("Testing with: {}", test_user.email);

// For production: load user from database
let user = User::get_by_email("alice@example.com")?;
println!("User: {} ({})", user.email, user.subscription_tier);

// Access user's settings
println!("Persona: {}", user.persona);
println!("Phone: {:?}", user.xswarm_phone);
```

### Node.js: Access User Data

```javascript
import { loadConfig } from './scripts/load-config.js';
import { getUserByEmail } from './lib/database.js';

// Load project config and secrets
const { secrets, config } = loadConfig();

// For testing: use test user
const testUser = config.test_user;
console.log(`Test user: ${testUser.email}`);

// For production: load user from database
const user = await getUserByEmail('alice@example.com');
console.log(`User: ${user.email} (${user.subscription_tier})`);
console.log(`xSwarm phone: ${user.xswarm_phone}`);
```

---

## Development Workflow

### Local Development

```bash
# 1. Start with test user from config.toml
xswarm dev

# Uses test_user settings:
#   email: test@example.com
#   phone: +15551234567
#   tier: premium
```

### Testing with Real Users

```bash
# 1. Create test user in database
turso db shell xswarm-users

INSERT INTO users (id, email, phone, xswarm_email, subscription_tier)
VALUES ('test-123', 'alice@example.com', '+15551234567', 'alice@xswarm.ai', 'premium');

# 2. Test with real database user
xswarm test --user alice@example.com
```

### Production

```bash
# Real users come from database automatically
# No config file needed per user
```

---

## Benefits

### Scalability
- ✅ Supports unlimited users
- ✅ No per-user config files to manage
- ✅ Database handles millions of records

### Security
- ✅ User data properly secured in database
- ✅ No sensitive data in config files
- ✅ Proper access control via database permissions

### Maintainability
- ✅ Single source of truth (database)
- ✅ Easy to backup (Turso replication)
- ✅ Simple to update user settings

### Developer Experience
- ✅ Test user in config.toml for easy development
- ✅ No need to seed database for basic testing
- ✅ Clear separation of concerns

---

## Migration from Old Architecture

If you had `~/.config/xswarm/config.toml` per user:

**Old (per-user config files):**
```toml
# ~/.config/xswarm/config.toml
[user]
email = "alice@example.com"
subscription_tier = "premium"
```

**New (database + test user):**
```sql
-- Database
INSERT INTO users VALUES ('123', 'alice@example.com', 'premium', ...);
```

```toml
# config.toml (test user only)
[test_user]
email = "test@example.com"
subscription_tier = "premium"
```

---

## FAQ

**Q: Where do I configure MY settings as a developer?**
A: Use the test_user section in `config.toml` for local testing.

**Q: How do real users configure their settings?**
A: Through the CLI (`xswarm config set persona jarvis`) which updates the database.

**Q: Can I have multiple test users?**
A: Add them to the database for testing. The config test_user is just a default.

**Q: What about admin settings?**
A: Admin credentials are in `config.toml` under `[admin]` section.

**Q: Is this like a traditional SaaS?**
A: Yes! Config for project settings, database for user data. Standard architecture.

---

## Related Documentation

- [DATABASE.md](./planning/DATABASE.md) - Database schema (TODO)
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup

---

**Summary:** Config files for project settings and test users. Database for real user data. Clean, scalable, standard SaaS architecture.
