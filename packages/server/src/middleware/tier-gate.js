/**
 * Tier Gating Middleware
 *
 * Express middleware for feature-based access control.
 * Elegant, functional implementation with automatic upgrade CTAs.
 */

import { hasFeature, generateUpgradeMessage, TIER_FEATURES } from '../lib/features.js';

/**
 * Require specific feature access
 * Returns 403 with upgrade info if user doesn't have access
 *
 * @param {string} feature - Feature name to check
 * @returns {Function} Express middleware
 */
export function requireFeature(feature) {
  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const tier = user.subscription_tier || 'free';
    const hasAccess = hasFeature(tier, feature);

    if (!hasAccess) {
      const upgradeInfo = generateUpgradeMessage(feature, tier);

      return res.status(403).json({
        error: 'Feature not available on your plan',
        code: 'FEATURE_LOCKED',
        feature,
        current_tier: tier,
        upgrade: upgradeInfo
      });
    }

    next();
  };
}

/**
 * Require specific subscription tier (or higher)
 *
 * @param {string} minTier - Minimum required tier
 * @returns {Function} Express middleware
 */
export function requireTier(minTier) {
  const tierOrder = ['free', 'personal', 'professional', 'enterprise', 'admin'];
  const minIndex = tierOrder.indexOf(minTier);

  if (minIndex === -1) {
    throw new Error(`Invalid tier: ${minTier}`);
  }

  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const currentTier = user.subscription_tier || 'free';
    const currentIndex = tierOrder.indexOf(currentTier);

    if (currentIndex < minIndex) {
      const targetTierConfig = TIER_FEATURES[minTier];

      return res.status(403).json({
        error: `This feature requires ${targetTierConfig.name} or higher`,
        code: 'TIER_REQUIRED',
        current_tier: currentTier,
        required_tier: minTier,
        upgrade: {
          message: `Upgrade to ${targetTierConfig.name} to access this feature`,
          cta: {
            text: `Upgrade to ${targetTierConfig.name}`,
            tier: minTier,
            price: targetTierConfig.monthly_price > 0
              ? `$${targetTierConfig.monthly_price}/month`
              : 'Free'
          }
        }
      });
    }

    next();
  };
}

/**
 * Check usage limits before allowing action
 * Attaches usage info to req.usageCheck for later processing
 *
 * @param {string} feature - Feature to check (voice_minutes, sms_messages, etc.)
 * @param {Function} getUsage - Async function to get current usage (receives req)
 * @returns {Function} Express middleware
 */
export function checkUsageLimit(feature, getUsage) {
  return async (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    try {
      // Import features lib
      const { checkLimit } = await import('../lib/features.js');

      // Get current usage
      const currentUsage = await getUsage(req);
      const tier = user.subscription_tier || 'free';

      // Check limit
      const limitCheck = checkLimit(tier, feature, currentUsage);

      if (!limitCheck.allowed) {
        const upgradeInfo = generateUpgradeMessage(feature, tier);

        return res.status(403).json({
          error: `You've reached your limit for ${feature.replace(/_/g, ' ')}`,
          code: 'LIMIT_REACHED',
          feature,
          usage: {
            current: currentUsage,
            limit: limitCheck.limit,
            remaining: limitCheck.remaining
          },
          upgrade: upgradeInfo
        });
      }

      // Attach usage info for later use
      req.usageCheck = {
        feature,
        tier,
        usage: currentUsage,
        limit: limitCheck.limit,
        remaining: limitCheck.remaining,
        overage: limitCheck.overage,
        overage_allowed: limitCheck.overage_allowed,
        overage_rate: limitCheck.overage_rate
      };

      next();
    } catch (error) {
      console.error('Error checking usage limit:', error);
      return res.status(500).json({
        error: 'Failed to check usage limits',
        code: 'LIMIT_CHECK_FAILED'
      });
    }
  };
}

/**
 * Admin-only middleware
 * Requires admin tier or specific admin flag
 */
