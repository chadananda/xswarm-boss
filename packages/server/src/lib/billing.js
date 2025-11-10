/**
 * Billing System
 *
 * Handles overage billing, usage resets, prorations, and invoice generation.
 * Integrates with Stripe for automated billing.
 */

import Stripe from 'stripe';
import { createClient } from '@libsql/client';
import { getCurrentUsage, getOrCreateUsageRecord } from './usage-tracker.js';
import { getUserById, getUserByStripeCustomerId } from './users.js';

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
 * Overage pricing (cents)
 */
const OVERAGE_RATES = {
  voice_per_minute: 1.3, // $0.013 per minute = 1.3 cents
  sms_per_message: 0.75, // $0.0075 per message = 0.75 cents
  phone_number_monthly: 500, // $5 per month = 500 cents
};

/**
 * Subscription tier limits
 */
const TIER_LIMITS = {
  ai_buddy: {
    voice_minutes: 0,
    sms_messages: 0,
  },
  ai_secretary: {
    voice_minutes: 100,
    sms_messages: 100,
  },
  ai_project_manager: {
    voice_minutes: 500,
    sms_messages: 500,
  },
  ai_cto: {
    voice_minutes: -1, // unlimited
    sms_messages: -1, // unlimited
  },
};

/**
 * Calculate overage charges for current billing period
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 * @returns {Object} Overage breakdown
 */
export async function calculateOverages(userId, env) {
  try {
    const usage = await getCurrentUsage(userId, env);
    const user = await getUserById(userId, env);

    const limits = TIER_LIMITS[user.subscription_tier] || TIER_LIMITS.ai_buddy;

    // Calculate overages (0 if unlimited)
    const voiceOverage = limits.voice_minutes === -1 ? 0 : Math.max(0, usage.voice_minutes - limits.voice_minutes);
    const smsOverage = limits.sms_messages === -1 ? 0 : Math.max(0, usage.sms_messages - limits.sms_messages);

    // Calculate costs in cents
    const voiceCost = Math.round(voiceOverage * OVERAGE_RATES.voice_per_minute);
    const smsCost = Math.round(smsOverage * OVERAGE_RATES.sms_per_message);

    // Phone number cost if provisioned
    const phoneCost = user.xswarm_phone ? OVERAGE_RATES.phone_number_monthly : 0;

    const totalCents = voiceCost + smsCost + phoneCost;

    return {
      voice: {
        overage_units: voiceOverage,
        cost_cents: voiceCost,
        rate_cents: OVERAGE_RATES.voice_per_minute,
      },
      sms: {
        overage_units: smsOverage,
        cost_cents: smsCost,
        rate_cents: OVERAGE_RATES.sms_per_message,
      },
      phone: {
        has_phone: !!user.xswarm_phone,
        cost_cents: phoneCost,
      },
      total_cents: totalCents,
      total_dollars: (totalCents / 100).toFixed(2),
    };
  } catch (error) {
    console.error('Error calculating overages:', error);
    throw error;
  }
}

/**
 * Create Stripe invoice items for overages
 *
 * @param {string} userId - User ID
 * @param {string} subscriptionId - Stripe subscription ID
 * @param {Object} env - Environment variables
 * @returns {Array} Created invoice items
 */
export async function createOverageInvoiceItems(userId, subscriptionId, env) {
  try {
    const stripe = new Stripe(env.STRIPE_SECRET_KEY);
    const user = await getUserById(userId, env);
    const overages = await calculateOverages(userId, env);

    if (!user.stripe_customer_id) {
      throw new Error('User has no Stripe customer ID');
    }

    const items = [];

    // Voice overage item
    if (overages.voice.cost_cents > 0) {
      const item = await stripe.invoiceItems.create({
        customer: user.stripe_customer_id,
        amount: overages.voice.cost_cents,
        currency: 'usd',
        description: `Voice overage: ${overages.voice.overage_units} minutes @ $${(overages.voice.rate_cents / 100).toFixed(4)}/min`,
        subscription: subscriptionId,
      });
      items.push(item);
      console.log(`Created voice overage invoice item: ${item.id} ($${(item.amount / 100).toFixed(2)})`);
    }

    // SMS overage item
    if (overages.sms.cost_cents > 0) {
      const item = await stripe.invoiceItems.create({
        customer: user.stripe_customer_id,
        amount: overages.sms.cost_cents,
        currency: 'usd',
        description: `SMS overage: ${overages.sms.overage_units} messages @ $${(overages.sms.rate_cents / 100).toFixed(4)}/msg`,
        subscription: subscriptionId,
      });
      items.push(item);
      console.log(`Created SMS overage invoice item: ${item.id} ($${(item.amount / 100).toFixed(2)})`);
    }

    // Phone number item
    if (overages.phone.cost_cents > 0) {
      const item = await stripe.invoiceItems.create({
        customer: user.stripe_customer_id,
        amount: overages.phone.cost_cents,
        currency: 'usd',
        description: `Phone number: ${user.xswarm_phone}`,
        subscription: subscriptionId,
      });
      items.push(item);
      console.log(`Created phone number invoice item: ${item.id} ($${(item.amount / 100).toFixed(2)})`);
    }

    return items;
  } catch (error) {
    console.error('Error creating overage invoice items:', error);
    throw error;
  }
}

