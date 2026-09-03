/**
 * Stripe Webhook Handler
 * Handles checkout.session.completed events
 * Cloudflare Pages Function
 */

import { createClient } from '@libsql/client/web';

export async function onRequestPost(context) {
  const { request, env } = context;

  const headers = {
    'Content-Type': 'application/json'
  };

  try {
    const signature = request.headers.get('stripe-signature');
    const body = await request.text();

    // Verify webhook signature
    const event = await verifyStripeWebhook(
      body,
      signature,
      env.STRIPE_WEBHOOK_SECRET
    );

    if (!event) {
      return new Response(JSON.stringify({ error: 'Invalid signature' }), {
        status: 400,
        headers
      });
    }

    // Handle the event
    if (event.type === 'checkout.session.completed') {
      const session = event.data.object;
      await handleCompletedDonation(session, env);
    }

    return new Response(JSON.stringify({ received: true }), { headers });

  } catch (error) {
    console.error('Webhook error:', error);
    return new Response(JSON.stringify({ error: 'Webhook handler failed' }), {
      status: 500,
      headers
    });
  }
}

async function handleCompletedDonation(session, env) {
  const { amount_total, metadata, customer_email } = session;

  // Connect to Turso database
  const db = createClient({
    url: env.TURSO_DATABASE_URL,
    authToken: env.TURSO_AUTH_TOKEN
  });

  // Insert donation record
  const donationResult = await db.execute({
    sql: `INSERT INTO donations (amount_cents, email, note, display_note, receive_updates, stripe_session_id)
          VALUES (?, ?, ?, ?, ?, ?)
          RETURNING id`,
    args: [
      amount_total,
      metadata.email || customer_email || null,
      metadata.note || null,
      metadata.displayNote === 'true',
      metadata.receiveUpdates === 'true',
      session.id
    ]
  });

  const donationId = donationResult.rows[0]?.id;

  // If there's a note to display, add it to notes table for moderation
  if (metadata.note && metadata.displayNote === 'true' && donationId) {
    await db.execute({
      sql: `INSERT INTO notes (donation_id, content, status)
            VALUES (?, ?, 'pending')`,
      args: [donationId, metadata.note.substring(0, 200)]
    });
  }

  // If user wants updates and provided email, add to mailing list
  if (metadata.email && metadata.receiveUpdates === 'true') {
    await db.execute({
      sql: `INSERT OR IGNORE INTO donor_emails (email, subscribed)
            VALUES (?, true)`,
      args: [metadata.email]
    });
  }
}

// Verify Stripe webhook signature
async function verifyStripeWebhook(payload, signature, secret) {
  if (!signature || !secret) {
    console.warn('Missing signature or secret');
    return null;
  }

  const parts = signature.split(',').reduce((acc, part) => {
    const [key, value] = part.split('=');
    acc[key] = value;
    return acc;
  }, {});

  const timestamp = parts['t'];
  const sig = parts['v1'];

  if (!timestamp || !sig) {
    return null;
  }

  // Check timestamp is within tolerance (5 minutes)
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - parseInt(timestamp)) > 300) {
    console.warn('Webhook timestamp too old');
    return null;
  }

  // Compute expected signature
  const signedPayload = `${timestamp}.${payload}`;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signatureBytes = await crypto.subtle.sign(
    'HMAC',
    key,
    encoder.encode(signedPayload)
  );

  const expectedSig = Array.from(new Uint8Array(signatureBytes))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Compare signatures (timing-safe comparison)
  if (expectedSig.length !== sig.length) {
    return null;
  }

  let match = true;
  for (let i = 0; i < expectedSig.length; i++) {
    if (expectedSig[i] !== sig[i]) {
      match = false;
    }
  }

  if (!match) {
    return null;
  }

  return JSON.parse(payload);
}
