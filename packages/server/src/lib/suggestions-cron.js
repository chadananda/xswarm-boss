/**
 * Suggestions Cron Jobs
 *
 * Scheduled tasks for suggestion management:
 * - Weekly digest emails
 * - Auto-prioritization
 * - Stale suggestion cleanup
 */

import { sendWeeklyDigest, generateWeeklyDigest } from './suggestions-admin.js';

/**
 * Send weekly suggestion digest to admin
 *
 * This should be triggered weekly (e.g., every Monday at 9am)
 * via Cloudflare Workers cron trigger
 *
 * @param {Object} env - Environment bindings
 * @returns {Promise<Response>}
 */
export async function handleWeeklyDigest(env) {
  try {
    console.log('[Suggestions Cron] Starting weekly digest generation...');

    const adminEmail = env.ADMIN_EMAIL;
    if (!adminEmail) {
      console.warn('[Suggestions Cron] No ADMIN_EMAIL configured, skipping digest');
      return new Response(JSON.stringify({
        success: false,
        message: 'No admin email configured'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const digest = generateWeeklyDigest();

    if (digest.stats.new_count === 0) {
      console.log('[Suggestions Cron] No new suggestions this week, skipping digest');
      return new Response(JSON.stringify({
        success: true,
        message: 'No new suggestions this week'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const success = await sendWeeklyDigest(adminEmail);

    if (success) {
      console.log(`[Suggestions Cron] Weekly digest sent successfully to ${adminEmail}`);
      return new Response(JSON.stringify({
        success: true,
        message: 'Weekly digest sent',
        stats: digest.stats
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } else {
      console.error('[Suggestions Cron] Failed to send weekly digest');
      return new Response(JSON.stringify({
        success: false,
        message: 'Failed to send digest'
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  } catch (error) {
    console.error('[Suggestions Cron] Error in weekly digest:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Auto-prioritize suggestions based on votes and age
 *
 * This should be triggered daily to automatically adjust priority
 * of suggestions based on community feedback
 *
 * @param {Object} env - Environment bindings
 * @returns {Promise<Response>}
 */
export async function handleAutoPrioritize(env) {
  try {
    console.log('[Suggestions Cron] Starting auto-prioritization...');

    // Update priority for high-voted suggestions
    await env.DB.prepare(`
      UPDATE suggestions
      SET priority = 'high'
      WHERE status IN ('new', 'reviewed')
        AND upvotes >= 10
        AND priority != 'high'
    `).run();

    // Update priority for moderately-voted suggestions
    await env.DB.prepare(`
      UPDATE suggestions
      SET priority = 'medium'
      WHERE status IN ('new', 'reviewed')
        AND upvotes >= 5
        AND upvotes < 10
        AND priority = 'low'
    `).run();

    // Downgrade priority for old, low-voted suggestions
    await env.DB.prepare(`
      UPDATE suggestions
      SET priority = 'low'
      WHERE status = 'new'
        AND upvotes < 3
        AND created_at <= datetime('now', '-30 days')
        AND priority != 'low'
    `).run();

    console.log('[Suggestions Cron] Auto-prioritization complete');

    return new Response(JSON.stringify({
      success: true,
      message: 'Auto-prioritization complete'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('[Suggestions Cron] Error in auto-prioritize:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Manual trigger endpoint for testing cron jobs
 *
 * @param {Request} request
 * @param {Object} env
 * @param {string} action - Which cron job to trigger
 * @returns {Promise<Response>}
 */
export async function handleManualTrigger(request, env, action) {
  try {
    switch (action) {
      case 'weekly-digest':
        return await handleWeeklyDigest(env);

      case 'auto-prioritize':
        return await handleAutoPrioritize(env);

      default:
        return new Response(JSON.stringify({
          error: 'Invalid action',
          validActions: ['weekly-digest', 'auto-prioritize']
        }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
    }
  } catch (error) {
    console.error('[Suggestions Cron] Error in manual trigger:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Main scheduled event handler for Cloudflare Workers
 *
 * Add to wrangler.toml:
 * [triggers]
 * crons = [
 *   "0 9 * * 1",  # Weekly digest every Monday at 9am
 *   "0 2 * * *"   # Daily auto-prioritize at 2am
 * ]
 *
 * @param {ScheduledEvent} event
 * @param {Object} env
 * @param {Object} ctx
 */
export async function handleScheduledEvent(event, env, ctx) {
  const cron = event.cron;

  console.log(`[Suggestions Cron] Scheduled event triggered: ${cron}`);

  // Weekly digest (every Monday at 9am)
  if (cron === '0 9 * * 1') {
    ctx.waitUntil(handleWeeklyDigest(env));
  }

  // Daily auto-prioritize (every day at 2am)
  if (cron === '0 2 * * *') {
    ctx.waitUntil(handleAutoPrioritize(env));
  }
}
