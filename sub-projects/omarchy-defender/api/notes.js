/**
 * Notes API - Fetch Approved Donor Notes
 * Returns notes for sticky note display
 * Cloudflare Pages Function
 */

import { createClient } from '@libsql/client/web';

export async function onRequestGet(context) {
  const { env } = context;

  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Content-Type': 'application/json',
    'Cache-Control': 'public, max-age=300' // Cache for 5 minutes
  };

  try {
    // Connect to Turso database
    const db = createClient({
      url: env.TURSO_DATABASE_URL,
      authToken: env.TURSO_AUTH_TOKEN
    });

    // Fetch approved notes with donation amounts
    const result = await db.execute({
      sql: `SELECT
              n.id,
              n.content,
              n.created_at,
              d.amount_cents
            FROM notes n
            JOIN donations d ON n.donation_id = d.id
            WHERE n.status = 'approved'
            ORDER BY n.created_at DESC
            LIMIT 50`,
      args: []
    });

    // Format notes for display
    const notes = result.rows.map(row => ({
      id: row.id,
      content: row.content,
      amount: (row.amount_cents / 100).toFixed(0),
      date: row.created_at,
      // Random rotation for sticky note effect
      rotation: (Math.random() * 10 - 5).toFixed(1)
    }));

    return new Response(JSON.stringify({
      notes,
      count: notes.length
    }), { headers });

  } catch (error) {
    console.error('Notes fetch error:', error);

    // Return empty array on error (graceful degradation)
    return new Response(JSON.stringify({
      notes: [],
      count: 0,
      error: 'Unable to load notes'
    }), { headers });
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}
