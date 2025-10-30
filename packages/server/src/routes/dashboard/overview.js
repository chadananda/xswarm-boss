/**
 * Dashboard Overview Endpoint
 *
 * GET /api/dashboard/overview
 *
 * Returns dashboard summary stats and current plan info.
 * Requires authentication.
 */

import { getDashboardOverview } from '../../lib/dashboard-utils.js';

export async function handleDashboardOverview(request, env) {
  try {
    // User is attached to request by auth middleware
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const overview = await getDashboardOverview(user.id, env);

    return new Response(JSON.stringify(overview), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting dashboard overview:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
