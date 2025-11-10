# Tier Migration Quick Reference

## Quick Commands

```bash
# Test the migration logic (no database needed)
node scripts/test-tier-migration.js

# Preview database changes (dry-run)
node scripts/migrate-tier-names.js --dry-run

# Apply migration
node scripts/migrate-tier-names.js

# Rollback if needed
node scripts/migrate-tier-names.js --rollback
```

## Tier Names

| Old (Legacy)        | New (Standard) |
|--------------------|----------------|
| ai_buddy           | free           |
| ai_secretary       | personal       |
| ai_project_manager | professional   |
| ai_cto             | enterprise     |
| admin              | admin          |

## Code Examples

### Usage Tracker
```javascript
// OLD
const limits = getSubscriptionLimits('ai_secretary');

// NEW
const limits = getSubscriptionLimits('personal');
```

### Team Permissions
```javascript
// OLD
const proTiers = ['ai_project_manager', 'ai_cto', 'admin'];

// NEW
const proTiers = ['professional', 'enterprise', 'admin'];
```

### User Features
```javascript
// OLD (still works, backward compatible)
if (user.subscription_tier === 'ai_buddy') { ... }

// NEW (preferred)
if (user.subscription_tier === 'free') { ... }
```

## Migration Workflow

1. **Run Tests First**
   ```bash
   node scripts/test-tier-migration.js
   ```
   Expected: All 31 tests pass

2. **Preview Migration**
   ```bash
   node scripts/migrate-tier-names.js --dry-run
   ```
   Review output carefully

3. **Apply Migration**
   ```bash
   node scripts/migrate-tier-names.js
   ```
   This updates the database

4. **Verify Results**
   ```bash
   # Check users
   SELECT subscription_tier, COUNT(*) FROM users GROUP BY subscription_tier;

   # Check teams
   SELECT subscription_tier, COUNT(*) FROM teams GROUP BY subscription_tier;
   ```

## Rollback

If something goes wrong:
```bash
node scripts/migrate-tier-names.js --rollback
```

This reverts all tier names to legacy format.

## Feature Matrix

```
Feature              Free  Personal  Professional  Enterprise
------------------------------------------------------------------
Email                ✅    ✅        ✅            ✅
Voice (100 min)      ❌    ✅        ✅            ✅
SMS (100 msg)        ❌    ✅        ✅            ✅
Voice (500 min)      ❌    ❌        ✅            ✅
SMS (500 msg)        ❌    ❌        ✅            ✅
Teams                ❌    ❌        ✅            ✅
Buzz                 ❌    ❌        ✅            ✅
Unlimited Voice      ❌    ❌        ❌            ✅
Unlimited SMS        ❌    ❌        ❌            ✅
Unlimited Teams      ❌    ❌        ❌            ✅
```

## Troubleshooting

### "Migration failed: SERVER_ERROR"
- Check `.env` file exists in project root
- Verify `TURSO_DATABASE_URL` is set
- Verify `TURSO_AUTH_TOKEN` is set
- Ensure database is accessible

### "No users found"
- Database might be empty
- Check database connection
- Verify you're connected to correct database

### "Some tests failed"
- This indicates a logic error
- Do NOT run migration
- Review code changes
- Contact development team

## Files Changed

### JavaScript
- `packages/server/src/lib/usage-tracker.js` - Tier limits
- `packages/server/src/lib/team-permissions.js` - Team access
- `packages/server/src/lib/users.js` - Feature checking
- `packages/server/src/lib/teams-db.js` - Team creation

### Scripts
- `scripts/migrate-tier-names.js` - Migration tool
- `scripts/test-tier-migration.js` - Test suite

## Need Help?

1. Run tests: `node scripts/test-tier-migration.js`
2. Check documentation: `TIER_NAMING_MIGRATION.md`
3. Review code changes in files above
4. Contact development team
