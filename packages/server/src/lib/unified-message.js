/**
 * Unified Message Layer for Boss AI
 *
 * This module provides a unified interface for handling messages across all
 * communication channels (CLI, SMS, Email, Voice).
 *
 * Architecture:
 * 1. Message Normalization - Convert all channel-specific formats to unified format
 * 2. Message Processing - Channel-agnostic core logic
 * 3. Response Formatting - Convert responses back to channel-specific formats
 *
 * Benefits:
 * - Single source of truth for message processing
 * - Easy to add new channels (Discord, Slack, etc.)
 * - Consistent error handling and logging
 * - Simplified testing and maintenance
 */

import usersConfig from '../config/users.json' with { type: 'json' };
import {
  getClaudeResponse,
  processDevTask,
  parseMessageType,
  getStatusResponse,
  getHelpResponse
} from './claude.js';
import { getSupervisorClient } from './supervisor-client.js';

// =============================================================================
// UNIFIED MESSAGE SCHEMA
// =============================================================================

/**
 * Unified message format used internally
 *
 * @typedef {Object} UnifiedMessage
 * @property {string} channel - Communication channel: 'cli', 'sms', 'email', 'voice'
 * @property {string} from - Sender identifier (phone, email, or username)
 * @property {string} to - Recipient identifier (optional, for routing)
 * @property {string} content - Message content/body
 * @property {Object} metadata - Channel-specific metadata
 * @property {string} timestamp - ISO timestamp
 */

/**
 * Unified response format
 *
 * @typedef {Object} UnifiedResponse
 * @property {boolean} success - Whether processing was successful
 * @property {string} message - Response message content
 * @property {Object} metadata - Additional response metadata
 * @property {string} channel - Original channel (for response formatting)
 */

// =============================================================================
// MESSAGE NORMALIZATION - Convert channel formats to unified format
// =============================================================================

/**
 * Normalize CLI/API message to unified format
 *
 * Expected input format:
 * {
 *   from: "user@example.com" | "+1234567890" | "username",
 *   content: "message text",
 *   channel: "cli" | "api" (optional)
 * }
 */
export function normalizeCLIMessage(body, metadata = {}) {
  return {
    channel: body.channel || 'cli',
    from: body.from,
    to: body.to || null,
    content: body.content || body.message || '',
    metadata: {
      ...metadata,
      userAgent: body.userAgent,
      clientVersion: body.clientVersion,
    },
    timestamp: new Date().toISOString(),
  };
}

/**
 * Normalize Twilio SMS webhook to unified format
 *
 * Twilio sends form data with fields:
 * - From: Sender phone number
 * - To: Recipient phone number (Boss number)
 * - Body: Message content
 * - MessageSid: Unique message identifier
 */
export function normalizeSMSMessage(formData, metadata = {}) {
  return {
    channel: 'sms',
    from: formData.get('From') || '',
    to: formData.get('To') || '',
    content: formData.get('Body') || '',
    metadata: {
      ...metadata,
      messageSid: formData.get('MessageSid'),
      fromCity: formData.get('FromCity'),
      fromState: formData.get('FromState'),
      fromCountry: formData.get('FromCountry'),
    },
    timestamp: new Date().toISOString(),
  };
}

/**
 * Normalize SendGrid email webhook to unified format
 *
 * SendGrid sends form data with fields:
 * - from: Sender email (may include name)
 * - to: Recipient email
 * - subject: Email subject
 * - text: Plain text body
 * - html: HTML body
 */
export function normalizeEmailMessage(formData, metadata = {}) {
  const from = formData.get('from') || '';
  const to = formData.get('to') || '';

  // Extract email from "Name <email@domain.com>" format
  const fromEmail = from.match(/<(.+?)>/) ? from.match(/<(.+?)>/)[1] : from;
  const toEmail = to.match(/<(.+?)>/) ? to.match(/<(.+?)>/)[1] : to;

  return {
    channel: 'email',
    from: fromEmail,
    to: toEmail,
    content: formData.get('text') || formData.get('html') || '',
    metadata: {
      ...metadata,
      subject: formData.get('subject') || '',
      html: formData.get('html'),
      attachments: formData.get('attachments'),
    },
    timestamp: new Date().toISOString(),
  };
}

