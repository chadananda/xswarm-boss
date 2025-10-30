# Email Marketing System - xSwarm Tier Upselling

Comprehensive automated email marketing system for driving tier upgrades across the 4-tier xSwarm structure.

## Overview

This system provides:
- **Automated email sequences** for each tier upgrade path
- **Professional branded templates** with xSwarm terminal aesthetic
- **A/B testing** for subject line optimization
- **Comprehensive analytics** and conversion tracking
- **Unsubscribe management** and compliance
- **SendGrid integration** for reliable delivery

## Architecture

### Database Schema

Located in: `/migrations/email-marketing.sql`

**Tables:**
- `email_campaigns` - Campaign definitions (Free→Secretary, Secretary→PM, PM→CTO)
- `email_sequences` - Individual emails in each campaign (5-7 emails per campaign)
- `user_email_subscriptions` - Track user enrollment and status
- `email_sends` - Track sent emails and engagement metrics

**Views:**
- `pending_marketing_emails` - Emails ready to be sent
- `campaign_analytics` - Performance metrics per campaign
- `sequence_analytics` - Performance metrics per email
- `upgrade_ready_users` - Users eligible for enrollment

### Core Components

#### 1. Email Templates (`/lib/marketing-emails.js`)
Professional, branded email templates for all campaigns:
- Free → AI Secretary (6 emails over 30 days)
- AI Secretary → AI Project Manager (6 emails over 30 days)
- AI Project Manager → AI CTO (6 emails over 30 days)

Each template includes:
- Compelling subject lines (with A/B test variants)
- xSwarm terminal aesthetic HTML
- Clear call-to-action buttons
- Unsubscribe links
- Plain text fallback

#### 2. Email Scheduler (`/lib/email-scheduler.js`)
Automated email sending and management:
- `processPendingEmails()` - Send scheduled emails
- `enrollUserInCampaign()` - Enroll users in campaigns
- `unsubscribeUser()` - Handle unsubscribe requests
- `markSubscriptionConverted()` - Track conversions
- `trackEmailEngagement()` - Record opens/clicks
- `batchEnrollUsers()` - Bulk enrollment

#### 3. Analytics System (`/lib/marketing-analytics.js`)
Comprehensive campaign analytics:
- Dashboard overview statistics
- Campaign performance metrics
- Email sequence performance
- A/B test results
- Conversion funnel analysis
- Revenue attribution
- Engagement timelines
- User engagement profiles

#### 4. API Routes (`/routes/marketing/index.js`)
RESTful API endpoints for marketing operations.

#### 5. Cron Job (`/lib/marketing-cron.js`)
Scheduled task for automated email sending.

## Email Campaigns

### Campaign 1: Free → AI Secretary

**Target:** Free tier users
**Goal:** Upgrade to AI Secretary ($49/month)
**Duration:** 30 days
**Emails:** 6

| Day | Type | Subject Line | Focus |
|-----|------|-------------|-------|
| 0 | Welcome | "Your AI Secretary is Ready" | Introduction to voice AI benefits |
| 3 | Feature Intro | "See what AI Secretary can do for you" | Feature showcase |
| 7 | Testimonial | "How Sarah saved 10 hours/week" | Social proof |
| 14 | Spotlight | "Your AI Secretary never sleeps" | 24/7 availability |
| 21 | Limited Offer | "50% off AI Secretary - This week only" | Special pricing |
| 30 | Final CTA | "Last chance: Upgrade to AI Secretary" | Final push |

### Campaign 2: AI Secretary → AI Project Manager

**Target:** AI Secretary subscribers
**Goal:** Upgrade to AI Project Manager ($149/month)
**Duration:** 30 days
**Emails:** 6

| Day | Type | Subject Line | Focus |
|-----|------|-------------|-------|
| 0 | Welcome | "Ready to supercharge your team?" | Team features intro |
| 3 | Feature Intro | "Meet xSwarm Buzz - Your AI Marketing Platform" | Buzz marketing platform |
| 7 | Testimonial | "How Mike's team doubled output" | Team success story |
| 14 | Spotlight | "Project Management + Marketing = xSwarm" | Value proposition |
| 21 | Limited Offer | "Upgrade to AI PM - Save $50/month" | Special pricing |
| 30 | Final CTA | "Final call: Scale your business with AI PM" | Final push |

