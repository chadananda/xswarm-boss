/**
 * Stripe Webhook Handler
 *
 * Handles subscription lifecycle events:
 * - customer.subscription.created (provision phone number)
 * - customer.subscription.updated (handle tier changes)
 * - customer.subscription.deleted (release phone number)
 * - customer.subscription.trial_will_end (send notification)
 * - invoice.payment_succeeded (reset usage counters)
 * - invoice.payment_failed (notify user)
 * - invoice.upcoming (add overage charges)
 */

import Stripe from 'stripe';
import { getUserByStripeCustomerId, updateUserTier, updateUserStripeInfo } from '../lib/users.js';
import {
  provisionPhoneNumber,
  releasePhoneNumber,
} from '../lib/phone-provisioning.js';
import {
  resetUsageCounters,
  recordBillingEvent,
  createBillingHistoryRecord,
  createOverageInvoiceItems,
} from '../lib/billing.js';

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
        await handleSubscriptionCreated(event.data.object, event.id, env);
        break;

      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object, event.id, env);
        break;

      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(event.data.object, event.id, env);
        break;

      case 'customer.subscription.trial_will_end':
        await handleTrialEnding(event.data.object, event.id, env);
        break;

      case 'invoice.payment_succeeded':
        await handlePaymentSucceeded(event.data.object, event.id, env);
        break;

      case 'invoice.payment_failed':
        await handlePaymentFailed(event.data.object, event.id, env);
        break;

      case 'invoice.upcoming':
        await handleUpcomingInvoice(event.data.object, event.id, env);
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
async function handleSubscriptionCreated(subscription, eventId, env) {
  try {
    const customerId = subscription.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    console.log(`Provisioning premium features for user: ${user.id} (${user.email})`);

    // Update user with subscription ID
    await updateUserStripeInfo(user.id, customerId, subscription.id, env);

    // Determine tier from subscription metadata or price ID
    const tier = subscription.metadata?.target_tier || determineTierFromSubscription(subscription, env);
    await updateUserTier(user.id, tier, env);

    // Record billing cycle start
    const billingCycleStart = new Date(subscription.current_period_start * 1000);
    await recordBillingEvent(
      user.id,
      'subscription_created',
      0,
      `Subscription created: ${tier}`,
      eventId,
      env
    );

    // Provision phone number for premium tiers
    if (tier !== 'ai_buddy') {
      try {
        console.log(`Provisioning phone number for user ${user.id}...`);
        const phoneDetails = await provisionPhoneNumber(user.id, null, env);
        console.log(`Phone number provisioned: ${phoneDetails.phone_number}`);

        // Send welcome email (if email service available)
        if (env.SENDGRID_API_KEY) {
          await sendWelcomeEmail(user, phoneDetails.phone_number, tier, env);
        }
      } catch (error) {
        console.error(`Failed to provision phone number for user ${user.id}:`, error);
        // Don't fail the webhook, but log for manual follow-up
      }
    }

    console.log(`Subscription created successfully for user ${user.id}`);
  } catch (error) {
    console.error('Error handling subscription created:', error);
    throw error;
  }
}

/**
 * Handle subscription updated
 */
