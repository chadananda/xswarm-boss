# xSwarm Boss - Monitoring & Operations Guide

**Comprehensive Monitoring, Logging, and Operational Procedures**

---

## Table of Contents

1. [Monitoring Overview](#monitoring-overview)
2. [Health Check Endpoints](#health-check-endpoints)
3. [Logging Configuration](#logging-configuration)
4. [Metrics & Analytics](#metrics--analytics)
5. [Alerting Setup](#alerting-setup)
6. [Performance Monitoring](#performance-monitoring)
7. [Backup & Recovery](#backup--recovery)
8. [Scaling Procedures](#scaling-procedures)
9. [Incident Response](#incident-response)

---

## Monitoring Overview

### Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│  External Monitoring (Uptime & Availability)            │
│  - UptimeRobot: Health check endpoints every 5 min      │
│  - Cloudflare Analytics: Edge metrics, global latency   │
│  - Pingdom: Synthetic transaction monitoring            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Application Monitoring (Performance & Errors)          │
│  - Cloudflare Workers: Request logs, error tracking     │
│  - systemd journal: Rust client logs                    │
│  - Turso: Database query performance                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Infrastructure Monitoring (Resources & Capacity)       │
│  - System metrics: CPU, RAM, GPU, disk I/O              │
│  - Network metrics: Bandwidth, latency, packet loss     │
│  - MOSHI metrics: Inference time, queue depth           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Business Monitoring (Usage & Revenue)                  │
│  - Stripe: Revenue, MRR, churn rate                     │
│  - Twilio: Call minutes, SMS volume, costs              │
│  - User metrics: Active users, retention, growth        │
└─────────────────────────────────────────────────────────┘
```

---

## Health Check Endpoints

### Server Health (Cloudflare Workers)

**Endpoint:** `GET /health`
**URL:** `https://xswarm-webhooks.your-subdomain.workers.dev/health`

**Response (Healthy):**
```json
{
  "status": "ok",
  "service": "xswarm-webhooks",
  "timestamp": "2025-10-28T10:30:00.000Z",
  "version": "1.0.0"
}
```

**Response (Unhealthy):**
```json
{
  "status": "error",
  "service": "xswarm-webhooks",
  "error": "Database connection failed",
  "timestamp": "2025-10-28T10:30:00.000Z"
}
```

**Monitoring:**
```bash
# Check with curl
curl -f https://xswarm-webhooks.your-subdomain.workers.dev/health

# Exit code 0 = healthy, non-zero = unhealthy

# UptimeRobot configuration:
# - URL: https://xswarm-webhooks.your-subdomain.workers.dev/health
# - Interval: 5 minutes
# - Alert: Email + SMS after 2 failures
```

---

### Voice Bridge Health

**Endpoint:** `GET /health`
**URL:** `http://localhost:9998/health` (internal)

**Response:**
```json
{
  "status": "ok",
  "service": "xswarm-voice",
  "version": "0.1.0",
  "moshi_loaded": true,
  "active_calls": 3,
  "max_concurrent": 10,
  "uptime_seconds": 86400
}
```

**Check script:**
```bash
#!/bin/bash
# /usr/local/bin/check-voice-health.sh

RESPONSE=$(curl -s http://localhost:9998/health)
STATUS=$(echo $RESPONSE | jq -r '.status')

if [ "$STATUS" != "ok" ]; then
  echo "Voice bridge unhealthy: $RESPONSE"
  exit 1
fi

ACTIVE=$(echo $RESPONSE | jq -r '.active_calls')
MAX=$(echo $RESPONSE | jq -r '.max_concurrent')

if [ $ACTIVE -ge $MAX ]; then
  echo "Warning: Voice bridge at capacity ($ACTIVE/$MAX)"
  exit 2
fi

echo "Voice bridge healthy ($ACTIVE/$MAX calls)"
exit 0
```

---

### Supervisor Health

**Endpoint:** `GET /health`
**URL:** `http://localhost:9999/health` (internal)

**Response:**
```json
{
  "status": "ok",
  "service": "xswarm-supervisor",
  "version": "0.1.0",
  "connected_clients": 1,
  "uptime_seconds": 86400
}
```

---

### Database Health (Turso)

**Check via API:**
```bash
# Query database
turso db show xswarm-production

# Check replica status
turso db replicas xswarm-production
```

**Health indicator:**
- Primary: `active`
- Replicas: `synced`
- Lag: `<10s` acceptable

---

## Logging Configuration

### Cloudflare Workers Logs

#### Real-Time Tail
```bash
cd packages/server
pnpm tail

# Or with filtering
pnpm wrangler tail --format pretty
```

**Output:**
```
[2025-10-28 10:30:00] Voice webhook: +15551234567 → +18005551234
[2025-10-28 10:30:00] User: alice@example.com (premium)
[2025-10-28 10:30:00] Accepting call, connecting to voice bridge
[2025-10-28 10:30:15] Call completed, duration: 15s
```

---

#### Structured Logging

**Log format:**
```json
{
  "timestamp": "2025-10-28T10:30:00.000Z",
  "level": "info",
  "service": "xswarm-webhooks",
  "event": "voice_webhook",
  "user_id": "usr_123",
  "phone_from": "+15551234567",
  "phone_to": "+18005551234",
  "duration_ms": 150,
  "status": "success"
}
```

---

#### Log Retention

**Cloudflare Workers:**
- Free tier: 24 hours
- Paid tier: 3 days
- Long-term: Export to external logging service

**Export logs:**
```bash
# Use Logpush (requires paid plan)
# Cloudflare dashboard → Analytics → Logs → Logpush

# Destinations:
# - S3 / R2
# - Google Cloud Storage
# - Azure Blob Storage
# - Datadog
# - Splunk
```

---

### Rust Client Logs (systemd)

#### View Logs
```bash
# Real-time logs
sudo journalctl -u xswarm-voice -f
sudo journalctl -u xswarm-dashboard -f

# Last 100 lines
sudo journalctl -u xswarm-voice -n 100

# Since specific time
sudo journalctl -u xswarm-voice --since "2025-10-28 10:00:00"

# Filter by priority
sudo journalctl -u xswarm-voice -p err  # Errors only
```

---

#### Log Format

**Voice bridge log:**
```
Oct 28 10:30:00 server xswarm-voice[1234]: INFO Accepting WebSocket connection from 192.168.1.100
Oct 28 10:30:00 server xswarm-voice[1234]: INFO MOSHI processing audio frame (seq=123, size=1024)
Oct 28 10:30:00 server xswarm-voice[1234]: INFO Generated response (latency=180ms)
Oct 28 10:30:15 server xswarm-voice[1234]: INFO Call completed (duration=15s, frames=187)
```

---

#### Log Rotation

**systemd journal configuration:**
```bash
# /etc/systemd/journald.conf
[Journal]
SystemMaxUse=1G        # Max disk space
SystemKeepFree=500M    # Keep free space
MaxRetentionSec=30day  # Retain 30 days
```

**Apply configuration:**
```bash
sudo systemctl restart systemd-journald
```

---

#### Export Logs to File

```bash
# Export specific service logs
sudo journalctl -u xswarm-voice --since today > /var/log/xswarm-voice-$(date +%F).log

# Compress old logs
gzip /var/log/xswarm-voice-*.log

# Automated daily export (cron)
sudo crontab -e

# Add:
0 0 * * * journalctl -u xswarm-voice --since "1 day ago" | gzip > /var/log/xswarm-voice-$(date -d yesterday +\%F).log.gz
```

---

### Application Log Levels

**Environment variable:**
```bash
# .env or systemd service file
RUST_LOG=info  # Options: trace, debug, info, warn, error
```

**Log level guidelines:**

| Level | Use Case | Volume |
|-------|----------|--------|
| `trace` | Deep debugging, all function calls | Very high |
| `debug` | Development, detailed debugging | High |
| `info` | Production, normal operations | Medium |
| `warn` | Potential issues, degraded performance | Low |
| `error` | Failures requiring attention | Very low |

**Production recommendation:** `info`

---

## Metrics & Analytics

### Cloudflare Workers Analytics

**Dashboard:** Cloudflare → Workers → xswarm-webhooks → Metrics

**Key metrics:**
- **Requests per second**: Total traffic volume
- **Success rate**: % of 2xx responses
- **Error rate**: % of 5xx errors
- **P50/P99 latency**: Response time percentiles
- **CPU time**: Execution time per request

**Acceptable thresholds:**
- Success rate: >99%
- P99 latency: <500ms
- CPU time: <10ms (free tier), <50ms (paid tier)

---

### Turso Database Metrics

**Dashboard:** turso.tech → xswarm-production → Metrics

**Key metrics:**
- **Row reads/writes**: Database activity
- **Query latency**: P50, P95, P99
- **Storage used**: Database size
- **Replica lag**: Sync delay for edge replicas

**Acceptable thresholds:**
- Query latency P99: <100ms
- Replica lag: <10s
- Storage: <80% of limit

---

### Voice Processing Metrics

**Collected by Rust client:**

```rust
// Example metrics
struct VoiceMetrics {
    calls_active: u32,
    calls_total: u64,
    latency_ms_p50: f64,
    latency_ms_p99: f64,
    errors_total: u64,
    uptime_seconds: u64,
}
```

**Expose via HTTP endpoint:**
```bash
# GET /metrics (Prometheus format)
curl http://localhost:9998/metrics
```

**Output:**
```
# HELP xswarm_voice_calls_active Current active calls
# TYPE xswarm_voice_calls_active gauge
xswarm_voice_calls_active 3

# HELP xswarm_voice_calls_total Total calls processed
# TYPE xswarm_voice_calls_total counter
xswarm_voice_calls_total 1234

# HELP xswarm_voice_latency_ms Voice processing latency
# TYPE xswarm_voice_latency_ms histogram
xswarm_voice_latency_ms_bucket{le="100"} 450
xswarm_voice_latency_ms_bucket{le="200"} 890
xswarm_voice_latency_ms_bucket{le="300"} 1200
xswarm_voice_latency_ms_sum 234567
xswarm_voice_latency_ms_count 1234
```

---

### System Resource Metrics

**Monitor with:**
- `htop` (interactive)
- `top` (command line)
- `nvidia-smi` (GPU utilization)
- `iostat` (disk I/O)
- `netstat` (network connections)

**Key metrics:**

| Metric | Command | Threshold |
|--------|---------|-----------|
| CPU usage | `top` | <80% sustained |
| Memory usage | `free -h` | <90% |
| GPU memory | `nvidia-smi` | <90% VRAM |
| Disk usage | `df -h` | <80% capacity |
| Disk I/O | `iostat -x` | <80% utilization |
| Network bandwidth | `iftop` | <80% capacity |

**Automated monitoring script:**
```bash
#!/bin/bash
# /usr/local/bin/monitor-resources.sh

CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEM=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100)}')
DISK=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)

echo "CPU: ${CPU}%, MEM: ${MEM}%, DISK: ${DISK}%"

if (( $(echo "$CPU > 80" | bc -l) )); then
  echo "WARNING: High CPU usage"
fi

if (( MEM > 90 )); then
  echo "WARNING: High memory usage"
fi

if (( DISK > 80 )); then
  echo "WARNING: High disk usage"
fi
```

---

## Alerting Setup

### Email Alerts (Free)

**Tools:**
- UptimeRobot (built-in email alerts)
- Cronitor
- Healthchecks.io

**Setup:**
```bash
# UptimeRobot configuration:
1. Add monitor: https://xswarm-webhooks.your-subdomain.workers.dev/health
2. Alert contacts: admin@yourdomain.com
3. Alert threshold: 2 failures (10 minutes)
4. Alert channels: Email + SMS
```

---

### SMS/Phone Alerts

**Twilio webhook for self-monitoring:**
```javascript
// Send alert SMS via Twilio
async function sendAlert(message) {
  await twilioClient.messages.create({
    to: '+15551234567',  // Admin phone
    from: '+18005551234', // xSwarm number
    body: `🚨 xSwarm Alert: ${message}`
  });
}

// Example usage
if (errorRate > 0.05) {  // >5% errors
  await sendAlert('High error rate detected');
}
```

---

### Slack/Discord Webhooks

**Send alerts to team chat:**
```bash
#!/bin/bash
# /usr/local/bin/alert-slack.sh

MESSAGE="$1"
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

curl -X POST $WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"🚨 xSwarm Alert: $MESSAGE\"}"
```

**Usage:**
```bash
# In monitoring script
if [ $CPU_USAGE -gt 80 ]; then
  /usr/local/bin/alert-slack.sh "High CPU usage: ${CPU_USAGE}%"
fi
```

---

### PagerDuty Integration (Enterprise)

**For 24/7 on-call rotation:**

1. Create PagerDuty account
2. Set up integration in Cloudflare Workers
3. Configure escalation policies
4. Test incident creation

**Incident routing:**
- P1 (Critical): Page on-call engineer immediately
- P2 (High): Email + Slack alert
- P3 (Medium): Slack alert only
- P4 (Low): Email digest (daily)

---

## Performance Monitoring

### Voice Processing Latency

**Target:** <200ms end-to-end
**Measured:** Twilio webhook → MOSHI inference → TwiML response

**Breakdown:**
- Network (Twilio → Workers): 10-50ms
- Workers processing: 5-10ms
- WebSocket → Rust client: 10-30ms
- MOSHI inference: 160-200ms
- Response path: 10-50ms

**Total:** 195-340ms (target: <300ms)

**Monitoring:**
```bash
# Add timing logs
[2025-10-28 10:30:00.000] Webhook received
[2025-10-28 10:30:00.015] User authenticated (15ms)
[2025-10-28 10:30:00.045] WebSocket connected (30ms)
[2025-10-28 10:30:00.225] MOSHI inference complete (180ms)
[2025-10-28 10:30:00.275] Response sent (50ms)
# Total: 275ms ✓
```

---

### Database Query Performance

**Monitor slow queries:**
```bash
# Turso doesn't expose query logs by default
# Monitor via application logs

# In Rust client, log slow queries:
if query_duration > 100ms {
  log::warn!("Slow query: {} ({}ms)", query, duration);
}
```

**Optimization tips:**
- Add indexes on frequently queried columns
- Use edge replicas for read queries
- Cache user data in memory (short TTL)
- Batch write operations

---

### API Response Times

**Cloudflare Workers metrics:**
- P50: 10-20ms (typical)
- P95: 30-50ms (acceptable)
- P99: 50-100ms (investigate if higher)

**Slow endpoint investigation:**
```bash
# View detailed logs for slow requests
pnpm wrangler tail --format pretty | grep -E "duration_ms: [0-9]{3,}"
```

---

## Backup & Recovery

### Database Backups

#### Automatic (Turso)
- **Point-in-time recovery**: 30 days retention
- **Frequency**: Continuous (automatic)
- **No configuration needed**

**Restore from PITR:**
```bash
# Restore to specific timestamp
turso db restore xswarm-production --timestamp "2025-10-28T10:00:00Z"

# Create new database from backup (non-destructive)
turso db create xswarm-production-restore --from-backup <backup-id>
```

---

#### Manual Backups

**Script:**
```bash
#!/bin/bash
# /usr/local/bin/backup-database.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/xswarm"
BACKUP_FILE="$BACKUP_DIR/xswarm-production-$TIMESTAMP.db"

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
turso db dump xswarm-production > $BACKUP_FILE

# Compress
gzip $BACKUP_FILE

# Upload to R2
aws s3 cp $BACKUP_FILE.gz s3://xswarm-production/backups/ \
  --endpoint-url https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com

# Delete local backup after 7 days
find $BACKUP_DIR -name "*.db.gz" -mtime +7 -delete

echo "Backup complete: $BACKUP_FILE.gz"
```

**Cron schedule:**
```bash
# Daily at 3 AM
0 3 * * * /usr/local/bin/backup-database.sh
```

---

### Configuration Backups

**Backup critical files:**
```bash
#!/bin/bash
# /usr/local/bin/backup-config.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/xswarm"
TAR_FILE="$BACKUP_DIR/config-$TIMESTAMP.tar.gz"

# Backup config files
tar -czf $TAR_FILE \
  /opt/xswarm/config.toml \
  /opt/xswarm/.env \
  /etc/systemd/system/xswarm-*.service \
  /etc/nginx/sites-available/xswarm

# Upload to R2
aws s3 cp $TAR_FILE s3://xswarm-production/backups/config/ \
  --endpoint-url https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com

echo "Config backup complete: $TAR_FILE"
```

---

### Binary Backups

**Before deploying new version:**
```bash
#!/bin/bash
# /usr/local/bin/backup-binaries.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/xswarm/backup"

mkdir -p $BACKUP_DIR

# Backup current binaries
cp /opt/xswarm/target/release/xswarm-voice \
   $BACKUP_DIR/xswarm-voice-$TIMESTAMP

cp /opt/xswarm/target/release/xswarm-dashboard \
   $BACKUP_DIR/xswarm-dashboard-$TIMESTAMP

# Keep last 3 versions
ls -t $BACKUP_DIR/xswarm-voice-* | tail -n +4 | xargs rm -f
ls -t $BACKUP_DIR/xswarm-dashboard-* | tail -n +4 | xargs rm -f

echo "Binaries backed up"
```

---

### Recovery Testing

**Test restore procedure monthly:**
```bash
# 1. Create test database from backup
turso db create xswarm-test --from-backup latest

# 2. Verify data integrity
turso db shell xswarm-test
SELECT COUNT(*) FROM users;
SELECT * FROM users LIMIT 10;

# 3. Test application connection
# Update .env with test database URL
# Run application and verify functionality

# 4. Clean up
turso db destroy xswarm-test
```

---

## Scaling Procedures

### Horizontal Scaling (Multiple Instances)

**Load balancer configuration (nginx):**
```nginx
upstream xswarm_voice {
    # Least connections algorithm
    least_conn;

    # Health checks
    server voice1.internal:9998 max_fails=3 fail_timeout=30s;
    server voice2.internal:9998 max_fails=3 fail_timeout=30s;
    server voice3.internal:9998 max_fails=3 fail_timeout=30s;

    # Sticky sessions (for WebSocket affinity)
    ip_hash;
}
```

**Deploy additional instances:**
```bash
# On each new server
1. Install dependencies
2. Copy config.toml and .env
3. Build binaries: cargo build --release
4. Start services: systemctl start xswarm-voice
5. Add to load balancer pool
```

---

### Vertical Scaling (Upgrade Hardware)

**Procedure:**
1. Schedule maintenance window
2. Backup database and config
3. Drain existing connections
4. Stop services
5. Upgrade hardware (CPU/RAM/GPU)
6. Restart services
7. Verify performance improvement

**Zero-downtime alternative:**
1. Deploy new server with upgraded hardware
2. Add to load balancer pool
3. Gradually shift traffic (weighted routing)
4. Remove old server once fully migrated

---

### Auto-Scaling Triggers

**Scale up when:**
- CPU usage >80% sustained for 5 minutes
- Memory usage >85%
- Active calls approaching max_concurrent
- Queue depth >10

**Scale down when:**
- CPU usage <20% sustained for 15 minutes
- Active calls <50% capacity
- No traffic for 1 hour (off-peak)

---

## Incident Response

### Incident Severity Levels

| Level | Impact | Response Time | Escalation |
|-------|--------|---------------|------------|
| P1 | Complete outage | Immediate | Page on-call + manager |
| P2 | Major degradation | <15 minutes | Alert on-call |
| P3 | Minor issues | <1 hour | Email team |
| P4 | Cosmetic | <24 hours | Create ticket |

---

### Incident Response Checklist

**P1 Incident (Complete Outage):**

1. **Acknowledge** (within 5 minutes)
   - Confirm incident via monitoring
   - Page on-call engineer
   - Update status page

2. **Investigate** (within 15 minutes)
   - Check health endpoints
   - Review recent deployments
   - Check error logs

3. **Mitigate** (within 30 minutes)
   - Rollback recent changes if applicable
   - Restart services if needed
   - Failover to backup systems

4. **Resolve** (within 2 hours)
   - Fix root cause
   - Verify full functionality
   - Monitor for recurrence

5. **Post-Mortem** (within 48 hours)
   - Document timeline
   - Identify root cause
   - Create prevention tasks

---

### Common Incident Scenarios

#### Database Connection Failure

**Symptoms:**
- Health checks failing
- 500 errors in Workers
- "Failed to connect to database" logs

**Resolution:**
```bash
# 1. Check Turso status
turso db show xswarm-production

# 2. Verify auth token
echo $TURSO_AUTH_TOKEN | head -c 20

# 3. Test connection
turso db shell xswarm-production

# 4. Rotate token if expired
turso db tokens create xswarm-production --expiration none

# 5. Update Workers secrets
cd packages/server
pnpm wrangler secret put TURSO_AUTH_TOKEN

# 6. Verify resolution
curl https://xswarm-webhooks.your-subdomain.workers.dev/health
```

---

#### MOSHI Model Not Loading

**Symptoms:**
- Voice bridge service fails to start
- "Model not found" errors
- High startup time (>5 minutes)

**Resolution:**
```bash
# 1. Check model cache
ls -lh ~/.cache/huggingface/hub/

# 2. Clear corrupted cache
rm -rf ~/.cache/huggingface/hub/models--kyutai--moshika-mlx-q4

# 3. Re-download model
python3 << EOF
from moshi_mlx import load_model
model = load_model("kyutai/moshika-mlx-q4")
print("Model loaded successfully")
EOF

# 4. Restart service
sudo systemctl restart xswarm-voice

# 5. Verify
curl http://localhost:9998/health
```

---

#### High CPU/Memory Usage

**Symptoms:**
- System becoming unresponsive
- Increased latency
- Service crashes (OOM)

**Resolution:**
```bash
# 1. Identify resource hogs
top -o %CPU
top -o %MEM

# 2. Check for memory leaks
sudo journalctl -u xswarm-voice | grep -i "memory"

# 3. Restart affected services
sudo systemctl restart xswarm-voice

# 4. If persistent, scale up
# - Add more RAM
# - Reduce max_concurrent_calls
# - Deploy additional instances

# 5. Monitor for recurrence
watch -n 5 'free -h'
```

---

## Related Documentation

- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) - Deployment procedures
- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) - Detailed troubleshooting
- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - Security best practices
- [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md) - Hardware requirements

---

**Last Updated**: 2025-10-28
**Next Review**: After major version release or scaling event