### Campaign 3: AI Project Manager → AI CTO

**Target:** AI Project Manager subscribers
**Goal:** Upgrade to AI CTO ($499/month)
**Duration:** 30 days
**Emails:** 6

| Day | Type | Subject Line | Focus |
|-----|------|-------------|-------|
| 0 | Welcome | "Enterprise-grade AI for serious businesses" | Unlimited features |
| 3 | Feature Intro | "No more usage limits - Scale without worry" | Unlimited usage |
| 7 | Testimonial | "Why TechCorp chose AI CTO" | Enterprise success |
| 14 | Spotlight | "Custom integrations built for you" | Dedicated engineering |
| 21 | Limited Offer | "Enterprise pricing - Lock in now" | Annual discount |
| 30 | Final CTA | "Ready for unlimited AI?" | Final push |

## API Endpoints

### User Operations

#### Enroll User in Campaign
```bash
POST /marketing/enroll
Content-Type: application/json

{
  "user_id": "user_123",
  "current_tier": "free"
}
```

**Response:**
```json
{
  "enrolled": true,
  "campaign_id": "camp_free_to_secretary"
}
```

#### Unsubscribe from Marketing
```bash
GET /marketing/unsubscribe/{token}
```

Returns HTML unsubscribe confirmation page.

#### Mark User as Converted
```bash
POST /marketing/convert
Content-Type: application/json

{
  "user_id": "user_123",
  "new_tier": "ai_secretary"
}
```

### Admin Operations

#### Batch Send Pending Emails
```bash
POST /marketing/send-batch
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "sent": 42,
  "failed": 1,
  "errors": [...]
}
```

#### Batch Enroll Eligible Users
```bash
POST /marketing/batch-enroll
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "enrolled": 156,
  "skipped": 8
}
```

### Analytics

#### Dashboard Statistics
```bash
GET /marketing/stats?type=dashboard
```

**Response:**
```json
{
  "campaigns": {
    "total_campaigns": 3,
    "active_campaigns": 3
  },
  "subscribers": {
    "total_subscriptions": 1523,
    "active_subscriptions": 892,
    "total_conversions": 156,
    "total_unsubscribes": 23
  },
  "sends": {
    "total_sends": 8945,
    "total_opens": 3214,
    "total_clicks": 892,
    "overall_open_rate": 35.94,
    "overall_click_rate": 9.97
  }
}
```

#### Campaign Performance
```bash
GET /marketing/stats?type=campaign&campaign_id={campaign_id}
```

#### Sequence Performance
```bash
GET /marketing/stats?type=sequence&campaign_id={campaign_id}
```

#### Conversion Funnel
```bash
GET /marketing/stats?type=funnel&campaign_id={campaign_id}
```

#### Revenue Attribution
```bash
GET /marketing/stats?type=revenue&campaign_id={campaign_id}
```

#### Engagement Timeline
```bash
GET /marketing/stats?type=timeline&campaign_id={campaign_id}&days=30
```

#### Top Performing Emails
```bash
GET /marketing/stats?type=top&limit=10
```

#### User Engagement Profile
```bash
GET /marketing/stats?type=user&user_id={user_id}
```

#### Complete Analytics Report
```bash
GET /marketing/stats?type=report&campaign_id={campaign_id}
```

### Webhooks

#### SendGrid Event Webhook
```bash
POST /marketing/webhook/sendgrid
Content-Type: application/json

[
  {
    "event": "open",
    "sg_message_id": "msg_123",
    "timestamp": 1234567890
  }
]
```

Tracks email engagement (opens, clicks, bounces, complaints).

## Setup Instructions

### 1. Database Migration

Run the migration to create tables:
```bash
cd packages/server
node scripts/setup-db.js
```

The migration file (`migrations/email-marketing.sql`) will:
- Create all required tables
- Create analytics views
- Seed default campaigns and email sequences

### 2. Environment Variables

Add to `wrangler.toml` or Cloudflare Workers secrets:
```toml
SENDGRID_API_KEY = "SG.xxx..."
FROM_EMAIL = "boss@xswarm.ai"
BASE_URL = "https://xswarm.ai"
ADMIN_TOKEN = "your-secure-admin-token"
```

