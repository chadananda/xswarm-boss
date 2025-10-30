/**
 * MOSHI WebSocket Proxy Handler
 *
 * Proxies Twilio Media Streams WebSocket connections to local xSwarm Rust client.
 * This enables real-time voice processing with the MOSHI voice AI model.
 *
 * Flow:
 * Phone → Twilio → Cloudflare Workers (this) → xSwarm Rust → MOSHI
 */

const XSWARM_WS_URL = 'ws://127.0.0.1:9998';

/**
 * Handle WebSocket upgrade for MOSHI voice processing
 *
 * @param {Request} request - WebSocket upgrade request from Twilio
 * @param {Object} env - Environment variables
 * @returns {Response} WebSocket response
 */
export async function handleMoshiWebSocket(request, env) {
  try {
    // DEBUG: Log complete request details from Twilio
    console.log('MOSHI WebSocket: =============================================');
    console.log('MOSHI WebSocket: Incoming request details:');
    console.log('MOSHI WebSocket: Method:', request.method);
    console.log('MOSHI WebSocket: URL:', request.url);

    // Log ALL headers
    console.log('MOSHI WebSocket: Headers:');
    for (const [key, value] of request.headers.entries()) {
      console.log(`MOSHI WebSocket:   ${key}: ${value}`);
    }
    console.log('MOSHI WebSocket: =============================================');

    // Verify this is a WebSocket upgrade request
    const upgradeHeader = request.headers.get('Upgrade');
    if (!upgradeHeader || upgradeHeader !== 'websocket') {
      console.log('MOSHI WebSocket: ERROR - No valid WebSocket upgrade header');
      console.log('MOSHI WebSocket: Expected: "websocket", Got:', upgradeHeader);
      return new Response('Expected WebSocket upgrade', { status: 426 });
    }

    console.log('MOSHI WebSocket: Creating WebSocket pair');

    // Create WebSocket pair (client <-> server)
    const webSocketPair = new WebSocketPair();
    const [client, server] = Object.values(webSocketPair);

    // Accept the client connection (Twilio side)
    server.accept();

    console.log('MOSHI WebSocket: Accepted client connection');

    // Connect to xSwarm Rust backend
    handleProxying(server, env).catch(err => {
      console.error('MOSHI WebSocket: Proxy error:', err);
      server.close(1011, 'Proxy error');
    });

    // Return WebSocket response to Twilio
    return new Response(null, {
      status: 101,
      webSocket: client,
    });

  } catch (error) {
    console.error('MOSHI WebSocket: Upgrade error:', error);
    return new Response('WebSocket upgrade failed', { status: 500 });
  }
}

/**
 * Handle bidirectional WebSocket proxying
 *
 * @param {WebSocket} clientWs - WebSocket connection to Twilio
 * @param {Object} env - Environment variables
 */
async function handleProxying(clientWs, env) {
  let backendWs = null;
  let messageCount = 0;

  try {
    console.log(`MOSHI WebSocket: Connecting to xSwarm at ${XSWARM_WS_URL}`);

    // Connect to xSwarm Rust backend
    backendWs = new WebSocket(XSWARM_WS_URL);

    // Wait for backend connection to open
    await new Promise((resolve, reject) => {
      backendWs.addEventListener('open', () => {
        console.log('MOSHI WebSocket: Connected to xSwarm backend');
        resolve();
      });

      backendWs.addEventListener('error', (event) => {
        console.error('MOSHI WebSocket: Backend connection error:', event);
        reject(new Error('Failed to connect to xSwarm backend'));
      });

      // Timeout after 5 seconds
      setTimeout(() => reject(new Error('Backend connection timeout')), 5000);
    });

    // Set up bidirectional message forwarding

    // Client (Twilio) → Backend (xSwarm)
    clientWs.addEventListener('message', (event) => {
      try {
        messageCount++;

        // Enhanced logging: Log first 50 messages to understand protocol
        if (messageCount <= 50) {
          console.log(`MOSHI WebSocket: [${messageCount}] Twilio → Voice Bridge:`, event.data);
        } else if (messageCount % 100 === 0) {
          console.log(`MOSHI WebSocket: Forwarded ${messageCount} messages to backend`);
        }

        // Try to parse and log Twilio Media Stream events
        try {
          const message = JSON.parse(event.data);
          if (message.event) {
            console.log(`MOSHI WebSocket: Twilio Event - ${message.event}:`, message);
          }
        } catch (parseError) {
          // Not JSON, could be binary audio data
          if (messageCount <= 10) {
            console.log(`MOSHI WebSocket: Non-JSON message (${event.data.length} bytes):`, event.data);
          }
        }

        if (backendWs && backendWs.readyState === WebSocket.OPEN) {
          backendWs.send(event.data);
        } else {
          console.error('MOSHI WebSocket: Backend not ready, dropping message');
        }
      } catch (error) {
        console.error('MOSHI WebSocket: Error forwarding to backend:', error);
      }
    });

    // Backend (xSwarm) → Client (Twilio)
    backendWs.addEventListener('message', (event) => {
      try {
        // Enhanced logging: Log first few backend responses
        if (messageCount <= 10) {
          console.log(`MOSHI WebSocket: Voice Bridge → Twilio:`, event.data);
        }

        // Try to parse and log backend responses
        try {
          const message = JSON.parse(event.data);
          console.log(`MOSHI WebSocket: Backend Response:`, message);
        } catch (parseError) {
          // Not JSON, could be binary audio data
          if (messageCount <= 5) {
            console.log(`MOSHI WebSocket: Backend binary data (${event.data.length} bytes)`);
          }
        }

        if (clientWs.readyState === WebSocket.OPEN) {
          clientWs.send(event.data);
        } else {
          console.error('MOSHI WebSocket: Client not ready, dropping response');
        }
      } catch (error) {
        console.error('MOSHI WebSocket: Error forwarding to client:', error);
      }
    });

    // Handle client close
    clientWs.addEventListener('close', (event) => {
      console.log(`MOSHI WebSocket: Client closed (code: ${event.code}, reason: ${event.reason})`);
      if (backendWs && backendWs.readyState === WebSocket.OPEN) {
        backendWs.close(1000, 'Client disconnected');
      }
    });

    // Handle backend close
    backendWs.addEventListener('close', (event) => {
      console.log(`MOSHI WebSocket: Backend closed (code: ${event.code}, reason: ${event.reason})`);
      if (clientWs.readyState === WebSocket.OPEN) {
        clientWs.close(1000, 'Backend disconnected');
      }
    });

    // Handle client error
    clientWs.addEventListener('error', (event) => {
      console.error('MOSHI WebSocket: Client error:', event);
      if (backendWs && backendWs.readyState === WebSocket.OPEN) {
        backendWs.close(1011, 'Client error');
      }
    });

    // Handle backend error
    backendWs.addEventListener('error', (event) => {
      console.error('MOSHI WebSocket: Backend error:', event);
      if (clientWs.readyState === WebSocket.OPEN) {
        clientWs.close(1011, 'Backend error');
      }
    });

  } catch (error) {
    console.error('MOSHI WebSocket: Proxy setup error:', error);

    // Clean up connections
    if (backendWs) {
      try {
        backendWs.close(1011, 'Setup error');
      } catch (e) {
        console.error('MOSHI WebSocket: Error closing backend:', e);
      }
    }

    if (clientWs.readyState === WebSocket.OPEN) {
      clientWs.close(1011, 'Setup error');
    }

    throw error;
  }
}
