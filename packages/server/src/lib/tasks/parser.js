/**
 * Task Parser - Natural language task parsing with chrono-node
 * Extracts task details from voice/text input
 */

import * as chrono from 'chrono-node';

export class TaskParser {
  constructor() {
    this.priorities = {
      'urgent': 1,
      'high': 2,
      'medium': 3,
      'normal': 3,
      'low': 4,
      'later': 5
    };

    this.categories = [
      'work', 'personal', 'health', 'finance', 'shopping',
      'family', 'travel', 'home', 'learning', 'project'
    ];
  }

  async parseVoiceInput(input) {
    const normalizedInput = input.toLowerCase().trim();

    // Extract the main task description
    const taskText = this.extractTaskText(normalizedInput);

    // Parse temporal information
    const timing = this.parseTimeInfo(normalizedInput);

    // Extract priority
    const priority = this.extractPriority(normalizedInput);

    // Extract category
    const category = this.extractCategory(normalizedInput);

    // Extract location if mentioned
    const location = this.extractLocation(normalizedInput);

    // Extract duration estimate
    const duration = this.extractDuration(normalizedInput);

    // Extract reminder preferences
    const reminder = this.extractReminderInfo(normalizedInput);

    return {
      title: taskText,
      description: this.generateDescription(input, {
        timing, priority, category, location, duration
      }),
      dueDate: timing.dueDate,
      dueTime: timing.dueTime,
      priority,
      category,
      location,
      estimatedDuration: duration,
      reminderTime: reminder.time,
      reminderType: reminder.type,
      tags: this.extractTags(normalizedInput),
      isRecurring: timing.isRecurring,
      recurrencePattern: timing.recurrencePattern
    };
  }

  extractTaskText(input) {
    // Remove common prefixes and time/priority indicators
    const cleaningPatterns = [
      /^(add task|create task|new task|remind me to|i need to|todo)\s+/i,
      /\s+(today|tomorrow|next week|this afternoon|tonight|high priority|urgent|low priority).*$/i,
      /\s+(at \d+|in \d+ (minutes?|hours?|days?)).*$/i
    ];

    let cleaned = input;
    cleaningPatterns.forEach(pattern => {
      cleaned = cleaned.replace(pattern, '').trim();
    });

    // Extract the core task before temporal/priority modifiers
    const taskMatch = cleaned.match(/^([^,]+?)(?:\s+(?:by|before|at|on|today|tomorrow|next|this|high|low|urgent).*)?$/i);

    return taskMatch ? taskMatch[1].trim() : cleaned;
  }

  parseTimeInfo(input) {
    const result = {
      dueDate: null,
      dueTime: null,
      isRecurring: false,
      recurrencePattern: null
    };

    // Use chrono-node for date/time parsing
    const parsed = chrono.parse(input);

    if (parsed.length > 0) {
      const dateTime = parsed[0];
      result.dueDate = dateTime.start.date();

      // Extract time if specified
      if (dateTime.start.get('hour') !== undefined) {
        const hour = dateTime.start.get('hour');
        const minute = dateTime.start.get('minute') || 0;
        result.dueTime = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
      }
    }

    // Check for recurring patterns
    const recurringPatterns = {
      'daily': { type: 'daily', interval: 1 },
      'every day': { type: 'daily', interval: 1 },
      'weekly': { type: 'weekly', interval: 1 },
      'every week': { type: 'weekly', interval: 1 },
      'monthly': { type: 'monthly', interval: 1 },
      'every month': { type: 'monthly', interval: 1 },
      'every morning': { type: 'daily', interval: 1, time: '09:00' },
      'every evening': { type: 'daily', interval: 1, time: '18:00' }
    };

    for (const [pattern, config] of Object.entries(recurringPatterns)) {
      if (input.toLowerCase().includes(pattern)) {
        result.isRecurring = true;
        result.recurrencePattern = config;
        break;
      }
    }

    // Handle relative time expressions
    this.parseRelativeTime(input, result);

    return result;
  }

