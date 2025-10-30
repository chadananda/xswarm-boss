# xSwarm AI Assistant Dashboard

Comprehensive user dashboard with usage analytics, billing management, and subscription control.

## Features

### 1. Overview Dashboard
- Real-time usage statistics (voice minutes, SMS messages, emails)
- Current plan display with features
- Usage limit progress bars with warnings
- Overage charge calculations
- Billing period information
- Alert notifications for usage thresholds

### 2. Usage Analytics
- Historical usage charts (12 months)
- Voice minutes tracking with Chart.js visualization
- SMS message volume tracking
- Email volume tracking
- Month-over-month comparison
- Percentage change calculations
- Trend analysis

### 3. Subscription Management
- Current subscription details
- Feature list for current tier
- Upgrade options display
- Stripe Checkout integration for upgrades
- Downgrade flow with proration
- Cancel subscription with period-end handling

### 4. Billing History
- Upcoming charge preview
- Base price + overage breakdown
- Payment history table
- Invoice download links
- Stripe invoice integration
- Transaction status tracking

### 5. Team Management (Pro+ Plans)
- Team overview (AI Project Manager and AI CTO plans)
- Conditional display based on subscription tier

### 6. Buzz Listings (Pro+ Plans)
- Marketing platform integration
- Link to buzz management page
- Analytics for buzz listings

### 7. User Settings
- Profile management (name, persona, wake word)
- AI persona selection
- Security settings
- Account preferences

## File Structure

```
packages/server/
├── src/
│   ├── lib/
│   │   ├── usage-tracker.js       # Usage tracking and recording
│   │   └── dashboard-utils.js     # Data aggregation and formatting
│   └── routes/
│       └── dashboard/
│           ├── index.js           # Main dashboard router
│           ├── overview.js        # Overview endpoint
│           ├── usage.js           # Usage analytics endpoint
│           ├── billing.js         # Billing history endpoint
│           ├── subscription.js    # Subscription management
│           ├── profile.js         # User profile endpoints
│           └── upgrade.js         # Upgrade/downgrade/cancel
└── scripts/
    └── migrate-dashboard.js       # Database migration script

admin-pages/
└── dashboard.html                 # Frontend dashboard SPA

.claude/todos/
└── dashboard-implementation.md    # Implementation checklist
```

## Database Schema

