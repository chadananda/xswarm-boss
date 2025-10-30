# SendGrid Inbound Email Fix Guide

## Problem Summary

**Error**: `554 5.7.1: Relay access denied`
**Symptom**: Emails sent to `chadananda@xswarm.ai` are bouncing
**Root Cause**: Missing MX record and incorrect webhook configuration

## Diagnostic Results

### Current Status
- ✅ API Key: Valid
- ✅ Domain Authentication: xswarm.ai is authenticated
- ✅ Account: Free tier (potential limitation)
- ⚠️ Webhook Configuration: Hostnames don't match
- ❌ MX Record: Not configured for chadananda.xswarm.ai

### Issues Found

1. **Missing MX Record** (CRITICAL)
   - No MX record exists for `chadananda.xswarm.ai`
   - SendGrid cannot receive emails without this DNS configuration

2. **Incorrect Webhook Hostnames**
   - Configured: `mail.xswarm.ai` and `xswarm.ai`
   - Required: `chadananda` (or `chadananda.xswarm.ai`)

3. **Free Tier Limitation** (POTENTIAL)
   - SendGrid free tier may have inbound parse limitations
   - This could require upgrading to paid tier

## Solution Steps

### Step 1: Configure DNS MX Record (REQUIRED)

**Action**: Add MX record to DNS configuration for xswarm.ai domain

**DNS Record Configuration**:
```
Type: MX
Host/Name: chadananda
Priority: 10
Value: mx.sendgrid.net
TTL: 3600 (or automatic)
```

**Where to Configure**:
1. Log in to your DNS provider (where xswarm.ai is registered)
2. Navigate to DNS management / DNS records
3. Add new MX record with the values above
4. Save changes
5. Wait 5-60 minutes for DNS propagation

**Verification**:
```bash
# Check MX record
dig MX chadananda.xswarm.ai

# Expected output:
# chadananda.xswarm.ai. 3600 IN MX 10 mx.sendgrid.net.
```

Or use the provided script:
```bash
./scripts/check-sendgrid-dns.sh
```

### Step 2: Update SendGrid Webhook Configuration

**Option A: Automated Fix (Recommended)**
```bash
node scripts/fix-sendgrid.js
```

This script will:
1. Remove incorrect webhooks (mail.xswarm.ai, xswarm.ai)
2. Create correct webhook for chadananda subdomain
3. Configure with proper settings (send_raw: true)
4. Update webhook URL to current cloudflare tunnel

**Option B: Manual Configuration**

If automated fix fails (common with free tier):

1. Go to: https://app.sendgrid.com/settings/parse
2. Delete existing webhooks for mail.xswarm.ai and xswarm.ai
3. Click "Add Host & URL"
4. Enter:
   - **Hostname**: `chadananda`
   - **URL**: `https://tion-fifteen-substantial-jimmy.trycloudflare.com/email/inbound`
   - Check: ☑ "POST the raw, full MIME message"
5. Save

### Step 3: Verify Configuration

Run diagnostics again:
```bash
node scripts/diagnose-sendgrid.js
```

Expected output:
- ✅ API Key: Valid
- ✅ Account: Free tier
- ✅ Parse Webhooks: 1 configured for chadananda
- ✅ Domain Auth: Valid
- ✅ MX Record: Pointing to mx.sendgrid.net

### Step 4: Test Email Delivery

Send test email:
```bash
# From the fix script
node scripts/fix-sendgrid.js
# Then select 'y' when prompted to send test email
```

Or send manually from any email client to:
```
chadananda@xswarm.ai
```

**Expected behavior**:
1. Email is received by mx.sendgrid.net
2. SendGrid parses email and POSTs to webhook
3. Webhook processes with Claude AI
4. Auto-reply sent back to sender

## Free Tier Limitations

### Issue
SendGrid free tier may not support inbound parse webhooks. This is account-specific.

### Symptoms
- Webhook configuration fails with error mentioning "free tier"
- Webhook appears configured but doesn't receive emails
- "Relay access denied" error persists after all fixes

### Solutions

**Option 1: Contact SendGrid Support**
- Email: support@sendgrid.com
- Request: Enable inbound parse for your account
- Mention: You need it for a development/testing project

**Option 2: Upgrade to Paid Tier**
- Essentials plan: $19.95/month (includes inbound parse)
- Go to: https://app.sendgrid.com/settings/billing

**Option 3: Alternative Service (if needed)**
- Use Mailgun (has free inbound parsing)
- Use AWS SES (very low cost)
- Use Postmark (free tier includes inbound)

## Scripts Reference

