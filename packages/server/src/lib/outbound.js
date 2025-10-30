/**
 * Outbound Calling with Twilio
 *
 * Enables Boss to initiate phone calls to users.
 */

/**
 * Make an outbound call using Twilio API
 *
 * @param {string} toNumber - Phone number to call (E.164 format)
 * @param {string} callbackUrl - URL for TwiML instructions
 * @param {Object} env - Environment variables (TWILIO credentials)
 * @returns {Promise<Object>} Call SID and status
 */
export async function makeOutboundCall(toNumber, callbackUrl, env) {
	const accountSid = env.TWILIO_ACCOUNT_SID;
	const authToken = env.TWILIO_AUTH_TOKEN;
	const fromNumber = env.TWILIO_PHONE_NUMBER;

	if (!accountSid || !authToken || !fromNumber) {
		throw new Error('Missing Twilio credentials in environment');
	}

	// Twilio API endpoint
	const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Calls.json`;

	// Prepare form data
	const formData = new URLSearchParams();
	formData.append('To', toNumber);
	formData.append('From', fromNumber);
	formData.append('Url', callbackUrl); // TwiML instructions URL
	formData.append('Method', 'POST');

	// Basic Auth header
	const credentials = btoa(`${accountSid}:${authToken}`);

	try {
		const response = await fetch(url, {
			method: 'POST',
			headers: {
				'Authorization': `Basic ${credentials}`,
				'Content-Type': 'application/x-www-form-urlencoded',
			},
			body: formData.toString(),
		});

		if (!response.ok) {
			const errorText = await response.text();
			throw new Error(`Twilio API error: ${response.status} - ${errorText}`);
		}

		const callData = await response.json();

		console.log(`✓ Outbound call initiated: ${callData.sid}`);
		console.log(`  To: ${toNumber}`);
		console.log(`  From: ${fromNumber}`);
		console.log(`  Status: ${callData.status}`);

		return {
			callSid: callData.sid,
			status: callData.status,
			to: toNumber,
			from: fromNumber,
		};

	} catch (error) {
		console.error('Failed to initiate outbound call:', error);
		throw error;
	}
}

/**
 * Generate TwiML for MOSHI voice AI integration
 *
 * Connects the call to MOSHI via WebSocket for real-time voice processing.
 *
 * @param {string} baseUrl - Base URL for WebSocket (e.g., wss://xswarm-boss.workers.dev or ws://localhost:8787)
 * @returns {string} TwiML XML
 */
export function generateMoshiTwiML(wsUrl) {
	// Pure MOSHI - no TTS, immediate WebSocket connection
	const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${wsUrl}" track="both_tracks"/>
  </Connect>
</Response>`;

	return twiml;
}

/**
 * Generate TwiML for Boss introduction call
 *
 * @param {string} userName - User's name
 * @param {string} persona - Persona name (default: boss)
 * @returns {string} TwiML XML
 */
export function generateBossIntroTwiML(userName, persona = 'boss') {
	// Boss greeting - concise for voicemail
	const greeting = `Boss here. Hey ${userName}, your voice assistant is now up and running.`;

	// Capabilities introduction - brief version
	const capabilities = `I can help with software architecture, code reviews, planning, and technical decisions.`;

	// Ask how to help
	const question = `What can I help you with today?`;

	// Voicemail-friendly ending
	const voicemailEnding = `If you're not available, no worries. I'll try calling back later. You can also reach me anytime through the app. Talk soon!`;

	// Full conversation - using Polly.Brian for British accent (Jarvis-like)
	const voice = "Polly.Brian-Neural";
	const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="${voice}">${greeting}</Say>
  <Pause length="1"/>
  <Say voice="${voice}">${capabilities}</Say>
  <Pause length="1"/>
  <Say voice="${voice}">${question}</Say>
  <Gather input="speech" timeout="10" speechTimeout="auto" action="/voice/boss-response" method="POST">
    <Say voice="${voice}">I'm listening.</Say>
  </Gather>
  <Say voice="${voice}">${voicemailEnding}</Say>
</Response>`;

	return twiml;
}

/**
 * Generate TwiML response to user's answer
 *
 * @param {string} userSpeech - Transcribed user speech from Gather
 * @returns {string} TwiML XML
 */
export function generateBossResponseTwiML(userSpeech) {
	// Simple acknowledgment for now
	// In a full implementation, this would call an LLM to generate a contextual response

	let response;
	let shouldEnd = false;

	if (!userSpeech || userSpeech.trim() === '') {
		response = `Sorry, I didn't catch that. Could you repeat that?`;
	} else {
		// Check for common responses
		const lowerSpeech = userSpeech.toLowerCase();

		// Check if user wants to end the call
		if (lowerSpeech.includes('goodbye') ||
		    lowerSpeech.includes('bye') ||
		    lowerSpeech.includes('that\'s all') ||
		    lowerSpeech.includes('thanks that\'s it') ||
		    lowerSpeech.includes('nothing else') ||
		    lowerSpeech.includes('no thanks') ||
		    lowerSpeech.includes('gotta go') ||
		    lowerSpeech.includes('have to go') ||
		    lowerSpeech.includes('talk later') ||
		    lowerSpeech.includes('talk to you later')) {
			response = `Sounds good! Feel free to reach out anytime. Take care!`;
			shouldEnd = true;
		} else if (lowerSpeech.includes('nothing') || lowerSpeech.includes('not right now')) {
			response = `No problem. I'm here whenever you need me. Anything else on your mind?`;
		} else if (lowerSpeech.includes('how are you')) {
			response = `I'm doing great, thanks for asking. All systems running smoothly. What can I help you with?`;
		} else {
			response = `That's a good question about ${userSpeech}. I'd love to dig into that with you. For now though, I'm still getting my full capabilities online. But when we're connected via the app, I can give you detailed architectural guidance on that. What else can I help with?`;
		}
	}

	// British neural voice for Jarvis-like quality
	const voice = "Polly.Brian-Neural";

	// Only end if user clearly indicated they want to
	if (shouldEnd) {
		return `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="${voice}">${response}</Say>
  <Hangup/>
</Response>`;
	}

	// Otherwise, keep the conversation going
	const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="${voice}">${response}</Say>
  <Gather input="speech" timeout="15" speechTimeout="auto" action="/voice/boss-response" method="POST">
    <Say voice="${voice}">I'm listening.</Say>
  </Gather>
  <Say voice="${voice}">Still there? Let me know if you need anything. Otherwise, feel free to hang up anytime.</Say>
  <Pause length="3"/>
  <Say voice="${voice}">Alright, catch you later!</Say>
</Response>`;

	return twiml;
}

/**
 * Escape XML special characters in speech text
 *
 * @param {string} text - Text to escape
 * @returns {string} XML-safe text
 */
function escapeXml(text) {
	return text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}
