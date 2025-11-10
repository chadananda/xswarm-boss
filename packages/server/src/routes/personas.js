/**
 * Personas API Routes
 *
 * RESTful API for AI persona management with personality traits,
 * voice training, and tier-based limits.
 */

import {
  createPersona,
  listPersonas,
  getPersonaById,
  getActivePersona,
  updatePersona,
  deletePersona,
  activatePersona,
  addConversationExample,
  createTrainingSession,
  getTrainingStatus,
  canCreatePersona,
} from '../lib/personas.js';
import { getUserById } from '../lib/users.js';

/**
 * POST /api/personas
 * Create a new persona
 */
export async function handleCreatePersona(request, env) {
  try {
    // Auth check
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // In production, validate JWT token here
    // For now, extract user ID from a custom header
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();

    // Create persona
    const persona = await createPersona(userId, body, env);

    return new Response(JSON.stringify({
      success: true,
      persona,
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error creating persona:', error);

    // Check for tier limit error
    if (error.message.includes('tier limited') || error.message.includes('Upgrade to')) {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'TIER_LIMIT_EXCEEDED',
        upgrade_cta: {
          tier: 'personal',
          feature: 'unlimited_personas',
          benefit: 'Create unlimited AI personalities',
          message: 'Upgrade to Personal tier for unlimited personas',
        },
      }), {
        status: 402, // Payment Required
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to create persona',
      code: 'CREATE_FAILED',
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/personas
 * List all personas for current user
 */
export async function handleListPersonas(request, env) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const personas = await listPersonas(userId, env);

    // Check tier limits
    const limitCheck = await canCreatePersona(userId, env);

    return new Response(JSON.stringify({
      success: true,
      personas,
      meta: {
        total: personas.length,
        limit: limitCheck.limit,
        can_create_more: limitCheck.allowed,
        tier: limitCheck.tier,
      },
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error listing personas:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to list personas',
      code: 'LIST_FAILED',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/personas/active
 * Get active persona for current user
 */
export async function handleGetActivePersona(request, env) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const persona = await getActivePersona(userId, env);

    if (!persona) {
      return new Response(JSON.stringify({
        success: true,
        persona: null,
        message: 'No active persona',
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      success: true,
      persona,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting active persona:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to get active persona',
      code: 'GET_FAILED',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/personas/:personaId
 * Get specific persona
 */
export async function handleGetPersona(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const persona = await getPersonaById(personaId, env);

    if (!persona) {
      return new Response(JSON.stringify({
        error: 'Persona not found',
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check ownership
    if (persona.user_id !== userId) {
      return new Response(JSON.stringify({
        error: 'Access denied',
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      success: true,
      persona,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting persona:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to get persona',
      code: 'GET_FAILED',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * PUT /api/personas/:personaId
 * Update persona
 */
export async function handleUpdatePersona(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();

    const persona = await updatePersona(personaId, userId, body, env);

    return new Response(JSON.stringify({
      success: true,
      persona,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error updating persona:', error);

    if (error.message === 'Persona not found') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (error.message === 'Access denied') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to update persona',
      code: 'UPDATE_FAILED',
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * DELETE /api/personas/:personaId
 * Delete persona
 */
export async function handleDeletePersona(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    await deletePersona(personaId, userId, env);

    return new Response(JSON.stringify({
      success: true,
      message: 'Persona deleted successfully',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error deleting persona:', error);

    if (error.message === 'Persona not found') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (error.message === 'Access denied') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to delete persona',
      code: 'DELETE_FAILED',
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * POST /api/personas/:personaId/activate
 * Activate persona (deactivates others)
 */
export async function handleActivatePersona(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const persona = await activatePersona(personaId, userId, env);

    return new Response(JSON.stringify({
      success: true,
      persona,
      message: `Activated persona: ${persona.name}`,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error activating persona:', error);

    if (error.message === 'Persona not found') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (error.message === 'Access denied') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to activate persona',
      code: 'ACTIVATE_FAILED',
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * POST /api/personas/:personaId/learn
 * Add conversation example for learning
 */
export async function handleAddExample(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();

    if (!body.user_message || !body.persona_response) {
      return new Response(JSON.stringify({
        error: 'Both user_message and persona_response are required',
        code: 'INVALID_INPUT',
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const persona = await addConversationExample(personaId, userId, body, env);

    return new Response(JSON.stringify({
      success: true,
      persona,
      message: 'Conversation example added',
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error adding conversation example:', error);

    if (error.message === 'Persona not found') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (error.message === 'Access denied') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to add example',
      code: 'ADD_FAILED',
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * POST /api/personas/:personaId/train-voice
 * Train voice model (Personal tier feature)
 */
export async function handleTrainVoice(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Check if user has Personal tier or higher
    const user = await getUserById(userId, env);
    const tier = user?.subscription_tier || 'free';

    if (tier === 'free') {
      return new Response(JSON.stringify({
        error: 'Voice training requires Personal tier or higher',
        code: 'TIER_REQUIRED',
        upgrade_cta: {
          tier: 'personal',
          feature: 'voice_training',
          benefit: 'Train custom voice models for your personas',
          message: 'Upgrade to Personal tier for voice training',
        },
      }), {
        status: 402, // Payment Required
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();

    if (!body.audio_samples || !Array.isArray(body.audio_samples) || body.audio_samples.length < 5) {
      return new Response(JSON.stringify({
        error: 'At least 5 audio samples required for voice training',
        code: 'INSUFFICIENT_SAMPLES',
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Create training session
    const session = await createTrainingSession(
      personaId,
      userId,
      'voice_model',
      {
        audio_samples: body.audio_samples,
        sample_texts: body.sample_texts || [],
      },
      env
    );

    // TODO: Trigger async voice training job

    return new Response(JSON.stringify({
      success: true,
      session,
      message: 'Voice training started',
    }), {
      status: 202, // Accepted
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error training voice:', error);

    if (error.message === 'Persona not found') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (error.message === 'Access denied') {
      return new Response(JSON.stringify({
        error: error.message,
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to start voice training',
      code: 'TRAINING_FAILED',
    }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * GET /api/personas/:personaId/training-status
 * Get training status
 */
export async function handleGetTrainingStatus(request, env, personaId) {
  try {
    const userId = request.headers.get('X-User-Id');
    if (!userId) {
      return new Response(JSON.stringify({ error: 'User ID required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Verify ownership
    const persona = await getPersonaById(personaId, env);
    if (!persona) {
      return new Response(JSON.stringify({
        error: 'Persona not found',
        code: 'NOT_FOUND',
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (persona.user_id !== userId) {
      return new Response(JSON.stringify({
        error: 'Access denied',
        code: 'FORBIDDEN',
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const sessions = await getTrainingStatus(personaId, env);

    return new Response(JSON.stringify({
      success: true,
      sessions,
    }), {
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting training status:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to get training status',
      code: 'STATUS_FAILED',
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
