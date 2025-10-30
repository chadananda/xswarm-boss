/**
 * Boss AI - Simple Message Router
 *
 * Philosophy: Minimal, testable, easy to understand, easy to extend
 * Based on SIMPLE_DESIGN.md specification
 *
 * Architecture:
 * 1. Pure functions for business logic (no side effects)
 * 2. Minimal database interface layer (for mocking in tests)
 * 3. Separation of routing logic from database operations
 *
 * This router handles:
 * 1. SMS/Email/API messages from any channel
 * 2. Routes admin messages to Claude Code
 * 3. Handles simple commands (calendar, reminders)
 * 4. Responds back through the same channel
 */

import { createClient } from '@libsql/client';

// =============================================================================
// PURE FUNCTIONS - Business Logic (No Side Effects)
// =============================================================================

/**
 * Parse natural language date/time expressions
 * Pure function - no side effects, fully testable
 */
export function parseDateTime(text, referenceDate = new Date()) {
  const lowerText = text.toLowerCase();

  // Handle "tomorrow"
  if (lowerText.includes('tomorrow')) {
    const tomorrow = new Date(referenceDate);
    tomorrow.setUTCDate(referenceDate.getUTCDate() + 1);

    const hour = extractHour(lowerText);
    if (hour !== null) {
      tomorrow.setUTCHours(hour, 0, 0, 0);
    } else {
      tomorrow.setUTCHours(9, 0, 0, 0); // Default to 9am
    }

    return tomorrow.toISOString();
  }

  // Handle "today"
  if (lowerText.includes('today')) {
    const today = new Date(referenceDate);

    const hour = extractHour(lowerText);
    if (hour !== null) {
      today.setUTCHours(hour, 0, 0, 0);
    } else {
      today.setUTCHours(9, 0, 0, 0); // Default to 9am
    }

    return today.toISOString();
  }

  // Handle "next week"
  if (lowerText.includes('next week')) {
    const nextWeek = new Date(referenceDate);
    nextWeek.setUTCDate(referenceDate.getUTCDate() + 7);
    nextWeek.setUTCHours(9, 0, 0, 0);
    return nextWeek.toISOString();
  }

  // Extract specific time if present
  const hour = extractHour(lowerText);
  if (hour !== null) {
    const result = new Date(referenceDate);
    result.setUTCHours(hour, 0, 0, 0);

    // If the time has passed today, schedule for tomorrow
    if (result < referenceDate) {
      result.setUTCDate(referenceDate.getUTCDate() + 1);
    }

    return result.toISOString();
  }

  // Default: 1 hour from now
  const defaultTime = new Date(referenceDate.getTime() + 60 * 60 * 1000);
  return defaultTime.toISOString();
}

/**
 * Extract hour from time expressions like "2pm", "14:00", "3:30pm"
 * Pure function - no side effects
 */