### 3. Configure Cron Job

Add to `wrangler.toml`:
```toml
[triggers]
crons = ["0 * * * *"]  # Run every hour
```

Update your worker to handle scheduled events:
```javascript
export default {
  async fetch(request, env, ctx) {
    // ... existing fetch handler
  },

  async scheduled(event, env, ctx) {
    const { handleScheduledEvent } = await import('./lib/marketing-cron.js');
    await handleScheduledEvent(event, env, ctx);
  }
}
```

### 4. Configure SendGrid Webhook

In SendGrid dashboard:
1. Go to Settings → Mail Settings → Event Notification
2. Add webhook URL: `https://your-domain.com/marketing/webhook/sendgrid`
3. Enable events: Opened, Clicked, Bounced, Spam Report, Unsubscribe
4. Save configuration

### 5. Integrate with User Signup Flow

Add to your signup/upgrade handlers:
```javascript
import { enrollUserInCampaign } from './lib/email-scheduler.js';

// After user signs up or changes tier
await enrollUserInCampaign(userId, currentTier, env);
```

### 6. Integrate with Stripe Webhooks

Add to `stripe.js` webhook handler:
```javascript
import { markSubscriptionConverted } from './lib/email-scheduler.js';

// When subscription is upgraded
case 'customer.subscription.updated':
  const newTier = getSubscriptionTier(subscription);
  await markSubscriptionConverted(customerId, newTier, env);
  break;
```

## Usage Examples

### Enroll New Free User
```javascript
// When user signs up for free tier
const result = await enrollUserInCampaign(userId, 'free', env);
// User is now enrolled in "Free → AI Secretary" campaign
```

### Track Conversion
```javascript
// When user upgrades to AI Secretary
await markSubscriptionConverted(userId, 'ai_secretary', env);
// Previous campaign marked as converted
// User enrolled in "AI Secretary → AI Project Manager" campaign
```

### Get Campaign Analytics
```javascript
// Get performance for specific campaign
const analytics = await getCampaignPerformance('camp_free_to_secretary', env);
console.log(`Conversion rate: ${analytics[0].conversion_rate}%`);
```

### Manual Email Send (Testing)
```bash
# Trigger manual batch send
curl -X POST https://your-domain.com/marketing/send-batch \
  -H "Authorization: Bearer your-admin-token"
```

## Email Design Philosophy

All emails follow the **xSwarm terminal aesthetic**:
- **Black background** with neon green text
- **Monospace fonts** (Monaco, Courier New)
- **ASCII-style borders** and decorations
- **Clear hierarchy** with green color variations
- **Professional tone** despite hacker aesthetic
- **Mobile-responsive** design
- **Plain text fallback** for all emails

## A/B Testing

Each email includes two subject line variants:
- **Variant A:** Primary subject line
- **Variant B:** Alternative subject line (in `subject_line_variant` field)

System automatically:
- Randomly assigns variant to each send (50/50 split)
- Tracks performance per variant
- Provides A/B test results via analytics API

### Get A/B Test Results
```bash
GET /marketing/stats?type=ab&campaign_id={campaign_id}
```

**Response:**
```json
[
  {
    "sequence_number": 1,
    "variant_a": "Your AI Secretary is Ready",
    "variant_b": "Your AI Secretary is waiting for you",
    "variant_a_sends": 256,
    "variant_b_sends": 248,
    "variant_a_open_rate": 38.28,
    "variant_b_open_rate": 42.34
  }
]
```

## Compliance & Privacy

### Unsubscribe Handling
- **One-click unsubscribe** link in every email
- **Immediate effect** - user removed from active campaigns
- **Preserved history** - past sends tracked for analytics
- **Branded unsubscribe page** - maintains xSwarm aesthetic

### Data Retention
- **Email sends** - Retained indefinitely for analytics
- **User subscriptions** - Retained indefinitely
- **Personal data** - User email/name from `users` table
- **GDPR compliance** - User can request data deletion via support

### Rate Limiting
- **100 emails per batch** - Prevents SendGrid rate limits
- **100ms delay between sends** - Prevents overwhelming SendGrid
- **Hourly cron job** - Sends pending emails every hour

