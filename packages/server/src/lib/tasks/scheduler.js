/**
 * Task Scheduler - Smart scheduling and conflict detection
 * Handles task scheduling optimization
 */

export class TaskScheduler {
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

  async findOptimalTimeSlot(userId, duration, preferences = {}) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const {
      startDate = new Date(),
      endDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
      preferredTime = 'morning', // morning, afternoon, evening
      avoidWeekends = false
    } = preferences;

    // Get existing tasks in the timeframe
    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND due_date BETWEEN ? AND ?
      ORDER BY due_date ASC, due_time ASC
    `;

    const existingTasks = await this.getAll(query, [
      userId,
      startDate.toISOString(),
      endDate.toISOString()
    ]);

    // Find gaps in the schedule
    const slots = this.findAvailableSlots(
      existingTasks,
      duration,
      startDate,
      endDate,
      preferredTime,
      avoidWeekends
    );

    return slots[0] || null; // Return first available slot
  }

  findAvailableSlots(existingTasks, durationMinutes, startDate, endDate, preferredTime, avoidWeekends) {
    const slots = [];
    const timePreferences = {
      'morning': { start: 9, end: 12 },
      'afternoon': { start: 13, end: 17 },
      'evening': { start: 18, end: 21 }
    };

    const preferred = timePreferences[preferredTime] || timePreferences.morning;
    let currentDate = new Date(startDate);

    while (currentDate <= endDate) {
      // Skip weekends if requested
      if (avoidWeekends && (currentDate.getDay() === 0 || currentDate.getDay() === 6)) {
        currentDate.setDate(currentDate.getDate() + 1);
        continue;
      }

      // Check each hour in the preferred time range
      for (let hour = preferred.start; hour < preferred.end; hour++) {
        const slotStart = new Date(currentDate);
        slotStart.setHours(hour, 0, 0, 0);

        const slotEnd = new Date(slotStart);
        slotEnd.setMinutes(slotEnd.getMinutes() + durationMinutes);

        // Check for conflicts
        const hasConflict = existingTasks.some(task => {
          if (!task.due_date || !task.due_time) return false;

          const taskDate = new Date(task.due_date);
          const [taskHour, taskMinute] = task.due_time.split(':').map(Number);
          taskDate.setHours(taskHour, taskMinute, 0, 0);

          const taskEnd = new Date(taskDate);
          taskEnd.setMinutes(taskEnd.getMinutes() + (task.estimated_duration_minutes || 30));

          // Check for overlap
          return (slotStart < taskEnd && slotEnd > taskDate);
        });

        if (!hasConflict) {
          slots.push({
            start: slotStart,
            end: slotEnd,
            date: slotStart.toISOString().split('T')[0],
            time: `${hour.toString().padStart(2, '0')}:00`
          });
        }
      }

      currentDate.setDate(currentDate.getDate() + 1);
    }

    return slots;
  }

  async checkConflicts(userId, taskDate, taskTime, duration) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    if (!taskDate || !taskTime) {
      return { hasConflicts: false, conflicts: [] };
    }

    const taskDateTime = new Date(taskDate);
    const [hour, minute] = taskTime.split(':').map(Number);
    taskDateTime.setHours(hour, minute, 0, 0);

    const taskEnd = new Date(taskDateTime);
    taskEnd.setMinutes(taskEnd.getMinutes() + (duration || 30));

    // Find tasks that might conflict
    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND date(due_date) = date(?)
      ORDER BY due_time ASC
    `;

    const sameDayTasks = await this.getAll(query, [
      userId,
      taskDateTime.toISOString()
    ]);

    const conflicts = sameDayTasks.filter(task => {
      if (!task.due_time) return false;

      const [existingHour, existingMinute] = task.due_time.split(':').map(Number);
      const existingStart = new Date(task.due_date);
      existingStart.setHours(existingHour, existingMinute, 0, 0);

      const existingEnd = new Date(existingStart);
      existingEnd.setMinutes(existingEnd.getMinutes() + (task.estimated_duration_minutes || 30));

      // Check for overlap
      return (taskDateTime < existingEnd && taskEnd > existingStart);
    });

    return {
      hasConflicts: conflicts.length > 0,
      conflicts: conflicts.map(task => ({
        id: task.id,
        title: task.title,
        dueDate: task.due_date,
        dueTime: task.due_time,
        duration: task.estimated_duration_minutes
      }))
    };
  }

  async suggestReschedule(userId, taskId) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    // Get the task
    const task = await this.getOne(
      `SELECT * FROM tasks WHERE id = ? AND user_id = ?`,
      [taskId, userId]
    );

    if (!task) {
      throw new Error('Task not found');
    }

    const duration = task.estimated_duration_minutes || 30;

    // Find next available slot
    const slot = await this.findOptimalTimeSlot(userId, duration, {
      startDate: new Date(),
      preferredTime: this.getTimeOfDay(task.due_time)
    });

    return {
      originalDate: task.due_date,
      originalTime: task.due_time,
      suggestedDate: slot ? slot.date : null,
      suggestedTime: slot ? slot.time : null,
      slot
    };
  }

  getTimeOfDay(time) {
    if (!time) return 'morning';

    const [hour] = time.split(':').map(Number);

    if (hour >= 6 && hour < 12) return 'morning';
    if (hour >= 12 && hour < 17) return 'afternoon';
    return 'evening';
  }

  async getScheduleOverview(userId, date) {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const targetDate = date || new Date();

    const query = `
      SELECT * FROM tasks
      WHERE user_id = ?
        AND completed = 0
        AND date(due_date) = date(?)
      ORDER BY due_time ASC
    `;

    const tasks = await this.getAll(query, [
      userId,
      targetDate.toISOString()
    ]);

    // Calculate schedule metrics
    const totalDuration = tasks.reduce((sum, task) =>
      sum + (task.estimated_duration_minutes || 30), 0);

    const earliestTask = tasks[0];
    const latestTask = tasks[tasks.length - 1];

    return {
      date: targetDate.toISOString().split('T')[0],
      taskCount: tasks.length,
      totalDuration,
      earliestTime: earliestTask ? earliestTask.due_time : null,
      latestTime: latestTask ? latestTask.due_time : null,
      tasks: tasks.map(task => ({
        id: task.id,
        title: task.title,
        time: task.due_time,
        duration: task.estimated_duration_minutes,
        priority: task.priority
      }))
    };
  }
}
