/**
 * Tiers API Routes
 *
 * RESTful API for tier management, feature checking, and upgrade flows.
 * Provides comprehensive tier information and usage tracking.
 */

import { Router } from 'express';
import {
  TIER_FEATURES,
  hasFeature,
  checkLimit,
  compareTiers,
  getNextTier,
  getAllTiers,
  generateUpgradeMessage,
  calculateOverageCost
} from '../lib/features.js';
import { requireAuth } from '../lib/auth-middleware.js';
import { getCurrentUsage } from '../lib/usage-tracker.js';

const router = Router();

/**
 * GET /api/tiers
 * List all available subscription tiers (public)
 */
router.get('/', (req, res) => {
  try {
    const tiers = getAllTiers();

    res.json({
      success: true,
      tiers
    });
  } catch (error) {
    console.error('Error fetching tiers:', error);
    res.status(500).json({
      error: 'Failed to fetch tiers',
      code: 'FETCH_FAILED'
    });
  }
});

/**
 * GET /api/tiers/current
 * Get current user's tier information
 */
router.get('/current', requireAuth(), (req, res) => {
  try {
    const user = req.user;
    const tier = user.subscription_tier || 'free';
    const tierConfig = TIER_FEATURES[tier];

    if (!tierConfig) {
      return res.status(404).json({
        error: 'Tier not found',
        code: 'TIER_NOT_FOUND'
      });
    }

    res.json({
      success: true,
      tier: {
        name: tier,
        ...tierConfig
      }
    });
  } catch (error) {
    console.error('Error fetching current tier:', error);
    res.status(500).json({
      error: 'Failed to fetch tier information',
      code: 'FETCH_FAILED'
    });
  }
});

/**
 * GET /api/tiers/features
 * Get user's available features
 */
router.get('/features', requireAuth(), (req, res) => {
  try {
    const user = req.user;
    const tier = user.subscription_tier || 'free';
    const tierConfig = TIER_FEATURES[tier];

    if (!tierConfig) {
      return res.status(404).json({
        error: 'Tier not found',
        code: 'TIER_NOT_FOUND'
      });
    }

    // Build feature access map
    const features = {
      voice: hasFeature(tier, 'voice_minutes'),
      sms: hasFeature(tier, 'sms_messages'),
      email: hasFeature(tier, 'email_daily'),
      calendar: tierConfig.calendar_access,
      personas: tierConfig.personas,
      ai_models: tierConfig.ai_models,
      document_generation: tierConfig.document_generation,
      team_collaboration: tierConfig.team_collaboration,
      buzz_workspace: tierConfig.buzz_workspace,
      api_access: tierConfig.api_access,
      priority_support: tierConfig.priority_support
    };

    res.json({
      success: true,
      tier,
      features
    });
  } catch (error) {
    console.error('Error fetching features:', error);
    res.status(500).json({
      error: 'Failed to fetch features',
      code: 'FETCH_FAILED'
    });
  }
});

/**
 * GET /api/tiers/usage
 * Get current usage vs limits
 */
router.get('/usage', requireAuth(), async (req, res) => {
  try {
    const user = req.user;
    const tier = user.subscription_tier || 'free';

    // Get usage from usage tracker
    const usage = await getCurrentUsage(user.id, req.env);

    // Calculate costs if any overages
    const voiceOverageCost = calculateOverageCost(tier, 'voice_minutes', usage.overages?.voice_minutes || 0);
    const smsOverageCost = calculateOverageCost(tier, 'sms_messages', usage.overages?.sms_messages || 0);

    res.json({
      success: true,
      tier,
      usage: {
        voice_minutes: {
          used: usage.voice_minutes,
          limit: usage.limits.voice_minutes,
          remaining: usage.limits.voice_minutes === -1
            ? null
            : Math.max(0, usage.limits.voice_minutes - usage.voice_minutes),
          overage: usage.overages?.voice_minutes || 0,
          overage_cost: voiceOverageCost
        },
        sms_messages: {
          used: usage.sms_messages,
          limit: usage.limits.sms_messages,
          remaining: usage.limits.sms_messages === -1
            ? null
            : Math.max(0, usage.limits.sms_messages - usage.sms_messages),
          overage: usage.overages?.sms_messages || 0,
          overage_cost: smsOverageCost
        },
        email_count: {
          used: usage.email_count,
          limit: usage.limits.email_limit,
          remaining: usage.limits.email_limit === -1
            ? null
            : Math.max(0, usage.limits.email_limit - usage.email_count)
        }
      },
      total_overage_cost: voiceOverageCost + smsOverageCost,
      period: {
        start: usage.period_start,
        end: usage.period_end
      }
    });
  } catch (error) {
    console.error('Error fetching usage:', error);
    res.status(500).json({
      error: 'Failed to fetch usage information',
      code: 'FETCH_FAILED'
    });
  }
});

/**
 * POST /api/tiers/check-access
 * Check if user has access to a specific feature
 */
router.post('/check-access', requireAuth(), (req, res) => {
  try {
    const user = req.user;
    const { feature } = req.body;

    if (!feature) {
      return res.status(400).json({
        error: 'Feature name required',
        code: 'FEATURE_REQUIRED'
      });
    }

    const tier = user.subscription_tier || 'free';
    const hasAccess = hasFeature(tier, feature);

    if (!hasAccess) {
      const upgradeInfo = generateUpgradeMessage(feature, tier);

      return res.json({
        success: true,
        has_access: false,
        feature,
        tier,
        upgrade: upgradeInfo
      });
    }

    res.json({
      success: true,
      has_access: true,
      feature,
      tier
    });
  } catch (error) {
    console.error('Error checking feature access:', error);
    res.status(500).json({
      error: 'Failed to check feature access',
      code: 'CHECK_FAILED'
    });
  }
});

