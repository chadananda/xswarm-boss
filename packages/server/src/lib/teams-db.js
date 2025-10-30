/**
 * Team Database Operations
 *
 * Provides database operations for team management:
 * - Team CRUD operations
 * - Team member management
 * - Team invitation management
 */

import { createClient } from '@libsql/client';
import crypto from 'crypto';

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

// =============================================================================
// TEAM OPERATIONS
// =============================================================================

/**
 * Create a new team
 *
 * @param {Object} teamData - Team data
 * @param {string} teamData.name - Team name
 * @param {string} teamData.description - Team description (optional)
 * @param {string} teamData.owner_id - User ID of team owner
 * @param {string} teamData.subscription_tier - Subscription tier (ai_project_manager, ai_cto)
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Created team record
 */
export async function createTeam(teamData, env) {
  const db = getDbClient(env);
  const teamId = crypto.randomUUID();
  const memberId = crypto.randomUUID();
  const now = new Date().toISOString();

  // Determine max_members based on tier
  const maxMembers = teamData.subscription_tier === 'ai_cto' ? -1 : 10;

  try {
    // Begin transaction - create team and add owner as member
    await db.batch([
      {
        sql: `
          INSERT INTO teams (id, name, description, owner_id, subscription_tier, max_members, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `,
        args: [
          teamId,
          teamData.name,
          teamData.description || null,
          teamData.owner_id,
          teamData.subscription_tier,
          maxMembers,
          now,
          now,
        ],
      },
      {
        sql: `
          INSERT INTO team_members (id, team_id, user_id, role, joined_at)
          VALUES (?, ?, ?, 'owner', ?)
        `,
        args: [memberId, teamId, teamData.owner_id, now],
      },
    ]);

    // Fetch and return the created team
    return await getTeamById(teamId, env);
  } catch (error) {
    console.error('Failed to create team:', error);
    throw new Error('Failed to create team');
  }
}

/**
 * Get team by ID
 *
 * @param {string} teamId - Team ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object|null>} Team record or null
 */
export async function getTeamById(teamId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM teams WHERE id = ?',
    args: [teamId],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return formatTeamRecord(result.rows[0]);
}

/**
 * Update team
 *
 * @param {string} teamId - Team ID
 * @param {Object} updates - Fields to update
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Updated team record
 */
export async function updateTeam(teamId, updates, env) {
  const db = getDbClient(env);
  const now = new Date().toISOString();

  const fields = [];
  const args = [];

  if (updates.name !== undefined) {
    fields.push('name = ?');
    args.push(updates.name);
  }

  if (updates.description !== undefined) {
    fields.push('description = ?');
    args.push(updates.description);
  }

  if (fields.length === 0) {
    throw new Error('No fields to update');
  }

  fields.push('updated_at = ?');
  args.push(now);
  args.push(teamId);

  await db.execute({
    sql: `UPDATE teams SET ${fields.join(', ')} WHERE id = ?`,
    args,
  });

  return await getTeamById(teamId, env);
}

/**
 * Delete team
 *
 * @param {string} teamId - Team ID
 * @param {Object} env - Environment variables
 */
export async function deleteTeam(teamId, env) {
  const db = getDbClient(env);

  await db.execute({
    sql: 'DELETE FROM teams WHERE id = ?',
    args: [teamId],
  });
}

/**
 * List teams for a user
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Array of team records with user's role
 */
