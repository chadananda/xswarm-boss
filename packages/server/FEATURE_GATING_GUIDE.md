# Feature Gating System - Implementation Guide

Comprehensive tier-based feature access control with automatic upgrade prompts.

## Architecture Overview

The feature gating system consists of three main components:

1. **`lib/features.js`** - Centralized feature definitions and tier matrix
2. **`middleware/tier-gate.js`** - Express middleware for access control
3. **`routes/tiers.js`** - RESTful API for tier management

## Quick Start

### 1. Protect an Endpoint with Feature Gating

```javascript
import { requireFeature } from '../middleware/tier-gate.js';

// Require voice feature
router.post('/api/call', requireFeature('voice_minutes'), async (req, res) => {
  // Only users with voice access can reach here
  // Users without access get 403 with upgrade CTA
});

// Require SMS feature
router.post('/api/sms', requireFeature('sms_messages'), async (req, res) => {
  // Protected SMS endpoint
});
```

### 2. Check Usage Limits

```javascript
import { checkUsageLimit } from '../middleware/tier-gate.js';

// Check voice usage before allowing call
router.post('/api/call',
  requireAuth(),
  checkUsageLimit('voice_minutes', async (req) => {
    const { getCurrentUsage } = await import('../lib/usage-tracker.js');
    const usage = await getCurrentUsage(req.user.id, req.env);
    return usage.voice_minutes;
  }),
  async (req, res) => {
    // Access granted - usage info available in req.usageCheck
    const { remaining, overage, overage_rate } = req.usageCheck;

    // Process call...
  }
);
```

### 3. Require Specific Tier

```javascript
import { requireTier } from '../middleware/tier-gate.js';

// Require Professional tier or higher
router.get('/api/teams', requireTier('professional'), async (req, res) => {
  // Only professional and enterprise users
});
```

### 4. Admin-Only Endpoints

```javascript
import { requireAdmin } from '../middleware/tier-gate.js';

router.get('/api/admin/users', requireAdmin(), async (req, res) => {
  // Admin only
});
```

## Feature Matrix

### Free Tier (AI Buddy)
- 3 personas max
- 0 voice minutes (feature locked)
- 0 SMS messages (feature locked)
- 100 emails/day
- Read-only calendar
- 30-day memory retention
- GPT-3.5-turbo only
- 3 projects max
- 1 GB storage

### Personal Tier (AI Secretary) - $29/mo
- Unlimited personas
- 100 voice minutes/month ($0.013/min overage)
- 100 SMS messages/month ($0.0075/msg overage)
- Unlimited emails
- Full calendar write access
- 1-year memory retention
- GPT-4, Claude 3, Gemini Pro
- Document generation (DOCX, PDF, TXT, MD)
- 25 projects
- 10 GB storage

### Professional Tier (AI Project Manager) - $99/mo
- Everything in Personal
- 500 voice minutes ($0.010/min overage)
- 500 SMS messages ($0.005/msg overage)
- Team collaboration (10 members)
- Buzz workspace (50 channels)
- Advanced AI models
- Full document suite (Word, Excel, PowerPoint)
- 2-year memory retention
- 100 projects
- 100 GB storage

### Enterprise Tier (AI CTO) - $299/mo
- Everything in Professional
- Unlimited voice minutes
- Unlimited SMS messages
- Unlimited team members
- Unlimited Buzz workspace
- Custom AI models
- White-label options
- Dedicated account manager
- 99.9% SLA
- Unlimited projects
- Unlimited storage

## API Endpoints

### GET /api/tiers
List all available subscription tiers (public endpoint)

**Response:**
```json
{
  "success": true,
  "tiers": [
    {
      "tier": "free",
      "name": "AI Buddy",
      "monthly_price": 0,
      "features": [...]
    },
    ...
  ]
}
```

### GET /api/tiers/current
Get current user's tier information

**Response:**
```json
{
  "success": true,
  "tier": {
    "name": "personal",
    "monthly_price": 29,
    "voice_minutes": { "limit": 100, "overage_rate": 0.013 },
    ...
  }
}
```

### GET /api/tiers/features
Get user's available features

**Response:**
```json
{
  "success": true,
  "tier": "personal",
  "features": {
    "voice": true,
    "sms": true,
    "email": true,
    "calendar": "write",
    "personas": { "limit": null },
    ...
  }
}
```

### GET /api/tiers/usage
Get current usage vs limits

