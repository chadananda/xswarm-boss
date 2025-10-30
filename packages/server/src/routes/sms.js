/**
 * Twilio SMS Webhook Handler
 *
 * Handles incoming SMS messages to Boss phone numbers.
 * Validates sender against authorized user phone number.
 * Responds intelligently using Claude AI or Rust supervisor.
 */

import usersConfig from '../config/users.json' with { type: 'json' };
import {
  getClaudeResponse,
  processDevTask,
  parseMessageType,
  getStatusResponse,
  getHelpResponse
} from '../lib/claude.js';
import { getSupervisorClient } from '../lib/supervisor-client.js';

/**
 * Get authorized user by Boss phone and validate sender
 *
 * @param {string} bossPhone - Boss phone number
 * @param {string} senderPhone - Sender's phone number
 * @returns {Object|null} User info if authorized, null otherwise
 */
function getAuthorizedUserForSms(bossPhone, senderPhone) {
  console.log(`Auth check: Boss phone: "${bossPhone}", Sender: "${senderPhone}"`);

  // Normalize phone numbers (remove spaces, dashes, etc.)
  const normalizedBossPhone = bossPhone.replace(/[^\d+]/g, '');
  const normalizedSenderPhone = senderPhone.replace(/[^\d+]/g, '');

  console.log(`Normalized: Boss: "${normalizedBossPhone}", Sender: "${normalizedSenderPhone}"`);

  // Find user by Boss phone
  for (const user of usersConfig.users) {
    const normalizedUserBossPhone = user.boss_phone.replace(/[^\d+]/g, '');
    const normalizedUserPhone = user.phone.replace(/[^\d+]/g, '');

    console.log(`Checking user ${user.name}: Boss phone "${normalizedUserBossPhone}", User phone "${normalizedUserPhone}"`);

    if (normalizedUserBossPhone === normalizedBossPhone) {
      console.log(`Found boss phone match for ${user.name}`);
      // Verify sender is the authorized user phone
      if (normalizedUserPhone === normalizedSenderPhone) {
        console.log(`✅ Authorization SUCCESS: ${user.name} verified`);
        return {
          name: user.name,
          username: user.username,
          phone: user.phone,
          bossPhone: user.boss_phone,
          email: user.email,
          bossEmail: user.boss_email,
        };
      } else {
        console.log(`❌ Authorization FAILED: sender "${normalizedSenderPhone}" != user phone "${normalizedUserPhone}"`);
      }
    }
  }

  console.log(`❌ No authorization found for ${normalizedSenderPhone} → ${normalizedBossPhone}`);
  return null;
}

/**
 * Handle SMS webhook from Twilio
 *
 * @param {Request} request - Incoming webhook request
 * @param {Object} env - Environment variables (secrets)
 * @param {string} userId - User ID from URL path (unused, kept for compatibility)
 * @returns {Response} TwiML response
 */
export async function handleSmsWebhook(request, env, userId) {
  try {
    // Parse form data from Twilio
    const formData = await request.formData();

    const sender = formData.get('From') || '';
    const bossPhone = formData.get('To') || '';
    const message = formData.get('Body') || '';
    const messageSid = formData.get('MessageSid') || '';

    // Input validation: Check required fields
    if (!sender || !bossPhone || !message) {
      console.warn('SMS webhook missing required fields:', { sender, bossPhone, message });

      // Return TwiML error for malformed requests
      const errorTwiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>Invalid request format.</Message>
</Response>`;

      return new Response(errorTwiml, {
        status: 400,
        headers: { 'Content-Type': 'application/xml' },
      });
    }

    console.log(`SMS from: ${sender} to Boss: ${bossPhone}`);
    console.log(`Message: "${message}" (${messageSid})`);

    // Security check: Validate sender is authorized for this Boss phone
    const user = getAuthorizedUserForSms(bossPhone, sender);

    if (!user) {
      console.warn(`Unauthorized SMS: ${sender} → ${bossPhone}`);

      // Return explicit rejection TwiML for unauthorized users
      const rejectionTwiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>You are not authorized to use this service.</Message>
</Response>`;

      return new Response(rejectionTwiml, {
        status: 403,
        headers: { 'Content-Type': 'application/xml' },
      });
    }

    // Authorized - process the message
    console.log(`Processing SMS from ${user.name} to Boss`);

    // TODO: Integrate with AI command processing
    // For now, send a simple acknowledgment
    const response = await processCommand(user, message, env);

    // Send TwiML response
    const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>${response}</Message>
</Response>`;

    return new Response(twiml, {
      status: 200,
      headers: { 'Content-Type': 'application/xml' },
    });

  } catch (error) {
    console.error('Error handling SMS webhook:', error);
    return new Response('', { status: 200 });
  }
}

/**
 * Process SMS command via Supervisor or Claude AI
 *
 * @param {Object} user - User record from database
 * @param {string} message - SMS message text
 * @param {Object} env - Environment variables
 * @returns {string} Response message
 */
async function processCommand(user, message, env) {
  try {
    // Try to send to supervisor WebSocket first
    const supervisor = getSupervisorClient({
      authToken: env.SUPERVISOR_TOKEN || 'dev-token-12345',
    });

    if (supervisor.isReady()) {
      console.log(`[SMS] Sending to supervisor for ${user.name}`);
      try {
        const response = await supervisor.sendSmsEvent({
          from: user.phone,
          to: user.bossPhone,
          message: message,
          user: user.username,
        });

        console.log(`[SMS] Supervisor response:`, response);

        // If supervisor returns a response message, use it
        if (response.type === 'send_sms_response') {
          return response.message;
        }

        // If just acknowledged, fall back to local processing
        console.log(`[SMS] Supervisor acknowledged, falling back to local processing`);
      } catch (error) {
        console.error('[SMS] Supervisor error, falling back to local processing:', error);
      }
    } else {
      console.log('[SMS] Supervisor not ready, using local processing');
    }

    // Fallback to local processing
    // Parse the message type for routing
    const messageType = parseMessageType(message);

    // Handle quick commands locally for speed
    if (messageType === 'status') {
      return getStatusResponse(user);
    }

    if (messageType === 'help') {
      return getHelpResponse(user, 'sms');
    }

    // For development tasks, use specialized processing
    if (messageType === 'task') {
      console.log(`Processing development task for ${user.name}: ${message}`);
      return await processDevTask(user, message, env, 'sms');
    }

    // For questions and general messages, use Claude AI
    console.log(`Getting Claude AI response for ${user.name}: ${message}`);
    return await getClaudeResponse(user, message, 'sms', env);

  } catch (error) {
    console.error('Error processing SMS command:', error);
    return `I encountered an issue processing your message. I'll retry shortly. - Boss`;
  }
}
