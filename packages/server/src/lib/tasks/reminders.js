/**
 * Task Reminders - Reminder scheduling and delivery
 * Manages task reminders via voice, SMS, email
 */

export class TaskReminders {
  constructor(db) {
    this.db = db;
  }

  // Helper methods for libsql API
  async executeQuery(query, params = []) {
    const result = await this.db.execute({ sql: query, args: params });
    return result;
  }

  async getAll(query, params = []) {
    const result = await this.executeQuery(query, params);
    return result.rows || [];
  }

  async scheduleReminder(taskId, reminderTime, type = 'voice') {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      INSERT INTO task_reminders (task_id, reminder_time, reminder_type, message, delivered)
      VALUES (?, ?, ?, ?, 0)
    `;

    const message = `Reminder: Task "${taskId}" is due soon`;

    await this.executeQuery(query, [
      taskId,
      reminderTime.toISOString(),
      type,
      message
    ]);

    return {
      taskId,
      reminderTime,
      type,
      message
    };
  }

  async getPendingReminders(userId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT r.*, t.title, t.description, t.due_date, t.due_time
      FROM task_reminders r
      JOIN tasks t ON r.task_id = t.id
      WHERE t.user_id = ?
        AND r.delivered = 0
        AND r.reminder_time <= datetime('now')
      ORDER BY r.reminder_time ASC
    `;

    const reminders = await this.getAll(query, [userId]);

    return reminders.map(reminder => ({
      id: reminder.id,
      taskId: reminder.task_id,
      taskTitle: reminder.title,
      taskDescription: reminder.description,
      dueDate: reminder.due_date ? new Date(reminder.due_date) : null,
      dueTime: reminder.due_time,
      reminderTime: new Date(reminder.reminder_time),
      reminderType: reminder.reminder_type,
      message: reminder.message
    }));
  }

  async markReminderDelivered(reminderId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      UPDATE task_reminders
      SET delivered = 1, delivered_at = datetime('now')
      WHERE id = ?
    `;

    await this.executeQuery(query, [reminderId]);
  }

  async cancelReminder(reminderId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `DELETE FROM task_reminders WHERE id = ?`;
    await this.executeQuery(query, [reminderId]);
  }

  async getTaskReminders(taskId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const query = `
      SELECT * FROM task_reminders
      WHERE task_id = ?
      ORDER BY reminder_time ASC
    `;

    const reminders = await this.getAll(query, [taskId]);

    return reminders.map(reminder => ({
      id: reminder.id,
      taskId: reminder.task_id,
      reminderTime: new Date(reminder.reminder_time),
      reminderType: reminder.reminder_type,
      message: reminder.message,
      delivered: Boolean(reminder.delivered),
      deliveredAt: reminder.delivered_at ? new Date(reminder.delivered_at) : null
    }));
  }

  async scheduleSmartReminder(taskId, dueDate, priority) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    if (!dueDate) return null;

    // Calculate smart reminder time based on priority
    const reminderOffsets = {
      1: 30,   // Urgent: 30 minutes before
      2: 60,   // High: 1 hour before
      3: 120,  // Medium: 2 hours before
      4: 240,  // Low: 4 hours before
      5: 480   // Later: 8 hours before
    };

    const offsetMinutes = reminderOffsets[priority] || 120;
    const reminderTime = new Date(dueDate.getTime() - (offsetMinutes * 60 * 1000));

    // Don't schedule reminders in the past
    if (reminderTime < new Date()) {
      return null;
    }

    return await this.scheduleReminder(taskId, reminderTime, 'voice');
  }

  formatReminderMessage(task) {
    const parts = [`Reminder: ${task.title}`];

    if (task.dueTime) {
      parts.push(`due at ${task.dueTime}`);
    } else if (task.dueDate) {
      const dueDate = new Date(task.dueDate);
      const today = new Date();

      if (dueDate.toDateString() === today.toDateString()) {
        parts.push('due today');
      } else {
        parts.push(`due ${dueDate.toLocaleDateString()}`);
      }
    }

    if (task.location) {
      parts.push(`at ${task.location}`);
    }

    if (task.estimatedDuration) {
      parts.push(`(${task.estimatedDuration} minutes)`);
    }

    return parts.join(' ');
  }
}