  parseRelativeTime(input, result) {
    const relativePatterns = [
      { pattern: /in (\d+) (minutes?|hours?|days?|weeks?)/i, handler: this.handleRelativeTime },
      { pattern: /(tomorrow) (morning|afternoon|evening)/i, handler: this.handleNamedTime },
      { pattern: /(today|tonight|this (morning|afternoon|evening))/i, handler: this.handleToday }
    ];

    relativePatterns.forEach(({ pattern, handler }) => {
      const match = input.match(pattern);
      if (match) {
        handler.call(this, match, result);
      }
    });
  }

  handleRelativeTime(match, result) {
    const [, amount, unit] = match;
    const now = new Date();

    const timeUnits = {
      'minute': 60 * 1000,
      'minutes': 60 * 1000,
      'hour': 60 * 60 * 1000,
      'hours': 60 * 60 * 1000,
      'day': 24 * 60 * 60 * 1000,
      'days': 24 * 60 * 60 * 1000,
      'week': 7 * 24 * 60 * 60 * 1000,
      'weeks': 7 * 24 * 60 * 60 * 1000
    };

    const multiplier = timeUnits[unit.toLowerCase()];
    if (multiplier) {
      result.dueDate = new Date(now.getTime() + (parseInt(amount) * multiplier));
    }
  }

  handleNamedTime(match, result) {
    const [, day, timeOfDay] = match;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);

    const times = {
      'morning': '09:00',
      'afternoon': '14:00',
      'evening': '18:00'
    };

