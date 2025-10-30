# SendGrid Diagnostic and Fix Scripts

## Overview

Three scripts to diagnose and fix SendGrid inbound email issues causing "554 5.7.1: Relay access denied" errors.

## Scripts

### 1. diagnose-sendgrid.js
**Comprehensive diagnostic tool**

```bash
node scripts/diagnose-sendgrid.js
```

**Checks:**
- ✅ API key validity and permissions
- ✅ Account tier and limitations
- ✅ Inbound parse webhook configuration
- ✅ Webhook hostname matching
- ✅ Send raw MIME message setting
- ✅ Domain authentication status
- ✅ Mail settings and restrictions
- ✅ IP access management
- ✅ MX record requirements

**Output:**
- List of critical issues
- List of warnings
- Recommendations
- Root cause analysis
- Next steps

**When to use:**
- First step in troubleshooting
- To understand current configuration
- Before running fix script
- After making changes to verify

---

### 2. fix-sendgrid.js
**Automated configuration fix**

```bash
node scripts/fix-sendgrid.js
```

**Actions:**
- Verifies API key
- Creates/updates inbound parse webhook
  - Correct hostname (chadananda)
  - Correct URL (current cloudflare tunnel)
  - Enables send_raw for full MIME message
- Verifies domain authentication
- Provides MX record configuration instructions
- Optionally sends test email

**Interactive prompts:**
- Update existing webhook? (y/n)
- Send test email? (y/n)

**When to use:**
- After running diagnostic
- When webhook needs updating
- When cloudflare tunnel URL changes
- To send test emails

**Note:** May fail on free tier accounts - provides manual instructions if needed.

---

### 3. check-sendgrid-dns.sh
**DNS configuration checker**

```bash
./scripts/check-sendgrid-dns.sh
```

**Checks:**
- MX record for chadananda.xswarm.ai
- SPF record for xswarm.ai
- DKIM records (links to SendGrid dashboard)

**Output:**
- Current DNS configuration
- Expected configuration
- Pass/fail status
- Configuration instructions
- Online checker links

**When to use:**
- To verify MX record is configured
- After adding MX record to DNS
- To check DNS propagation status
- Troubleshooting relay access denied errors

---

## Typical Workflow

### Initial Setup
```bash
# 1. Diagnose current state
node scripts/diagnose-sendgrid.js

# 2. Check DNS configuration
./scripts/check-sendgrid-dns.sh

# 3. Fix SendGrid configuration
node scripts/fix-sendgrid.js

# 4. Manually add MX record to DNS
# (see output from steps above)

# 5. Wait 5-60 minutes for DNS propagation

# 6. Verify fixes
node scripts/diagnose-sendgrid.js
./scripts/check-sendgrid-dns.sh
```

### After Cloudflare Tunnel Changes
```bash
# Update webhook URL when tunnel changes
node scripts/fix-sendgrid.js
# Select 'y' to update webhook
```

### Troubleshooting
```bash
# Get comprehensive diagnostics
node scripts/diagnose-sendgrid.js > diagnostics.txt

# Check DNS status
./scripts/check-sendgrid-dns.sh

# Try automated fix
node scripts/fix-sendgrid.js
```

## Current Configuration

**From**: `packages/server/src/config/users.json`
```json
{
  "username": "chadananda",
  "boss_email": "chadananda@xswarm.ai",
  "email": "chadananda@gmail.com"
}
```

**Webhook URL**: From `packages/server/.dev.vars`
```
PUBLIC_BASE_URL=https://tion-fifteen-substantial-jimmy.trycloudflare.com
```

**Required DNS**:
```
Type: MX
Host: chadananda
Priority: 10
Value: mx.sendgrid.net
```

## Expected Diagnostic Output (When Fixed)

```
✅ API Key: Valid
✅ Account: Free tier (with inbound parse enabled)
✅ Parse Webhooks: 1 configured
   - Hostname: chadananda
   - URL: https://[tunnel].trycloudflare.com/email/inbound
   - Send Raw: Yes
✅ Domain Auth: Valid
✅ MX Record: Configured and propagated
```

## Common Issues

### Issue: "Relay access denied"
**Cause**: MX record not configured or not propagated
**Fix**: Add MX record, wait for DNS propagation

### Issue: Webhook configuration fails
**Cause**: Free tier limitation
**Fix**: Configure manually at https://app.sendgrid.com/settings/parse

### Issue: Emails not reaching webhook
**Cause**: Wrong hostname or MX record
**Fix**: Ensure hostname is "chadananda" and MX points to mx.sendgrid.net

### Issue: Webhook receives data but parsing fails
**Cause**: send_raw not enabled
**Fix**: Update webhook to enable "POST the raw, full MIME message"

## Environment Variables

Required in `packages/server/.dev.vars`:
```
SENDGRID_API_KEY=SG.xxx...
PUBLIC_BASE_URL=https://xxx.trycloudflare.com
```

Required in `.env`:
```
SENDGRID_API_KEY=SG.xxx...
```

## API Endpoints Used

All scripts use SendGrid API v3:
- `/user/profile` - Verify API key
- `/user/account` - Check account tier
- `/user/webhooks/parse/settings` - Manage inbound parse webhooks
- `/whitelabel/domains` - Check domain authentication
- `/mail_settings/*` - Check mail settings
- `/access_settings/whitelist` - Check IP access
- `/mail/send` - Send test emails

## Documentation Links

- **SendGrid Inbound Parse**: https://docs.sendgrid.com/for-developers/parsing-email/setting-up-the-inbound-parse-webhook
- **Domain Authentication**: https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication
- **API Documentation**: https://docs.sendgrid.com/api-reference
- **Parse Settings Dashboard**: https://app.sendgrid.com/settings/parse
- **Domain Auth Dashboard**: https://app.sendgrid.com/settings/sender_auth

## Support

If issues persist after running all scripts:

1. Save diagnostic output:
   ```bash
   node scripts/diagnose-sendgrid.js > sendgrid-diagnostics.txt
   ```

2. Contact SendGrid support:
   - Email: support@sendgrid.com
   - Include diagnostic output
   - Mention: "Inbound parse webhook not working - relay access denied"

3. Check SendGrid status:
   - https://status.sendgrid.com/

## Free Tier Considerations

SendGrid free tier **may** have limitations on inbound parse webhooks. This is account-specific and not clearly documented.

**Symptoms of free tier limitation:**
- Webhook creation fails with validation error
- Webhook appears configured but never receives data
- "Relay access denied" persists after all fixes

**Solutions:**
1. Contact SendGrid support - they may enable it for your account
2. Upgrade to paid tier ($19.95/month Essentials plan)
3. Use alternative service (Mailgun, AWS SES, Postmark)

## Testing

### Test Webhook Directly
```bash
curl -X POST https://[tunnel].trycloudflare.com/email/inbound \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "from=test@example.com&to=chadananda@xswarm.ai&subject=Test&text=Hello"
```

### Test Full Email Flow
```bash
# Send email to chadananda@xswarm.ai from chadananda@gmail.com
# Should receive AI-powered auto-reply
```

### Monitor Webhook Activity
- Go to: https://app.sendgrid.com/settings/parse
- Click on webhook to see POST history
- Check for successful/failed deliveries

## Version Info

Created: 2024-10-27
Last Updated: 2024-10-27
SendGrid API: v3
Node.js: v18+
