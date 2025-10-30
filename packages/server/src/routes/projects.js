/**
 * Project Management API Routes
 *
 * Comprehensive API layer for project management that bridges the tested
 * database schema with the Rust ProjectManager system.
 *
 * Handles:
 * - Project CRUD operations
 * - Task management
 * - Git integration
 * - Agent assignment and coordination
 * - Analytics and health monitoring
 * - Status reporting
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
 * Error response helper
 */
function errorResponse(message, code, status = 400, details = null) {
  const body = { error: message, code, status };
  if (details) body.details = details;
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Success response helper
 */
function successResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Validate project data
 */
function validateProject(data, isUpdate = false) {
  const errors = [];

  if (!isUpdate) {
    if (!data.name || data.name.length < 1 || data.name.length > 100) {
      errors.push('Name is required and must be 1-100 characters');
    }
    if (!data.path || data.path.length < 1) {
      errors.push('Path is required');
    }
  }

  if (data.priority !== undefined) {
    const priority = parseInt(data.priority);
    if (isNaN(priority) || priority < 1 || priority > 5) {
      errors.push('Priority must be between 1 and 5');
    }
  }

  if (data.progress_percentage !== undefined) {
    const progress = parseInt(data.progress_percentage);
    if (isNaN(progress) || progress < 0 || progress > 100) {
      errors.push('Progress must be between 0 and 100');
    }
  }

  if (data.status && !['active', 'paused', 'completed', 'blocked', 'archived'].includes(data.status)) {
    errors.push('Status must be one of: active, paused, completed, blocked, archived');
  }

  if (data.git_url && data.git_url.length > 0) {
    try {
      new URL(data.git_url);
    } catch {
      errors.push('Invalid Git URL format');
    }
  }

  return errors;
}

/**
 * Validate task data
 */
function validateTask(data, isUpdate = false) {
  const errors = [];

  if (!isUpdate && (!data.title || data.title.length < 1)) {
    errors.push('Title is required');
  }

  if (data.priority !== undefined) {
    const priority = parseInt(data.priority);
    if (isNaN(priority) || priority < 1 || priority > 5) {
      errors.push('Priority must be between 1 and 5');
    }
  }

  if (data.status && !['pending', 'in_progress', 'completed', 'blocked'].includes(data.status)) {
    errors.push('Status must be one of: pending, in_progress, completed, blocked');
  }

  if (data.estimated_hours !== undefined && data.estimated_hours !== null) {
    const hours = parseFloat(data.estimated_hours);
    if (isNaN(hours) || hours < 0) {
      errors.push('Estimated hours must be a non-negative number');
    }
  }

  if (data.actual_hours !== undefined && data.actual_hours !== null) {
    const hours = parseFloat(data.actual_hours);
    if (isNaN(hours) || hours < 0) {
      errors.push('Actual hours must be a non-negative number');
    }
  }

  return errors;
}

/**
 * Calculate project health score (matches Rust algorithm)
 */
function calculateHealthScore(project, tasks, commits) {
  let score = 0.5; // Base score

  // Progress factor (0.0 - 0.3)
  const progressFactor = (project.progress_percentage / 100) * 0.3;
  score += progressFactor;

  // Activity factor (0.0 - 0.2)
  if (project.last_activity) {
    const daysSinceActivity = (Date.now() - new Date(project.last_activity).getTime()) / (1000 * 60 * 60 * 24);
    const activityFactor = Math.max(0, 0.2 - (daysSinceActivity / 30) * 0.2);
    score += activityFactor;
  }

  // Task completion factor (0.0 - 0.3)
  if (tasks.length > 0) {
    const completedTasks = tasks.filter(t => t.status === 'completed').length;
    const taskFactor = (completedTasks / tasks.length) * 0.3;
    score += taskFactor;
  }

  // Blocked tasks penalty (-0.2)
  const blockedTasks = tasks.filter(t => t.status === 'blocked').length;
  if (blockedTasks > 0) {
    score -= Math.min(0.2, blockedTasks * 0.05);
  }

  // Recent commits bonus (0.0 - 0.2)
  if (commits.length > 0) {
    const recentCommits = commits.filter(c => {
      const daysSinceCommit = (Date.now() - new Date(c.committed_at).getTime()) / (1000 * 60 * 60 * 24);
      return daysSinceCommit <= 7;
    });
    const commitFactor = Math.min(0.2, (recentCommits.length / 10) * 0.2);
    score += commitFactor;
  }

  return Math.max(0, Math.min(1, score));
}

// ============================================================================
// PROJECT CRUD OPERATIONS
// ============================================================================

/**
 * Create new project
 * POST /api/projects
 */
export async function createProject(request, env) {
  try {
    const body = await request.json();
    const { user_id, name, description, path, git_url, priority = 3 } = body;

    // Validate required fields
    if (!user_id) {
      return errorResponse('user_id is required', 'MISSING_USER_ID', 400);
    }

    const validationErrors = validateProject(body);
    if (validationErrors.length > 0) {
      return errorResponse('Validation failed', 'VALIDATION_ERROR', 400, validationErrors);
    }

    const db = getDbClient(env);
    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        INSERT INTO projects (
          id, user_id, name, description, path, git_url,
          status, priority, progress_percentage, last_activity,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
      args: [
        id,
        user_id,
        name,
        description || null,
        path,
        git_url || null,
        'active',
        priority,
        0,
        now,
        now,
        now,
      ],
    });

    return successResponse(formatProject(result.rows[0]), 201);
  } catch (error) {
    console.error('Error creating project:', error);
    return errorResponse('Failed to create project', 'CREATE_FAILED', 500);
  }
}