async function handleSubscriptionUpdated(subscription, eventId, env) {
  try {
    const customerId = subscription.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    console.log(`Subscription updated for user: ${user.id}`);

    // Check if subscription is being cancelled
    if (subscription.cancel_at_period_end) {
      const cancelDate = new Date(subscription.current_period_end * 1000);
      console.log(`Subscription will cancel at: ${cancelDate.toISOString()}`);

      await recordBillingEvent(
        user.id,
        'subscription_cancel_scheduled',
        0,
        `Subscription scheduled for cancellation on ${cancelDate.toISOString()}`,
        eventId,
        env
      );

      // Send cancellation notification
      if (env.SENDGRID_API_KEY) {
        await sendCancellationNotification(user, cancelDate, env);
      }

      return;
    }

    // Check for tier change
    const newTier = subscription.metadata?.target_tier || determineTierFromSubscription(subscription, env);
    if (newTier && newTier !== user.subscription_tier) {
      console.log(`Tier changed from ${user.subscription_tier} to ${newTier}`);
      await updateUserTier(user.id, newTier, env);

      await recordBillingEvent(
        user.id,
        'subscription_tier_changed',
        0,
        `Tier changed from ${user.subscription_tier} to ${newTier}`,
        eventId,
        env
      );

      // Handle phone provisioning based on tier change
      if (user.subscription_tier === 'ai_buddy' && newTier !== 'ai_buddy') {
        // Upgrading from free to paid - provision phone
        if (!user.xswarm_phone) {
          try {
            const phoneDetails = await provisionPhoneNumber(user.id, null, env);
            console.log(`Phone number provisioned on upgrade: ${phoneDetails.phone_number}`);
          } catch (error) {
            console.error(`Failed to provision phone on upgrade:`, error);
          }
        }
      } else if (user.subscription_tier !== 'ai_buddy' && newTier === 'ai_buddy') {
        // Downgrading to free - release phone
        if (user.xswarm_phone) {
          try {
            await releasePhoneNumber(user.id, user.xswarm_phone, env);
            console.log(`Phone number released on downgrade`);
          } catch (error) {
            console.error(`Failed to release phone on downgrade:`, error);
          }
        }
      }
    }

    // Check if subscription status changed
    if (subscription.status === 'active' && user.subscription_tier === 'ai_buddy') {
      // Subscription reactivated
      const tier = determineTierFromSubscription(subscription, env);
      await updateUserTier(user.id, tier, env);

      await recordBillingEvent(
        user.id,
        'subscription_reactivated',
        0,
        `Subscription reactivated: ${tier}`,
        eventId,
        env
      );
    }
  } catch (error) {
    console.error('Error handling subscription updated:', error);
    throw error;
  }
}

/**
 * Handle subscription deleted - release phone number
 */
async function handleSubscriptionDeleted(subscription, eventId, env) {
  try {
    const customerId = subscription.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    console.log(`Downgrading user to free tier: ${user.id}`);

    // Release phone number
    if (user.xswarm_phone) {
      try {
        await releasePhoneNumber(user.id, user.xswarm_phone, env);
        console.log(`Phone number released: ${user.xswarm_phone}`);
      } catch (error) {
        console.error(`Failed to release phone number:`, error);
        // Continue with downgrade even if phone release fails
      }
    }

    // Downgrade to free tier
    await updateUserTier(user.id, 'ai_buddy', env);
    await updateUserStripeInfo(user.id, customerId, null, env);

    await recordBillingEvent(
      user.id,
      'subscription_deleted',
      0,
      'Subscription cancelled, downgraded to free tier',
      eventId,
      env
    );

    // Send downgrade notification
    if (env.SENDGRID_API_KEY) {
      await sendDowngradeNotification(user, env);
    }

    console.log(`User ${user.id} downgraded to free tier successfully`);
  } catch (error) {
    console.error('Error handling subscription deleted:', error);
    throw error;
  }
}

/**
 * Handle trial ending soon
 */
async function handleTrialEnding(subscription, eventId, env) {
  try {
    const customerId = subscription.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    const trialEndDate = new Date(subscription.trial_end * 1000);
    console.log(`Trial ending for user ${user.id} on ${trialEndDate.toISOString()}`);

    await recordBillingEvent(
      user.id,
      'trial_ending',
      0,
      `Trial ending on ${trialEndDate.toISOString()}`,
      eventId,
      env
    );

    // Send trial ending notification
    if (env.SENDGRID_API_KEY) {
      await sendTrialEndingNotification(user, trialEndDate, env);
    }
  } catch (error) {
    console.error('Error handling trial ending:', error);
    throw error;
  }
}

/**
 * Handle successful payment - reset usage counters
 */
async function handlePaymentSucceeded(invoice, eventId, env) {
  try {
    const customerId = invoice.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    console.log(`Payment succeeded for user: ${user.id}`);
    console.log(`Amount: $${(invoice.amount_paid / 100).toFixed(2)}`);

    // Record billing event
    await recordBillingEvent(
      user.id,
      'payment_succeeded',
      invoice.amount_paid,
      `Payment received: $${(invoice.amount_paid / 100).toFixed(2)}`,
      eventId,
      env
    );

    // Create billing history record
    await createBillingHistoryRecord(invoice, user.id, env);

    // Reset usage counters for new billing period
    await resetUsageCounters(user.id, env);
    console.log(`Usage counters reset for user ${user.id}`);

    // Send receipt email
    if (env.SENDGRID_API_KEY && invoice.hosted_invoice_url) {
      await sendReceiptEmail(user, invoice, env);
    }
  } catch (error) {
    console.error('Error handling payment succeeded:', error);
    throw error;
  }
}

