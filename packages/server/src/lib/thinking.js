/**
 * Thinking Service API
 *
 * Provides AI-powered memory filtering with cost-based model selection.
 *
 * Endpoints:
 *   POST /api/thinking/filter - Filter memories by relevance and importance
 *
 * Features:
 * - Automatic model selection (cheapest for requested tier)
 * - Multi-provider support (Anthropic Claude, OpenAI GPT)
 * - Cost tracking per request
 * - Graceful fallback to unfiltered results
 *
 * Usage from client:
 *   POST /api/thinking/filter
 *   Body: {
 *     level: "light",  // or "normal", "deep"
 *     context: "User asking about preferences",
 *     candidates: [
 *       { id: "mem1", text: "User's favorite color is blue", ... },
 *       { id: "mem2", text: "User likes pizza", ... }
 *     ]
 *   }
 *
 *   Response: {
 *     approved: [{ id: "mem1", text: "...", ... }],
 *     cost: { tokensUsed: 1500, costUSD: 0.000225 },
 *     model: "OPENAI:gpt-4o-mini"
 *   }
 */

import Anthropic from '@anthropic-ai/sdk';
import OpenAI from 'openai';
import { selectModelForThinking, estimateCost } from './thinking-models.js';

// =============================================================================
// AI CLIENT INITIALIZATION
// =============================================================================

let anthropicClient = null;
let openaiClient = null;

/**
 * Initialize AI clients from environment variables.
 *
 * Expected env vars:
 * - ANTHROPIC_API_KEY
 * - OPENAI_API_KEY
 */
function initializeClients() {
  if (process.env.ANTHROPIC_API_KEY) {
    anthropicClient = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY
    });
    console.log('✅ Anthropic client initialized');
  } else {
    console.warn('⚠️  ANTHROPIC_API_KEY not set, Anthropic models unavailable');
  }

  if (process.env.OPENAI_API_KEY) {
    openaiClient = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY
    });
    console.log('✅ OpenAI client initialized');
  } else {
    console.warn('⚠️  OPENAI_API_KEY not set, OpenAI models unavailable');
  }
}

// Initialize on module load
initializeClients();

// =============================================================================
// THINKING PROMPT
// =============================================================================

/**
 * Build prompt for AI thinking engine.
 *
 * Asks AI to evaluate each memory for:
 * - Relevance: Does it relate to current conversation?
 * - Importance: Is it significant enough to inject?
 *
 * @param {string} context - Current conversation context
 * @param {array} candidates - Candidate memories to filter
 * @returns {string} Formatted prompt
 */
function buildFilterPrompt(context, candidates) {
  let prompt = `Given this conversation context:
${context}

For each of these ${candidates.length} candidate memories, evaluate:
1. Is this memory relevant to the current conversation? (yes/no)
2. Is this memory important enough to inject into limited context? (yes/no)

Memories:
`;

  // Add numbered memories
  candidates.forEach((mem, i) => {
    prompt += `\n${i + 1}. ${mem.text}`;
  });

  // Request JSON response
  prompt += `\n\nRespond with JSON array (one object per memory):
[{"relevant": true/false, "important": true/false}, ...]`;

  return prompt;
}

// =============================================================================
// AI PROVIDER CALLS
// =============================================================================

/**
 * Call Anthropic Claude for thinking.
 *
 * @param {string} model - Model name (e.g., "claude-haiku-4-5")
 * @param {string} prompt - Filter prompt
 * @returns {object} Response with text and token usage
 */
async function callAnthropic(model, prompt) {
  if (!anthropicClient) {
    throw new Error('Anthropic client not initialized (missing API key)');
  }

  const response = await anthropicClient.messages.create({
    model: model,
    max_tokens: 1024,
    messages: [{
      role: 'user',
      content: prompt
    }]
  });

  return {
    text: response.content[0].text,
    tokensUsed: response.usage.input_tokens + response.usage.output_tokens
  };
}

/**
 * Call OpenAI GPT for thinking.
 *
 * @param {string} model - Model name (e.g., "gpt-4o-mini")
 * @param {string} prompt - Filter prompt
 * @returns {object} Response with text and token usage
 */
async function callOpenAI(model, prompt) {
  if (!openaiClient) {
    throw new Error('OpenAI client not initialized (missing API key)');
  }

  const response = await openaiClient.chat.completions.create({
    model: model,
    max_tokens: 1024,
    messages: [{
      role: 'user',
      content: prompt
    }]
  });

  return {
    text: response.choices[0].message.content,
    tokensUsed: response.usage.total_tokens
  };
}

// =============================================================================
// MAIN FILTERING LOGIC
// =============================================================================

/**
 * Filter memories using AI thinking service.
 *
 * @param {string} level - Thinking level ("light", "normal", "deep")
 * @param {string} context - Conversation context
 * @param {array} candidates - Candidate memories [{id, text, ...}, ...]
 * @returns {object} Filtered results with cost tracking
 *
 * @example
 * const result = await filterMemories('light', 'User asking about preferences', [
 *   { id: 'mem1', text: 'User likes blue', user_id: 'u1', created_at: '2025-01-01' },
 *   { id: 'mem2', text: 'User likes pizza', user_id: 'u1', created_at: '2025-01-02' }
 * ]);
 * // => { approved: [...], cost: {...}, model: 'OPENAI:gpt-4o-mini' }
 */
