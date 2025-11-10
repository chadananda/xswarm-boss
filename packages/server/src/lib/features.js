/**
 * Feature Gating System - Centralized Feature Definitions
 *
 * Defines tier-based feature matrix with limits, capabilities, and upgrade paths.
 * Modern, functional approach with comprehensive feature definitions.
 */

/**
 * Tier-based feature matrix
 * Defines all features, limits, and capabilities for each subscription tier
 */
export const TIER_FEATURES = {
  free: {
    name: 'AI Buddy',
    monthly_price: 0,
    annual_price: 0,
    personas: { limit: 3, default: ['boss', 'hal', 'sauron'] },
    voice_minutes: { limit: 0, overage_rate: null, overage_allowed: false },
    sms_messages: { limit: 0, overage_rate: null, overage_allowed: false },
    email_daily: { limit: 100 },
    calendar_access: 'read',
    memory_retention_days: 30,
    wake_words: ['hey-hal', 'hey-xswarm'],
    ai_models: ['gpt-3.5-turbo'],
    document_generation: false,
    team_collaboration: false,
    buzz_workspace: false,
    priority_support: false,
    custom_integrations: false,
    api_access: false,
    max_projects: 3,
    storage_gb: 1,
    features: [
      'Basic email assistance',
      'Read-only calendar access',
      'Up to 3 custom personas',
      '30-day memory retention',
      'Community support'
    ]
  },

  personal: {
    name: 'AI Secretary',
    monthly_price: 29,
    annual_price: 290,
    personas: { limit: null }, // unlimited
    voice_minutes: { limit: 100, overage_rate: 0.013, overage_allowed: true },
    sms_messages: { limit: 100, overage_rate: 0.0075, overage_allowed: true },
    email_daily: { limit: null }, // unlimited
    calendar_access: 'write',
    memory_retention_days: 365,
    wake_words: ['hey-hal', 'hey-xswarm', 'hey-boss', 'custom'],
    ai_models: ['gpt-4', 'claude-3-sonnet', 'gemini-pro'],
    document_generation: ['docx', 'pdf', 'txt', 'md'],
    team_collaboration: false,
    buzz_workspace: false,
    priority_support: 'email',
    custom_integrations: 'limited',
    api_access: 'basic',
    max_projects: 25,
    storage_gb: 10,
    features: [
      'Everything in AI Buddy',
      '100 voice minutes/month',
      '100 SMS messages/month',
      'Unlimited emails',
      'Full calendar management',
      'Advanced AI models (GPT-4, Claude)',
      'Document generation',
      'Custom wake words',
      '1-year memory retention',
      'Email support'
    ]
  },

  professional: {
    name: 'AI Project Manager',
    monthly_price: 99,
    annual_price: 990,
    personas: { limit: null },
    voice_minutes: { limit: 500, overage_rate: 0.010, overage_allowed: true },
    sms_messages: { limit: 500, overage_rate: 0.005, overage_allowed: true },
    email_daily: { limit: null },
    calendar_access: 'write',
    memory_retention_days: 730, // 2 years
    wake_words: ['hey-hal', 'hey-xswarm', 'hey-boss', 'custom'],
    ai_models: ['gpt-4-turbo', 'claude-3-opus', 'gemini-ultra'],
    document_generation: ['docx', 'pdf', 'xlsx', 'pptx', 'txt', 'md'],
    team_collaboration: { limit: 10, roles: ['viewer', 'editor', 'admin'] },
    buzz_workspace: { channels: 50, members_per_channel: 25 },
    priority_support: 'priority',
    custom_integrations: 'advanced',
    api_access: 'full',
    max_projects: 100,
    storage_gb: 100,
    features: [
      'Everything in AI Secretary',
      '500 voice minutes/month',
      '500 SMS messages/month',
      'Team collaboration (up to 10 members)',
      'Buzz workspace integration',
      'Advanced AI models',
      'Full document suite (Word, Excel, PowerPoint)',
      'Custom integrations',
      'Full API access',
      '2-year memory retention',
      'Priority support'
    ]
  },

  enterprise: {
    name: 'AI CTO',
    monthly_price: 299,
    annual_price: 2990,
    personas: { limit: null },
    voice_minutes: { limit: null, overage_rate: null, overage_allowed: false }, // unlimited
    sms_messages: { limit: null, overage_rate: null, overage_allowed: false }, // unlimited
    email_daily: { limit: null },
    calendar_access: 'write',
    memory_retention_days: null, // unlimited
    wake_words: ['hey-hal', 'hey-xswarm', 'hey-boss', 'custom'],
    ai_models: ['gpt-4-turbo', 'claude-3-opus', 'gemini-ultra', 'custom'],
    document_generation: ['docx', 'pdf', 'xlsx', 'pptx', 'txt', 'md', 'html', 'custom'],
    team_collaboration: { limit: null, roles: ['viewer', 'editor', 'admin', 'owner'] },
    buzz_workspace: { channels: null, members_per_channel: null },
    priority_support: 'dedicated',
    custom_integrations: 'unlimited',
    api_access: 'enterprise',
    max_projects: null,
    storage_gb: null, // unlimited
    white_label: true,
    custom_deployment: true,
    sla_guarantee: '99.9%',
    features: [
      'Everything in AI Project Manager',
      'Unlimited voice minutes',
      'Unlimited SMS messages',
      'Unlimited team members',
      'Unlimited Buzz workspace',
      'All AI models + custom models',
      'White-label options',
      'Custom deployment',
      'Dedicated account manager',
      '99.9% SLA guarantee',
      'Unlimited storage',
      'Unlimited memory retention'
    ]
  },

  admin: {
    name: 'Admin',
    monthly_price: 0,
    annual_price: 0,
    personas: { limit: null },
    voice_minutes: { limit: null, overage_rate: null, overage_allowed: false },
    sms_messages: { limit: null, overage_rate: null, overage_allowed: false },
    email_daily: { limit: null },
    calendar_access: 'write',
    memory_retention_days: null,
    wake_words: ['hey-hal', 'hey-xswarm', 'hey-boss', 'custom'],
    ai_models: ['gpt-4-turbo', 'claude-3-opus', 'gemini-ultra', 'custom'],
    document_generation: ['docx', 'pdf', 'xlsx', 'pptx', 'txt', 'md', 'html', 'custom'],
    team_collaboration: { limit: null, roles: ['viewer', 'editor', 'admin', 'owner'] },
    buzz_workspace: { channels: null, members_per_channel: null },
    priority_support: 'dedicated',
    custom_integrations: 'unlimited',
    api_access: 'enterprise',
    max_projects: null,
    storage_gb: null,
    admin_panel: true,
    all_features: true,
    features: ['All features enabled', 'Admin panel access', 'System management']
  }
};

