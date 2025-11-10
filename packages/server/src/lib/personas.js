/**
 * Persona Management Library
 *
 * Handles CRUD operations for AI personas with personality traits,
 * voice models, and tier-based limits.
 */

import { createClient } from '@libsql/client';
import { v4 as uuidv4 } from 'uuid';

/**
 * Create Turso client (singleton pattern)
 */
let dbClient = null;

function getDbClient(env) {
  if (!dbClient) {
    dbClient = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });
  }
  return dbClient;
}

/**
 * Tier limits for personas
 */
const PERSONA_LIMITS = {
  free: 3,
  personal: -1, // unlimited
  professional: -1, // unlimited
  enterprise: -1, // unlimited
};

/**
 * Check if user can create more personas
 */
export async function canCreatePersona(userId, env) {
  const db = getDbClient(env);

  // Get user's tier
  const userResult = await db.execute({
    sql: 'SELECT subscription_tier FROM users WHERE id = ?',
    args: [userId],
  });

  if (userResult.rows.length === 0) {
    throw new Error('User not found');
  }

  const tier = userResult.rows[0].subscription_tier || 'free';
  const limit = PERSONA_LIMITS[tier] || PERSONA_LIMITS.free;

  // If unlimited, allow
  if (limit === -1) {
    return { allowed: true, limit: -1, current: null };
  }

  // Get current persona count
  const countResult = await db.execute({
    sql: 'SELECT COUNT(*) as count FROM personas WHERE user_id = ?',
    args: [userId],
  });

  const current = Number(countResult.rows[0].count);

  return {
    allowed: current < limit,
    limit,
    current,
    tier,
  };
}

/**
 * Create a new persona
 */
export async function createPersona(userId, personaData, env) {
  const db = getDbClient(env);

  // Check tier limits
  const limitCheck = await canCreatePersona(userId, env);
  if (!limitCheck.allowed) {
    throw new Error(`Free tier limited to ${limitCheck.limit} personas. Upgrade to Personal for unlimited personas.`);
  }

  // Validate persona data
  if (!personaData.name || personaData.name.trim().length === 0) {
    throw new Error('Persona name is required');
  }

  if (personaData.name.length > 50) {
    throw new Error('Persona name must be 50 characters or less');
  }

  // Validate personality traits (if provided)
  if (personaData.personality_traits) {
    const traits = personaData.personality_traits;
    const traitKeys = ['extraversion', 'agreeableness', 'conscientiousness', 'neuroticism', 'openness', 'formality', 'enthusiasm'];

    for (const key of traitKeys) {
      if (traits[key] !== undefined) {
        const value = parseFloat(traits[key]);
        if (isNaN(value) || value < 0 || value > 1) {
          throw new Error(`Personality trait '${key}' must be between 0.0 and 1.0`);
        }
      }
    }
  }

  // Validate response style (if provided)
  if (personaData.response_style) {
    const style = personaData.response_style;
    const styleKeys = ['humor_level', 'technical_depth', 'empathy_level', 'proactivity'];

    for (const key of styleKeys) {
      if (style[key] !== undefined) {
        const value = parseFloat(style[key]);
        if (isNaN(value) || value < 0 || value > 1) {
          throw new Error(`Response style '${key}' must be between 0.0 and 1.0`);
        }
      }
    }

    const validVerbosity = ['Concise', 'Balanced', 'Detailed', 'Elaborate'];
    if (style.verbosity && !validVerbosity.includes(style.verbosity)) {
      throw new Error(`Invalid verbosity level. Must be one of: ${validVerbosity.join(', ')}`);
    }

    const validTones = ['Professional', 'Friendly', 'Casual', 'Authoritative', 'Supportive', 'Analytical'];
    if (style.tone && !validTones.includes(style.tone)) {
      throw new Error(`Invalid tone style. Must be one of: ${validTones.join(', ')}`);
    }
  }

  // Create persona record
  const personaId = uuidv4();
  const now = new Date().toISOString();

  const personalityTraits = JSON.stringify(personaData.personality_traits || {
    extraversion: 0.5,
    agreeableness: 0.5,
    conscientiousness: 0.5,
    neuroticism: 0.5,
    openness: 0.5,
    formality: 0.5,
    enthusiasm: 0.5,
  });

  const responseStyle = JSON.stringify(personaData.response_style || {
    verbosity: 'Balanced',
    tone: 'Friendly',
    humor_level: 0.5,
    technical_depth: 0.5,
    empathy_level: 0.5,
    proactivity: 0.5,
  });

  const expertiseAreas = JSON.stringify(personaData.expertise_areas || []);

  const voiceModelConfig = JSON.stringify(personaData.voice_model_config || {
    voice_id: 'default',
    speed: 1.0,
    pitch: 1.0,
    custom_model_path: null,
    training_status: 'NotStarted',
  });

  await db.execute({
    sql: `
      INSERT INTO personas (
        id, user_id, name, description,
        personality_traits, response_style, expertise_areas,
        voice_model_config, conversation_examples, is_active,
        created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `,
    args: [
      personaId,
      userId,
      personaData.name.trim(),
      personaData.description || '',
      personalityTraits,
      responseStyle,
      expertiseAreas,
      voiceModelConfig,
      '[]', // conversation_examples
      personaData.is_active || false,
      now,
      now,
    ],
  });

  return getPersonaById(personaId, env);
}