**Response:**
```json
{
  "success": true,
  "tier": "personal",
  "usage": {
    "voice_minutes": {
      "used": 75,
      "limit": 100,
      "remaining": 25,
      "overage": 0,
      "overage_cost": 0
    },
    "sms_messages": {
      "used": 120,
      "limit": 100,
      "remaining": 0,
      "overage": 20,
      "overage_cost": 0.15
    }
  },
  "total_overage_cost": 0.15
}
```

### POST /api/tiers/check-access
Check if user has access to a specific feature

**Request:**
```json
{
  "feature": "voice_minutes"
}
```

**Response (has access):**
```json
{
  "success": true,
  "has_access": true,
  "feature": "voice_minutes",
  "tier": "personal"
}
```

**Response (no access):**
```json
{
  "success": true,
  "has_access": false,
  "feature": "voice_minutes",
  "tier": "free",
  "upgrade": {
    "message": "Voice Minutes is available on the AI Secretary plan and higher.",
    "cta": {
      "text": "Upgrade to AI Secretary",
      "tier": "personal",
      "price": "$29/month"
    },
    "upgrade_options": [...]
  }
}
```

### POST /api/tiers/check-limit
Check usage limit for a feature

**Request:**
```json
{
  "feature": "voice_minutes",
  "amount": 10
}
```

**Response:**
```json
{
  "success": true,
  "feature": "voice_minutes",
  "tier": "personal",
  "current_usage": 75,
  "projected_usage": 85,
  "limit": 100,
  "remaining": 15,
  "allowed": true,
  "would_overage": false,
  "overage_amount": 0,
  "overage_cost": 0
}
```

### GET /api/tiers/upgrade-options
Get available upgrade paths

**Response:**
```json
{
  "success": true,
  "current_tier": "free",
  "next_tier": {
    "tier": "personal",
    "name": "AI Secretary",
    "monthly_price": 29,
    ...
  },
  "upgrade_options": [...]
}
```

### GET /api/tiers/compare?from=free&to=personal
Compare two tiers

**Response:**
```json
{
  "success": true,
  "comparison": {
    "tier_change": { "from": "free", "to": "personal" },
    "price_change": { "monthly": 29, "annual": 290 },
    "new_features": ["voice_minutes", "sms_messages"],
    "improved_limits": [
      { "feature": "personas", "from": 3, "to": "unlimited" },
      { "feature": "email_daily", "from": 100, "to": "unlimited" }
    ]
  },
  "from_tier": {...},
  "to_tier": {...}
}
```

### POST /api/tiers/request-upgrade
Request upgrade to a specific tier

**Request:**
```json
{
  "target_tier": "personal",
  "billing_period": "monthly"
}
```

**Response:**
```json
{
  "success": true,
  "upgrade": {
    "from_tier": "free",
    "to_tier": "personal",
    "billing_period": "monthly",
    "price": 29,
    "next_step": "checkout",
    "checkout_url": "/checkout/personal?period=monthly"
  }
}
```

## Middleware Functions

### `requireFeature(feature)`
Blocks access if user doesn't have feature. Returns 403 with upgrade CTA.

### `requireTier(minTier)`
Requires minimum tier level. Returns 403 if user tier is lower.

### `checkUsageLimit(feature, getUsage)`
Checks usage limits before allowing action. Blocks if limit exceeded (unless overages allowed).

### `requireAdmin()`
Admin-only access. Returns 403 for non-admin users.

### `attachTierInfo()`
Attaches tier info to `req.tierInfo` without gating access.

### `tierBasedRateLimit(tierLimits, windowMs)`
Rate limiting based on tier. Higher tiers get higher limits.

### `softGate(feature)`
Allows access but attaches upgrade CTA to `req.softGateUpgrade` if user lacks feature.

### `requireAllFeatures(features)`
User must have ALL specified features.

### `requireAnyFeature(features)`
User must have at least ONE of the specified features.

## Usage Examples

### Protecting Multiple Features

```javascript
import { requireAllFeatures } from '../middleware/tier-gate.js';

router.post('/api/team-call',
  requireAllFeatures(['voice_minutes', 'team_collaboration']),
  async (req, res) => {
    // Requires both voice and teams
  }
);
```

### Tier-Based Rate Limiting

```javascript
import { tierBasedRateLimit } from '../middleware/tier-gate.js';

router.use('/api', tierBasedRateLimit({
  free: 10,        // 10 requests per minute
  personal: 60,    // 60 requests per minute
  professional: 300,
  enterprise: 1000
}, 60000)); // 1 minute window
```

### Soft Gating (Freemium)

```javascript
import { softGate } from '../middleware/tier-gate.js';

router.get('/api/preview-feature', softGate('document_generation'), async (req, res) => {
  // Everyone can access, but free users see upgrade prompt
  const upgrade = req.softGateUpgrade;

  res.json({
    data: {...},
    upgrade: upgrade || null
  });
});
```