/**
 * Feature categories for organized checking
 */
export const FEATURE_CATEGORIES = {
  communication: ['voice', 'sms', 'email', 'calendar'],
  ai: ['ai_models', 'personas', 'wake_words', 'memory_retention'],
  collaboration: ['team_collaboration', 'buzz_workspace', 'projects'],
  content: ['document_generation', 'storage'],
  support: ['priority_support', 'custom_integrations', 'api_access']
};

/**
 * Check if a tier has access to a specific feature
 *
 * @param {string} tier - Subscription tier
 * @param {string} feature - Feature to check
 * @returns {boolean|Object} Feature availability (true/false or config object)
 */
export function hasFeature(tier, feature) {
  const tierConfig = TIER_FEATURES[tier];
  if (!tierConfig) return false;

  // Admin has everything
  if (tier === 'admin') return true;

  const value = tierConfig[feature];

  // Handle different value types
  if (value === undefined || value === null) return false;
  if (typeof value === 'boolean') return value;
  if (typeof value === 'object' && value.limit !== undefined) {
    return value.limit !== 0; // Has feature if limit > 0 or null (unlimited)
  }

  return !!value;
}

/**
 * Check if user is within usage limits for a feature
 *
 * @param {string} tier - Subscription tier
 * @param {string} feature - Feature name (voice_minutes, sms_messages, etc.)
 * @param {number} currentUsage - Current usage amount
 * @returns {Object} { allowed: boolean, limit: number|null, remaining: number|null, overage: number }
 */
