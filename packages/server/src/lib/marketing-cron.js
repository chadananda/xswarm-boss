/**
 * Marketing Email Cron Job
 *
 * Scheduled task that runs periodically to send pending marketing emails.
 * Should be configured in Cloudflare Workers Cron Triggers or run via external scheduler.
 */

import { processPendingEmails } from './email-scheduler.js';

/**
 * Cron handler for Cloudflare Workers
 *
 * Add to wrangler.toml:
 * [triggers]
 * crons = ["0 * * * *"]  # Run every hour
 *
 * @param {ScheduledEvent} event
 * @param {Object} env
 * @param {Object} ctx
 */
export async function handleScheduledEvent(event, env, ctx) {
  console.log('[Marketing Cron] Starting scheduled email processing...');

  try {
    const result = await processPendingEmails(env);

    console.log(`[Marketing Cron] Completed: ${result.sent} sent, ${result.failed} failed`);

    if (result.failed > 0) {
      console.error('[Marketing Cron] Errors:', result.errors);
    }

    return result;
  } catch (error) {
    console.error('[Marketing Cron] Fatal error:', error);
    throw error;
  }
}

/**
 * Manual trigger endpoint for testing
 *
 * POST /marketing/cron-trigger
 * Headers: { Authorization: Bearer <admin_token> }
 *
 * @param {Request} request
 * @param {Object} env
 * @returns {Response}
 */
export async function handleManualTrigger(request, env) {
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

    console.log('[Marketing Cron] Manual trigger started...');

    const result = await processPendingEmails(env);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[Marketing Cron] Manual trigger error:', error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
