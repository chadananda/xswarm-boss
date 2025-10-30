/**
 * Marketing Email Routes
 *
 * API endpoints for email marketing campaign management:
 * - User enrollment/unsubscribe
 * - Campaign analytics
 * - Manual batch sends (admin)
 * - SendGrid webhook handlers
 */

import {
  enrollUserInCampaign,
  unsubscribeUser,
  processPendingEmails,
  markSubscriptionConverted,
  trackEmailEngagement,
  batchEnrollUsers,
} from '../../lib/email-scheduler.js';

import {
  getDashboardStats,
  getCampaignPerformance,
  getSequencePerformance,
  getConversionFunnel,
  getRevenueAttribution,
  getEngagementTimeline,
  getTopPerformingEmails,
  getUserEngagement,
  exportAnalyticsReport,
} from '../../lib/marketing-analytics.js';

/**
 * Enroll user in appropriate marketing campaign
 *
 * POST /marketing/enroll
 * Body: { user_id: string, current_tier: string }
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleEnroll(request, env) {
  try {
    const { user_id, current_tier } = await request.json();

    if (!user_id || !current_tier) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: user_id, current_tier' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const result = await enrollUserInCampaign(user_id, current_tier, env);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[Marketing] Enrollment error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Unsubscribe user from marketing emails
 *
 * GET /marketing/unsubscribe/:token
 *
 * @param {Request} request
 * @param {Object} env
 * @param {Object} params
 * @returns {Response}
 */