/**
 * Normalize voice call data to unified format
 *
 * For future voice integration
 */
export function normalizeVoiceMessage(callData, metadata = {}) {
  return {
    channel: 'voice',
    from: callData.From || callData.from || '',
    to: callData.To || callData.to || '',
    content: callData.transcription || callData.content || '',
    metadata: {
      ...metadata,
      callSid: callData.CallSid,
      duration: callData.duration,
      recordingUrl: callData.recordingUrl,
    },
    timestamp: new Date().toISOString(),
  };
}

// =============================================================================
// USER RESOLUTION - Find user across different identifiers
// =============================================================================

/**
 * Find user by any identifier (phone, email, username)
 *
 * @param {string} identifier - Phone, email, or username
 * @returns {Object|null} User info if found, null otherwise
 */
export function findUserByIdentifier(identifier) {
  if (!identifier) return null;

  // Normalize phone numbers (remove spaces, dashes, etc.)
  const normalizedIdentifier = identifier.replace(/[^\d+@a-zA-Z._-]/g, '');

  // Search through all users
  for (const user of usersConfig.users) {
    // Check phone number
    if (user.phone && user.phone.replace(/[^\d+]/g, '') === normalizedIdentifier) {
      return formatUser(user);
    }

    // Check boss phone
    if (user.boss_phone && user.boss_phone.replace(/[^\d+]/g, '') === normalizedIdentifier) {
      return formatUser(user, true); // Boss context
    }

    // Check email
    if (user.email && user.email.toLowerCase() === normalizedIdentifier.toLowerCase()) {
      return formatUser(user);
    }

    // Check boss email
    if (user.boss_email && user.boss_email.toLowerCase() === normalizedIdentifier.toLowerCase()) {
      return formatUser(user, true); // Boss context
    }

    // Check username
    if (user.username && user.username.toLowerCase() === normalizedIdentifier.toLowerCase()) {
      return formatUser(user);
    }
  }

  return null;
}

/**
 * Format user object from config
 */
function formatUser(user, isBossContext = false) {
  return {
    name: user.name,
    username: user.username,
    phone: user.phone,
    bossPhone: user.boss_phone,
    email: user.email,
    bossEmail: user.boss_email,
    isBossContext, // Whether message came to/from boss address
  };
}

/**
 * Validate authorization for a unified message
 * Returns user if authorized, null otherwise
 */
export function validateMessageAuthorization(unifiedMessage) {
  const { from, to, channel } = unifiedMessage;

  // Find user by sender
  const fromUser = findUserByIdentifier(from);

  if (!fromUser) {
    console.warn(`[Unified] Unknown sender: ${from}`);
    return null;
  }

  // For CLI/API, any identified user is authorized
  if (channel === 'cli' || channel === 'api') {
    console.log(`[Unified] CLI/API user authorized: ${fromUser.name}`);
    return fromUser;
  }

  // For SMS and Email, validate sender-receiver relationship
  if (channel === 'sms' || channel === 'email') {
    const toUser = findUserByIdentifier(to);

    if (!toUser) {
      console.warn(`[Unified] Unknown recipient: ${to}`);
      return null;
    }

    // Ensure communication is between user and their boss
    if (fromUser.email !== toUser.email) {
      console.warn(`[Unified] Not between paired accounts: ${from} → ${to}`);
      return null;
    }

    console.log(`[Unified] SMS/Email user authorized: ${fromUser.name}`);
    return fromUser;
  }

  // Unknown channel
  console.warn(`[Unified] Unknown channel: ${channel}`);
  return null;
}

// =============================================================================
// MESSAGE PROCESSING - Channel-agnostic core logic
// =============================================================================

