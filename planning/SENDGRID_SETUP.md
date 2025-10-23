# SendGrid Setup Guide

This guide walks you through setting up SendGrid for xSwarm's email communication system.

## Overview

SendGrid (owned by Twilio) provides email delivery infrastructure for the xSwarm multi-channel communication system. Each user gets a unique email address (`username@xswarm.ai`) that their xSwarm instance uses to communicate.

**Key Features:**
- Send emails from `username@xswarm.ai`
- Receive emails at `username@xswarm.ai`
- Whitelist-based security (only owner's email accepted)
- Free tier: 100 emails/day (3,000/month)
- Excellent deliverability

---

## Step 1: Create SendGrid Account

### Via Twilio (Recommended)

If you already have a Twilio account:

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Email** → **SendGrid Email**
3. Click **Create SendGrid Account**
4. Follow the integration wizard
5. Your SendGrid account is automatically linked to Twilio

**Benefits:**
- Single billing (Twilio + SendGrid combined)
- Easier account management
- Potential bundle discounts

### Direct SendGrid Signup

Alternatively, sign up directly:

1. Go to [SendGrid.com](https://sendgrid.com/pricing/)
2. Click **Try for Free**
3. Select **Free Plan**: 100 emails/day forever
4. Complete signup form
5. Verify your email address

---

## Step 2: Domain Verification

To send emails from `@xswarm.ai`, you must verify the domain.

### DNS Configuration

1. **In SendGrid Console:**
   - Go to **Settings** → **Sender Authentication**
   - Click **Authenticate Your Domain**
   - Select DNS host (e.g., Cloudflare, Namecheap, GoDaddy)
   - Domain: `xswarm.ai`

2. **Add DNS Records:**

SendGrid will provide these DNS records to add:

```dns
# SPF Record (TXT)
Type: TXT
Host: @
Value: v=spf1 include:sendgrid.net ~all

# DKIM Records (CNAME)
Type: CNAME
Host: s1._domainkey
Value: s1.domainkey.u12345678.wl123.sendgrid.net

Type: CNAME
Host: s2._domainkey
Value: s2.domainkey.u12345678.wl123.sendgrid.net

# DMARC Record (TXT) - Optional but recommended
Type: TXT
Host: _dmarc
Value: v=DMARC1; p=none; pct=100; rua=mailto:dmarc@xswarm.ai
```

3. **Verify Domain:**
   - Wait 24-48 hours for DNS propagation
   - Click **Verify** in SendGrid Console
   - Status should show **Verified**

---

## Step 3: Get API Key

1. **In SendGrid Console:**
   - Go to **Settings** → **API Keys**
   - Click **Create API Key**

2. **Configure API Key:**
   - Name: `xSwarm Production`
   - Permissions: **Full Access** (or restricted access if you prefer)
   - Click **Create & View**

3. **Copy API Key:**
   ```
   SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

   **⚠️ IMPORTANT:** This is shown only once! Copy it immediately.

4. **Add to `.env`:**
   ```bash
   SENDGRID_API_KEY="SG.your_api_key_here"
   ```

---

## Step 4: Configure Inbound Parse (Receiving Emails)

To receive emails sent to `username@xswarm.ai`, set up Inbound Parse:

1. **In SendGrid Console:**
   - Go to **Settings** → **Inbound Parse**
   - Click **Add Host & URL**

2. **Configure Parse Webhook:**
   ```
   Domain: xswarm.ai
   Subdomain: (leave blank for root domain)
   Destination URL: https://your-server.com/email/incoming

   Options:
   ✓ Check incoming emails for spam
   ✓ POST the raw, full MIME message
   ```

3. **Add MX Record to DNS:**
   ```dns
   Type: MX
   Host: @
   Priority: 10
   Value: mx.sendgrid.net
   ```

4. **Verify MX Record:**
   ```bash
   dig xswarm.ai MX
   # Should show: mx.sendgrid.net
   ```

---

## Step 5: Test Email Sending

Run the test script to verify SendGrid is working:

```bash
npm run test:sendgrid
```

The script will:
1. Verify API key
2. Send a test email from `test@xswarm.ai`
3. Check delivery status
4. Display any errors

---

## Step 6: Test Email Receiving

1. **Start xSwarm server** with webhook endpoint active
2. **Send email** to your configured address (e.g., `username@xswarm.ai`)
3. **Check webhook logs** to confirm receipt

Test webhook locally with ngrok:

```bash
# Install ngrok
npm install -g ngrok

# Expose local server
ngrok http 3000

# Update SendGrid Inbound Parse URL
# Destination: https://your-id.ngrok.io/email/incoming
```

---

## Pricing

### Free Tier
- **100 emails/day** (3,000/month)
- Perfect for personal use
- All features included
- No credit card required

### Paid Plans (if needed)
| Plan | Price | Emails/Month | Use Case |
|------|-------|--------------|----------|
| **Essentials** | $19.95/mo | 50,000 | Small team |
| **Pro** | $89.95/mo | 100,000 | Growing business |
| **Premier** | Custom | Unlimited | Enterprise |

**For xSwarm:** Free tier is sufficient for most users (low-volume, personal communication).

---

## Architecture

### Email Flow

**Outbound (xSwarm → User):**
```
xSwarm detects issue
  ↓
Urgency: Low/Medium → Email selected
  ↓
SendGrid API: /mail/send
  ↓
Email delivered to user's real email
  ↓
User sees: From "HAL 9000 <hal@xswarm.ai>"
```

**Inbound (User → xSwarm):**
```
User sends email to hal@xswarm.ai
  ↓
MX Record: mx.sendgrid.net
  ↓
SendGrid Inbound Parse
  ↓
Webhook POST: https://your-server.com/email/incoming
  ↓
xSwarm checks whitelist (user_email)
  ↓
If authorized: Process email
  ↓
AI generates response
  ↓
Reply via SendGrid
```

---

## Security

### Whitelist Enforcement

```rust
// Webhook handler validates sender
async fn handle_incoming_email(from: &str, config: &CommunicationConfig) -> EmailResponse {
    if from == config.user_email {
        // Authorized - process email
        EmailResponse::Process
    } else {
        // Unauthorized - reject silently
        EmailResponse::Reject
    }
}
```

### API Key Security

- Store API key in `.env` (never commit to git)
- Use restricted API key permissions if possible
- Rotate keys periodically
- Monitor usage in SendGrid dashboard

### DNS Security

- Enable DMARC to prevent spoofing
- Use SPF to whitelist SendGrid servers
- Monitor DMARC reports for unauthorized sending attempts

---

## Troubleshooting

### Email Not Sending

**Check API Key:**
```bash
curl -X GET https://api.sendgrid.com/v3/user/profile \
  -H "Authorization: Bearer $SENDGRID_API_KEY"
```

**Common Errors:**
- `401 Unauthorized`: Invalid API key
- `403 Forbidden`: API key lacks permissions
- `429 Too Many Requests`: Rate limit exceeded (100/day on free tier)

### Email Going to Spam

**Solutions:**
1. Verify domain authentication (SPF + DKIM)
2. Add DMARC record
3. Warm up sender reputation (send gradually, not bulk)
4. Avoid spam trigger words
5. Include unsubscribe link (for transactional emails)

### Inbound Parse Not Working

**Verify MX Record:**
```bash
dig xswarm.ai MX
# Should return: mx.sendgrid.net
```

**Check Webhook:**
- URL must be HTTPS (not HTTP)
- Endpoint must return 200 OK
- Use ngrok for local testing

**Test Webhook:**
```bash
curl -X POST https://your-server.com/email/incoming \
  -H "Content-Type: multipart/form-data" \
  -F "from=test@example.com" \
  -F "to=username@xswarm.ai" \
  -F "subject=Test" \
  -F "text=Test message"
```

---

## Multi-User Configuration

For xSwarm's multi-tenant architecture:

### Single Domain, Multiple Users

```toml
# User 1 config
[communication]
user_email = "user1@example.com"
xswarm_email = "alice@xswarm.ai"

# User 2 config
[communication]
user_email = "user2@example.com"
xswarm_email = "bob@xswarm.ai"
```

### Email Routing

All emails to `*@xswarm.ai` go to the same Inbound Parse webhook:

```rust
// Webhook routes to correct user instance
async fn route_email(to: &str) -> Option<UserId> {
    // Extract username from "username@xswarm.ai"
    let username = to.split('@').next()?;

    // Look up user by xswarm_email
    database.find_user_by_email(to).await
}
```

---

## Next Steps

After SendGrid is configured:

1. ✅ Domain verified
2. ✅ API key added to `.env`
3. ✅ MX record configured
4. ✅ Inbound Parse webhook set up
5. ⏳ Test email sending (`npm run test:sendgrid`)
6. ⏳ Test email receiving (send to `username@xswarm.ai`)
7. ⏳ Integrate with xSwarm communication module

---

## Resources

- [SendGrid Documentation](https://docs.sendgrid.com/)
- [Domain Authentication Guide](https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication)
- [Inbound Parse Webhook](https://docs.sendgrid.com/for-developers/parsing-email/setting-up-the-inbound-parse-webhook)
- [API Reference](https://docs.sendgrid.com/api-reference/how-to-use-the-sendgrid-v3-api/authentication)
- [Twilio SendGrid Integration](https://www.twilio.com/docs/sendgrid)

---

**Questions?** See `planning/DIRECT_LINE.md` for overall communication architecture.
