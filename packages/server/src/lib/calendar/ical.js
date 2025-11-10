/**
 * iCal Calendar Integration
 *
 * Read-only calendar subscriptions from iCal URLs.
 * Supports standard .ics format from various providers.
 */

import ical from 'node-ical';
import { createClient } from '@libsql/client';

export class ICalCalendar {
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
   * Add iCal subscription for a user
   *
   * @param {string} userId - User ID
   * @param {string} name - Subscription name
   * @param {string} url - iCal URL
   * @returns {Promise<Object>} Subscription result
   */
  async addSubscription(userId, name, url) {
    // Validate URL
    if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('webcal://')) {
      throw new Error('Invalid iCal URL. Must start with http://, https://, or webcal://');
    }

    // Convert webcal:// to https://
    const cleanUrl = url.replace('webcal://', 'https://');

    // Test the URL by fetching and parsing
    try {
      await this.fetchAndParse(cleanUrl);
    } catch (error) {
      throw new Error(`Failed to fetch iCal feed: ${error.message}`);
    }

    const db = this.getDb();

    // Store subscription
    const result = await db.execute({
      sql: `
        INSERT INTO ical_subscriptions (user_id, name, url, sync_interval_hours)
        VALUES (?, ?, ?, 24)
        RETURNING id
      `,
      args: [userId, name, cleanUrl],
    });

    const subscriptionId = result.rows[0].id;

    // Initial sync
    await this.syncSubscription(userId, subscriptionId);