/**
 * List all projects with filtering
 * GET /api/projects?user_id=xxx&status=active&limit=50&offset=0
 */
export async function listProjects(request, env) {
  try {
    const url = new URL(request.url);
    const user_id = url.searchParams.get('user_id');
    const status = url.searchParams.get('status');
    const assigned_agent = url.searchParams.get('assigned_agent');
    const limit = parseInt(url.searchParams.get('limit')) || 50;
    const offset = parseInt(url.searchParams.get('offset')) || 0;

    const db = getDbClient(env);

    // Build dynamic query
    let sql = 'SELECT * FROM projects WHERE 1=1';
    const args = [];

    if (user_id) {
      sql += ' AND user_id = ?';
      args.push(user_id);
    }

    if (status) {
      sql += ' AND status = ?';
      args.push(status);
    }

    if (assigned_agent) {
      sql += ' AND assigned_agent = ?';
      args.push(assigned_agent);
    }

    sql += ' ORDER BY priority ASC, last_activity DESC LIMIT ? OFFSET ?';
    args.push(limit, offset);

    const result = await db.execute({ sql, args });

    return successResponse({
      projects: result.rows.map(formatProject),
      total: result.rows.length,
      limit,
      offset,
    });
  } catch (error) {
    console.error('Error listing projects:', error);
    return errorResponse('Failed to list projects', 'LIST_FAILED', 500);
  }
}

/**
 * Get specific project details
 * GET /api/projects/:id
 */
export async function getProject(request, env, projectId) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM projects WHERE id = ?',
      args: [projectId],
    });

    if (result.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    return successResponse(formatProject(result.rows[0]));
  } catch (error) {
    console.error('Error getting project:', error);
    return errorResponse('Failed to get project', 'GET_FAILED', 500);
  }
}

/**
 * Update project
 * PUT /api/projects/:id
 */
