/**
 * Task Queries - Natural language task queries
 * Handles "show my tasks", "what's due today", etc.
 */

export class TaskQueries {
  constructor(db) {
    this.db = db;
  }

  // Helper methods for libsql API
  async executeQuery(query, params = []) {
    const result = await this.db.execute({ sql: query, args: params });
    return result;
  }

  async getOne(query, params = []) {
    const result = await this.executeQuery(query, params);
    return result.rows[0] || null;
  }

  async getAll(query, params = []) {
    const result = await this.executeQuery(query, params);
    return result.rows || [];
  }

  async processQuery(userId, query) {
    const normalizedQuery = query.toLowerCase().trim();

    // Determine query type
    const queryType = this.determineQueryType(normalizedQuery);

    switch (queryType) {
      case 'today':
        return await this.getTasksForToday(userId);

      case 'tomorrow':
        return await this.getTasksForTomorrow(userId);

      case 'week':
        return await this.getTasksForWeek(userId);

      case 'overdue':
        return await this.getOverdueTasks(userId);

      case 'category':
        const category = this.extractCategory(normalizedQuery);
        return await this.getTasksByCategory(userId, category);

      case 'priority':
        const priority = this.extractPriority(normalizedQuery);
        return await this.getTasksByPriority(userId, priority);

      case 'all':
      default:
        return await this.getAllActiveTasks(userId);
    }
  }

  determineQueryType(query) {
    const patterns = {
      'today': /(?:today|due today|what.*today|tasks? for today)/i,
      'tomorrow': /(?:tomorrow|due tomorrow|what.*tomorrow)/i,
      'week': /(?:this week|next week|week|weekly)/i,
      'overdue': /(?:overdue|past due|late|missed)/i,
      'category': /(?:work|personal|home|health|finance|shopping|family|travel|learning|project) tasks?/i,
      'priority': /(?:urgent|high|low|priority) tasks?/i,
      'all': /(?:all|list|show)/i
    };

    for (const [type, pattern] of Object.entries(patterns)) {
      if (pattern.test(query)) {
        return type;
      }
    }

    return 'all';
  }

  extractCategory(query) {
    const categories = [
      'work', 'personal', 'health', 'finance', 'shopping',
      'family', 'travel', 'home', 'learning', 'project'
    ];

    for (const category of categories) {
      if (query.includes(category)) {
        return category;
      }
    }

    return 'general';
  }

  extractPriority(query) {
    const priorities = {
      'urgent': 1,
      'high': 2,
      'medium': 3,
      'low': 4
    };

    for (const [keyword, priority] of Object.entries(priorities)) {
      if (query.includes(keyword)) {
        return priority;
      }
    }

    return null;
  }

  async getTasksForToday(userId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND date(due_date) = date('now')
      ORDER BY priority ASC, due_time ASC
    `;

    const tasks = await this.getAll(query, [userId]);
    return {
      type: 'today',
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary('today', tasks)
    };
  }

  async getTasksForTomorrow(userId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND date(due_date) = date('now', '+1 day')
      ORDER BY priority ASC, due_time ASC
    `;

    const tasks = await this.getAll(query, [userId]);
    return {
      type: 'tomorrow',
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary('tomorrow', tasks)
    };
  }

  async getTasksForWeek(userId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND date(due_date) BETWEEN date('now') AND date('now', '+7 days')
      ORDER BY due_date ASC, priority ASC
    `;

    const tasks = await this.getAll(query, [userId]);
    return {
      type: 'week',
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary('week', tasks)
    };
  }

  async getOverdueTasks(userId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND due_date < datetime('now')
      ORDER BY due_date ASC
    `;

    const tasks = await this.getAll(query, [userId]);
    return {
      type: 'overdue',
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary('overdue', tasks)
    };
  }

  async getTasksByCategory(userId, category) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND category = ?
      ORDER BY priority ASC, due_date ASC
    `;

    const tasks = await this.db.all(query, [userId, category]);
    return {
      type: 'category',
      category,
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary(`${category} tasks`, tasks)
    };
  }

  async getTasksByPriority(userId, priority) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND priority = ?
      ORDER BY due_date ASC
    `;

    const tasks = await this.db.all(query, [userId, priority]);
    return {
      type: 'priority',
      priority,
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary(`priority ${priority} tasks`, tasks)
    };
  }

  async getAllActiveTasks(userId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
      ORDER BY priority ASC, due_date ASC
      LIMIT 50
    `;

    const tasks = await this.getAll(query, [userId]);
    return {
      type: 'all',
      count: tasks.length,
      tasks: tasks.map(task => this.deserializeTask(task)),
      summary: this.generateSummary('active tasks', tasks)
    };
  }

  async getTaskSummary(userId, timeframe = 'today') {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const queries = {
      today: `date(due_date) = date('now')`,
      week: `date(due_date) BETWEEN date('now') AND date('now', '+7 days')`,
      month: `date(due_date) BETWEEN date('now') AND date('now', '+30 days')`,
      all: '1=1'
    };

    const whereClause = queries[timeframe] || queries.today;

    const query = `
      SELECT
        COUNT(*) as total,
        SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN priority = 1 THEN 1 ELSE 0 END) as urgent,
        SUM(CASE WHEN due_date < datetime('now') AND completed = 0 THEN 1 ELSE 0 END) as overdue
      FROM tasks
      WHERE user_id = ? AND ${whereClause}
    `;

    const summary = await this.getOne(query, [userId]);

    return {
      timeframe,
      total: summary.total || 0,
      active: (summary.total || 0) - (summary.completed || 0),
      completed: summary.completed || 0,
      urgent: summary.urgent || 0,
      overdue: summary.overdue || 0
    };
  }

  generateSummary(type, tasks) {
    if (tasks.length === 0) {
      return `You have no ${type}.`;
    }

    const priorityCounts = {
      urgent: tasks.filter(t => t.priority === 1).length,
      high: tasks.filter(t => t.priority === 2).length,
      medium: tasks.filter(t => t.priority === 3).length,
      low: tasks.filter(t => t.priority >= 4).length
    };

    const parts = [`You have ${tasks.length} ${type}`];

    if (priorityCounts.urgent > 0) {
      parts.push(`${priorityCounts.urgent} urgent`);
    }

    if (priorityCounts.high > 0) {
      parts.push(`${priorityCounts.high} high priority`);
    }

    return parts.join(', ') + '.';
  }

  deserializeTask(dbTask) {
    if (!dbTask) return null;

    return {
      id: dbTask.id,
      userId: dbTask.user_id,
      title: dbTask.title,
      description: dbTask.description,
      dueDate: dbTask.due_date ? new Date(dbTask.due_date) : null,
      dueTime: dbTask.due_time,
      priority: dbTask.priority,
      category: dbTask.category,
      location: dbTask.location,
      estimatedDuration: dbTask.estimated_duration_minutes,
      actualDuration: dbTask.actual_duration_minutes,
      tags: dbTask.tags ? JSON.parse(dbTask.tags) : [],
      completed: Boolean(dbTask.completed),
      createdVia: dbTask.created_via,
      recurrencePattern: dbTask.recurrence_pattern ? JSON.parse(dbTask.recurrence_pattern) : null,
      nextDueDate: dbTask.next_due_date ? new Date(dbTask.next_due_date) : null,
      parentTaskId: dbTask.parent_task_id,
      projectId: dbTask.project_id,
      notes: dbTask.notes,
      createdAt: new Date(dbTask.created_at),
      updatedAt: new Date(dbTask.updated_at),
      completedAt: dbTask.completed_at ? new Date(dbTask.completed_at) : null
    };
  }
}
