/**
 * Gmail Client for Cloudflare Workers
 *
 * Uses Gmail REST API directly via fetch (no googleapis library needed)
 * Supports OAuth2, incremental authorization, and tier-based permissions
 */

import { createClient } from '@libsql/client';

/**
 * Gmail OAuth2 scopes
 */
const SCOPES = {
  readonly: 'https://www.googleapis.com/auth/gmail.readonly',
  compose: 'https://www.googleapis.com/auth/gmail.compose',
  send: 'https://www.googleapis.com/auth/gmail.send',
  modify: 'https://www.googleapis.com/auth/gmail.modify'
};

export class GmailClient {
  constructor(env) {
    this.env = env;
    this.clientId = env.GOOGLE_CLIENT_ID;
    this.clientSecret = env.GOOGLE_CLIENT_SECRET;
    this.redirectUri = env.GOOGLE_REDIRECT_URI;

    this.db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });
  }

  /**
   * Generate OAuth authorization URL
   *
   * @param {string} userId - User ID
   * @param {Array<string>} permissions - Array of permission types: ['readonly', 'compose', 'send']
   * @returns {string} Authorization URL
   */
  getAuthUrl(userId, permissions = ['readonly']) {
    const scopes = permissions.map(perm => SCOPES[perm]).filter(Boolean);

    const params = new URLSearchParams({
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      response_type: 'code',
      scope: scopes.join(' '),
      access_type: 'offline',
      prompt: 'consent',
      include_granted_scopes: 'true', // Incremental authorization
      state: JSON.stringify({ userId, permissions })
    });

    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  /**
   * Exchange authorization code for tokens
   *
   * @param {string} code - Authorization code from OAuth callback
   * @returns {Object} Token response with access_token, refresh_token, expires_in
   */
  async exchangeCodeForTokens(code) {
    const response = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: this.clientId,
        client_secret: this.clientSecret,
        code,
        grant_type: 'authorization_code',
        redirect_uri: this.redirectUri
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Token exchange failed: ${error.error_description || error.error}`);
    }

    return await response.json();
  }

  /**
   * Refresh access token
   *
   * @param {string} refreshToken - Refresh token
   * @returns {Object} New token response
   */
  async refreshAccessToken(refreshToken) {
    const response = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: this.clientId,
        client_secret: this.clientSecret,
        refresh_token: refreshToken,
        grant_type: 'refresh_token'
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Token refresh failed: ${error.error_description || error.error}`);
    }

    return await response.json();
  }

  /**
   * Store OAuth tokens in database
   *
   * @param {string} userId - User ID
   * @param {Object} tokens - Token object from OAuth
   * @param {Array<string>} permissions - Array of permission types
   * @param {string} emailAddress - Gmail email address
   */
  async storeTokens(userId, tokens, permissions, emailAddress) {
    const expiresAt = new Date(Date.now() + (tokens.expires_in * 1000)).toISOString();
    const now = new Date().toISOString();

    await this.db.execute({
      sql: `
        INSERT INTO email_integrations (
          user_id, provider, email_address, access_token, refresh_token,
          token_expires_at, permissions, sync_enabled, created_at, updated_at
        ) VALUES (?, 'gmail', ?, ?, ?, ?, ?, TRUE, ?, ?)
        ON CONFLICT (user_id, provider) DO UPDATE SET
          email_address = EXCLUDED.email_address,
          access_token = EXCLUDED.access_token,
          refresh_token = COALESCE(EXCLUDED.refresh_token, refresh_token),
          token_expires_at = EXCLUDED.token_expires_at,
          permissions = EXCLUDED.permissions,
          updated_at = EXCLUDED.updated_at
      `,
      args: [
        userId,
        emailAddress,
        tokens.access_token,
        tokens.refresh_token || null,
        expiresAt,
        JSON.stringify(permissions),
        now,
        now
      ]
    });
  }

  /**
   * Get stored tokens for user
   *
   * @param {string} userId - User ID
   * @returns {Object|null} Token data or null if not found
   */
  async getStoredTokens(userId) {
    const result = await this.db.execute({
      sql: `SELECT * FROM email_integrations WHERE user_id = ? AND provider = 'gmail'`,
      args: [userId]
    });

    if (result.rows.length === 0) {
      return null;
    }

    return result.rows[0];
  }

  /**
   * Get valid access token (refreshes if expired)
   *
   * @param {string} userId - User ID
   * @returns {string} Valid access token
   */
  async getValidAccessToken(userId) {
    const integration = await this.getStoredTokens(userId);

    if (!integration) {
      throw new Error('Gmail not connected. Please connect your Gmail account.');
    }

    // Check if token is expired
    const expiresAt = new Date(integration.token_expires_at);
    const now = new Date();
    const bufferTime = 5 * 60 * 1000; // 5 minutes buffer

    if (now >= (expiresAt.getTime() - bufferTime)) {
      // Token expired or about to expire, refresh it
      if (!integration.refresh_token) {
        throw new Error('Gmail connection expired. Please reconnect your account.');
      }

      const newTokens = await this.refreshAccessToken(integration.refresh_token);
      await this.storeTokens(
        userId,
        newTokens,
        JSON.parse(integration.permissions),
        integration.email_address
      );

      return newTokens.access_token;
    }

    return integration.access_token;
  }

  /**
   * Get user's Gmail profile info
   *
   * @param {string} accessToken - Valid access token
   * @returns {Object} Profile info with emailAddress
   */
  async getUserProfile(accessToken) {
    const response = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/profile', {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get profile: ${error.error?.message || 'Unknown error'}`);
    }

    return await response.json();
  }

  /**
   * List email messages
   *
   * @param {string} userId - User ID
   * @param {Object} options - Query options
   * @returns {Array} Array of formatted email messages
   */
  async getMessages(userId, options = {}) {
    const {
      query = '',
      maxResults = 50,
      labelIds = [],
      includeSpamTrash = false
    } = options;

    const accessToken = await this.getValidAccessToken(userId);

    // Build query parameters
    const params = new URLSearchParams({
      maxResults: maxResults.toString(),
      includeSpamTrash: includeSpamTrash.toString()
    });

    if (query) params.append('q', query);
    if (labelIds.length > 0) {
      labelIds.forEach(id => params.append('labelIds', id));
    }

    // Get message list
    const listResponse = await fetch(
      `https://gmail.googleapis.com/gmail/v1/users/me/messages?${params.toString()}`,
      { headers: { 'Authorization': `Bearer ${accessToken}` } }
    );

    if (!listResponse.ok) {
      const error = await listResponse.json();
      throw new Error(`Failed to list messages: ${error.error?.message || 'Unknown error'}`);
    }

    const listData = await listResponse.json();

    if (!listData.messages || listData.messages.length === 0) {
      return [];
    }

    // Fetch full message details in batches
    const messages = [];
    const batchSize = 10;

    for (let i = 0; i < listData.messages.length; i += batchSize) {
      const batch = listData.messages.slice(i, i + batchSize);
      const batchPromises = batch.map(msg => this.getMessage(userId, msg.id, accessToken));
      const batchResults = await Promise.all(batchPromises);
      messages.push(...batchResults);
    }

    // Cache messages in database
    await this.cacheMessages(userId, messages);

    return messages;
  }

  /**
   * Get single email message
   *
   * @param {string} userId - User ID
   * @param {string} messageId - Gmail message ID
   * @param {string} accessToken - Optional access token (reuses if provided)
   * @returns {Object} Formatted email message
   */
  async getMessage(userId, messageId, accessToken = null) {
    if (!accessToken) {
      accessToken = await this.getValidAccessToken(userId);
    }

    const response = await fetch(
      `https://gmail.googleapis.com/gmail/v1/users/me/messages/${messageId}?format=full`,
      { headers: { 'Authorization': `Bearer ${accessToken}` } }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get message: ${error.error?.message || 'Unknown error'}`);
    }

    const message = await response.json();
    return this.formatMessage(message);
  }

  /**
   * Send email
   *
   * @param {string} userId - User ID
   * @param {Object} emailData - Email data (to, subject, body, etc.)
   * @returns {Object} Sent message info
   */
  async sendEmail(userId, emailData) {
    const accessToken = await this.getValidAccessToken(userId);
    const integration = await this.getStoredTokens(userId);

    // Check if user has send permission
    const permissions = JSON.parse(integration.permissions);
    if (!permissions.includes('send')) {
      throw new Error('Send permission not granted. Please reconnect Gmail with compose permissions.');
    }

    // Create RFC 2822 formatted email
    const rawEmail = this.createRFC2822Message(emailData);
    const encodedEmail = btoa(rawEmail).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

    const response = await fetch(
      'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ raw: encodedEmail })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to send email: ${error.error?.message || 'Unknown error'}`);
    }

    return await response.json();
  }

  /**
   * Format Gmail message to standard structure
   *
   * @param {Object} message - Gmail API message object
   * @returns {Object} Formatted message
   */
  formatMessage(message) {
    const headers = this.parseHeaders(message.payload?.headers || []);
    const body = this.extractBody(message.payload);

    return {
      id: message.id,
      threadId: message.threadId,
      subject: headers.subject || '(No Subject)',
      from: headers.from || '',
      to: headers.to || '',
      cc: headers.cc || '',
      bcc: headers.bcc || '',
      date: new Date(parseInt(message.internalDate)),
      bodyText: body.text,
      bodyHtml: body.html,
      snippet: message.snippet || '',
      labelIds: message.labelIds || [],
      isRead: !(message.labelIds || []).includes('UNREAD'),
      isImportant: (message.labelIds || []).includes('IMPORTANT'),
      hasAttachments: this.hasAttachments(message.payload),
      attachmentCount: this.countAttachments(message.payload),
      sizeEstimate: message.sizeEstimate || 0
    };
  }

  /**
   * Parse email headers into object
   */
  parseHeaders(headers) {
    const result = {};
    headers.forEach(header => {
      const name = header.name.toLowerCase();
      result[name] = header.value;
    });
    return result;
  }

  /**
   * Extract email body from payload
   */
  extractBody(payload) {
    let textBody = '';
    let htmlBody = '';

    const extractFromPart = (part) => {
      if (part.mimeType === 'text/plain' && part.body?.data) {
        textBody += this.decodeBase64(part.body.data);
      } else if (part.mimeType === 'text/html' && part.body?.data) {
        htmlBody += this.decodeBase64(part.body.data);
      } else if (part.parts) {
        part.parts.forEach(extractFromPart);
      }
    };

    if (payload.parts) {
      payload.parts.forEach(extractFromPart);
    } else if (payload.body?.data) {
      const decoded = this.decodeBase64(payload.body.data);
      if (payload.mimeType === 'text/plain') {
        textBody = decoded;
      } else if (payload.mimeType === 'text/html') {
        htmlBody = decoded;
      }
    }

    return { text: textBody, html: htmlBody };
  }

  /**
   * Decode base64url encoded string
   */
  decodeBase64(str) {
    try {
      // Convert base64url to base64
      const base64 = str.replace(/-/g, '+').replace(/_/g, '/');
      return atob(base64);
    } catch (error) {
      console.error('Failed to decode base64:', error);
      return '';
    }
  }

  /**
   * Check if message has attachments
   */
  hasAttachments(payload) {
    if (!payload) return false;

    const checkPart = (part) => {
      if (part.filename && part.filename.length > 0) return true;
      if (part.parts) return part.parts.some(checkPart);
      return false;
    };

    return checkPart(payload);
  }

  /**
   * Count attachments in message
   */
  countAttachments(payload) {
    if (!payload) return 0;

    let count = 0;
    const countPart = (part) => {
      if (part.filename && part.filename.length > 0) count++;
      if (part.parts) part.parts.forEach(countPart);
    };

    countPart(payload);
    return count;
  }

  /**
   * Create RFC 2822 formatted email message
   */
  createRFC2822Message(emailData) {
    const { to, cc, bcc, subject, body, isHtml = false } = emailData;

    let message = '';
    message += `To: ${to}\r\n`;
    if (cc) message += `Cc: ${cc}\r\n`;
    if (bcc) message += `Bcc: ${bcc}\r\n`;
    message += `Subject: ${subject}\r\n`;
    message += `Content-Type: ${isHtml ? 'text/html' : 'text/plain'}; charset=utf-8\r\n`;
    message += '\r\n';
    message += body;

    return message;
  }

  /**
   * Cache messages in database
   */
  async cacheMessages(userId, messages) {
    const now = new Date().toISOString();

    for (const msg of messages) {
      try {
        await this.db.execute({
          sql: `
            INSERT INTO email_cache (
              user_id, provider, provider_message_id, thread_id,
              subject, sender, recipients, cc, bcc,
              body_preview, body_text, body_html,
              labels, is_read, is_important,
              has_attachments, attachment_count, received_at, synced_at
            ) VALUES (?, 'gmail', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, provider, provider_message_id) DO UPDATE SET
              is_read = EXCLUDED.is_read,
              labels = EXCLUDED.labels,
              synced_at = EXCLUDED.synced_at
          `,
          args: [
            userId, msg.id, msg.threadId,
            msg.subject, msg.from, msg.to, msg.cc || null, msg.bcc || null,
            msg.snippet, msg.bodyText, msg.bodyHtml,
            JSON.stringify(msg.labelIds), msg.isRead, msg.isImportant,
            msg.hasAttachments, msg.attachmentCount, msg.date.toISOString(), now
          ]
        });
      } catch (error) {
        console.error(`Failed to cache message ${msg.id}:`, error);
      }
    }
  }
}