export function checkLimit(tier, feature, currentUsage) {
  const tierConfig = TIER_FEATURES[tier];
  if (!tierConfig) {
    return { allowed: false, limit: 0, remaining: 0, overage: 0 };
  }

  const featureConfig = tierConfig[feature];

  // No limit defined = not available
  if (!featureConfig || featureConfig.limit === undefined) {
    return { allowed: false, limit: 0, remaining: 0, overage: 0 };
  }

  const limit = featureConfig.limit;

  // Unlimited access
  if (limit === null) {
    return { allowed: true, limit: null, remaining: null, overage: 0 };
  }

  // Zero limit = feature not available
  if (limit === 0) {
    return { allowed: false, limit: 0, remaining: 0, overage: 0 };
  }

  // Calculate remaining and overage
  const remaining = Math.max(0, limit - currentUsage);
  const overage = Math.max(0, currentUsage - limit);

  // Check if overages are allowed
  const allowed = featureConfig.overage_allowed ? true : currentUsage < limit;

  return {
    allowed,
    limit,
    remaining,
    overage,
    overage_allowed: featureConfig.overage_allowed || false,
    overage_rate: featureConfig.overage_rate || null
  };
}

/**
 * Calculate overage cost for a feature
 *
 * @param {string} tier - Subscription tier
 * @param {string} feature - Feature name
 * @param {number} overageAmount - Amount over limit
 * @returns {number} Cost in dollars
 */
export function calculateOverageCost(tier, feature, overageAmount) {
  const tierConfig = TIER_FEATURES[tier];
  if (!tierConfig) return 0;

  const featureConfig = tierConfig[feature];
  if (!featureConfig || !featureConfig.overage_rate) return 0;

  return overageAmount * featureConfig.overage_rate;
}

/**
 * Get upgrade path - which tiers would unlock a feature
 *
 * @param {string} currentTier - Current subscription tier
 * @param {string} feature - Feature to unlock
 * @returns {Array} Array of tier names that have the feature
 */
export function getUpgradePath(currentTier, feature) {
  const tierOrder = ['free', 'personal', 'professional', 'enterprise'];
  const currentIndex = tierOrder.indexOf(currentTier);

  return tierOrder
    .slice(currentIndex + 1)
    .filter(tier => hasFeature(tier, feature))
    .map(tier => ({
      tier,
      name: TIER_FEATURES[tier].name,
      monthly_price: TIER_FEATURES[tier].monthly_price,
      annual_price: TIER_FEATURES[tier].annual_price
    }));
}

/**
 * Get next tier upgrade option
 *
 * @param {string} currentTier - Current subscription tier
 * @returns {Object|null} Next tier info or null if at highest tier
 */
export function getNextTier(currentTier) {
  const tierOrder = ['free', 'personal', 'professional', 'enterprise'];
  const currentIndex = tierOrder.indexOf(currentTier);

  if (currentIndex === -1 || currentIndex >= tierOrder.length - 1) {
    return null;
  }

  const nextTier = tierOrder[currentIndex + 1];
  return {
    tier: nextTier,
    ...TIER_FEATURES[nextTier]
  };
}

/**
 * Compare features between two tiers
 *
 * @param {string} fromTier - Current tier
 * @param {string} toTier - Target tier
 * @returns {Object} Comparison object with added/improved features
 */
