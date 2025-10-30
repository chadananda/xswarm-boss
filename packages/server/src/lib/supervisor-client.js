/**
 * Supervisor WebSocket Client
 *
 * Connects Node.js Cloudflare Workers webhook server to the Rust supervisor WebSocket.
 * Enables SMS/Email webhooks to communicate with the AI processing layer.
 *
 * Architecture:
 * - WebSocket connection to ws://127.0.0.1:9999 (Rust supervisor)
 * - Authenticates with SUPERVISOR_TOKEN
 * - Sends SMS/Email events to supervisor
 * - Receives responses to send back via Twilio/SendGrid
 */

import WebSocket from 'ws';

/**
 * Supervisor client for WebSocket communication
 */
class SupervisorClient {
  constructor(config = {}) {
    this.url = config.url || 'ws://127.0.0.1:9999';
    this.authToken = config.authToken || 'dev-token-12345';
    this.ws = null;
    this.authenticated = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000; // Start with 1 second
    this.messageHandlers = new Map();
    this.nextMessageId = 1;
  }

  /**
   * Connect to the supervisor WebSocket
   * @returns {Promise<void>}
   */
  async connect() {
    return new Promise((resolve, reject) => {
      try {
        console.log(`[Supervisor] Connecting to ${this.url}...`);

        this.ws = new WebSocket(this.url);

        this.ws.on('open', () => {
          console.log('[Supervisor] WebSocket connection established');
          this.reconnectAttempts = 0;
          this.reconnectDelay = 1000;

          // Authenticate immediately
          this.authenticate()
            .then(() => {
              console.log('[Supervisor] Authentication successful');
              resolve();
            })
            .catch((error) => {
              console.error('[Supervisor] Authentication failed:', error);
              reject(error);
            });
        });

        this.ws.on('message', (data) => {
          this.handleMessage(data.toString());
        });

        this.ws.on('error', (error) => {
          console.error('[Supervisor] WebSocket error:', error);
          reject(error);
        });

        this.ws.on('close', () => {
          console.warn('[Supervisor] WebSocket connection closed');
          this.authenticated = false;
          this.attemptReconnect();
        });

      } catch (error) {
        console.error('[Supervisor] Failed to create WebSocket:', error);
        reject(error);
      }
    });
  }