export async function updateProject(request, env, projectId) {
  try {
    const body = await request.json();

    const validationErrors = validateProject(body, true);
    if (validationErrors.length > 0) {
      return errorResponse('Validation failed', 'VALIDATION_ERROR', 400, validationErrors);
    }

    const db = getDbClient(env);

    // Build dynamic update query
    const updates = [];
    const args = [];

    const allowedFields = [
      'name', 'description', 'path', 'git_url', 'status',
      'assigned_agent', 'priority', 'progress_percentage'
    ];

    for (const field of allowedFields) {
      if (body[field] !== undefined) {
        updates.push(`${field} = ?`);
        args.push(body[field]);
      }
    }

    if (updates.length === 0) {
      return errorResponse('No fields to update', 'NO_UPDATES', 400);
    }

    args.push(new Date().toISOString());
    args.push(projectId);

    const sql = `UPDATE projects SET ${updates.join(', ')}, updated_at = ? WHERE id = ? RETURNING *`;
    const result = await db.execute({ sql, args });

    if (result.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    return successResponse(formatProject(result.rows[0]));
  } catch (error) {
    console.error('Error updating project:', error);
    return errorResponse('Failed to update project', 'UPDATE_FAILED', 500);
  }
}

/**
 * Delete project
 * DELETE /api/projects/:id
 */
export async function deleteProject(request, env, projectId) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'DELETE FROM projects WHERE id = ? RETURNING id',
      args: [projectId],
    });

    if (result.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    return successResponse({ id: projectId, deleted: true });
  } catch (error) {
    console.error('Error deleting project:', error);
    return errorResponse('Failed to delete project', 'DELETE_FAILED', 500);
  }
}

// ============================================================================
// TASK MANAGEMENT
// ============================================================================

/**
 * Create task in project
 * POST /api/projects/:id/tasks
 */
export async function createTask(request, env, projectId) {
  try {
    const body = await request.json();
    const {
      title,
      description,
      assigned_to,
      priority = 3,
      estimated_hours,
      actual_hours,
    } = body;

    const validationErrors = validateTask(body);
    if (validationErrors.length > 0) {
      return errorResponse('Validation failed', 'VALIDATION_ERROR', 400, validationErrors);
    }

    const db = getDbClient(env);

    // Verify project exists
    const projectCheck = await db.execute({
      sql: 'SELECT id FROM projects WHERE id = ?',
      args: [projectId],
    });

    if (projectCheck.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        INSERT INTO project_tasks (
          id, project_id, title, description, status,
          assigned_to, priority, estimated_hours, actual_hours,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
      args: [
        id,
        projectId,
        title,
        description || null,
        'pending',
        assigned_to || null,
        priority,
        estimated_hours || null,
        actual_hours || null,
        now,
        now,
      ],
    });

    return successResponse(formatTask(result.rows[0]), 201);
  } catch (error) {
    console.error('Error creating task:', error);
    return errorResponse('Failed to create task', 'CREATE_FAILED', 500);
  }
}

/**
 * List project tasks
 * GET /api/projects/:id/tasks?status=pending
 */
export async function listTasks(request, env, projectId) {
  try {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');

    const db = getDbClient(env);

    let sql = 'SELECT * FROM project_tasks WHERE project_id = ?';
    const args = [projectId];

    if (status) {
      sql += ' AND status = ?';
      args.push(status);
    }

    sql += ' ORDER BY priority ASC, created_at ASC';

    const result = await db.execute({ sql, args });

    return successResponse({
      tasks: result.rows.map(formatTask),
      total: result.rows.length,
    });
  } catch (error) {
    console.error('Error listing tasks:', error);
    return errorResponse('Failed to list tasks', 'LIST_FAILED', 500);
  }
}

/**
 * Update task
 * PUT /api/projects/:id/tasks/:taskId
 */
export async function updateTask(request, env, projectId, taskId) {
  try {
    const body = await request.json();

    const validationErrors = validateTask(body, true);
    if (validationErrors.length > 0) {
      return errorResponse('Validation failed', 'VALIDATION_ERROR', 400, validationErrors);
    }

    const db = getDbClient(env);

    // Build dynamic update query
    const updates = [];
    const args = [];

    const allowedFields = [
      'title', 'description', 'status', 'assigned_to',
      'priority', 'estimated_hours', 'actual_hours'
    ];

    for (const field of allowedFields) {
      if (body[field] !== undefined) {
        updates.push(`${field} = ?`);
        args.push(body[field]);
      }
    }

    if (updates.length === 0) {
      return errorResponse('No fields to update', 'NO_UPDATES', 400);
    }

    args.push(taskId);
    args.push(projectId);

    const sql = `
      UPDATE project_tasks
      SET ${updates.join(', ')}
      WHERE id = ? AND project_id = ?
      RETURNING *
    `;

    const result = await db.execute({ sql, args });

    if (result.rows.length === 0) {
      return errorResponse('Task not found', 'TASK_NOT_FOUND', 404);
    }

    return successResponse(formatTask(result.rows[0]));
  } catch (error) {
    console.error('Error updating task:', error);
    return errorResponse('Failed to update task', 'UPDATE_FAILED', 500);
  }
}

