/**
 * Calendar Daily Briefings
 *
 * Generate intelligent daily briefings with conflict detection,
 * free time analysis, and event importance ranking.
 */

import { createClient } from '@libsql/client';

export class CalendarBriefings {
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
   * Generate daily briefing for a user
   *
   * @param {string} userId - User ID
   * @param {Date} date - Date for briefing
   * @returns {Promise<Object>} Daily briefing
   */
  async generateDailyBriefing(userId, date = new Date()) {
    const startOfDay = new Date(date);
    startOfDay.setHours(0, 0, 0, 0);
    const endOfDay = new Date(date);
    endOfDay.setHours(23, 59, 59, 999);

    // Get events for the day
    const events = await this.getEventsInRange(userId, startOfDay, endOfDay);

    if (events.length === 0) {
      const briefing = {
        type: 'no_events',
        message: 'You have a free day with no scheduled events!',
        summary: 'Clear schedule',
        totalEvents: 0,
        totalMeetingMinutes: 0,
        conflicts: [],
        freeTime: [],
        importantEvents: [],
        preparationNeeded: [],
        events: [],
      };

      // Cache briefing
      await this.cacheBriefing(userId, date, briefing);

      return briefing;
    }

    // Analyze schedule
    const analysis = this.analyzeDaySchedule(events, date);

    const briefing = {
      type: 'daily_briefing',
      message: this.generateBriefingMessage(analysis),
      summary: this.generateSummary(analysis),
      ...analysis,
      events: events.map(e => this.formatEvent(e)),
    };

    // Cache briefing
    await this.cacheBriefing(userId, date, briefing);

    return briefing;
  }

  /**
   * Analyze day's schedule for insights
   *
   * @param {Array} events - Day's events
   * @param {Date} date - Date being analyzed
   * @returns {Object} Schedule analysis
   */
  analyzeDaySchedule(events, date) {
    const analysis = {
      totalEvents: events.length,
      totalMeetingMinutes: 0,
      conflicts: [],
      freeTime: [],
      busyPeriods: [],
      importantEvents: [],
      preparationNeeded: [],
    };

    // Sort events by start time
    events.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    // Calculate total meeting time and identify important events
    events.forEach((event, index) => {
      const duration = this.calculateDuration(event);
      analysis.totalMeetingMinutes += duration;

      // Identify important events
      if (this.isImportantEvent(event)) {
        analysis.importantEvents.push(event);
      }

      // Check for conflicts with next event
      if (index < events.length - 1) {
        const nextEvent = events[index + 1];
        if (this.hasConflict(event, nextEvent)) {
          analysis.conflicts.push({
            current: this.formatEvent(event),
            next: this.formatEvent(nextEvent),
          });
        }
      }

      // Check if preparation time needed
      if (this.needsPreparation(event)) {
        analysis.preparationNeeded.push(event);
      }
    });

    // Calculate free time between events
    analysis.freeTime = this.calculateFreeTime(events, date);

    // Identify busy periods (consecutive events)
    analysis.busyPeriods = this.identifyBusyPeriods(events);

    return analysis;
  }

