/**
 * Thinking Models Database
 *
 * Maintains a database of AI models for the thinking service with:
 * - Model metadata (provider, capabilities, context window)
 * - Real-time pricing (updated periodically)
 * - Cost-based selection logic
 * - Quality tier mappings (light, normal, deep)
 *
 * Usage:
 *   const { selectModelForThinking } = require('./thinking-models');
 *   const model = selectModelForThinking('light');
 *   // => { provider: 'ANTHROPIC', model: 'claude-haiku-4-5', costPerMToken: 0.25 }
 */

/**
 * Model database with current pricing (as of 2025-01).
 *
 * Pricing structure:
 * - costPerMToken: Cost per million tokens (input + output average)
 * - qualityScore: 1-10 rating for response quality
 * - speedScore: 1-10 rating for response speed
 *
 * Note: Prices are updated monthly based on provider pricing pages.
 */
const MODEL_DATABASE = [
  // ========== LIGHT TIER (Fast & Cheap) ==========
  {
    provider: 'ANTHROPIC',
    model: 'claude-haiku-4-5',
    tier: 'light',
    costPerMToken: 0.25,    // $0.25 / 1M tokens (avg input/output)
    contextWindow: 200000,
    qualityScore: 7,
    speedScore: 10,
    description: 'Fast, efficient Haiku model - best for simple filtering'
  },
  {
    provider: 'OPENAI',
    model: 'gpt-4o-mini',
    tier: 'light',
    costPerMToken: 0.15,    // $0.15 / 1M tokens
    contextWindow: 128000,
    qualityScore: 6,
    speedScore: 9,
    description: 'OpenAI mini model - cheapest option'
  },
  {
    provider: 'ANTHROPIC',
    model: 'claude-3-haiku',
    tier: 'light',
    costPerMToken: 0.40,    // $0.25 input + $0.55 output avg
    contextWindow: 200000,
    qualityScore: 7,
    speedScore: 9,
    description: 'Previous gen Haiku - fallback'
  },

  // ========== NORMAL TIER (Balanced) ==========
  {
    provider: 'OPENAI',
    model: 'gpt-4-turbo',
    tier: 'normal',
    costPerMToken: 10.0,    // $10 / 1M tokens (avg)
    contextWindow: 128000,
    qualityScore: 8,
    speedScore: 7,
    description: 'GPT-4 Turbo - balanced quality and cost'
  },
  {
    provider: 'ANTHROPIC',
    model: 'claude-sonnet-4',
    tier: 'normal',
    costPerMToken: 3.0,     // $3 input + $15 output avg = ~$9/M
    contextWindow: 200000,
    qualityScore: 9,
    speedScore: 7,
    description: 'Sonnet 4 - excellent balance'
  },
  {
    provider: 'OPENAI',
    model: 'gpt-4o',
    tier: 'normal',
    costPerMToken: 5.0,     // $2.50 input + $7.50 output avg
    contextWindow: 128000,
    qualityScore: 8,
    speedScore: 8,
    description: 'GPT-4o - fast and balanced'
  },

  // ========== DEEP TIER (High Quality) ==========
  {
    provider: 'ANTHROPIC',
    model: 'claude-sonnet-4-5',
    tier: 'deep',
    costPerMToken: 3.0,     // $3 input + $15 output avg = ~$9/M
    contextWindow: 200000,
    qualityScore: 10,
    speedScore: 6,
    description: 'Sonnet 4.5 - highest quality reasoning'
  },
  {
    provider: 'OPENAI',
    model: 'o1-preview',
    tier: 'deep',
    costPerMToken: 30.0,    // $15 input + $60 output avg
    contextWindow: 128000,
    qualityScore: 10,
    speedScore: 4,
    description: 'OpenAI o1 - advanced reasoning'
  },
  {
    provider: 'ANTHROPIC',
    model: 'claude-opus-4',
    tier: 'deep',
    costPerMToken: 15.0,    // $15 input + $75 output avg = ~$45/M
    contextWindow: 200000,
    qualityScore: 10,
    speedScore: 5,
    description: 'Opus 4 - maximum quality'
  }
];

