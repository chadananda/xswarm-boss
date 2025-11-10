/**
 * Google Calendar Integration
 *
 * OAuth2-based calendar integration with token management and auto-refresh.
 * Supports both read-only (Free tier) and read/write (Personal+ tiers).
 */

import { google } from 'googleapis';
import { OAuth2Client } from 'google-auth-library';
import { createClient } from '@libsql/client';

export class GoogleCalendar {
  constructor(env) {
    this.env = env;
    this.oauth2Client = new OAuth2Client(
      env.GOOGLE_CLIENT_ID,
      env.GOOGLE_CLIENT_SECRET,
      env.GOOGLE_REDIRECT_URI
    );
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
   * Generate OAuth URL for user to authorize
   *
   * @param {string} userId - User ID
   * @param {string} scopes - Scope level (readonly or readwrite)
   * @returns {string} Authorization URL
   */
  async getAuthUrl(userId, scopes = 'readonly') {
    const scopeMap = {
      readonly: ['https://www.googleapis.com/auth/calendar.readonly'],
      readwrite: [
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events'
      ]
    };

    const authUrl = this.oauth2Client.generateAuthUrl({
      access_type: 'offline',
      scope: scopeMap[scopes] || scopeMap.readonly,
      state: userId,
      prompt: 'consent'
    });

    return authUrl;
  }

  /**
   * Handle OAuth callback and store tokens
   *
   * @param {string} code - Authorization code from OAuth callback
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Connection result
   */
  async handleCallback(code, userId) {
    try {
      const { tokens } = await this.oauth2Client.getToken(code);

      // Store tokens in database
      await this.storeTokens(userId, tokens);

      // Test connection by fetching calendars
      await this.testConnection(userId);

      return {
        success: true,
        message: 'Google Calendar connected successfully'
      };
    } catch (error) {
      console.error('Google Calendar connection error:', error);
      throw new Error(`Google Calendar connection failed: ${error.message}`);
    }
  }

  /**
   * Test calendar connection by fetching calendar list
   *
   * @param {string} userId - User ID
   * @returns {Promise<void>}
   */
  async testConnection(userId) {
    const tokens = await this.getStoredTokens(userId);
    this.oauth2Client.setCredentials(tokens);

    const calendar = google.calendar({ version: 'v3', auth: this.oauth2Client });

    await calendar.calendarList.list();
  }

  /**
   * Get calendar events within time range
   *
   * @param {string} userId - User ID
   * @param {Object} options - Query options
   * @returns {Promise<Array>} Array of formatted events
   */
  async getEvents(userId, options = {}) {
    const {
      timeMin = new Date().toISOString(),
      timeMax = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      maxResults = 50,
      calendarId = 'primary'
    } = options;

    const tokens = await this.getStoredTokens(userId);
    this.oauth2Client.setCredentials(tokens);

    const calendar = google.calendar({ version: 'v3', auth: this.oauth2Client });

    try {
      const response = await calendar.events.list({
        calendarId,
        timeMin,
        timeMax,
        maxResults,
        singleEvents: true,
        orderBy: 'startTime',
      });

      // Cache events in database
      await this.cacheEvents(userId, response.data.items || []);

      return this.formatEvents(response.data.items || []);
    } catch (error) {
      if (error.code === 401 || error.response?.status === 401) {
        // Token expired, try to refresh
        await this.refreshTokens(userId);
        return this.getEvents(userId, options); // Retry once
      }
      throw error;
    }
  }

  /**
   * Create a calendar event (requires write access)
   *
   * @param {string} userId - User ID
   * @param {Object} eventData - Event details
   * @returns {Promise<Object>} Created event
   */
  async createEvent(userId, eventData) {
    const tokens = await this.getStoredTokens(userId);
    this.oauth2Client.setCredentials(tokens);

    const calendar = google.calendar({ version: 'v3', auth: this.oauth2Client });

    const event = {
      summary: eventData.title,
      description: eventData.description,
      location: eventData.location,
      start: {
        dateTime: eventData.startTime,
        timeZone: eventData.timeZone || 'America/New_York',
      },
      end: {
        dateTime: eventData.endTime,
        timeZone: eventData.timeZone || 'America/New_York',
      },
      attendees: eventData.attendees?.map(email => ({ email })),
    };

    try {
      const response = await calendar.events.insert({
        calendarId: 'primary',
        resource: event,
        conferenceDataVersion: 1, // Enable Google Meet creation if needed
      });

      // Cache the created event
      await this.cacheEvents(userId, [response.data]);

      return this.formatEvent(response.data);
    } catch (error) {
      if (error.code === 401 || error.response?.status === 401) {
        await this.refreshTokens(userId);
        return this.createEvent(userId, eventData); // Retry once
      }
      throw error;
    }
  }

  /**
   * Sync events from Google Calendar to local cache
   *
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Sync result
   */
  async syncEvents(userId) {
    const now = new Date();
    const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    const threeMonthsAhead = new Date(now.getTime() + 90 * 24 * 60 * 60 * 1000);

    const events = await this.getEvents(userId, {
      timeMin: oneMonthAgo.toISOString(),
      timeMax: threeMonthsAhead.toISOString(),
      maxResults: 250,
    });

    // Update last sync timestamp
    await this.updateLastSync(userId);

    return {
      success: true,
      eventsCount: events.length,
    };
  }

  /**
   * Refresh OAuth tokens
   *
   * @param {string} userId - User ID
   * @returns {Promise<Object>} New credentials
   */
  async refreshTokens(userId) {
    const tokens = await this.getStoredTokens(userId);

    if (!tokens.refresh_token) {
      throw new Error('No refresh token available. Please reconnect your Google Calendar.');
    }

    this.oauth2Client.setCredentials(tokens);

    try {
      const { credentials } = await this.oauth2Client.refreshAccessToken();
      await this.storeTokens(userId, { ...tokens, ...credentials });
      return credentials;
    } catch (error) {
      console.error('Token refresh error:', error);
      throw new Error(`Failed to refresh Google Calendar tokens: ${error.message}`);
    }
  }

  /**
   * Store OAuth tokens in database
   *
   * @param {string} userId - User ID
   * @param {Object} tokens - OAuth tokens
   */
  async storeTokens(userId, tokens) {
    const db = this.getDb();

    const expiresAt = tokens.expiry_date
      ? new Date(tokens.expiry_date).toISOString()
      : null;

    await db.execute({
      sql: `
        INSERT INTO calendar_integrations (
          user_id, provider, access_token, refresh_token, token_expires_at
        ) VALUES (?, 'google', ?, ?, ?)
        ON CONFLICT (user_id, provider, provider_account_id) DO UPDATE SET
          access_token = excluded.access_token,
          refresh_token = COALESCE(excluded.refresh_token, refresh_token),
          token_expires_at = excluded.token_expires_at,
          last_sync = CURRENT_TIMESTAMP
      `,
      args: [userId, tokens.access_token, tokens.refresh_token, expiresAt],
    });
  }

  /**
   * Get stored OAuth tokens from database
   *
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Stored tokens
   */
  async getStoredTokens(userId) {
    const db = this.getDb();

    const result = await db.execute({
      sql: `
        SELECT access_token, refresh_token, token_expires_at
        FROM calendar_integrations
        WHERE user_id = ? AND provider = 'google'
      `,
      args: [userId],
    });

    if (result.rows.length === 0) {
      throw new Error('Google Calendar not connected. Please connect your calendar first.');
    }

    const row = result.rows[0];

    return {
      access_token: row.access_token,
      refresh_token: row.refresh_token,
      expiry_date: row.token_expires_at ? new Date(row.token_expires_at).getTime() : null,
    };
  }

  /**
   * Cache events in database
   *
   * @param {string} userId - User ID
   * @param {Array} events - Array of Google Calendar events
   */
  async cacheEvents(userId, events) {
    if (!events || events.length === 0) {
      return;
    }

    const db = this.getDb();

    for (const event of events) {
      try {
        const attendees = event.attendees?.map(a => ({
          email: a.email,
          name: a.displayName,
          status: a.responseStatus
        })) || [];

        const organizer = event.organizer ? {
          email: event.organizer.email,
          name: event.organizer.displayName
        } : null;

        await db.execute({
          sql: `
            INSERT INTO calendar_events (
              user_id, provider, provider_event_id, title, description, location,
              start_time, end_time, all_day, timezone,
              attendees, organizer, status, html_link, meet_link, synced_at
            ) VALUES (?, 'google', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, provider, provider_event_id) DO UPDATE SET
              title = excluded.title,
              description = excluded.description,
              location = excluded.location,
              start_time = excluded.start_time,
              end_time = excluded.end_time,
              all_day = excluded.all_day,
              attendees = excluded.attendees,
              organizer = excluded.organizer,
              status = excluded.status,
              html_link = excluded.html_link,
              meet_link = excluded.meet_link,
              synced_at = CURRENT_TIMESTAMP
          `,
          args: [
            userId,
            event.id,
            event.summary || 'Untitled Event',
            event.description || null,
            event.location || null,
            event.start?.dateTime || event.start?.date,
            event.end?.dateTime || event.end?.date,
            !event.start?.dateTime, // all_day if no time specified
            event.start?.timeZone || 'America/New_York',
            JSON.stringify(attendees),
            JSON.stringify(organizer),
            event.status || 'confirmed',
            event.htmlLink || null,
            event.hangoutLink || event.conferenceData?.entryPoints?.[0]?.uri || null,
          ],
        });
      } catch (error) {
        console.error(`Error caching event ${event.id}:`, error);
        // Continue with other events
      }
    }
  }

  /**
   * Update last sync timestamp
   *
   * @param {string} userId - User ID
   */
  async updateLastSync(userId) {
    const db = this.getDb();

    await db.execute({
      sql: `
        UPDATE calendar_integrations
        SET last_sync = CURRENT_TIMESTAMP,
            sync_error = NULL
        WHERE user_id = ? AND provider = 'google'
      `,
      args: [userId],
    });
  }

  /**
   * Format Google Calendar events to standard format
   *
   * @param {Array} events - Google Calendar events
   * @returns {Array} Formatted events
   */
  formatEvents(events) {
    return events.map(event => this.formatEvent(event));
  }

  /**
   * Format single Google Calendar event
   *
   * @param {Object} event - Google Calendar event
   * @returns {Object} Formatted event
   */
  formatEvent(event) {
    return {
      id: event.id,
      provider: 'google',
      title: event.summary || 'Untitled Event',
      description: event.description,
      startTime: event.start?.dateTime || event.start?.date,
      endTime: event.end?.dateTime || event.end?.date,
      allDay: !event.start?.dateTime,
      location: event.location,
      attendees: event.attendees?.map(a => ({
        email: a.email,
        name: a.displayName,
        status: a.responseStatus
      })) || [],
      organizer: event.organizer ? {
        email: event.organizer.email,
        name: event.organizer.displayName
      } : null,
      status: event.status,
      htmlLink: event.htmlLink,
      meetLink: event.hangoutLink || event.conferenceData?.entryPoints?.[0]?.uri,
    };
  }

  /**
   * Connect Google Calendar for a user
   *
   * @param {string} userId - User ID
   * @param {Object} credentials - OAuth credentials
   * @param {string} tier - User's subscription tier
   * @returns {Promise<Object>} Connection result
   */
  async connect(userId, credentials, tier) {
    // Determine scope based on tier
    const writeTiers = ['personal', 'professional', 'enterprise'];
    const scope = writeTiers.includes(tier) ? 'readwrite' : 'readonly';

    if (credentials.code) {
      // OAuth callback with code
      return await this.handleCallback(credentials.code, userId);
    } else {
      // Generate auth URL
      const authUrl = await this.getAuthUrl(userId, scope);
      return {
        success: false,
        authUrl,
        message: 'Please authorize Google Calendar access',
      };
    }
  }
}
