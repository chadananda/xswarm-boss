# xSwarm Boss - Deployment System

Production-ready deployment and monitoring infrastructure.

## Quick Start

### Deploy to Production

```bash
# 1. Check prerequisites
pnpm run deploy:check

# 2. Deploy (automated)
pnpm run deploy:prod

# 3. Verify
pnpm run deploy:verify
```

### Rollback

```bash
# List available versions
pnpm run deploy:list

# Rollback
pnpm run deploy:rollback --version=<id>
```

## Directory Structure

```
deployment/
├── scripts/         # Deployment automation scripts
├── monitoring/      # Health checks, metrics, alerts
├── config/          # Environment configuration templates
└── docs/            # Comprehensive documentation
```

## Documentation

- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Complete deployment procedures
- **[Monitoring Setup](docs/MONITORING_SETUP.md)** - Monitoring and alerting setup
- **[System Summary](DEPLOYMENT_SYSTEM_SUMMARY.md)** - Overview of entire system

## Key Scripts

### Deployment
- `pre-deploy-check.js` - Verify prerequisites before deploying
- `migrate-all.js` - Database migration orchestrator
- `deploy-production.js` - Automated production deployment
- `verify-deployment.js` - Post-deployment verification
- `rollback.js` - Automated rollback

### Monitoring
- `health-checks.js` - Health check endpoints
- `metrics.js` - Metrics collection system
- `alerts.js` - Multi-channel alerting

## NPM Scripts

```bash
pnpm run deploy:check      # Pre-deployment verification
pnpm run deploy:migrate    # Database migrations
pnpm run deploy:prod       # Full production deployment
pnpm run deploy:verify     # Post-deployment verification
pnpm run deploy:list       # List rollback points
pnpm run deploy:rollback   # Rollback deployment
```

## Health Check Endpoints

```bash
# Basic health
curl https://boss-ai.workers.dev/health

# Readiness check
curl https://boss-ai.workers.dev/health/ready

# Liveness check
curl https://boss-ai.workers.dev/health/live

# Detailed diagnostics
curl https://boss-ai.workers.dev/health/detailed
```

## Features

✅ Automated deployment with verification
✅ Comprehensive health checks
✅ Real-time metrics collection
✅ Multi-channel alerting (Email, SMS, Slack)
✅ Automated rollback capabilities
✅ Database migration tracking
✅ Structured logging
✅ Performance monitoring
✅ Business KPI tracking

## Environment Configuration

Copy and configure environment templates:

```bash
cp deployment/config/production.env.example .env.production
cp deployment/config/staging.env.example .env.staging
```

Fill in all required secrets and configuration values.

## Monitoring

### Key Metrics
- Response Time: P95 < 500ms
- Error Rate: < 1%
- Database Queries: P95 < 100ms
- Uptime: > 99.9%

### Alerts
Configure in environment:
```env
ADMIN_EMAIL=admin@xswarm.ai
ADMIN_PHONE=+1234567890
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxxxx
```

## Troubleshooting

Check logs:
```bash
wrangler tail
```

View metrics:
```bash
curl https://boss-ai.workers.dev/api/metrics
```

Check health:
```bash
curl https://boss-ai.workers.dev/health/detailed
```

## Support

- **Documentation**: See `docs/` directory
- **Email**: hello@xswarm.dev
- **GitHub**: https://github.com/xswarm-dev/xswarm-boss

---

**Status**: Production Ready ✅
**Version**: 1.0.0