export async function listUserTeams(userId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      SELECT
        t.*,
        tm.role as user_role,
        COUNT(DISTINCT tm_all.id) as member_count
      FROM teams t
      JOIN team_members tm ON t.id = tm.team_id
      LEFT JOIN team_members tm_all ON t.id = tm_all.team_id
      WHERE tm.user_id = ?
      GROUP BY t.id
      ORDER BY t.created_at DESC
    `,
    args: [userId],
  });

  return result.rows.map((row) => ({
    ...formatTeamRecord(row),
    user_role: row.user_role,
    member_count: Number(row.member_count),
  }));
}

// =============================================================================
// TEAM MEMBER OPERATIONS
// =============================================================================

/**
 * Add team member
 *
 * @param {Object} memberData - Member data
 * @param {string} memberData.team_id - Team ID
 * @param {string} memberData.user_id - User ID
 * @param {string} memberData.role - Member role
 * @param {string} memberData.invited_by - User ID of inviter (optional)
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Created member record
 */
export async function addTeamMember(memberData, env) {
  const db = getDbClient(env);
  const memberId = crypto.randomUUID();
  const now = new Date().toISOString();

  await db.execute({
    sql: `
      INSERT INTO team_members (id, team_id, user_id, role, invited_by, joined_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `,
    args: [
      memberId,
      memberData.team_id,
      memberData.user_id,
      memberData.role,
      memberData.invited_by || null,
      now,
    ],
  });

  return await getTeamMemberById(memberId, env);
}

/**
 * Remove team member
 *
 * @param {string} teamId - Team ID
 * @param {string} userId - User ID to remove
 * @param {Object} env - Environment variables
 */
export async function removeTeamMember(teamId, userId, env) {
  const db = getDbClient(env);

  await db.execute({
    sql: 'DELETE FROM team_members WHERE team_id = ? AND user_id = ?',
    args: [teamId, userId],
  });
}

/**
 * Update member role
 *
 * @param {string} teamId - Team ID
 * @param {string} userId - User ID
 * @param {string} newRole - New role
 * @param {Object} env - Environment variables
 */
export async function updateMemberRole(teamId, userId, newRole, env) {
  const db = getDbClient(env);

  await db.execute({
    sql: 'UPDATE team_members SET role = ? WHERE team_id = ? AND user_id = ?',
    args: [newRole, teamId, userId],
  });
}

/**
 * Get team members
 *
 * @param {string} teamId - Team ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Array of member records with user details
 */
export async function getTeamMembers(teamId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: `
      SELECT
        tm.*,
        u.name as user_name,
        u.email as user_email
      FROM team_members tm
      JOIN users u ON tm.user_id = u.id
      WHERE tm.team_id = ?
      ORDER BY
        CASE tm.role
          WHEN 'owner' THEN 1
          WHEN 'admin' THEN 2
          WHEN 'member' THEN 3
          WHEN 'viewer' THEN 4
        END,
        tm.joined_at ASC
    `,
    args: [teamId],
  });

  return result.rows.map((row) => ({
    id: row.id,
    team_id: row.team_id,
    user_id: row.user_id,
    user_name: row.user_name,
    user_email: row.user_email,
    role: row.role,
    invited_by: row.invited_by,
    joined_at: row.joined_at,
    invited_at: row.invited_at,
  }));
}

/**
 * Get team member by ID
 *
 * @param {string} memberId - Member ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object|null>} Member record or null
 */
async function getTeamMemberById(memberId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM team_members WHERE id = ?',
    args: [memberId],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return formatMemberRecord(result.rows[0]);
}

// =============================================================================
// TEAM INVITATION OPERATIONS
// =============================================================================

/**
 * Create team invitation
 *
 * @param {Object} invitationData - Invitation data
 * @param {string} invitationData.team_id - Team ID
 * @param {string} invitationData.email - Invitee email
 * @param {string} invitationData.role - Intended role
 * @param {string} invitationData.created_by - User ID of inviter
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} Created invitation record
 */
export async function createInvitation(invitationData, env) {
  const db = getDbClient(env);
  const invitationId = crypto.randomUUID();
  const token = crypto.randomBytes(32).toString('hex');
  const now = new Date();
  const expiresAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000); // 7 days

  await db.execute({
    sql: `
      INSERT INTO team_invitations (id, team_id, email, role, token, expires_at, created_by, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `,
    args: [
      invitationId,
      invitationData.team_id,
      invitationData.email.toLowerCase(),
      invitationData.role,
      token,
      expiresAt.toISOString(),
      invitationData.created_by,
      now.toISOString(),
    ],
  });

  return await getInvitationById(invitationId, env);
}

/**
 * Get invitation by token
 *
 * @param {string} token - Invitation token
 * @param {Object} env - Environment variables
 * @returns {Promise<Object|null>} Invitation record or null if not found/expired
 */
export async function getInvitationByToken(token, env) {
  const db = getDbClient(env);
  const now = new Date().toISOString();

  const result = await db.execute({
    sql: `
      SELECT * FROM team_invitations
      WHERE token = ? AND expires_at > ?
    `,
    args: [token, now],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return formatInvitationRecord(result.rows[0]);
}

/**
 * Delete invitation
 *
 * @param {string} invitationId - Invitation ID
 * @param {Object} env - Environment variables
 */
export async function deleteInvitation(invitationId, env) {
  const db = getDbClient(env);

  await db.execute({
    sql: 'DELETE FROM team_invitations WHERE id = ?',
    args: [invitationId],
  });
}

/**
 * List team invitations
 *
 * @param {string} teamId - Team ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Array>} Array of invitation records
 */
export async function listTeamInvitations(teamId, env) {
  const db = getDbClient(env);
  const now = new Date().toISOString();

  const result = await db.execute({
    sql: `
      SELECT
        ti.*,
        u.name as created_by_name
      FROM team_invitations ti
      JOIN users u ON ti.created_by = u.id
      WHERE ti.team_id = ? AND ti.expires_at > ?
      ORDER BY ti.created_at DESC
    `,
    args: [teamId, now],
  });

  return result.rows.map((row) => ({
    ...formatInvitationRecord(row),
    created_by_name: row.created_by_name,
  }));
}

/**
 * Get invitation by ID
 *
 * @param {string} invitationId - Invitation ID
 * @param {Object} env - Environment variables
 * @returns {Promise<Object|null>} Invitation record or null
 */
async function getInvitationById(invitationId, env) {
  const db = getDbClient(env);

  const result = await db.execute({
    sql: 'SELECT * FROM team_invitations WHERE id = ?',
    args: [invitationId],
  });

  if (result.rows.length === 0) {
    return null;
  }

  return formatInvitationRecord(result.rows[0]);
}

// =============================================================================
// FORMATTING HELPERS
// =============================================================================

/**
 * Format team database record
 */
function formatTeamRecord(row) {
  return {
    id: row.id,
    name: row.name,
    description: row.description,
    owner_id: row.owner_id,
    subscription_tier: row.subscription_tier,
    max_members: Number(row.max_members),
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

/**
 * Format member database record
 */
function formatMemberRecord(row) {
  return {
    id: row.id,
    team_id: row.team_id,
    user_id: row.user_id,
    role: row.role,
    invited_by: row.invited_by,
    joined_at: row.joined_at,
    invited_at: row.invited_at,
  };
}

/**
 * Format invitation database record
 */
function formatInvitationRecord(row) {
  return {
    id: row.id,
    team_id: row.team_id,
    email: row.email,
    role: row.role,
    token: row.token,
    expires_at: row.expires_at,
    created_by: row.created_by,
    created_at: row.created_at,
  };
}