/**
 * Get persona by ID
 */
export async function getPersonaById(personaId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM personas WHERE id = ?',
    args: [personaId],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return formatPersona(result.rows[0]);
}

/**
 * List personas for a user
 */
export async function listPersonas(userId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM personas WHERE user_id = ? ORDER BY created_at DESC',
    args: [userId],
  });

  return result.rows.map(formatPersona);
}

/**
 * Get active persona for a user
 */
export async function getActivePersona(userId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM personas WHERE user_id = ? AND is_active = TRUE LIMIT 1',
    args: [userId],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return formatPersona(result.rows[0]);
}

/**
 * Update persona
 */
export async function updatePersona(personaId, userId, updates, env) {
  const db = getDbClient(env);

  // Verify ownership
  const existing = await getPersonaById(personaId, env);
  if (!existing) {
    throw new Error('Persona not found');
  }

  if (existing.user_id !== userId) {
    throw new Error('Access denied');
  }

  // Build update query dynamically
  const fields = [];
  const args = [];

  if (updates.name !== undefined) {
    if (!updates.name || updates.name.trim().length === 0) {
      throw new Error('Persona name cannot be empty');
    }
    if (updates.name.length > 50) {
      throw new Error('Persona name must be 50 characters or less');
    }
    fields.push('name = ?');
    args.push(updates.name.trim());
  }

  if (updates.description !== undefined) {
    fields.push('description = ?');
    args.push(updates.description);
  }

  if (updates.personality_traits !== undefined) {
    fields.push('personality_traits = ?');
    args.push(JSON.stringify(updates.personality_traits));
  }

  if (updates.response_style !== undefined) {
    fields.push('response_style = ?');
    args.push(JSON.stringify(updates.response_style));
  }

  if (updates.expertise_areas !== undefined) {
    fields.push('expertise_areas = ?');
    args.push(JSON.stringify(updates.expertise_areas));
  }

  if (updates.voice_model_config !== undefined) {
    fields.push('voice_model_config = ?');
    args.push(JSON.stringify(updates.voice_model_config));
  }

  if (updates.conversation_examples !== undefined) {
    fields.push('conversation_examples = ?');
    args.push(JSON.stringify(updates.conversation_examples));
  }

  if (fields.length === 0) {
    return existing; // No updates
  }

  // Add updated_at
  fields.push('updated_at = ?');
  args.push(new Date().toISOString());

  // Add WHERE clause
  args.push(personaId);

  const sql = `UPDATE personas SET ${fields.join(', ')} WHERE id = ?`;

  await db.execute({ sql, args });

  return getPersonaById(personaId, env);
}

/**
 * Delete persona
 */