/**
 * Reset usage counters for new billing period
 *
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function resetUsageCounters(userId, env) {
  try {
    // This will create a new usage record for the current billing period
    await getOrCreateUsageRecord(userId, env);
    console.log(`Reset usage counters for user ${userId}`);
  } catch (error) {
    console.error('Error resetting usage counters:', error);
    throw error;
  }
}

/**
 * Record billing event in database
 *
 * @param {string} userId - User ID
 * @param {string} eventType - Event type (payment_succeeded, payment_failed, etc.)
 * @param {number} amountCents - Amount in cents
 * @param {string} description - Event description
 * @param {string} stripeEventId - Stripe event ID for idempotency
 * @param {Object} env - Environment variables
 */
export async function recordBillingEvent(userId, eventType, amountCents, description, stripeEventId, env) {
  try {
    const db = getDbClient(env);

    // Check if event already processed (idempotency)
    const existing = await db.execute({
      sql: 'SELECT id FROM billing_events WHERE stripe_event_id = ?',
      args: [stripeEventId],
    });

    if (existing.rows.length > 0) {
      console.log(`Billing event ${stripeEventId} already processed, skipping`);
      return existing.rows[0].id;
    }

    const id = crypto.randomUUID();
    await db.execute({
      sql: `
        INSERT INTO billing_events (id, user_id, event_type, amount_cents, description, stripe_event_id, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `,
      args: [id, userId, eventType, amountCents, description, stripeEventId, new Date().toISOString()],
    });

    console.log(`Recorded billing event: ${eventType} for user ${userId} (${stripeEventId})`);
    return id;
  } catch (error) {
    console.error('Error recording billing event:', error);
    throw error;
  }
}

/**
 * Calculate prorated price for tier change
 *
 * @param {string} currentTier - Current subscription tier
 * @param {string} newTier - New subscription tier
 * @param {Date} periodStart - Current period start date
 * @param {Date} periodEnd - Current period end date
 * @param {Object} env - Environment variables
 * @returns {Object} Proration details
 */
export async function calculateProration(currentTier, newTier, periodStart, periodEnd, env) {
  try {
    const tierPrices = {
      ai_buddy: 0,
      ai_secretary: 4000, // $40 in cents
      ai_project_manager: 28000, // $280 in cents
      ai_cto: 0, // custom pricing
    };

    const currentPrice = tierPrices[currentTier] || 0;
    const newPrice = tierPrices[newTier] || 0;

    const now = new Date();
    const totalDays = Math.ceil((periodEnd - periodStart) / (1000 * 60 * 60 * 24));
    const remainingDays = Math.ceil((periodEnd - now) / (1000 * 60 * 60 * 24));

    // Calculate unused portion of current tier
    const unusedAmount = Math.round((currentPrice * remainingDays) / totalDays);

    // Calculate prorated amount for new tier
    const proratedAmount = Math.round((newPrice * remainingDays) / totalDays);

    // Net charge (credit unused + charge for new tier)
    const netCharge = proratedAmount - unusedAmount;

    return {
      current_tier: currentTier,
      new_tier: newTier,
      current_price_cents: currentPrice,
      new_price_cents: newPrice,
      total_days: totalDays,
      remaining_days: remainingDays,
      unused_credit_cents: unusedAmount,
      prorated_charge_cents: proratedAmount,
      net_charge_cents: netCharge,
      net_charge_dollars: (netCharge / 100).toFixed(2),
    };
  } catch (error) {
    console.error('Error calculating proration:', error);
    throw error;
  }
}

