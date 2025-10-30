/**
 * xSwarm Boss - Comprehensive Health Check System
 *
 * Provides health check endpoints for monitoring:
 * - Basic health: /health
 * - Readiness: /health/ready (all dependencies ready)
 * - Liveness: /health/live (worker is alive)
 * - Detailed: /health/detailed (full diagnostic info)
 *
 * Usage: Import and add to your Cloudflare Worker routes
 */

/**
 * Check database connectivity
 */
async function checkDatabase(env) {
  try {
    const db = env.DB || createDatabaseClient(env);
    const startTime = Date.now();

    await db.execute('SELECT 1');

    return {
      status: 'healthy',
      responseTime: Date.now() - startTime,
      message: 'Database connection OK',
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error.message,
      message: 'Database connection failed',
    };
  }
}

/**
 * Check external API connectivity
 */
async function checkExternalAPI(name, url, headers = {}) {
  try {
    const startTime = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(url, {
      method: 'GET',
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeout);

    return {
      status: response.ok ? 'healthy' : 'degraded',
      responseTime: Date.now() - startTime,
      statusCode: response.status,
      message: `${name} API responding`,
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error.message,
      message: `${name} API unreachable`,
    };
  }
}

/**
 * Check Anthropic API
 */
async function checkAnthropicAPI(env) {
  if (!env.ANTHROPIC_API_KEY) {
    return {
      status: 'not_configured',
      message: 'Anthropic API key not set',
    };
  }

  return await checkExternalAPI(
    'Anthropic',
    'https://api.anthropic.com/v1/messages',
    {
      'x-api-key': env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    }
  );
}

/**
 * Check Stripe API
 */
async function checkStripeAPI(env) {
  if (!env.STRIPE_SECRET_KEY) {
    return {
      status: 'not_configured',
      message: 'Stripe API key not set',
    };
  }

  return await checkExternalAPI(
    'Stripe',
    'https://api.stripe.com/v1/balance',
    {
      'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
    }
  );
}

/**
 * Check SendGrid API
 */
async function checkSendGridAPI(env) {
  if (!env.SENDGRID_API_KEY) {
    return {
      status: 'not_configured',
      message: 'SendGrid API key not set',
    };
  }

  return await checkExternalAPI(
    'SendGrid',
    'https://api.sendgrid.com/v3/user/profile',
    {
      'Authorization': `Bearer ${env.SENDGRID_API_KEY}`,
    }
  );
}

/**
 * Check R2 Storage
 */
async function checkR2Storage(env) {
  try {
    if (!env.R2_BUCKET) {
      return {
        status: 'not_configured',
        message: 'R2 bucket not configured',
      };
    }

    const startTime = Date.now();

    // Try to list objects (limited to 1)
    await env.R2_BUCKET.list({ limit: 1 });

    return {
      status: 'healthy',
      responseTime: Date.now() - startTime,
      message: 'R2 storage accessible',
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      error: error.message,
      message: 'R2 storage error',
    };
  }
}

/**
 * Get system metrics
 */
function getSystemMetrics() {
  return {
    timestamp: new Date().toISOString(),
    uptime: performance.now(),
    memory: {
      // Note: Cloudflare Workers don't expose memory usage
      // This is a placeholder for future metrics
      available: 'N/A',
    },
  };
}

/**
 * Basic health check - returns 200 if worker is running
 */
export async function handleBasicHealth(request, env) {
  return new Response(
    JSON.stringify({
      status: 'ok',
      timestamp: new Date().toISOString(),
      service: 'xswarm-boss',
      version: env.VERSION || '1.0.0',
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}

/**
 * Readiness check - returns 200 if all dependencies are ready
 */
export async function handleReadinessCheck(request, env) {
  const checks = {
    database: await checkDatabase(env),
    r2_storage: await checkR2Storage(env),
  };

  // Check if any critical service is unhealthy
  const isReady = Object.values(checks).every(
    check => check.status === 'healthy' || check.status === 'not_configured'
  );

  const response = {
    ready: isReady,
    timestamp: new Date().toISOString(),
    checks,
  };

  return new Response(JSON.stringify(response, null, 2), {
    status: isReady ? 200 : 503,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Liveness check - returns 200 if worker is alive and processing requests
 */
export async function handleLivenessCheck(request, env) {
  const startTime = Date.now();

  // Perform a simple computation to ensure worker is responsive
  const testValue = Math.random() * 1000;
  const computed = Math.sqrt(testValue);

  return new Response(
    JSON.stringify({
      alive: true,
      timestamp: new Date().toISOString(),
      responseTime: Date.now() - startTime,
      test: {
        input: testValue,
        output: computed,
        passed: !isNaN(computed),
      },
    }),
    {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}

/**
 * Detailed health check - returns comprehensive diagnostic information
 */
export async function handleDetailedHealth(request, env) {
  const startTime = Date.now();

  // Run all checks in parallel
  const [database, anthropic, stripe, sendgrid, r2] = await Promise.all([
    checkDatabase(env),
    checkAnthropicAPI(env),
    checkStripeAPI(env),
    checkSendGridAPI(env),
    checkR2Storage(env),
  ]);

  const checks = {
    database,
    apis: {
      anthropic,
      stripe,
      sendgrid,
    },
    storage: {
      r2,
    },
  };

  // Calculate overall health
  const allChecks = [
    database,
    anthropic,
    stripe,
    sendgrid,
    r2,
  ];

  const healthyCount = allChecks.filter(c => c.status === 'healthy').length;
  const unhealthyCount = allChecks.filter(c => c.status === 'unhealthy').length;
  const notConfiguredCount = allChecks.filter(c => c.status === 'not_configured').length;
  const degradedCount = allChecks.filter(c => c.status === 'degraded').length;

  let overallStatus = 'healthy';
  if (unhealthyCount > 0) {
    overallStatus = 'unhealthy';
  } else if (degradedCount > 0) {
    overallStatus = 'degraded';
  }

  const response = {
    status: overallStatus,
    timestamp: new Date().toISOString(),
    responseTime: Date.now() - startTime,
    summary: {
      total: allChecks.length,
      healthy: healthyCount,
      unhealthy: unhealthyCount,
      degraded: degradedCount,
      not_configured: notConfiguredCount,
    },
    checks,
    system: getSystemMetrics(),
    service: {
      name: 'xswarm-boss',
      version: env.VERSION || '1.0.0',
      environment: env.ENVIRONMENT || 'production',
    },
  };

  // Return 503 if any critical service is unhealthy
  const statusCode = overallStatus === 'unhealthy' ? 503 : 200;

  return new Response(JSON.stringify(response, null, 2), {
    status: statusCode,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Create database client helper
 */
function createDatabaseClient(env) {
  // This is a placeholder - actual implementation would use @libsql/client
  // In Cloudflare Workers, you'd need to import and configure the client
  return {
    execute: async (sql) => {
      // Placeholder
      throw new Error('Database not configured');
    },
  };
}

/**
 * Route handler for all health check endpoints
 */
export async function handleHealthRoute(request, env) {
  const url = new URL(request.url);
  const path = url.pathname;

  // Basic health check
  if (path === '/health') {
    return await handleBasicHealth(request, env);
  }

  // Readiness probe
  if (path === '/health/ready') {
    return await handleReadinessCheck(request, env);
  }

  // Liveness probe
  if (path === '/health/live') {
    return await handleLivenessCheck(request, env);
  }

  // Detailed health check
  if (path === '/health/detailed') {
    return await handleDetailedHealth(request, env);
  }

  // Unknown health endpoint
  return new Response(
    JSON.stringify({
      error: 'Unknown health endpoint',
      available: ['/health', '/health/ready', '/health/live', '/health/detailed'],
    }),
    {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    }
  );
}
