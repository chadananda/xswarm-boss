# User Configuration Migration Guide

## Overview

This guide documents the migration from a mixed user configuration system to a unified system where:
- **Admin user**: Single user configured in `config.toml` with full system access
- **Regular users**: Multiple users stored in Turso database with limited permissions

## Architecture Changes

### Before (Mixed/Unclear)
- Users could be in config files OR database
- No clear distinction between admin and regular users
- Unclear permission boundaries

### After (Clean Separation)
```
┌─────────────────────────────────────────┐
│         config.toml [admin]             │
│  ┌───────────────────────────────────┐  │
│  │  Admin User (Single)              │  │
│  │  - Full system access             │  │
│  │  - Can manage all users           │  │
│  │  - Can provision resources        │  │
│  │  - Unlimited features             │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│        Turso Database (users)           │
│  ┌───────────────────────────────────┐  │
│  │  Regular Users (Multiple)         │  │
│  │  - Limited permissions            │  │
│  │  - Tier-based features            │  │
│  │  - Cannot manage others           │  │
│  │  - Subject to billing limits      │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

## File Changes

### 1. config.toml (Project Root)

**Changed:**
- Removed `[[users]]` array (was for multiple users)
- Enhanced `[admin]` section with full user configuration
- Admin now has all user fields + admin permissions

**New Admin Section:**
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

### 2. packages/core/src/config.rs

**Changed:**
- Removed `UserConfig` struct (was for `[[users]]` array)
- Removed old `AdminConfig` struct (was limited)
- Added `AdminUserConfig` struct (full user + admin permissions)
- Added `UserData` struct (database users with enhanced fields)
- Added `SubscriptionTiers` and `TierConfig` structs
- Updated `ProjectConfig` to use `admin: AdminUserConfig`

**Key Structs:**

```rust
// Admin user (config.toml only)
pub struct AdminUserConfig {
    pub username: String,
    pub name: String,
    pub email: String,
    pub phone: String,
    pub xswarm_email: String,
    pub xswarm_phone: String,
    pub persona: String,
    pub wake_word: String,
    pub subscription_tier: String,  // "admin"

    // Admin permissions
    pub access_level: String,
    pub can_provision_numbers: bool,
    pub can_view_all_users: bool,
    pub can_manage_subscriptions: bool,
    pub can_manage_config: bool,
    pub can_access_all_channels: bool,
}

// Regular users (database only)
pub struct UserData {
    pub id: String,
    pub username: String,
    pub name: Option<String>,
    pub email: String,
    pub user_phone: String,
    pub xswarm_email: String,
    pub xswarm_phone: Option<String>,
    pub subscription_tier: String,  // "free", "premium", "enterprise"
    pub persona: String,
    pub wake_word: Option<String>,
    pub stripe_customer_id: Option<String>,
    pub stripe_subscription_id: Option<String>,
    pub created_at: String,
    pub updated_at: Option<String>,
}
```

**New Helper Methods:**
```rust
impl ProjectConfig {
    pub fn get_admin(&self) -> &AdminUserConfig { ... }
    pub fn is_admin_by_email(&self, email: &str) -> bool { ... }
    pub fn is_admin_by_phone(&self, phone: &str) -> bool { ... }
    pub fn get_tier_config(&self, tier: &str) -> Option<&TierConfig> { ... }
}
```

### 3. packages/server/src/lib/users.js (NEW)

**Purpose:** Manage regular users in the database

**Key Functions:**
- `getUserById(userId, env)` - Get user by ID
- `getUserByEmail(email, env)` - Get user by email
- `getUserByPhone(phone, env)` - Get user by phone
- `getUserByXswarmPhone(xswarmPhone, env)` - Get user by xSwarm phone
- `getUserByStripeCustomerId(customerId, env)` - Get user by Stripe ID
- `createUser(userData, env)` - Create new user
- `updateUserTier(userId, tier, env)` - Update subscription
- `updateUserPhone(userId, xswarmPhone, env)` - Update phone
- `updateUserStripeInfo(userId, customerId, subscriptionId, env)` - Update Stripe
- `listUsers(env, limit, offset)` - List all users (admin only)
- `deleteUser(userId, env)` - Delete user (admin only)
- `userHasFeature(user, feature)` - Check feature access

### 4. packages/server/src/lib/database.js

**Changed:**
- Now just re-exports from `users.js`
- Maintains backward compatibility
- Includes deprecation notice

## Usage Examples

### Loading Admin User (Rust)

```rust
use crate::config::ProjectConfig;

// Load project config
let config = ProjectConfig::load()?;

// Get admin user
let admin = config.get_admin();
println!("Admin: {} <{}>", admin.name, admin.email);

// Check if email is admin
if config.is_admin_by_email("admin@xswarm.dev") {
    println!("This is the admin user!");
}