    result.dueDate = tomorrow;
    result.dueTime = times[timeOfDay.toLowerCase()];
  }

  handleToday(match, result) {
    const [, timeIndicator, timeOfDay] = match;
    const today = new Date();

    const times = {
      'morning': '09:00',
      'afternoon': '14:00',
      'evening': '18:00',
      'tonight': '20:00'
    };

    result.dueDate = today;

    if (timeOfDay) {
      result.dueTime = times[timeOfDay.toLowerCase()];
    } else if (timeIndicator === 'tonight') {
      result.dueTime = times['tonight'];
    }
  }

  extractPriority(input) {
    for (const [keyword, priority] of Object.entries(this.priorities)) {
      if (input.includes(keyword)) {
        return priority;
      }
    }
    return 3; // Default to medium priority
  }

  extractCategory(input) {
    for (const category of this.categories) {
      if (input.includes(category)) {
        return category;
      }
    }

    // Smart category inference
    const workKeywords = ['meeting', 'email', 'presentation', 'report', 'call', 'client'];
    const personalKeywords = ['grocery', 'shopping', 'doctor', 'dentist', 'birthday'];
    const homeKeywords = ['clean', 'laundry', 'dishes', 'vacuum', 'organize'];

    if (workKeywords.some(keyword => input.includes(keyword))) return 'work';
    if (personalKeywords.some(keyword => input.includes(keyword))) return 'personal';
    if (homeKeywords.some(keyword => input.includes(keyword))) return 'home';

    return 'general';
  }

  extractLocation(input) {
    const locationPatterns = [
      /at ([\w\s]+?)(?:\s+(?:by|before|at|on|today|tomorrow)|\s*$)/i,
      /@([\w\s]+?)(?:\s+(?:by|before|at|on|today|tomorrow)|\s*$)/i
    ];

    for (const pattern of locationPatterns) {
      const match = input.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }

    return null;
  }

  extractDuration(input) {
    const durationPattern = /(?:takes?|will take|duration|for) (\d+) (minutes?|hours?)/i;
    const match = input.match(durationPattern);

    if (match) {
      const [, amount, unit] = match;
      const minutes = unit.startsWith('hour') ? parseInt(amount) * 60 : parseInt(amount);
      return minutes;
    }

    return null;
  }

  extractReminderInfo(input) {
    const reminderPatterns = [
      { pattern: /remind me (\d+) (minutes?|hours?) before/i, type: 'relative' },
      { pattern: /notify me (today|tomorrow) (morning|afternoon|evening)/i, type: 'named' },
      { pattern: /alert me at (\d{1,2}):?(\d{2})?\s*(am|pm)?/i, type: 'absolute' }
    ];

    for (const { pattern, type } of reminderPatterns) {
      const match = input.match(pattern);
      if (match) {
        return {
          type,
          time: this.calculateReminderTime(match, type),
          original: match[0]
        };
      }
    }

    return { type: null, time: null };
  }

  calculateReminderTime(match, type) {
    switch (type) {
      case 'relative':
        const [, amount, unit] = match;
        const minutes = unit.startsWith('hour') ? parseInt(amount) * 60 : parseInt(amount);
        return new Date(Date.now() + minutes * 60 * 1000);

      case 'absolute':
        const [, hour, minute = '00', ampm = ''] = match;
        const reminderTime = new Date();
        let hour24 = parseInt(hour);

        if (ampm.toLowerCase() === 'pm' && hour24 !== 12) hour24 += 12;
        if (ampm.toLowerCase() === 'am' && hour24 === 12) hour24 = 0;

        reminderTime.setHours(hour24, parseInt(minute), 0, 0);
        return reminderTime;

      default:
        return null;
    }
  }

  extractTags(input) {
    const tagPattern = /#(\w+)/g;
    const tags = [];
    let match;

    while ((match = tagPattern.exec(input)) !== null) {
      tags.push(match[1].toLowerCase());
    }

    return tags;
  }

  generateDescription(originalInput, parsedData) {
    const parts = [`Original: "${originalInput}"`];

    if (parsedData.timing.dueDate) {
      parts.push(`Due: ${parsedData.timing.dueDate.toLocaleDateString()}`);
    }

    if (parsedData.priority !== 3) {
      parts.push(`Priority: ${Object.keys(this.priorities)[parsedData.priority - 1]}`);
    }

    if (parsedData.category !== 'general') {
      parts.push(`Category: ${parsedData.category}`);
    }

    return parts.join(' • ');
  }

  async parseUpdateCommand(input) {
    const normalizedInput = input.toLowerCase().trim();

    // Extract task identifier
    const taskIdentifier = this.extractTaskIdentifier(normalizedInput);

    // Determine update type
    const updateType = this.determineUpdateType(normalizedInput);

    // Extract new values
    const updates = {};

    switch (updateType) {
      case 'complete':
        updates.completed = true;
        updates.completedAt = new Date();
        break;

      case 'reschedule':
        const newTiming = this.parseTimeInfo(normalizedInput);
        updates.dueDate = newTiming.dueDate;
        updates.dueTime = newTiming.dueTime;
        break;

      case 'change_priority':
        updates.priority = this.extractPriority(normalizedInput);
        break;

      case 'add_note':
        updates.notes = this.extractNote(normalizedInput);
        break;
    }

    return {
      taskIdentifier,
      updateType,
      updates
    };
  }

  extractTaskIdentifier(input) {
    // Try to extract task title, ID, or index reference
    const patterns = [
      /(?:task|item)\s+(\d+)/i,           // "task 3"
      /"([^"]+)"/,                        // "quoted task name"
      /(?:complete|mark|finish)\s+(.+?)(?:\s+as|\s*$)/i, // "complete writing report"
      /(?:reschedule|move|change)\s+(.+?)(?:\s+to|\s*$)/i // "reschedule meeting"
    ];

    for (const pattern of patterns) {
      const match = input.match(pattern);
      if (match) {
        return match[1].trim();
      }
    }

    return null;
  }

  determineUpdateType(input) {
    const patterns = {
      'complete': /(?:complete|mark.*done|finish|check off)/i,
      'reschedule': /(?:reschedule|move|change.*time|postpone)/i,
      'change_priority': /(?:priority|urgent|important|low)/i,
      'add_note': /(?:add note|note that|remember)/i
    };

    for (const [type, pattern] of Object.entries(patterns)) {
      if (pattern.test(input)) {
        return type;
      }
    }

    return 'unknown';
  }

  extractNote(input) {
    const notePattern = /(?:add note|note that|remember)\s+(.+)$/i;
    const match = input.match(notePattern);
    return match ? match[1].trim() : null;
  }
}
