/**
 * Dashboard Usage Analytics Endpoint
 *
 * GET /api/dashboard/usage
 *
 * Returns detailed usage analytics with time series data.
 * Requires authentication.
 */

import { getUsageAnalytics } from '../../lib/dashboard-utils.js';

export async function handleDashboardUsage(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const analytics = await getUsageAnalytics(user.id, env);

    return new Response(JSON.stringify(analytics), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting usage analytics:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
