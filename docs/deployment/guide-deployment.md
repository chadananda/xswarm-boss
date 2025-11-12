# Boss AI - Simple Deployment Guide

This guide will help you deploy Boss AI in under 10 minutes.

## Philosophy

Boss AI uses a **simple, unified deployment approach**:
- **One configuration file** - `wrangler.toml` for everything
- **One command deployment** - `./deploy.sh` does it all
- **One database schema** - 4 simple tables
- **One API style** - Consistent REST endpoints

## Prerequisites

Before you start, make sure you have:

- **Node.js 18+** - [Download here](https://nodejs.org/)
- **pnpm** - Run: `npm install -g pnpm`
- **Rust (optional)** - For the CLI client: [Install here](https://rustup.rs/)
- **Cloudflare Account** - Free tier works: [Sign up](https://dash.cloudflare.com/)

## Quick Start (10 Minutes)

### Step 1: Clone and Install (2 minutes)

```bash
# Clone the repository
git clone https://github.com/yourusername/xswarm-boss.git
cd xswarm-boss

# Install dependencies
pnpm install
```

### Step 2: Configure Environment (3 minutes)

```bash
# Run the interactive setup script
node scripts/setup-env.js
```

This will guide you through setting up your API keys. You'll need:

1. **Anthropic API Key** - Get from [console.anthropic.com](https://console.anthropic.com/)
2. **OpenAI API Key** - Get from [platform.openai.com](https://platform.openai.com/)
3. **Twilio Credentials** - Get from [console.twilio.com](https://console.twilio.com/)
4. **SendGrid API Key** - Get from [sendgrid.com](https://sendgrid.com/)
5. **Stripe API Keys** - Get from [dashboard.stripe.com](https://dashboard.stripe.com/)
6. **Turso Database** - Get from [turso.tech](https://turso.tech/)
7. **Cloudflare R2** - Get from [dash.cloudflare.com](https://dash.cloudflare.com/)

**Tip:** You can skip production keys and add them later.

### Step 3: Deploy (5 minutes)

```bash
# One command does everything!
./deploy.sh
```

This script will:
1. ✅ Check prerequisites
2. ✅ Install dependencies
3. ✅ Build Rust CLI (if Cargo available)
4. ✅ Setup database with simple schema
5. ✅ Sync secrets to Cloudflare
6. ✅ Deploy to Cloudflare Workers
7. ✅ Setup webhooks
8. ✅ Verify deployment

### Step 4: Verify Deployment (1 minute)

```bash
# Test the health endpoint
curl https://boss-ai.YOUR-SUBDOMAIN.workers.dev/health

# Should return:
# {"status":"ok","service":"xswarm-webhooks","timestamp":"2024-10-29T..."}
```

🎉 **Done!** Your Boss AI is now live.

## What Just Happened?

The deployment script set up:

### 1. Database (4 Simple Tables)

```
users      - Who can talk to Boss
events     - Calendar appointments
reminders  - Notifications to send
messages   - Conversation history
```

Schema is in: `packages/server/migrations/schema.sql`

### 2. Cloudflare Worker (API + Webhooks)

```
/health              - Health check
/api/message         - Send message (CLI/API)
/sms/inbound         - Receive SMS (Twilio)
/email/inbound       - Receive Email (SendGrid)
/voice/inbound       - Receive Calls (Twilio)
/api/calendar/*      - Calendar API
/api/projects/*      - Project management
```

### 3. R2 Storage (Assets & Backups)

Single bucket with organized prefixes:
```
xswarm-boss/
  ├── assets/       - User uploads
  ├── backups/      - Database backups
  └── lfs/objects/  - Git LFS files
```

### 4. Secrets Management

Secrets are stored securely in Cloudflare Workers using `wrangler secret`.
Never committed to git. Never exposed in code.

## Using Boss AI

### Via CLI (Rust)

```bash
# Send a message to Boss
cargo run -- "What's on my calendar today?"

# Start voice conversation
cargo run -- --voice

# Get help
cargo run -- --help
```

### Via SMS

Send a text to your Twilio number:
```
"Remind me to call mom at 3pm tomorrow"
```

### Via Email

Send an email to your inbound address:
```
To: yourboss@inbound.sendgrid.net
Subject: Project Update

Hey Boss, here's the status update...
```

### Via API

```bash
curl -X POST https://boss-ai.YOUR-SUBDOMAIN.workers.dev/api/message \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "content": "What'\''s on my calendar today?",
    "channel": "api"
  }'
```

## Simple Configuration

### Environment Variables (`.env`)

These are **secrets** (never commit):
```env
ANTHROPIC_API_KEY=sk-ant-xxxxx...
OPENAI_API_KEY=sk-xxxxx...
TWILIO_AUTH_TOKEN=xxxxx...
SENDGRID_API_KEY=SG.xxxxx...
STRIPE_SECRET_KEY=sk_test_xxxxx...
TURSO_AUTH_TOKEN=eyJhbGci...
```

### Project Config (`config.toml`)

These are **settings** (safe to commit):
```toml
[server]
host = "localhost"
port = 8787

[twilio]
account_sid = "ACxxxxx..."

[stripe.prices]
premium = "price_xxxxx..."
voice = "price_xxxxx..."
```

### Worker Config (`wrangler.toml`)

This is **deployment config** (safe to commit):
```toml
name = "boss-ai"
account_id = "your_account_id"

[[r2_buckets]]
binding = "R2_BUCKET"
bucket_name = "xswarm-boss"
```

## Common Tasks

### Update Secrets

```bash
# Sync all secrets from .env to Cloudflare
pnpm run setup:secrets

# Or update one secret manually
wrangler secret put ANTHROPIC_API_KEY
```

### Update Database Schema

```bash
# Reset database and apply new schema
pnpm --filter @xswarm/server run db:reset
```

### Setup Webhooks

```bash
# Setup Stripe webhooks
pnpm run setup:webhooks

# Setup Twilio webhooks
pnpm run setup:twilio

# Setup SendGrid inbound email
pnpm run setup:sendgrid
```

### View Logs

```bash
# Stream live logs from Cloudflare Workers
wrangler tail

# Or view in dashboard
open https://dash.cloudflare.com/
```

### Test Everything

```bash
# Test all webhooks
pnpm run test:webhooks

# Test specific channels
pnpm run test:e2e:sms
pnpm run test:e2e:email
pnpm run test:e2e:voice
```

## Troubleshooting

### Deployment fails with "Authentication error"

**Problem:** Cloudflare API token is missing or invalid.

**Solution:**
```bash
# Get a new API token from Cloudflare dashboard
# Permissions needed: Workers Scripts:Edit

# Add to .env
CLOUDFLARE_API_TOKEN=your_new_token

# Sync to Cloudflare
pnpm run setup:secrets
```

### SMS/Email not working

**Problem:** Webhooks not configured correctly.

**Solution:**
```bash
# Re-run webhook setup
pnpm run setup:twilio
pnpm run setup:sendgrid

# Verify webhooks are set
# Check Twilio Console: https://console.twilio.com/
# Check SendGrid Inbound Parse: https://app.sendgrid.com/settings/parse
```

### Database connection fails

**Problem:** Turso auth token expired or database URL wrong.

**Solution:**
```bash
# Get new auth token from Turso
turso db tokens create your-database

# Update .env
TURSO_AUTH_TOKEN=new_token_here

# Sync to Cloudflare
pnpm run setup:secrets
```

### "Module not found" errors

**Problem:** Dependencies not installed or build failed.

**Solution:**
```bash
# Clean install
pnpm clean
pnpm install
pnpm build
```

## Development Workflow

### Local Development

```bash
# Start local server (port 8787)
pnpm dev:server

# In another terminal, forward webhooks
pnpm dev:webhooks

# Test locally
curl http://localhost:8787/health
```

### Test Before Deploy

```bash
# Run all tests
pnpm test

# Test database
pnpm --filter @xswarm/server run test:db

# Test webhooks
pnpm run test:webhooks
```

### Deploy to Production

```bash
# Deploy everything
./deploy.sh production

# Or just deploy the worker
pnpm deploy:server
```

## Project Structure

```
xswarm-boss/
├── wrangler.toml           # Unified deployment config
├── config.toml             # Project settings
├── .env                    # Secrets (gitignored)
├── deploy.sh               # One-command deployment
├── packages/
│   ├── server/             # Cloudflare Worker
│   │   ├── src/
│   │   │   ├── index.js    # Main router
│   │   │   ├── routes/     # API endpoints
│   │   │   └── lib/        # Utilities
│   │   └── migrations/
│   │       └── schema.sql  # Simple database schema
│   └── core/               # Rust CLI client
│       └── src/
│           ├── main.rs     # CLI entry point
│           └── ai.rs       # AI integration
└── scripts/
    ├── setup-env.js        # Environment setup
    └── setup-*.js          # Setup scripts
```

## Next Steps

Now that Boss AI is deployed:

1. **Add your first user** - Update `config.toml` with your phone/email
2. **Send a test message** - Try SMS, email, or CLI
3. **Configure calendar** - Set up appointments and reminders
4. **Customize persona** - Edit `packages/personas/boss/`
5. **Monitor usage** - Check Cloudflare dashboard for metrics

## Getting Help

- **Documentation:** Check files in `planning/` folder
- **Examples:** Look at test scripts in `scripts/test-*.js`
- **Issues:** Open an issue on GitHub
- **Logs:** Run `wrangler tail` to see live logs

## Advanced Configuration

### Multiple Environments

You can deploy to different environments:

```bash
./deploy.sh dev        # Development
./deploy.sh staging    # Staging
./deploy.sh production # Production (default)
```

Each environment uses the same `wrangler.toml` but different secrets.

### Custom Domain

Add a custom domain in `wrangler.toml`:

```toml
[env.production]
routes = [
  { pattern = "boss.yourdomain.com", custom_domain = true }
]
```

Then deploy:
```bash
./deploy.sh production
```

### Database Backups

Automatic backups are configured in `config.toml`:

```toml
[turso.backup]
enabled = true
retention_days = 30
```

Manual backup:
```bash
turso db backup your-database
```

## Security Best Practices

1. **Never commit `.env`** - Always in `.gitignore`
2. **Rotate secrets regularly** - Use `pnpm run setup:secrets`
3. **Use test keys in dev** - Only live keys in production
4. **Verify webhook signatures** - Already implemented in routes
5. **Limit API access** - Use authentication tokens

## Cost Estimate

Boss AI uses free tiers where possible:

- **Cloudflare Workers:** 100,000 requests/day free
- **Cloudflare R2:** 10 GB storage free
- **Turso Database:** 9 GB storage free
- **Twilio:** Pay as you go (~$0.0075/SMS, ~$0.013/min voice)
- **SendGrid:** 100 emails/day free
- **Stripe:** 2.9% + $0.30 per transaction

Estimated cost for personal use: **$0-10/month**

## Conclusion

You now have a fully deployed Boss AI system that can:
- ✅ Receive SMS messages
- ✅ Receive emails
- ✅ Handle voice calls
- ✅ Manage your calendar
- ✅ Track projects
- ✅ Send reminders
- ✅ Process payments

All with a simple, unified configuration! 🎉

---

**Need help?** Open an issue or check the planning docs in `planning/`.
