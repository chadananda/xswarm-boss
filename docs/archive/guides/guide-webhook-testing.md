# Webhook Testing Guide

Complete guide for testing Stripe webhooks in local development.

## Overview

We have three tools for webhook testing:

1. **`pnpm dev:webhooks`** - Stripe CLI webhook forwarding
2. **`pnpm dev:webhook-server`** - Local test server to receive webhooks
3. **`pnpm test:webhooks`** - Automated test suite

## Quick Start

### Option 1: Manual Testing (Recommended)

Test webhooks with full control over each step:

```bash
# Terminal 1: Start webhook forwarding
pnpm dev:webhooks

# Copy the webhook secret from output (whsec_...)
# Add to .env: STRIPE_WEBHOOK_SECRET_LOCAL=whsec_...

# Terminal 2: Start local webhook server
pnpm dev:webhook-server

# Terminal 3: Trigger test events
scripts/bin/stripe trigger customer.subscription.created
scripts/bin/stripe trigger invoice.payment_succeeded
```

### Option 2: Automated Testing

Run automated test suite to trigger multiple webhooks:

```bash
# Start webhook forwarding and server first (see above)

# Run basic tests (3 common events)
pnpm test:webhooks

# Run all tests (5+ events)
pnpm test:webhooks:all

# Test specific event
node scripts/test-webhooks.js --event=invoice.payment_failed
```

## Detailed Setup

### 1. Prerequisites

Before testing webhooks, ensure:

```bash
# ✓ Stripe CLI installed and logged in
scripts/bin/stripe --version
scripts/bin/stripe login

# ✓ Stripe API keys configured in .env
grep STRIPE_SECRET_KEY_TEST .env

# ✓ Local webhook secret configured (optional but recommended)
grep STRIPE_WEBHOOK_SECRET_LOCAL .env
```

### 2. Start Webhook Forwarding

**What it does**: Forwards Stripe webhooks from Stripe's servers to your local machine.

```bash
pnpm dev:webhooks
```

**Output**:
```
🔗 Local Webhook Forwarding

📍 Local server: http://localhost:8787/stripe/webhook
🔧 Method: stripe

🚀 Starting Stripe CLI webhook forwarding...

✓ Stripe CLI ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORTANT: Copy the webhook signing secret below to your .env file:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your webhook signing secret is ***REMOVED***

Ready! You are using Stripe API Version [2024-xx-xx]. Your webhook signing secret is ***REMOVED*** (^C to quit)
```

**Important**:
- Copy the `whsec_...` secret to `.env` as `STRIPE_WEBHOOK_SECRET_LOCAL`
- This secret changes every time you restart `pnpm dev:webhooks`
- Keep this terminal running

### 3. Start Local Webhook Server

**What it does**: HTTP server that receives and validates Stripe webhooks.

```bash
# In a new terminal
pnpm dev:webhook-server
```

**Output**:
```
🧪 Stripe Webhook Test Server

📍 Listening on: http://localhost:8787
🔗 Webhook endpoint: http://localhost:8787/stripe/webhook
🔐 Signature verification: ENABLED
   Secret: whsec_48d59c2...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Waiting for webhooks...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Features**:
- ✅ Verifies webhook signatures
- ✅ Parses and displays event details
- ✅ Handles all webhook event types
- ✅ Shows clear success/error messages

### 4. Trigger Test Events

**Option A: Manual (one at a time)**

```bash
# Trigger specific events
scripts/bin/stripe trigger customer.created
scripts/bin/stripe trigger customer.subscription.created
scripts/bin/stripe trigger invoice.payment_succeeded
scripts/bin/stripe trigger invoice.payment_failed
```

**Option B: Automated (batch)**

```bash
# Run test suite
pnpm test:webhooks        # Tests 3 common events
pnpm test:webhooks:all    # Tests 5+ events
```

### 5. Verify Results

Check the **webhook server terminal** for received events:

```
📨 Webhook received: customer.subscription.created
   ID: evt_1QF2xpRfk9upK3BeKwN3jqGw
   Created: 2024-01-15T10:30:45.000Z
   ✓ New subscription created
     Customer: cus_PQxRyZvWkXYzAB
     Status: active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Test Events

### Subscription Events

```bash
# New subscription
stripe trigger customer.subscription.created

# Subscription updated
stripe trigger customer.subscription.updated

# Subscription cancelled
stripe trigger customer.subscription.deleted
```

### Payment Events

```bash
# Successful payment
stripe trigger invoice.payment_succeeded

# Failed payment
stripe trigger invoice.payment_failed

# Payment requires action (3D Secure)
stripe trigger invoice.payment_action_required
```