### diagnose-sendgrid.js
**Purpose**: Comprehensive diagnostic tool
**Usage**: `node scripts/diagnose-sendgrid.js`
**Checks**:
- API key validity and permissions
- Account tier and limitations
- Inbound parse webhook configuration
- Domain authentication status
- Mail settings and restrictions
- IP access management

### fix-sendgrid.js
**Purpose**: Automated configuration fix
**Usage**: `node scripts/fix-sendgrid.js`
**Actions**:
- Creates/updates inbound parse webhook
- Verifies domain authentication
- Provides DNS configuration instructions
- Sends test email

### check-sendgrid-dns.sh
**Purpose**: DNS configuration checker
**Usage**: `./scripts/check-sendgrid-dns.sh`
**Checks**:
- MX record for chadananda.xswarm.ai
- SPF record for xswarm.ai
- Provides online checker links

## Troubleshooting

### "Relay access denied" persists after fixes

**Possible causes**:
1. DNS not yet propagated (wait 5-60 minutes)
2. MX record configured incorrectly
3. Free tier doesn't support inbound parse
4. Webhook hostname mismatch

**Debug steps**:
```bash
# 1. Verify MX record
dig MX chadananda.xswarm.ai

# 2. Check webhook configuration
node scripts/diagnose-sendgrid.js

# 3. Check SendGrid logs
# Go to: https://app.sendgrid.com/settings/parse
# Click on your webhook to see activity logs

# 4. Test webhook directly
curl -X POST https://tion-fifteen-substantial-jimmy.trycloudflare.com/email/inbound \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "from=test@example.com&to=chadananda@xswarm.ai&subject=Test&text=Hello"
```

### Webhook receives no data

**Possible causes**:
1. MX record not configured
2. DNS not propagated
3. Wrong webhook URL (check cloudflare tunnel)

**Debug steps**:
```bash
# 1. Check cloudflare tunnel is running
# Should show: https://tion-fifteen-substantial-jimmy.trycloudflare.com

# 2. Test webhook endpoint
curl https://tion-fifteen-substantial-jimmy.trycloudflare.com/health

# 3. Check server logs
# (when running: pnpm dev:server)
```

### Email parsing works but no response

**Possible causes**:
1. Claude API key not configured
2. Webhook processing error
3. SendGrid can't send outbound email

**Debug steps**:
```bash
# 1. Check API key
echo $SENDGRID_API_KEY

# 2. Check server logs for errors
# Look for "Error handling inbound email" messages

# 3. Test outbound email
node scripts/fix-sendgrid.js
# Select 'y' to send test email
```

## Current Configuration

**Boss Email**: `chadananda@xswarm.ai`
**User Email**: `chadananda@gmail.com`
**Webhook URL**: `https://tion-fifteen-substantial-jimmy.trycloudflare.com/email/inbound`
**Domain**: `xswarm.ai`
**Account Tier**: Free

## Environment Variables

Located in: `packages/server/.dev.vars`
```
SENDGRID_API_KEY=***REMOVED***
PUBLIC_BASE_URL=https://tion-fifteen-substantial-jimmy.trycloudflare.com
```

## References

- SendGrid Inbound Parse Docs: https://docs.sendgrid.com/for-developers/parsing-email/setting-up-the-inbound-parse-webhook
- SendGrid Domain Authentication: https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication
- MX Record Testing: https://mxtoolbox.com/
- DNS Propagation Checker: https://dnschecker.org/

## Success Checklist

- [ ] MX record configured in DNS
- [ ] DNS propagated (verified with dig)
- [ ] SendGrid webhook configured for "chadananda"
- [ ] Webhook URL matches current cloudflare tunnel
- [ ] Send_raw enabled on webhook
- [ ] Domain authentication valid
- [ ] Test email sent successfully
- [ ] Reply processed by webhook
- [ ] Auto-reply received

## Next Steps After Fix

Once inbound email is working:

1. **Update webhook URL** when cloudflare tunnel URL changes
   - Edit webhook at: https://app.sendgrid.com/settings/parse
   - Or run: `node scripts/fix-sendgrid.js`

2. **Monitor webhook activity**
   - Check logs at: https://app.sendgrid.com/settings/parse
   - Click on webhook to see POST history

3. **Test full email workflow**
   - Send email from chadananda@gmail.com to chadananda@xswarm.ai
   - Verify AI-powered response received
   - Test various message types (questions, tasks, status)

4. **Consider upgrading** if free tier limitations encountered
   - Inbound parse reliability
   - Higher volume support
   - Better deliverability

## Contact

If issues persist after following all steps:
- SendGrid Support: support@sendgrid.com
- Include this diagnostic output: `node scripts/diagnose-sendgrid.js > sendgrid-diagnostics.txt`