/**
 * Process a unified message and return a unified response
 *
 * This is the core message processing logic that works the same
 * regardless of which channel the message came from.
 *
 * @param {UnifiedMessage} message - Normalized message
 * @param {Object} env - Environment variables
 * @returns {Promise<UnifiedResponse>} Unified response
 */
export async function processUnifiedMessage(message, env) {
  const { channel, from, content, metadata } = message;

  console.log(`[Unified] Processing ${channel} message from ${from}`);

  // Validate authorization
  const user = validateMessageAuthorization(message);

  if (!user) {
    return {
      success: false,
      message: 'You are not authorized to use this service.',
      metadata: { reason: 'unauthorized' },
      channel,
    };
  }

  // Validate content
  if (!content || content.trim().length === 0) {
    return {
      success: false,
      message: 'Message content is required.',
      metadata: { reason: 'empty_content' },
      channel,
    };
  }

  try {
    // Process message with AI/routing logic
    const responseMessage = await processMessageWithAI(user, content, channel, metadata, env);

    return {
      success: true,
      message: responseMessage,
      metadata: {
        user: user.name,
        processedAt: new Date().toISOString(),
      },
      channel,
    };

  } catch (error) {
    console.error('[Unified] Processing error:', error);

    return {
      success: false,
      message: getErrorMessage(channel, error),
      metadata: {
        error: error.message,
        user: user.name,
      },
      channel,
    };
  }
}

/**
 * Process message with Supervisor or Claude AI
 *
 * This handles the actual AI routing and response generation.
 */
async function processMessageWithAI(user, content, channel, metadata, env) {
  try {
    // Try supervisor WebSocket first
    const supervisor = getSupervisorClient({
      authToken: env.SUPERVISOR_TOKEN || 'dev-token-12345',
    });

    if (supervisor.isReady()) {
      console.log(`[Unified] Sending to supervisor for ${user.name}`);

      try {
        const response = await supervisor.sendMessage({
          channel,
          from: user.email || user.phone,
          content,
          user: user.username,
          metadata,
        });

        console.log(`[Unified] Supervisor response:`, response);

        // If supervisor returns a response, use it
        if (response && response.message) {
          return response.message;
        }

        console.log(`[Unified] Supervisor acknowledged, falling back to local`);
      } catch (error) {
        console.error('[Unified] Supervisor error, falling back:', error);
      }
    } else {
      console.log('[Unified] Supervisor not ready, using local processing');
    }

    // Fallback to local processing
    const messageType = parseMessageType(content);

    // Handle quick commands locally
    if (messageType === 'status') {
      return getStatusResponse(user);
    }

    if (messageType === 'help') {
      return getHelpResponse(user, channel);
    }

    // For development tasks, use specialized processing
    if (messageType === 'task') {
      console.log(`[Unified] Processing task for ${user.name}`);
      return await processDevTask(user, content, env, channel);
    }

    // For general messages, use Claude AI
    console.log(`[Unified] Getting Claude response for ${user.name}`);
    return await getClaudeResponse(user, content, channel, env);

  } catch (error) {
    console.error('[Unified] AI processing error:', error);
    throw error;
  }
}

/**
 * Get channel-appropriate error message
 */
function getErrorMessage(channel, error) {
  const baseMessage = "I encountered an issue processing your message.";

  switch (channel) {
    case 'sms':
      return `${baseMessage} I'll retry shortly. - Boss`;

    case 'email':
      return `Hello,\n\n${baseMessage} I'll review your message and send you a detailed response shortly.\n\nBest regards,\nYour Boss Assistant 🤖`;

    case 'cli':
    case 'api':
    default:
      return `${baseMessage} Error: ${error.message}`;
  }
}

// =============================================================================
// RESPONSE FORMATTING - Convert unified response to channel format
// =============================================================================

/**
 * Format unified response for CLI/API
 * Returns JSON response
 */
