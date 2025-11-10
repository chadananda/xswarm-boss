/**
 * Calendar Natural Language Queries
 *
 * Process voice-friendly calendar queries using chrono-node for time parsing.
 * Supports queries like "What's on my calendar today?" and "Am I free tomorrow at 2pm?"
 */

import chrono from 'chrono-node';
import { createClient } from '@libsql/client';

export class CalendarQueries {
  constructor(env) {
    this.env = env;
    this.dbClient = null;
  }

  /**
   * Get database client
   */
  getDb() {
    if (!this.dbClient) {
      this.dbClient = createClient({
        url: this.env.TURSO_DATABASE_URL,
        authToken: this.env.TURSO_AUTH_TOKEN,
      });
    }
    return this.dbClient;
  }

  /**
   * Process natural language calendar query
   *
   * @param {string} userId - User ID
   * @param {string} query - Natural language query
   * @param {Object} options - Optional parameters
   * @returns {Promise<Object>} Query results
   */
  async processQuery(userId, query, options = {}) {
    const normalizedQuery = query.toLowerCase().trim();

    // Parse temporal references using chrono-node
    const timeContext = this.parseTimeContext(normalizedQuery);

    // Determine query type
    const queryType = this.determineQueryType(normalizedQuery);

    // Execute appropriate query
    let result;
    switch (queryType) {
      case 'list_events':
        result = await this.listEvents(userId, timeContext);
        break;
      case 'find_conflicts':
        result = await this.findConflicts(userId, timeContext);
        break;
      case 'check_availability':
        result = await this.checkAvailability(userId, timeContext);
        break;
      case 'find_meeting_time':
        result = await this.findMeetingTime(userId, normalizedQuery, timeContext);
        break;
      case 'get_next_event':
        result = await this.getNextEvent(userId);
        break;
      default:
        result = await this.handleGenericQuery(userId, normalizedQuery, timeContext);
    }

    // Log query for analytics
    await this.logQuery(userId, query, queryType, result);

    return result;
  }

  /**
   * Parse time context from natural language
   *
   * @param {string} query - Query text
   * @returns {Object} Time context with start/end dates
   */
  parseTimeContext(query) {
    // Use chrono-node for natural language date parsing
    const parsed = chrono.parse(query);

    if (parsed.length > 0) {
      const date = parsed[0];
      return {
        start: date.start.date(),
        end: date.end?.date() || new Date(date.start.date().getTime() + 24 * 60 * 60 * 1000),
        text: date.text,
      };
    }

    // Handle common time references manually
    const timePatterns = {
      'today': () => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const end = new Date(today);
        end.setHours(23, 59, 59, 999);
        return { start: today, end };
      },
      'tomorrow': () => {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        tomorrow.setHours(0, 0, 0, 0);
        const end = new Date(tomorrow);
        end.setHours(23, 59, 59, 999);
        return { start: tomorrow, end };
      },
      'this week': () => {
        const now = new Date();
        const start = new Date(now);
        start.setDate(now.getDate() - now.getDay()); // Start of week (Sunday)
        start.setHours(0, 0, 0, 0);
        const end = new Date(start);
        end.setDate(start.getDate() + 7);
        return { start, end };
      },
      'next week': () => {
        const now = new Date();
        const start = new Date(now);
        start.setDate(now.getDate() - now.getDay() + 7); // Start of next week
        start.setHours(0, 0, 0, 0);
        const end = new Date(start);
        end.setDate(start.getDate() + 7);
        return { start, end };
      },
    };

    for (const [pattern, generator] of Object.entries(timePatterns)) {
      if (query.includes(pattern)) {
        return generator();
      }
    }

