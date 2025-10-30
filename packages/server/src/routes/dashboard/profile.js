/**
 * Dashboard Profile Management Endpoints
 *
 * GET /api/dashboard/profile - Get user profile
 * PUT /api/dashboard/profile - Update user profile
 *
 * Requires authentication.
 */

import { getUserById } from '../../lib/users.js';
import { createClient } from '@libsql/client';

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

export async function handleGetProfile(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const profile = await getUserById(user.id, env);

    // Remove sensitive fields
    delete profile.password_hash;
    delete profile.email_verification_token;
    delete profile.password_reset_token;

    return new Response(JSON.stringify(profile), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting profile:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function handleUpdateProfile(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const { name, persona, wake_word } = body;

    const db = getDbClient(env);
    const now = new Date().toISOString();

    // Build update query dynamically
    const updates = [];
    const args = [];

    if (name !== undefined) {
      updates.push('name = ?');
      args.push(name);
    }

    if (persona !== undefined) {
      updates.push('persona = ?');
      args.push(persona);
    }

    if (wake_word !== undefined) {
      updates.push('wake_word = ?');
      args.push(wake_word);
    }

    if (updates.length === 0) {
      return new Response(JSON.stringify({ error: 'No fields to update' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    updates.push('updated_at = ?');
    args.push(now);
    args.push(user.id);

    await db.execute({
      sql: `UPDATE users SET ${updates.join(', ')} WHERE id = ?`,
      args,
    });

    const updatedProfile = await getUserById(user.id, env);

    // Remove sensitive fields
    delete updatedProfile.password_hash;
    delete updatedProfile.email_verification_token;
    delete updatedProfile.password_reset_token;

    return new Response(JSON.stringify(updatedProfile), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error updating profile:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
