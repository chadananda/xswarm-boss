/**
 * Twilio Voice Webhook Handler
 *
 * Handles incoming voice calls to xSwarm phone numbers.
 * Validates caller against whitelist before accepting call.
 */

import { verifyTwilioSignature } from '../lib/auth.js';
import { getUserByXswarmPhone } from '../lib/database.js';
import { rejectCall, answerCall } from '../lib/twilio.js';

/**
 * Handle voice webhook from Twilio
 *
 * @param {Request} request - Incoming webhook request
 * @param {Object} env - Environment variables (secrets)
 * @param {string} userId - User ID from URL path
 * @returns {Response} TwiML response
 */
export async function handleVoiceWebhook(request, env, userId) {
  try {
    // Parse form data from Twilio
    const formData = await request.formData();
    const params = Object.fromEntries(formData);

    const {
      From: caller,
      To: xswarmPhone,
      CallSid: callSid,
    } = params;

    console.log(`Voice webhook: ${caller} → ${xswarmPhone} (${callSid})`);

    // Verify Twilio signature
    const url = request.url;
    const signature = request.headers.get('X-Twilio-Signature');

    if (!verifyTwilioSignature(url, params, signature, env.TWILIO_AUTH_TOKEN)) {
      console.error('Invalid Twilio signature');
      return new Response('Forbidden', { status: 403 });
    }

    // Get user from database
    const user = await getUserByXswarmPhone(xswarmPhone, env);

    if (!user) {
      console.error(`No user found for xSwarm phone: ${xswarmPhone}`);
      return rejectCall('User not found');
    }

    // Whitelist validation - only accept calls from user's registered phone
    if (caller !== user.user_phone) {
      console.warn(`Unauthorized call attempt: ${caller} → ${xswarmPhone}`);
      console.warn(`Expected caller: ${user.user_phone}`);
      return rejectCall('Unauthorized');
    }

    // Authorized - answer the call
    console.log(`Accepting call from ${caller} to ${user.username}'s xSwarm`);

    return answerCall(user);

  } catch (error) {
    console.error('Error handling voice webhook:', error);
    return rejectCall('Internal error');
  }
}