/**
 * POST /api/tiers/check-limit
 * Check usage limit for a feature
 */
router.post('/check-limit', requireAuth(), async (req, res) => {
  try {
    const user = req.user;
    const { feature, amount = 1 } = req.body;

    if (!feature) {
      return res.status(400).json({
        error: 'Feature name required',
        code: 'FEATURE_REQUIRED'
      });
    }

    const tier = user.subscription_tier || 'free';

    // Get current usage
    const usage = await getCurrentUsage(user.id, req.env);

    // Map feature to usage field
    const featureMap = {
      voice_minutes: usage.voice_minutes,
      sms_messages: usage.sms_messages,
      email_daily: usage.email_count
    };

    const currentUsage = featureMap[feature] || 0;
    const projectedUsage = currentUsage + amount;

    // Check limit
    const limitCheck = checkLimit(tier, feature, projectedUsage);

    res.json({
      success: true,
      feature,
      tier,
      current_usage: currentUsage,
      projected_usage: projectedUsage,
      limit: limitCheck.limit,
      remaining: limitCheck.remaining,
      allowed: limitCheck.allowed,
      would_overage: limitCheck.overage > 0,
      overage_amount: limitCheck.overage,
      overage_cost: calculateOverageCost(tier, feature, limitCheck.overage),
      upgrade: !limitCheck.allowed ? generateUpgradeMessage(feature, tier) : null
    });
  } catch (error) {
    console.error('Error checking limit:', error);
    res.status(500).json({
      error: 'Failed to check limit',
      code: 'CHECK_FAILED'
    });
  }
});

/**
 * GET /api/tiers/upgrade-options
 * Get available upgrade paths for current user
 */
router.get('/upgrade-options', requireAuth(), (req, res) => {
  try {
    const user = req.user;
    const currentTier = user.subscription_tier || 'free';

    const nextTier = getNextTier(currentTier);

    if (!nextTier) {
      return res.json({
        success: true,
        message: 'You are on the highest tier',
        current_tier: currentTier,
        upgrade_options: []
      });
    }

    // Get all higher tiers
    const tierOrder = ['free', 'personal', 'professional', 'enterprise'];
    const currentIndex = tierOrder.indexOf(currentTier);

    const upgradeOptions = tierOrder
      .slice(currentIndex + 1)
      .map(tier => ({
        tier,
        ...TIER_FEATURES[tier],
        comparison: compareTiers(currentTier, tier)
      }));

    res.json({
      success: true,
      current_tier: currentTier,
      next_tier: nextTier,
      upgrade_options: upgradeOptions
    });
  } catch (error) {
    console.error('Error fetching upgrade options:', error);
    res.status(500).json({
      error: 'Failed to fetch upgrade options',
      code: 'FETCH_FAILED'
    });
  }
});

/**
 * GET /api/tiers/compare
 * Compare two tiers
 */
router.get('/compare', requireAuth(), (req, res) => {
  try {
    const { from, to } = req.query;

    if (!from || !to) {
      return res.status(400).json({
        error: 'Both from and to tiers required',
        code: 'TIERS_REQUIRED'
      });
    }

    if (!TIER_FEATURES[from] || !TIER_FEATURES[to]) {
      return res.status(404).json({
        error: 'Invalid tier specified',
        code: 'INVALID_TIER'
      });
    }

    const comparison = compareTiers(from, to);

    res.json({
      success: true,
      comparison,
      from_tier: { tier: from, ...TIER_FEATURES[from] },
      to_tier: { tier: to, ...TIER_FEATURES[to] }
    });
  } catch (error) {
    console.error('Error comparing tiers:', error);
    res.status(500).json({
      error: 'Failed to compare tiers',
      code: 'COMPARE_FAILED'
    });
  }
});

/**
 * POST /api/tiers/request-upgrade
 * Request upgrade to a specific tier (creates Stripe checkout or contact request)
 */
router.post('/request-upgrade', requireAuth(), async (req, res) => {
  try {
    const user = req.user;
    const { target_tier, billing_period = 'monthly' } = req.body;

    if (!target_tier) {
      return res.status(400).json({
        error: 'Target tier required',
        code: 'TIER_REQUIRED'
      });
    }

    const tierConfig = TIER_FEATURES[target_tier];

    if (!tierConfig) {
      return res.status(404).json({
        error: 'Invalid tier',
        code: 'INVALID_TIER'
      });
    }

    const currentTier = user.subscription_tier || 'free';

    // For enterprise tier, return contact info instead of checkout
    if (target_tier === 'enterprise') {
      return res.json({
        success: true,
        requires_contact: true,
        message: 'Enterprise plans require a custom quote. Our team will contact you shortly.',
        contact_email: 'enterprise@xswarm.ai'
      });
    }

    // For other tiers, return Stripe checkout info
    // (This would integrate with Stripe in production)
    const price = billing_period === 'annual'
      ? tierConfig.annual_price
      : tierConfig.monthly_price;

    res.json({
      success: true,
      upgrade: {
        from_tier: currentTier,
        to_tier: target_tier,
        billing_period,
        price,
        next_step: 'checkout',
        checkout_url: `/checkout/${target_tier}?period=${billing_period}` // Placeholder
      }
    });
  } catch (error) {
    console.error('Error requesting upgrade:', error);
    res.status(500).json({
      error: 'Failed to process upgrade request',
      code: 'UPGRADE_FAILED'
    });
  }
});

export default router;