/**
 * Delete task
 * DELETE /api/projects/:id/tasks/:taskId
 */
export async function deleteTask(request, env, projectId, taskId) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'DELETE FROM project_tasks WHERE id = ? AND project_id = ? RETURNING id',
      args: [taskId, projectId],
    });

    if (result.rows.length === 0) {
      return errorResponse('Task not found', 'TASK_NOT_FOUND', 404);
    }

    return successResponse({ id: taskId, deleted: true });
  } catch (error) {
    console.error('Error deleting task:', error);
    return errorResponse('Failed to delete task', 'DELETE_FAILED', 500);
  }
}

/**
 * Mark task as complete
 * POST /api/projects/:id/tasks/:taskId/complete
 */
export async function completeTask(request, env, projectId, taskId) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: `
        UPDATE project_tasks
        SET status = 'completed'
        WHERE id = ? AND project_id = ?
        RETURNING *
      `,
      args: [taskId, projectId],
    });

    if (result.rows.length === 0) {
      return errorResponse('Task not found', 'TASK_NOT_FOUND', 404);
    }

    return successResponse(formatTask(result.rows[0]));
  } catch (error) {
    console.error('Error completing task:', error);
    return errorResponse('Failed to complete task', 'COMPLETE_FAILED', 500);
  }
}

// ============================================================================
// GIT INTEGRATION
// ============================================================================

/**
 * Sync project with Git repository
 * POST /api/projects/:id/sync-git
 */