    // Default to today
    return timePatterns['today']();
  }

  /**
   * Determine query type from natural language
   *
   * @param {string} query - Query text
   * @returns {string} Query type
   */
  determineQueryType(query) {
    const patterns = {
      'list_events': /what['s]?\s+(on|do\s+i\s+have|are\s+my|events?|meetings?|appointments?|scheduled|calendar)/i,
      'find_conflicts': /(conflicts?|overlapping|clash|double.?booked)/i,
      'check_availability': /(available|free|busy|open)/i,
      'find_meeting_time': /(when\s+can|find\s+time|schedule\s+meeting)/i,
      'get_next_event': /(next\s+meeting|what['s]?\s+next|upcoming)/i,
    };

    for (const [type, pattern] of Object.entries(patterns)) {
      if (pattern.test(query)) {
        return type;
      }
    }

    return 'list_events'; // Default
  }

  /**
   * List events within time range
   *
   * @param {string} userId - User ID
   * @param {Object} timeContext - Time range
   * @returns {Promise<Object>} Event list
   */
  async listEvents(userId, timeContext) {
    const events = await this.getEventsInRange(userId, timeContext.start, timeContext.end);

    if (events.length === 0) {
      return {
        type: 'no_events',
        message: `You have no events ${this.formatTimeContext(timeContext)}`,
        events: [],
      };
    }

    return {
      type: 'event_list',
      message: `You have ${events.length} event${events.length > 1 ? 's' : ''} ${this.formatTimeContext(timeContext)}`,
      events,
      summary: this.generateEventSummary(events),
    };
  }

  /**
   * Get next upcoming event
   *
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Next event
   */
  async getNextEvent(userId) {
    const now = new Date();
    const endOfDay = new Date(now);
    endOfDay.setHours(23, 59, 59, 999);

    const events = await this.getEventsInRange(userId, now, endOfDay);
    const upcomingEvents = events
      .filter(event => new Date(event.start_time) > now)
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    if (upcomingEvents.length === 0) {
      return {
        type: 'no_next_event',
        message: 'You have no more events today',
        nextEvent: null,
      };
    }

    const nextEvent = upcomingEvents[0];
    const timeUntil = this.formatTimeUntil(new Date(nextEvent.start_time));

    return {
      type: 'next_event',
      message: `Your next event is "${nextEvent.title}" ${timeUntil}`,
      nextEvent: this.formatEventForResponse(nextEvent),
      timeUntil,
    };
  }

  /**
   * Check availability in time range
   *
   * @param {string} userId - User ID
   * @param {Object} timeContext - Time range
   * @returns {Promise<Object>} Availability status
   */
  async checkAvailability(userId, timeContext) {
    const events = await this.getEventsInRange(userId, timeContext.start, timeContext.end);

    if (events.length === 0) {
      return {
        type: 'available',
        message: `You're free ${this.formatTimeContext(timeContext)}`,
        available: true,
        events: [],
      };
    }

    return {
      type: 'busy',
      message: `You have ${events.length} event${events.length > 1 ? 's' : ''} ${this.formatTimeContext(timeContext)}`,
      available: false,
      events: events.map(e => this.formatEventForResponse(e)),
    };
  }

  /**
   * Find scheduling conflicts
   *
   * @param {string} userId - User ID
   * @param {Object} timeContext - Time range
   * @returns {Promise<Object>} Conflicts found
   */
  async findConflicts(userId, timeContext) {
    const events = await this.getEventsInRange(userId, timeContext.start, timeContext.end);

    const conflicts = [];
    for (let i = 0; i < events.length - 1; i++) {
      const current = events[i];
      const next = events[i + 1];

      if (this.eventsOverlap(current, next)) {
        conflicts.push({
          event1: this.formatEventForResponse(current),
          event2: this.formatEventForResponse(next),
        });
      }
    }

    if (conflicts.length === 0) {
      return {
        type: 'no_conflicts',
        message: 'No scheduling conflicts found',
        conflicts: [],
      };
    }

    return {
      type: 'conflicts_found',
      message: `Found ${conflicts.length} scheduling conflict${conflicts.length > 1 ? 's' : ''}`,
      conflicts,
    };
  }

  /**
   * Find available meeting time
   *
   * @param {string} userId - User ID
   * @param {string} query - Query text
   * @param {Object} timeContext - Time range
   * @returns {Promise<Object>} Available times
   */
  async findMeetingTime(userId, query, timeContext) {
    // Extract duration from query (default 1 hour)
    const durationMatch = query.match(/(\d+)\s*(hour|hr|minute|min)/i);
    let durationMinutes = 60; // Default 1 hour

    if (durationMatch) {
      const value = parseInt(durationMatch[1]);
      const unit = durationMatch[2].toLowerCase();
      durationMinutes = unit.startsWith('hour') || unit === 'hr' ? value * 60 : value;
    }

    const events = await this.getEventsInRange(userId, timeContext.start, timeContext.end);
    const freeSlots = this.findFreeSlots(events, timeContext, durationMinutes);

    if (freeSlots.length === 0) {
      return {
        type: 'no_free_time',
        message: `No ${durationMinutes}-minute slots available ${this.formatTimeContext(timeContext)}`,
        freeSlots: [],
      };
    }

    return {
      type: 'free_time_found',
      message: `Found ${freeSlots.length} available slot${freeSlots.length > 1 ? 's' : ''} for ${durationMinutes} minutes`,
      freeSlots: freeSlots.slice(0, 5), // Return top 5 slots
      duration: durationMinutes,
    };
  }

  /**
   * Handle generic calendar query
   *
   * @param {string} userId - User ID
   * @param {string} query - Query text
   * @param {Object} timeContext - Time context
   * @returns {Promise<Object>} Query result
   */
  async handleGenericQuery(userId, query, timeContext) {
    // Default to listing events
    return await this.listEvents(userId, timeContext);
  }

  /**
   * Get events within date range from database
   *
   * @param {string} userId - User ID
   * @param {Date} start - Start date
   * @param {Date} end - End date
   * @returns {Promise<Array>} Events
   */
  async getEventsInRange(userId, start, end) {
    const db = this.getDb();

    const result = await db.execute({
      sql: `
        SELECT * FROM calendar_events
        WHERE user_id = ?
          AND start_time >= ?
          AND start_time < ?
          AND status != 'cancelled'
        ORDER BY start_time ASC
      `,
      args: [userId, start.toISOString(), end.toISOString()],
    });

    return result.rows;
  }

  /**
   * Check if two events overlap
   *
   * @param {Object} event1 - First event
   * @param {Object} event2 - Second event
   * @returns {boolean} True if overlapping
   */
  eventsOverlap(event1, event2) {
    const start1 = new Date(event1.start_time);
    const end1 = new Date(event1.end_time);
    const start2 = new Date(event2.start_time);
    const end2 = new Date(event2.end_time);

    return start1 < end2 && start2 < end1;
  }

  /**
   * Find free time slots
   *
   * @param {Array} events - Sorted events
   * @param {Object} timeContext - Time range
   * @param {number} durationMinutes - Required duration
   * @returns {Array} Free slots
   */
  findFreeSlots(events, timeContext, durationMinutes) {
    const slots = [];
    const workStart = 9; // 9 AM
    const workEnd = 17; // 5 PM

    let currentTime = new Date(timeContext.start);
    currentTime.setHours(workStart, 0, 0, 0);

    const endTime = new Date(timeContext.end);
    endTime.setHours(workEnd, 0, 0, 0);

    for (const event of events) {
      const eventStart = new Date(event.start_time);

      // Check if there's a free slot before this event
      if (currentTime < eventStart) {
        const freeMinutes = (eventStart - currentTime) / (1000 * 60);
        if (freeMinutes >= durationMinutes) {
          slots.push({
            start: new Date(currentTime).toISOString(),
            end: new Date(currentTime.getTime() + durationMinutes * 60 * 1000).toISOString(),
            durationMinutes: Math.min(freeMinutes, durationMinutes),
          });
        }
      }

      // Move current time to end of this event
      currentTime = new Date(Math.max(currentTime, new Date(event.end_time)));
    }

    // Check for free time after last event
    if (currentTime < endTime) {
      const freeMinutes = (endTime - currentTime) / (1000 * 60);
      if (freeMinutes >= durationMinutes) {
        slots.push({
          start: new Date(currentTime).toISOString(),
          end: new Date(currentTime.getTime() + durationMinutes * 60 * 1000).toISOString(),
          durationMinutes: Math.min(freeMinutes, durationMinutes),
        });
      }
    }

    return slots;
  }

  /**
   * Format time context for human-readable message
   *
   * @param {Object} timeContext - Time context
   * @returns {string} Formatted text
   */
  formatTimeContext(timeContext) {
    const now = new Date();
    const start = timeContext.start;

    if (this.isSameDay(start, now)) {
      return 'today';
    } else if (this.isSameDay(start, new Date(now.getTime() + 24 * 60 * 60 * 1000))) {
      return 'tomorrow';
    } else {
      return `on ${start.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}`;
    }
  }

  /**
   * Format time until event
   *
   * @param {Date} targetTime - Target time
   * @returns {string} Formatted text
   */
  formatTimeUntil(targetTime) {
    const now = new Date();
    const diffMs = targetTime - now;
    const diffMinutes = Math.round(diffMs / (1000 * 60));

    if (diffMinutes < 1) {
      return 'starting now';
    } else if (diffMinutes < 60) {
      return `in ${diffMinutes} minute${diffMinutes > 1 ? 's' : ''}`;
    } else if (diffMinutes < 1440) {
      const hours = Math.round(diffMinutes / 60);
      return `in ${hours} hour${hours > 1 ? 's' : ''}`;
    } else {
      return `at ${targetTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}`;
    }
  }

  /**
   * Check if two dates are same day
   *
   * @param {Date} date1 - First date
   * @param {Date} date2 - Second date
   * @returns {boolean} True if same day
   */
  isSameDay(date1, date2) {
    return date1.toDateString() === date2.toDateString();
  }

  /**
   * Generate event summary
   *
   * @param {Array} events - Events
   * @returns {string} Summary text
   */
  generateEventSummary(events) {
    if (events.length === 0) return '';

    const firstEvent = events[0];
    const firstTime = new Date(firstEvent.start_time).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });

    if (events.length === 1) {
      return `Your event "${firstEvent.title}" starts at ${firstTime}`;
    } else {
      return `Starting with "${firstEvent.title}" at ${firstTime}`;
    }
  }

  /**
   * Format event for response
   *
   * @param {Object} event - Database event
   * @returns {Object} Formatted event
   */
  formatEventForResponse(event) {
    return {
      id: event.id,
      title: event.title,
      description: event.description,
      location: event.location,
      startTime: event.start_time,
      endTime: event.end_time,
      allDay: event.all_day,
      provider: event.provider,
      attendees: event.attendees ? JSON.parse(event.attendees) : [],
      htmlLink: event.html_link,
      meetLink: event.meet_link,
    };
  }

  /**
   * Log query for analytics
   *
   * @param {string} userId - User ID
   * @param {string} query - Query text
   * @param {string} queryType - Query type
   * @param {Object} result - Query result
   */
  async logQuery(userId, query, queryType, result) {
    try {
      const db = this.getDb();

      await db.execute({
        sql: `
          INSERT INTO calendar_queries (
            user_id, query_text, query_type, results_count, response_text
          ) VALUES (?, ?, ?, ?, ?)
        `,
        args: [
          userId,
          query,
          queryType,
          result.events?.length || result.freeSlots?.length || 0,
          result.message,
        ],
      });
    } catch (error) {
      console.error('Error logging calendar query:', error);
      // Don't throw - logging should not break the query
    }
  }
}
