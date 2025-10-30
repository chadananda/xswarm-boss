# xSwarm Boss - Production Deployment Guide

**Complete Step-by-Step Guide for Zero-Downtime Production Deployment**

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Environment Configuration](#environment-configuration)
4. [Server Deployment (Cloudflare Workers)](#server-deployment-cloudflare-workers)
5. [Client Deployment (Rust + MOSHI)](#client-deployment-rust--moshi)
6. [Service Configuration](#service-configuration)
7. [Testing & Verification](#testing--verification)
8. [Post-Deployment Tasks](#post-deployment-tasks)
9. [Rollback Procedures](#rollback-procedures)

---

## Pre-Deployment Checklist

### Required Accounts & Services

- [ ] **Cloudflare Account** - Workers hosting (free tier sufficient)
- [ ] **Turso Account** - Database hosting (free tier sufficient)
- [ ] **Twilio Account** - Voice & SMS ($15 trial credit available)
- [ ] **SendGrid Account** - Email delivery (free tier: 100 emails/day)
- [ ] **Stripe Account** - Payment processing (free, pay per transaction)
- [ ] **Domain Name** - For custom branding (optional but recommended)
- [ ] **Hardware** - M1/M2 Mac or Linux GPU server (see [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md))

### Required Tools

```bash
# Verify installations
node --version      # v18+ required
pnpm --version      # v8+ required
rust --version      # 1.70+ required
python3 --version   # 3.10+ required
turso --version     # Latest
stripe --version    # Latest (optional, for webhook testing)
```

### Required Knowledge

- Basic command line usage
- Git operations
- Understanding of environment variables
- Basic networking (ports, firewalls)

---

## Infrastructure Setup

### 1. Cloudflare Setup

#### Create Account
1. Go to [cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
2. Verify email address
3. (Optional) Add custom domain for branding

#### Get API Credentials
```bash
# Login to Cloudflare
cd packages/server
pnpm wrangler login

# Get your account ID
pnpm wrangler whoami
# Copy the Account ID for later
```

#### Configure Wrangler
Edit `packages/server/wrangler.toml`:
```toml
account_id = "YOUR_ACCOUNT_ID_HERE"
```

---

### 2. Turso Database Setup

#### Create Database
```bash
# Install Turso CLI
curl -sSfL https://get.tur.so/install.sh | bash

# Login
turso auth login

# Create production database
turso db create xswarm-production --location pdx

# Get database URL
turso db show xswarm-production
# Copy the URL: libsql://xswarm-production-your-org.turso.io
```

#### Create Schema
```bash
# Connect to database
turso db shell xswarm-production

# Create tables (paste from planning/DATABASE_SCHEMA.md)
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  phone TEXT,
  xswarm_email TEXT NOT NULL UNIQUE,
  xswarm_phone TEXT,
  subscription_tier TEXT DEFAULT 'free',
  persona TEXT DEFAULT 'boss',
  wake_word TEXT DEFAULT 'hey boss',
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_xswarm_phone ON users(xswarm_phone);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);

CREATE TABLE usage_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_data TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at);

-- Exit shell
.quit
```

#### Generate Auth Token
```bash
# Create long-lived auth token
turso db tokens create xswarm-production --expiration none

# Copy the token (starts with eyJhbGciOi...)
# Save to .env as TURSO_AUTH_TOKEN
```

#### (Optional) Enable Replication
```bash
# Add replica regions for global edge caching
turso db replicate xswarm-production --location iad  # US East
turso db replicate xswarm-production --location fra  # Europe
```

---

### 3. Twilio Setup

#### Create Account
1. Go to [twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Complete phone verification
3. Get $15 trial credit

#### Get Credentials
```bash
# From console.twilio.com
# Copy these values:
ACCOUNT_SID: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AUTH_TOKEN: your_auth_token_here (SECRET)
```

#### Buy Phone Numbers
```bash
# Option 1: Via console.twilio.com
# Phone Numbers → Buy a number → Search for toll-free (+1 800/888/etc.)

# Option 2: Via Twilio CLI
twilio phone-numbers:buy --search-tollfree --country-code US
```

**Costs:**
- Toll-free number: $2/month
- Voice calls: $0.013/minute incoming
- SMS messages: $0.0075/message incoming

---

### 4. SendGrid Setup

#### Create Account
1. Go to [sendgrid.com/free](https://signup.sendgrid.com/)
2. Complete email verification
3. Choose Free plan (100 emails/day)

#### Domain Authentication (Recommended)
```bash
# In SendGrid dashboard:
# Settings → Sender Authentication → Authenticate Your Domain

# Add these DNS records to your domain:
# (SendGrid will provide specific values)
```

**Required DNS Records:**
- SPF record (TXT)
- DKIM records (CNAME x2)
- DMARC record (TXT, optional)

#### Create API Key
```bash
# In SendGrid dashboard:
# Settings → API Keys → Create API Key
# Name: xswarm-production
# Permissions: Full Access

# Copy the API key (starts with SG.)
# Save to .env as SENDGRID_API_KEY_LIVE
```

---

### 5. Stripe Setup

#### Create Account
1. Go to [dashboard.stripe.com/register](https://dashboard.stripe.com/register)
2. Complete business verification
3. Connect bank account for payouts

#### Create Products & Prices
```bash
# In Stripe dashboard:
# Products → Add product

# Create these products:
1. Premium Subscription
   - Name: "xSwarm Premium"
   - Price: $9.99/month (recurring)
   - Copy price ID: price_1Oxxxxxxxxxxxxxxxxxxxxx

2. Voice Minutes (Metered)
   - Name: "Voice Minutes"
   - Price: $0.013 per unit
   - Billing: Metered usage
   - Copy price ID: price_1Oxxxxxxxxxxxxxxxxxxxxx

3. SMS Messages (Metered)
   - Name: "SMS Messages"
   - Price: $0.0075 per unit
   - Billing: Metered usage
   - Copy price ID: price_1Oxxxxxxxxxxxxxxxxxxxxx

4. Additional Phone Numbers
   - Name: "Additional Phone Number"
   - Price: $2.00/month (recurring)
   - Billing: Per-unit
   - Copy price ID: price_1Oxxxxxxxxxxxxxxxxxxxxx
```

#### Get API Keys
```bash
# In Stripe dashboard:
# Developers → API keys

# Copy these values:
Publishable key: pk_test_... (safe to commit)
Secret key: sk_test_... (SECRET)
```

---

### 6. Cloudflare R2 Storage Setup

#### Create R2 Bucket
```bash
# In Cloudflare dashboard:
# R2 → Create bucket
# Name: xswarm-production
# Location: Automatic
```

#### Create API Token
```bash
# Cloudflare dashboard:
# R2 → Manage R2 API Tokens → Create API Token
# Name: xswarm-production
# Permissions: Object Read & Write

# Copy credentials:
Access Key ID: xxx
Secret Access Key: xxx (SECRET)
Endpoint: https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
```

---

## Environment Configuration

### 1. Create Production .env File

```bash
# Copy template
cp .env.example .env

# Edit .env with production values
nano .env
```

**Complete .env template:**

```bash
# =============================================================================
# Environment
# =============================================================================
ENVIRONMENT=production

# =============================================================================
# AI Providers
# =============================================================================
ANTHROPIC_API_KEY=sk-ant-xxxxx...
OPENAI_API_KEY=sk-xxxxx...

# =============================================================================
# Twilio (Voice & SMS)
# =============================================================================
TWILIO_AUTH_TOKEN_LIVE=your_live_auth_token

# =============================================================================
# SendGrid (Email)
# =============================================================================
SENDGRID_API_KEY_LIVE=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# =============================================================================
# Stripe (Payments)
# =============================================================================
STRIPE_SECRET_KEY_LIVE=***REMOVED***

# NOTE: Webhook secrets are set automatically by deployment script
# STRIPE_WEBHOOK_SECRET_LIVE=***REMOVED***

# =============================================================================
# Turso (Database)
# =============================================================================
TURSO_AUTH_TOKEN=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...

# =============================================================================
# Cloudflare R2 (Storage)
# =============================================================================
S3_ACCESS_KEY_ID=your_r2_access_key
S3_SECRET_ACCESS_KEY=your_r2_secret_key

# =============================================================================
# Cloudflare Workers (Deployment)
# =============================================================================
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token

# =============================================================================
# Server Auth (Rust Client ↔ Node.js Server)
# =============================================================================
# Generate with: openssl rand -hex 32
XSWARM_AUTH_TOKEN=your_random_64_character_hex_string
```

---

### 2. Configure Production config.toml

```bash
# Copy production template
cp config/production.toml config.toml

# Edit with your specific values
nano config.toml
```

**Key values to update:**
- `[server] host` - Your Cloudflare Workers URL
- `[admin]` - Your contact information
- `[twilio] account_sid` - From Twilio console
- `[stripe.prices]` - Price IDs from Stripe
- `[sendgrid] domain` - Your verified domain
- `[turso] database_url` - From Turso
- `[storage] endpoint` - From Cloudflare R2

---

### 3. Push Secrets to Cloudflare Workers

```bash
# Automated script (recommended)
pnpm setup:secrets

# This will:
# 1. Read secrets from .env
# 2. Push to Cloudflare Workers encrypted storage
# 3. Verify each secret is set correctly
```

**Manual alternative:**
```bash
cd packages/server

# Push each secret individually
echo $TWILIO_AUTH_TOKEN_LIVE | pnpm wrangler secret put TWILIO_AUTH_TOKEN_LIVE
echo $SENDGRID_API_KEY_LIVE | pnpm wrangler secret put SENDGRID_API_KEY_LIVE
echo $STRIPE_SECRET_KEY_LIVE | pnpm wrangler secret put STRIPE_SECRET_KEY_LIVE
echo $TURSO_AUTH_TOKEN | pnpm wrangler secret put TURSO_AUTH_TOKEN
echo $S3_ACCESS_KEY_ID | pnpm wrangler secret put S3_ACCESS_KEY_ID
echo $S3_SECRET_ACCESS_KEY | pnpm wrangler secret put S3_SECRET_ACCESS_KEY
echo $XSWARM_AUTH_TOKEN | pnpm wrangler secret put XSWARM_AUTH_TOKEN

# Verify all secrets
pnpm wrangler secret list
```

---

## Server Deployment (Cloudflare Workers)

### 1. Build & Test Locally

```bash
# Install dependencies
pnpm install

# Test locally with production config
cd packages/server
pnpm dev

# In another terminal, test health endpoint
curl http://localhost:8787/health
# Should return: {"status":"ok","service":"xswarm-webhooks"}
```

---

### 2. Deploy to Cloudflare

```bash
# From project root
pnpm deploy:server

# Or from packages/server
cd packages/server
pnpm deploy
```

**Expected output:**
```
⛅️ wrangler 3.28.0
------------------
Total Upload: 45.23 KiB / gzip: 12.34 KiB
Uploaded xswarm-webhooks (0.89 sec)
Published xswarm-webhooks (0.25 sec)
  https://xswarm-webhooks.your-subdomain.workers.dev
Current Deployment ID: abc12345-6789-def0-1234-567890abcdef
```

**Save your Worker URL!** You'll need it for:
- config.toml (`[server] host`)
- Twilio webhooks
- Stripe webhooks

---

### 3. Test Production Deployment

```bash
# Test health endpoint
curl https://xswarm-webhooks.your-subdomain.workers.dev/health

# Should return:
# {"status":"ok","service":"xswarm-webhooks","timestamp":"..."}

# Test identity API (requires auth token)
curl -H "Authorization: Bearer $XSWARM_AUTH_TOKEN" \
  https://xswarm-webhooks.your-subdomain.workers.dev/api/identity/admin

# Should return admin user data
```

---

### 4. Configure Webhook Endpoints

#### Twilio Webhooks

```bash
# Automated setup (recommended)
pnpm setup:twilio

# Manual setup:
# 1. Go to console.twilio.com
# 2. Phone Numbers → Active Numbers → Select your number
# 3. Voice Configuration:
#    - Webhook: https://xswarm-webhooks.your-subdomain.workers.dev/voice/{userId}
#    - Method: POST
# 4. Messaging Configuration:
#    - Webhook: https://xswarm-webhooks.your-subdomain.workers.dev/sms/{userId}
#    - Method: POST
# 5. Save
```

#### Stripe Webhooks

```bash
# Automated setup (recommended)
pnpm setup:webhooks --live

# This will:
# 1. Create webhook endpoint in Stripe
# 2. Subscribe to required events
# 3. Push webhook secret to Cloudflare Workers

# Manual setup:
# 1. Go to dashboard.stripe.com/webhooks
# 2. Add endpoint: https://xswarm-webhooks.your-subdomain.workers.dev/stripe/webhook
# 3. Select events:
#    - customer.subscription.created
#    - customer.subscription.updated
#    - customer.subscription.deleted
#    - invoice.payment_succeeded
#    - invoice.payment_failed
# 4. Copy webhook signing secret (whsec_...)
# 5. Push to Workers:
#    echo "whsec_..." | pnpm wrangler secret put STRIPE_WEBHOOK_SECRET_LIVE
```

---

## Client Deployment (Rust + MOSHI)

### 1. Prepare Deployment Environment

#### macOS (Recommended)
```bash
# Install system dependencies
brew install portaudio

# Install Rust (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Python dependencies
cd packages/voice
python3 -m pip install -e .
```

#### Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  pkg-config \
  libssl-dev \
  portaudio19-dev \
  libasound2-dev \
  python3-pip \
  python3-venv

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install CUDA (for GPU acceleration)
# Follow: https://developer.nvidia.com/cuda-downloads

# Install Python dependencies
cd packages/voice
python3 -m pip install -e .
```

---

### 2. Build Rust Client

```bash
# From project root
cargo build --release

# Binaries will be in:
# - target/release/xswarm (main CLI)
# - target/release/xswarm-voice (voice bridge)
# - target/release/xswarm-dashboard (supervisor TUI)
```

**Build time:**
- First build: 5-10 minutes (downloads dependencies)
- Subsequent builds: 1-2 minutes (incremental)

---

### 3. Download MOSHI Models

```bash
# Models are downloaded automatically on first use
# Or pre-download:

# macOS (Apple Silicon)
python3 << EOF
from moshi_mlx import load_model
model = load_model("kyutai/moshika-mlx-q4")
print("✓ MOSHI model downloaded and cached")
EOF

# Linux (CUDA)
python3 << EOF
from moshi import load_model
model = load_model("kyutai/moshika-pytorch-bf16")
print("✓ MOSHI model downloaded and cached")
EOF
```

**Download size:** ~4GB
**Cache location:** `~/.cache/huggingface/hub/`

---

### 4. Install System Services

#### Create systemd Service Files

**Voice Bridge Service:**
```bash
sudo nano /etc/systemd/system/xswarm-voice.service
```

```ini
[Unit]
Description=xSwarm Voice Bridge
After=network.target

[Service]
Type=simple
User=xswarm
Group=xswarm
WorkingDirectory=/opt/xswarm
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="RUST_LOG=info"
ExecStart=/opt/xswarm/target/release/xswarm-voice
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=16G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
```

**Dashboard Service:**
```bash
sudo nano /etc/systemd/system/xswarm-dashboard.service
```

```ini
[Unit]
Description=xSwarm Supervisor Dashboard
After=network.target xswarm-voice.service
Requires=xswarm-voice.service

[Service]
Type=simple
User=xswarm
Group=xswarm
WorkingDirectory=/opt/xswarm
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="RUST_LOG=info"
ExecStart=/opt/xswarm/target/release/xswarm-dashboard
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

#### Install and Enable Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable xswarm-voice
sudo systemctl enable xswarm-dashboard

# Start services
sudo systemctl start xswarm-voice
sudo systemctl start xswarm-dashboard

# Check status
sudo systemctl status xswarm-voice
sudo systemctl status xswarm-dashboard

# View logs
sudo journalctl -u xswarm-voice -f
sudo journalctl -u xswarm-dashboard -f
```

---

## Service Configuration

### 1. Configure Firewall

```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/xswarm/target/release/xswarm-voice
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/xswarm/target/release/xswarm-dashboard

# Linux (ufw)
sudo ufw allow 9998/tcp  # Voice bridge
sudo ufw allow 9999/tcp  # Supervisor
sudo ufw enable

# Linux (firewalld)
sudo firewall-cmd --permanent --add-port=9998/tcp
sudo firewall-cmd --permanent --add-port=9999/tcp
sudo firewall-cmd --reload
```

---

### 2. Configure Reverse Proxy (Optional but Recommended)

**nginx configuration:**
```nginx
# /etc/nginx/sites-available/xswarm

upstream xswarm_voice {
    server 127.0.0.1:9998;
}

upstream xswarm_supervisor {
    server 127.0.0.1:9999;
}

server {
    listen 443 ssl http2;
    server_name voice.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://xswarm_voice;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeout
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}

server {
    listen 443 ssl http2;
    server_name supervisor.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://xswarm_supervisor;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeout
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

**Enable and test:**
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/xswarm /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Testing & Verification

### 1. Health Checks

```bash
# Server (Cloudflare Workers)
curl https://xswarm-webhooks.your-subdomain.workers.dev/health

# Voice bridge
curl http://localhost:9998/health

# Supervisor
curl http://localhost:9999/health
```

---

### 2. Test Voice Call

```bash
# Make a test call to your xSwarm number
# From your phone, call: +1-800-XXX-XXXX

# Check logs
sudo journalctl -u xswarm-voice -f

# Should see:
# - Twilio webhook received
# - WebSocket connection established
# - MOSHI processing audio
# - Response generated
```

---

### 3. Test SMS

```bash
# Send SMS to your xSwarm number
# Text: "status"

# Check Worker logs
cd packages/server
pnpm tail

# Should see:
# - SMS webhook received
# - User identified
# - Response sent via Twilio
```

---

### 4. Test Email

```bash
# Send email to: yourname@yourdomain.com

# Check SendGrid webhook logs
curl https://xswarm-webhooks.your-subdomain.workers.dev/sendgrid/webhook
```

---

### 5. Test Payment Flow

```bash
# Use Stripe test card: 4242 4242 4242 4242
# 1. Visit your signup page
# 2. Enter test card details
# 3. Complete subscription

# Check Stripe webhook logs
cd packages/server
pnpm tail

# Should see:
# - customer.subscription.created
# - User upgraded to premium
# - Twilio number provisioned
```

---

## Post-Deployment Tasks

### 1. Monitor Logs

```bash
# Server logs (Cloudflare Workers)
cd packages/server
pnpm tail

# Client logs (systemd)
sudo journalctl -u xswarm-voice -f
sudo journalctl -u xswarm-dashboard -f

# Database logs (Turso)
turso db logs xswarm-production
```

---

### 2. Set Up Monitoring

**Health check endpoints:**
- Server: `https://xswarm-webhooks.your-subdomain.workers.dev/health`
- Voice: `http://localhost:9998/health`
- Supervisor: `http://localhost:9999/health`

**Recommended monitoring services:**
- UptimeRobot (free tier: 50 monitors)
- Pingdom
- Datadog
- Cloudflare's built-in analytics

---

### 3. Configure Backups

```bash
# Turso automatic backups (enabled by default)
# 30-day point-in-time recovery

# Manual database backup
turso db backup xswarm-production

# R2 backup configuration (already in config.toml)
# Daily backups at 3 AM UTC
```

---

### 4. Document Deployed Configuration

```bash
# Create deployment notes
cat > DEPLOYMENT_NOTES.md << EOF
# xSwarm Production Deployment

**Deployed:** $(date)
**Version:** $(git rev-parse HEAD)

## URLs
- Server: https://xswarm-webhooks.your-subdomain.workers.dev
- Voice Bridge: wss://voice.yourdomain.com
- Supervisor: wss://supervisor.yourdomain.com

## Phone Numbers
- Admin: +1-800-XXX-XXXX

## Database
- Turso URL: libsql://xswarm-production-your-org.turso.io
- Regions: pdx (primary), iad, fra (replicas)

## Monitoring
- Health checks: Every 5 minutes via UptimeRobot
- Logs: Cloudflare Workers dashboard + systemd journal

## Contacts
- Admin: admin@yourdomain.com
- Emergency: +1-555-123-4567
EOF
```

---

## Rollback Procedures

### Server Rollback (Cloudflare Workers)

```bash
# View deployment history
cd packages/server
pnpm wrangler deployments list

# Rollback to previous version
pnpm wrangler rollback <deployment-id>

# Or rollback to specific version
pnpm wrangler rollback abc12345
```

---

### Client Rollback (Rust)

```bash
# Stop services
sudo systemctl stop xswarm-voice
sudo systemctl stop xswarm-dashboard

# Restore previous binary
sudo cp /opt/xswarm/backup/xswarm-voice /opt/xswarm/target/release/
sudo cp /opt/xswarm/backup/xswarm-dashboard /opt/xswarm/target/release/

# Restart services
sudo systemctl start xswarm-voice
sudo systemctl start xswarm-dashboard
```

---

### Database Rollback (Turso)

```bash
# Point-in-time recovery (within 30 days)
turso db restore xswarm-production --timestamp "2025-10-27T10:00:00Z"

# Or restore from specific backup
turso db restore xswarm-production --backup-id <backup-id>
```

---

## Troubleshooting

See [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) for detailed troubleshooting procedures.

**Common issues:**
- Webhook signature validation failures → Check auth tokens
- MOSHI model not loading → Verify HuggingFace cache permissions
- WebSocket connection timeouts → Check firewall rules
- Database connection errors → Verify Turso auth token

---

## Related Documentation

- [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md) - Hardware & software requirements
- [MONITORING_GUIDE.md](./MONITORING_GUIDE.md) - Operations and monitoring
- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - Security configuration
- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) - Common issues and solutions

---

**Deployment Complete!** 🚀

Your xSwarm Boss system is now live and ready to handle voice calls, SMS, and emails.

**Next steps:**
1. Monitor logs for first 24 hours
2. Test all communication channels
3. Configure monitoring alerts
4. Review security settings
5. Plan for scaling

---

**Last Updated**: 2025-10-28
**Support**: See [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)