export function extractHour(text) {
  // Match patterns like "2pm", "2 pm", "14:00", "2:30pm"
  const timePattern = /(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i;
  const match = text.match(timePattern);

  if (!match) return null;

  let hour = parseInt(match[1]);
  const minutes = match[2] ? parseInt(match[2]) : 0;
  const meridiem = match[3] ? match[3].toLowerCase() : null;

  // Convert to 24-hour format
  if (meridiem === 'pm' && hour !== 12) {
    hour += 12;
  } else if (meridiem === 'am' && hour === 12) {
    hour = 0;
  }

  return hour;
}

/**
 * Extract title from schedule command
 * Pure function - no side effects
 */
export function extractTitle(text) {
  // Remove common scheduling words to get the title
  let title = text
    .replace(/schedule|appointment|meeting|tomorrow|today|next week|at|on/gi, '')
    .replace(/\d{1,2}(?::\d{2})?\s*(?:am|pm)?/gi, '')
    .trim();

  if (!title || title.length < 3) {
    title = 'Meeting';
  }

  return title;
}

/**
 * Extract reminder text from remind command
 * Pure function - no side effects
 */
export function extractReminderText(text) {
  // Remove "remind me to" or "remind me" and time expressions
  let reminder = text
    .replace(/remind\s+me\s+to\s+/gi, '')
    .replace(/remind\s+me\s+/gi, '')
    .replace(/tomorrow|today|next week|at|on/gi, '')
    .replace(/\d{1,2}(?::\d{2})?\s*(?:am|pm)?/gi, '')
    .trim();

  if (!reminder || reminder.length < 3) {
    reminder = 'Reminder';
  }

  return reminder;
}

/**
 * Detect command type from message content
 * Pure function - returns command type or null
 */
export function detectCommand(content) {
  const text = content.toLowerCase().trim();

  // Calendar view commands (check first to avoid false positives with "schedule")
  if (text.includes('calendar') ||
      text.includes('show my schedule') ||
      text.includes('my schedule') ||
      (text.includes("what's on") && text.includes('schedule'))) {
    return 'calendar';
  }

  // Schedule/appointment commands
  if (text.includes('schedule') || text.includes('appointment') || text.includes('meeting')) {
    return 'schedule';
  }

  // Reminder commands
  if (text.includes('remind')) {
    return 'reminder';
  }

  // Help/unknown
  return 'help';
}

/**
 * Format user data from database row
 * Pure function - no side effects
 */
export function formatUser(row) {
  return {
    id: row.id,
    name: row.name,
    email: row.email,
    phone: row.phone,
    is_admin: row.is_admin === 1 || row.is_admin === true,
  };
}

/**
 * Build schedule confirmation response
 * Pure function - no side effects
 */
export function buildScheduleResponse(title, startTime) {
  const date = new Date(startTime);
  return `Scheduled: ${title} on ${date.toLocaleDateString()} at ${date.toLocaleTimeString()}`;
}

/**
 * Build reminder confirmation response
 * Pure function - no side effects
 */
export function buildReminderResponse(reminderText, dueTime) {
  const date = new Date(dueTime);
  return `Reminder set: ${reminderText} at ${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

/**
 * Build calendar view response
 * Pure function - no side effects
 */
export function buildCalendarResponse(appointments) {
  if (appointments.length === 0) {
    return "You have no appointments scheduled for today.";
  }

  let response = "Today's schedule:\n";
  for (const appt of appointments) {
    const time = new Date(appt.start_time).toLocaleTimeString([], {
      hour: 'numeric',
      minute: '2-digit'
    });
    response += `- ${time}: ${appt.title}\n`;
  }

  return response;
}

/**
 * Build help message
 * Pure function - no side effects
 */
export function buildHelpMessage() {
  return "I can help with:\n" +
         "- Schedule: 'schedule meeting tomorrow at 2pm'\n" +
         "- Reminders: 'remind me to call John at 3pm'\n" +
         "- Calendar: 'show my calendar' or 'what's on my schedule today'";
}

/**
 * Route message to appropriate handler
 * Pure function - returns routing decision, doesn't execute anything
 */
export function routeMessage(user, content) {
  // Admin users get routed to Claude Code
  if (user.is_admin) {
    return {
      type: 'claude_code',
      userId: user.id,
      content,
    };
  }

  // Regular users get command routing
  const commandType = detectCommand(content);
  return {
    type: 'command',
    userId: user.id,
    commandType,
    content,
  };
}

// =============================================================================
// DATABASE INTERFACE LAYER - Minimal layer for mocking
// =============================================================================

let dbClient = null;

function getDbClient(env) {
  if (!dbClient) {
    dbClient = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN,
    });
  }
  return dbClient;
}

/**
 * Database interface - can be mocked in tests
 */
export const db = {
  /**
   * Find user by phone or email
   */
  async findUser(identifier, env) {
    try {
      const client = getDbClient(env);

      // Check if identifier is phone (starts with +) or email (contains @)
      const isPhone = identifier.startsWith('+');

      const result = await client.execute({
        sql: isPhone
          ? 'SELECT * FROM users WHERE phone = ?'
          : 'SELECT * FROM users WHERE email = ?',
        args: [identifier],
      });

      if (result.rows.length > 0) {
        return formatUser(result.rows[0]);
      }

      // Check if this is the admin user from config
      const adminPhone = env.ADMIN_PHONE;
      const adminEmail = env.ADMIN_EMAIL;

      if ((isPhone && identifier === adminPhone) ||
          (!isPhone && identifier === adminEmail)) {
        return {
          id: 'admin',
          name: env.ADMIN_NAME || 'Admin',
          email: env.ADMIN_EMAIL,
          phone: env.ADMIN_PHONE,
          is_admin: true,
        };
      }

      return null;
    } catch (error) {
      console.error('Error finding user:', error);
      return null;
    }
  },

  /**
   * Log message to database
   */
  async logMessage(userId, channel, direction, content, env) {
    try {
      const client = getDbClient(env);

      await client.execute({
        sql: `
          INSERT INTO messages (id, user_id, channel, direction, content, created_at)
          VALUES (?, ?, ?, ?, ?, ?)
        `,
        args: [
          crypto.randomUUID(),
          userId,
          channel,
          direction,
          content,
          new Date().toISOString(),
        ],
      });
    } catch (error) {
      // If messages table doesn't exist, just log to console
      console.log(`[${direction.toUpperCase()}] [${channel}] ${userId}: ${content}`);
    }
  },

  /**
   * Create appointment in database
   */
  async createAppointment(userId, title, startTime, endTime, env) {
    const client = getDbClient(env);

    const id = crypto.randomUUID();
    await client.execute({
      sql: `
        INSERT INTO events (
          id, user_id, title, start_time, end_time, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
      `,
      args: [
        id,
        userId,
        title,
        startTime,
        endTime,
        new Date().toISOString(),
      ],
    });

    return id;
  },

  /**
   * Create reminder in database
   */
  async createReminder(userId, reminderText, dueTime, env) {
    const client = getDbClient(env);

    const id = crypto.randomUUID();
    await client.execute({
      sql: `
        INSERT INTO reminders (
          id, user_id, text, due_time, method, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `,
      args: [
        id,
        userId,
        reminderText,
        dueTime,
        'sms', // Default to SMS
        'pending',
        new Date().toISOString(),
      ],
    });

    return id;
  },

  /**
   * Get appointments for a specific date
   */
  async getAppointments(userId, date, env) {
    const client = getDbClient(env);

    const result = await client.execute({
      sql: `
        SELECT * FROM events
        WHERE user_id = ?
          AND date(start_time) = ?
        ORDER BY start_time
      `,
      args: [userId, date],
    });

    return result.rows;
  },
};

// =============================================================================
// COMMAND HANDLERS - Orchestrate pure functions + database calls
// =============================================================================

/**
 * Handle schedule command
 */
async function handleScheduleCommand(userId, content, env) {
  try {
    // Pure functions - easy to test
    const title = extractTitle(content);
    const startTime = parseDateTime(content);
    const endTime = new Date(new Date(startTime).getTime() + 60 * 60 * 1000).toISOString();

    // Database call - can be mocked
    await db.createAppointment(userId, title, startTime, endTime, env);

    // Pure function - easy to test
    return buildScheduleResponse(title, startTime);

  } catch (error) {
    console.error('Error creating appointment:', error);
    return 'Sorry, I had trouble scheduling that. Please try again.';
  }
}

/**
 * Handle reminder command
 */
async function handleReminderCommand(userId, content, env) {
  try {
    // Pure functions - easy to test
    const reminderText = extractReminderText(content);
    const dueTime = parseDateTime(content);

    // Database call - can be mocked
    await db.createReminder(userId, reminderText, dueTime, env);

    // Pure function - easy to test
    return buildReminderResponse(reminderText, dueTime);

  } catch (error) {
    console.error('Error creating reminder:', error);
    return 'Sorry, I had trouble setting that reminder. Please try again.';
  }
}

/**
 * Handle calendar view command
 */
async function handleCalendarCommand(userId, content, env) {
  try {
    const today = new Date().toISOString().split('T')[0];

    // Database call - can be mocked
    const appointments = await db.getAppointments(userId, today, env);

    // Pure function - easy to test
    return buildCalendarResponse(appointments);

  } catch (error) {
    console.error('Error fetching calendar:', error);
    return 'Sorry, I had trouble fetching your calendar. Please try again.';
  }
}

/**
 * Execute command based on routing decision
 */
async function executeCommand(routing, env) {
  const { commandType, userId, content } = routing;

  switch (commandType) {
    case 'schedule':
      return await handleScheduleCommand(userId, content, env);
    case 'reminder':
      return await handleReminderCommand(userId, content, env);
    case 'calendar':
      return await handleCalendarCommand(userId, content, env);
    case 'help':
    default:
      return buildHelpMessage();
  }
}

// =============================================================================
// CLAUDE CODE INTEGRATION
// =============================================================================

/**
 * Route admin messages to Claude Code
 */
async function routeToClaudeCode(userId, message, channel, env) {
  try {
    // Try to connect to local Claude Code instance
    const response = await fetch('http://localhost:8080/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        user_id: userId,
        channel,
        context: 'boss-ai-routing',
      }),
    });

    if (response.ok) {
      const data = await response.json();
      return data.response || "Claude Code processed your message.";
    }

    // If Claude Code is not available, return a helpful message
    return "Claude Code is not currently available. Your message has been logged.";

  } catch (error) {
    console.error('Claude Code connection error:', error);
    return "I'm having trouble connecting to Claude Code right now. Please try again later.";
  }
}

// =============================================================================
// MAIN MESSAGE HANDLER - Orchestrates everything
// =============================================================================

/**
 * Main message handler - routes ALL incoming messages
 * This is the only function that should be called from webhooks
 */
export async function handleMessage(channel, from, content, env) {
  // Find user (database call)
  const user = await db.findUser(from, env);

  if (!user) {
    return { error: 'Unknown user. Please sign up at xswarm.ai' };
  }

  // Log incoming message
  await db.logMessage(user.id, channel, 'in', content, env);

  // Route message (pure function - returns decision)
  const routing = routeMessage(user, content);

  // Execute based on routing decision
  let response;
  if (routing.type === 'claude_code') {
    response = await routeToClaudeCode(routing.userId, routing.content, channel, env);
  } else {
    response = await executeCommand(routing, env);
  }

  // Log outgoing message
  await db.logMessage(user.id, channel, 'out', response, env);

  return { message: response };
}

// =============================================================================
// WEBHOOK HANDLERS
// =============================================================================

/**
 * Handle Twilio SMS webhook
 */
async function handleSMS(formData, env) {
  const from = formData.get('From');
  const body = formData.get('Body');

  const result = await handleMessage('sms', from, body, env);

  // Return TwiML response
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Message>${result.message || result.error}</Message>
    </Response>`,
    { headers: { 'Content-Type': 'application/xml' } }
  );
}

/**
 * Handle SendGrid email webhook
 */
async function handleEmail(body, env) {
  const from = body.from || body.email;
  const text = body.text || body.body || '';

  const result = await handleMessage('email', from, text, env);

  // Send email response via SendGrid
  if (env.SENDGRID_API_KEY) {
    await sendEmail(from, 'Re: Your message', result.message || result.error, env);
  }

  return new Response('OK');
}

/**
 * Handle API message (CLI or direct API calls)
 */
async function handleAPI(body, env) {
  const result = await handleMessage(
    body.channel || 'api',
    body.from,
    body.content || body.message,
    env
  );

  return Response.json(result);
}

/**
 * Send email via SendGrid
 */
async function sendEmail(to, subject, text, env) {
  try {
    const response = await fetch('https://api.sendgrid.com/v3/mail/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.SENDGRID_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        personalizations: [{ to: [{ email: to }] }],
        from: { email: env.ADMIN_EMAIL || 'boss@xswarm.ai' },
        subject,
        content: [{ type: 'text/plain', value: text }],
      }),
    });

    if (!response.ok) {
      console.error('SendGrid error:', await response.text());
    }
  } catch (error) {
    console.error('Error sending email:', error);
  }
}

// =============================================================================
// MAIN ROUTER
// =============================================================================

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    // Health check
    if (path === '/health' || path === '/') {
      return Response.json({
        status: 'ok',
        service: 'boss-ai-simple',
        timestamp: new Date().toISOString(),
      });
    }

    try {
      // SMS webhook
      if (path === '/sms' && request.method === 'POST') {
        const formData = await request.formData();
        return await handleSMS(formData, env);
      }

      // Email webhook
      if (path === '/email' && request.method === 'POST') {
        const body = await request.json();
        return await handleEmail(body, env);
      }

      // API endpoint
      if (path === '/api/message' && request.method === 'POST') {
        const body = await request.json();
        return await handleAPI(body, env);
      }

      // Not found
      return Response.json({ error: 'Not found', path }, { status: 404 });

    } catch (error) {
      console.error('Error handling request:', error);
      return Response.json({
        error: 'Internal server error',
        message: error.message,
      }, { status: 500 });
    }
  },
};