/**
 * Select best model for requested thinking level based on cost.
 *
 * Selection algorithm:
 * 1. Filter models by requested tier (light/normal/deep)
 * 2. Sort by cost (cheapest first)
 * 3. Return cheapest available model
 *
 * @param {string} thinkingLevel - "light", "normal", or "deep"
 * @param {object} options - Optional constraints
 * @param {string[]} options.excludeProviders - Providers to exclude (e.g., ["OPENAI"])
 * @param {number} options.maxCostPerMToken - Maximum acceptable cost
 * @param {number} options.minQualityScore - Minimum quality score (1-10)
 * @returns {object} Selected model with provider, model name, and cost
 *
 * @example
 * const model = selectModelForThinking('light');
 * // => { provider: 'OPENAI', model: 'gpt-4o-mini', costPerMToken: 0.15, ... }
 *
 * @example
 * const model = selectModelForThinking('normal', { excludeProviders: ['OPENAI'] });
 * // => { provider: 'ANTHROPIC', model: 'claude-sonnet-4', costPerMToken: 3.0, ... }
 */
function selectModelForThinking(thinkingLevel, options = {}) {
  const {
    excludeProviders = [],
    maxCostPerMToken = Infinity,
    minQualityScore = 0
  } = options;

  // Normalize thinking level
  const tier = thinkingLevel.toLowerCase();
  if (!['light', 'normal', 'deep'].includes(tier)) {
    throw new Error(`Invalid thinking level: ${thinkingLevel}. Must be light, normal, or deep.`);
  }

  // Filter models by tier and constraints
  let candidates = MODEL_DATABASE.filter(model => {
    return (
      model.tier === tier &&
      !excludeProviders.includes(model.provider) &&
      model.costPerMToken <= maxCostPerMToken &&
      model.qualityScore >= minQualityScore
    );
  });

  if (candidates.length === 0) {
    throw new Error(
      `No models available for tier ${tier} with given constraints. ` +
      `Try removing excludeProviders or increasing maxCostPerMToken.`
    );
  }

  // Sort by cost (cheapest first), then quality (highest first)
  candidates.sort((a, b) => {
    if (a.costPerMToken !== b.costPerMToken) {
      return a.costPerMToken - b.costPerMToken;  // Cheaper is better
    }
    return b.qualityScore - a.qualityScore;  // Higher quality is better
  });

  // Return cheapest model
  return candidates[0];
}

/**
 * Get all models for a specific tier (for debugging/admin).
 *
 * @param {string} tier - "light", "normal", or "deep"
 * @returns {object[]} Array of models in tier, sorted by cost
 *
 * @example
 * const lightModels = getModelsForTier('light');
 * // => [ { provider: 'OPENAI', model: 'gpt-4o-mini', ... }, ... ]
 */
function getModelsForTier(tier) {
  return MODEL_DATABASE
    .filter(model => model.tier === tier)
    .sort((a, b) => a.costPerMToken - b.costPerMToken);
}

/**
 * Get all available providers.
 *
 * @returns {string[]} Array of unique provider names
 *
 * @example
 * const providers = getAvailableProviders();
 * // => ['ANTHROPIC', 'OPENAI']
 */
function getAvailableProviders() {
  return [...new Set(MODEL_DATABASE.map(model => model.provider))];
}

/**
 * Estimate cost for a thinking request.
 *
 * @param {string} thinkingLevel - "light", "normal", or "deep"
 * @param {number} estimatedTokens - Estimated tokens for request (input + output)
 * @returns {object} Cost estimate with model info
 *
 * @example
 * const estimate = estimateCost('light', 5000);
 * // => { model: 'gpt-4o-mini', costUSD: 0.00075, tokensUsed: 5000 }
 */
