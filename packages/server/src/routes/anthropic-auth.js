/**
 * Anthropic OAuth Routes
 *
 * Handles OAuth callback from Anthropic and polling for TUI clients.
 * The TUI generates a session_id, opens the browser for auth, and polls
 * this endpoint to retrieve the authorization code once the user approves.
 *
 * Cloudflare Workers compatible (Fetch API pattern)
 */

import { createClient } from '@libsql/client';

/**
 * Handle Anthropic OAuth callback
 * GET /api/auth/anthropic/callback?code=...&state=...
 *
 * Called by Anthropic after user authorizes. Stores the code in DB
 * for the TUI to poll and retrieve.
 */
export async function handleAnthropicCallback(request, env) {
  try {
    const url = new URL(request.url);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state'); // session_id from TUI

    if (!code || !state) {
      return new Response(ERROR_HTML('Missing code or state parameter'), {
        status: 400,
        headers: { 'Content-Type': 'text/html' }
      });
    }

    // Store code in database with 5-minute TTL
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN
    });

    await db.execute({
      sql: `INSERT INTO oauth_pending (session_id, code, expires_at)
            VALUES (?, ?, datetime('now', '+5 minutes'))
            ON CONFLICT(session_id) DO UPDATE SET
              code = excluded.code,
              expires_at = datetime('now', '+5 minutes')`,
      args: [state, code]
    });

    // Show success page (user can close browser)
    return new Response(SUCCESS_HTML, {
      status: 200,
      headers: { 'Content-Type': 'text/html' }
    });

  } catch (error) {
    console.error('Anthropic callback error:', error);
    return new Response(ERROR_HTML('Failed to process authorization. Please try again.'), {
      status: 500,
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

/**
 * Poll for Anthropic OAuth code
 * GET /api/auth/anthropic/poll?session=...
 *
 * TUI polls this endpoint to retrieve the authorization code
 * after the user completes authorization in the browser.
 */
export async function handleAnthropicPoll(request, env) {
  try {
    const url = new URL(request.url);
    const session = url.searchParams.get('session');

    if (!session) {
      return Response.json({ error: 'Missing session parameter' }, { status: 400 });
    }

    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN
    });

    // Get code if exists and not expired
    const result = await db.execute({
      sql: `SELECT code FROM oauth_pending
            WHERE session_id = ? AND expires_at > datetime('now')`,
      args: [session]
    });

    if (result.rows.length > 0) {
      const code = result.rows[0].code;

      // Delete after retrieval (one-time use)
      await db.execute({
        sql: `DELETE FROM oauth_pending WHERE session_id = ?`,
        args: [session]
      });

      return Response.json({ code });
    }

    // No code yet - still pending
    return Response.json({ pending: true });

  } catch (error) {
    console.error('Anthropic poll error:', error);
    return Response.json({ error: 'Failed to check authorization status' }, { status: 500 });
  }
}

/**
 * Cleanup expired OAuth pending codes
 * Called periodically or via cron trigger
 */
export async function cleanupExpiredCodes(env) {
  try {
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN
    });

    const result = await db.execute({
      sql: `DELETE FROM oauth_pending WHERE expires_at < datetime('now')`
    });

    return result.rowsAffected || 0;
  } catch (error) {
    console.error('Cleanup error:', error);
    return 0;
  }
}

// Success HTML page shown after authorization
const SUCCESS_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Connected to Anthropic</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      color: #ffffff;
    }
    .container {
      text-align: center;
      padding: 48px 40px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      max-width: 420px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    .icon {
      font-size: 72px;
      margin-bottom: 24px;
      animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.05); }
    }
    h1 {
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 16px;
      background: linear-gradient(135deg, #00d4ff, #7c3aed);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    p {
      font-size: 16px;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
    }
    .brand {
      margin-top: 32px;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.4);
    }
    .brand strong {
      color: rgba(255, 255, 255, 0.6);
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">✅</div>
    <h1>Connected to Anthropic!</h1>
    <p>Authorization successful. You can close this window and return to xSwarm Assistant.</p>
    <p class="brand">Powered by <strong>xSwarm</strong></p>
  </div>
</body>
</html>`;

// Error HTML page
function ERROR_HTML(message) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Authorization Error</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #2d1a1a 0%, #3d1616 50%, #4a1010 100%);
      color: #ffffff;
    }
    .container {
      text-align: center;
      padding: 48px 40px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 20px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 100, 100, 0.2);
      max-width: 420px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    .icon { font-size: 72px; margin-bottom: 24px; }
    h1 {
      font-size: 28px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #ff6b6b;
    }
    p {
      font-size: 16px;
      color: rgba(255, 255, 255, 0.7);
      line-height: 1.6;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">❌</div>
    <h1>Authorization Error</h1>
    <p>${message}</p>
  </div>
</body>
</html>`;
}