## Monitoring & Alerts

### Key Metrics to Monitor
- **Open rate** - Should be >30%
- **Click rate** - Should be >8%
- **Bounce rate** - Should be <2%
- **Complaint rate** - Should be <0.1%
- **Conversion rate** - Track per campaign

### Alert Thresholds
- **Failed sends** - Alert if >10% of batch fails
- **Low open rates** - Alert if <20% for any campaign
- **High bounces** - Alert if >5% of sends bounce
- **High complaints** - Alert if >1% report spam

### Logging
All operations logged with prefix:
- `[Email Scheduler]` - Sending operations
- `[Marketing]` - API operations
- `[Marketing Webhook]` - SendGrid webhook events
- `[Marketing Cron]` - Scheduled job execution
- `[Enrollment]` - User enrollment operations
- `[Unsubscribe]` - Unsubscribe operations
- `[Conversion]` - Conversion tracking
- `[Engagement]` - Engagement tracking

## Troubleshooting

### Emails Not Sending
1. Check cron job is configured and running
2. Verify `SENDGRID_API_KEY` is set correctly
3. Check `pending_marketing_emails` view has rows
4. Run manual batch send to test: `POST /marketing/send-batch`
5. Check SendGrid dashboard for errors

### Low Open Rates
1. Review subject lines - test variants
2. Check sender reputation in SendGrid
3. Verify emails not going to spam
4. Review email content and CTAs
5. Consider adjusting send times

### High Unsubscribe Rate
1. Review email frequency (30 days = 6 emails)
2. Check email content relevance
3. Verify targeting (right tier for campaign)
4. Review unsubscribe feedback if available
5. Consider reducing email count

### Users Not Getting Enrolled
1. Check `enrollUserInCampaign()` is called on signup
2. Verify user's `subscription_tier` is set correctly
3. Check `upgrade_ready_users` view
4. Run batch enrollment: `POST /marketing/batch-enroll`
5. Check database for enrollment records

### Webhook Not Working
1. Verify webhook URL in SendGrid dashboard
2. Check webhook is receiving POST requests
3. Verify SendGrid sends message IDs in events
4. Check `email_sends` table has matching `sendgrid_message_id`
5. Review SendGrid webhook logs

## Performance Optimization

### Database Indexes
All critical queries indexed:
- User lookups by subscription tier
- Pending email queries by date
- Engagement tracking by message ID
- Analytics queries by campaign/sequence

### Caching Strategy
- **Campaign data** - Rarely changes, can cache
- **User subscriptions** - Changes frequently, no cache
- **Analytics** - Can cache for 15 minutes
- **Email templates** - Static, can cache indefinitely

### Batch Processing
- Process max 100 emails per cron run
- Use rate limiting between sends
- Consider splitting large batches across multiple runs

## Future Enhancements

### Planned Features
- [ ] Visual email builder for templates
- [ ] Advanced segmentation (behavior-based)
- [ ] Predictive send time optimization
- [ ] Multi-variant testing (>2 variants)
- [ ] Dynamic content personalization
- [ ] Re-engagement campaigns for churned users
- [ ] Referral email campaigns
- [ ] Win-back campaigns for downgraded users

### Integration Ideas
- [ ] Slack notifications for conversions
- [ ] Dashboard UI for campaign management
- [ ] Export analytics to Google Sheets
- [ ] Integration with CRM systems
- [ ] Advanced attribution tracking

## File Reference

```
packages/server/
├── migrations/
│   └── email-marketing.sql           # Database schema and seed data
├── src/
│   ├── lib/
│   │   ├── marketing-emails.js       # Email templates
│   │   ├── email-scheduler.js        # Scheduling and enrollment
│   │   ├── marketing-analytics.js    # Analytics and reporting
│   │   └── marketing-cron.js         # Cron job handler
│   └── routes/
│       └── marketing/
│           └── index.js              # API endpoints
└── EMAIL_MARKETING_SYSTEM.md         # This file
```

## Support

For issues or questions:
- Review logs with prefix `[Marketing]`
- Check SendGrid dashboard for delivery issues
- Query database views for current state
- Contact: support@xswarm.ai

---

**Built with ❤️ for xSwarm by the Boss AI Team**

*Last updated: 2025-10-29*
