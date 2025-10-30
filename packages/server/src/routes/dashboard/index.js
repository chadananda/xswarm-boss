/**
 * Dashboard Routes Index
 *
 * Central router for all dashboard endpoints.
 * All routes require authentication via JWT middleware.
 */

import { handleDashboardOverview } from './overview.js';
import { handleDashboardUsage } from './usage.js';
import { handleDashboardBilling } from './billing.js';
import { handleGetSubscription, handleUpdateSubscription } from './subscription.js';
import { handleGetProfile, handleUpdateProfile } from './profile.js';
import { handleUpgrade, handleDowngrade, handleCancel } from './upgrade.js';

/**
 * Main dashboard router
 *
 * Handles routing for all dashboard-related endpoints.
 * Assumes authentication middleware has already attached user to request.
 */
export async function handleDashboardRoutes(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;

  // GET /api/dashboard/overview
  if (path === '/api/dashboard/overview' && method === 'GET') {
    return handleDashboardOverview(request, env);
  }

  // GET /api/dashboard/usage
  if (path === '/api/dashboard/usage' && method === 'GET') {
    return handleDashboardUsage(request, env);
  }

  // GET /api/dashboard/billing
  if (path === '/api/dashboard/billing' && method === 'GET') {
    return handleDashboardBilling(request, env);
  }

  // GET /api/dashboard/subscription
  if (path === '/api/dashboard/subscription' && method === 'GET') {
    return handleGetSubscription(request, env);
  }

  // PUT /api/dashboard/subscription
  if (path === '/api/dashboard/subscription' && method === 'PUT') {
    return handleUpdateSubscription(request, env);
  }

  // GET /api/dashboard/profile
  if (path === '/api/dashboard/profile' && method === 'GET') {
    return handleGetProfile(request, env);
  }

  // PUT /api/dashboard/profile
  if (path === '/api/dashboard/profile' && method === 'PUT') {
    return handleUpdateProfile(request, env);
  }

  // POST /api/dashboard/upgrade
  if (path === '/api/dashboard/upgrade' && method === 'POST') {
    return handleUpgrade(request, env);
  }

  // POST /api/dashboard/downgrade
  if (path === '/api/dashboard/downgrade' && method === 'POST') {
    return handleDowngrade(request, env);
  }

  // POST /api/dashboard/cancel
  if (path === '/api/dashboard/cancel' && method === 'POST') {
    return handleCancel(request, env);
  }

  // 404 - Route not found
  return new Response(JSON.stringify({ error: 'Dashboard route not found' }), {
    status: 404,
    headers: { 'Content-Type': 'application/json' },
  });
}
