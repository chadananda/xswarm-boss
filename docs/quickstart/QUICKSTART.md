# Boss AI - Quick Start

Get Boss AI running in 3 commands.

## Prerequisites

- Node.js 18+
- pnpm (`npm install -g pnpm`)
- Cloudflare account (free tier)

## Setup

### 1. Install

```bash
pnpm install
```

### 2. Configure

```bash
pnpm run setup:env
```

Follow the prompts to add your API keys.

### 3. Deploy

```bash
pnpm run deploy
```

That's it! 🎉

## What You Get

- **SMS Interface** - Text your Boss AI
- **Email Interface** - Email your Boss AI
- **Voice Interface** - Call your Boss AI
- **CLI Interface** - Command line access
- **Calendar** - Schedule and reminders
- **Projects** - Task management
- **Simple Database** - 4 tables, easy to understand

## Usage

### Send a Message (CLI)

```bash
cargo run -- "What's on my calendar?"
```

### Send a Text (SMS)

Text to your Twilio number:
```
Remind me to call mom at 3pm
```

### Send an Email

Email to your inbound address with any request.

## Configuration Files

- `wrangler.toml` - Deployment config (unified, simple)
- `config.toml` - Project settings (safe to commit)
- `.env` - Secrets (never commit)

## Simple Architecture

```
User Message (SMS/Email/CLI)
    ↓
Cloudflare Worker (Router)
    ↓
Unified Message Handler
    ↓
Claude AI (Processing)
    ↓
Response + Database Update
    ↓
Send Reply (Same Channel)
```

## Database Schema (4 Tables)

```sql
users      - Who can talk to Boss
events     - Calendar appointments
reminders  - Notifications
messages   - Conversation history
```

## Common Commands

```bash
# Development
pnpm dev:server              # Start local server
pnpm dev:webhooks            # Forward webhooks to local

# Testing
pnpm test                    # Run all tests
pnpm test:webhooks           # Test webhooks
pnpm test:e2e:sms            # Test SMS flow
pnpm test:e2e:email          # Test email flow

# Deployment
pnpm run deploy              # Deploy to production
pnpm run deploy:dev          # Deploy to dev environment
pnpm run deploy:staging      # Deploy to staging

# Database
pnpm run setup:db            # Initialize database
node scripts/migrate-db.js   # Apply migrations

# Secrets
pnpm run setup:secrets       # Sync .env to Cloudflare
pnpm run setup:webhooks      # Setup Stripe webhooks
pnpm run setup:twilio        # Setup Twilio webhooks
pnpm run setup:sendgrid      # Setup SendGrid inbound

# Logs
wrangler tail                # Stream live logs
```

## File Structure

```
xswarm-boss/
├── wrangler.toml            # Unified deployment config
├── config.toml              # Project settings
├── .env                     # Your secrets (gitignored)
├── deploy.sh                # One-command deployment
├── packages/
│   ├── server/              # Cloudflare Worker
│   │   ├── src/
│   │   │   ├── index.js     # Router
│   │   │   ├── routes/      # API endpoints
│   │   │   └── lib/         # Utilities
│   │   └── migrations/
│   │       └── schema.sql   # Database schema
│   └── core/                # Rust CLI
└── scripts/
    ├── setup-env.js         # Environment setup
    └── migrate-db.js        # Database migration
```

## Environment Variables

Required in `.env`:

```env
# AI
ANTHROPIC_API_KEY=sk-ant-xxxxx...
OPENAI_API_KEY=sk-xxxxx...

# Communication
TWILIO_AUTH_TOKEN=xxxxx...
SENDGRID_API_KEY=SG.xxxxx...

# Payments
STRIPE_SECRET_KEY=sk_test_xxxxx...
STRIPE_WEBHOOK_SECRET=whsec_xxxxx...

# Database
TURSO_DATABASE_URL=libsql://xxxxx...
TURSO_AUTH_TOKEN=eyJhbGci...

# Storage
S3_ACCESS_KEY_ID=xxxxx...
S3_SECRET_ACCESS_KEY=xxxxx...

# Deployment
CLOUDFLARE_API_TOKEN=xxxxx...
```

## Troubleshooting

### "Authentication error" during deploy

```bash
# Check your Cloudflare API token
echo $CLOUDFLARE_API_TOKEN

# If missing, add to .env and re-sync
pnpm run setup:secrets
```

### Webhooks not working

```bash
# Re-setup webhooks
pnpm run setup:twilio
pnpm run setup:sendgrid

# Check webhook URLs in respective dashboards
```

### Database connection fails

```bash
# Verify credentials
echo $TURSO_DATABASE_URL
echo $TURSO_AUTH_TOKEN

# Re-run migration
node scripts/migrate-db.js
```

## Next Steps

1. **Read docs/deployment/DEPLOYMENT.md** - Full deployment guide
2. **Check examples** - Look at `scripts/test-*.js`
3. **Customize** - Edit `config.toml` for your needs
4. **Monitor** - Run `wrangler tail` to see logs

## Philosophy

Boss AI is built on simplicity:

- **One config file** for deployment
- **One command** to deploy
- **One database schema** (4 tables)
- **One API style** (REST)
- **One message handler** (unified)

Everything is designed to be easy to understand, easy to modify, and easy to maintain.

## Documentation

- `docs/deployment/DEPLOYMENT.md` - Comprehensive deployment guide
- `planning/` - Architecture and design docs
- `packages/server/README.md` - API documentation
- `packages/core/README.md` - CLI documentation

## Support

- **Issues:** GitHub Issues
- **Docs:** Check `planning/` folder
- **Examples:** Look at `scripts/test-*.js`
- **Logs:** `wrangler tail`

---

**Ready to deploy?** Run: `pnpm run deploy`
