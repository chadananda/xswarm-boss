# Email Marketing Quick Start Guide

Get the xSwarm email marketing system up and running in 5 minutes.

## Prerequisites

- SendGrid account with API key
- Cloudflare Workers account
- Database (Turso) configured
- Node.js installed

## Step 1: Install Dependencies

All dependencies are already in `package.json`. If you need to reinstall:

```bash
cd packages/server
npm install
```

## Step 2: Run Database Migration

Create the email marketing tables:

```bash
cd packages/server
node scripts/setup-db.js
```

This will:
- Create 4 core tables (`email_campaigns`, `email_sequences`, `user_email_subscriptions`, `email_sends`)
- Create analytics views
- Seed 3 default campaigns with 18 email sequences

## Step 3: Configure Environment

Add to `.env` or Cloudflare Workers secrets:

```bash
SENDGRID_API_KEY=SG.xxx...
FROM_EMAIL=boss@xswarm.ai
BASE_URL=https://xswarm.ai
ADMIN_TOKEN=your-secure-random-token
```

## Step 4: Test the System

Run the test script:

```bash
node scripts/test-marketing.js
```

You should see:
```
✓ Found 4 email marketing tables
✓ Found 3 campaigns
✓ Found 18 email sequences
✓ All database checks passed!
```

## Step 5: Configure Cron Job

Add to `wrangler.toml`:

```toml
[triggers]
crons = ["0 * * * *"]  # Run every hour
```

## Step 6: Deploy to Cloudflare

```bash
cd packages/server
npm run deploy
```

## Step 7: Configure SendGrid Webhook

1. Go to SendGrid Dashboard → Settings → Mail Settings → Event Notification
2. Add webhook URL: `https://your-domain.workers.dev/marketing/webhook/sendgrid`
3. Enable events: Opened, Clicked, Bounced, Spam Report, Unsubscribe
4. Save

## Step 8: Enroll Your First User

### Via API:
```bash
curl -X POST https://your-domain.workers.dev/marketing/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "current_tier": "free"
  }'
```

### Via Code:
```javascript
import { enrollUserInCampaign } from './lib/email-scheduler.js';

// In your signup handler
await enrollUserInCampaign(userId, 'free', env);
```

## Step 9: Trigger Test Email Send

Manually trigger email batch (for testing):

```bash
curl -X POST https://your-domain.workers.dev/marketing/send-batch \
  -H "Authorization: Bearer your-admin-token"
```

Response:
```json
{
  "sent": 1,
  "failed": 0,
  "errors": []
}
```

## Step 10: Check Analytics

View dashboard stats:

```bash
curl https://your-domain.workers.dev/marketing/stats?type=dashboard
```

## Common Operations

### Batch Enroll All Eligible Users
```bash
curl -X POST https://your-domain.workers.dev/marketing/batch-enroll \
  -H "Authorization: Bearer your-admin-token"
```

### View Campaign Performance
```bash
curl "https://your-domain.workers.dev/marketing/stats?type=campaign&campaign_id=camp_free_to_secretary"
```

### Get Conversion Funnel
```bash
curl "https://your-domain.workers.dev/marketing/stats?type=funnel&campaign_id=camp_free_to_secretary"
```

### Test Unsubscribe Page
```bash
# Get a token from the database first
sqlite3 your-db.db "SELECT unsubscribe_token FROM user_email_subscriptions LIMIT 1;"

# Then visit in browser:
https://your-domain.workers.dev/marketing/unsubscribe/{token}
```

## Integration with Signup Flow

Add to your user signup handler:

```javascript
// After user is created
await enrollUserInCampaign(user.id, user.subscription_tier, env);
```

## Integration with Stripe Upgrades

Add to your Stripe webhook handler:

```javascript
import { markSubscriptionConverted } from './lib/email-scheduler.js';

// When user upgrades subscription
case 'customer.subscription.updated':
  const newTier = getSubscriptionTier(subscription);
  await markSubscriptionConverted(userId, newTier, env);
  break;
```

## Verify Everything Works

1. **Database**: Run `node scripts/test-marketing.js`
2. **API**: Test enroll endpoint
3. **Emails**: Trigger manual batch send
4. **Webhook**: Check SendGrid webhook logs
5. **Cron**: Wait 1 hour and check logs
6. **Analytics**: Query stats endpoint

## Troubleshooting

### "No campaigns found"
- Run database migration: `node scripts/setup-db.js`

### "SendGrid API error"
- Verify `SENDGRID_API_KEY` is correct
- Check SendGrid API key has sending permissions
- Verify `FROM_EMAIL` is verified in SendGrid

### "No pending emails"
- Enroll users first: `POST /marketing/enroll`
- Check enrollment succeeded: Query `user_email_subscriptions` table

### "Emails not sending"
- Verify cron job is configured in `wrangler.toml`
- Check Cloudflare Workers logs for cron execution
- Trigger manual send to test: `POST /marketing/send-batch`

### "Webhook not receiving events"
- Verify webhook URL in SendGrid dashboard
- Check URL is publicly accessible
- Review SendGrid webhook delivery logs

## Email Campaign Structure

### Free → AI Secretary (Campaign 1)
- Day 0: Welcome
- Day 3: Feature introduction
- Day 7: Testimonials
- Day 14: Feature spotlight
- Day 21: Limited offer
- Day 30: Final CTA

### AI Secretary → Project Manager (Campaign 2)
- Day 0: Welcome to team features
- Day 3: Introduce xSwarm Buzz
- Day 7: Team testimonials
- Day 14: Platform benefits
- Day 21: Special pricing
- Day 30: Final CTA

### Project Manager → AI CTO (Campaign 3)
- Day 0: Enterprise features
- Day 3: Unlimited everything
- Day 7: Enterprise testimonials
- Day 14: Custom integrations
- Day 21: Annual pricing
- Day 30: Final CTA

## Monitoring

Key metrics to watch:
- **Open rate**: Should be >30%
- **Click rate**: Should be >8%
- **Conversion rate**: Track per campaign
- **Unsubscribe rate**: Should be <2%

Check dashboard regularly:
```bash
curl "https://your-domain.workers.dev/marketing/stats?type=dashboard"
```

## Next Steps

1. ✅ System is running
2. Monitor first campaign results
3. Optimize subject lines based on A/B tests
4. Adjust email timing if needed
5. Add more campaigns for specific use cases
6. Build dashboard UI for team visibility

## Resources

- **Full Documentation**: `EMAIL_MARKETING_SYSTEM.md`
- **Database Schema**: `migrations/email-marketing.sql`
- **Email Templates**: `src/lib/marketing-emails.js`
- **API Reference**: See documentation for all endpoints

## Support

Questions or issues?
- Check logs with prefix `[Marketing]`
- Review SendGrid dashboard
- Query database directly for debugging
- Email: support@xswarm.ai

---

**You're all set! 🚀**

Your email marketing system is now automated and ready to drive tier upgrades.