### Customer Events

```bash
# New customer
stripe trigger customer.created

# Customer updated
stripe trigger customer.updated

# Customer deleted
stripe trigger customer.deleted
```

### Other Useful Events

```bash
# Checkout completed
stripe trigger checkout.session.completed

# Payment intent succeeded
stripe trigger payment_intent.succeeded

# Setup intent succeeded (saved card)
stripe trigger setup_intent.succeeded
```

## Webhook Event Structure

All webhooks follow this structure:

```json
{
  "id": "evt_1234567890",
  "type": "customer.subscription.created",
  "created": 1234567890,
  "data": {
    "object": {
      // Event-specific data
    }
  }
}
```

## Troubleshooting

### Webhook Not Received

**Problem**: Triggered event but nothing appears in server logs.

**Solutions**:
1. Check `pnpm dev:webhooks` is running
2. Check `pnpm dev:webhook-server` is running
3. Verify port is `8787` in both terminals
4. Check for firewall blocking localhost connections

### Signature Verification Failed

**Problem**: `❌ Signature verification failed: No signatures found matching the expected signature for payload`

**Solutions**:
1. Ensure `STRIPE_WEBHOOK_SECRET_LOCAL` is set in `.env`
2. Verify the secret matches the one from `pnpm dev:webhooks` output
3. Restart webhook server after updating `.env`
4. Check secret hasn't expired (restart `pnpm dev:webhooks` to get new one)

### Connection Refused

**Problem**: `Error: connect ECONNREFUSED 127.0.0.1:8787`

**Solution**:
1. Start `pnpm dev:webhook-server` first
2. Then start `pnpm dev:webhooks`

### Event Not Triggered

**Problem**: `stripe trigger` command fails

**Solutions**:
1. Verify Stripe CLI is logged in: `scripts/bin/stripe login`
2. Check API key is valid: `pnpm test:stripe`
3. Ensure using test mode keys (not live mode)

## Best Practices

### During Development

1. **Always verify signatures** - Never skip webhook signature verification
2. **Use test mode** - Only use test mode keys for development
3. **Check event types** - Handle all relevant event types for your app
4. **Test failure cases** - Trigger both success and failure events
5. **Monitor logs** - Watch webhook server logs for errors

### Testing Checklist

- [ ] Webhook forwarding running (`pnpm dev:webhooks`)
- [ ] Local server running (`pnpm dev:webhook-server`)
- [ ] Webhook secret configured in `.env`
- [ ] Signature verification enabled
- [ ] Test successful events (payment_succeeded, subscription_created)
- [ ] Test failure events (payment_failed)
- [ ] Verify event data is correctly parsed
- [ ] Check error handling works

## Production Webhooks

### Differences from Local Development

| Feature | Local Development | Production |
|---------|------------------|------------|
| **Webhook Secret** | Temporary (`whsec_...`) | Permanent (from Stripe Dashboard) |
| **Endpoint** | `localhost:8787/stripe/webhook` | `https://your-worker.dev/stripe/webhook` |
| **Forwarding** | Via Stripe CLI | Direct from Stripe |
| **Secret Management** | `.env` file | Cloudflare Workers environment variable |
| **Setup Command** | `pnpm dev:webhooks` | `pnpm setup:webhooks` |

### Deploying to Production

When you're ready to deploy:

```bash
# 1. Deploy your application
pnpm deploy:server

# 2. Set up production webhooks (automated)
pnpm setup:webhooks

# This will:
# - Create webhook endpoint in Stripe Dashboard
# - Configure all required event types
# - Push webhook secret to Cloudflare Workers
```

## Available Commands

```bash
# Start webhook forwarding
pnpm dev:webhooks

# Start local webhook test server
pnpm dev:webhook-server

# Run automated webhook tests
pnpm test:webhooks              # Basic (3 events)
pnpm test:webhooks:all          # Full suite (5+ events)

# Test specific event
node scripts/test-webhooks.js --event=customer.created

# Trigger events manually
scripts/bin/stripe trigger <event-type>

# View Stripe events
scripts/bin/stripe events list
```

## Resources

- **Stripe CLI Docs**: https://stripe.com/docs/stripe-cli
- **Webhook Events Reference**: https://stripe.com/docs/api/events/types
- **Testing Guide**: https://stripe.com/docs/webhooks/test
- **Signature Verification**: https://stripe.com/docs/webhooks/signatures

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review `planning/STRIPE_WEBHOOKS_SETUP.md`
3. Check Stripe Dashboard → Developers → Events
4. Open an issue with error logs
