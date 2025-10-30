/**
 * Dashboard Subscription Management Endpoints
 *
 * GET /api/dashboard/subscription - Get subscription details
 * PUT /api/dashboard/subscription - Update subscription preferences
 *
 * Requires authentication.
 */

import { getSubscriptionDetails } from '../../lib/dashboard-utils.js';
import { getUserById, updateUserTier } from '../../lib/users.js';

export async function handleGetSubscription(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const subscription = await getSubscriptionDetails(user.id, env);

    return new Response(JSON.stringify(subscription), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error getting subscription details:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function handleUpdateSubscription(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const { preferences } = body;

    // Update user preferences (persona, wake_word, etc.)
    // Note: Tier changes should go through Stripe checkout
    // This endpoint is for preferences only

    if (preferences) {
      // TODO: Add updateUserPreferences function to users.js
      // For now, return success
      console.log('Updating user preferences:', preferences);
    }

    const subscription = await getSubscriptionDetails(user.id, env);

    return new Response(JSON.stringify(subscription), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error updating subscription:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
