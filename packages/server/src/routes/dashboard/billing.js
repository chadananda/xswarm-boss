/**
 * Dashboard Billing History Endpoint
 *
 * GET /api/dashboard/billing
 *
 * Returns billing history and invoices.
 * Requires authentication.
 */

import { getBillingHistory } from '../../lib/dashboard-utils.js';

export async function handleDashboardBilling(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const billing = await getBillingHistory(user.id, env);

    return new Response(JSON.stringify(billing), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      });

  } catch (error) {
    console.error('Error getting billing history:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