export async function handleUnsubscribe(request, env, params) {
  try {
    const token = params.token;

    if (!token) {
      return new Response('Invalid unsubscribe link', { status: 400 });
    }

    const result = await unsubscribeUser(token, env);

    // Return HTML page
    const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsubscribe - xSwarm</title>
  <style>
    body {
      font-family: 'Monaco', 'Courier New', monospace;
      background-color: #000000;
      color: #00ff00;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
    }
    .container {
      max-width: 600px;
      padding: 40px;
      border: 2px solid #00ff00;
      background-color: #0a0a0a;
      text-align: center;
    }
    h1 {
      color: #00ff00;
      font-size: 28px;
      margin-bottom: 20px;
      text-transform: uppercase;
      letter-spacing: 2px;
    }
    p {
      color: #00cc00;
      line-height: 1.6;
      margin-bottom: 15px;
    }
    .success {
      color: #00ff00;
    }
    .error {
      color: #ff0000;
    }
    a {
      color: #00ff00;
      text-decoration: none;
      border-bottom: 1px solid #00ff00;
    }
    a:hover {
      color: #ffffff;
      border-bottom-color: #ffffff;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>[ xSWARM AI ]</h1>
    ${
      result.success
        ? `
      <p class="success">✓ You have been unsubscribed from marketing emails.</p>
      <p>You will no longer receive tier upgrade emails from us.</p>
      <p>You'll still receive important account notifications and transactional emails.</p>
    `
        : `
      <p class="error">✗ ${result.message}</p>
      <p>If you continue to have issues, please contact support.</p>
    `
    }
    <p><a href="https://xswarm.ai">Return to xSwarm</a></p>
  </div>
</body>
</html>
    `.trim();

    return new Response(html, {
      status: result.success ? 200 : 400,
      headers: { 'Content-Type': 'text/html' },
    });
  } catch (error) {
    console.error('[Marketing] Unsubscribe error:', error);
    return new Response('Error processing unsubscribe request', { status: 500 });
  }
}

/**
 * Manual batch send (admin only)
 *
 * POST /marketing/send-batch
 * Headers: { Authorization: Bearer <admin_token> }
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleSendBatch(request, env) {
  try {
    // Verify admin authorization
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // TODO: Implement proper JWT verification
    // For now, check against a simple admin token
    const token = authHeader.substring(7);
    if (token !== env.ADMIN_TOKEN) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      );
    }

    console.log('[Marketing] Starting manual batch send...');
    const result = await processPendingEmails(env);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[Marketing] Batch send error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Batch enroll eligible users (admin only)
 *
 * POST /marketing/batch-enroll
 * Headers: { Authorization: Bearer <admin_token> }
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleBatchEnroll(request, env) {
  try {
    // Verify admin authorization
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const token = authHeader.substring(7);
    if (token !== env.ADMIN_TOKEN) {
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
      );
    }

    console.log('[Marketing] Starting batch enrollment...');
    const result = await batchEnrollUsers(env);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[Marketing] Batch enrollment error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Get marketing dashboard stats
 *
 * GET /marketing/stats
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleStats(request, env) {
  try {
    const url = new URL(request.url);
    const type = url.searchParams.get('type') || 'dashboard';
    const campaignId = url.searchParams.get('campaign_id');

    let data;

    switch (type) {
      case 'dashboard':
        data = await getDashboardStats(env);
        break;

      case 'campaign':
        data = await getCampaignPerformance(campaignId, env);
        break;

      case 'sequence':
        if (!campaignId) {
          return new Response(
            JSON.stringify({ error: 'campaign_id required for sequence stats' }),
            { status: 400, headers: { 'Content-Type': 'application/json' } }
          );
        }
        data = await getSequencePerformance(campaignId, env);
        break;

      case 'funnel':
        if (!campaignId) {
          return new Response(
            JSON.stringify({ error: 'campaign_id required for funnel stats' }),
            { status: 400, headers: { 'Content-Type': 'application/json' } }
          );
        }
        data = await getConversionFunnel(campaignId, env);
        break;

      case 'revenue':
        data = await getRevenueAttribution(campaignId, env);
        break;

      case 'timeline':
        const days = parseInt(url.searchParams.get('days')) || 30;
        data = await getEngagementTimeline(campaignId, days, env);
        break;

      case 'top':
        const limit = parseInt(url.searchParams.get('limit')) || 10;
        data = await getTopPerformingEmails(limit, env);
        break;

      case 'user':
        const userId = url.searchParams.get('user_id');
        if (!userId) {
          return new Response(
            JSON.stringify({ error: 'user_id required for user stats' }),
            { status: 400, headers: { 'Content-Type': 'application/json' } }
          );
        }
        data = await getUserEngagement(userId, env);
        break;

      case 'report':
        if (!campaignId) {
          return new Response(
            JSON.stringify({ error: 'campaign_id required for report' }),
            { status: 400, headers: { 'Content-Type': 'application/json' } }
          );
        }
        data = await exportAnalyticsReport(campaignId, env);
        break;

      default:
        return new Response(
          JSON.stringify({ error: 'Invalid stats type' }),
          { status: 400, headers: { 'Content-Type': 'application/json' } }
        );
    }

    return new Response(JSON.stringify(data), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[Marketing] Stats error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Handle SendGrid engagement webhook
 *
 * POST /marketing/webhook/sendgrid
 * Body: SendGrid event data
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleSendGridWebhook(request, env) {
  try {
    const events = await request.json();

    // SendGrid sends an array of events
    if (!Array.isArray(events)) {
      return new Response(
        JSON.stringify({ error: 'Invalid webhook data' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    console.log(`[Marketing Webhook] Processing ${events.length} SendGrid events`);

    for (const event of events) {
      const { event: eventType, sg_message_id } = event;

      if (!sg_message_id) {
        console.warn('[Marketing Webhook] Event missing sg_message_id:', event);
        continue;
      }

      // Track engagement
      await trackEmailEngagement(sg_message_id, eventType, env);
    }

    return new Response(JSON.stringify({ received: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[Marketing Webhook] Error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Mark user as converted (tier upgrade)
 *
 * POST /marketing/convert
 * Body: { user_id: string, new_tier: string }
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleConvert(request, env) {
  try {
    const { user_id, new_tier } = await request.json();

    if (!user_id || !new_tier) {
      return new Response(
        JSON.stringify({ error: 'Missing required fields: user_id, new_tier' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    await markSubscriptionConverted(user_id, new_tier, env);

    return new Response(
      JSON.stringify({ success: true, message: 'User marked as converted' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('[Marketing] Conversion tracking error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
