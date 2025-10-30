# Stripe Webhooks - Automated Setup Guide

Complete guide for setting up Stripe webhooks in local development and production environments.

---

## Overview

Stripe webhooks notify your server about important events (subscription changes, payments, etc.). This guide covers:

1. **Local Development** - Test webhooks on your local machine
2. **Production Deployment** - Automated webhook setup after deployment

### Why Automated?

Manual webhook configuration via Stripe Dashboard is error-prone and time-consuming. Our automated approach:

✅ Creates webhook endpoints via Stripe API
✅ Automatically retrieves signing secrets
✅ Pushes secrets to Cloudflare Workers
✅ Idempotent (safe to re-run)
✅ Supports test and live modes

---

## Local Development Workflow

### Prerequisites

1. **Local dev server running:**
   ```bash
   pnpm dev:server
   # Server runs on http://localhost:8787
   ```

2. **Stripe CLI installed:**
   ```bash
   # macOS
   brew install stripe/stripe-cli/stripe

   # Linux
   # Download from https://github.com/stripe/stripe-cli/releases

   # Windows
   scoop install stripe
   ```

3. **Login to Stripe CLI:**
   ```bash
   stripe login
   # Opens browser to authenticate
   ```

### Step 1: Start Webhook Forwarding

```bash
pnpm dev:webhooks
```

This command:
- Starts Stripe CLI webhook forwarding
- Forwards webhook events to `http://localhost:8787/stripe/webhook`
- Displays a **webhook signing secret** (temporary, for local dev only)

**Example output:**
```
🔗 Local Webhook Forwarding

📍 Local server: http://localhost:8787/stripe/webhook
🔧 Method: stripe

✓ Stripe CLI ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORTANT: Copy the webhook signing secret below to your .env file:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ready! Your webhook signing secret is whsec_abcdef1234567890...
```

### Step 2: Configure .env

Copy the signing secret to your `.env` file:

```bash
# Add to .env (for local development only)
STRIPE_WEBHOOK_SECRET_LOCAL=whsec_abcdef1234567890...
```

**Note:** This secret is temporary and only works while `pnpm dev:webhooks` is running.

### Step 3: Test Webhooks Locally

With both the dev server and webhook forwarding running, trigger test events:

```bash
# Trigger subscription created event
stripe trigger customer.subscription.created

# Trigger payment succeeded event
stripe trigger invoice.payment_succeeded

# Trigger payment failed event
stripe trigger invoice.payment_failed
```

**Verify in terminal:**
- Stripe CLI shows event forwarded
- Your dev server logs show webhook received

---

## Alternative: Cloudflare Tunnel (For Team Sharing)

If you need a persistent public URL (e.g., for sharing with teammates):

### Step 1: Install cloudflared

```bash
# macOS
brew install cloudflared

# Linux
# Download from https://github.com/cloudflare/cloudflared/releases

# Windows
winget install --id Cloudflare.cloudflared
```

### Step 2: Start Tunnel

```bash
pnpm dev:webhooks --method cloudflare
```

This creates a public URL like `https://xxxxx.trycloudflare.com` that forwards to your local server.

### Step 3: Create Webhook in Stripe

