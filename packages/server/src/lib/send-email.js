/**
 * SendGrid Email Sending Helper
 *
 * Wraps SendGrid API for sending transactional emails
 */

/**
 * Send email via SendGrid API
 *
 * @param {Object} options - Email options
 * @param {string} options.to - Recipient email
 * @param {string} options.from - Sender email
 * @param {string} options.subject - Email subject
 * @param {string} options.text - Plain text body
 * @param {string} options.html - HTML body (optional)
 * @param {Object} env - Environment variables
 * @returns {Promise<Object>} { success: boolean, messageId: string }
 */
export async function sendEmail({ to, from, subject, text, html }, env) {
  const SENDGRID_API_KEY = env.SENDGRID_API_KEY;

  if (!SENDGRID_API_KEY) {
    throw new Error('SENDGRID_API_KEY not configured');
  }

  const emailData = {
    personalizations: [
      {
        to: [{ email: to }],
        subject: subject,
      },
    ],
    from: { email: from },
    content: [{ type: 'text/plain', value: text }],
  };

  // Add HTML version if provided
  if (html) {
    emailData.content.push({ type: 'text/html', value: html });
  }

  const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(emailData),
  });

  if (!response.ok) {
    const error = await response.text();
    console.error('SendGrid API error:', error);
    throw new Error(`SendGrid API error: ${response.status}`);
  }

  return {
    success: true,
    messageId: response.headers.get('x-message-id'),
  };
}
