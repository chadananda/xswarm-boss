# Email Forwarding System

## Overview

The email system now supports forwarding functionality for specific addresses, allowing emails sent to privacy, contact, and DPO addresses to be automatically forwarded to the admin email.

## Implementation

### File Modified
- `/packages/server/src/routes/email.js`

### Forwarding Addresses

The following addresses automatically forward to `chadananda@gmail.com`:

| Address | Purpose | Forward To |
|---------|---------|------------|
| `privacy@xswarm.ai` | Privacy inquiries | `chadananda@gmail.com` |
| `contact@xswarm.ai` | General contact | `chadananda@gmail.com` |
| `dpo@xswarm.ai` | GDPR Data Protection Officer | `chadananda@gmail.com` |

### How It Works

1. **Authorization Check**: The `getAuthorizedUserByEmail()` function now recognizes forwarding addresses
2. **Forwarding Logic**: When an email is sent to a forwarding address:
   - The system validates the recipient (forwarding address)
   - Skips sender validation for forwarding addresses (accepts from anyone)
   - Forwards the original email content to the admin
   - Adds metadata headers showing original sender and recipient
   - Tags the subject line with the purpose (e.g., `[PRIVACY]`, `[CONTACT]`, `[DPO]`)
3. **Boss AI Preservation**: Emails to `chadananda@xswarm.ai` continue using the Boss AI system unchanged

### Email Format

Forwarded emails include:

**Subject**: `[PURPOSE] Original Subject`
- Example: `[PRIVACY] Question about data retention`

**Plain Text Body**:
```
Forwarded from: John Doe <john@example.com>
Original To: privacy@xswarm.ai

---

[Original email content]
```

**HTML Body** (if present):
```html
<div style="background: #f5f5f5; padding: 10px; margin-bottom: 20px;">
  <strong>Forwarded from:</strong> John Doe &lt;john@example.com&gt;<br>
  <strong>Original To:</strong> privacy@xswarm.ai
</div>
<hr>
[Original HTML content]
```

## Security Features

- **Recipient Validation**: Only authorized forwarding addresses are accepted
- **Spam Protection**: Unauthorized emails are silently dropped (no bounce)
- **No AI Processing**: Forwarding addresses bypass AI processing for simple forwarding
- **Preserved Metadata**: Original sender and recipient information is preserved

## Testing

A test script is available at `/scripts/test-email-forwarding.js` that validates:
- Forwarding address recognition
- Boss AI address preservation
- User address preservation
- Unknown address rejection

Run tests:
```bash
node scripts/test-email-forwarding.js
```

## SendGrid Configuration

To enable these forwarding addresses in SendGrid:

1. **Add MX Records** (if using Inbound Parse):
   ```
   privacy.xswarm.ai → mx.sendgrid.net (priority 10)
   contact.xswarm.ai → mx.sendgrid.net (priority 10)
   dpo.xswarm.ai → mx.sendgrid.net (priority 10)
   ```

2. **Configure Inbound Parse**:
   - Point all three domains to your webhook URL
   - Webhook: `https://your-worker.workers.dev/api/email/inbound`

3. **Verify Domain Authentication**:
   - Ensure xswarm.ai is authenticated in SendGrid
   - Set up DKIM, SPF, and DMARC records

## Usage Examples

### Privacy Inquiry
Someone sends email to `privacy@xswarm.ai`:
- System accepts the email
- Forwards to `chadananda@gmail.com`
- Subject: `[PRIVACY] Original Subject`
- Includes original sender metadata

### Contact Form
Website contact form sends to `contact@xswarm.ai`:
- System accepts the email
- Forwards to `chadananda@gmail.com`
- Subject: `[CONTACT] Original Subject`
- Includes original sender metadata

### GDPR Request
Data subject sends to `dpo@xswarm.ai`:
- System accepts the email
- Forwards to `chadananda@gmail.com`
- Subject: `[DPO] Original Subject`
- Includes original sender metadata

### Boss AI (Unchanged)
User sends to `chadananda@xswarm.ai`:
- System validates sender/recipient pairing
- Processes with Claude AI
- Sends intelligent auto-reply
- No change to existing behavior

## Future Enhancements

Potential improvements:
- Add reply-to handling for forwarded emails
- Track forwarding statistics
- Add configurable forwarding rules
- Support multiple admin recipients
- Add email threading for conversations
- Implement auto-categorization of forwarded emails