  /**
   * Generate briefing message
   *
   * @param {Object} analysis - Schedule analysis
   * @returns {string} Briefing message
   */
  generateBriefingMessage(analysis) {
    const parts = [];

    // Overview
    if (analysis.totalEvents === 1) {
      parts.push('You have 1 event today');
    } else {
      parts.push(`You have ${analysis.totalEvents} events today`);
    }

    // Meeting time
    const hours = Math.floor(analysis.totalMeetingMinutes / 60);
    const minutes = analysis.totalMeetingMinutes % 60;
    if (hours > 0) {
      parts.push(`totaling ${hours}h ${minutes}m of meetings`);
    } else if (minutes > 0) {
      parts.push(`totaling ${minutes} minutes of meetings`);
    }

    // Conflicts warning
    if (analysis.conflicts.length > 0) {
      parts.push(`WARNING: ${analysis.conflicts.length} scheduling conflict${analysis.conflicts.length > 1 ? 's' : ''} detected`);
    }

    // Important events
    if (analysis.importantEvents.length > 0) {
      const event = analysis.importantEvents[0];
      const time = new Date(event.start_time).toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit'
      });
      parts.push(`Key event: "${event.title}" at ${time}`);
    }

    // Free time
    if (analysis.freeTime.length > 0) {
      const longestFree = Math.max(...analysis.freeTime);
      if (longestFree >= 60) {
        parts.push(`Longest free block: ${Math.floor(longestFree / 60)}h ${longestFree % 60}m`);
      }
    }

    return parts.join('. ') + '.';
  }

  /**
   * Generate summary text
   *
   * @param {Object} analysis - Schedule analysis
   * @returns {string} Summary
   */
  generateSummary(analysis) {
    if (analysis.totalEvents === 0) {
      return 'Clear schedule';
    }

    const density = analysis.totalMeetingMinutes / (9 * 60); // 9 hour workday

    if (density > 0.8) {
      return 'Very busy day';
    } else if (density > 0.5) {
      return 'Moderately busy';
    } else {
      return 'Light schedule';
    }
  }

  /**
   * Calculate event duration in minutes
   *
   * @param {Object} event - Calendar event
   * @returns {number} Duration in minutes
   */
  calculateDuration(event) {
    const start = new Date(event.start_time);
    const end = new Date(event.end_time);
    return Math.round((end - start) / (1000 * 60));
  }

  /**
   * Check if event is important
   *
   * @param {Object} event - Calendar event
   * @returns {boolean} True if important
   */
  isImportantEvent(event) {
    const importantKeywords = [
      'interview', 'presentation', 'board', 'client', 'demo',
      'launch', 'deadline', 'review', 'meeting with ceo', 'executive'
    ];

    const title = event.title.toLowerCase();
    const description = (event.description || '').toLowerCase();

    // Check keywords
    const hasKeyword = importantKeywords.some(keyword =>
      title.includes(keyword) || description.includes(keyword)
    );

    // Check attendee count (5+ attendees = important)
    let attendeeCount = 0;
    if (event.attendees) {
      try {
        const attendees = JSON.parse(event.attendees);
        attendeeCount = Array.isArray(attendees) ? attendees.length : 0;
      } catch (e) {
        // Ignore parse errors
      }
    }

    return hasKeyword || attendeeCount >= 5;
  }

  /**
   * Check if event needs preparation
   *
   * @param {Object} event - Calendar event
   * @returns {boolean} True if prep needed
   */
  needsPreparation(event) {
    const prepKeywords = [
      'presentation', 'demo', 'interview', 'pitch', 'review',
      'prepare', 'preparation', 'present'
    ];

    const title = event.title.toLowerCase();
    const description = (event.description || '').toLowerCase();

    return prepKeywords.some(keyword =>
      title.includes(keyword) || description.includes(keyword)
    );
  }

  /**
   * Check if two events conflict
   *
   * @param {Object} event1 - First event
   * @param {Object} event2 - Second event
   * @returns {boolean} True if overlapping
   */
  hasConflict(event1, event2) {
    const end1 = new Date(event1.end_time);
    const start2 = new Date(event2.start_time);
    return end1 > start2; // Overlap if first ends after second starts
  }

  /**
   * Calculate free time blocks
   *
   * @param {Array} events - Sorted events
   * @param {Date} date - Date
   * @returns {Array} Free time blocks in minutes
   */
  calculateFreeTime(events, date) {
    if (events.length === 0) return [];

    const freeBlocks = [];
    const workStart = 9; // 9 AM
    const workEnd = 18; // 6 PM

    // Free time before first event
    const firstEventStart = new Date(events[0].start_time);
    const dayStart = new Date(date);
    dayStart.setHours(workStart, 0, 0, 0);

    if (firstEventStart > dayStart) {
      const freeMinutes = (firstEventStart - dayStart) / (1000 * 60);
      if (freeMinutes >= 15) { // Only meaningful blocks
        freeBlocks.push(Math.round(freeMinutes));
      }
    }

    // Free time between events
    for (let i = 0; i < events.length - 1; i++) {
      const eventEnd = new Date(events[i].end_time);
      const nextEventStart = new Date(events[i + 1].start_time);

      if (nextEventStart > eventEnd) {
        const freeMinutes = (nextEventStart - eventEnd) / (1000 * 60);
        if (freeMinutes >= 15) {
          freeBlocks.push(Math.round(freeMinutes));
        }
      }
    }

    // Free time after last event
    const lastEventEnd = new Date(events[events.length - 1].end_time);
    const dayEnd = new Date(date);
    dayEnd.setHours(workEnd, 0, 0, 0);

    if (dayEnd > lastEventEnd) {
      const freeMinutes = (dayEnd - lastEventEnd) / (1000 * 60);
      if (freeMinutes >= 15) {
        freeBlocks.push(Math.round(freeMinutes));
      }
    }

    return freeBlocks;
  }

  /**
   * Identify busy periods (back-to-back meetings)
   *
   * @param {Array} events - Sorted events
   * @returns {Array} Busy periods
   */
  identifyBusyPeriods(events) {
    const periods = [];
    let currentPeriod = null;

    for (let i = 0; i < events.length; i++) {
      const event = events[i];
      const nextEvent = events[i + 1];

      if (!currentPeriod) {
        currentPeriod = {
          start: event.start_time,
          end: event.end_time,
          eventCount: 1,
        };
      } else {
        const gapMinutes = nextEvent
          ? (new Date(nextEvent.start_time) - new Date(event.end_time)) / (1000 * 60)
          : Infinity;

        if (gapMinutes < 15) {
          // Part of current busy period
          currentPeriod.end = event.end_time;
          currentPeriod.eventCount++;
        } else {
          // End of busy period
          if (currentPeriod.eventCount >= 2) {
            periods.push(currentPeriod);
          }
          currentPeriod = nextEvent ? {
            start: nextEvent.start_time,
            end: nextEvent.end_time,
            eventCount: 1,
          } : null;
        }
      }
    }

    // Add final period if exists
    if (currentPeriod && currentPeriod.eventCount >= 2) {
      periods.push(currentPeriod);
    }

    return periods;
  }

  /**
   * Get events in date range
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
   * Cache briefing in database
   *
   * @param {string} userId - User ID
   * @param {Date} date - Briefing date
   * @param {Object} briefing - Briefing data
   */
  async cacheBriefing(userId, date, briefing) {
    try {
      const db = this.getDb();

      const briefingDate = date.toISOString().split('T')[0]; // YYYY-MM-DD

      await db.execute({
        sql: `
          INSERT INTO calendar_briefings (
            user_id, briefing_date, summary, total_events, total_meeting_minutes,
            conflicts_count, free_time_blocks, important_events, preparation_needed
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT (user_id, briefing_date) DO UPDATE SET
            summary = excluded.summary,
            total_events = excluded.total_events,
            total_meeting_minutes = excluded.total_meeting_minutes,
            conflicts_count = excluded.conflicts_count,
            free_time_blocks = excluded.free_time_blocks,
            important_events = excluded.important_events,
            preparation_needed = excluded.preparation_needed
        `,
        args: [
          userId,
          briefingDate,
          briefing.summary,
          briefing.totalEvents,
          briefing.totalMeetingMinutes,
          briefing.conflicts?.length || 0,
          JSON.stringify(briefing.freeTime || []),
          JSON.stringify(briefing.importantEvents?.map(e => e.id) || []),
          JSON.stringify(briefing.preparationNeeded?.map(e => e.id) || []),
        ],
      });
    } catch (error) {
      console.error('Error caching briefing:', error);
      // Don't throw - caching failure should not break briefing generation
    }
  }

  /**
   * Format event for response
   *
   * @param {Object} event - Database event
   * @returns {Object} Formatted event
   */
  formatEvent(event) {
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
   * Get cached briefing if available
   *
   * @param {string} userId - User ID
   * @param {Date} date - Briefing date
   * @returns {Promise<Object|null>} Cached briefing or null
   */
  async getCachedBriefing(userId, date) {
    try {
      const db = this.getDb();
      const briefingDate = date.toISOString().split('T')[0];

      const result = await db.execute({
        sql: `
          SELECT * FROM calendar_briefings
          WHERE user_id = ? AND briefing_date = ?
        `,
        args: [userId, briefingDate],
      });

      if (result.rows.length === 0) {
        return null;
      }

      const row = result.rows[0];
      return {
        type: 'daily_briefing',
        summary: row.summary,
        totalEvents: row.total_events,
        totalMeetingMinutes: row.total_meeting_minutes,
        conflictsCount: row.conflicts_count,
        freeTime: JSON.parse(row.free_time_blocks || '[]'),
        importantEvents: JSON.parse(row.important_events || '[]'),
        preparationNeeded: JSON.parse(row.preparation_needed || '[]'),
        delivered: row.delivered,
        deliveredAt: row.delivered_at,
      };
    } catch (error) {
      console.error('Error getting cached briefing:', error);
      return null;
    }
  }
}
