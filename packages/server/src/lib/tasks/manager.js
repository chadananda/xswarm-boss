/**
 * Task Manager - Core task CRUD operations
 * Handles task lifecycle and database operations
 */

export class TaskManager {
  constructor(db) {
    this.db = db;
  }

  // Helper method to execute queries with libsql API
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

  async createTask(userId, taskData) {
    const taskId = await this.generateTaskId();

    const task = {
      id: taskId,
      userId,
      title: taskData.title,
      description: taskData.description,
      dueDate: taskData.dueDate,
      dueTime: taskData.dueTime,
      priority: taskData.priority || 3,
      category: taskData.category || 'general',
      location: taskData.location,
      estimatedDuration: taskData.estimatedDuration,
      tags: taskData.tags || [],
      completed: false,
      createdVia: 'voice',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Handle recurring tasks
    if (taskData.isRecurring) {
      task.recurrencePattern = taskData.recurrencePattern;
      task.nextDueDate = this.calculateNextDueDate(task);
    }

    // Store in database
    await this.saveTask(task);

    // Schedule reminders
    if (taskData.reminderTime) {
      await this.scheduleTaskReminder(taskId, taskData.reminderTime);
    }

    return task;
  }

  async updateTask(userId, updateData) {
    const { taskIdentifier, updates } = updateData;

    // Find task by identifier
    const task = await this.findTask(userId, taskIdentifier);

    if (!task) {
      throw new Error(`Task not found: ${taskIdentifier}`);
    }

    // Apply updates
    const updatedTask = {
      ...task,
      ...updates,
      updatedAt: new Date()
    };

    // Handle completion
    if (updates.completed && task.recurrence_pattern) {
      // Parse recurrence pattern if it's a string
      const recurrencePattern = typeof task.recurrence_pattern === 'string'
        ? JSON.parse(task.recurrence_pattern)
        : task.recurrence_pattern;

      // Create next instance for recurring tasks
      if (recurrencePattern) {
        await this.createNextRecurringInstance({
          ...task,
          recurrence_pattern: recurrencePattern
        });
      }
    }

    // Update in database
    await this.saveTask(updatedTask);

    return updatedTask;
  }

  async completeTask(userId, taskIdentifier) {
    return await this.updateTask(userId, {
      taskIdentifier,
      updates: {
        completed: true,
        completedAt: new Date()
      }
    });
  }

  async findTask(userId, identifier) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    // Try different identification methods
    const queries = {
      byId: `SELECT * FROM tasks WHERE user_id = ? AND id = ?`,
      byExactTitle: `SELECT * FROM tasks WHERE user_id = ? AND title = ? AND completed = 0`,
      byPartialTitle: `SELECT * FROM tasks WHERE user_id = ? AND LOWER(title) LIKE ? AND completed = 0`,
      byIndex: `SELECT * FROM tasks WHERE user_id = ? AND completed = 0 ORDER BY created_at LIMIT 1 OFFSET ?`
    };

    // Try ID first
    if (/^[A-Z0-9]{8}$/.test(identifier)) {
      const taskById = await this.getOne(queries.byId, [userId, identifier]);
      if (taskById) return this.deserializeTask(taskById);
    }

    // Try exact title match
    const exactMatch = await this.getOne(queries.byExactTitle, [userId, identifier]);
    if (exactMatch) return this.deserializeTask(exactMatch);

    // Try partial match
    const partialMatch = await this.getOne(queries.byPartialTitle, [userId, `%${identifier}%`]);
    if (partialMatch) return this.deserializeTask(partialMatch);

    // Try index-based (for "task 1", "first task", etc.)
    const indexMatch = identifier.match(/(\d+)/);
    if (indexMatch) {
      const index = parseInt(indexMatch[1]) - 1; // Convert to 0-based
      const indexedTask = await this.getOne(queries.byIndex, [userId, index]);
      if (indexedTask) return this.deserializeTask(indexedTask);
    }

    return null;
  }

