/**
 * Dashboard Subscription Upgrade/Downgrade Endpoints
 *
 * POST /api/dashboard/upgrade - Initiate subscription upgrade (Stripe checkout)
 * POST /api/dashboard/downgrade - Downgrade subscription
 * POST /api/dashboard/cancel - Cancel subscription
 *
 * Requires authentication.
 */

import Stripe from 'stripe';
import { getUserById } from '../../lib/users.js';

export async function handleUpgrade(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const { target_tier } = body;

    if (!target_tier) {
      return new Response(JSON.stringify({ error: 'target_tier is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const stripe = new Stripe(env.STRIPE_SECRET_KEY);

    // Get or create Stripe customer
    let customerId = user.stripe_customer_id;

    if (!customerId) {
      const customer = await stripe.customers.create({
        email: user.email,
        name: user.name,
        metadata: {
          user_id: user.id,
          username: user.username,
        },
      });
      customerId = customer.id;

      // Update user with customer ID
      const { updateUserStripeInfo } = await import('../../lib/users.js');
      await updateUserStripeInfo(user.id, customerId, null, env);
    }

    // Map tier to Stripe price ID
    const priceIds = {
      ai_secretary: env.STRIPE_PRICE_AI_SECRETARY,
      ai_project_manager: env.STRIPE_PRICE_AI_PROJECT_MANAGER,
    };

    const priceId = priceIds[target_tier];

    if (!priceId) {
      return new Response(JSON.stringify({ error: 'Invalid tier or tier not available for self-service upgrade' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Create Stripe Checkout session
    const session = await stripe.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      success_url: `${env.BASE_URL}/dashboard.html?upgrade=success`,
      cancel_url: `${env.BASE_URL}/dashboard.html?upgrade=cancelled`,
      metadata: {
        user_id: user.id,
        target_tier,
      },
    });

    return new Response(JSON.stringify({
      checkout_url: session.url,
      session_id: session.id,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error creating upgrade session:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function handleDowngrade(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await request.json();
    const { target_tier } = body;

    if (!target_tier) {
      return new Response(JSON.stringify({ error: 'target_tier is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const stripe = new Stripe(env.STRIPE_SECRET_KEY);

    if (!user.stripe_subscription_id) {
      return new Response(JSON.stringify({ error: 'No active subscription found' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Map tier to Stripe price ID
    const priceIds = {
      ai_buddy: null, // Free tier - cancel subscription
      ai_secretary: env.STRIPE_PRICE_AI_SECRETARY,
    };

    const priceId = priceIds[target_tier];

    if (target_tier === 'ai_buddy') {
      // Downgrade to free tier - cancel at period end
      await stripe.subscriptions.update(user.stripe_subscription_id, {
        cancel_at_period_end: true,
      });

      return new Response(JSON.stringify({
        message: 'Subscription will be cancelled at the end of the current billing period',
        downgrade_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(), // approximate
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Change subscription plan
    const subscription = await stripe.subscriptions.retrieve(user.stripe_subscription_id);

    await stripe.subscriptions.update(user.stripe_subscription_id, {
      items: [{
        id: subscription.items.data[0].id,
        price: priceId,
      }],
      proration_behavior: 'create_prorations',
    });

    return new Response(JSON.stringify({
      message: 'Subscription updated successfully',
      new_tier: target_tier,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error downgrading subscription:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function handleCancel(request, env) {
  try {
    const user = request.user;

    if (!user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (!user.stripe_subscription_id) {
      return new Response(JSON.stringify({ error: 'No active subscription found' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const stripe = new Stripe(env.STRIPE_SECRET_KEY);

    // Cancel at period end (don't cancel immediately)
    await stripe.subscriptions.update(user.stripe_subscription_id, {
      cancel_at_period_end: true,
    });

    return new Response(JSON.stringify({
      message: 'Subscription will be cancelled at the end of the current billing period',
      status: 'pending_cancellation',
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error cancelling subscription:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
