/**
 * Boss Outbound and Inbound Call Routes
 *
 * Handles TwiML generation for Boss's outbound and inbound calls.
 */

import { generateBossIntroTwiML, generateBossResponseTwiML, generateMoshiTwiML, makeOutboundCall } from '../lib/outbound.js';
import usersConfig from '../config/users.json' with { type: 'json' };

/**
 * Check if caller is authorized to access Boss
 *
 * @param {string} callerNumber - Caller's phone number in E.164 format
 * @returns {Promise<Object|null>} User info if authorized, null otherwise
 */
async function getAuthorizedUser(callerNumber) {
	// Look up user by phone number from config
	const user = usersConfig.phoneToUser[callerNumber];

	if (user) {
		console.log(`Found authorized user: ${user.username} (${user.role})`);
		return {
			phone: user.phone,
			name: user.name,
			username: user.username,
			role: user.role,
			persona: user.persona,
			bossPhone: user.boss_phone,
		};
	}

	// TODO: In production, also query Turso database for additional users
	return null;
}

/**
 * Handle inbound calls to Boss
 *
 * This is the webhook URL set in Twilio for incoming calls.
 * SECURITY: Only authorized phone numbers can access Boss.
 */
export async function handleInboundCall(request, env) {
	try {
		// Get caller info from Twilio
		const formData = await request.formData();
		const from = formData.get('From') || '';
		const callerName = formData.get('CallerName') || 'there';

		console.log(`Inbound call from: ${from} (${callerName})`);

		// Security check: Is this caller authorized?
		const user = await getAuthorizedUser(from);

		if (!user) {
			console.warn(`Unauthorized call attempt from: ${from}`);

			// Reject unauthorized callers politely but firmly
			const unauthorizedTwiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Brian-Neural">I'm sorry, but this number is not authorized to access this service. If you believe this is an error, please contact support. Goodbye.</Say>
  <Hangup/>
</Response>`;

			return new Response(unauthorizedTwiml, {
				status: 200,
				headers: {
					'Content-Type': 'application/xml',
				},
			});
		}

		// Authorized - proceed with Boss intro
		console.log(`Authorized call from user: ${user.name} (${user.userId})`);
		const twiml = generateBossIntroTwiML(user.name);

		return new Response(twiml, {
			status: 200,
			headers: {
				'Content-Type': 'application/xml',
			},
		});

	} catch (error) {
		console.error('Error handling inbound call:', error);

		// Fallback TwiML with British voice
		const errorTwiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Brian-Neural">Boss here. I'm having a bit of trouble right now. Please try calling back in a moment.</Say>
</Response>`;

		return new Response(errorTwiml, {
			status: 200,
			headers: {
				'Content-Type': 'application/xml',
			},
		});
	}
}

/**
 * Handle MOSHI voice AI call TwiML
 *
 * This is the callback URL for MOSHI-powered voice calls.
 */
export async function handleMoshiCall(request, env) {
	try {
		// For local development, use environment variable if provided
		// For production, use the Workers proxy endpoint
		let wsUrl;

		if (env.VOICE_BRIDGE_WS_URL) {
			// Local dev: Use explicit voice bridge URL from environment
			wsUrl = env.VOICE_BRIDGE_WS_URL + '/voice/moshi';
			console.log(`LOCAL DEV: Using voice bridge at ${wsUrl}`);
		} else {
			// Production: Use Workers proxy endpoint
			const baseUrl = new URL(request.url).origin;
			wsUrl = baseUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/voice/moshi';
			console.log(`PRODUCTION: Using Workers proxy at ${wsUrl}`);
		}

		console.log(`Generating MOSHI TwiML with WebSocket URL: ${wsUrl}`);

		// Generate MOSHI TwiML
		const twiml = generateMoshiTwiML(wsUrl);

		return new Response(twiml, {
			status: 200,
			headers: {
				'Content-Type': 'application/xml',
			},
		});

	} catch (error) {
		console.error('Error generating MOSHI TwiML:', error);
		return new Response('Internal error', { status: 500 });
	}
}

/**
 * Handle Boss intro call TwiML
 *
 * This is the callback URL used when Boss calls a user.
 */
export async function handleBossIntro(request, env) {
	try {
		// Parse query params to get user name
		const url = new URL(request.url);
		const userName = url.searchParams.get('user') || 'there';

		console.log(`Generating Boss intro TwiML for user: ${userName}`);

		// Generate TwiML
		const twiml = generateBossIntroTwiML(userName);

		return new Response(twiml, {
			status: 200,
			headers: {
				'Content-Type': 'application/xml',
			},
		});

	} catch (error) {
		console.error('Error generating Boss intro:', error);
		return new Response('Internal error', { status: 500 });
	}
}

/**
 * Handle Boss response to user's answer
 *
 * This is called after the Gather completes.
 */
export async function handleBossResponse(request, env) {
	try {
		// Parse form data from Gather
		const formData = await request.formData();
		const speechResult = formData.get('SpeechResult') || '';

		console.log(`User said: "${speechResult}"`);

		// Generate response TwiML
		const twiml = generateBossResponseTwiML(speechResult);

		return new Response(twiml, {
			status: 200,
			headers: {
				'Content-Type': 'application/xml',
			},
		});

	} catch (error) {
		console.error('Error generating Boss response:', error);
		return new Response('Internal error', { status: 500 });
	}
}

/**
 * Trigger Boss to call a user
 *
 * POST /api/boss/call
 * Body: { "phone": "+19167656913", "user": "Chad" }
 */
export async function triggerBossCall(request, env) {
	try {
		// Parse request body
		const body = await request.json();
		const { phone, user } = body;

		if (!phone) {
			return new Response(JSON.stringify({
				error: 'Missing required field: phone'
			}), {
				status: 400,
				headers: { 'Content-Type': 'application/json' },
			});
		}

		console.log(`Triggering Boss call to: ${phone} (user: ${user || 'unknown'})`);

		// Build callback URL for TwiML
		// Use PUBLIC_BASE_URL for local dev, request origin for production
		const baseUrl = env.PUBLIC_BASE_URL || new URL(request.url).origin;
		const callbackUrl = `${baseUrl}/voice/moshi-call`;

		// Make the outbound call
		const callResult = await makeOutboundCall(phone, callbackUrl, env);

		return new Response(JSON.stringify({
			success: true,
			message: 'Boss is calling you now!',
			callSid: callResult.callSid,
			status: callResult.status,
		}), {
			status: 200,
			headers: { 'Content-Type': 'application/json' },
		});

	} catch (error) {
		console.error('Error triggering Boss call:', error);
		return new Response(JSON.stringify({
			error: 'Failed to initiate call',
			details: error.message,
		}), {
			status: 500,
			headers: { 'Content-Type': 'application/json' },
		});
	}
}