/**
 * Handle failed payment - notify user
 */
async function handlePaymentFailed(invoice, eventId, env) {
  try {
    const customerId = invoice.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    console.log(`Payment FAILED for user: ${user.id}`);
    console.log(`Amount attempted: $${(invoice.amount_due / 100).toFixed(2)}`);

    // Record billing event
    await recordBillingEvent(
      user.id,
      'payment_failed',
      invoice.amount_due,
      `Payment failed: $${(invoice.amount_due / 100).toFixed(2)}`,
      eventId,
      env
    );

    // Create billing history record
    await createBillingHistoryRecord(invoice, user.id, env);

    // Send urgent notification via email and SMS
    if (env.SENDGRID_API_KEY) {
      await sendPaymentFailedEmail(user, invoice, env);
    }

    if (env.TWILIO_ACCOUNT_SID && user.user_phone) {
      await sendPaymentFailedSMS(user, env);
    }

    console.log(`Payment failure notifications sent to user ${user.id}`);
  } catch (error) {
    console.error('Error handling payment failed:', error);
    throw error;
  }
}

/**
 * Handle upcoming invoice - add overage charges
 */
async function handleUpcomingInvoice(invoice, eventId, env) {
  try {
    const customerId = invoice.customer;
    const user = await getUserByStripeCustomerId(customerId, env);

    if (!user) {
      console.error(`User not found for customer ${customerId}`);
      return;
    }

    if (!user.stripe_subscription_id) {
      console.log(`User ${user.id} has no active subscription, skipping overage charges`);
      return;
    }

    console.log(`Processing upcoming invoice for user: ${user.id}`);

    // Add overage charges to invoice
    const items = await createOverageInvoiceItems(user.id, user.stripe_subscription_id, env);

    if (items.length > 0) {
      const totalOverage = items.reduce((sum, item) => sum + item.amount, 0);
      console.log(`Added ${items.length} overage items totaling $${(totalOverage / 100).toFixed(2)}`);

      await recordBillingEvent(
        user.id,
        'overage_charges_added',
        totalOverage,
        `Overage charges added: $${(totalOverage / 100).toFixed(2)}`,
        eventId,
        env
      );
    } else {
      console.log(`No overage charges for user ${user.id}`);
    }
  } catch (error) {
    console.error('Error handling upcoming invoice:', error);
    throw error;
  }
}

/**
 * Determine subscription tier from subscription object
 */
function determineTierFromSubscription(subscription, env) {
  // Check metadata first
  if (subscription.metadata?.target_tier) {
    return subscription.metadata.target_tier;
  }

  // Check price ID
  const priceId = subscription.items?.data[0]?.price?.id;

  if (priceId === env.STRIPE_PRICE_AI_SECRETARY) {
    return 'ai_secretary';
  } else if (priceId === env.STRIPE_PRICE_AI_PROJECT_MANAGER) {
    return 'ai_project_manager';
  }

  // Default to ai_secretary for paid subscriptions
  return 'ai_secretary';
}

/**
 * Send welcome email (placeholder - implement with SendGrid)
 */
async function sendWelcomeEmail(user, phoneNumber, tier, env) {
  console.log(`TODO: Send welcome email to ${user.email} with phone ${phoneNumber}`);
  // Implementation would use SendGrid API
}

/**
 * Send cancellation notification (placeholder)
 */
async function sendCancellationNotification(user, cancelDate, env) {
  console.log(`TODO: Send cancellation notification to ${user.email}`);
}

/**
 * Send downgrade notification (placeholder)
 */
async function sendDowngradeNotification(user, env) {
  console.log(`TODO: Send downgrade notification to ${user.email}`);
}

/**
 * Send trial ending notification (placeholder)
 */
async function sendTrialEndingNotification(user, trialEndDate, env) {
  console.log(`TODO: Send trial ending notification to ${user.email}`);
}

/**
 * Send receipt email (placeholder)
 */
async function sendReceiptEmail(user, invoice, env) {
  console.log(`TODO: Send receipt email to ${user.email}`);
}

/**
 * Send payment failed email (placeholder)
 */
async function sendPaymentFailedEmail(user, invoice, env) {
  console.log(`TODO: Send payment failed email to ${user.email}`);
}

/**
 * Send payment failed SMS (placeholder)
 */
async function sendPaymentFailedSMS(user, env) {
  console.log(`TODO: Send payment failed SMS to ${user.user_phone}`);
}