export function formatCLIResponse(unifiedResponse) {
  return {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: {
      success: unifiedResponse.success,
      message: unifiedResponse.message,
      metadata: unifiedResponse.metadata,
      timestamp: new Date().toISOString(),
    },
  };
}

/**
 * Format unified response for SMS (TwiML)
 * Returns XML response for Twilio
 */
export function formatSMSResponse(unifiedResponse) {
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>${escapeXml(unifiedResponse.message)}</Message>
</Response>`;

  return {
    status: unifiedResponse.success ? 200 : 403,
    headers: {
      'Content-Type': 'application/xml',
    },
    body: twiml,
  };
}

/**
 * Format unified response for Email
 * This triggers an outbound email send
 */
export async function formatEmailResponse(unifiedResponse, originalMessage, env) {
  // For email, we need to send a reply
  const { from, to, metadata } = originalMessage;

  // Send email via SendGrid
  await sendEmailResponse(
    from, // Reply to sender
    to,   // From boss address
    metadata.subject,
    unifiedResponse.message,
    env
  );

  return {
    status: 200,
    headers: {
      'Content-Type': 'text/plain',
    },
    body: 'OK',
  };
}

/**
 * Send email response via SendGrid
 */
async function sendEmailResponse(to, from, subject, text, env) {
  const SENDGRID_API_KEY = env.SENDGRID_API_KEY;

  if (!SENDGRID_API_KEY) {
    console.error('[Unified] SendGrid API key not configured');
    return;
  }

  const emailData = {
    personalizations: [{
      to: [{ email: to }],
      subject: `Re: ${subject}`,
    }],
    from: { email: from },
    content: [
      { type: 'text/plain', value: text },
    ],
  };

  try {
    const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${SENDGRID_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(emailData),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error('[Unified] SendGrid error:', error);
    } else {
      console.log('[Unified] Email sent successfully');
    }
  } catch (error) {
    console.error('[Unified] Error sending email:', error);
  }
}

/**
 * Escape XML special characters for TwiML
 */
function escapeXml(unsafe) {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

// =============================================================================
// HIGH-LEVEL API - Simplified interface for route handlers
// =============================================================================

/**
 * Handle CLI/API message (simplified interface)
 *
 * @param {Object} body - Request body
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} HTTP Response
 */
export async function handleCLIMessage(body, env) {
  // Normalize message
  const unifiedMessage = normalizeCLIMessage(body);

  // Process message
  const unifiedResponse = await processUnifiedMessage(unifiedMessage, env);

  // Format response
  const formattedResponse = formatCLIResponse(unifiedResponse);

  return new Response(
    JSON.stringify(formattedResponse.body),
    {
      status: formattedResponse.status,
      headers: formattedResponse.headers,
    }
  );
}

/**
 * Handle SMS webhook (simplified interface)
 *
 * @param {FormData} formData - Twilio webhook form data
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} HTTP Response
 */
export async function handleSMSMessage(formData, env) {
  // Normalize message
  const unifiedMessage = normalizeSMSMessage(formData);

  // Process message
  const unifiedResponse = await processUnifiedMessage(unifiedMessage, env);

  // Format response
  const formattedResponse = formatSMSResponse(unifiedResponse);

  return new Response(
    formattedResponse.body,
    {
      status: formattedResponse.status,
      headers: formattedResponse.headers,
    }
  );
}

/**
 * Handle Email webhook (simplified interface)
 *
 * @param {FormData} formData - SendGrid webhook form data
 * @param {Object} env - Environment variables
 * @returns {Promise<Response>} HTTP Response
 */
export async function handleEmailMessage(formData, env) {
  // Normalize message
  const unifiedMessage = normalizeEmailMessage(formData);

  // Process message
  const unifiedResponse = await processUnifiedMessage(unifiedMessage, env);

  // Format and send email response
  const formattedResponse = await formatEmailResponse(unifiedResponse, unifiedMessage, env);

  return new Response(
    formattedResponse.body,
    {
      status: formattedResponse.status,
      headers: formattedResponse.headers,
    }
  );
}
