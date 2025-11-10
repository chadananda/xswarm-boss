/**
 * Example Protected Route
 *
 * Demonstrates how to use the feature gating system to protect endpoints.
 * This is a reference implementation - adapt for your actual routes.
 */

import { Router } from 'express';
import { requireAuth } from '../lib/auth-middleware.js';
import {
  requireFeature,
  requireTier,
  checkUsageLimit,
  requireAllFeatures,
  tierBasedRateLimit,
  softGate
} from '../middleware/tier-gate.js';

const router = Router();

/**
 * EXAMPLE 1: Simple Feature Gating
 * Blocks users without voice feature
 */
router.post('/voice/call',
  requireAuth(),
  requireFeature('voice_minutes'),
  async (req, res) => {
    // Only users with voice access can reach here
    res.json({
      success: true,
      message: 'Voice call initiated'
    });
  }
);

/**
 * EXAMPLE 2: Usage Limit Checking
 * Checks if user has remaining voice minutes before allowing call
 */
router.post('/voice/call-with-limit',
  requireAuth(),
  requireFeature('voice_minutes'),
  checkUsageLimit('voice_minutes', async (req) => {
    // Get current usage for this user
    const { getCurrentUsage } = await import('../lib/usage-tracker.js');
    const usage = await getCurrentUsage(req.user.id, req.env);
    return usage.voice_minutes;
  }),
  async (req, res) => {
    // Access granted - usage info available in req.usageCheck
    const { usage, limit, remaining, overage, overage_rate } = req.usageCheck;

    // Track the call (this would be done after call completes)
    // await trackVoiceUsage(req.user.id, callDuration, req.env);

    res.json({
      success: true,
      message: 'Voice call initiated',
      usage_info: {
        current_usage: usage,
        limit: limit === null ? 'unlimited' : limit,
        remaining: remaining === null ? 'unlimited' : remaining,
        will_incur_overage: overage > 0,
        overage_rate: overage_rate
      }
    });
  }
);

/**
 * EXAMPLE 3: Tier-Based Access
 * Requires at least Professional tier
 */
router.get('/teams',
  requireAuth(),
  requireTier('professional'),
  async (req, res) => {
    // Only professional and enterprise users
    res.json({
      success: true,
      teams: [
        { id: 1, name: 'Development Team' },
        { id: 2, name: 'Marketing Team' }
      ]
    });
  }
);

/**
 * EXAMPLE 4: Multiple Feature Requirements
 * User must have BOTH voice and team collaboration
 */
router.post('/team-call',
  requireAuth(),
  requireAllFeatures(['voice_minutes', 'team_collaboration']),
  async (req, res) => {
    res.json({
      success: true,
      message: 'Team call initiated'
    });
  }
);

/**
 * EXAMPLE 5: Tier-Based Rate Limiting
 * Higher tiers get higher rate limits
 */
router.use('/api',
  requireAuth(),
  tierBasedRateLimit({
    free: 10,        // 10 requests per minute
    personal: 60,    // 60 requests per minute
    professional: 300,
    enterprise: 1000
  }, 60000) // 1 minute window
);

/**
 * EXAMPLE 6: Soft Gating (Freemium Pattern)
 * Everyone can access, but free users see upgrade prompt in response
 */
router.get('/document-preview',
  requireAuth(),
  softGate('document_generation'),
  async (req, res) => {
    // Everyone can access, but we include upgrade CTA for free users
    const documentPreview = {
      title: 'Q4 Report',
      preview: 'Lorem ipsum dolor sit amet...',
      page_count: 15
    };

    res.json({
      success: true,
      data: documentPreview,
      upgrade: req.softGateUpgrade || null // Upgrade CTA if user lacks feature
    });
  }
);

/**
 * EXAMPLE 7: Programmatic Feature Check
 * Check feature access in code without middleware
 */