### usage_records Table
```sql
CREATE TABLE usage_records (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  voice_minutes INTEGER DEFAULT 0,
  sms_messages INTEGER DEFAULT 0,
  email_count INTEGER DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### billing_history Table
```sql
CREATE TABLE billing_history (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL,
  description TEXT,
  invoice_url TEXT,
  period_start TEXT,
  period_end TEXT,
  stripe_invoice_id TEXT,
  stripe_payment_intent_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## API Endpoints

### Dashboard Data
- `GET /api/dashboard/overview` - Dashboard summary stats
- `GET /api/dashboard/usage` - Detailed usage analytics
- `GET /api/dashboard/billing` - Billing history and invoices
- `GET /api/dashboard/subscription` - Subscription details
- `PUT /api/dashboard/subscription` - Update subscription preferences

### User Profile
- `GET /api/dashboard/profile` - User profile information
- `PUT /api/dashboard/profile` - Update profile

### Subscription Actions
- `POST /api/dashboard/upgrade` - Initiate upgrade (Stripe checkout)
- `POST /api/dashboard/downgrade` - Downgrade subscription
- `POST /api/dashboard/cancel` - Cancel subscription

## Usage Tracking

The usage tracking system automatically records:

1. **Voice Minutes**: Tracked via `trackVoiceUsage(userId, minutes, env)`
2. **SMS Messages**: Tracked via `trackSMSUsage(userId, count, env)`
3. **Email Volume**: Tracked via `trackEmailUsage(userId, count, env)`

### Integration Points

Add to existing routes:

```javascript
// In voice route after call ends
import { trackVoiceUsage } from '../lib/usage-tracker.js';
await trackVoiceUsage(user.id, callDurationMinutes, env);

// In SMS route after sending message
import { trackSMSUsage } from '../lib/usage-tracker.js';
await trackSMSUsage(user.id, 1, env);

// In email route after sending email
import { trackEmailUsage } from '../lib/usage-tracker.js';
await trackEmailUsage(user.id, 1, env);
```

### Usage Limits

The system enforces limits based on subscription tier:

```javascript
import { checkUsageLimit } from '../lib/usage-tracker.js';

// Before performing action
const check = await checkUsageLimit(user.id, 'voice', env);
if (!check.allowed) {
  return new Response(check.reason, { status: 403 });
}
```

## Subscription Tiers

### AI Buddy (Free)
- Email only: 100/day
- No voice or SMS

### AI Secretary ($40/month)
- Unlimited emails
- 100 voice minutes/month
- 100 SMS messages/month
- Overages: $0.013/min voice, $0.0075/msg SMS

### AI Project Manager ($280/month)
- Everything in AI Secretary
- 500 voice minutes/month
- 500 SMS messages/month
- Team management
- Buzz marketing platform

### AI CTO (Enterprise)
- Unlimited everything
- Custom pricing
- Enterprise support

## Overage Calculations

Voice overages: `$0.013 per minute`
SMS overages: `$0.0075 per message`

Example:
- Plan: AI Secretary (100 voice minutes included)
- Used: 150 voice minutes
- Overage: 50 minutes × $0.013 = $0.65

## Chart.js Integration

The dashboard uses Chart.js 4.4.0 for data visualization:

```javascript
// Voice usage chart example
new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Jan', 'Feb', 'Mar', ...],
    datasets: [{
      label: 'Voice Minutes',
      data: [45, 52, 73, ...],
      borderColor: 'rgb(0, 217, 255)',
      backgroundColor: 'rgba(0, 217, 255, 0.1)',
    }]
  },
  options: { /* responsive options */ }
});
```

## Stripe Integration

### Upgrade Flow
1. User clicks "Upgrade" button
2. POST to `/api/dashboard/upgrade` with target tier
3. Server creates Stripe Checkout session
4. User redirected to Stripe
5. After payment, Stripe webhook updates subscription
6. User redirected back to dashboard

### Webhook Handling
Stripe webhooks handle:
- `customer.subscription.created` - Provision features
- `customer.subscription.updated` - Update tier
- `customer.subscription.deleted` - Downgrade to free
- `invoice.payment_succeeded` - Reset usage counters

## Setup Instructions

### 1. Run Database Migration

```bash
cd packages/server
node scripts/migrate-dashboard.js
```

### 2. Set Environment Variables

Add to `.env`:
```bash
TURSO_DATABASE_URL="your_database_url"
TURSO_AUTH_TOKEN="your_auth_token"
STRIPE_PRICE_AI_SECRETARY="price_xxxxx"
STRIPE_PRICE_AI_PROJECT_MANAGER="price_xxxxx"
BASE_URL="https://yourdomain.com"
```

### 3. Integrate Dashboard Routes

Add to main server router:

```javascript
import { handleDashboardRoutes } from './routes/dashboard/index.js';
import { authMiddleware } from './lib/auth-middleware.js';

// In your router
if (path.startsWith('/api/dashboard/')) {
  // Apply auth middleware
  const authenticatedRequest = await authMiddleware(request, env);
  return handleDashboardRoutes(authenticatedRequest, env);
}
```

### 4. Add Usage Tracking

Integrate usage tracking into existing routes (see Integration Points above).

## Mobile Responsive Design

The dashboard is fully responsive with:
- Mobile-first CSS grid layouts
- Touch-friendly buttons and controls
- Collapsible sections
- Optimized chart sizes for small screens
- Horizontal scrolling tab navigation on mobile

## Security

All dashboard endpoints require JWT authentication:
```javascript
headers: {
  'Authorization': `Bearer ${token}`
}
```

User data is scoped to authenticated user - no cross-user data access.

## Testing

Test the dashboard:

1. **Authentication**: Ensure login redirects to dashboard
2. **Overview**: Verify stats display correctly
3. **Charts**: Check Chart.js renders on all screen sizes
4. **Upgrade**: Test Stripe Checkout flow
5. **Profile**: Verify profile updates save
6. **Mobile**: Test on iOS/Android devices

## Future Enhancements

- [ ] WebSocket integration for real-time usage updates
- [ ] Export usage data to CSV/PDF
- [ ] Two-factor authentication
- [ ] Usage alerts via email/SMS
- [ ] Custom usage reports
- [ ] Team member activity tracking
- [ ] API usage statistics
- [ ] Cost forecasting

## Support

For issues or questions:
- Check logs: Dashboard API server logs all requests
- Verify database migration completed successfully
- Ensure Stripe products are configured correctly
- Check JWT token is valid and not expired

## License

MIT License - See LICENSE file for details