export function requireAdmin() {
  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const isAdmin = user.subscription_tier === 'admin' || user.is_admin === true;

    if (!isAdmin) {
      return res.status(403).json({
        error: 'Admin access required',
        code: 'ADMIN_REQUIRED'
      });
    }

    next();
  };
}

/**
 * Attach tier info to request
 * Useful for endpoints that need tier info but don't gate access
 */
export function attachTierInfo() {
  return (req, res, next) => {
    const user = req.user;

    if (user) {
      const tier = user.subscription_tier || 'free';
      req.tierInfo = TIER_FEATURES[tier];
    }

    next();
  };
}

/**
 * Rate limit based on tier
 * Higher tiers get higher rate limits
 *
 * @param {Object} tierLimits - Object mapping tier to request limit per window
 * @param {number} windowMs - Time window in milliseconds
 * @returns {Function} Express middleware
 */
export function tierBasedRateLimit(tierLimits, windowMs = 60000) {
  const requests = new Map(); // userId -> [timestamps]

  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const tier = user.subscription_tier || 'free';
    const limit = tierLimits[tier] || tierLimits.free || 10;
    const now = Date.now();
    const windowStart = now - windowMs;

    // Get user's request history
    let userRequests = requests.get(user.id) || [];

    // Filter to current window
    userRequests = userRequests.filter(timestamp => timestamp > windowStart);

    if (userRequests.length >= limit) {
      const oldestRequest = Math.min(...userRequests);
      const resetIn = Math.ceil((oldestRequest + windowMs - now) / 1000);

      return res.status(429).json({
        error: 'Rate limit exceeded',
        code: 'RATE_LIMIT_EXCEEDED',
        limit,
        reset_in_seconds: resetIn,
        upgrade: generateUpgradeMessage('api_access', tier)
      });
    }

    // Add current request
    userRequests.push(now);
    requests.set(user.id, userRequests);

    // Attach rate limit headers
    res.setHeader('X-RateLimit-Limit', limit);
    res.setHeader('X-RateLimit-Remaining', limit - userRequests.length);
    res.setHeader('X-RateLimit-Reset', Math.ceil((windowStart + windowMs) / 1000));

    next();
  };
}

/**
 * Soft gate - allows access but includes upgrade CTA in response
 * Useful for freemium features where you want to show what's possible
 *
 * @param {string} feature - Feature name
 * @returns {Function} Express middleware
 */
export function softGate(feature) {
  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return next();
    }

    const tier = user.subscription_tier || 'free';
    const hasAccess = hasFeature(tier, feature);

    if (!hasAccess) {
      const upgradeInfo = generateUpgradeMessage(feature, tier);
      req.softGateUpgrade = upgradeInfo;
    }

    next();
  };
}

/**
 * Combined middleware: check multiple features (user must have ALL)
 *
 * @param {Array<string>} features - Array of feature names
 * @returns {Function} Express middleware
 */
export function requireAllFeatures(features) {
  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const tier = user.subscription_tier || 'free';
    const missingFeatures = features.filter(f => !hasFeature(tier, f));

    if (missingFeatures.length > 0) {
      const upgradeInfos = missingFeatures.map(f => generateUpgradeMessage(f, tier));

      return res.status(403).json({
        error: 'Multiple features required',
        code: 'FEATURES_LOCKED',
        missing_features: missingFeatures,
        current_tier: tier,
        upgrades: upgradeInfos
      });
    }

    next();
  };
}

/**
 * Combined middleware: check multiple features (user needs ANY one)
 *
 * @param {Array<string>} features - Array of feature names
 * @returns {Function} Express middleware
 */
export function requireAnyFeature(features) {
  return (req, res, next) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const tier = user.subscription_tier || 'free';
    const hasAny = features.some(f => hasFeature(tier, f));

    if (!hasAny) {
      const upgradeInfos = features.map(f => generateUpgradeMessage(f, tier));

      return res.status(403).json({
        error: 'At least one of these features is required',
        code: 'FEATURES_LOCKED',
        required_features: features,
        current_tier: tier,
        upgrades: upgradeInfos
      });
    }

    next();
  };
}
