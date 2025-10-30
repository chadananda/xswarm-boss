# xSwarm Boss - Production Deployment Guide

Complete guide for deploying xSwarm Boss to production.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Database Migration](#database-migration)
4. [Deployment Process](#deployment-process)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Rollback Procedures](#rollback-procedures)
7. [Monitoring Setup](#monitoring-setup)
8. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

Before deploying to production, ensure you have:

### Required Accounts & Services

- [ ] Cloudflare account with Workers enabled
- [ ] Turso database (production instance)
- [ ] Anthropic API account (Claude)
- [ ] OpenAI API account
- [ ] Stripe account (live mode enabled)
- [ ] SendGrid account (verified domain)
- [ ] Twilio account (live credentials)
- [ ] Domain configured (DNS pointing to Cloudflare)

### Required Credentials

Run the pre-deployment check to verify all credentials:

```bash
node deployment/scripts/pre-deploy-check.js --env=production
```

This will verify:
- All API keys are configured
- Database connectivity
- Cloudflare Workers setup
- Webhook configurations
- DNS settings

### Code Preparation

- [ ] All tests passing: `pnpm test`
- [ ] Code reviewed and approved
- [ ] Database migrations tested in staging
- [ ] No pending TODO or FIXME items
- [ ] Security audit completed
- [ ] Performance testing completed

---

## Environment Setup

### 1. Configure Production Environment

Copy the production environment template:

```bash
cp deployment/config/production.env.example .env.production
```

Fill in all required values in `.env.production`:

```env
# Critical: Use LIVE keys only for production!
ENVIRONMENT=production
ANTHROPIC_API_KEY=sk-ant-xxxxx...
STRIPE_SECRET_KEY_LIVE=sk_live_xxxxx...
TWILIO_AUTH_TOKEN_LIVE=xxxxx...
SENDGRID_API_KEY_LIVE=SG.xxxxx...
TURSO_DATABASE_URL=libsql://xswarm-production.turso.io
TURSO_AUTH_TOKEN=eyJxxxx...
JWT_SECRET=<generate_secure_random_string>
```

### 2. Generate JWT Secret

```bash
openssl rand -base64 64
```

Copy the output to `JWT_SECRET` in your `.env.production` file.

### 3. Sync Secrets to Cloudflare

```bash
pnpm run setup:secrets
```

This will push all secrets from `.env.production` to Cloudflare Workers.

---

## Database Migration

### 1. Create Database Backup

Before any production changes, create a backup:

```bash
# Manual backup via Turso CLI
turso db shell xswarm-production ".backup backup-$(date +%Y%m%d).db"

# Or let the deployment script handle it automatically
```

### 2. Test Migrations in Staging

Always test migrations in staging first:

```bash
# Switch to staging environment
cp .env.staging .env

# Run migrations
node deployment/scripts/migrate-all.js

# Verify
node deployment/scripts/verify-deployment.js --env=staging
```

### 3. Run Production Migrations

```bash
# Switch to production environment
cp .env.production .env

# Dry run first (to see what will happen)
node deployment/scripts/migrate-all.js --dry-run

# Run actual migrations
node deployment/scripts/migrate-all.js
```

---

## Deployment Process

### Automated Deployment (Recommended)

The easiest way to deploy is using the automated deployment script:

```bash
# Full production deployment
node deployment/scripts/deploy-production.js --env=production
```

This script will:
1. Run pre-deployment checks
2. Create database backup
3. Run database migrations
4. Sync secrets to Cloudflare
5. Deploy Cloudflare Workers
6. Deploy static pages
7. Configure webhooks
8. Run post-deployment verification
9. Send deployment notification

### Manual Deployment

If you prefer to deploy step-by-step:

```bash
# 1. Pre-deployment checks
node deployment/scripts/pre-deploy-check.js --env=production

# 2. Database migrations
node deployment/scripts/migrate-all.js

# 3. Deploy Cloudflare Workers
pnpm run deploy:server

# 4. Deploy static pages
pnpm run deploy:pages

# 5. Configure webhooks
pnpm run setup:webhooks
pnpm run setup:twilio

# 6. Verify deployment
node deployment/scripts/verify-deployment.js --env=production
```

### Blue-Green Deployment (Advanced)

For zero-downtime deployment:

1. Deploy to a new worker version
2. Test the new version
3. Switch traffic gradually
4. Monitor for issues
5. Rollback if needed

```bash
# Deploy new version
wrangler publish --name boss-ai-v2

# Test new version
curl https://boss-ai-v2.workers.dev/health

# Switch traffic (using Cloudflare dashboard or API)

# Monitor metrics
node deployment/monitoring/metrics.js
```

---

## Post-Deployment Verification

### Automated Verification

Run the comprehensive verification script:

```bash
# Full verification
node deployment/scripts/verify-deployment.js --env=production

# Quick checks only
node deployment/scripts/verify-deployment.js --env=production --quick
```

### Manual Verification

Test critical flows manually:

#### 1. Health Checks

```bash
curl https://boss-ai.workers.dev/health
curl https://boss-ai.workers.dev/health/ready
curl https://boss-ai.workers.dev/health/detailed
```

#### 2. Authentication Flow

```bash
# Signup
curl -X POST https://boss-ai.workers.dev/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","name":"Test User"}'

# Login
curl -X POST https://boss-ai.workers.dev/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

#### 3. Webhook Endpoints

```bash
# Test Stripe webhook endpoint exists
curl -X POST https://boss-ai.workers.dev/stripe/webhook \
  -H "Content-Type: application/json" \
  -d '{}'

# Should return 400 or 401 (endpoint exists but rejects invalid signature)
```

#### 4. Database Connectivity

```bash
# Check database tables
turso db shell xswarm-production "SELECT name FROM sqlite_master WHERE type='table';"

# Check migration status
turso db shell xswarm-production "SELECT * FROM _migrations ORDER BY applied_at DESC LIMIT 5;"
```

### Monitoring Dashboard

After deployment, monitor these metrics for 24-48 hours:

- **Error Rate**: Should be < 1%
- **Response Time**: P95 < 500ms, P99 < 1000ms
- **Database Performance**: P95 < 100ms
- **User Signups**: Track new user registrations
- **Payment Success Rate**: Should be > 95%

Access metrics:
```bash
curl https://boss-ai.workers.dev/api/metrics \
  -H "Authorization: Bearer <admin-token>"
```

---

## Rollback Procedures

### When to Rollback

Rollback if you see:
- Error rate > 5%
- Critical functionality broken
- Database corruption
- Security vulnerability exposed
- Payment processing fails

### Automatic Rollback

The deployment script will automatically rollback if:
- Pre-deployment checks fail
- Database migration fails
- Worker deployment fails
- Post-deployment verification fails

### Manual Rollback

#### 1. List Available Versions

```bash
node deployment/scripts/rollback.js --list
```

#### 2. Rollback Worker Only

```bash
# Rollback to specific version
node deployment/scripts/rollback.js --version=<deployment-id>

# Or use wrangler directly
wrangler rollback --name boss-ai
```

#### 3. Rollback Database

```bash
# List available backups
node deployment/scripts/rollback.js --list

# Restore from specific backup
node deployment/scripts/rollback.js --restore-db=.backups/backup-20241029.sql
```

#### 4. Complete Rollback

```bash
# Rollback both worker and database
node deployment/scripts/rollback.js \
  --version=<deployment-id> \
  --restore-db=.backups/backup-20241029.sql
```

#### 5. Verify Rollback

```bash
node deployment/scripts/verify-deployment.js --env=production --quick
```

### Emergency Rollback

For critical issues requiring immediate rollback:

```bash
# 1. Disable new traffic
wrangler publish --name boss-ai-maintenance --config wrangler.maintenance.toml

# 2. Rollback to last known good version
wrangler rollback --name boss-ai

# 3. Verify health
curl https://boss-ai.workers.dev/health/detailed

# 4. Re-enable traffic
# (automatic after rollback completes)
```

---

## Monitoring Setup

### Set Up Alerts

Configure alerting in `.env.production`:

```env
# Email alerts
ADMIN_EMAIL=admin@xswarm.ai

# SMS alerts (critical only)
ADMIN_PHONE=+1234567890

# Slack alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxxxx
```

### Alert Thresholds

Default thresholds (configurable in `deployment/monitoring/alerts.js`):

- Error Rate: > 5%
- Response Time: P95 > 2000ms
- Database Query Time: P95 > 5000ms

### Health Check Integration

Set up external monitoring (UptimeRobot, Pingdom, etc.) to monitor:

- `https://boss-ai.workers.dev/health` - Every 1 minute
- `https://boss-ai.workers.dev/health/ready` - Every 5 minutes

### Log Aggregation

View real-time logs:

```bash
# Worker logs
wrangler tail

# With filtering
wrangler tail --format pretty | grep ERROR
```

---

## Troubleshooting

### Common Issues

#### 1. "Database connection failed"

**Cause**: Invalid Turso credentials or network issue

**Solution**:
```bash
# Test connection
turso db shell xswarm-production

# Regenerate token
turso db tokens create xswarm-production

# Update secret
wrangler secret put TURSO_AUTH_TOKEN
```

#### 2. "Webhook signature verification failed"

**Cause**: Outdated webhook secret

**Solution**:
```bash
# Regenerate webhook secrets
pnpm run setup:webhooks

# Verify in Stripe dashboard
stripe listen --forward-to https://boss-ai.workers.dev/stripe/webhook
```

#### 3. "API rate limit exceeded"

**Cause**: Too many requests to external API

**Solution**:
- Check rate limiting configuration
- Review recent usage spike
- Consider caching strategies
- Contact API provider for limit increase

#### 4. "High memory usage"

**Cause**: Memory leak or inefficient queries

**Solution**:
```bash
# Check slow queries
turso db shell xswarm-production "SELECT * FROM _migrations WHERE execution_time_ms > 1000;"

# Review worker metrics
wrangler tail | grep "exceeded"
```

### Getting Help

If you encounter issues:

1. Check logs: `wrangler tail`
2. Review metrics: Access `/api/metrics` endpoint
3. Check health: `curl https://boss-ai.workers.dev/health/detailed`
4. Review recent changes: `git log -10 --oneline`
5. Contact support: hello@xswarm.dev

---

## Success Criteria

Deployment is successful when:

- ✅ All pre-deployment checks pass
- ✅ Database migrations complete without errors
- ✅ Worker deploys successfully
- ✅ All health checks return 200 OK
- ✅ Authentication flow works
- ✅ Webhooks are properly configured
- ✅ Error rate < 1% for 1 hour post-deployment
- ✅ Response time P95 < 500ms
- ✅ No critical alerts triggered

---

## Next Steps

After successful deployment:

1. Monitor for 24-48 hours
2. Review error logs daily
3. Check business metrics (signups, revenue)
4. Gather user feedback
5. Plan next release

---

**Last Updated**: 2025-10-29
**Version**: 1.0.0
