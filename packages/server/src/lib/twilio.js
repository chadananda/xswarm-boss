/**
 * Twilio TwiML Response Builders
 *
 * Helper functions to generate TwiML responses for voice and SMS.
 */

/**
 * Reject incoming call with TwiML
 *
 * @param {string} reason - Rejection reason (for logging)
 * @returns {Response} TwiML response that rejects the call
 */
export function rejectCall(reason = 'Unauthorized') {
  const twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Reject/></Response>';

  return new Response(twiml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}

/**
 * Answer incoming call with TwiML
 *
 * @param {Object} user - User record from database
 * @returns {Response} TwiML response that answers the call
 */
export function answerCall(user) {
  // Get persona name from user config (default to HAL 9000)
  const persona = user.persona || 'HAL 9000';

  // Generate greeting based on persona
  const greeting = getPersonaGreeting(persona, user.username);

  // TwiML to answer call, greet user, and record message
  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="man">${greeting}</Say>
  <Record maxLength="120" transcribe="true" playBeep="true"/>
  <Say voice="man">I did not receive your message. Please try again.</Say>
</Response>`;

  return new Response(twiml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}

/**
 * Reject SMS (empty response)
 *
 * @returns {Response} Empty TwiML response (ignores SMS)
 */
export function rejectSms() {
  const twiml = '<?xml version="1.0" encoding="UTF-8"?><Response/>';

  return new Response(twiml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}

/**
 * Send SMS reply
 *
 * @param {string} message - Reply message text
 * @returns {Response} TwiML response with SMS message
 */
export function sendSmsReply(message) {
  // Escape XML special characters
  const escapedMessage = escapeXml(message);

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>${escapedMessage}</Message>
</Response>`;

  return new Response(twiml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml',
    },
  });
}

/**
 * Get persona-specific greeting
 *
 * @param {string} persona - Persona name (hal-9000, jarvis, etc.)
 * @param {string} username - User's name
 * @returns {string} Greeting text
 */
function getPersonaGreeting(persona, username) {
  const greetings = {
    'hal-9000': `Good afternoon, ${username}. This is HAL. I'm ready to assist you.`,
    'jarvis': `Good to hear from you, ${username}. How may I be of service?`,
    'friday': `Hey ${username}, it's FRIDAY. What can I do for you?`,
    'cortana': `Hello ${username}, this is Cortana. I'm here to help.`,
    'samantha': `Hi ${username}, it's Samantha. What's on your mind?`,
  };

  return greetings[persona.toLowerCase()] || greetings['hal-9000'];
}

/**
 * Escape XML special characters
 *
 * @param {string} text - Text to escape
 * @returns {string} XML-safe text
 */
function escapeXml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}