export async function filterMemories(level, context, candidates) {
  try {
    // Step 1: Select best model for requested tier
    const excludeProviders = [];
    if (!anthropicClient) excludeProviders.push('ANTHROPIC');
    if (!openaiClient) excludeProviders.push('OPENAI');

    if (excludeProviders.length === 2) {
      throw new Error('No AI providers available (missing API keys)');
    }

    const modelInfo = selectModelForThinking(level, { excludeProviders });
    console.log(`🧠 Selected ${modelInfo.provider}:${modelInfo.model} for thinking level: ${level}`);

    // Step 2: Build prompt
    const prompt = buildFilterPrompt(context, candidates);

    // Step 3: Call appropriate AI provider
    let response;
    if (modelInfo.provider === 'ANTHROPIC') {
      response = await callAnthropic(modelInfo.model, prompt);
    } else if (modelInfo.provider === 'OPENAI') {
      response = await callOpenAI(modelInfo.model, prompt);
    } else {
      throw new Error(`Unknown provider: ${modelInfo.provider}`);
    }

    // Step 4: Parse JSON response
    let evaluations;
    try {
      // Extract JSON from response (may have markdown code blocks)
      const jsonMatch = response.text.match(/\[[\s\S]*\]/);
      if (!jsonMatch) {
        throw new Error('No JSON array found in response');
      }
      evaluations = JSON.parse(jsonMatch[0]);
    } catch (parseError) {
      console.error('Failed to parse AI response:', response.text);
      throw new Error(`JSON parse error: ${parseError.message}`);
    }

    // Step 5: Filter memories (relevant AND important)
    const approved = [];
    candidates.forEach((mem, i) => {
      const evaluation = evaluations[i];
      if (evaluation && evaluation.relevant && evaluation.important) {
        approved.push(mem);
      }
    });

    // Step 6: Calculate cost
    const costUSD = (response.tokensUsed / 1_000_000) * modelInfo.costPerMToken;

    console.log(
      `✅ Filtered ${candidates.length} → ${approved.length} memories ` +
      `(${response.tokensUsed} tokens, $${costUSD.toFixed(6)})`
    );

    return {
      approved,
      cost: {
        tokensUsed: response.tokensUsed,
        costUSD: parseFloat(costUSD.toFixed(6)),
        costPerMToken: modelInfo.costPerMToken
      },
      model: `${modelInfo.provider}:${modelInfo.model}`,
      tier: level
    };

  } catch (error) {
    console.error('Thinking service error:', error);

    // Fallback: Return top 3 unfiltered candidates
    console.warn('⚠️  Falling back to unfiltered top-3 memories');
    return {
      approved: candidates.slice(0, 3),
      cost: { tokensUsed: 0, costUSD: 0 },
      model: 'FALLBACK:unfiltered',
      tier: level,
      error: error.message
    };
  }
}

// =============================================================================
// EXPRESS ROUTE HANDLERS
// =============================================================================

/**
 * POST /api/thinking/filter
 *
 * Filter memories by relevance and importance.
 *
 * Request body:
 * {
 *   level: "light" | "normal" | "deep",
 *   context: "conversation context",
 *   candidates: [{id, text, user_id, created_at}, ...]
 * }
 *
 * Response:
 * {
 *   approved: [...],
 *   cost: { tokensUsed, costUSD, costPerMToken },
 *   model: "PROVIDER:model-name",
 *   tier: "light"
 * }
 */
export async function handleFilterRequest(req, res) {
  try {
    const { level, context, candidates } = req.body;

    // Validate request
    if (!level || !['light', 'normal', 'deep'].includes(level)) {
      return res.status(400).json({
        error: 'Invalid thinking level. Must be: light, normal, or deep'
      });
    }

    if (!context || typeof context !== 'string') {
      return res.status(400).json({
        error: 'Missing or invalid context'
      });
    }

    if (!Array.isArray(candidates) || candidates.length === 0) {
      return res.status(400).json({
        error: 'Missing or empty candidates array'
      });
    }

    // Filter memories
    const result = await filterMemories(level, context, candidates);

    // Return result
    return res.status(200).json(result);

  } catch (error) {
    console.error('Filter request error:', error);
    return res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
}

/**
 * GET /api/thinking/health
 *
 * Check thinking service availability.
 *
 * Response:
 * {
 *   available: true/false,
 *   providers: ["ANTHROPIC", "OPENAI"],
 *   message: "..."
 * }
 */
export async function handleHealthCheck(req, res) {
  const providers = [];
  if (anthropicClient) providers.push('ANTHROPIC');
  if (openaiClient) providers.push('OPENAI');

  const available = providers.length > 0;

  return res.status(200).json({
    available,
    providers,
    message: available
      ? `Thinking service available with ${providers.join(', ')}`
      : 'Thinking service unavailable (no API keys configured)'
  });
}

// =============================================================================
// EXPORTS
// =============================================================================

export default {
  filterMemories,
  handleFilterRequest,
  handleHealthCheck,
  initializeClients  // For testing
};