  /**
   * Attempt to reconnect to supervisor
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[Supervisor] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`[Supervisor] Attempting reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms...`);

    setTimeout(() => {
      this.connect().catch((error) => {
        console.error('[Supervisor] Reconnection failed:', error);
      });
    }, delay);
  }

  /**
   * Authenticate with the supervisor
   * @returns {Promise<void>}
   */
  async authenticate() {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      const messageId = this.nextMessageId++;

      // Wait for AuthResult response
      this.messageHandlers.set('auth', (event) => {
        if (event.type === 'auth_result') {
          if (event.success) {
            this.authenticated = true;
            this.messageHandlers.delete('auth');
            resolve();
          } else {
            this.messageHandlers.delete('auth');
            reject(new Error(event.message || 'Authentication failed'));
          }
        }
      });

      // Send auth message
      const authMessage = {
        type: 'auth',
        token: this.authToken,
      };

      this.ws.send(JSON.stringify(authMessage));
    });
  }

  /**
   * Handle incoming WebSocket message
   * @param {string} data - Raw message data
   */
  handleMessage(data) {
    try {
      const event = JSON.parse(data);
      console.log('[Supervisor] Received event:', event.type);

      // Check for specific message handlers first
      for (const [id, handler] of this.messageHandlers.entries()) {
        if (handler(event) === true) {
          // Handler consumed the message
          return;
        }
      }

      // Handle specific event types
      switch (event.type) {
        case 'auth_result':
          // Handled by authenticate() promise
          break;

        case 'message_acknowledged':
          console.log(`[Supervisor] Message acknowledged for user ${event.user}`);
          break;

        case 'send_sms_response':
          console.log(`[Supervisor] SMS response for ${event.user}: ${event.message}`);
          // TODO: Send SMS via Twilio
          break;

        case 'send_email_response':
          console.log(`[Supervisor] Email response for ${event.user}: ${event.subject}`);
          // TODO: Send email via SendGrid
          break;

        case 'error':
          console.error('[Supervisor] Error from supervisor:', event.message);
          break;

        case 'pong':
          console.log('[Supervisor] Pong received');
          break;

        default:
          console.log('[Supervisor] Unhandled event type:', event.type);
      }
    } catch (error) {
      console.error('[Supervisor] Error parsing message:', error);
    }
  }

  /**
   * Send SMS event to supervisor
   * @param {Object} smsData - SMS data
   * @param {string} smsData.from - Sender phone number
   * @param {string} smsData.to - Boss phone number
   * @param {string} smsData.message - SMS message text
   * @param {string} smsData.user - User identifier
   * @returns {Promise<Object>} Supervisor response
   */
  async sendSmsEvent(smsData) {
    if (!this.authenticated) {
      throw new Error('Not authenticated with supervisor');
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    console.log(`[Supervisor] Sending SMS event for user ${smsData.user}`);

    const message = {
      type: 'sms_received',
      from: smsData.from,
      to: smsData.to,
      message: smsData.message,
      user: smsData.user,
    };

    return new Promise((resolve, reject) => {
      const messageId = `sms_${Date.now()}`;
      const timeout = setTimeout(() => {
        this.messageHandlers.delete(messageId);
        reject(new Error('SMS event timeout'));
      }, 10000);

      this.messageHandlers.set(messageId, (event) => {
        if (event.type === 'message_acknowledged' && event.message_type === 'sms') {
          clearTimeout(timeout);
          this.messageHandlers.delete(messageId);
          resolve(event);
          return true;
        }
        if (event.type === 'send_sms_response' && event.user === smsData.user) {
          clearTimeout(timeout);
          this.messageHandlers.delete(messageId);
          resolve(event);
          return true;
        }
        if (event.type === 'error') {
          clearTimeout(timeout);
          this.messageHandlers.delete(messageId);
          reject(new Error(event.message));
          return true;
        }
        return false;
      });

      this.ws.send(JSON.stringify(message));
    });
  }

  /**
   * Send Email event to supervisor
   * @param {Object} emailData - Email data
   * @param {string} emailData.from - Sender email
   * @param {string} emailData.to - Boss email
   * @param {string} emailData.subject - Email subject
   * @param {string} emailData.body - Email body
   * @param {string} emailData.user - User identifier
   * @returns {Promise<Object>} Supervisor response
   */
  async sendEmailEvent(emailData) {
    if (!this.authenticated) {
      throw new Error('Not authenticated with supervisor');
    }

    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    console.log(`[Supervisor] Sending Email event for user ${emailData.user}`);

    const message = {
      type: 'email_received',
      from: emailData.from,
      to: emailData.to,
      subject: emailData.subject,
      body: emailData.body,
      user: emailData.user,
    };

    return new Promise((resolve, reject) => {
      const messageId = `email_${Date.now()}`;
      const timeout = setTimeout(() => {
        this.messageHandlers.delete(messageId);
        reject(new Error('Email event timeout'));
      }, 10000);

      this.messageHandlers.set(messageId, (event) => {
        if (event.type === 'message_acknowledged' && event.message_type === 'email') {
          clearTimeout(timeout);
          this.messageHandlers.delete(messageId);
          resolve(event);
          return true;
        }
        if (event.type === 'send_email_response' && event.user === emailData.user) {
          clearTimeout(timeout);
          this.messageHandlers.delete(messageId);
          resolve(event);
          return true;
        }
        if (event.type === 'error') {
          clearTimeout(timeout);
          this.messageHandlers.delete(messageId);
          reject(new Error(event.message));
          return true;
        }
        return false;
      });

      this.ws.send(JSON.stringify(message));
    });
  }

  /**
   * Send ping to keep connection alive
   */
  ping() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }

  /**
   * Close the WebSocket connection
   */
  disconnect() {
    if (this.ws) {
      console.log('[Supervisor] Disconnecting...');
      this.ws.close();
      this.ws = null;
      this.authenticated = false;
    }
  }

  /**
   * Check if connected and authenticated
   * @returns {boolean}
   */
  isReady() {
    return this.authenticated && this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// Singleton instance for Cloudflare Workers
let supervisorClient = null;

/**
 * Get or create the supervisor client singleton
 * @param {Object} config - Configuration options
 * @returns {SupervisorClient}
 */
export function getSupervisorClient(config = {}) {
  if (!supervisorClient) {
    supervisorClient = new SupervisorClient(config);
  }
  return supervisorClient;
}

/**
 * Initialize supervisor connection (call on server startup)
 * @param {Object} config - Configuration options
 * @returns {Promise<SupervisorClient>}
 */
export async function initializeSupervisor(config = {}) {
  const client = getSupervisorClient(config);

  if (!client.isReady()) {
    await client.connect();
  }

  // Setup ping interval to keep connection alive
  setInterval(() => {
    if (client.isReady()) {
      client.ping();
    }
  }, 30000); // Ping every 30 seconds

  return client;
}

export default SupervisorClient;
