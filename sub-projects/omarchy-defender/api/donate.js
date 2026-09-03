/**
 * Donation API - Create Stripe Checkout Session
 * Cloudflare Pages Function
 */

export async function onRequestPost(context) {
  const { request, env } = context;

  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json'
  };

  try {
    const body = await request.json();
    const { amount, email, note, displayNote, receiveUpdates } = body;

    // Validate amount
    const cents = Math.round(parseFloat(amount) * 100);
    if (isNaN(cents) || cents < 100) {
      return new Response(JSON.stringify({ error: 'Minimum donation is $1' }), {
        status: 400,
        headers
      });
    }

    // Create Stripe Checkout Session
    const stripe = new Stripe(env.STRIPE_SECRET_KEY);

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [{
        price_data: {
          currency: 'usd',
          product_data: {
            name: 'Omarchy Defender Donation',
            description: 'Support the development of Omarchy Defender'
          },
          unit_amount: cents
        },
        quantity: 1
      }],
      mode: 'payment',
      success_url: `${new URL(request.url).origin}/?donated=true`,
      cancel_url: `${new URL(request.url).origin}/?cancelled=true`,
      customer_email: email || undefined,
      metadata: {
        note: note?.substring(0, 200) || '',
        displayNote: displayNote ? 'true' : 'false',
        receiveUpdates: receiveUpdates ? 'true' : 'false',
        email: email || ''
      }
    });

    return new Response(JSON.stringify({
      sessionId: session.id,
      url: session.url
    }), { headers });

  } catch (error) {
    console.error('Donation error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to create checkout session'
    }), {
      status: 500,
      headers
    });
  }
}

export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    }
  });
}

// Minimal Stripe API client for Cloudflare Workers
class Stripe {
  constructor(secretKey) {
    this.secretKey = secretKey;
    this.baseUrl = 'https://api.stripe.com/v1';

    // Define checkout API
    this.checkout = {
      sessions: {
        create: async (params) => {
          const formData = this.toFormData(params);

          const response = await fetch(`${this.baseUrl}/checkout/sessions`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${this.secretKey}`,
              'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Stripe API error');
          }

          return response.json();
        }
      }
    };
  }

  toFormData(obj, prefix = '') {
    const parts = [];

    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}[${key}]` : key;

      if (value === undefined || value === null) continue;

      if (Array.isArray(value)) {
        value.forEach((item, i) => {
          if (typeof item === 'object') {
            parts.push(this.toFormData(item, `${fullKey}[${i}]`));
          } else {
            parts.push(`${fullKey}[${i}]=${encodeURIComponent(item)}`);
          }
        });
      } else if (typeof value === 'object') {
        parts.push(this.toFormData(value, fullKey));
      } else {
        parts.push(`${fullKey}=${encodeURIComponent(value)}`);
      }
    }

    return parts.filter(Boolean).join('&');
  }
}
