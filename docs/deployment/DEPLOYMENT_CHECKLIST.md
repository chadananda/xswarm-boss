# Boss AI - Deployment Checklist

Quick checklist to ensure successful deployment.

## Pre-Deployment

- [ ] Node.js 18+ installed
- [ ] pnpm installed (`npm install -g pnpm`)
- [ ] Git repository cloned
- [ ] Dependencies installed (`pnpm install`)

## Get API Keys

- [ ] **Anthropic** - [console.anthropic.com](https://console.anthropic.com/)
- [ ] **OpenAI** - [platform.openai.com](https://platform.openai.com/)
- [ ] **Twilio** - [console.twilio.com](https://console.twilio.com/)
- [ ] **SendGrid** - [sendgrid.com](https://sendgrid.com/)
- [ ] **Stripe** - [dashboard.stripe.com](https://dashboard.stripe.com/)
- [ ] **Turso** - [turso.tech](https://turso.tech/)
- [ ] **Cloudflare** - [dash.cloudflare.com](https://dash.cloudflare.com/)

## Configuration

- [ ] Run `pnpm run setup:env`
- [ ] Add all required API keys
- [ ] Verify `.env` file created
- [ ] Check `config.toml` settings
- [ ] Review `wrangler.toml` config

## Database Setup

- [ ] Turso database created
- [ ] Database URL in `.env`
- [ ] Auth token in `.env`
- [ ] Run `pnpm run setup:db`
- [ ] Verify tables created

## Deployment

- [ ] Run `./deploy.sh`
- [ ] Check for errors in output
- [ ] Note the Worker URL
- [ ] Verify health endpoint works

## Webhooks Setup

- [ ] Stripe webhooks configured
- [ ] Twilio SMS webhook set
- [ ] Twilio voice webhook set
- [ ] SendGrid inbound parse set

## Testing

- [ ] Health check: `curl <worker-url>/health`
- [ ] Send test SMS
- [ ] Send test email
- [ ] Test CLI: `cargo run -- "test"`
- [ ] Check logs: `wrangler tail`

## Post-Deployment

- [ ] Verify all channels working
- [ ] Set up monitoring
- [ ] Configure alerts
- [ ] Update documentation
- [ ] Notify team

## Troubleshooting

If something fails:

1. Check logs: `wrangler tail`
2. Verify secrets: `wrangler secret list`
3. Re-run setup: `pnpm run setup:secrets`
4. Check docs: `docs/deployment/DEPLOYMENT.md`

## Quick Commands

```bash
# Setup
pnpm run setup:env
pnpm run setup:db

# Deploy
pnpm run deploy

# Verify
curl https://boss-ai.workers.dev/health
wrangler tail

# Update
pnpm run setup:secrets
pnpm run deploy
```

## Success Criteria

✅ Worker deployed
✅ Health endpoint returns 200
✅ Database tables created
✅ Webhooks configured
✅ Test messages work
✅ No errors in logs

---

**All done?** Start using Boss AI! 🎉
