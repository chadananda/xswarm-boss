/**
 * Email Routes (SendGrid Integration)
 *
 * Handles:
 * - Inbound email from SendGrid (parse webhook)
 * - Outbound email via SendGrid API
 * - Email-based Boss communication for progress reports and directions
 * - Intelligent AI responses via Claude or Rust supervisor
 */

import usersConfig from '../config/users.json' with { type: 'json' };
import {
  getClaudeResponse,
  processDevTask,
  parseMessageType,
  getStatusResponse,
  getHelpResponse
} from '../lib/claude.js';
import { getSupervisorClient } from '../lib/supervisor-client.js';

/**
 * Validate email addresses - only allow authorized user emails
 *
 * @param {string} email - Email address to validate
 * @returns {Object|null} User info if authorized, null otherwise
 */
function getAuthorizedUserByEmail(email) {
	// Define forwarding addresses that route to admin
	const forwardingAddresses = {
		'privacy@xswarm.ai': { type: 'forwarding', forwardTo: 'chadananda@gmail.com', purpose: 'privacy' },
		'contact@xswarm.ai': { type: 'forwarding', forwardTo: 'chadananda@gmail.com', purpose: 'contact' },
		'dpo@xswarm.ai': { type: 'forwarding', forwardTo: 'chadananda@gmail.com', purpose: 'dpo' },
	};

	// Check if this is a forwarding address
	if (forwardingAddresses[email]) {
		return {
			...forwardingAddresses[email],
			email: email,
		};
	}

	// Check if this is a boss email trying to send to a user
	for (const user of usersConfig.users) {
		if (email === user.boss_email) {
			return {
				type: 'boss',
				userEmail: user.email,
				bossEmail: user.boss_email,
				name: user.name,
				username: user.username,
			};
		}
		if (email === user.email) {
			return {
				type: 'user',
				userEmail: user.email,
				bossEmail: user.boss_email,
				name: user.name,
				username: user.username,
			};
		}
	}
	return null;
}

/**
 * Send email via SendGrid API
 *
 * @param {string} to - Recipient email
 * @param {string} from - Sender email
 * @param {string} subject - Email subject
 * @param {string} text - Plain text body
 * @param {string} html - HTML body (optional)
 * @param {Object} env - Environment variables
 */
async function sendEmail(to, from, subject, text, html, env) {
	const SENDGRID_API_KEY = env.SENDGRID_API_KEY;

	if (!SENDGRID_API_KEY) {
		throw new Error('SENDGRID_API_KEY not configured');
	}

	const emailData = {
		personalizations: [{
			to: [{ email: to }],
			subject: subject,
		}],
		from: { email: from },
		content: [
			{ type: 'text/plain', value: text },
		],
	};

	// Add HTML version if provided
	if (html) {
		emailData.content.push({ type: 'text/html', value: html });
	}

	const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
		method: 'POST',
		headers: {
			'Authorization': `Bearer ${SENDGRID_API_KEY}`,
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(emailData),
	});

	if (!response.ok) {
		const error = await response.text();
		throw new Error(`SendGrid API error: ${error}`);
	}

	return { success: true, messageId: response.headers.get('x-message-id') };
}

/**
 * Handle inbound email from SendGrid Parse API
 *
 * This is the webhook URL set in SendGrid for incoming emails.
 * SendGrid will POST parsed email data here.
 */
export async function handleInboundEmail(request, env) {
	try {
		// SendGrid sends form-encoded data
		const formData = await request.formData();

		const from = formData.get('from') || '';
		const to = formData.get('to') || '';
		const subject = formData.get('subject') || '';
		const text = formData.get('text') || '';
		const html = formData.get('html') || '';

		// Input validation: Check required fields
		if (!from || !to) {
			console.warn('Email webhook missing required fields:', { from, to, subject });
			return new Response('Missing required fields', { status: 400 });
		}

		console.log(`Inbound email from: ${from} to: ${to}`);
		console.log(`Subject: ${subject}`);

		// Extract email address from "Name <email@domain.com>" format
		const fromEmail = from.match(/<(.+?)>/) ? from.match(/<(.+?)>/)[1] : from;
		const toEmail = to.match(/<(.+?)>/) ? to.match(/<(.+?)>/)[1] : to;

		console.log(`Extracted emails - From: "${fromEmail}", To: "${toEmail}"`);

		// Validate email format (basic check)
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!emailRegex.test(fromEmail) || !emailRegex.test(toEmail)) {
			console.warn('Invalid email format:', { fromEmail, toEmail });
			return new Response('Invalid email format', { status: 400 });
		}

		// Security check: Validate sender and recipient
		console.log(`Checking authorization for: ${fromEmail} → ${toEmail}`);
		const toUser = getAuthorizedUserByEmail(toEmail);

		console.log(`To user result:`, toUser);

		if (!toUser) {
			console.warn(`Unauthorized recipient: ${toEmail}`);

			// Silently drop unauthorized emails (no bounce to avoid spam)
			return new Response('OK', { status: 200 });
		}

		// Handle forwarding addresses
		if (toUser.type === 'forwarding') {
			console.log(`Forwarding email from ${fromEmail} to ${toUser.forwardTo} (purpose: ${toUser.purpose})`);

			// Forward the original email to admin
			const forwardSubject = `[${toUser.purpose.toUpperCase()}] ${subject}`;
			const forwardText = `Forwarded from: ${from}\nOriginal To: ${to}\n\n---\n\n${text}`;
			const forwardHtml = html ?
				`<div style="background: #f5f5f5; padding: 10px; margin-bottom: 20px;">
					<strong>Forwarded from:</strong> ${from}<br>
					<strong>Original To:</strong> ${to}
				</div>
				<hr>
				${html}` : null;

			await sendEmail(
				toUser.forwardTo,
				toUser.email,
				forwardSubject,
				forwardText,
				forwardHtml,
				env
			);

			console.log(`Successfully forwarded email to ${toUser.forwardTo}`);
			return new Response('OK', { status: 200 });
		}

		// For non-forwarding addresses, validate sender
		const fromUser = getAuthorizedUserByEmail(fromEmail);
		console.log(`From user result:`, fromUser);

		if (!fromUser) {
			console.warn(`Unauthorized sender: ${fromEmail}`);
			// Silently drop unauthorized emails (no bounce to avoid spam)
			return new Response('OK', { status: 200 });
		}

		// Ensure communication is only between user and their boss
		if (fromUser.userEmail !== toUser.userEmail) {
			console.warn(`Email not between paired accounts: ${fromEmail} → ${toEmail}`);
			return new Response('OK', { status: 200 });
		}

		// Process the email based on sender type
		if (fromUser.type === 'user') {
			// User → Boss: This is a direction/question for development
			console.log(`User ${fromUser.name} sent direction to Boss`);
			console.log(`Subject: ${subject}`);
			console.log(`Message: ${text.substring(0, 200)}...`);

			// Process the email content with Claude AI
			const response = await processEmailWithAI(fromUser, subject, text, env);

			// Send intelligent auto-reply
			await sendEmail(
				fromUser.userEmail,
				fromUser.bossEmail,
				`Re: ${subject}`,
				response,
				null,
				env
			);

			console.log(`Sent AI-powered response to ${fromUser.name}`);
		} else {
			// Boss → User: This is a progress report (shouldn't happen via inbound)
			console.log(`Received email from Boss address (unusual)`);
		}

		return new Response('OK', { status: 200 });

	} catch (error) {
		console.error('Error handling inbound email:', error);
		return new Response('Internal error', { status: 500 });
	}
}

