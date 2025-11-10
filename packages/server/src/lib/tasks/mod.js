/**
 * Task System - Main coordinator for task management
 * Voice-first task management with natural language support
 */

import { TaskManager } from './manager.js';
import { TaskParser } from './parser.js';
import { TaskReminders } from './reminders.js';
import { TaskQueries } from './queries.js';
import { TaskScheduler } from './scheduler.js';

export class TaskSystem {
  constructor(db) {
    this.db = db;
    this.manager = new TaskManager(db);
    this.parser = new TaskParser();
    this.reminders = new TaskReminders(db);
    this.queries = new TaskQueries(db);
    this.scheduler = new TaskScheduler(db);
  }

  async createTaskFromVoice(userId, voiceInput) {
    // Parse natural language input
    const parsedTask = await this.parser.parseVoiceInput(voiceInput);

    // Check for conflicts if date/time specified
    if (parsedTask.dueDate && parsedTask.dueTime && parsedTask.estimatedDuration) {
      const conflicts = await this.scheduler.checkConflicts(
        userId,
        parsedTask.dueDate,
        parsedTask.dueTime,
        parsedTask.estimatedDuration
      );

      if (conflicts.hasConflicts) {
        parsedTask.hasConflicts = true;
        parsedTask.conflicts = conflicts.conflicts;
      }
    }

    // Create task with parsed data
    const task = await this.manager.createTask(userId, parsedTask);

    // Schedule smart reminder based on priority
    if (parsedTask.dueDate && !parsedTask.reminderTime) {
      await this.reminders.scheduleSmartReminder(
        task.id,
        parsedTask.dueDate,
        parsedTask.priority
      );
    } else if (parsedTask.reminderTime) {
      await this.reminders.scheduleReminder(
        task.id,
        parsedTask.reminderTime,
        parsedTask.reminderType || 'voice'
      );
    }

    return task;
  }

  async queryTasks(userId, query) {
    return await this.queries.processQuery(userId, query);
  }

  async updateTaskFromVoice(userId, query) {
    // Parse update command
    const updateData = await this.parser.parseUpdateCommand(query);

    if (!updateData.taskIdentifier) {
      throw new Error('Could not identify which task to update');
    }

    // Find and update task
    return await this.manager.updateTask(userId, updateData);
  }

  async completeTask(userId, taskIdentifier) {
    return await this.manager.completeTask(userId, taskIdentifier);
  }

  async getTaskSummary(userId, timeframe = 'today') {
    return await this.queries.getTaskSummary(userId, timeframe);
  }

  async getPendingReminders(userId) {
    return await this.reminders.getPendingReminders(userId);
  }

  async markReminderDelivered(reminderId) {
    return await this.reminders.markReminderDelivered(reminderId);
  }

  async getScheduleOverview(userId, date) {
    return await this.scheduler.getScheduleOverview(userId, date);
  }

  async suggestReschedule(userId, taskId) {
    return await this.scheduler.suggestReschedule(userId, taskId);
  }

  async findOptimalTimeSlot(userId, duration, preferences) {
    return await this.scheduler.findOptimalTimeSlot(userId, duration, preferences);
  }

  async getTask(userId, taskId) {
    return await this.manager.findTask(userId, taskId);
  }

  async getTasks(userId, filters) {
    return await this.manager.getTasks(userId, filters);
  }
}

// Export individual components for advanced usage
export { TaskManager } from './manager.js';
export { TaskParser } from './parser.js';
export { TaskReminders } from './reminders.js';
export { TaskQueries } from './queries.js';
export { TaskScheduler } from './scheduler.js';
