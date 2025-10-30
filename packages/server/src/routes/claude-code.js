/**
 * Claude Code Integration API Routes
 *
 * Provides HTTP endpoints for:
 * - Session management (create, connect, disconnect)
 * - Message routing between Admin and Claude Code
 * - Cost tracking and usage monitoring
 * - Session status and history
 *
 * Integrates with Rust supervisor WebSocket for bidirectional communication
 */

import { getUserById, getUserByPhone, getUserByXswarmPhone } from '../lib/users.js';

/**
 * Helper: Get WebSocket connection to Rust supervisor
 *
 * @param {Object} env - Cloudflare Worker environment
 * @returns {Promise<WebSocket>} WebSocket connection
 */
async function getSupervisorWebSocket(env) {
  const supervisorUrl = env.SUPERVISOR_WEBSOCKET_URL || 'ws://localhost:9999';
  const ws = new WebSocket(supervisorUrl);

  return new Promise((resolve, reject) => {
    ws.addEventListener('open', () => {
      // Authenticate with supervisor
      ws.send(JSON.stringify({
        type: 'auth',
        token: env.SUPERVISOR_TOKEN || 'dev-token-12345'
      }));
      resolve(ws);
    });

    ws.addEventListener('error', (error) => {
      reject(new Error(`WebSocket connection failed: ${error.message}`));
    });

    // Set timeout
    setTimeout(() => reject(new Error('WebSocket connection timeout')), 5000);
  });
}

/**
 * Helper: Send message to supervisor and wait for response
 *
 * @param {WebSocket} ws - WebSocket connection
 * @param {Object} message - Message to send
 * @returns {Promise<Object>} Response from supervisor
 */
async function sendSupervisorMessage(ws, message) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      ws.close();
      reject(new Error('Supervisor response timeout'));
    }, 10000);

    ws.addEventListener('message', (event) => {
      clearTimeout(timeout);
      try {
        const response = JSON.parse(event.data);
        resolve(response);
      } catch (error) {
        reject(new Error(`Failed to parse response: ${error.message}`));
      }
    });

    ws.send(JSON.stringify(message));
  });
}

/**
 * POST /api/claude-code/sessions
 *
 * Create a new Claude Code session
 *
 * Body:
 * {
 *   "user_id": "user123",
 *   "project_path": "/path/to/project"
 * }
 */