    return {
      success: true,
      subscriptionId,
      message: 'iCal subscription added successfully',
    };
  }

  /**
   * Sync events from an iCal subscription
   *
   * @param {string} userId - User ID
   * @param {number} subscriptionId - Subscription ID
   * @returns {Promise<Object>} Sync result
   */
  async syncSubscription(userId, subscriptionId) {
    const db = this.getDb();

    // Get subscription details
    const subResult = await db.execute({
      sql: 'SELECT * FROM ical_subscriptions WHERE id = ? AND user_id = ?',
      args: [subscriptionId, userId],
    });

    if (subResult.rows.length === 0) {
      throw new Error('Subscription not found');
    }

    const subscription = subResult.rows[0];

    try {
      // Fetch and parse iCal data
      const events = await this.fetchAndParse(subscription.url);

      // Cache events in database
      await this.cacheEvents(userId, events, subscriptionId);

      // Update last sync timestamp
      await db.execute({
        sql: `
          UPDATE ical_subscriptions
          SET last_sync = CURRENT_TIMESTAMP,
              sync_error = NULL
          WHERE id = ?
        `,
        args: [subscriptionId],
      });

      return {
        success: true,
        eventsCount: events.length,
      };
    } catch (error) {
      // Store sync error
      await db.execute({
        sql: `
          UPDATE ical_subscriptions
          SET sync_error = ?
          WHERE id = ?
        `,
        args: [error.message, subscriptionId],
      });

      throw error;
    }
  }

  /**
   * Sync all active iCal subscriptions for a user
   *
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Sync results
   */
  async syncEvents(userId) {
    const db = this.getDb();

    // Get all active subscriptions
    const result = await db.execute({
      sql: `
        SELECT id FROM ical_subscriptions
        WHERE user_id = ? AND enabled = TRUE
      `,
      args: [userId],
    });

    const results = {
      synced: [],
      errors: [],
    };

    for (const row of result.rows) {
      try {
        const syncResult = await this.syncSubscription(userId, row.id);
        results.synced.push({
          subscriptionId: row.id,
          eventsCount: syncResult.eventsCount,
        });
      } catch (error) {
        results.errors.push({
          subscriptionId: row.id,
          error: error.message,
        });
      }
    }

    return {
      success: results.errors.length === 0,
      ...results,
    };
  }

  /**
   * Fetch and parse iCal data from URL
   *
   * @param {string} url - iCal URL
   * @returns {Promise<Array>} Array of parsed events
   */
  async fetchAndParse(url) {
    try {
      const data = await ical.async.fromURL(url);
      const events = [];

      for (const k in data) {
        const event = data[k];

        // Only process VEVENT components
        if (event.type !== 'VEVENT') {
          continue;
        }

        // Skip events without start time
        if (!event.start) {
          continue;
        }

        // Filter to events within reasonable timeframe (past month to 3 months ahead)
        const now = new Date();
        const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        const threeMonthsAhead = new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000);

        const eventStart = new Date(event.start);

        if (eventStart < oneMonthAgo || eventStart > threeMonthsAhead) {
          continue;
        }

        events.push({
          id: event.uid,
          title: event.summary || 'Untitled Event',
          description: event.description,
          location: event.location,
          startTime: event.start,
          endTime: event.end,
          allDay: event.start?.dateOnly || false,
          organizer: event.organizer ? {
            email: event.organizer.val?.replace('mailto:', ''),
            name: event.organizer.params?.CN,
          } : null,
          attendees: event.attendee ? (Array.isArray(event.attendee) ? event.attendee : [event.attendee]).map(a => ({
            email: a.val?.replace('mailto:', ''),
            name: a.params?.CN,
            status: a.params?.PARTSTAT?.toLowerCase(),
          })) : [],
          status: event.status?.toLowerCase() || 'confirmed',
          recurrence: event.rrule ? event.rrule.toString() : null,
        });
      }

      return events;
    } catch (error) {
      console.error('iCal fetch/parse error:', error);
      throw new Error(`Failed to fetch or parse iCal feed: ${error.message}`);
    }
  }

  /**
   * Cache iCal events in database
   *
   * @param {string} userId - User ID
   * @param {Array} events - Array of parsed iCal events
   * @param {number} subscriptionId - Subscription ID
   */
  async cacheEvents(userId, events, subscriptionId) {
    if (!events || events.length === 0) {
      return;
    }

    const db = this.getDb();

    // First, delete old events from this subscription
    await db.execute({
      sql: `
        DELETE FROM calendar_events
        WHERE user_id = ?
          AND provider = 'ical'
          AND provider_event_id LIKE ?
      `,
      args: [userId, `ical_${subscriptionId}_%`],
    });

    // Insert new events
    for (const event of events) {
      try {
        const providerEventId = `ical_${subscriptionId}_${event.id}`;

        await db.execute({
          sql: `
            INSERT INTO calendar_events (
              user_id, provider, provider_event_id, title, description, location,
              start_time, end_time, all_day, timezone,
              attendees, organizer, status, recurrence_rule, synced_at
            ) VALUES (?, 'ical', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
          `,
          args: [
            userId,
            providerEventId,
            event.title,
            event.description || null,
            event.location || null,
            event.startTime instanceof Date ? event.startTime.toISOString() : event.startTime,
            event.endTime instanceof Date ? event.endTime.toISOString() : event.endTime,
            event.allDay,
            'America/New_York', // Default timezone for iCal
            JSON.stringify(event.attendees || []),
            JSON.stringify(event.organizer),
            event.status,
            event.recurrence,
          ],
        });
      } catch (error) {
        console.error(`Error caching iCal event ${event.id}:`, error);
        // Continue with other events
      }
    }
  }

  /**
   * Get all iCal subscriptions for a user
   *
   * @param {string} userId - User ID
   * @returns {Promise<Array>} Array of subscriptions
   */
  async getSubscriptions(userId) {
    const db = this.getDb();

    const result = await db.execute({
      sql: `
        SELECT * FROM ical_subscriptions
        WHERE user_id = ?
        ORDER BY created_at DESC
      `,
      args: [userId],
    });

    return result.rows.map(row => ({
      id: row.id,
      name: row.name,
      url: row.url,
      syncIntervalHours: row.sync_interval_hours,
      lastSync: row.last_sync,
      syncError: row.sync_error,
      enabled: row.enabled,
      createdAt: row.created_at,
    }));
  }

  /**
   * Remove iCal subscription
   *
   * @param {string} userId - User ID
   * @param {number} subscriptionId - Subscription ID
   */
  async removeSubscription(userId, subscriptionId) {
    const db = this.getDb();

    // Delete events from this subscription
    await db.execute({
      sql: `
        DELETE FROM calendar_events
        WHERE user_id = ?
          AND provider = 'ical'
          AND provider_event_id LIKE ?
      `,
      args: [userId, `ical_${subscriptionId}_%`],
    });

    // Delete subscription
    await db.execute({
      sql: 'DELETE FROM ical_subscriptions WHERE id = ? AND user_id = ?',
      args: [subscriptionId, userId],
    });

    console.log(`Removed iCal subscription ${subscriptionId} for user ${userId}`);
  }

  /**
   * Connect iCal calendar for a user
   *
   * @param {string} userId - User ID
   * @param {Object} credentials - Subscription details (name, url)
   * @returns {Promise<Object>} Connection result
   */
  async connect(userId, credentials) {
    return await this.addSubscription(userId, credentials.name, credentials.url);
  }
}