export async function syncGit(request, env, projectId) {
  try {
    const db = getDbClient(env);

    // Get project details
    const projectResult = await db.execute({
      sql: 'SELECT * FROM projects WHERE id = ?',
      args: [projectId],
    });

    if (projectResult.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    const project = projectResult.rows[0];

    if (!project.path) {
      return errorResponse('Project path not set', 'NO_PATH', 400);
    }

    // Get recent commits from Git
    const commits = await getGitCommits(project.path, 10);

    // Store commits in database
    const now = new Date().toISOString();
    let insertedCount = 0;

    for (const commit of commits) {
      try {
        await db.execute({
          sql: `
            INSERT INTO project_commits (
              id, project_id, commit_hash, commit_message,
              author, committed_at, files_changed, lines_added, lines_removed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (project_id, commit_hash) DO NOTHING
          `,
          args: [
            crypto.randomUUID(),
            projectId,
            commit.hash,
            commit.message,
            commit.author,
            commit.date,
            commit.files_changed || 0,
            commit.lines_added || 0,
            commit.lines_removed || 0,
          ],
        });
        insertedCount++;
      } catch (err) {
        console.warn('Failed to insert commit:', commit.hash, err.message);
      }
    }

    return successResponse({
      synced: true,
      commits_processed: commits.length,
      commits_inserted: insertedCount,
    });
  } catch (error) {
    console.error('Error syncing Git:', error);
    return errorResponse('Failed to sync Git repository', 'SYNC_FAILED', 500);
  }
}

/**
 * Get Git commits from repository
 */
async function getGitCommits(repoPath, limit = 10) {
  try {
    // Note: This runs in Cloudflare Workers, so we can't actually exec git
    // In production, this would need to be handled by the Rust supervisor
    // For now, return empty array and log a warning
    console.warn('Git operations not supported in Cloudflare Workers environment');
    console.warn('Git sync should be handled by Rust supervisor');
    return [];

    // Keeping this code for reference when implementing in Rust:
    /*
    const { stdout } = await execAsync(
      `cd "${repoPath}" && git log -${limit} --pretty=format:"%H|%an|%ae|%aI|%s" --numstat`,
      { maxBuffer: 1024 * 1024 }
    );

    const commits = [];
    const lines = stdout.trim().split('\n');

    let currentCommit = null;
    for (const line of lines) {
      if (line.includes('|')) {
        const [hash, author, email, date, message] = line.split('|');
        currentCommit = {
          hash,
          author: `${author} <${email}>`,
          date,
          message,
          files_changed: 0,
          lines_added: 0,
          lines_removed: 0,
        };
        commits.push(currentCommit);
      } else if (currentCommit && line.trim()) {
        const [added, removed] = line.trim().split('\t');
        currentCommit.files_changed++;
        currentCommit.lines_added += parseInt(added) || 0;
        currentCommit.lines_removed += parseInt(removed) || 0;
      }
    }

    return commits;
    */
  } catch (error) {
    console.error('Error getting Git commits:', error);
    return [];
  }
}

// ============================================================================
// AGENT MANAGEMENT
// ============================================================================

/**
 * Assign project to agent
 * POST /api/projects/:id/assign
 */
export async function assignAgent(request, env, projectId) {
  try {
    const body = await request.json();
    const { agent_name, cost_budget } = body;

    if (!agent_name || agent_name.trim().length === 0) {
      return errorResponse('agent_name is required', 'MISSING_AGENT_NAME', 400);
    }

    const db = getDbClient(env);

    // Update project
    await db.execute({
      sql: 'UPDATE projects SET assigned_agent = ? WHERE id = ?',
      args: [agent_name, projectId],
    });

    // Create agent assignment record
    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        INSERT INTO agent_assignments (
          id, project_id, agent_name, status,
          cost_budget, cost_used, assigned_at, last_activity
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
      args: [
        id,
        projectId,
        agent_name,
        'active',
        cost_budget || null,
        0.0,
        now,
        now,
      ],
    });

    return successResponse(formatAssignment(result.rows[0]));
  } catch (error) {
    console.error('Error assigning agent:', error);
    return errorResponse('Failed to assign agent', 'ASSIGN_FAILED', 500);
  }
}

/**
 * Unassign project from agent
 * DELETE /api/projects/:id/assign
 */
export async function unassignAgent(request, env, projectId) {
  try {
    const db = getDbClient(env);

    // Update project
    await db.execute({
      sql: 'UPDATE projects SET assigned_agent = NULL WHERE id = ?',
      args: [projectId],
    });

    // Mark assignments as inactive
    await db.execute({
      sql: `UPDATE agent_assignments SET status = 'inactive' WHERE project_id = ? AND status = 'active'`,
      args: [projectId],
    });

    return successResponse({ unassigned: true });
  } catch (error) {
    console.error('Error unassigning agent:', error);
    return errorResponse('Failed to unassign agent', 'UNASSIGN_FAILED', 500);
  }
}

/**
 * Get agent workload summary
 * GET /api/agents/workload
 */
export async function getAgentWorkload(request, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM agent_workload',
      args: [],
    });

    return successResponse({
      workload: result.rows.map(formatWorkload),
    });
  } catch (error) {
    console.error('Error getting agent workload:', error);
    return errorResponse('Failed to get agent workload', 'WORKLOAD_FAILED', 500);
  }
}

/**
 * Track agent costs
 * POST /api/agents/:name/costs
 */
