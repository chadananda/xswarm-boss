/**
 * Unsubscribe API - Handle Email Unsubscription
 * Cloudflare Pages Function
 */

import { createClient } from '@libsql/client/web';

export async function onRequestGet(context) {
  const { request, env } = context;

  const url = new URL(request.url);
  const email = url.searchParams.get('email');
  const token = url.searchParams.get('token');

  // Basic HTML response
  const htmlResponse = (message, success = false) => {
    return new Response(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Unsubscribe - Omarchy Defender</title>
        <style>
          body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff41;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
          }
          .container {
            text-align: center;
            padding: 2rem;
            border: 2px solid ${success ? '#00ff41' : '#ff4141'};
            max-width: 400px;
          }
          h1 { font-size: 1.5rem; }
          p { color: #888; }
          a { color: #00ff41; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>${success ? 'UNSUBSCRIBED' : 'ERROR'}</h1>
          <p>${message}</p>
          <p><a href="/">Return to Omarchy Defender</a></p>
        </div>
      </body>
      </html>
    `, {
      headers: { 'Content-Type': 'text/html' }
    });
  };

  if (!email) {
    return htmlResponse('Missing email parameter');
  }

  // Verify token (simple hash-based verification)
  const expectedToken = await generateUnsubscribeToken(email, env.STRIPE_WEBHOOK_SECRET);
  if (token !== expectedToken) {
    return htmlResponse('Invalid unsubscribe link');
  }

  try {
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN
    });

    // Update subscription status
    await db.execute({
      sql: `UPDATE donor_emails SET subscribed = false WHERE email = ?`,
      args: [email]
    });

    return htmlResponse(
      `You have been unsubscribed from Omarchy Defender updates. You will no longer receive emails at ${email}.`,
      true
    );

  } catch (error) {
    console.error('Unsubscribe error:', error);
    return htmlResponse('Failed to process unsubscribe request');
  }
}

async function generateUnsubscribeToken(email, secret) {
  const encoder = new TextEncoder();
  const data = encoder.encode(email + secret);

  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

  return hashHex.substring(0, 32);
}

// Export helper for generating unsubscribe URLs
export function getUnsubscribeUrl(email, secret, baseUrl) {
  const token = generateUnsubscribeToken(email, secret);
  return `${baseUrl}/api/unsubscribe?email=${encodeURIComponent(email)}&token=${token}`;
}
