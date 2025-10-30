# xSwarm Boss - Troubleshooting Guide

**Complete Guide for Diagnosing and Resolving Common Issues**

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Server Issues (Cloudflare Workers)](#server-issues-cloudflare-workers)
3. [Client Issues (Rust)](#client-issues-rust)
4. [MOSHI Voice Processing](#moshi-voice-processing)
5. [Database Issues (Turso)](#database-issues-turso)
6. [Webhook Problems](#webhook-problems)
7. [Performance Issues](#performance-issues)
8. [Network & Connectivity](#network--connectivity)
9. [Deployment Failures](#deployment-failures)
10. [Recovery Procedures](#recovery-procedures)

---

## Quick Diagnostics

### Health Check Checklist

Run these commands to quickly identify issues:

```bash
# 1. Server health
curl https://xswarm-webhooks.your-subdomain.workers.dev/health

# 2. Voice bridge health
curl http://localhost:9998/health

# 3. Supervisor health
curl http://localhost:9999/health

# 4. Database connectivity
turso db shell xswarm-production "SELECT 1"

# 5. Check service status (Linux)
sudo systemctl status xswarm-voice
sudo systemctl status xswarm-dashboard

# 6. Check recent logs
sudo journalctl -u xswarm-voice -n 50
cd packages/server && pnpm tail
```

**Expected results:**
- All health endpoints return `{"status":"ok"}`
- Services show `active (running)`
- No error messages in logs

---

### Common Error Messages

| Error Message | Location | Quick Fix |
|---------------|----------|-----------|
| "Invalid Twilio signature" | Server logs | Check TWILIO_AUTH_TOKEN |
| "Model not found" | Voice logs | Re-download MOSHI model |
| "Database connection failed" | Server logs | Check TURSO_AUTH_TOKEN |
| "WebSocket connection refused" | Client logs | Check voice bridge is running |
| "Rate limit exceeded" | Server logs | Normal during high load |
| "Out of memory" | System logs | Reduce max_concurrent_calls |

---

## Server Issues (Cloudflare Workers)

### Issue: Server Returns 500 Errors

**Symptoms:**
```bash
$ curl https://xswarm-webhooks.your-subdomain.workers.dev/health
{"error": "Internal server error"}
```

**Diagnosis:**
```bash
# Check Worker logs
cd packages/server
pnpm tail

# Look for stack traces or error messages
```

**Common causes:**

#### 1. Missing Environment Variable

**Error in logs:**
```
ReferenceError: TWILIO_AUTH_TOKEN is not defined
```

**Fix:**
```bash
# List current secrets
pnpm wrangler secret list

# Push missing secret
echo $TWILIO_AUTH_TOKEN | pnpm wrangler secret put TWILIO_AUTH_TOKEN

# Verify deployment
curl https://xswarm-webhooks.your-subdomain.workers.dev/health
```

---

#### 2. Database Connection Failure

**Error in logs:**
```
Error: Failed to connect to database: unauthorized
```

**Fix:**
```bash
# Test database connection
turso db show xswarm-production

# Generate new auth token
turso db tokens create xswarm-production --expiration none

# Update secret
echo $NEW_TOKEN | pnpm wrangler secret put TURSO_AUTH_TOKEN

# Verify
curl https://xswarm-webhooks.your-subdomain.workers.dev/health
```

---

#### 3. Code Error After Deployment

**Error in logs:**
```
SyntaxError: Unexpected token
TypeError: Cannot read property 'x' of undefined
```

**Fix:**
```bash
# Rollback to previous version
pnpm wrangler deployments list
pnpm wrangler rollback <previous-deployment-id>

# Verify rollback
curl https://xswarm-webhooks.your-subdomain.workers.dev/health

# Fix code locally
# Test locally: pnpm dev
# Deploy again: pnpm deploy
```

---

### Issue: Webhook Signature Validation Fails

**Symptoms:**
- Twilio/Stripe webhooks rejected
- "Invalid signature" in logs

**Diagnosis:**
```bash
# Check logs for signature validation errors
pnpm wrangler tail | grep -i signature
```

**Fix for Twilio:**
```bash
# 1. Verify auth token is correct
echo $TWILIO_AUTH_TOKEN

# 2. Compare with Twilio console
# https://console.twilio.com/ → Account → Auth Token

# 3. If different, update
echo $CORRECT_TOKEN | pnpm wrangler secret put TWILIO_AUTH_TOKEN

# 4. Test webhook
# Make a test call to your number
```

**Fix for Stripe:**
```bash
# 1. Get current webhook secret from Stripe dashboard
# https://dashboard.stripe.com/webhooks

# 2. Update secret
echo $WEBHOOK_SECRET | pnpm wrangler secret put STRIPE_WEBHOOK_SECRET_LIVE

# 3. Test webhook
stripe trigger customer.subscription.created
```

---

### Issue: High CPU Time Usage

**Symptoms:**
- Workers logs show "CPU time limit exceeded"
- Slow response times

**Diagnosis:**
```bash
# Check CPU time in Cloudflare dashboard
# Workers → xswarm-webhooks → Metrics → CPU time
```

**Common causes:**
1. Complex database queries
2. Large payloads
3. Synchronous operations

**Fix:**
```javascript
// Optimize database queries
// Before (slow):
const users = await db.execute('SELECT * FROM users');

// After (fast):
const users = await db.execute({
  sql: 'SELECT id, email FROM users WHERE subscription_tier = ?',
  args: ['premium']
});

// Use indexes
CREATE INDEX idx_users_tier ON users(subscription_tier);

// Async operations
await Promise.all([
  updateUser(userId),
  sendNotification(userId),
  logEvent(userId)
]);
```

---

## Client Issues (Rust)

### Issue: Service Fails to Start

**Symptoms:**
```bash
$ sudo systemctl status xswarm-voice
● xswarm-voice.service - xSwarm Voice Bridge
   Loaded: loaded
   Active: failed (Result: exit-code)
```

**Diagnosis:**
```bash
# Check detailed logs
sudo journalctl -u xswarm-voice -n 100 --no-pager

# Check for common errors
sudo journalctl -u xswarm-voice | grep -i error
```

**Common causes:**

#### 1. Missing .env File

**Error in logs:**
```
Error: .env file not found
```

**Fix:**
```bash
# Check if .env exists
ls -l /opt/xswarm/.env

# If missing, create it
sudo -u xswarm cp /opt/xswarm/.env.example /opt/xswarm/.env
sudo -u xswarm nano /opt/xswarm/.env
# (Fill in secrets)

# Set correct permissions
sudo chmod 600 /opt/xswarm/.env
sudo chown xswarm:xswarm /opt/xswarm/.env

# Restart service
sudo systemctl restart xswarm-voice
```

---

#### 2. Port Already in Use

**Error in logs:**
```
Error: Address already in use (os error 98)
```

**Fix:**
```bash
# Find what's using the port
sudo netstat -tulpn | grep 9998

# Kill the process
sudo kill <PID>

# Or use a different port
# Edit config.toml:
[voice.bridge]
port = 9998  # Change to 10000 or another free port

# Restart service
sudo systemctl restart xswarm-voice
```

---

#### 3. Permission Denied

**Error in logs:**
```
Error: Permission denied (os error 13)
```

**Fix:**
```bash
# Check file ownership
ls -la /opt/xswarm/

# Fix ownership
sudo chown -R xswarm:xswarm /opt/xswarm/
sudo chown -R xswarm:xswarm /var/lib/xswarm/
sudo chown -R xswarm:xswarm /var/log/xswarm/

# Restart service
sudo systemctl restart xswarm-voice
```

---

### Issue: Service Keeps Restarting

**Symptoms:**
```bash
$ sudo systemctl status xswarm-voice
Active: activating (auto-restart) (Result: exit-code)
```

**Diagnosis:**
```bash
# Check restart count
sudo systemctl status xswarm-voice | grep Restart

# Check crash logs
sudo journalctl -u xswarm-voice --since "5 minutes ago"

# Disable auto-restart temporarily
sudo systemctl edit --full xswarm-voice.service
# Change: Restart=always → Restart=no
sudo systemctl daemon-reload
sudo systemctl start xswarm-voice

# Watch logs in real-time
sudo journalctl -u xswarm-voice -f
```

**Common causes:**

#### 1. Configuration Error

**Error in logs:**
```
Error parsing config.toml: invalid value for key 'port'
```

**Fix:**
```bash
# Validate config
cargo run -- --check-config

# Or manually check syntax
cat config.toml | grep -A5 -B5 "port"

# Fix syntax error
sudo -u xswarm nano /opt/xswarm/config.toml

# Restart
sudo systemctl restart xswarm-voice
```

---

#### 2. Out of Memory

**Error in logs:**
```
Error: Out of memory
kernel: Out of memory: Killed process 12345 (xswarm-voice)
```

**Fix:**
```bash
# Check memory usage
free -h
systemctl status xswarm-voice | grep Memory

# Reduce max concurrent calls
# Edit config.toml:
[performance]
moshi_max_concurrent_calls = 5  # Reduce from 10

# Increase memory limit (if server has more RAM)
# Edit /etc/systemd/system/xswarm-voice.service:
MemoryMax=32G  # Increase from 16G

sudo systemctl daemon-reload
sudo systemctl restart xswarm-voice
```

---

### Issue: WebSocket Connection Fails

**Symptoms:**
- Client can't connect to server
- "Connection refused" errors

**Diagnosis:**
```bash
# Test WebSocket connection
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:9998/

# Expected: HTTP 101 Switching Protocols
```

**Fix:**
```bash
# 1. Check service is running
sudo systemctl status xswarm-voice

# 2. Check port is listening
sudo netstat -tulpn | grep 9998

# 3. Check firewall
sudo ufw status | grep 9998
# If blocked: sudo ufw allow 9998/tcp

# 4. Test locally first
curl http://localhost:9998/health

# 5. If nginx reverse proxy, check config
sudo nginx -t
sudo systemctl status nginx
```

---

## MOSHI Voice Processing

### Issue: MOSHI Model Not Loading

**Symptoms:**
```
Error: Model not found: kyutai/moshika-mlx-q4
Error: Failed to load model from cache
```

**Diagnosis:**
```bash
# Check model cache
ls -lh ~/.cache/huggingface/hub/ | grep moshi

# Check Python environment
python3 -c "import moshi_mlx; print(moshi_mlx.__version__)"
```

**Fix:**
```bash
# 1. Clear corrupted cache
rm -rf ~/.cache/huggingface/hub/models--kyutai--moshika-mlx-q4

# 2. Re-download model
python3 << EOF
from moshi_mlx import load_model
model = load_model("kyutai/moshika-mlx-q4")
print("✓ Model downloaded successfully")
EOF

# 3. Verify cache
ls -lh ~/.cache/huggingface/hub/ | grep moshi

# 4. Restart service
sudo systemctl restart xswarm-voice
```

---

### Issue: High Voice Processing Latency

**Symptoms:**
- Voice calls have >500ms delay
- Slow response generation

**Diagnosis:**
```bash
# Check MOSHI inference time in logs
sudo journalctl -u xswarm-voice | grep "inference time"

# Check GPU usage (if available)
nvidia-smi  # NVIDIA
sudo powermetrics | grep -i gpu  # Apple Silicon

# Check CPU usage
top -o %CPU | head -20
```

**Common causes:**

#### 1. Running on CPU Instead of GPU

**Fix (Apple Silicon):**
```bash
# Verify Metal is available
python3 << EOF
import mlx.core as mx
print("Metal available:", mx.metal.is_available())
EOF

# If false, reinstall mlx
pip uninstall mlx mlx-metal
pip install mlx mlx-metal
```

**Fix (Linux NVIDIA):**
```bash
# Check CUDA
nvidia-smi

# If not found, install CUDA
# https://developer.nvidia.com/cuda-downloads

# Reinstall PyTorch with CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

---

#### 2. Too Many Concurrent Calls

**Fix:**
```bash
# Check active calls
curl http://localhost:9998/health | jq '.active_calls'

# Reduce max_concurrent_calls
# Edit config.toml:
[performance]
moshi_max_concurrent_calls = 5  # Reduce from 10

# Restart
sudo systemctl restart xswarm-voice
```

---

#### 3. Insufficient Memory

**Fix:**
```bash
# Check memory usage
free -h

# Close unused applications
# Or add more RAM
# Or deploy multiple instances with load balancer
```

---

### Issue: Audio Quality Problems

**Symptoms:**
- Choppy audio
- Robotic voice
- Echo or feedback

**Diagnosis:**
```bash
# Check sample rate configuration
grep sample_rate config.toml
# Should be: sample_rate = 24000

# Check audio device
arecord -l  # List input devices
aplay -l    # List output devices
```

**Fix:**
```bash
# 1. Verify sample rate is 24kHz
# Edit config.toml:
[voice]
sample_rate = 24000  # MOSHI requires 24kHz

# 2. Test audio device
arecord -d 5 -f cd test.wav
aplay test.wav

# 3. Check network bandwidth
speedtest-cli

# 4. Enable echo cancellation (if available)
# Add to config.toml:
[voice]
enable_echo_cancellation = true
enable_noise_suppression = true
```

---

## Database Issues (Turso)

### Issue: Database Connection Timeout

**Symptoms:**
```
Error: Connection timeout connecting to database
Error: ETIMEDOUT
```

**Diagnosis:**
```bash
# Test direct connection
turso db shell xswarm-production "SELECT 1"

# Check database status
turso db show xswarm-production

# Check network connectivity
ping xswarm-production-your-org.turso.io
```

**Fix:**
```bash
# 1. Verify database URL
echo $TURSO_DATABASE_URL
# Should match: turso db show xswarm-production

# 2. Check auth token is valid
turso db tokens validate $TURSO_AUTH_TOKEN

# 3. If expired, create new token
NEW_TOKEN=$(turso db tokens create xswarm-production --expiration none)

# 4. Update .env
echo "TURSO_AUTH_TOKEN=$NEW_TOKEN" >> .env

# 5. Update Cloudflare Workers
echo $NEW_TOKEN | pnpm wrangler secret put TURSO_AUTH_TOKEN

# 6. Restart services
sudo systemctl restart xswarm-voice xswarm-dashboard
```

---

### Issue: Slow Database Queries

**Symptoms:**
- High query latency (>100ms)
- Timeouts during high load

**Diagnosis:**
```bash
# Check query performance in logs
sudo journalctl -u xswarm-voice | grep "query took"

# Check database size
turso db show xswarm-production | grep "Size"

# Check indexes
turso db shell xswarm-production
SELECT name, sql FROM sqlite_master WHERE type='index';
```

**Fix:**
```sql
-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_xswarm_phone ON users(xswarm_phone);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);

-- Analyze query performance
EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'test@example.com';

-- Vacuum database (clean up deleted records)
VACUUM;
```

**Enable edge replicas:**
```bash
# Add replicas closer to users
turso db replicate xswarm-production --location iad  # US East
turso db replicate xswarm-production --location fra  # Europe
turso db replicate xswarm-production --location nrt  # Asia
```

---

### Issue: Database Write Conflicts

**Symptoms:**
```
Error: SQLITE_BUSY: database is locked
Error: Database write conflict
```

**Fix:**
```bash
# Enable WAL mode (Write-Ahead Logging)
turso db shell xswarm-production
PRAGMA journal_mode=WAL;

# Increase busy timeout
PRAGMA busy_timeout=5000;  # 5 seconds
```

---

## Webhook Problems

### Issue: Twilio Webhooks Not Received

**Symptoms:**
- Incoming calls/SMS don't trigger webhooks
- No logs in Worker

**Diagnosis:**
```bash
# Check Twilio webhook configuration
# https://console.twilio.com/
# Phone Numbers → Active Numbers → Select number → Webhooks

# Check Worker logs
cd packages/server
pnpm tail
```

**Fix:**
```bash
# 1. Verify webhook URL is correct
# Should be: https://xswarm-webhooks.your-subdomain.workers.dev/voice/{userId}

# 2. Test webhook manually
curl -X POST https://xswarm-webhooks.your-subdomain.workers.dev/voice/test123 \
  -d "From=+15551234567" \
  -d "To=+18005551234" \
  -d "CallSid=CA1234567890"

# 3. Check Twilio debugger
# https://console.twilio.com/monitor/debugger

# 4. Re-run webhook setup
pnpm setup:twilio
```

---

### Issue: Stripe Webhooks Failing

**Symptoms:**
```
Stripe webhook failed: Invalid signature
Subscription events not processing
```

**Diagnosis:**
```bash
# Check Stripe webhook logs
# https://dashboard.stripe.com/webhooks

# Check Worker logs
pnpm wrangler tail | grep stripe
```

**Fix:**
```bash
# 1. Get correct webhook secret from Stripe
# Dashboard → Webhooks → Select endpoint → Signing secret

# 2. Update secret
echo $WEBHOOK_SECRET | pnpm wrangler secret put STRIPE_WEBHOOK_SECRET_LIVE

# 3. Test webhook
stripe trigger customer.subscription.created

# 4. Or re-run setup
pnpm setup:webhooks --live
```

---

## Performance Issues

### Issue: High Memory Usage

**Symptoms:**
```
Memory usage >90%
OOM (Out of Memory) kills
System becoming unresponsive
```

**Diagnosis:**
```bash
# Check memory usage
free -h
top -o %MEM | head -20

# Check service memory
systemctl status xswarm-voice | grep Memory

# Check for memory leaks
sudo journalctl -u xswarm-voice | grep -i "memory\|oom"
```

**Fix:**
```bash
# 1. Reduce max concurrent calls
# Edit config.toml:
[performance]
moshi_max_concurrent_calls = 5

# 2. Increase swap (temporary fix)
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 3. Add more RAM (permanent fix)
# Or deploy multiple instances

# 4. Enable aggressive garbage collection
# Edit systemd service:
Environment="MALLOC_MMAP_THRESHOLD_=65536"

sudo systemctl daemon-reload
sudo systemctl restart xswarm-voice
```

---

### Issue: High CPU Usage

**Symptoms:**
- CPU usage >80% sustained
- Slow response times
- System lag

**Diagnosis:**
```bash
# Check CPU usage
top -o %CPU | head -20
mpstat 1 10  # Monitor CPU for 10 seconds

# Check which process
ps aux | sort -nrk 3,3 | head -10
```

**Fix:**
```bash
# 1. Limit CPU usage
# Edit /etc/systemd/system/xswarm-voice.service:
CPUQuota=300%  # Limit to 3 cores

sudo systemctl daemon-reload
sudo systemctl restart xswarm-voice

# 2. Optimize MOSHI batch size
# Edit config.toml:
[performance]
moshi_batch_size = 1  # Keep at 1 for lowest latency

# 3. Use GPU acceleration (if available)
[performance]
moshi_use_gpu = true

# 4. Deploy multiple instances with load balancer
```

---

### Issue: Disk I/O Bottleneck

**Symptoms:**
- High disk wait time (iowait)
- Slow model loading
- Log writes delayed

**Diagnosis:**
```bash
# Check disk I/O
iostat -x 1 10

# Check disk usage
df -h
du -sh /opt/xswarm/* | sort -h

# Check what's using I/O
iotop
```

**Fix:**
```bash
# 1. Move to faster storage
# SSD or NVMe if using HDD

# 2. Reduce log verbosity
# Edit config.toml or systemd service:
Environment="RUST_LOG=warn"  # Instead of info

# 3. Use in-memory cache for models
# Create tmpfs
sudo mount -t tmpfs -o size=8G tmpfs /opt/xswarm/model_cache

# 4. Enable disk write cache
sudo hdparm -W1 /dev/sda
```

---

## Network & Connectivity

### Issue: Network Latency

**Symptoms:**
- Slow API responses
- Voice call delays
- Timeout errors

**Diagnosis:**
```bash
# Test latency to Cloudflare Workers
ping xswarm-webhooks.your-subdomain.workers.dev

# Test latency to Turso
ping xswarm-production-your-org.turso.io

# Test bandwidth
speedtest-cli

# Trace route
traceroute xswarm-webhooks.your-subdomain.workers.dev
```

**Fix:**
```bash
# 1. Use edge replicas closer to users
turso db replicate xswarm-production --location <closest-region>

# 2. Enable Cloudflare Argo (paid)
# Reduces latency by ~30%

# 3. Use custom domain on Cloudflare
# Improves routing

# 4. Deploy client closer to users
# Use cloud provider in same region
```

---

### Issue: Firewall Blocking Connections

**Symptoms:**
```
Connection refused
Connection timeout
No route to host
```

**Diagnosis:**
```bash
# Check if port is open
sudo ufw status | grep 9998
sudo firewall-cmd --list-all | grep 9998

# Test from another machine
curl http://your-server-ip:9998/health
```

**Fix:**
```bash
# Open required ports
sudo ufw allow 9998/tcp
sudo ufw allow 9999/tcp
sudo ufw reload

# Or
sudo firewall-cmd --permanent --add-port=9998/tcp
sudo firewall-cmd --permanent --add-port=9999/tcp
sudo firewall-cmd --reload
```

---

## Deployment Failures

### Issue: Cargo Build Fails

**Symptoms:**
```
error: could not compile `xswarm`
error[E0425]: cannot find function `xyz` in this scope
```

**Fix:**
```bash
# 1. Clean build cache
cargo clean

# 2. Update dependencies
cargo update

# 3. Check Rust version
rustc --version
# Should be 1.70+

# 4. Update Rust if needed
rustup update stable

# 5. Try build again
cargo build --release
```

---

### Issue: Cloudflare Deployment Fails

**Symptoms:**
```
Error: You are not authenticated
Error: Failed to publish
```

**Fix:**
```bash
# 1. Re-authenticate
cd packages/server
pnpm wrangler login

# 2. Verify authentication
pnpm wrangler whoami

# 3. Check account ID in wrangler.toml
pnpm wrangler whoami | grep "Account ID"
# Compare with wrangler.toml

# 4. Try deployment again
pnpm deploy
```

---

## Recovery Procedures

### Emergency Rollback

**If production is completely broken:**

```bash
# 1. Rollback server immediately
cd packages/server
pnpm wrangler deployments list
pnpm wrangler rollback <last-known-good-deployment-id>

# 2. Rollback client binaries
sudo systemctl stop xswarm-voice xswarm-dashboard
sudo cp /opt/xswarm/backups/latest/xswarm-voice /opt/xswarm/target/release/
sudo cp /opt/xswarm/backups/latest/xswarm-dashboard /opt/xswarm/target/release/
sudo systemctl start xswarm-voice xswarm-dashboard

# 3. Verify services are back
curl https://xswarm-webhooks.your-subdomain.workers.dev/health
curl http://localhost:9998/health
```

---

### Database Recovery

**If database is corrupted or data is lost:**

```bash
# 1. Stop all services writing to database
sudo systemctl stop xswarm-voice xswarm-dashboard

# 2. Check point-in-time recovery options
turso db show xswarm-production | grep "retention"

# 3. Restore to specific time
turso db restore xswarm-production --timestamp "2025-10-28T10:00:00Z"

# Or create new database from backup (safer)
turso db create xswarm-production-restore --from-backup latest

# 4. Test restored database
turso db shell xswarm-production-restore "SELECT COUNT(*) FROM users"

# 5. Switch to restored database (update config.toml and secrets)

# 6. Restart services
sudo systemctl start xswarm-voice xswarm-dashboard
```

---

### Complete System Recovery

**If everything is broken:**

```bash
# 1. Deploy fresh server
cd packages/server
pnpm install
pnpm deploy

# 2. Restore database from backup
turso db restore xswarm-production --timestamp "2025-10-27T00:00:00Z"

# 3. Rebuild and deploy client
cd /opt/xswarm
git pull
cargo build --release
sudo systemctl restart xswarm-voice xswarm-dashboard

# 4. Restore configuration
sudo cp /opt/xswarm/backups/latest/config.toml /opt/xswarm/
sudo cp /opt/xswarm/backups/latest/.env /opt/xswarm/

# 5. Re-push all secrets
pnpm setup:secrets

# 6. Verify everything works
./scripts/deploy.sh --skip-tests --force
```

---

## Getting Help

### Support Channels

1. **Documentation:**
   - [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
   - [MONITORING_GUIDE.md](./MONITORING_GUIDE.md)
   - [SECURITY_GUIDE.md](./SECURITY_GUIDE.md)

2. **Logs:**
   ```bash
   # Gather all relevant logs
   cd packages/server && pnpm tail > server.log &
   sudo journalctl -u xswarm-voice -n 500 > voice.log
   sudo journalctl -u xswarm-dashboard -n 500 > dashboard.log
   ```

3. **System info:**
   ```bash
   uname -a > system-info.txt
   free -h >> system-info.txt
   df -h >> system-info.txt
   sudo systemctl status xswarm-* >> system-info.txt
   ```

4. **GitHub Issues:**
   - Create issue at: https://github.com/xswarm-dev/xswarm-boss/issues
   - Include logs and system info
   - Describe steps to reproduce

---

**Last Updated**: 2025-10-28
**Maintained by**: xSwarm Development Team
**Emergency Contact**: See SECURITY.md
