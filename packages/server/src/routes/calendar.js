/**
 * Calendar API Routes
 *
 * Handles:
 * - Appointment creation, modification, deletion
 * - Reminder management
 * - Calendar integration (Google Calendar, Outlook)
 * - Conflict detection and resolution
 * - Natural language processing for scheduling
 */

import { createClient } from '@libsql/client';

/**
 * Create Turso client (singleton pattern)
 */
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
 * Create a new appointment
 * POST /api/calendar/appointments
 */
export async function createAppointment(request, env) {
  try {
    const body = await request.json();
    const {
      user_id,
      title,
      description,
      start_time,
      end_time,
      timezone = 'UTC',
      location,
      recurrence_rule,
      participants = [],
    } = body;

    // Validate required fields
    if (!user_id || !title || !start_time || !end_time) {
      return new Response(
        JSON.stringify({
          error: 'Missing required fields: user_id, title, start_time, end_time',
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const db = getDbClient(env);
    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    // Check for conflicts
    const conflicts = await db.execute({
      sql: `
        SELECT * FROM appointments
        WHERE user_id = ?
          AND status = 'scheduled'
          AND datetime(start_time) < datetime(?)
          AND datetime(end_time) > datetime(?)
      `,
      args: [user_id, end_time, start_time],
    });

    if (conflicts.rows.length > 0) {
      return new Response(
        JSON.stringify({
          error: 'Scheduling conflict detected',
          conflicts: conflicts.rows.map(formatAppointment),
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Create appointment
    const result = await db.execute({
      sql: `
        INSERT INTO appointments (
          id, user_id, title, description, start_time, end_time,
          timezone, location, recurrence_rule, participants,
          status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
      args: [
        id,
        user_id,
        title,
        description || null,
        start_time,
        end_time,
        timezone,
        location || null,
        recurrence_rule || null,
        JSON.stringify(participants),
        'scheduled',
        now,
      ],
    });

    return new Response(
      JSON.stringify({
        success: true,
        appointment: formatAppointment(result.rows[0]),
      }),
      { status: 201, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error creating appointment:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to create appointment' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Get appointments for a user
 * GET /api/calendar/appointments?user_id=xxx&start=xxx&end=xxx
 */
export async function getAppointments(request, env) {
  try {
    const url = new URL(request.url);
    const user_id = url.searchParams.get('user_id');
    const start = url.searchParams.get('start');
    const end = url.searchParams.get('end');
    const status = url.searchParams.get('status') || 'scheduled';

    if (!user_id) {
      return new Response(
        JSON.stringify({ error: 'Missing user_id parameter' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const db = getDbClient(env);

    let sql = 'SELECT * FROM appointments WHERE user_id = ? AND status = ?';
    let args = [user_id, status];

    if (start && end) {
      sql += ' AND datetime(start_time) >= datetime(?) AND datetime(end_time) <= datetime(?)';
      args.push(start, end);
    } else if (start) {
      sql += ' AND datetime(start_time) >= datetime(?)';
      args.push(start);
    } else if (end) {
      sql += ' AND datetime(end_time) <= datetime(?)';
      args.push(end);
    }

    sql += ' ORDER BY start_time ASC';

    const result = await db.execute({ sql, args });

    return new Response(
      JSON.stringify({
        appointments: result.rows.map(formatAppointment),
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error getting appointments:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to get appointments' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Get today's schedule
 * GET /api/calendar/today?user_id=xxx
 */
export async function getTodaySchedule(request, env) {
  try {
    const url = new URL(request.url);
    const user_id = url.searchParams.get('user_id');

    if (!user_id) {
      return new Response(
        JSON.stringify({ error: 'Missing user_id parameter' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM todays_schedule WHERE user_id = ?',
      args: [user_id],
    });

    return new Response(
      JSON.stringify({
        schedule: result.rows.map(formatAppointment),
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error getting today schedule:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to get today schedule' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Get this week's schedule
 * GET /api/calendar/week?user_id=xxx
 */
export async function getWeekSchedule(request, env) {
  try {
    const url = new URL(request.url);
    const user_id = url.searchParams.get('user_id');

    if (!user_id) {
      return new Response(
        JSON.stringify({ error: 'Missing user_id parameter' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'SELECT * FROM weekly_schedule WHERE user_id = ?',
      args: [user_id],
    });

    return new Response(
      JSON.stringify({
        schedule: result.rows.map(formatAppointment),
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error getting week schedule:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to get week schedule' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Update an appointment
 * PUT /api/calendar/appointments/:id
 */
export async function updateAppointment(request, env, appointmentId) {
  try {
    const body = await request.json();
    const {
      title,
      description,
      start_time,
      end_time,
      timezone,
      location,
      recurrence_rule,
      participants,
      status,
    } = body;

    const db = getDbClient(env);
    const now = new Date().toISOString();

    // Build dynamic update query
    const updates = [];
    const args = [];

    if (title !== undefined) {
      updates.push('title = ?');
      args.push(title);
    }
    if (description !== undefined) {
      updates.push('description = ?');
      args.push(description);
    }
    if (start_time !== undefined) {
      updates.push('start_time = ?');
      args.push(start_time);
    }
    if (end_time !== undefined) {
      updates.push('end_time = ?');
      args.push(end_time);
    }
    if (timezone !== undefined) {
      updates.push('timezone = ?');
      args.push(timezone);
    }
    if (location !== undefined) {
      updates.push('location = ?');
      args.push(location);
    }
    if (recurrence_rule !== undefined) {
      updates.push('recurrence_rule = ?');
      args.push(recurrence_rule);
    }
    if (participants !== undefined) {
      updates.push('participants = ?');
      args.push(JSON.stringify(participants));
    }
    if (status !== undefined) {
      updates.push('status = ?');
      args.push(status);
    }

    if (updates.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No fields to update' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    updates.push('updated_at = ?');
    args.push(now);
    args.push(appointmentId);

    const sql = `UPDATE appointments SET ${updates.join(', ')} WHERE id = ? RETURNING *`;

    const result = await db.execute({ sql, args });

    if (result.rows.length === 0) {
      return new Response(
        JSON.stringify({ error: 'Appointment not found' }),
        { status: 404, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({
        success: true,
        appointment: formatAppointment(result.rows[0]),
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error updating appointment:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to update appointment' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Delete an appointment
 * DELETE /api/calendar/appointments/:id
 */
export async function deleteAppointment(request, env, appointmentId) {
  try {
    const db = getDbClient(env);

    const result = await db.execute({
      sql: 'DELETE FROM appointments WHERE id = ? RETURNING *',
      args: [appointmentId],
    });

    if (result.rows.length === 0) {
      return new Response(
        JSON.stringify({ error: 'Appointment not found' }),
        { status: 404, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({ success: true }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error deleting appointment:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to delete appointment' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Create a reminder
 * POST /api/calendar/reminders
 */
export async function createReminder(request, env) {
  try {
    const body = await request.json();
    const {
      user_id,
      title,
      description,
      due_time,
      priority = 3,
      recurrence_rule,
      notification_channels = ['sms', 'email'],
    } = body;

    if (!user_id || !title || !due_time) {
      return new Response(
        JSON.stringify({
          error: 'Missing required fields: user_id, title, due_time',
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const db = getDbClient(env);
    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    const result = await db.execute({
      sql: `
        INSERT INTO reminders (
          id, user_id, title, description, due_time, priority,
          recurrence_rule, notification_channels, completed, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
      args: [
        id,
        user_id,
        title,
        description || null,
        due_time,
        priority,
        recurrence_rule || null,
        JSON.stringify(notification_channels),
        false,
        now,
      ],
    });

    return new Response(
      JSON.stringify({
        success: true,
        reminder: formatReminder(result.rows[0]),
      }),
      { status: 201, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error creating reminder:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to create reminder' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Get reminders for a user
 * GET /api/calendar/reminders?user_id=xxx&completed=false
 */
export async function getReminders(request, env) {
  try {
    const url = new URL(request.url);
    const user_id = url.searchParams.get('user_id');
    const completed = url.searchParams.get('completed') === 'true';

    if (!user_id) {
      return new Response(
        JSON.stringify({ error: 'Missing user_id parameter' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const db = getDbClient(env);

    const result = await db.execute({
      sql: `
        SELECT * FROM reminders
        WHERE user_id = ? AND completed = ?
        ORDER BY due_time ASC
      `,
      args: [user_id, completed],
    });

    return new Response(
      JSON.stringify({
        reminders: result.rows.map(formatReminder),
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error getting reminders:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to get reminders' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Update a reminder
 * PUT /api/calendar/reminders/:id
 */
export async function updateReminder(request, env, reminderId) {
  try {
    const body = await request.json();
    const { completed, snoozed_until } = body;

    const db = getDbClient(env);
    const now = new Date().toISOString();

    const updates = [];
    const args = [];

    if (completed !== undefined) {
      updates.push('completed = ?');
      args.push(completed);
    }
    if (snoozed_until !== undefined) {
      updates.push('snoozed_until = ?');
      args.push(snoozed_until);
    }

    if (updates.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No fields to update' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    updates.push('updated_at = ?');
    args.push(now);
    args.push(reminderId);

    const sql = `UPDATE reminders SET ${updates.join(', ')} WHERE id = ? RETURNING *`;

    const result = await db.execute({ sql, args });

    if (result.rows.length === 0) {
      return new Response(
        JSON.stringify({ error: 'Reminder not found' }),
        { status: 404, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({
        success: true,
        reminder: formatReminder(result.rows[0]),
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error updating reminder:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to update reminder' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Natural language scheduling endpoint
 * POST /api/calendar/schedule
 */
export async function scheduleNaturalLanguage(request, env) {
  try {
    const body = await request.json();
    const { user_id, text } = body;

    if (!user_id || !text) {
      return new Response(
        JSON.stringify({ error: 'Missing user_id or text' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // TODO: Call Rust scheduler module for natural language parsing
    // For now, return a placeholder response
    return new Response(
      JSON.stringify({
        success: true,
        message: 'Natural language scheduling will be implemented via Rust module',
        parsed: {
          text,
          user_id,
        },
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error in natural language scheduling:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to process scheduling request' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

/**
 * Format appointment row
 */
function formatAppointment(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    title: row.title,
    description: row.description,
    start_time: row.start_time,
    end_time: row.end_time,
    timezone: row.timezone,
    location: row.location,
    recurrence_rule: row.recurrence_rule,
    participants: row.participants ? JSON.parse(row.participants) : [],
    status: row.status,
    external_calendar_id: row.external_calendar_id,
    external_event_id: row.external_event_id,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

/**
 * Format reminder row
 */
function formatReminder(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    title: row.title,
    description: row.description,
    due_time: row.due_time,
    completed: row.completed === 1 || row.completed === true,
    priority: row.priority,
    recurrence_rule: row.recurrence_rule,
    snoozed_until: row.snoozed_until,
    notification_channels: row.notification_channels
      ? JSON.parse(row.notification_channels)
      : [],
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}