  async saveTask(task) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      INSERT INTO tasks (
        id, user_id, title, description, due_date, due_time,
        priority, category, location, estimated_duration_minutes,
        tags, completed, created_via, recurrence_pattern,
        next_due_date, created_at, updated_at, completed_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        description = EXCLUDED.description,
        due_date = EXCLUDED.due_date,
        due_time = EXCLUDED.due_time,
        priority = EXCLUDED.priority,
        category = EXCLUDED.category,
        location = EXCLUDED.location,
        estimated_duration_minutes = EXCLUDED.estimated_duration_minutes,
        tags = EXCLUDED.tags,
        completed = EXCLUDED.completed,
        recurrence_pattern = EXCLUDED.recurrence_pattern,
        next_due_date = EXCLUDED.next_due_date,
        updated_at = EXCLUDED.updated_at,
        completed_at = EXCLUDED.completed_at
    `;

    await this.executeQuery(query, [
      task.id,
      task.userId,
      task.title,
      task.description,
      task.dueDate ? task.dueDate.toISOString() : null,
      task.dueTime,
      task.priority,
      task.category,
      task.location,
      task.estimatedDuration,
      JSON.stringify(task.tags || []),
      task.completed ? 1 : 0,
      task.createdVia,
      task.recurrencePattern ? JSON.stringify(task.recurrencePattern) : null,
      task.nextDueDate ? task.nextDueDate.toISOString() : null,
      task.createdAt ? task.createdAt.toISOString() : new Date().toISOString(),
      task.updatedAt ? task.updatedAt.toISOString() : new Date().toISOString(),
      task.completedAt ? task.completedAt.toISOString() : null
    ]);
  }

  async scheduleTaskReminder(taskId, reminderTime) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      INSERT INTO task_reminders (task_id, reminder_time, reminder_type, message)
      VALUES (?, ?, ?, ?)
    `;

    await this.executeQuery(query, [
      taskId,
      reminderTime.toISOString(),
      'voice',
      'Task reminder'
    ]);
  }

  async generateTaskId() {
    // Generate short, readable ID (8 characters)
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let result = '';
    for (let i = 0; i < 8; i++) {
      result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
  }

  calculateNextDueDate(task) {
    if (!task.recurrencePattern || !task.dueDate) return null;

    const pattern = typeof task.recurrencePattern === 'string'
      ? JSON.parse(task.recurrencePattern)
      : task.recurrencePattern;

    const { type, interval = 1, time } = pattern;
    const nextDate = new Date(task.dueDate);

    switch (type) {
      case 'daily':
        nextDate.setDate(nextDate.getDate() + interval);
        break;
      case 'weekly':
        nextDate.setDate(nextDate.getDate() + (7 * interval));
        break;
      case 'monthly':
        nextDate.setMonth(nextDate.getMonth() + interval);
        break;
    }

    if (time) {
      const [hours, minutes] = time.split(':');
      nextDate.setHours(parseInt(hours), parseInt(minutes), 0, 0);
    }

    return nextDate;
  }

  async createNextRecurringInstance(task) {
    const nextTask = {
      ...task,
      id: await this.generateTaskId(),
      dueDate: task.nextDueDate || this.calculateNextDueDate(task),
      completed: false,
      completedAt: null,
      createdAt: new Date(),
      updatedAt: new Date(),
      nextDueDate: this.calculateNextDueDate({
        ...task,
        dueDate: task.nextDueDate || this.calculateNextDueDate(task)
      })
    };

    await this.saveTask(nextTask);
    return nextTask;
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
      recurrence_pattern: dbTask.recurrence_pattern ? JSON.parse(dbTask.recurrence_pattern) : null,
      nextDueDate: dbTask.next_due_date ? new Date(dbTask.next_due_date) : null,
      parentTaskId: dbTask.parent_task_id,
      projectId: dbTask.project_id,
      notes: dbTask.notes,
      createdAt: new Date(dbTask.created_at),
      updatedAt: new Date(dbTask.updated_at),
      completedAt: dbTask.completed_at ? new Date(dbTask.completed_at) : null
    };
  }

  async getTasks(userId, filters = {}) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    let query = `SELECT * FROM tasks WHERE user_id = ?`;
    const params = [userId];

    if (filters.completed !== undefined) {
      query += ` AND completed = ?`;
      params.push(filters.completed ? 1 : 0);
    }

    if (filters.category) {
      query += ` AND category = ?`;
      params.push(filters.category);
    }

    if (filters.priority) {
      query += ` AND priority = ?`;
      params.push(filters.priority);
    }

    query += ` ORDER BY priority ASC, due_date ASC`;

    if (filters.limit) {
      query += ` LIMIT ?`;
      params.push(filters.limit);
    }

    const tasks = await this.getAll(query, params);
    return tasks.map(task => this.deserializeTask(task));
  }
}