/**
 * Send Boss progress report via email
 *
 * POST /api/boss/email
 * Body: {
 *   "to": "chadananda@gmail.com",
 *   "subject": "Daily Progress Report",
 *   "message": "Here's what I accomplished today..."
 * }
 */
export async function sendBossEmail(request, env) {
	try {
		const body = await request.json();
		const { to, subject, message } = body;

		if (!to || !subject || !message) {
			return new Response(JSON.stringify({
				error: 'Missing required fields: to, subject, message'
			}), {
				status: 400,
				headers: { 'Content-Type': 'application/json' },
			});
		}

		// Validate recipient
		const user = getAuthorizedUserByEmail(to);

		if (!user || user.type !== 'user') {
			return new Response(JSON.stringify({
				error: 'Unauthorized recipient. Boss can only email authorized users.'
			}), {
				status: 403,
				headers: { 'Content-Type': 'application/json' },
			});
		}

		console.log(`Sending Boss email to ${user.name}: ${subject}`);

		// Send email from Boss address
		await sendEmail(
			user.userEmail,
			user.bossEmail,
			subject,
			message,
			null,
			env
		);

		return new Response(JSON.stringify({
			success: true,
			message: 'Email sent successfully',
		}), {
			status: 200,
			headers: { 'Content-Type': 'application/json' },
		});

	} catch (error) {
		console.error('Error sending Boss email:', error);
		return new Response(JSON.stringify({
			error: 'Failed to send email',
			details: error.message,
		}), {
			status: 500,
			headers: { 'Content-Type': 'application/json' },
		});
	}
}

/**
 * Process incoming email with Supervisor or Claude AI
 *
 * @param {Object} user - User information
 * @param {string} subject - Email subject line
 * @param {string} content - Email body content
 * @param {Object} env - Environment variables
 * @returns {Promise<string>} AI-generated response
 */
async function processEmailWithAI(user, subject, content, env) {
	try {
		// Try to send to supervisor WebSocket first
		const supervisor = getSupervisorClient({
			authToken: env.SUPERVISOR_TOKEN || 'dev-token-12345',
		});

		if (supervisor.isReady()) {
			console.log(`[Email] Sending to supervisor for ${user.name}`);
			try {
				const response = await supervisor.sendEmailEvent({
					from: user.email,
					to: user.bossEmail,
					subject: subject,
					body: content,
					user: user.username,
				});

				console.log(`[Email] Supervisor response:`, response);

				// If supervisor returns a response message, use it
				if (response.type === 'send_email_response') {
					return response.body;
				}

				// If just acknowledged, fall back to local processing
				console.log(`[Email] Supervisor acknowledged, falling back to local processing`);
			} catch (error) {
				console.error('[Email] Supervisor error, falling back to local processing:', error);
			}
		} else {
			console.log('[Email] Supervisor not ready, using local processing');
		}

		// Fallback to local processing
		// Combine subject and content for AI processing
		const fullMessage = `Subject: ${subject}\n\n${content}`;

		// Parse message type for intelligent routing
		const messageType = parseMessageType(content);

		// Handle quick commands locally for speed
		if (messageType === 'status') {
			return getStatusResponse(user);
		}

		if (messageType === 'help') {
			return getHelpResponse(user, 'email');
		}

		// For development tasks, use specialized processing
		if (messageType === 'task') {
			console.log(`Processing development task via email for ${user.name}`);
			return await processDevTask(user, fullMessage, env, 'email');
		}

		// For questions and general messages, use Claude AI with email context
		console.log(`Getting Claude AI email response for ${user.name}`);
		return await getClaudeResponse(user, fullMessage, 'email', env);

	} catch (error) {
		console.error('Error processing email with AI:', error);
		return `Hello ${user.name},

I received your email but encountered an issue processing it. I'll review your message and send you a detailed response shortly.

Best regards,
Your Boss Assistant 🤖`;
	}
}
