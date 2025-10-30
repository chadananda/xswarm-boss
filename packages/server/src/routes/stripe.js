/**
 * Stripe Webhook Handler
 *
 * Handles subscription lifecycle events:
 * - customer.subscription.created (provision phone number)
 * - customer.subscription.deleted (release phone number)
 * - invoice.payment_failed (notify user)
 * - invoice.payment_succeeded (reset usage counters)
 */

import Stripe from 'stripe';

/**
 * Handle Stripe webhook events
 *
 * @param {Request} request - Incoming webhook request
 * @param {Object} env - Environment variables (secrets)
 * @returns {Response} JSON response
 */
export async function handleStripeWebhook(request, env) {
  try {
    const stripe = new Stripe(env.STRIPE_SECRET_KEY);

    // Get raw body for signature verification
    const body = await request.text();
    const signature = request.headers.get('stripe-signature');

    // Verify webhook signature
    let event;
    try {
      event = stripe.webhooks.constructEvent(
        body,
        signature,
        env.STRIPE_WEBHOOK_SECRET
      );
    } catch (err) {
      console.error('Invalid Stripe signature:', err.message);
      return new Response(JSON.stringify({ error: 'Invalid signature' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    console.log(`Stripe webhook: ${event.type} (${event.id})`);

    // Handle different event types
    switch (event.type) {
      case 'customer.subscription.created':
        await handleSubscriptionCreated(event.data.object, env);
        break;

      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object, env);
        break;

      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(event.data.object, env);
        break;

      case 'invoice.payment_succeeded':
        await handlePaymentSucceeded(event.data.object, env);
        break;

      case 'invoice.payment_failed':
        await handlePaymentFailed(event.data.object, env);
        break;

      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    return new Response(JSON.stringify({ received: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (error) {
    console.error('Error handling Stripe webhook:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Handle subscription created - provision phone number
 */
async function handleSubscriptionCreated(subscription, env) {
  const customerId = subscription.customer;

  console.log(`Provisioning premium features for customer: ${customerId}`);

  // TODO: Implement phone number provisioning
  // 1. Search for available toll-free number via Twilio API
  // 2. Purchase number
  // 3. Configure webhook URLs
  // 4. Update user config in database
  // 5. Send welcome email with phone number

  console.log('Phone number provisioning: TODO');
}

/**
 * Handle subscription updated
 */
async function handleSubscriptionUpdated(subscription, env) {
  const customerId = subscription.customer;

  console.log(`Subscription updated for customer: ${customerId}`);

  // Check if subscription is being cancelled
  if (subscription.cancel_at_period_end) {
    console.log(`Subscription will cancel at period end: ${new Date(subscription.current_period_end * 1000)}`);
    // TODO: Send notification email
  }
}

/**
 * Handle subscription deleted - release phone number
 */
async function handleSubscriptionDeleted(subscription, env) {
  const customerId = subscription.customer;

  console.log(`Downgrading customer to free tier: ${customerId}`);

  // TODO: Implement phone number release
  // 1. Get user's xSwarm phone number from database
  // 2. Release number back to Twilio pool
  // 3. Update user config to free tier
  // 4. Send downgrade notification email

  console.log('Phone number release: TODO');
}

/**
 * Handle successful payment - reset usage counters
 */
async function handlePaymentSucceeded(invoice, env) {
  const customerId = invoice.customer;

  console.log(`Payment succeeded for customer: ${customerId}`);
  console.log(`Amount: $${(invoice.amount_paid / 100).toFixed(2)}`);

  // TODO: Reset usage counters for new billing period
  // 1. Update user config: voice_minutes = 0, sms_messages = 0
  // 2. Update period_start and period_end dates
  // 3. Send receipt email

  console.log('Usage counter reset: TODO');
}

/**
 * Handle failed payment - notify user
 */
async function handlePaymentFailed(invoice, env) {
  const customerId = invoice.customer;

  console.log(`Payment FAILED for customer: ${customerId}`);
  console.log(`Amount attempted: $${(invoice.amount_due / 100).toFixed(2)}`);

  // TODO: Send urgent notification
  // 1. Send email with "Update Payment Method" link
  // 2. Send SMS alert if phone enabled
  // 3. Schedule auto-downgrade in 3 days if not resolved

  console.log('Payment failure notification: TODO');
}