export async function trackAgentCost(request, env, agentName) {
  try {
    const body = await request.json();
    const { project_id, cost } = body;

    if (!project_id || cost === undefined) {
      return errorResponse('project_id and cost are required', 'MISSING_FIELDS', 400);
    }

    const costValue = parseFloat(cost);
    if (isNaN(costValue) || costValue < 0) {
      return errorResponse('Cost must be a non-negative number', 'INVALID_COST', 400);
    }

    const db = getDbClient(env);
    const now = new Date().toISOString();

    // Update agent assignment cost
    const result = await db.execute({
      sql: `
        UPDATE agent_assignments
        SET cost_used = cost_used + ?, last_activity = ?
        WHERE project_id = ? AND agent_name = ? AND status = 'active'
        RETURNING *
      `,
      args: [costValue, now, project_id, agentName],
    });

    if (result.rows.length === 0) {
      return errorResponse('Active assignment not found', 'ASSIGNMENT_NOT_FOUND', 404);
    }

    return successResponse(formatAssignment(result.rows[0]));
  } catch (error) {
    console.error('Error tracking agent cost:', error);
    return errorResponse('Failed to track agent cost', 'TRACK_COST_FAILED', 500);
  }
}

// ============================================================================
// ANALYTICS AND REPORTING
// ============================================================================

/**
 * Get project analytics dashboard
 * GET /api/projects/analytics?user_id=xxx
 */
export async function getAnalytics(request, env) {
  try {
    const url = new URL(request.url);
    const user_id = url.searchParams.get('user_id');

    const db = getDbClient(env);

    let whereClause = '';
    const args = [];

    if (user_id) {
      whereClause = 'WHERE user_id = ?';
      args.push(user_id);
    }

    const result = await db.execute({
      sql: `SELECT * FROM project_summary ${whereClause}`,
      args,
    });

    // Aggregate analytics
    const projects = result.rows;
    const analytics = {
      total_projects: projects.length,
      active_projects: projects.filter(p => p.status === 'active').length,
      completed_projects: projects.filter(p => p.status === 'completed').length,
      blocked_projects: projects.filter(p => p.status === 'blocked').length,
      total_tasks: projects.reduce((sum, p) => sum + (p.total_tasks || 0), 0),
      completed_tasks: projects.reduce((sum, p) => sum + (p.completed_tasks || 0), 0),
      in_progress_tasks: projects.reduce((sum, p) => sum + (p.in_progress_tasks || 0), 0),
      blocked_tasks: projects.reduce((sum, p) => sum + (p.blocked_tasks || 0), 0),
      total_commits: projects.reduce((sum, p) => sum + (p.total_commits || 0), 0),
      average_progress: projects.length > 0
        ? projects.reduce((sum, p) => sum + p.progress_percentage, 0) / projects.length
        : 0,
    };

    return successResponse(analytics);
  } catch (error) {
    console.error('Error getting analytics:', error);
    return errorResponse('Failed to get analytics', 'ANALYTICS_FAILED', 500);
  }
}

/**
 * Get stalled projects
 * GET /api/projects/stalled
 */
export async function getStalledProjects(request, env) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM stalled_projects',
      args: [],
    });

    return successResponse({
      stalled_projects: result.rows.map(p => ({
        ...formatProject(p),
        days_stalled: p.days_stalled,
      })),
    });
  } catch (error) {
    console.error('Error getting stalled projects:', error);
    return errorResponse('Failed to get stalled projects', 'STALLED_FAILED', 500);
  }
}

/**
 * Get detailed project status report
 * GET /api/projects/:id/status
 */