export async function createSession(request, env) {
  try {
    const { user_id, project_path } = await request.json();

    if (!user_id || !project_path) {
      return new Response(JSON.stringify({
        error: 'user_id and project_path are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Verify user exists
    const user = await getUserById(user_id);
    if (!user) {
      return new Response(JSON.stringify({
        error: 'User not found'
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Generate session ID
    const session_id = crypto.randomUUID();

    // Connect to supervisor
    const ws = await getSupervisorWebSocket(env);

    try {
      // Send connection request
      const response = await sendSupervisorMessage(ws, {
        type: 'claude_code_connect',
        session_id,
        project_path,
        user_id
      });

      if (response.type === 'claude_code_connected') {
        return new Response(JSON.stringify({
          session_id: response.session_id,
          status: response.status,
          user_id,
          project_path,
          timestamp: response.timestamp
        }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' }
        });
      } else if (response.type === 'error') {
        return new Response(JSON.stringify({
          error: response.message
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      return new Response(JSON.stringify({
        error: 'Unexpected response from supervisor'
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });

    } finally {
      ws.close();
    }

  } catch (error) {
    console.error('Error creating Claude Code session:', error);
    return new Response(JSON.stringify({
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * POST /api/claude-code/sessions/:session_id/messages
 *
 * Send message to Claude Code session
 *
 * Body:
 * {
 *   "message": "Check git status",
 *   "context": {
 *     "source": "sms",
 *     "from": "+1234567890"
 *   }
 * }
 */
export async function sendMessage(request, env) {
  try {
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/');
    const session_id = pathParts[pathParts.length - 2]; // .../sessions/{id}/messages

    const { message, context } = await request.json();

    if (!message) {
      return new Response(JSON.stringify({
        error: 'message is required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Connect to supervisor
    const ws = await getSupervisorWebSocket(env);

    try {
      // Send message
      const response = await sendSupervisorMessage(ws, {
        type: 'claude_code_message',
        session_id,
        message,
        context: context || null
      });

      if (response.type === 'claude_code_response') {
        return new Response(JSON.stringify({
          message_id: response.message_id,
          content: response.content,
          cost_usd: response.cost_usd,
          timestamp: response.timestamp
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      } else if (response.type === 'error') {
        return new Response(JSON.stringify({
          error: response.message
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      return new Response(JSON.stringify({
        error: 'Unexpected response from supervisor'
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });

    } finally {
      ws.close();
    }

  } catch (error) {
    console.error('Error sending Claude Code message:', error);
    return new Response(JSON.stringify({
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * DELETE /api/claude-code/sessions/:session_id
 *
 * Disconnect Claude Code session
 */
export async function disconnectSession(request, env) {
  try {
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/');
    const session_id = pathParts[pathParts.length - 1];

    // Connect to supervisor
    const ws = await getSupervisorWebSocket(env);

    try {
      // Send disconnection request
      const response = await sendSupervisorMessage(ws, {
        type: 'claude_code_disconnect',
        session_id
      });

      if (response.type === 'claude_code_disconnected') {
        return new Response(JSON.stringify({
          session_id: response.session_id,
          reason: response.reason,
          timestamp: response.timestamp
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      } else if (response.type === 'error') {
        return new Response(JSON.stringify({
          error: response.message
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      return new Response(JSON.stringify({
        error: 'Unexpected response from supervisor'
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });

    } finally {
      ws.close();
    }

  } catch (error) {
    console.error('Error disconnecting Claude Code session:', error);
    return new Response(JSON.stringify({
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * POST /api/claude-code/route-conversation
 *
 * Route Admin conversation to Claude Code (smart routing)
 *
 * Body:
 * {
 *   "from": "+1234567890",
 *   "message": "Check the status of my project",
 *   "channel": "sms"
 * }
 */
export async function routeConversation(request, env) {
  try {
    const { from, message, channel } = await request.json();

    if (!from || !message) {
      return new Response(JSON.stringify({
        error: 'from and message are required'
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Identify user
    let user;
    if (channel === 'sms') {
      user = await getUserByPhone(from) || await getUserByXswarmPhone(from);
    } else {
      user = await getUserById(from);
    }

    if (!user) {
      return new Response(JSON.stringify({
        error: 'User not found'
      }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check if message is Claude Code related
    const claudeCodeKeywords = [
      'project', 'code', 'git', 'build', 'test', 'deploy',
      'commit', 'branch', 'status', 'develop', 'debug',
      'fix', 'error', 'bug', 'run', 'compile'
    ];

    const isClaudeCodeRelated = claudeCodeKeywords.some(keyword =>
      message.toLowerCase().includes(keyword)
    );

    if (!isClaudeCodeRelated) {
      return new Response(JSON.stringify({
        routed: false,
        reason: 'Message does not appear to be Claude Code related'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // TODO: Check for active Claude Code session for user
    // For now, return routing decision without execution

    return new Response(JSON.stringify({
      routed: true,
      user_id: user.id,
      message,
      channel,
      action: 'would_route_to_claude_code'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error) {
    console.error('Error routing conversation:', error);
    return new Response(JSON.stringify({
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * GET /api/claude-code/sessions/:session_id/cost
 *
 * Get cost tracking for a session
 */
export async function getSessionCost(request, env) {
  try {
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/');
    const session_id = pathParts[pathParts.length - 2]; // .../sessions/{id}/cost

    // Connect to supervisor
    const ws = await getSupervisorWebSocket(env);

    try {
      // Request session status (includes cost)
      const response = await sendSupervisorMessage(ws, {
        type: 'get_session_status',
        session_id
      });

      if (response.type === 'session_status') {
        return new Response(JSON.stringify({
          session_id,
          cost_usd: response.cost_usd,
          message_count: response.message_count,
          duration_seconds: response.duration_seconds,
          status: response.status
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      } else if (response.type === 'error') {
        return new Response(JSON.stringify({
          error: response.message
        }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      return new Response(JSON.stringify({
        error: 'Unexpected response from supervisor'
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });

    } finally {
      ws.close();
    }

  } catch (error) {
    console.error('Error getting session cost:', error);
    return new Response(JSON.stringify({
      error: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
