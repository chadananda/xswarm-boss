/**
 * Email Management Routes
 *
 * Gmail OAuth integration, AI summarization, and natural language queries
 * Cloudflare Workers compatible (Fetch API pattern)
 */

import { EmailSystem } from '../lib/email/email-system.js';
import { requireAuth } from '../lib/auth-middleware.js';
import { getUserById } from '../lib/users.js';
import { hasFeature } from '../lib/features.js';

/**
 * Start Gmail OAuth flow
 * POST /api/email/auth/gmail
 */
export async function handleGmailAuth(request, env) {
  try {
    const user = await requireAuth(request, env);

    // Check if user has email integration feature
    const tier = user.subscription_tier || 'free';
    if (!hasFeature(tier, 'email_daily')) {
      return new Response(JSON.stringify({
        error: 'Email integration not available on your plan',
        upgrade: {
          message: 'Email integration is available on all plans',
          tier: 'free'
        }
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const emailSystem = new EmailSystem(env);
    const result = await emailSystem.getGmailAuthUrl(user.id, tier);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Gmail auth error:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to start Gmail authorization'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Handle Gmail OAuth callback
 * GET /api/email/auth/callback?code=...&state=...
 */
export async function handleGmailCallback(request, env) {
  try {
    const url = new URL(request.url);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state');

    if (!code || !state) {
      return new Response(JSON.stringify({
        error: 'Missing code or state parameter'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Verify state contains valid user ID
    const stateData = JSON.parse(state);
    const user = await getUserById(stateData.userId, env);

    if (!user) {
      return new Response(JSON.stringify({
        error: 'Invalid user ID in state parameter'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const emailSystem = new EmailSystem(env);
    const result = await emailSystem.handleGmailCallback(code, state);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Gmail callback error:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to complete Gmail authorization'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Natural language email query
 * POST /api/email/query
 * Body: { query: "show me unread emails from today" }
 */
export async function handleEmailQuery(request, env) {
  try {
    const user = await requireAuth(request, env);

    // Check feature access
    const tier = user.subscription_tier || 'free';
    if (!hasFeature(tier, 'email_daily')) {
      return new Response(JSON.stringify({
        error: 'Email queries not available on your plan'
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    const { query, options = {} } = body;

    if (!query || query.trim().length === 0) {
      return new Response(JSON.stringify({
        error: 'Query is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const emailSystem = new EmailSystem(env);
    const result = await emailSystem.queryEmails(user.id, query, options);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Email query error:', error);

    if (error.message.includes('not connected')) {
      return new Response(JSON.stringify({
        error: error.message,
        action: 'connect_gmail'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to query emails'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Get email briefing
 * GET /api/email/briefing?timeframe=24h
 */
export async function handleEmailBriefing(request, env) {
  try {
    const user = await requireAuth(request, env);

    // Check feature access
    const tier = user.subscription_tier || 'free';
    if (!hasFeature(tier, 'email_daily')) {
      return new Response(JSON.stringify({
        error: 'Email briefings not available on your plan'
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const url = new URL(request.url);
    const timeframe = url.searchParams.get('timeframe') || '24h';

    const emailSystem = new EmailSystem(env);
    const briefing = await emailSystem.getEmailBriefing(user.id, timeframe);

    return new Response(JSON.stringify(briefing), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Email briefing error:', error);

    if (error.message.includes('not connected')) {
      return new Response(JSON.stringify({
        error: error.message,
        action: 'connect_gmail'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to generate email briefing'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Summarize specific email
 * POST /api/email/summarize/:emailId
 */
export async function handleEmailSummarize(request, env, emailId) {
  try {
    const user = await requireAuth(request, env);

    // Check feature access
    const tier = user.subscription_tier || 'free';
    if (!hasFeature(tier, 'email_daily')) {
      return new Response(JSON.stringify({
        error: 'Email summarization not available on your plan'
      }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (!emailId) {
      return new Response(JSON.stringify({
        error: 'Email ID is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const emailSystem = new EmailSystem(env);
    const summary = await emailSystem.summarizeEmail(user.id, emailId);

    return new Response(JSON.stringify(summary), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Email summarize error:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to summarize email'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Compose and send email (Personal tier+)
 * POST /api/email/compose
 * Body: { to, subject, body, cc?, bcc?, isHtml? }
 */
export async function handleEmailCompose(request, env) {
  try {
    const user = await requireAuth(request, env);

    // Check tier (Personal+ required)
    const tier = user.subscription_tier || 'free';
    if (!['personal', 'professional', 'enterprise', 'admin'].includes(tier)) {
      return new Response(JSON.stringify({
        error: 'Email composition requires Personal tier or higher',
        upgrade: {
          tier: 'personal',
          feature: 'email_compose',
          benefit: 'Send emails and create drafts',
          price: '$29/month'
        }
      }), {
        status: 402,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    const { to, subject, body: emailBody, cc, bcc, isHtml = false } = body;

    if (!to || !subject || !emailBody) {
      return new Response(JSON.stringify({
        error: 'Missing required fields: to, subject, body'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const emailData = { to, subject, body: emailBody, cc, bcc, isHtml };
    const emailSystem = new EmailSystem(env);
    const result = await emailSystem.composeEmail(user.id, emailData);

    return new Response(JSON.stringify(result), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Email compose error:', error);

    if (error.message.includes('Personal tier')) {
      return new Response(JSON.stringify({
        error: error.message,
        upgrade: {
          tier: 'personal',
          feature: 'email_compose',
          benefit: 'Send emails and create drafts'
        }
      }), {
        status: 402,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (error.message.includes('permission')) {
      return new Response(JSON.stringify({
        error: error.message,
        action: 'reconnect_gmail'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify({
      error: error.message || 'Failed to send email'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Get Gmail integration status
 * GET /api/email/status
 */
export async function handleEmailStatus(request, env) {
  try {
    const user = await requireAuth(request, env);

    const emailSystem = new EmailSystem(env);
    const status = await emailSystem.getIntegrationStatus(user.id);

    if (!status) {
      return new Response(JSON.stringify({
        connected: false,
        message: 'Gmail not connected'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response(JSON.stringify(status), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Email status error:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to get Gmail status'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Disconnect Gmail integration
 * DELETE /api/email/disconnect
 */
export async function handleEmailDisconnect(request, env) {
  try {
    const user = await requireAuth(request, env);

    const emailSystem = new EmailSystem(env);
    const result = await emailSystem.disconnectGmail(user.id);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Email disconnect error:', error);
    return new Response(JSON.stringify({
      error: error.message || 'Failed to disconnect Gmail'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