/**
 * Create billing history record
 *
 * @param {Object} invoice - Stripe invoice object
 * @param {string} userId - User ID
 * @param {Object} env - Environment variables
 */
export async function createBillingHistoryRecord(invoice, userId, env) {
  try {
    const db = getDbClient(env);

    // Check if already exists (idempotency)
    const existing = await db.execute({
      sql: 'SELECT id FROM billing_history WHERE stripe_invoice_id = ?',
      args: [invoice.id],
    });

    if (existing.rows.length > 0) {
      console.log(`Billing history for invoice ${invoice.id} already exists`);
      return existing.rows[0].id;
    }

    const id = crypto.randomUUID();
    const now = new Date().toISOString();

    await db.execute({
      sql: `
        INSERT INTO billing_history (
          id, user_id, amount, status, description,
          invoice_url, period_start, period_end,
          stripe_invoice_id, stripe_payment_intent_id,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
      args: [
        id,
        userId,
        invoice.amount_paid || invoice.amount_due,
        invoice.status,
        invoice.description || 'Monthly subscription',
        invoice.hosted_invoice_url,
        invoice.period_start ? new Date(invoice.period_start * 1000).toISOString() : null,
        invoice.period_end ? new Date(invoice.period_end * 1000).toISOString() : null,
        invoice.id,
        invoice.payment_intent,
        now,
        now,
      ],
    });

    console.log(`Created billing history record for invoice ${invoice.id}`);
    return id;
  } catch (error) {
    console.error('Error creating billing history record:', error);
    throw error;
  }
}

/**
 * Get upcoming invoice estimate from Stripe
 *
 * @param {string} customerId - Stripe customer ID
 * @param {Object} env - Environment variables
 * @returns {Object} Upcoming invoice details
 */
export async function getUpcomingInvoice(customerId, env) {
  try {
    const stripe = new Stripe(env.STRIPE_SECRET_KEY);

    const upcomingInvoice = await stripe.invoices.retrieveUpcoming({
      customer: customerId,
    });

    return {
      amount_due: upcomingInvoice.amount_due,
      amount_dollars: (upcomingInvoice.amount_due / 100).toFixed(2),
      period_start: new Date(upcomingInvoice.period_start * 1000).toISOString(),
      period_end: new Date(upcomingInvoice.period_end * 1000).toISOString(),
      next_payment_attempt: upcomingInvoice.next_payment_attempt
        ? new Date(upcomingInvoice.next_payment_attempt * 1000).toISOString()
        : null,
      lines: upcomingInvoice.lines.data.map(line => ({
        description: line.description,
        amount: line.amount,
        amount_dollars: (line.amount / 100).toFixed(2),
      })),
    };
  } catch (error) {
    console.error('Error retrieving upcoming invoice:', error);
    throw error;
  }
}

/**
 * Update user billing cycle start date
 *
 * @param {string} userId - User ID
 * @param {Date} billingCycleStart - Billing cycle start date
 * @param {Object} env - Environment variables
 */
export async function updateBillingCycleStart(userId, billingCycleStart, env) {
  try {
    const db = getDbClient(env);

    await db.execute({
      sql: 'UPDATE users SET billing_cycle_start = ?, updated_at = ? WHERE id = ?',
      args: [billingCycleStart.toISOString(), new Date().toISOString(), userId],
    });

    console.log(`Updated billing cycle start for user ${userId}: ${billingCycleStart.toISOString()}`);
  } catch (error) {
    console.error('Error updating billing cycle start:', error);
    throw error;
  }
}

/**
 * Update user trial end date
 *
 * @param {string} userId - User ID
 * @param {Date} trialEndDate - Trial end date
 * @param {Object} env - Environment variables
 */
export async function updateTrialEndDate(userId, trialEndDate, env) {
  try {
    const db = getDbClient(env);

    await db.execute({
      sql: 'UPDATE users SET trial_end_date = ?, updated_at = ? WHERE id = ?',
      args: [trialEndDate.toISOString(), new Date().toISOString(), userId],
    });

    console.log(`Updated trial end date for user ${userId}: ${trialEndDate.toISOString()}`);
  } catch (error) {
    console.error('Error updating trial end date:', error);
    throw error;
  }
}