// Admin always has full access
if admin.can_provision_numbers {
    // Provision phone numbers
}
```

### Managing Regular Users (JavaScript)

```javascript
import {
  getUserByEmail,
  createUser,
  updateUserTier,
  userHasFeature,
} from './lib/users.js';

// Create a new regular user
const newUser = await createUser({
  username: 'john_doe',
  email: 'john@example.com',
  user_phone: '+15551234567',
  xswarm_email: 'john_doe@xswarm.ai',
  subscription_tier: 'free',
  persona: 'boss',
}, env);

// Get user by email
const user = await getUserByEmail('john@example.com', env);

// Check feature access
if (userHasFeature(user, 'voice')) {
  // User has voice access (premium or admin)
  await initiateVoiceCall(user);
} else {
  // User does not have voice access (free tier)
  throw new Error('Voice requires premium subscription');
}

// Upgrade user to premium
await updateUserTier(user.id, 'premium', env);
```

### Authentication Flow (JavaScript)

```javascript
import { ProjectConfig } from './config.js';
import { getUserByEmail } from './lib/users.js';

async function authenticateUser(email, env) {
  // Load project config
  const config = ProjectConfig.load();

  // Check if admin user
  if (config.is_admin_by_email(email)) {
    return {
      ...config.get_admin(),
      is_admin: true,
      has_unlimited_access: true,
    };
  }

  // Regular user from database
  const user = await getUserByEmail(email, env);
  if (!user) {
    throw new Error('User not found');
  }

  return {
    ...user,
    is_admin: false,
    has_unlimited_access: false,
  };
}
```

## Permission Matrix

| Feature | Free Tier | Premium Tier | Admin |
|---------|-----------|--------------|-------|
| Email | 100/day | Unlimited | Unlimited |
| Voice | ❌ | 100 min/mo | Unlimited |
| SMS | ❌ | 100 msg/mo | Unlimited |
| Phone Number | ❌ | 1 number | Configured |
| View All Users | ❌ | ❌ | ✅ |
| Provision Numbers | ❌ | ❌ | ✅ |
| Manage Subscriptions | Own only | Own only | ✅ All |
| Modify Config | ❌ | ❌ | ✅ |

## Migration Checklist

- [x] Update `config.toml` admin section
- [x] Remove `[[users]]` array from config.toml
- [x] Update Rust `config.rs` with `AdminUserConfig`
- [x] Update Rust `config.rs` with enhanced `UserData`
- [x] Add `SubscriptionTiers` to config system
- [x] Create `users.js` for database user management
- [x] Update `database.js` to re-export from `users.js`
- [x] Document database schema in `DATABASE_SCHEMA.md`
- [x] Add helper methods to `ProjectConfig`
- [ ] Create database migration SQL (when Turso is set up)
- [ ] Update authentication middleware to check admin vs regular
- [ ] Update API routes to respect user permissions
- [ ] Add admin-only routes for user management
- [ ] Test admin user configuration loading
- [ ] Test regular user CRUD operations
- [ ] Test permission checks for each tier

## Testing

### Test Admin User Load
```bash
# In Rust code
cargo run --bin test-config
# Should print admin user details from config.toml
```

### Test Regular User Creation
```javascript
// In Node.js server
import { createUser } from './lib/users.js';

const user = await createUser({
  username: 'test_user',
  email: 'test@example.com',
  user_phone: '+15551234567',
  xswarm_email: 'test_user@xswarm.ai',
  subscription_tier: 'free',
  persona: 'boss',
}, env);

console.log('Created user:', user);
```

### Test Permission Checks
```javascript
import { userHasFeature } from './lib/users.js';

// Free user
const freeUser = { subscription_tier: 'free' };
console.assert(!userHasFeature(freeUser, 'voice')); // Should be false
console.assert(userHasFeature(freeUser, 'email'));  // Should be true

// Premium user
const premiumUser = { subscription_tier: 'premium' };
console.assert(userHasFeature(premiumUser, 'voice')); // Should be true
console.assert(userHasFeature(premiumUser, 'sms'));   // Should be true

// Admin user
const adminUser = { subscription_tier: 'admin' };
console.assert(userHasFeature(adminUser, 'voice')); // Should be true (all features)
```

## Backward Compatibility

- `database.js` still exports user functions (via re-export)
- Existing code using `getUserByXswarmPhone()` etc. will continue to work
- New code should use `users.js` directly for clarity

## Next Steps

1. Set up Turso database and create users table
2. Implement authentication middleware that checks admin vs regular users
3. Add admin-only API routes for user management
4. Implement usage tracking for metered billing
5. Add Stripe webhook handlers for subscription changes
6. Create user onboarding flow for new signups

## Questions?

See `DATABASE_SCHEMA.md` for database structure details.
