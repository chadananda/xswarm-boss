/**
 * Team Permission Middleware
 *
 * Provides permission checks for team-based operations:
 * - Tier verification (Pro+ only)
 * - Team membership verification
 * - Role-based access control (owner, admin, member, viewer)
 * - Member limit enforcement
 */

import { createClient } from '@libsql/client';

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
 * Check if user has Pro+ tier (required for team features)
 *
 * @param {Object} user - User object from requireAuth
 * @throws {TeamPermissionError} If user doesn't have Pro+ tier
 */
export function checkTeamTier(user) {
  const proTiers = ['professional', 'enterprise', 'admin'];

  if (!proTiers.includes(user.subscription_tier)) {
    throw new TeamPermissionError(
      'Team features require Professional or Enterprise subscription tier',
      403
    );
  }
}

/**
 * Get team member record for user
 *
 * @param {string} teamId - Team ID
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object|null>} Team member record or null
 */
async function getTeamMember(teamId, userId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      SELECT * FROM team_members
      WHERE team_id = ? AND user_id = ?
    `,
    args: [teamId, userId],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return {
    id: result.rows[0].id,
    team_id: result.rows[0].team_id,
    user_id: result.rows[0].user_id,
    role: result.rows[0].role,
    invited_by: result.rows[0].invited_by,
    joined_at: result.rows[0].joined_at,
    invited_at: result.rows[0].invited_at,
  };
}

/**
 * Require team membership (any role)
 *
 * @param {string} teamId - Team ID
 * @param {Object} user - User object from requireAuth
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Team member record
 * @throws {TeamPermissionError} If user is not a team member
 */
export async function requireTeamMembership(teamId, user, env) {
  const member = await getTeamMember(teamId, user.id, env);

  if (!member) {
    throw new TeamPermissionError('You are not a member of this team', 403);
  }

  return member;
}

/**
 * Require team admin role (admin or owner)
 *
 * @param {string} teamId - Team ID
 * @param {Object} user - User object from requireAuth
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Team member record
 * @throws {TeamPermissionError} If user is not an admin or owner
 */
export async function requireTeamAdmin(teamId, user, env) {
  const member = await requireTeamMembership(teamId, user, env);

  if (member.role !== 'admin' && member.role !== 'owner') {
    throw new TeamPermissionError('This action requires admin or owner role', 403);
  }

  return member;
}

/**
 * Require team owner role
 *
 * @param {string} teamId - Team ID
 * @param {Object} user - User object from requireAuth
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Team member record
 * @throws {TeamPermissionError} If user is not the team owner
 */
export async function requireTeamOwner(teamId, user, env) {
  const member = await requireTeamMembership(teamId, user, env);

  if (member.role !== 'owner') {
    throw new TeamPermissionError('This action requires team owner role', 403);
  }

  return member;
}

/**
 * Check if team has reached member limit
 *
 * @param {string} teamId - Team ID
 * @param {Object} env - Environment variables
 * @returns {Promise<void>}
 * @throws {TeamPermissionError} If team has reached member limit
 */
export async function checkMemberLimit(teamId, env) {
  const db = getDbClient(env);

  // Get team with current member count
  const result = await db.execute({
    sql: `
      SELECT
        t.max_members,
        COUNT(tm.id) as current_members
      FROM teams t
      LEFT JOIN team_members tm ON t.id = tm.team_id
      WHERE t.id = ?
      GROUP BY t.id
    `,
    args: [teamId],
  });

  if (result.rows.length === 0) {
    throw new TeamPermissionError('Team not found', 404);
  }

  const team = result.rows[0];
  const maxMembers = Number(team.max_members);
  const currentMembers = Number(team.current_members);

  // -1 means unlimited
  if (maxMembers === -1) {
    return;
  }

  if (currentMembers >= maxMembers) {
    throw new TeamPermissionError(
      `Team has reached maximum member limit of ${maxMembers}`,
      403
    );
  }
}

/**
 * Get team with verification
 *
 * @param {string} teamId - Team ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Team record
 * @throws {TeamPermissionError} If team not found
 */
export async function getTeamOrFail(teamId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM teams WHERE id = ?',
    args: [teamId],
  });

  if (result.rows.length === 0) {
    throw new TeamPermissionError('Team not found', 404);
  }

  return {
    id: result.rows[0].id,
    name: result.rows[0].name,
    description: result.rows[0].description,
    owner_id: result.rows[0].owner_id,
    subscription_tier: result.rows[0].subscription_tier,
    max_members: result.rows[0].max_members,
    created_at: result.rows[0].created_at,
    updated_at: result.rows[0].updated_at,
  };
}

/**
 * Custom team permission error class
 */
export class TeamPermissionError extends Error {
  constructor(message, statusCode = 403) {
    super(message);
    this.name = 'TeamPermissionError';
    this.statusCode = statusCode;
  }
}

/**
 * Create JSON error response from TeamPermissionError
 *
 * @param {TeamPermissionError} error - Team permission error
 * @returns {Response} JSON error response
 */
export function createTeamErrorResponse(error) {
  return new Response(
    JSON.stringify({
      error: error.message,
    }),
    {
      status: error.statusCode || 403,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}
