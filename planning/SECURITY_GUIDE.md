# xSwarm Boss - Security Configuration Guide

**Production Security Best Practices and Configuration**

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [API Security](#api-security)
3. [Network Security](#network-security)
4. [Data Protection](#data-protection)
5. [Access Control](#access-control)
6. [Secrets Management](#secrets-management)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Security Monitoring](#security-monitoring)
9. [Compliance](#compliance)
10. [Incident Response](#incident-response)

---

## Security Overview

### Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Network Security Layer                                 │
│  - Cloudflare DDoS protection                           │
│  - Firewall rules (ufw/firewalld)                       │
│  - Rate limiting                                        │
│  - IP whitelisting (optional)                           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Application Security Layer                             │
│  - Webhook signature verification (Twilio, Stripe)      │
│  - JWT authentication (Rust ↔ Server)                   │
│  - Input validation and sanitization                    │
│  - CORS configuration                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Data Security Layer                                    │
│  - Encryption at rest (Turso)                           │
│  - Encryption in transit (TLS 1.3)                      │
│  - Secrets in encrypted storage (Cloudflare Workers)    │
│  - PII minimization                                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Access Control Layer                                   │
│  - Admin-only endpoints                                 │
│  - User-level permissions                               │
│  - API key rotation                                     │
│  - Audit logging                                        │
└─────────────────────────────────────────────────────────┘
```

---

## API Security

### Authentication Methods

#### 1. Webhook Signature Verification

**Twilio Webhook Security:**
```javascript
// Automatic signature verification in packages/server
import twilio from 'twilio';

export async function verifyTwilioSignature(request, authToken) {
  const signature = request.headers.get('x-twilio-signature');
  const url = new URL(request.url).toString();
  const params = await request.formData();

  return twilio.validateRequest(authToken, signature, url, params);
}

// Usage in webhook handler
if (!verifyTwilioSignature(request, env.TWILIO_AUTH_TOKEN)) {
  return new Response('Invalid signature', { status: 403 });
}
```

**Stripe Webhook Security:**
```javascript
// Automatic signature verification via Stripe SDK
import Stripe from 'stripe';

const stripe = new Stripe(env.STRIPE_SECRET_KEY);

try {
  const event = stripe.webhooks.constructEvent(
    rawBody,
    signature,
    env.STRIPE_WEBHOOK_SECRET
  );
  // Process event
} catch (err) {
  return new Response('Invalid signature', { status: 403 });
}
```

---

#### 2. JWT Authentication (Rust ↔ Server)

**Token generation (server):**
```javascript
import jwt from '@tsndr/cloudflare-worker-jwt';

// Generate token for Rust client
const token = await jwt.sign({
  sub: 'rust-client',
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + (60 * 60 * 24 * 30), // 30 days
}, env.XSWARM_AUTH_TOKEN);
```

**Token verification (server):**
```javascript
// Verify token from Rust client
const authHeader = request.headers.get('authorization');
if (!authHeader?.startsWith('Bearer ')) {
  return new Response('Unauthorized', { status: 401 });
}

const token = authHeader.substring(7);
const isValid = await jwt.verify(token, env.XSWARM_AUTH_TOKEN);

if (!isValid) {
  return new Response('Invalid token', { status: 401 });
}
```

---

### Rate Limiting

**Implementation in config.toml:**
```toml
[security]
# Requests per minute per user
rate_limit_voice = 10      # Max 10 voice calls/minute
rate_limit_sms = 20        # Max 20 SMS/minute
rate_limit_api = 100       # Max 100 API requests/minute
```

**Cloudflare Workers rate limiting:**
```javascript
// Simple in-memory rate limiter (single worker)
const rateLimits = new Map();

function checkRateLimit(userId, limit, window) {
  const now = Date.now();
  const key = `${userId}:${window}`;
  const requests = rateLimits.get(key) || [];

  // Remove old requests outside window
  const validRequests = requests.filter(t => now - t < window * 1000);

  if (validRequests.length >= limit) {
    return false; // Rate limit exceeded
  }

  validRequests.push(now);
  rateLimits.set(key, validRequests);
  return true; // Within limit
}

// Usage
if (!checkRateLimit(userId, 10, 60)) { // 10 requests per 60 seconds
  return new Response('Rate limit exceeded', { status: 429 });
}
```

**Cloudflare Rate Limiting (Enterprise):**
- Use Cloudflare Dashboard → Security → Rate Limiting
- Configure rules per endpoint
- Automatic DDoS protection

---

### Input Validation

**Phone number validation:**
```javascript
function validatePhone(phone) {
  // E.164 format: +[country code][number]
  const phoneRegex = /^\+[1-9]\d{1,14}$/;
  return phoneRegex.test(phone);
}
```

**Email validation:**
```javascript
function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}
```

**SQL injection prevention:**
```javascript
// Use parameterized queries (libsql already does this)
const user = await db.execute({
  sql: 'SELECT * FROM users WHERE email = ?',
  args: [email] // Automatically escaped
});
```

**XSS prevention:**
```javascript
// Sanitize user input before storing/displaying
import DOMPurify from 'isomorphic-dompurify';

const sanitized = DOMPurify.sanitize(userInput);
```

---

## Network Security

### Firewall Configuration

#### Linux (ufw)

```bash
# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change port if non-standard)
sudo ufw allow 22/tcp

# Allow xSwarm services
sudo ufw allow 9998/tcp  # Voice bridge
sudo ufw allow 9999/tcp  # Supervisor

# Allow HTTP/HTTPS (if using nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

---

#### Linux (firewalld)

```bash
# Allow xSwarm services
sudo firewall-cmd --permanent --add-port=9998/tcp
sudo firewall-cmd --permanent --add-port=9999/tcp

# Allow HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# Reload firewall
sudo firewall-cmd --reload

# Check status
sudo firewall-cmd --list-all
```

---

### IP Whitelisting (Optional)

**Cloudflare Workers IP whitelist:**
```javascript
// In packages/server
const ADMIN_IPS = [
  '192.168.1.100',     // Office
  '203.0.113.0/24',    // VPN range
];

function isAdminIP(ip) {
  return ADMIN_IPS.some(range => {
    if (range.includes('/')) {
      // CIDR range check
      return isIPInRange(ip, range);
    }
    return ip === range;
  });
}

// Admin-only endpoint
if (request.url.includes('/admin/') && !isAdminIP(clientIP)) {
  return new Response('Forbidden', { status: 403 });
}
```

---

### DDoS Protection

**Cloudflare automatic protection:**
- Enabled by default for all Workers
- No configuration needed
- Protects against:
  - Layer 3/4 attacks (network/transport)
  - Layer 7 attacks (application)
  - Bot attacks

**Additional protection:**
- Enable "Under Attack Mode" in Cloudflare dashboard during active attack
- Use Cloudflare Load Balancing for failover
- Implement CAPTCHA for suspicious traffic

---

## Data Protection

### Encryption at Rest

**Turso Database:**
- Automatic encryption at rest (AES-256)
- No configuration needed
- Managed by Turso platform

**Cloudflare R2 Storage:**
- Automatic encryption at rest
- Optional: Server-side encryption with customer-managed keys

---

### Encryption in Transit

**TLS Configuration:**

**Cloudflare Workers:**
- Automatic TLS 1.3
- Automatic HTTP → HTTPS redirect
- Free SSL certificates

**nginx (Rust client reverse proxy):**
```nginx
# /etc/nginx/sites-available/xswarm

server {
    listen 443 ssl http2;
    server_name voice.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Strong SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS (force HTTPS)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Other security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://localhost:9998;
        # ... (rest of proxy config)
    }
}
```

**Let's Encrypt SSL certificates:**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d voice.yourdomain.com -d supervisor.yourdomain.com

# Auto-renewal (certbot installs cron job automatically)
sudo certbot renew --dry-run
```

---

### Data Minimization

**PII handling principles:**
1. **Collect only necessary data**
   - Email, phone number for communication
   - No passwords (authentication via external providers)
   - No sensitive personal information

2. **Store data securely**
   - Encrypted database (Turso)
   - No logs containing PII
   - Automatic backup encryption

3. **Delete data when no longer needed**
   - User account deletion removes all data
   - Logs rotated after 30 days
   - Backup retention: 90 days

**Data retention policy:**
```sql
-- Delete inactive users after 2 years
DELETE FROM users
WHERE subscription_tier = 'free'
AND updated_at < datetime('now', '-2 years');

-- Delete old logs
DELETE FROM usage_logs
WHERE created_at < datetime('now', '-90 days');
```

---

## Access Control

### User Permission Levels

**Admin (config.toml):**
```toml
[admin]
access_level = "superadmin"
can_provision_numbers = true
can_view_all_users = true
can_manage_subscriptions = true
can_manage_config = true
can_access_all_channels = true
```

**Premium User (database):**
```sql
INSERT INTO users (id, email, subscription_tier, permissions)
VALUES ('usr_123', 'user@example.com', 'premium', '{"voice": true, "sms": true, "email": true}');
```

**Free User (database):**
```sql
INSERT INTO users (id, email, subscription_tier, permissions)
VALUES ('usr_456', 'free@example.com', 'free', '{"voice": false, "sms": false, "email": true}');
```

---

### Admin-Only Endpoints

```javascript
// packages/server
const ADMIN_ENDPOINTS = [
  '/admin/users',
  '/admin/subscriptions',
  '/admin/config',
  '/admin/logs',
];

function isAdminRequest(request, user) {
  const url = new URL(request.url);
  return ADMIN_ENDPOINTS.some(endpoint => url.pathname.startsWith(endpoint))
    && user.access_level === 'superadmin';
}

// Usage
if (isAdminRequest(request, user) && user.access_level !== 'superadmin') {
  return new Response('Forbidden', { status: 403 });
}
```

---

### API Key Rotation

**Twilio Auth Token:**
```bash
# 1. Generate new secondary token in Twilio console
# 2. Update .env with new token
# 3. Push to Cloudflare Workers
echo $NEW_TWILIO_AUTH_TOKEN | pnpm wrangler secret put TWILIO_AUTH_TOKEN

# 4. Wait 24 hours for propagation
# 5. Revoke old token in Twilio console
```

**Stripe API Key:**
```bash
# 1. Create new restricted key in Stripe dashboard
# 2. Update .env with new key
# 3. Push to Cloudflare Workers
echo $NEW_STRIPE_SECRET_KEY | pnpm wrangler secret put STRIPE_SECRET_KEY

# 4. Wait 24 hours
# 5. Delete old key in Stripe dashboard
```

**Recommended rotation schedule:**
- Every 90 days for production keys
- Every 30 days for high-security deployments
- Immediately if key is compromised

---

## Secrets Management

### Environment Variables

**Production .env file:**
```bash
# Set restrictive permissions
chmod 600 .env
chown xswarm:xswarm .env

# Verify
ls -l .env
# Should show: -rw------- 1 xswarm xswarm
```

---

### Cloudflare Workers Secrets

**Encrypted storage:**
- All secrets encrypted at rest (AES-256)
- Accessible only to your Worker at runtime
- Never exposed in logs or responses

**Push secrets securely:**
```bash
# From file (recommended)
cat .env | grep ANTHROPIC_API_KEY | cut -d'=' -f2 | \
  pnpm wrangler secret put ANTHROPIC_API_KEY

# From stdin (manual)
pnpm wrangler secret put ANTHROPIC_API_KEY
# (Paste secret, press Ctrl+D)
```

---

### Secret Rotation Checklist

**When rotating secrets:**
- [ ] Generate new secret/key
- [ ] Update .env file locally
- [ ] Test locally with new secret
- [ ] Push to Cloudflare Workers (server)
- [ ] Update systemd service EnvironmentFile (client)
- [ ] Restart affected services
- [ ] Verify functionality
- [ ] Wait 24-48 hours for full propagation
- [ ] Revoke old secret/key
- [ ] Document rotation in logs

---

## SSL/TLS Configuration

### Certificate Management

**Let's Encrypt (Free):**
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate (interactive)
sudo certbot --nginx -d yourdomain.com

# Or non-interactive
sudo certbot certonly --nginx \
  -d voice.yourdomain.com \
  -d supervisor.yourdomain.com \
  --agree-tos \
  --email admin@yourdomain.com \
  --non-interactive

# Test auto-renewal
sudo certbot renew --dry-run
```

**Certificate expiration monitoring:**
```bash
# Check expiration
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | \
  openssl x509 -noout -dates

# Automated monitoring (cron)
0 0 * * * certbot renew --quiet --deploy-hook "systemctl reload nginx"
```

---

### WebSocket SSL (wss://)

**nginx configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name voice.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:9998;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # SSL-specific headers
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## Security Monitoring

### Audit Logging

**Log security events:**
```javascript
// packages/server
function auditLog(event, user, details) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    event,
    user_id: user.id,
    user_email: user.email,
    ip_address: request.headers.get('cf-connecting-ip'),
    details,
  }));
}

// Usage
auditLog('user_login', user, { method: 'phone' });
auditLog('subscription_upgrade', user, { from: 'free', to: 'premium' });
auditLog('admin_action', user, { action: 'view_all_users' });
```

---

### Failed Authentication Tracking

```javascript
// Track failed auth attempts
const failedAttempts = new Map();

function trackFailedAuth(identifier) {
  const key = `failed:${identifier}`;
  const attempts = failedAttempts.get(key) || 0;
  failedAttempts.set(key, attempts + 1);

  if (attempts >= 5) {
    // Lock account or rate limit
    auditLog('account_locked', { identifier }, { attempts });
    return true; // Locked
  }
  return false; // Not locked
}

function clearFailedAuth(identifier) {
  failedAttempts.delete(`failed:${identifier}`);
}
```

---

### Security Alerts

**Alert on suspicious activity:**
```bash
# Monitor for multiple failed auth attempts
journalctl -u xswarm-voice -f | grep "authentication failed" | \
  awk '{print $NF}' | sort | uniq -c | \
  awk '$1 > 5 {print "Alert: " $1 " failed attempts from " $2}'

# Email alert script
echo "Security alert: Multiple failed auth attempts detected" | \
  mail -s "xSwarm Security Alert" admin@yourdomain.com
```

---

## Compliance

### GDPR Compliance

**User rights implementation:**

**1. Right to Access:**
```javascript
// GET /api/user/data
async function getUserData(userId) {
  const user = await db.execute({
    sql: 'SELECT * FROM users WHERE id = ?',
    args: [userId]
  });

  const logs = await db.execute({
    sql: 'SELECT * FROM usage_logs WHERE user_id = ? ORDER BY created_at DESC',
    args: [userId]
  });

  return { user: user.rows[0], logs: logs.rows };
}
```

**2. Right to Deletion:**
```javascript
// DELETE /api/user
async function deleteUser(userId) {
  // Delete user data
  await db.execute({
    sql: 'DELETE FROM usage_logs WHERE user_id = ?',
    args: [userId]
  });

  await db.execute({
    sql: 'DELETE FROM users WHERE id = ?',
    args: [userId]
  });

  // Cancel Stripe subscription
  if (user.stripe_subscription_id) {
    await stripe.subscriptions.cancel(user.stripe_subscription_id);
  }

  auditLog('user_deleted', user, { reason: 'user_request' });
}
```

**3. Right to Portability:**
```javascript
// GET /api/user/export
async function exportUserData(userId) {
  const data = await getUserData(userId);

  return new Response(JSON.stringify(data, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Content-Disposition': `attachment; filename="xswarm-data-${userId}.json"`,
    },
  });
}
```

---

### Data Processing Agreement

**Required for GDPR compliance:**
- xSwarm (you) = Data Controller
- Twilio = Data Processor (DPA available)
- SendGrid = Data Processor (DPA available)
- Stripe = Data Processor (DPA available)
- Turso = Data Processor (DPA available)

**Action items:**
1. Review and sign DPAs with all processors
2. Document data flows in privacy policy
3. Implement user consent mechanisms
4. Provide privacy policy and terms of service

---

## Incident Response

### Security Incident Checklist

**P1: Data Breach**

1. **Immediate (within 1 hour):**
   - [ ] Isolate affected systems
   - [ ] Preserve logs and evidence
   - [ ] Notify security team
   - [ ] Begin investigation

2. **Short-term (within 24 hours):**
   - [ ] Identify scope of breach
   - [ ] Determine affected users
   - [ ] Patch vulnerability
   - [ ] Rotate all secrets/keys

3. **Medium-term (within 72 hours):**
   - [ ] Notify affected users (GDPR requirement)
   - [ ] Report to authorities if required
   - [ ] Publish incident report

4. **Long-term (within 30 days):**
   - [ ] Complete post-mortem
   - [ ] Implement prevention measures
   - [ ] Update security policies
   - [ ] Conduct security audit

---

### Compromised API Key

**Immediate actions:**
```bash
# 1. Revoke compromised key immediately
# (In provider's dashboard)

# 2. Generate new key
# (In provider's dashboard)

# 3. Update .env
nano .env

# 4. Push to Cloudflare Workers
pnpm wrangler secret put COMPROMISED_KEY_NAME

# 5. Restart Rust services
sudo systemctl restart xswarm-voice xswarm-dashboard

# 6. Monitor logs for suspicious activity
pnpm wrangler tail
sudo journalctl -u xswarm-voice -f
```

---

## Related Documentation

- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) - Deployment procedures
- [MONITORING_GUIDE.md](./MONITORING_GUIDE.md) - Security monitoring
- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) - Security issues

---

**Last Updated**: 2025-10-28
**Security Contact**: security@yourdomain.com
**Responsible Disclosure**: See SECURITY.md in repository