### Check Feature in Code

```javascript
import { userHasFeature } from '../lib/users.js';

// Simple check
if (userHasFeature(user, 'voice')) {
  // Allow voice access
}

// Advanced check with usage limits
const access = await userHasFeature(user, 'voice_minutes', env);
if (access.allowed) {
  console.log(`Remaining: ${access.remaining} minutes`);
}
```

## Error Responses

### Feature Locked (403)
```json
{
  "error": "Feature not available on your plan",
  "code": "FEATURE_LOCKED",
  "feature": "voice_minutes",
  "current_tier": "free",
  "upgrade": {
    "message": "Voice Minutes is available on the AI Secretary plan and higher.",
    "cta": {
      "text": "Upgrade to AI Secretary",
      "tier": "personal",
      "price": "$29/month"
    }
  }
}
```

### Limit Reached (403)
```json
{
  "error": "You've reached your limit for voice minutes",
  "code": "LIMIT_REACHED",
  "feature": "voice_minutes",
  "usage": {
    "current": 100,
    "limit": 100,
    "remaining": 0
  },
  "upgrade": {...}
}
```

### Rate Limit Exceeded (429)
```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "limit": 10,
  "reset_in_seconds": 45,
  "upgrade": {...}
}
```

## Integration Steps

### 1. Add Tiers Routes to Express App

```javascript
// In src/index.js or main router
import tiersRouter from './routes/tiers.js';

app.use('/api/tiers', tiersRouter);
```

### 2. Protect Existing Endpoints

```javascript
// Before:
router.post('/api/call', requireAuth(), handleCall);

// After:
import { requireFeature, checkUsageLimit } from './middleware/tier-gate.js';

router.post('/api/call',
  requireAuth(),
  requireFeature('voice_minutes'),
  checkUsageLimit('voice_minutes', getVoiceUsage),
  handleCall
);
```

### 3. Update Frontend to Show Upgrade CTAs

```javascript
// Handle 403 responses
try {
  const response = await fetch('/api/call', { method: 'POST' });
  const data = await response.json();

  if (response.status === 403 && data.upgrade) {
    // Show upgrade modal
    showUpgradeModal(data.upgrade);
  }
} catch (error) {
  // Handle error
}
```

## Testing

### Test Feature Access

```javascript
import { hasFeature, checkLimit } from './lib/features.js';

// Check if tier has feature
console.log(hasFeature('free', 'voice_minutes')); // false
console.log(hasFeature('personal', 'voice_minutes')); // true

// Check usage limits
const limit = checkLimit('personal', 'voice_minutes', 75);
console.log(limit);
// { allowed: true, limit: 100, remaining: 25, overage: 0 }
```

### Test Middleware

```javascript
// Mock request/response
const mockReq = {
  user: { id: 'user123', subscription_tier: 'free' }
};
const mockRes = {
  status: (code) => ({ json: (data) => console.log(code, data) })
};

const middleware = requireFeature('voice_minutes');
middleware(mockReq, mockRes, () => console.log('Access granted'));
// Outputs: 403 { error: '...', upgrade: {...} }
```

## Best Practices

1. **Always use feature names from TIER_FEATURES** - Don't hardcode feature checks
2. **Check usage limits for metered features** - Use `checkUsageLimit` middleware
3. **Provide clear upgrade CTAs** - The system auto-generates these
4. **Log feature access attempts** - For analytics and fraud detection
5. **Test all tier combinations** - Ensure proper access control
6. **Handle overages gracefully** - Some features allow overages with billing

## Performance Considerations

- Feature checks are cached per request via middleware
- Usage data is fetched once per request and reused
- Tier info is attached to user object (minimal overhead)
- Rate limiting uses in-memory Map (consider Redis for production)

## Security Notes

- Always validate tier changes server-side
- Never trust client-side tier information
- Log all tier changes for audit trail
- Implement webhook verification for Stripe events
- Use JWT version to invalidate sessions on tier changes

---

**Implementation Status:** ✅ Complete and ready for integration

**Files Created:**
- `/packages/server/src/lib/features.js` - Feature definitions
- `/packages/server/src/middleware/tier-gate.js` - Access control middleware
- `/packages/server/src/routes/tiers.js` - RESTful tier API
- `/packages/server/src/lib/users.js` - Enhanced userHasFeature()

**Next Steps:**
1. Integrate tiers router into main Express app
2. Add middleware to existing protected routes
3. Test with real Stripe subscriptions
4. Build frontend upgrade flow
5. Add usage tracking to all metered features