1. Go to [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click **Add endpoint**
3. Endpoint URL: `https://xxxxx.trycloudflare.com/stripe/webhook`
4. Select events (see [Events](#webhook-events) section)
5. Copy the signing secret to `.env`

---

## Production Deployment Workflow

### Prerequisites

1. **API keys configured in .env:**
   ```bash
   STRIPE_SECRET_KEY_TEST=sk_test_...
   STRIPE_SECRET_KEY_LIVE=sk_live_...
   CLOUDFLARE_API_TOKEN=your_token_here
   ```

2. **Cloudflare Worker deployed:**
   ```bash
   pnpm deploy:server
   ```

### Automated Webhook Setup

After deploying your Worker, run:

```bash
pnpm setup:webhooks --url https://xswarm-server.your-account.workers.dev
```

**Or auto-detect Worker URL:**
```bash
pnpm setup:webhooks
```

**What this does:**

1. **Creates Test Mode Webhook:**
   - Endpoint: `https://your-worker.workers.dev/stripe/webhook`
   - Events: All required subscription/payment events
   - Returns: `whsec_test_xxxxxxxxxxxxx`

2. **Creates Live Mode Webhook:**
   - Same endpoint, different Stripe mode
   - Returns: `whsec_xxxxxxxxxxxxx`

3. **Pushes Secrets to Workers:**
   - `STRIPE_WEBHOOK_SECRET_TEST` → Cloudflare Workers
   - `STRIPE_WEBHOOK_SECRET_LIVE` → Cloudflare Workers

**Example output:**
```
🔗 Stripe Webhook Automation

📡 Detecting Worker URL from wrangler...
  Detected: https://xswarm-server.abc123.workers.dev

🎯 Webhook endpoint: https://xswarm-server.abc123.workers.dev/stripe/webhook

📝 Setting up test mode webhook...
  Creating new webhook...
  ✓ Webhook created successfully
  ID: we_xxxxxxxxxxxxx
  Secret: whsec_test_xxxxxxxxxxx...

📤 Pushing STRIPE_WEBHOOK_SECRET_TEST to Cloudflare Workers...
  ✓ STRIPE_WEBHOOK_SECRET_TEST pushed successfully

📝 Setting up live mode webhook...
  Creating new webhook...
  ✓ Webhook created successfully
  ID: we_xxxxxxxxxxxxx
  Secret: whsec_xxxxxxxxxx...

📤 Pushing STRIPE_WEBHOOK_SECRET_LIVE to Cloudflare Workers...
  ✓ STRIPE_WEBHOOK_SECRET_LIVE pushed successfully

✅ Webhook setup complete!

📋 Summary:
  Endpoint URL: https://xswarm-server.abc123.workers.dev/stripe/webhook
  Test webhook: we_test_xxxxxxxxxxxxx
  Live webhook: we_live_xxxxxxxxxxxxx
```

### Test-Only Mode

To only set up test webhooks (skip live mode):

```bash
pnpm setup:webhooks --test-only
```

---

## Webhook Events

The automated setup subscribes to these events:

### Subscription Events
| Event | Description |
|-------|-------------|
| `customer.subscription.created` | New subscription → provision phone number |
| `customer.subscription.updated` | Plan/status change → sync to database |
| `customer.subscription.deleted` | Cancellation → release resources |

### Payment Events
| Event | Description |
|-------|-------------|
| `invoice.payment_succeeded` | Successful billing → send receipt |
| `invoice.payment_failed` | Failed payment → notify user, start grace period |

### Customer Events
| Event | Description |
|-------|-------------|
| `customer.created` | New customer record |
| `customer.updated` | Payment method or info changed |

**Total: 7 events**

---

## Verification & Testing

### 1. Verify Webhook in Stripe Dashboard

**Test Mode:**
1. Go to [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/test/webhooks)
2. Toggle **Test mode** (orange banner)
3. Find your webhook endpoint
4. Status should be **Enabled**

**Live Mode:**
1. Toggle to **Live mode**
2. Repeat verification

### 2. Test Webhook Delivery

```bash
# Trigger test event
stripe trigger customer.subscription.created

# View Worker logs
wrangler tail --env production
```

**Expected log output:**
```
[Webhook] Received event: customer.subscription.created
[Webhook] Signature verified ✓
[Handler] Processing subscription creation...
```

### 3. Check Webhook Logs in Stripe

1. Stripe Dashboard → Developers → Webhooks
2. Click your endpoint
3. **Event logs** tab shows:
   - Recent events sent
   - Response status (should be 200 OK)
   - Delivery attempts

---

## Troubleshooting

### Problem: Webhook Secret Not Working

**Symptoms:**
- Signature verification fails
- 400 Bad Request errors in logs

**Solution:**
1. Ensure you're using the correct secret for the environment:
   - Local dev: `STRIPE_WEBHOOK_SECRET_LOCAL` (from `pnpm dev:webhooks`)
   - Production test: `STRIPE_WEBHOOK_SECRET_TEST` (from `pnpm setup:webhooks`)
   - Production live: `STRIPE_WEBHOOK_SECRET_LIVE`

2. Re-run setup script to get fresh secrets:
   ```bash
   pnpm setup:webhooks --url https://your-worker.workers.dev
   ```

### Problem: Worker URL Not Detected

**Symptoms:**
```
❌ Could not detect Worker URL from wrangler
```

**Solution:**
Provide URL manually:
```bash
pnpm setup:webhooks --url https://xswarm-server.your-account.workers.dev
```

Get your Worker URL:
```bash
wrangler whoami
# Or check: wrangler.toml → [env.production] → route
```

### Problem: Webhook Not Receiving Events

**Causes:**
1. **Firewall blocking** - Ensure Worker is publicly accessible
2. **Endpoint not registered** - Run `pnpm setup:webhooks`
3. **Wrong mode** - Test events only sent to test webhooks

**Debug steps:**
```bash
# 1. Test endpoint manually
curl -X POST https://your-worker.workers.dev/stripe/webhook

# 2. Check Worker logs
wrangler tail --env production

# 3. Verify webhook in Stripe Dashboard
# → Developers → Webhooks → Event logs
```

### Problem: Local Webhooks Not Working

**Symptoms:**
- Stripe CLI shows "forwarding to http://localhost:8787" but nothing happens

**Solution:**
1. **Verify dev server is running:**
   ```bash
   curl http://localhost:8787/health
   # Should return 200 OK
   ```

2. **Check port number:**
   ```bash
   # If server runs on different port:
   pnpm dev:webhooks --port 3000
   ```

3. **Restart both services:**
   ```bash
   # Terminal 1
   pnpm dev:server

   # Terminal 2
   pnpm dev:webhooks
   ```

---

## Complete Deployment Checklist

### Initial Setup (One Time)

- [ ] Install Stripe CLI: `brew install stripe/stripe-cli/stripe`
- [ ] Login to Stripe: `stripe login`
- [ ] Get Stripe API keys (test + live)
- [ ] Add keys to `.env`

### Local Development (Daily)

- [ ] Start dev server: `pnpm dev:server`
- [ ] Start webhook forwarding: `pnpm dev:webhooks`
- [ ] Copy local webhook secret to `.env`
- [ ] Test with: `stripe trigger customer.subscription.created`

### Production Deployment (Release)

- [ ] Build: `pnpm build:server`
- [ ] Deploy: `pnpm deploy:server`
- [ ] Setup webhooks: `pnpm setup:webhooks`
- [ ] Verify in Stripe Dashboard
- [ ] Test with: `stripe trigger customer.subscription.created`
- [ ] Monitor logs: `wrangler tail --env production`

---

## Webhook Security Best Practices

### 1. Always Verify Signatures

```typescript
// ✅ CORRECT: Verify before processing
const event = stripe.webhooks.constructEvent(
  rawBody,
  signature,
  webhookSecret
);

// ❌ WRONG: Trust without verification
const event = JSON.parse(rawBody);
```

### 2. Use Different Secrets per Environment

```bash
# Local development (temporary)
STRIPE_WEBHOOK_SECRET_LOCAL=whsec_abc...

# Production test mode
STRIPE_WEBHOOK_SECRET_TEST=whsec_test_xyz...

# Production live mode
STRIPE_WEBHOOK_SECRET_LIVE=whsec_xyz...
```

### 3. Idempotency

Track processed event IDs to prevent duplicate processing:

```typescript
// Check if event already processed
if (await db.eventExists(event.id)) {
  return { status: 200 }; // Already processed
}

// Process event
await handleEvent(event);

// Mark as processed
await db.saveEventId(event.id);
```

### 4. HTTPS Only in Production

- ✅ Production: `https://your-worker.workers.dev/stripe/webhook`
- ❌ Never use: `http://` in production (Stripe requires HTTPS)

### 5. Return 200 Quickly

```typescript
// ✅ CORRECT: Respond immediately, process async
export async function POST(request: Request) {
  const event = await verifyWebhook(request);

  // Queue for background processing
  await queue.enqueue(event);

  return new Response(null, { status: 200 });
}

// ❌ WRONG: Long processing blocks response
export async function POST(request: Request) {
  const event = await verifyWebhook(request);

  await processSubscription(event); // 5 seconds
  await sendEmail(event);           // 3 seconds
  await updateDatabase(event);      // 2 seconds

  return new Response(null, { status: 200 });
}
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install dependencies
        run: pnpm install

      - name: Build
        run: pnpm build:server

      - name: Deploy to Cloudflare Workers
        run: pnpm deploy:server
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}

      - name: Setup Stripe Webhooks
        run: pnpm setup:webhooks --url https://xswarm-server.abc123.workers.dev
        env:
          STRIPE_SECRET_KEY_TEST: ${{ secrets.STRIPE_SECRET_KEY_TEST }}
          STRIPE_SECRET_KEY_LIVE: ${{ secrets.STRIPE_SECRET_KEY_LIVE }}
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

---

## Resources

- **Stripe CLI:** https://stripe.com/docs/stripe-cli
- **Webhook API:** https://stripe.com/docs/api/webhook_endpoints
- **Signature Verification:** https://stripe.com/docs/webhooks/signatures
- **Event Types:** https://stripe.com/docs/api/events/types
- **Cloudflare Tunnel:** https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

---

**Next Steps:**
1. Set up local webhook forwarding: `pnpm dev:webhooks`
2. Test locally with Stripe CLI triggers
3. Deploy to production and run: `pnpm setup:webhooks`
4. Verify webhooks in Stripe Dashboard
