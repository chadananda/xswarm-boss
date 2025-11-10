# Feature Gating - Quick Reference Card

## Import What You Need

```javascript
// Middleware
import {
  requireFeature,
  requireTier,
  requireAdmin,
  checkUsageLimit,
  softGate
} from '../middleware/tier-gate.js';

// Features library
import {
  hasFeature,
  checkLimit,
  generateUpgradeMessage
} from '../lib/features.js';

// User features
import { userHasFeature } from '../lib/users.js';
```

## Common Patterns

### 1. Block if No Feature Access

```javascript
router.post('/api/call',
  requireAuth(),
  requireFeature('voice_minutes'),
  handleCall
);
```

### 2. Check Usage Limits

```javascript
router.post('/api/call',
  requireAuth(),
  checkUsageLimit('voice_minutes', async (req) => {
    const { getCurrentUsage } = await import('../lib/usage-tracker.js');
    const usage = await getCurrentUsage(req.user.id, req.env);
    return usage.voice_minutes;
  }),
  handleCall
);
```

### 3. Require Minimum Tier

```javascript
router.get('/api/teams',
  requireAuth(),
  requireTier('professional'),
  handleTeams
);
```

### 4. Admin Only

```javascript
router.get('/api/admin/settings',
  requireAuth(),
  requireAdmin(),
  handleAdmin
);
```

### 5. Soft Gate (Show Upgrade CTA)

```javascript
router.get('/api/preview',
  requireAuth(),
  softGate('document_generation'),
  (req, res) => {
    res.json({
      data: { ... },
      upgrade: req.softGateUpgrade
    });
  }
);
```

## Feature Names

| Feature | Free | Personal | Professional | Enterprise |
|---------|------|----------|--------------|------------|
| `voice_minutes` | ✗ | 100/mo | 500/mo | Unlimited |
| `sms_messages` | ✗ | 100/mo | 500/mo | Unlimited |
| `email_daily` | 100 | Unlimited | Unlimited | Unlimited |
| `calendar_access` | read | write | write | write |
| `team_collaboration` | ✗ | ✗ | 10 members | Unlimited |
| `buzz_workspace` | ✗ | ✗ | 50 channels | Unlimited |
| `document_generation` | ✗ | ✓ | ✓ | ✓ |
| `api_access` | ✗ | basic | full | enterprise |

## Tier Names

- `free` - AI Buddy ($0/mo)
- `personal` - AI Secretary ($29/mo)
- `professional` - AI Project Manager ($99/mo)
- `enterprise` - AI CTO ($299/mo)
- `admin` - Admin (all access)

## Check Feature in Code

```javascript
// Simple check
if (userHasFeature(user, 'voice')) {
  // Has voice access
}

// Advanced check with usage
const access = await userHasFeature(user, 'voice_minutes', env);
if (access.allowed) {
  console.log(`Remaining: ${access.remaining}`);
}
```

## API Endpoints

```
GET  /api/tiers                  - List all tiers
GET  /api/tiers/current          - User's current tier
GET  /api/tiers/features         - User's features
GET  /api/tiers/usage            - Usage vs limits
POST /api/tiers/check-access     - Check feature access
POST /api/tiers/check-limit      - Check usage limit
GET  /api/tiers/upgrade-options  - Available upgrades
POST /api/tiers/request-upgrade  - Request upgrade
GET  /api/tiers/compare          - Compare two tiers
```

## Error Codes

- `FEATURE_LOCKED` - Feature not on user's plan
- `LIMIT_REACHED` - Usage limit exceeded
- `TIER_REQUIRED` - Higher tier needed
- `ADMIN_REQUIRED` - Admin access needed
- `RATE_LIMIT_EXCEEDED` - Too many requests

## Overage Rates

- Voice: $0.013/min (Personal), $0.010/min (Professional)
- SMS: $0.0075/msg (Personal), $0.005/msg (Professional)

## Quick Test

```bash
node test-feature-gating.js
```

## Need Help?

See complete docs: `FEATURE_GATING_GUIDE.md`
See examples: `src/routes/example-protected-route.js`