export async function getProjectStatus(request, env, projectId) {
  try {
    const db = getDbClient(env);

    // Get project
    const projectResult = await db.execute({
      sql: 'SELECT * FROM projects WHERE id = ?',
      args: [projectId],
    });

    if (projectResult.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    const project = projectResult.rows[0];

    // Get tasks
    const tasksResult = await db.execute({
      sql: 'SELECT * FROM project_tasks WHERE project_id = ?',
      args: [projectId],
    });

    const tasks = tasksResult.rows;

    // Get recent commits
    const commitsResult = await db.execute({
      sql: `
        SELECT * FROM project_commits
        WHERE project_id = ?
        ORDER BY committed_at DESC
        LIMIT 10
      `,
      args: [projectId],
    });

    const commits = commitsResult.rows;

    // Get agent assignment
    const assignmentResult = await db.execute({
      sql: `
        SELECT * FROM agent_assignments
        WHERE project_id = ? AND status = 'active'
        ORDER BY assigned_at DESC
        LIMIT 1
      `,
      args: [projectId],
    });

    const assignment = assignmentResult.rows[0] || null;

    // Calculate health score
    const healthScore = calculateHealthScore(project, tasks, commits);

    // Build status report
    const status = {
      project: {
        ...formatProject(project),
        health_score: healthScore,
      },
      tasks: {
        total: tasks.length,
        completed: tasks.filter(t => t.status === 'completed').length,
        in_progress: tasks.filter(t => t.status === 'in_progress').length,
        pending: tasks.filter(t => t.status === 'pending').length,
        blocked: tasks.filter(t => t.status === 'blocked').length,
      },
      git: {
        total_commits: commits.length,
        last_commit: commits[0] ? {
          hash: commits[0].commit_hash,
          message: commits[0].commit_message,
          author: commits[0].author,
          date: commits[0].committed_at,
        } : null,
        commits_today: commits.filter(c => {
          const commitDate = new Date(c.committed_at);
          const today = new Date();
          return commitDate.toDateString() === today.toDateString();
        }).length,
      },
      agent: assignment ? {
        assigned_to: assignment.agent_name,
        cost_used: assignment.cost_used,
        cost_budget: assignment.cost_budget,
        last_activity: assignment.last_activity,
      } : null,
    };

    return successResponse(status);
  } catch (error) {
    console.error('Error getting project status:', error);
    return errorResponse('Failed to get project status', 'STATUS_FAILED', 500);
  }
}

/**
 * Get project health score
 * GET /api/projects/:id/health
 */
export async function getProjectHealth(request, env, projectId) {
  try {
    const db = getDbClient(env);

    // Get project
    const projectResult = await db.execute({
      sql: 'SELECT * FROM projects WHERE id = ?',
      args: [projectId],
    });

    if (projectResult.rows.length === 0) {
      return errorResponse('Project not found', 'PROJECT_NOT_FOUND', 404);
    }

    const project = projectResult.rows[0];

    // Get tasks
    const tasksResult = await db.execute({
      sql: 'SELECT * FROM project_tasks WHERE project_id = ?',
      args: [projectId],
    });

    // Get commits
    const commitsResult = await db.execute({
      sql: 'SELECT * FROM project_commits WHERE project_id = ?',
      args: [projectId],
    });

    const healthScore = calculateHealthScore(
      project,
      tasksResult.rows,
      commitsResult.rows
    );

    return successResponse({
      project_id: projectId,
      health_score: healthScore,
      status: project.status,
      progress: project.progress_percentage,
      last_activity: project.last_activity,
    });
  } catch (error) {
    console.error('Error getting project health:', error);
    return errorResponse('Failed to get project health', 'HEALTH_FAILED', 500);
  }
}

// ============================================================================
// FORMATTING HELPERS
// ============================================================================

function formatProject(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    name: row.name,
    description: row.description,
    path: row.path,
    git_url: row.git_url,
    status: row.status,
    assigned_agent: row.assigned_agent,
    priority: row.priority,
    progress_percentage: row.progress_percentage,
    last_activity: row.last_activity,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

function formatTask(row) {
  return {
    id: row.id,
    project_id: row.project_id,
    title: row.title,
    description: row.description,
    status: row.status,
    assigned_to: row.assigned_to,
    priority: row.priority,
    estimated_hours: row.estimated_hours,
    actual_hours: row.actual_hours,
    created_at: row.created_at,
    updated_at: row.updated_at,
    completed_at: row.completed_at,
  };
}

function formatAssignment(row) {
  return {
    id: row.id,
    project_id: row.project_id,
    agent_name: row.agent_name,
    status: row.status,
    cost_budget: row.cost_budget,
    cost_used: row.cost_used,
    assigned_at: row.assigned_at,
    last_activity: row.last_activity,
  };
}

function formatWorkload(row) {
  return {
    agent_name: row.assigned_agent,
    project_count: row.project_count,
    active_projects: row.active_projects,
    completed_projects: row.completed_projects,
    avg_progress: row.avg_progress,
    last_activity: row.last_agent_activity,
  };
}