export async function deletePersona(personaId, userId, env) {
  const db = getDbClient(env);

  // Verify ownership
  const existing = await getPersonaById(personaId, env);
  if (!existing) {
    throw new Error('Persona not found');
  }

  if (existing.user_id !== userId) {
    throw new Error('Access denied');
  }

  await db.execute({
    sql: 'DELETE FROM personas WHERE id = ?',
    args: [personaId],
  });

  return { success: true };
}

/**
 * Activate persona (deactivates others)
 */
export async function activatePersona(personaId, userId, env) {
  const db = getDbClient(env);

  // Verify ownership
  const existing = await getPersonaById(personaId, env);
  if (!existing) {
    throw new Error('Persona not found');
  }

  if (existing.user_id !== userId) {
    throw new Error('Access denied');
  }

  // Deactivate all user's personas
  await db.execute({
    sql: 'UPDATE personas SET is_active = FALSE WHERE user_id = ?',
    args: [userId],
  });

  // Activate this persona
  await db.execute({
    sql: 'UPDATE personas SET is_active = TRUE, updated_at = ? WHERE id = ?',
    args: [new Date().toISOString(), personaId],
  });

  return getPersonaById(personaId, env);
}

/**
 * Add conversation example for learning
 */
export async function addConversationExample(personaId, userId, example, env) {
  const db = getDbClient(env);

  // Verify ownership
  const persona = await getPersonaById(personaId, env);
  if (!persona) {
    throw new Error('Persona not found');
  }

  if (persona.user_id !== userId) {
    throw new Error('Access denied');
  }

  // Add example to conversation_examples array
  const examples = persona.conversation_examples || [];
  examples.push({
    user_message: example.user_message,
    persona_response: example.persona_response,
    context: example.context || 'user_feedback',
    quality_score: example.quality_score || 1.0,
    timestamp: new Date().toISOString(),
  });

  // Keep only last 100 examples
  if (examples.length > 100) {
    examples.shift();
  }

  await db.execute({
    sql: 'UPDATE personas SET conversation_examples = ?, updated_at = ? WHERE id = ?',
    args: [JSON.stringify(examples), new Date().toISOString(), personaId],
  });

  return getPersonaById(personaId, env);
}

/**
 * Create training session
 */
export async function createTrainingSession(personaId, userId, trainingType, trainingData, env) {
  const db = getDbClient(env);

  // Verify ownership
  const persona = await getPersonaById(personaId, env);
  if (!persona) {
    throw new Error('Persona not found');
  }

  if (persona.user_id !== userId) {
    throw new Error('Access denied');
  }

  const sessionId = uuidv4();
  const now = new Date().toISOString();

  await db.execute({
    sql: `
      INSERT INTO persona_training_sessions (
        id, persona_id, training_type, training_data,
        status, progress_percent, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `,
    args: [
      sessionId,
      personaId,
      trainingType,
      JSON.stringify(trainingData),
      'pending',
      0,
      now,
    ],
  });

  return {
    id: sessionId,
    persona_id: personaId,
    training_type: trainingType,
    status: 'pending',
    progress_percent: 0,
    created_at: now,
  };
}

/**
 * Get training status
 */
export async function getTrainingStatus(personaId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      SELECT * FROM persona_training_sessions
      WHERE persona_id = ?
      ORDER BY created_at DESC
      LIMIT 10
    `,
    args: [personaId],
  });

  return result.rows.map(row => ({
    id: row.id,
    persona_id: row.persona_id,
    training_type: row.training_type,
    status: row.status,
    progress_percent: row.progress_percent,
    error_message: row.error_message,
    started_at: row.started_at,
    completed_at: row.completed_at,
    created_at: row.created_at,
  }));
}

/**
 * Format persona record
 */
function formatPersona(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    name: row.name,
    description: row.description,
    personality_traits: JSON.parse(row.personality_traits),
    response_style: JSON.parse(row.response_style),
    expertise_areas: JSON.parse(row.expertise_areas),
    voice_model_config: JSON.parse(row.voice_model_config),
    conversation_examples: JSON.parse(row.conversation_examples || '[]'),
    is_active: Boolean(row.is_active),
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}