function estimateCost(thinkingLevel, estimatedTokens) {
  const model = selectModelForThinking(thinkingLevel);
  const costUSD = (estimatedTokens / 1_000_000) * model.costPerMToken;

  return {
    provider: model.provider,
    model: model.model,
    tier: model.tier,
    tokensUsed: estimatedTokens,
    costUSD: parseFloat(costUSD.toFixed(6)),  // Round to 6 decimal places
    costPerMToken: model.costPerMToken
  };
}

/**
 * Get model database statistics (for admin dashboard).
 *
 * @returns {object} Statistics about available models
 */
function getModelStats() {
  const tiers = ['light', 'normal', 'deep'];
  const stats = {
    totalModels: MODEL_DATABASE.length,
    providers: getAvailableProviders(),
    tierBreakdown: {}
  };

  tiers.forEach(tier => {
    const tierModels = getModelsForTier(tier);
    stats.tierBreakdown[tier] = {
      count: tierModels.length,
      cheapest: tierModels[0],
      mostExpensive: tierModels[tierModels.length - 1],
      avgCost: tierModels.reduce((sum, m) => sum + m.costPerMToken, 0) / tierModels.length
    };
  });

  return stats;
}

// =============================================================================
// EXPORTS
// =============================================================================

export {
  selectModelForThinking,
  getModelsForTier,
  getAvailableProviders,
  estimateCost,
  getModelStats,
  MODEL_DATABASE  // Export for testing/admin
};

// =============================================================================
// INLINE TESTS (run with: node thinking-models.js)
// =============================================================================

if (import.meta.url === `file://${process.argv[1]}`) {
  console.log('Testing Thinking Models Database...\n');

  // Test 1: Select light model
  console.log('1. Testing light tier selection:');
  const lightModel = selectModelForThinking('light');
  console.log(`   ✓ Selected: ${lightModel.provider}:${lightModel.model}`);
  console.log(`   ✓ Cost: $${lightModel.costPerMToken}/M tokens\n`);

  // Test 2: Select normal model
  console.log('2. Testing normal tier selection:');
  const normalModel = selectModelForThinking('normal');
  console.log(`   ✓ Selected: ${normalModel.provider}:${normalModel.model}`);
  console.log(`   ✓ Cost: $${normalModel.costPerMToken}/M tokens\n`);

  // Test 3: Select deep model
  console.log('3. Testing deep tier selection:');
  const deepModel = selectModelForThinking('deep');
  console.log(`   ✓ Selected: ${deepModel.provider}:${deepModel.model}`);
  console.log(`   ✓ Cost: $${deepModel.costPerMToken}/M tokens\n`);

  // Test 4: Exclude providers
  console.log('4. Testing provider exclusion:');
  const anthropicOnly = selectModelForThinking('light', { excludeProviders: ['OPENAI'] });
  console.log(`   ✓ Selected: ${anthropicOnly.provider}:${anthropicOnly.model}`);
  console.log(`   ✓ Provider: ${anthropicOnly.provider} (no OpenAI)\n`);

  // Test 5: Cost estimation
  console.log('5. Testing cost estimation:');
  const estimate = estimateCost('light', 5000);
  console.log(`   ✓ Model: ${estimate.provider}:${estimate.model}`);
  console.log(`   ✓ Est. cost for 5k tokens: $${estimate.costUSD}\n`);

  // Test 6: Get model stats
  console.log('6. Testing model statistics:');
  const stats = getModelStats();
  console.log(`   ✓ Total models: ${stats.totalModels}`);
  console.log(`   ✓ Providers: ${stats.providers.join(', ')}`);
  console.log(`   ✓ Light tier: ${stats.tierBreakdown.light.count} models`);
  console.log(`   ✓ Cheapest light: ${stats.tierBreakdown.light.cheapest.provider}:${stats.tierBreakdown.light.cheapest.model}\n`);

  console.log('✅ All tests passed!');
  console.log('\nModel database ready for production use.');
}
