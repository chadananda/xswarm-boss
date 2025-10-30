# Server Setup Guide - Cloudflare Workers

Complete guide to deploying the xSwarm webhook server on Cloudflare Workers.

---

## Overview

xSwarm uses **Cloudflare Workers** for serverless webhook handling. This provides:

- **Global edge deployment** - 330+ cities worldwide, <15ms latency
- **Zero cost** - FREE tier includes 100,000 requests/day (3M/month)
- **Zero maintenance** - No servers to manage, auto-scaling
- **Perfect for webhooks** - Instant response to Twilio and Stripe callbacks

**Architecture:**
```
Twilio Call/SMS → Cloudflare Workers → Turso Database
Stripe Event     →                  → TwiML Response
```

---

## Prerequisites

### 1. Cloudflare Account

Sign up for free at [cloudflare.com](https://dash.cloudflare.com/sign-up).

**Free tier includes:**
- 100,000 requests/day
- No credit card required
- Unlimited Workers scripts
- 30 Workers KV namespaces (not needed for MVP)

### 2. Wrangler CLI

Already installed via `pnpm install`. Verify:

```bash
cd packages/server
pnpm wrangler --version
```

### 3. Required API Keys

Make sure your `.env` file has:

- `TWILIO_ACCOUNT_SID` - From console.twilio.com
- `TWILIO_AUTH_TOKEN` - From console.twilio.com
- `STRIPE_SECRET_KEY` - From dashboard.stripe.com
- `STRIPE_WEBHOOK_SECRET` - From Stripe webhook settings
- `TURSO_DATABASE_URL` - From turso.tech
- `TURSO_AUTH_TOKEN` - From turso.tech

---

## Initial Setup

### Step 1: Login to Cloudflare

```bash
cd packages/server
pnpm wrangler login
```

This opens your browser for authentication. Approve access.

### Step 2: Get Account ID

```bash
pnpm wrangler whoami
```

Copy your **Account ID** and add it to `wrangler.toml`:

```toml
account_id = "your_account_id_here"
```

### Step 3: Create .dev.vars for Local Development

```bash
cd packages/server
cp .dev.vars.example .dev.vars
```

Edit `.dev.vars` with your actual secrets (same as root `.env`).

**Important:** `.dev.vars` is gitignored. Never commit secrets.

---

## Secret Management

Secrets are stored encrypted in Cloudflare, **separate from your code**.

### One-Time Secret Setup (Recommended)

From project root:

```bash
pnpm setup:secrets
```

This script:
1. Reads secrets from root `.env`
2. Pushes them to Cloudflare Workers
3. Shows confirmation of each secret pushed

**Output:**
```
🔐 Cloudflare Workers Secret Setup

📋 Found secrets in .env:
  ✓ TWILIO_ACCOUNT_SID: ACcddd6c85...
  ✓ TWILIO_AUTH_TOKEN: d1b32e7a93...
  ✓ STRIPE_SECRET_KEY: sk_test_51...
  ✓ STRIPE_WEBHOOK_SECRET: whsec_abc1...
  ✓ TURSO_DATABASE_URL: libsql://x...
  ✓ TURSO_AUTH_TOKEN: eyJhbGciOi...

📤 Ready to push 6 secrets to Cloudflare Workers.

Continue? (yes/no): yes

🚀 Pushing secrets to Cloudflare Workers...

  ✓ TWILIO_ACCOUNT_SID pushed successfully
  ✓ TWILIO_AUTH_TOKEN pushed successfully
  ✓ STRIPE_SECRET_KEY pushed successfully
  ✓ STRIPE_WEBHOOK_SECRET pushed successfully
  ✓ TURSO_DATABASE_URL pushed successfully
  ✓ TURSO_AUTH_TOKEN pushed successfully

✅ Secret setup complete!
```

### Manual Secret Management (Alternative)

Push individual secrets:

```bash
cd packages/server
pnpm wrangler secret put TWILIO_AUTH_TOKEN
# Enter value when prompted
```

List secrets:

```bash
pnpm wrangler secret list
```

Delete secret:

```bash
pnpm wrangler secret delete TWILIO_AUTH_TOKEN
```

---

## Local Development

### Run Locally

```bash
# From project root
pnpm dev:server

# Or from packages/server
cd packages/server
pnpm dev
```

**Output:**
```
⛅️ wrangler 3.28.0
------------------
⎔ Starting local server...
[wrangler:inf] Ready on http://localhost:8787
```

### Test Health Endpoint

```bash
curl http://localhost:8787/health
```

**Response:**
```json
{
  "status": "ok",
  "service": "xswarm-webhooks",
  "timestamp": "2025-10-23T10:30:00.000Z"
}
```

### Test Voice Webhook (Local)

```bash
curl -X POST http://localhost:8787/voice/test123 \
  -d "From=+15551234567" \
  -d "To=+18005551234" \
  -d "CallSid=CA1234567890"
```

**Response:** TwiML XML

---

## Production Deployment

### Deploy to Cloudflare

```bash
# From project root
pnpm deploy:server

# Or from packages/server
cd packages/server
pnpm deploy
```

**Output:**
```
⛅️ wrangler 3.28.0
------------------
Total Upload: 45.23 KiB / gzip: 12.34 KiB
Uploaded xswarm-webhooks (0.89 sec)
Published xswarm-webhooks (0.25 sec)
  https://xswarm-webhooks.your-subdomain.workers.dev
Current Deployment ID: abc12345-6789-def0-1234-567890abcdef
```

**Your Worker URL:**
```
https://xswarm-webhooks.your-subdomain.workers.dev
```

Save this URL - you'll need it for Twilio and Stripe webhooks.

---

## Webhook Configuration

### Twilio Voice & SMS Webhooks

For each phone number provisioned:

1. Go to [console.twilio.com](https://console.twilio.com)
2. Phone Numbers → Active Numbers → Select number
3. **Voice Configuration:**
   - A Call Comes In: `Webhook`
   - URL: `https://xswarm-webhooks.your-subdomain.workers.dev/voice/{userId}`
   - Method: `HTTP POST`
4. **Messaging Configuration:**
   - A Message Comes In: `Webhook`
   - URL: `https://xswarm-webhooks.your-subdomain.workers.dev/sms/{userId}`
   - Method: `HTTP POST`
5. Save

**Important:** Replace `{userId}` with the actual user ID from your database.

### Stripe Webhooks

1. Go to [dashboard.stripe.com/webhooks](https://dashboard.stripe.com/webhooks)
2. Click **Add endpoint**
3. **Endpoint URL:**
   ```
   https://xswarm-webhooks.your-subdomain.workers.dev/stripe/webhook
   ```
4. **Events to send:**
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Save endpoint
6. **Copy webhook signing secret** (starts with `whsec_`)
7. Update secret:
   ```bash
   cd packages/server
   pnpm wrangler secret put STRIPE_WEBHOOK_SECRET
   # Paste the whsec_... value
   ```

---

## Monitoring & Debugging

### View Real-Time Logs

```bash
cd packages/server
pnpm tail
```

**Output:**
```
Streaming logs from xswarm-webhooks...

[2025-10-23 10:30:15] Voice webhook: +15551234567 → +18005551234
[2025-10-23 10:30:15] Accepting call from +15551234567 to alice's xSwarm
[2025-10-23 10:30:23] SMS webhook: +15551234567 → +18005551234
[2025-10-23 10:30:23] Message: "status" (SM1234567890)
```

### View Metrics in Dashboard

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Workers & Pages → xswarm-webhooks
3. **Metrics tab** shows:
   - Requests per second
   - Response time (p50, p99)
   - Success rate
   - CPU time

### Debug Failed Requests

In Cloudflare dashboard → Workers → xswarm-webhooks → Logs:

- View all requests with errors
- See stack traces
- Filter by status code, URL, etc.

---

## Testing

### Test Health Check

```bash
curl https://xswarm-webhooks.your-subdomain.workers.dev/health
```

**Expected:**
```json
{
  "status": "ok",
  "service": "xswarm-webhooks",
  "timestamp": "2025-10-23T10:30:00.000Z"
}
```

### Test Twilio Webhook (requires valid signature)

Use Twilio's test tool:

1. Go to console.twilio.com
2. Phone Numbers → Your number → Make test call
3. Check Worker logs: `pnpm tail`

### Test Stripe Webhook

Use Stripe CLI:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Forward webhooks to local dev
stripe listen --forward-to localhost:8787/stripe/webhook

# Trigger test event
stripe trigger customer.subscription.created
```

---

## Troubleshooting

### Secret Not Found Error

**Symptom:**
```
Error: TWILIO_AUTH_TOKEN is not defined
```

**Solution:**
```bash
# Verify secret exists
cd packages/server
pnpm wrangler secret list

# If missing, push it
pnpm wrangler secret put TWILIO_AUTH_TOKEN
```

### Invalid Twilio Signature

**Symptom:**
```
Invalid Twilio signature
```

**Causes:**
- Wrong `TWILIO_AUTH_TOKEN` secret
- Webhook URL doesn't match actual URL (http vs https)
- Request was modified in transit

**Solution:**
1. Verify auth token matches Twilio console
2. Ensure webhook URL is correct (no trailing slash)
3. Check Twilio webhook logs for actual URL used

### Database Connection Error

**Symptom:**
```
Failed to query database
```

**Solution:**
1. Verify Turso secrets:
   ```bash
   pnpm wrangler secret list
   ```
2. Test database connection:
   ```bash
   turso db show your-database
   ```
3. Check Turso auth token is still valid

### Worker Deployment Fails

**Symptom:**
```
Error: You are not authenticated
```

**Solution:**
```bash
cd packages/server
pnpm wrangler login
pnpm wrangler whoami  # Verify login
```

---

## Performance Optimization

### Caching Database Queries

Workers have no persistent state between requests. Use Turso's edge caching:

```javascript
// Already implemented in database.js
const db = createClient({
  url: env.TURSO_DATABASE_URL,
  authToken: env.TURSO_AUTH_TOKEN,
  // Turso handles edge caching automatically
});
```

### Minimize Cold Start Time

- Keep Worker bundle small (currently ~45 KB)
- Use ES modules (native to Workers)
- Avoid large dependencies

### Monitor CPU Time

Workers have 10ms CPU time limit per request (50ms for paid plan).

Check CPU usage in dashboard → Metrics. If approaching limit:
- Optimize database queries
- Reduce computation in webhook handlers
- Consider moving heavy work to async processing

---

## Costs

### Cloudflare Workers FREE Tier

- **100,000 requests/day** (3M/month)
- **No credit card required**
- **Unlimited Workers scripts**

**Estimated usage for xSwarm:**
```
Assumptions:
- 100 users
- Each user: 10 calls/month + 20 SMS/month
- Total: 3,000 requests/month

Cost: $0/month (well under free tier)
```

### Paid Plan ($5/month)

If you exceed 100k requests/day:
- **10 million requests included**
- **$0.50 per additional million**
- **50ms CPU time** (vs 10ms free)

---

## Security

### Webhook Signature Verification

All webhooks verify signatures:

**Twilio:** HMAC-SHA1 signature verification
**Stripe:** Webhook signature verification (via SDK)

Requests with invalid signatures are rejected with `403 Forbidden`.

### Secret Storage

Secrets are:
- Stored encrypted in Cloudflare infrastructure
- Never exposed in code or logs
- Accessible only to your Worker at runtime

### HTTPS Only

All Workers run on HTTPS only. HTTP requests are auto-upgraded.

### Whitelist Validation

Voice and SMS webhooks validate caller against user's registered phone number.

Unauthorized calls/SMS are rejected silently.

---

## Custom Domain (Optional)

Use your own domain instead of `*.workers.dev`:

1. Add domain to Cloudflare (free)
2. Workers → xswarm-webhooks → Settings → Triggers
3. Add custom domain: `webhooks.xswarm.ai`
4. Update Twilio and Stripe webhook URLs

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy Worker

on:
  push:
    branches: [main]
    paths:
      - 'packages/server/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: pnpm/action-setup@v2
      - run: pnpm install
      - run: pnpm deploy:server
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
```

---

## Rollback

If a deployment breaks production:

```bash
cd packages/server

# View deployment history
pnpm wrangler deployments list

# Rollback to previous deployment
pnpm wrangler rollback <deployment-id>
```

---

## Related Documentation

- [SUBSCRIPTION.md](./SUBSCRIPTION.md) - Subscription lifecycle
- [STRIPE_SETUP.md](./STRIPE_SETUP.md) - Stripe configuration
- [TWILIO_SETUP.md](./TWILIO_SETUP.md) - Twilio phone setup
- [MULTI_CHANNEL.md](./MULTI_CHANNEL.md) - Communication architecture

---

## Support

**Cloudflare Workers:**
- Docs: [developers.cloudflare.com/workers](https://developers.cloudflare.com/workers)
- Discord: [discord.gg/cloudflaredev](https://discord.gg/cloudflaredev)

**xSwarm Issues:**
- GitHub: [github.com/xswarm-dev/xswarm-boss/issues](https://github.com/xswarm-dev/xswarm-boss/issues)

---

**Next:** Configure Turso database schema and deploy your Worker!
