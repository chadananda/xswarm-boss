# xSwarm Boss - Monitoring Setup Guide

Complete guide for setting up monitoring, metrics, and alerting for xSwarm Boss.

## Table of Contents

1. [Overview](#overview)
2. [Health Checks](#health-checks)
3. [Metrics Collection](#metrics-collection)
4. [Alerting System](#alerting-system)
5. [Dashboard Setup](#dashboard-setup)
6. [Log Management](#log-management)
7. [Performance Monitoring](#performance-monitoring)
8. [Business Metrics](#business-metrics)

---

## Overview

xSwarm Boss includes a comprehensive monitoring system with:

- **Health Checks**: Multiple endpoints for different health aspects
- **Metrics Collection**: Performance and business metrics
- **Alerting**: Multi-channel alerts (email, SMS, Slack)
- **Logging**: Structured logging with correlation IDs
- **Dashboards**: Real-time visualization (via external tools)

### Architecture

```
┌─────────────────┐
│ Cloudflare      │
│ Workers         │
│  - Health API   │
│  - Metrics API  │
│  - Logs         │
└────────┬────────┘
         │
         ├─────────────► Health Checks (External Monitoring)
         ├─────────────► Metrics Storage (Cloudflare Analytics)
         ├─────────────► Alert Manager (SendGrid/Twilio/Slack)
         └─────────────► Log Aggregation (Cloudflare Logs)
```

---

## Health Checks

### Available Endpoints

#### 1. Basic Health Check
**Endpoint**: `GET /health`
**Purpose**: Quick check if worker is responding
**Response Time**: < 50ms

```bash
curl https://boss-ai.workers.dev/health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2024-10-29T12:00:00Z",
  "service": "xswarm-boss",
  "version": "1.0.0"
}
```

#### 2. Readiness Check
**Endpoint**: `GET /health/ready`
**Purpose**: Check if all dependencies are ready
**Response Time**: < 200ms

```bash
curl https://boss-ai.workers.dev/health/ready
```

Response:
```json
{
  "ready": true,
  "timestamp": "2024-10-29T12:00:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "responseTime": 45
    },
    "r2_storage": {
      "status": "healthy",
      "responseTime": 23
    }
  }
}
```

#### 3. Liveness Check
**Endpoint**: `GET /health/live`
**Purpose**: Verify worker is processing requests
**Response Time**: < 50ms

```bash
curl https://boss-ai.workers.dev/health/live
```

#### 4. Detailed Health Check
**Endpoint**: `GET /health/detailed`
**Purpose**: Comprehensive diagnostic information
**Response Time**: < 500ms

```bash
curl https://boss-ai.workers.dev/health/detailed
```

Response includes:
- Overall health status
- Database connectivity
- External API status (Anthropic, Stripe, SendGrid, Twilio)
- R2 storage status
- System metrics
- Performance metrics

### External Monitoring Setup

#### UptimeRobot

1. Create account at [uptimerobot.com](https://uptimerobot.com)
2. Add monitors:
   - **Basic Health**: `/health` every 1 minute
   - **Readiness**: `/health/ready` every 5 minutes
   - **API Test**: `/api/health` every 5 minutes

#### Pingdom

1. Create account at [pingdom.com](https://pingdom.com)
2. Configure checks:
   - HTTP check on `/health`
   - Transaction check for signup flow
   - API monitoring for key endpoints

#### Cloudflare Health Checks

Configure in Cloudflare dashboard:
1. Go to Traffic → Health Checks
2. Add health check:
   - URL: `https://boss-ai.workers.dev/health`
   - Interval: 60 seconds
   - Expected status: 200

---

## Metrics Collection

### Automatic Metrics

The metrics system automatically tracks:

- **Request Metrics**:
  - Total requests
  - Requests per endpoint
  - Response times (avg, p50, p95, p99)
  - Error rates
  - Status code distribution

- **Database Metrics**:
  - Query count
  - Query duration
  - Slow queries (> 1s)
  - Connection errors

- **Business Metrics**:
  - User signups
  - Subscription upgrades
  - Payment successes/failures
  - API usage by customer

### Accessing Metrics

#### Real-time Metrics API

```bash
curl https://boss-ai.workers.dev/api/metrics \
  -H "Authorization: Bearer <admin-token>"
```

Response:
```json
{
  "timestamp": "2024-10-29T12:00:00Z",
  "uptime": 86400000,
  "requests": {
    "count": 15234,
    "avgResponseTime": 156,
    "p95ResponseTime": 423,
    "successRate": 99.2,
    "errorRate": 0.8
  },
  "database": {
    "count": 8421,
    "avgDuration": 45,
    "slowQueries": 3
  }
}
```

#### Cloudflare Analytics

View metrics in Cloudflare dashboard:
1. Go to Workers → boss-ai → Metrics
2. See:
   - Requests per second
   - CPU time
   - Duration
   - Errors

#### Custom Metrics Integration

Integrate with your metrics system:

```javascript
import { MetricsCollector } from './deployment/monitoring/metrics.js';

// In your worker
const metrics = new MetricsCollector(env);

// Track custom events
metrics.trackBusinessEvent('subscription_upgraded', {
  userId: 'user123',
  plan: 'premium',
  amount: 99.00
});

// Get metrics report
const report = metrics.getMetricsReport();
```

### Prometheus Export

Export metrics in Prometheus format:

```bash
curl https://boss-ai.workers.dev/api/metrics/prometheus
```

---

## Alerting System

### Alert Channels

Configure multiple alert channels:

#### 1. Email Alerts (via SendGrid)

Configure in `.env.production`:
```env
ADMIN_EMAIL=admin@xswarm.ai
SENDGRID_API_KEY_LIVE=SG.xxxxx...
```

Receives:
- Critical errors
- Service outages
- Payment failures
- High error rates

#### 2. SMS Alerts (via Twilio)

Configure in `.env.production`:
```env
ADMIN_PHONE=+1234567890
TWILIO_AUTH_TOKEN_LIVE=xxxxx...
```

Receives:
- Critical errors only
- Service outages
- Database failures

#### 3. Slack Alerts

Configure webhook:
```env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxxxx
```

Receives:
- All alerts (info, warning, error, critical)
- Deployment notifications
- Performance warnings

### Alert Types

#### Critical Alerts

- Service outage
- Database connection failure
- Payment processing down
- Security breach

**Notification**: Email + SMS + Slack

#### Error Alerts

- High error rate (> 5%)
- Payment failures
- API rate limits exceeded

**Notification**: Email + Slack

#### Warning Alerts

- Slow response times
- Slow database queries
- Approaching rate limits

**Notification**: Slack only

#### Info Alerts

- Deployment completed
- Backup completed
- Configuration changes

**Notification**: Slack only

### Alert Thresholds

Default thresholds (configurable):

```javascript
{
  errorRate: 5,           // Percent
  responseTime: 2000,     // ms (P95)
  databaseQueryTime: 5000 // ms (P95)
}
```

Customize in `deployment/monitoring/alerts.js`:

```javascript
alertManager.alertThresholds = {
  errorRate: 3,        // More strict
  responseTime: 1000,  // More strict
  databaseQueryTime: 3000
};
```

### Testing Alerts

Test each alert channel:

```bash
# Test email alert
curl -X POST https://boss-ai.workers.dev/api/test/alert \
  -H "Content-Type: application/json" \
  -d '{"channel":"email","message":"Test alert"}'

# Test SMS alert
curl -X POST https://boss-ai.workers.dev/api/test/alert \
  -H "Content-Type: application/json" \
  -d '{"channel":"sms","message":"Test alert"}'

# Test Slack alert
curl -X POST https://boss-ai.workers.dev/api/test/alert \
  -H "Content-Type: application/json" \
  -d '{"channel":"slack","message":"Test alert"}'
```

---

## Dashboard Setup

### Cloudflare Dashboard

Built-in metrics available at:
https://dash.cloudflare.com/workers/boss-ai/metrics

Shows:
- Requests per second
- CPU time
- Duration percentiles
- Error rate
- Geographic distribution

### Custom Dashboard

Create a custom dashboard using the metrics API:

```html
<!DOCTYPE html>
<html>
<head>
  <title>xSwarm Boss Monitoring</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>xSwarm Boss Monitoring</h1>

  <div>
    <canvas id="requestsChart"></canvas>
    <canvas id="responseTimeChart"></canvas>
    <canvas id="errorRateChart"></canvas>
  </div>

  <script>
    // Fetch metrics every 30 seconds
    async function fetchMetrics() {
      const response = await fetch('/api/metrics');
      const data = await response.json();
      updateCharts(data);
    }

    setInterval(fetchMetrics, 30000);
    fetchMetrics();
  </script>
</body>
</html>
```

### Grafana Integration

For advanced visualization:

1. Set up Grafana instance
2. Configure Prometheus data source
3. Import xSwarm Boss dashboard template
4. Set up alerting rules

---

## Log Management

### Structured Logging

All logs are structured JSON:

```json
{
  "timestamp": "2024-10-29T12:00:00Z",
  "level": "info",
  "requestId": "req_abc123",
  "userId": "user_xyz",
  "method": "POST",
  "path": "/api/auth/login",
  "duration": 156,
  "status": 200
}
```

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information
- **WARN**: Warning messages
- **ERROR**: Error messages
- **ALERT**: Critical alerts

Configure log level:
```env
LOG_LEVEL=info  # production
LOG_LEVEL=debug # staging/development
```

### Viewing Logs

#### Real-time Logs

```bash
# All logs
wrangler tail

# Filter by level
wrangler tail | grep ERROR

# Filter by user
wrangler tail | grep user_xyz

# Pretty print JSON
wrangler tail --format pretty
```

#### Historical Logs

View in Cloudflare dashboard:
1. Go to Workers → boss-ai → Logs
2. Filter by time range, status, method
3. Search by request ID or user ID

### Log Aggregation

For long-term storage and analysis:

#### Option 1: Cloudflare Logpush

1. Enable Logpush in dashboard
2. Configure destination (S3, GCS, etc.)
3. Set up retention policy

#### Option 2: Datadog

1. Install Datadog agent
2. Configure log forwarding
3. Set up dashboards and alerts

#### Option 3: Papertrail

1. Create Papertrail account
2. Configure log endpoint
3. Forward worker logs

---

## Performance Monitoring

### Key Metrics to Monitor

#### Response Time

- **Target**: P95 < 500ms, P99 < 1000ms
- **Alert**: P95 > 2000ms

Check:
```bash
curl https://boss-ai.workers.dev/api/metrics | jq '.requests.p95ResponseTime'
```

#### Error Rate

- **Target**: < 1%
- **Alert**: > 5%

Check:
```bash
curl https://boss-ai.workers.dev/api/metrics | jq '.requests.errorRate'
```

#### Database Performance

- **Target**: P95 < 100ms
- **Alert**: P95 > 5000ms

Check:
```bash
curl https://boss-ai.workers.dev/api/metrics | jq '.database.p95Duration'
```

### Performance Testing

Run performance tests regularly:

```bash
# Load test with k6
k6 run tests/performance/load-test.js

# Stress test
k6 run --vus 100 --duration 30s tests/performance/stress-test.js
```

---

## Business Metrics

### KPIs to Track

#### User Metrics

- Daily Active Users (DAU)
- Monthly Active Users (MAU)
- User retention rate
- Churn rate

#### Revenue Metrics

- Monthly Recurring Revenue (MRR)
- Average Revenue Per User (ARPU)
- Customer Lifetime Value (CLV)
- Conversion rate

#### Product Metrics

- Feature usage by endpoint
- API calls per customer
- Voice/SMS/Email usage
- Task completion rate

### Accessing Business Metrics

```bash
curl https://boss-ai.workers.dev/api/analytics/business \
  -H "Authorization: Bearer <admin-token>"
```

### Custom Analytics

Integrate with your analytics platform:

```javascript
// Track business event
metrics.trackBusinessEvent('subscription_upgraded', {
  userId: user.id,
  plan: 'premium',
  revenue: 99.00,
  source: 'organic'
});
```

---

## Maintenance & Best Practices

### Regular Tasks

#### Daily
- [ ] Review error logs
- [ ] Check error rate (should be < 1%)
- [ ] Monitor response times
- [ ] Review business metrics

#### Weekly
- [ ] Review slow queries
- [ ] Check database size growth
- [ ] Review alert history
- [ ] Update monitoring dashboards

#### Monthly
- [ ] Performance testing
- [ ] Review and adjust alert thresholds
- [ ] Clean up old logs
- [ ] Update monitoring documentation

### Troubleshooting

#### High Error Rate

1. Check logs: `wrangler tail | grep ERROR`
2. Identify error patterns
3. Check recent deployments
4. Review database status
5. Check external API status

#### Slow Response Times

1. Check metrics: `/api/metrics`
2. Identify slow endpoints
3. Review database queries
4. Check external API latency
5. Consider caching

#### Missing Metrics

1. Verify metrics collection is enabled
2. Check worker logs for errors
3. Verify metrics API is accessible
4. Check permissions and authentication

---

## Support

For monitoring issues:

- **Documentation**: Check this guide
- **Logs**: `wrangler tail`
- **Support**: hello@xswarm.dev
- **Status Page**: https://status.xswarm.ai (if available)

---

**Last Updated**: 2025-10-29
**Version**: 1.0.0
