/**
 * Calendar System - Main Coordinator
 *
 * Comprehensive calendar integration supporting multiple providers,
 * natural language queries, and tier-based access control.
 */

import { GoogleCalendar } from './google.js';
import { ICalCalendar } from './ical.js';
import { CalendarQueries } from './queries.js';
import { CalendarBriefings } from './briefings.js';
import { getUserById } from '../users.js';
import { createClient } from '@libsql/client';

export class CalendarSystem {
  constructor(env) {
    this.env = env;
    this.google = new GoogleCalendar(env);
    this.ical = new ICalCalendar(env);
    this.queries = new CalendarQueries(env);
    this.briefings = new CalendarBriefings(env);
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
   * Connect a calendar provider for a user
   *
   * @param {string} userId - User ID
   * @param {string} provider - Provider name (google, ical)
   * @param {Object} credentials - Provider-specific credentials
   * @returns {Promise<Object>} Connection result
   */
  async connectProvider(userId, provider, credentials) {
    const user = await getUserById(userId, this.env);
    if (!user) {
      throw new Error('User not found');
    }

    const tier = user.subscription_tier || 'free';

    switch (provider) {
      case 'google':
        return await this.google.connect(userId, credentials, tier);
      case 'ical':
        return await this.ical.connect(userId, credentials);
      default:
        throw new Error(`Unsupported calendar provider: ${provider}`);
    }
  }

  /**
   * Process natural language calendar query
   *
   * @param {string} userId - User ID
   * @param {string} query - Natural language query
   * @param {Object} options - Optional query parameters
   * @returns {Promise<Object>} Query results
   */
  async queryCalendar(userId, query, options = {}) {
    return await this.queries.processQuery(userId, query, options);
  }

  /**
   * Generate daily briefing for a user
   *
   * @param {string} userId - User ID
   * @param {Date} date - Date for briefing (defaults to today)
   * @returns {Promise<Object>} Daily briefing data
   */
  async getDailyBriefing(userId, date = new Date()) {
    return await this.briefings.generateDailyBriefing(userId, date);
  }

  /**
   * Create a calendar event (requires Personal tier+)
   *
   * @param {string} userId - User ID
   * @param {Object} eventData - Event details
   * @returns {Promise<Object>} Created event
   */
  async createEvent(userId, eventData) {
    const user = await getUserById(userId, this.env);
    if (!user) {
      throw new Error('User not found');
    }

    const tier = user.subscription_tier || 'free';
    const writeTiers = ['personal', 'professional', 'enterprise'];

    if (!writeTiers.includes(tier)) {
      throw new Error('Calendar write access requires Personal tier or higher');
    }

    return await this.google.createEvent(userId, eventData);
  }

  /**
   * Get all calendar integrations for a user
   *
   * @param {string} userId - User ID
   * @returns {Promise<Array>} Array of integrations
   */
  async getIntegrations(userId) {
    const db = this.getDb();

    const result = await db.execute({
      sql: `
        SELECT * FROM calendar_integrations
        WHERE user_id = ?
        ORDER BY created_at DESC
      `,
      args: [userId],
    });

    return result.rows.map(row => ({
      id: row.id,
      provider: row.provider,
      providerAccountId: row.provider_account_id,
      syncEnabled: row.sync_enabled,
      lastSync: row.last_sync,
      syncError: row.sync_error,
      createdAt: row.created_at,
    }));
  }

  /**
   * Disconnect a calendar provider
   *
   * @param {string} userId - User ID
   * @param {string} provider - Provider name
   * @returns {Promise<void>}
   */
  async disconnectProvider(userId, provider) {
    const db = this.getDb();

    // Delete integration
    await db.execute({
      sql: 'DELETE FROM calendar_integrations WHERE user_id = ? AND provider = ?',
      args: [userId, provider],
    });

    // Delete cached events from this provider
    await db.execute({
      sql: 'DELETE FROM calendar_events WHERE user_id = ? AND provider = ?',
      args: [userId, provider],
    });

    console.log(`Disconnected ${provider} calendar for user ${userId}`);
  }

  /**
   * Sync calendar events from all connected providers
   *
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Sync results
   */
  async syncCalendars(userId) {
    const integrations = await this.getIntegrations(userId);
    const results = {
      synced: [],
      errors: [],
    };

    for (const integration of integrations) {
      if (!integration.syncEnabled) {
        continue;
      }

      try {
        let syncResult;
        switch (integration.provider) {
          case 'google':
            syncResult = await this.google.syncEvents(userId);
            break;
          case 'ical':
            syncResult = await this.ical.syncEvents(userId);
            break;
          default:
            throw new Error(`Unsupported provider: ${integration.provider}`);
        }

        results.synced.push({
          provider: integration.provider,
          eventsCount: syncResult.eventsCount,
        });
      } catch (error) {
        results.errors.push({
          provider: integration.provider,
          error: error.message,
        });

        // Update sync error in database
        await this.updateSyncError(integration.id, error.message);
      }
    }

    return results;
  }

  /**
   * Update sync error for an integration
   *
   * @param {number} integrationId - Integration ID
   * @param {string} error - Error message
   */
  async updateSyncError(integrationId, error) {
    const db = this.getDb();

    await db.execute({
      sql: `
        UPDATE calendar_integrations
        SET sync_error = ?,
            last_sync = CURRENT_TIMESTAMP
        WHERE id = ?
      `,
      args: [error, integrationId],
    });
  }
}