router.post('/flexible-endpoint',
  requireAuth(),
  async (req, res) => {
    const { userHasFeature } = await import('../lib/users.js');

    // Simple sync check
    const hasVoice = userHasFeature(req.user, 'voice');

    if (!hasVoice) {
      return res.status(403).json({
        error: 'Voice feature required',
        code: 'FEATURE_REQUIRED'
      });
    }

    // Or async check with usage limits
    const voiceAccess = await userHasFeature(req.user, 'voice_minutes', req.env);

    if (typeof voiceAccess === 'object' && !voiceAccess.allowed) {
      return res.status(403).json({
        error: 'Voice minutes limit reached',
        usage: voiceAccess
      });
    }

    res.json({
      success: true,
      voice_status: voiceAccess
    });
  }
);

/**
 * EXAMPLE 8: Dynamic Feature Checking
 * Check different features based on request
 */
router.post('/send-notification',
  requireAuth(),
  async (req, res) => {
    const { channel } = req.body; // 'voice', 'sms', 'email'

    // Map channels to features
    const featureMap = {
      voice: 'voice_minutes',
      sms: 'sms_messages',
      email: 'email_daily'
    };

    const requiredFeature = featureMap[channel];

    if (!requiredFeature) {
      return res.status(400).json({
        error: 'Invalid channel',
        code: 'INVALID_CHANNEL'
      });
    }

    // Check feature access dynamically
    const { hasFeature } = await import('../lib/features.js');
    const tier = req.user.subscription_tier || 'free';

    if (!hasFeature(tier, requiredFeature)) {
      const { generateUpgradeMessage } = await import('../lib/features.js');
      const upgrade = generateUpgradeMessage(requiredFeature, tier);

      return res.status(403).json({
        error: `${channel} notifications not available on your plan`,
        code: 'FEATURE_LOCKED',
        upgrade
      });
    }

    // Send notification...
    res.json({
      success: true,
      message: `Notification sent via ${channel}`
    });
  }
);

/**
 * EXAMPLE 9: Usage Tracking After Action
 * Track usage after successful operation
 */
router.post('/send-sms',
  requireAuth(),
  requireFeature('sms_messages'),
  checkUsageLimit('sms_messages', async (req) => {
    const { getCurrentUsage } = await import('../lib/usage-tracker.js');
    const usage = await getCurrentUsage(req.user.id, req.env);
    return usage.sms_messages;
  }),
  async (req, res) => {
    const { to, message } = req.body;

    // Send SMS...
    const smsSent = true; // Placeholder

    if (smsSent) {
      // Track usage after successful send
      const { trackSMSUsage } = await import('../lib/usage-tracker.js');
      await trackSMSUsage(req.user.id, 1, req.env);

      res.json({
        success: true,
        message: 'SMS sent',
        usage: req.usageCheck
      });
    } else {
      res.status(500).json({
        error: 'Failed to send SMS'
      });
    }
  }
);

/**
 * EXAMPLE 10: Complex Conditional Access
 * Different behavior based on tier
 */
router.get('/dashboard',
  requireAuth(),
  async (req, res) => {
    const tier = req.user.subscription_tier || 'free';
    const { TIER_FEATURES } = await import('../lib/features.js');

    const tierConfig = TIER_FEATURES[tier];

    // Customize response based on tier
    const dashboard = {
      user: {
        name: req.user.name,
        tier: tierConfig.name,
        features: tierConfig.features
      },
      stats: {
        projects: tier === 'free' ? 3 : tierConfig.max_projects,
        storage_used: '500 MB',
        storage_limit: tierConfig.storage_gb === null
          ? 'unlimited'
          : `${tierConfig.storage_gb} GB`
      },
      available_actions: {
        can_make_calls: tierConfig.voice_minutes.limit !== 0,
        can_send_sms: tierConfig.sms_messages.limit !== 0,
        can_invite_team: !!tierConfig.team_collaboration,
        can_use_buzz: !!tierConfig.buzz_workspace
      }
    };

    res.json({
      success: true,
      dashboard
    });
  }
);

export default router;