export function compareTiers(fromTier, toTier) {
  const from = TIER_FEATURES[fromTier];
  const to = TIER_FEATURES[toTier];

  if (!from || !to) return null;

  const improvements = {
    tier_change: { from: fromTier, to: toTier },
    name_change: { from: from.name, to: to.name },
    price_change: {
      monthly: to.monthly_price - from.monthly_price,
      annual: to.annual_price - from.annual_price
    },
    new_features: [],
    improved_limits: []
  };

  // Check for new features
  Object.keys(to).forEach(key => {
    if (key === 'features' || key === 'name' || key.includes('price')) return;

    const fromValue = from[key];
    const toValue = to[key];

    // New boolean feature
    if (typeof toValue === 'boolean' && !fromValue && toValue) {
      improvements.new_features.push(key);
    }

    // New or improved limits
    if (typeof toValue === 'object' && toValue.limit !== undefined) {
      const fromLimit = fromValue?.limit || 0;
      const toLimit = toValue.limit;

      if (toLimit === null && fromLimit !== null) {
        improvements.improved_limits.push({
          feature: key,
          from: fromLimit,
          to: 'unlimited'
        });
      } else if (toLimit > fromLimit) {
        improvements.improved_limits.push({
          feature: key,
          from: fromLimit,
          to: toLimit
        });
      }
    }
  });

  return improvements;
}

/**
 * Generate user-friendly upgrade message
 *
 * @param {string} feature - Feature name
 * @param {string} currentTier - Current tier
 * @returns {Object} Upgrade message with CTA
 */
export function generateUpgradeMessage(feature, currentTier) {
  const upgrades = getUpgradePath(currentTier, feature);

  if (upgrades.length === 0) {
    return {
      message: 'This feature is not available on any plan.',
      cta: null
    };
  }

  const nextTier = upgrades[0];
  const featureName = feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

  return {
    message: `${featureName} is available on the ${nextTier.name} plan and higher.`,
    cta: {
      text: `Upgrade to ${nextTier.name}`,
      tier: nextTier.tier,
      price: nextTier.monthly_price > 0
        ? `$${nextTier.monthly_price}/month`
        : 'Free'
    },
    upgrade_options: upgrades
  };
}

/**
 * Validate tier name
 *
 * @param {string} tier - Tier to validate
 * @returns {boolean} True if valid tier
 */
export function isValidTier(tier) {
  return tier in TIER_FEATURES;
}

/**
 * Get all available tiers for comparison
 *
 * @returns {Array} Array of all tiers with their configs
 */
export function getAllTiers() {
  return Object.entries(TIER_FEATURES)
    .filter(([key]) => key !== 'admin') // Exclude admin from public listing
    .map(([tier, config]) => ({
      tier,
      ...config
    }));
}

/**
 * Feature mapping - Maps feature names to tier config keys
 */
const FEATURE_MAP = {
  'voice': 'voice_minutes',
  'sms': 'sms_messages',
  'email': 'email_daily',
  'email_integration': 'email_daily', // Gmail OAuth integration available on all tiers
  'email_compose': 'calendar_access', // Email sending requires Personal+ (same as write access)
  'calendar': 'calendar_access',
  'semantic_memory': 'memory_retention_days',
  'team_collaboration': 'team_collaboration',
  'buzz_workspace': 'buzz_workspace',
  'document_generation': 'document_generation',
  'api_access': 'api_access',
  'priority_support': 'priority_support',
  'custom_integrations': 'custom_integrations',
  'personas': 'personas',
  'wake_words': 'wake_words',
  'ai_models': 'ai_models',
  'projects': 'max_projects',
  'storage': 'storage_gb'
};

/**
 * Check if a user has access to a specific feature (async database lookup)
 *
 * @param {Object} db - Database connection
 * @param {string} userId - User ID
 * @param {string} feature - Feature name (e.g., 'semantic_memory', 'voice', 'sms')
 * @returns {Promise<boolean>} True if user has access to feature
 */
export async function checkFeatureAccess(db, userId, feature) {
  try {
    // Get user's subscription tier
    const result = await db.execute({
      sql: 'SELECT subscription_tier FROM users WHERE id = ?',
      args: [userId]
    });

    if (result.rows.length === 0) {
      return false;
    }

    const tier = result.rows[0].subscription_tier;

    // Map feature name to tier config key
    const tierKey = FEATURE_MAP[feature] || feature;

    // Check if tier has this feature
    return hasFeature(tier, tierKey);
  } catch (error) {
    console.error('Error checking feature access:', error);
    return false;
  }
}
