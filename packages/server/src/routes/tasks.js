/**
 * Task Management API Routes
 *
 * Voice-first task management with natural language support
 * Features:
 * - Natural language task creation
 * - Smart scheduling and reminders
 * - Voice-optimized queries
 * - Recurring tasks
 * - Conflict detection
 */

import { requireAuth } from '../middleware/auth-middleware.js';
import { checkFeatureAccess } from '../lib/features.js';
import { TaskSystem } from '../lib/tasks/mod.js';

/**
 * Register task management routes
 */
export function registerTaskRoutes(app, db) {
  const tasks = new TaskSystem(db);

  // =============================================================================
  // TASK CREATION
  // =============================================================================

  /**
   * Create task from voice/text input
   * POST /api/tasks/voice
   *
   * Body: { input: "Remind me to call John tomorrow at 2pm" }
   */
  app.post('/api/tasks/voice', requireAuth(db), async (req, res) => {
    try {
      const { input } = req.body;

      if (!input || input.trim().length === 0) {
        return res.status(400).json({
          error: 'Voice input is required'
        });
      }

      // Check if user has task management feature
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher',
          upgrade: {
            feature: 'task_management',
            availableIn: ['personal', 'professional', 'enterprise']
          }
        });
      }

      const task = await tasks.createTaskFromVoice(req.user.id, input);

      res.status(201).json({
        success: true,
        task,
        message: `Created task: "${task.title}"`,
        conflicts: task.hasConflicts ? task.conflicts : undefined
      });
    } catch (error) {
      console.error('Error creating task:', error);
      res.status(400).json({ error: error.message });
    }
  });

  /**
   * Create task with structured data
   * POST /api/tasks
   */
  app.post('/api/tasks', requireAuth(db), async (req, res) => {
    try {
      const taskData = req.body;

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const task = await tasks.manager.createTask(req.user.id, taskData);

      res.status(201).json({
        success: true,
        task
      });
    } catch (error) {
      console.error('Error creating task:', error);
      res.status(400).json({ error: error.message });
    }
  });

  // =============================================================================
  // TASK QUERIES
  // =============================================================================

  /**
   * Query tasks with natural language
   * POST /api/tasks/query
   *
   * Body: { query: "What tasks are due today?" }
   */
  app.post('/api/tasks/query', requireAuth(db), async (req, res) => {
    try {
      const { query } = req.body;

      if (!query) {
        return res.status(400).json({
          error: 'Query is required'
        });
      }

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const result = await tasks.queryTasks(req.user.id, query);

      res.json({
        success: true,
        ...result
      });
    } catch (error) {
      console.error('Error querying tasks:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Get all tasks with filters
   * GET /api/tasks
   */
  app.get('/api/tasks', requireAuth(db), async (req, res) => {
    try {
      const { completed, category, priority, limit } = req.query;

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const filters = {};
      if (completed !== undefined) filters.completed = completed === 'true';
      if (category) filters.category = category;
      if (priority) filters.priority = parseInt(priority);
      if (limit) filters.limit = parseInt(limit);

      const taskList = await tasks.getTasks(req.user.id, filters);

      res.json({
        success: true,
        tasks: taskList,
        count: taskList.length
      });
    } catch (error) {
      console.error('Error getting tasks:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Get specific task
   * GET /api/tasks/:taskId
   */
  app.get('/api/tasks/:taskId', requireAuth(db), async (req, res) => {
    try {
      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const task = await tasks.getTask(req.user.id, req.params.taskId);

      if (!task) {
        return res.status(404).json({
          error: 'Task not found'
        });
      }

      res.json({
        success: true,
        task
      });
    } catch (error) {
      console.error('Error getting task:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Get task summary
   * GET /api/tasks/summary/:timeframe
   */
  app.get('/api/tasks/summary/:timeframe?', requireAuth(db), async (req, res) => {
    try {
      const { timeframe = 'today' } = req.params;

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const summary = await tasks.getTaskSummary(req.user.id, timeframe);

      res.json({
        success: true,
        summary
      });
    } catch (error) {
      console.error('Error getting task summary:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // TASK UPDATES
  // =============================================================================

  /**
   * Update task from voice command
   * PUT /api/tasks/voice
   *
   * Body: { command: "Complete task write report" }
   */
  app.put('/api/tasks/voice', requireAuth(db), async (req, res) => {
    try {
      const { command } = req.body;

      if (!command) {
        return res.status(400).json({
          error: 'Command is required'
        });
      }

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const task = await tasks.updateTaskFromVoice(req.user.id, command);

      res.json({
        success: true,
        task,
        message: 'Task updated successfully'
      });
    } catch (error) {
      console.error('Error updating task:', error);
      res.status(400).json({ error: error.message });
    }
  });

  /**
   * Update task with structured data
   * PUT /api/tasks/:taskId
   */
  app.put('/api/tasks/:taskId', requireAuth(db), async (req, res) => {
    try {
      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const task = await tasks.manager.updateTask(req.user.id, {
        taskIdentifier: req.params.taskId,
        updates: req.body
      });

      res.json({
        success: true,
        task
      });
    } catch (error) {
      console.error('Error updating task:', error);
      res.status(400).json({ error: error.message });
    }
  });

  /**
   * Complete task
   * POST /api/tasks/:taskId/complete
   */
  app.post('/api/tasks/:taskId/complete', requireAuth(db), async (req, res) => {
    try {
      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const task = await tasks.completeTask(req.user.id, req.params.taskId);

      res.json({
        success: true,
        task,
        message: `Completed: "${task.title}"`
      });
    } catch (error) {
      console.error('Error completing task:', error);
      res.status(400).json({ error: error.message });
    }
  });

  // =============================================================================
  // REMINDERS
  // =============================================================================

  /**
   * Get pending reminders
   * GET /api/tasks/reminders/pending
   */
  app.get('/api/tasks/reminders/pending', requireAuth(db), async (req, res) => {
    try {
      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const reminders = await tasks.getPendingReminders(req.user.id);

      res.json({
        success: true,
        reminders,
        count: reminders.length
      });
    } catch (error) {
      console.error('Error getting reminders:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Mark reminder as delivered
   * POST /api/tasks/reminders/:reminderId/delivered
   */
  app.post('/api/tasks/reminders/:reminderId/delivered', requireAuth(db), async (req, res) => {
    try {
      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      await tasks.markReminderDelivered(parseInt(req.params.reminderId));

      res.json({
        success: true,
        message: 'Reminder marked as delivered'
      });
    } catch (error) {
      console.error('Error marking reminder:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // =============================================================================
  // SCHEDULING
  // =============================================================================

  /**
   * Get schedule overview
   * GET /api/tasks/schedule/:date?
   */
  app.get('/api/tasks/schedule/:date?', requireAuth(db), async (req, res) => {
    try {
      const date = req.params.date ? new Date(req.params.date) : new Date();

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const schedule = await tasks.getScheduleOverview(req.user.id, date);

      res.json({
        success: true,
        schedule
      });
    } catch (error) {
      console.error('Error getting schedule:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Find optimal time slot
   * POST /api/tasks/schedule/find-slot
   *
   * Body: { duration: 60, preferences: { preferredTime: 'morning' } }
   */
  app.post('/api/tasks/schedule/find-slot', requireAuth(db), async (req, res) => {
    try {
      const { duration, preferences } = req.body;

      if (!duration) {
        return res.status(400).json({
          error: 'Duration is required'
        });
      }

      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const slot = await tasks.findOptimalTimeSlot(req.user.id, duration, preferences);

      if (!slot) {
        return res.status(404).json({
          error: 'No available time slots found',
          suggestion: 'Try adjusting your preferences or timeframe'
        });
      }

      res.json({
        success: true,
        slot
      });
    } catch (error) {
      console.error('Error finding time slot:', error);
      res.status(500).json({ error: error.message });
    }
  });

  /**
   * Suggest reschedule for task
   * POST /api/tasks/:taskId/suggest-reschedule
   */
  app.post('/api/tasks/:taskId/suggest-reschedule', requireAuth(db), async (req, res) => {
    try {
      // Check feature access
      const hasFeature = await checkFeatureAccess(db, req.user.id, 'task_management');
      if (!hasFeature) {
        return res.status(403).json({
          error: 'Task management requires Personal tier or higher'
        });
      }

      const suggestion = await tasks.suggestReschedule(req.user.id, req.params.taskId);

      res.json({
        success: true,
        suggestion
      });
    } catch (error) {
      console.error('Error suggesting reschedule:', error);
      res.status(500).json({ error: error.message });
    }
  });
}

/**
 * Individual route handlers for Cloudflare Workers
 */

export async function handleCreateTaskVoice(request, env) {
  try {
    const { input } = await request.json();

    if (!input || input.trim().length === 0) {
      return new Response(JSON.stringify({ error: 'Voice input is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { requireAuth } = await import('../lib/auth-middleware.js');
    const user = await requireAuth(request, env);

    const { checkFeatureAccess } = await import('../lib/features.js');
    const hasFeature = await checkFeatureAccess(env.DB, user.id, 'task_management');

    if (!hasFeature) {
      return new Response(JSON.stringify({
        error: 'Task management requires Personal tier or higher'
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { TaskSystem } = await import('../lib/tasks/mod.js');
    const tasks = new TaskSystem(env.DB);
    const task = await tasks.createTaskFromVoice(user.id, input);

    return new Response(JSON.stringify({
      success: true,
      task,
      message: `Created task: "${task.title}"`
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error creating task:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

export async function handleQueryTasks(request, env) {
  try {
    const { query } = await request.json();

    if (!query) {
      return new Response(JSON.stringify({ error: 'Query is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { requireAuth } = await import('../lib/auth-middleware.js');
    const user = await requireAuth(request, env);

    const { checkFeatureAccess } = await import('../lib/features.js');
    const hasFeature = await checkFeatureAccess(env.DB, user.id, 'task_management');

    if (!hasFeature) {
      return new Response(JSON.stringify({
        error: 'Task management requires Personal tier or higher'
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { TaskSystem } = await import('../lib/tasks/mod.js');
    const tasks = new TaskSystem(env.DB);
    const result = await tasks.queryTasks(user.id, query);

    return new Response(JSON.stringify({
      success: true,
      ...result
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error querying tasks:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

export async function handleGetTaskSummary(request, env, timeframe = 'today') {
  try {
    const { requireAuth } = await import('../lib/auth-middleware.js');
    const user = await requireAuth(request, env);

    const { checkFeatureAccess } = await import('../lib/features.js');
    const hasFeature = await checkFeatureAccess(env.DB, user.id, 'task_management');

    if (!hasFeature) {
      return new Response(JSON.stringify({
        error: 'Task management requires Personal tier or higher'
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const { TaskSystem } = await import('../lib/tasks/mod.js');
    const tasks = new TaskSystem(env.DB);
    const summary = await tasks.getTaskSummary(user.id, timeframe);

    return new Response(JSON.stringify({
      success: true,
      summary
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error getting task summary:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
