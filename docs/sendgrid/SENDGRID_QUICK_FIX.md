# SendGrid "Relay Access Denied" - Quick Fix

## TL;DR - The Problem

Emails sent to `chadananda@xswarm.ai` bounce with error:
```
554 5.7.1: Relay access denied
```

## Root Cause

Two missing configuration items:

1. ❌ **No MX record** for chadananda.xswarm.ai
2. ❌ **Wrong webhook hostnames** (mail.xswarm.ai and xswarm.ai instead of chadananda)

## Quick Fix (5 minutes)

### Step 1: Add MX Record to DNS
Go to your DNS provider and add:
```
Type: MX
Host: chadananda
Priority: 10
Value: mx.sendgrid.net
```

### Step 2: Fix SendGrid Webhook
```bash
node scripts/fix-sendgrid.js
```

### Step 3: Wait & Test
- Wait 5-60 minutes for DNS propagation
- Send test email to: chadananda@xswarm.ai
- Should receive AI-powered auto-reply

## Verify Fix

```bash
# Check DNS
./scripts/check-sendgrid-dns.sh

# Check SendGrid config
node scripts/diagnose-sendgrid.js
```

## If It Still Doesn't Work

**Possible Issue**: SendGrid free tier may not support inbound parse

**Solutions**:
1. Contact SendGrid support: support@sendgrid.com
2. Upgrade to paid tier ($19.95/month)
3. Try alternative: Mailgun, AWS SES, or Postmark

## Full Documentation

See: `planning/SENDGRID_INBOUND_FIX.md` for complete guide

## Need Help?

Run diagnostics and save output:
```bash
node scripts/diagnose-sendgrid.js > sendgrid-diagnostics.txt
```

Send diagnostics to SendGrid support or include in issue report.
