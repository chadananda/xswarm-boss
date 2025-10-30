/**
 * Supervisor Initialization
 *
 * This module handles connecting to the Rust supervisor WebSocket
 * when running in development mode (local Node.js).
 *
 * Note: In production Cloudflare Workers, WebSocket client connections
 * are not supported. This integration only works in local dev mode.
 */

import { initializeSupervisor } from './supervisor-client.js';

let supervisorInitialized = false;

/**
 * Initialize supervisor connection if running locally
 * @param {Object} env - Environment variables
 */
export async function initSupervisorIfLocal(env) {
  // Only initialize in local development (not in Cloudflare Workers)
  // Cloudflare Workers don't support WebSocket clients
  if (supervisorInitialized) {
    return;
  }

  // Check if we're running locally (presence of local dev indicators)
  const isLocal = env.ENVIRONMENT === 'local' ||
                  process?.env?.NODE_ENV === 'development' ||
                  typeof process !== 'undefined';

  if (!isLocal) {
    console.log('[Supervisor] Running in Cloudflare Workers - supervisor integration disabled');
    return;
  }

  try {
    console.log('[Supervisor] Initializing local supervisor connection...');

    await initializeSupervisor({
      url: env.SUPERVISOR_URL || 'ws://127.0.0.1:9999',
      authToken: env.SUPERVISOR_TOKEN || 'dev-token-12345',
    });

    supervisorInitialized = true;
    console.log('[Supervisor] Successfully connected to supervisor');
  } catch (error) {
    console.error('[Supervisor] Failed to connect:', error);
    console.log('[Supervisor] Will fall back to local processing');
  }
}

export { supervisorInitialized };
