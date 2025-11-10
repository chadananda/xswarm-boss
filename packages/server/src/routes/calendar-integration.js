/**
 * Calendar Integration API Routes
 *
 * Comprehensive calendar integration with Google Calendar OAuth, iCal support,
 * natural language queries, and daily briefings.
 *
 * Features:
 * - Multi-provider calendar connections (Google, iCal)
 * - Natural language calendar queries
 * - Daily briefings with conflict detection
 * - Tier-based access control (Free: read-only, Personal+: read/write)
 */

import { CalendarSystem } from '../lib/calendar/mod.js';
import { verifyJWT } from '../lib/jwt.js';
import { hasFeature } from '../lib/features.js';

/**
 * Middleware to verify authentication
 */
async function requireAuth(request, env) {
  const authHeader = request.headers.get('Authorization');
  if (!authHeader?.startsWith('Bearer ')) {
    return { error: 'Missing or invalid authorization header', status: 401 };
  }

  const token = authHeader.substring(7);
  try {
    const decoded = await verifyJWT(token, env);
    return { user: decoded };
  } catch (error) {
    return { error: 'Invalid or expired token', status: 401 };
  }
}

/**
 * Middleware to check feature access
 */
function requireFeature(tier, feature) {
  if (!hasFeature(tier, feature)) {
    return {
      error: `This feature requires a higher subscription tier`,
      feature,
      currentTier: tier,
      requiredTier: 'personal',
      status: 402
    };
  }
  return null;
}

/**
 * Start Google Calendar OAuth flow
 * POST /api/calendar/auth/google
 */
export async function startGoogleAuth(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    const { scopes = 'readonly' } = body;

    const calendar = new CalendarSystem(env);
    const user = auth.user;
    const tier = user.subscription_tier || 'free';

    // Check if user can use write access
    if (scopes === 'readwrite') {
      const featureCheck = requireFeature(tier, 'calendar_write_access');
      if (featureCheck) {
        return new Response(JSON.stringify(featureCheck), {
          status: featureCheck.status,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    const authUrl = await calendar.google.getAuthUrl(user.id, scopes);

    return new Response(JSON.stringify({ authUrl }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Google auth error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Handle Google OAuth callback
 * GET /api/calendar/auth/callback?code=xxx&state=xxx
 */
export async function handleGoogleCallback(request, env) {
  try {
    const url = new URL(request.url);
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state'); // state = userId

    if (!code || !state) {
      return new Response(JSON.stringify({ error: 'Missing code or state parameter' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const result = await calendar.google.handleCallback(code, state);

    // Initial sync
    await calendar.google.syncEvents(state);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Callback error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Process natural language calendar query
 * POST /api/calendar/query
 */
export async function queryCalendar(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    const { query, options = {} } = body;

    if (!query || query.trim().length === 0) {
      return new Response(JSON.stringify({ error: 'Query is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check feature access
    const tier = auth.user.subscription_tier || 'free';
    const featureCheck = requireFeature(tier, 'calendar_integration');
    if (featureCheck) {
      return new Response(JSON.stringify(featureCheck), {
        status: featureCheck.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const result = await calendar.queryCalendar(auth.user.id, query, options);

    return new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Query error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Get daily briefing
 * GET /api/calendar/briefing?date=2024-01-01
 */
export async function getDailyBriefing(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const url = new URL(request.url);
    const dateParam = url.searchParams.get('date');
    const briefingDate = dateParam ? new Date(dateParam) : new Date();

    // Check feature access
    const tier = auth.user.subscription_tier || 'free';
    const featureCheck = requireFeature(tier, 'calendar_integration');
    if (featureCheck) {
      return new Response(JSON.stringify(featureCheck), {
        status: featureCheck.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const briefing = await calendar.getDailyBriefing(auth.user.id, briefingDate);

    return new Response(JSON.stringify(briefing), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Briefing error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Create calendar event (Personal tier+)
 * POST /api/calendar/events
 */
export async function createEvent(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    const { title, description, startTime, endTime, attendees, location, timeZone } = body;

    if (!title || !startTime || !endTime) {
      return new Response(JSON.stringify({
        error: 'Missing required fields: title, startTime, endTime'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check feature access
    const tier = auth.user.subscription_tier || 'free';
    const featureCheck = requireFeature(tier, 'calendar_write_access');
    if (featureCheck) {
      return new Response(JSON.stringify(featureCheck), {
        status: featureCheck.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const eventData = {
      title,
      description,
      startTime,
      endTime,
      attendees,
      location,
      timeZone
    };

    const event = await calendar.createEvent(auth.user.id, eventData);

    return new Response(JSON.stringify(event), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Create event error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Add iCal subscription
 * POST /api/calendar/ical
 */
export async function addICalSubscription(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    const { name, url } = body;

    if (!name || !url) {
      return new Response(JSON.stringify({
        error: 'Missing required fields: name, url'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check feature access
    const tier = auth.user.subscription_tier || 'free';
    const featureCheck = requireFeature(tier, 'calendar_integration');
    if (featureCheck) {
      return new Response(JSON.stringify(featureCheck), {
        status: featureCheck.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const result = await calendar.ical.addSubscription(auth.user.id, name, url);

    return new Response(JSON.stringify(result), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Add iCal error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Get calendar integrations
 * GET /api/calendar/integrations
 */
export async function getIntegrations(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const integrations = await calendar.getIntegrations(auth.user.id);

    return new Response(JSON.stringify({ integrations }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Get integrations error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Sync calendar events
 * POST /api/calendar/sync
 */
export async function syncCalendars(request, env) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    const results = await calendar.syncCalendars(auth.user.id);

    return new Response(JSON.stringify(results), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Sync error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Disconnect calendar provider
 * DELETE /api/calendar/providers/:provider
 */
export async function disconnectProvider(request, env, provider) {
  try {
    const auth = await requireAuth(request, env);
    if (auth.error) {
      return new Response(JSON.stringify({ error: auth.error }), {
        status: auth.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const calendar = new CalendarSystem(env);
    await calendar.disconnectProvider(auth.user.id, provider);

    return new Response(JSON.stringify({
      success: true,
      message: `${provider} calendar disconnected`
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Disconnect error:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
