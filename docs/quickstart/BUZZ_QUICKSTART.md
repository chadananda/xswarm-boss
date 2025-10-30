# xSwarm Buzz - Quick Start Guide

## What is Buzz?

xSwarm Buzz is a marketing platform that allows Pro+ users to showcase and promote their products and services to the xSwarm community. Think of it as a curated product directory with built-in analytics.

## For Users

### Creating a Listing

**Requirements:**
- Pro+ subscription (AI Project Manager or AI CTO tier)
- Maximum 5 active listings at a time

**API Request:**
```bash
curl -X POST https://webhooks.xswarm.ai/buzz/listings \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Product Name",
    "description": "A compelling description of what your product does and why it matters",
    "category": "saas",
    "url": "https://yourproduct.com",
    "image_url": "https://yourproduct.com/screenshot.png",
    "price_type": "freemium",
    "price_range": "10_50",
    "tags": ["productivity", "ai", "automation"]
  }'
```

**Categories:**
- `saas` - Software as a Service
- `mobile_app` - iOS/Android apps
- `web_app` - Web applications
- `api` - APIs and services
- `tool` - Developer tools
- `service` - Professional services
- `consulting` - Consulting services
- `other` - Other products

**Price Types:**
- `free` - Completely free
- `freemium` - Free tier + paid upgrades
- `paid` - Paid only
- `custom` - Custom pricing

**Price Ranges:**
- `under_10` - Under $10/month
- `10_50` - $10-50/month
- `50_200` - $50-200/month
- `200_plus` - $200+/month
- `custom` - Custom/variable

### Viewing Your Analytics

```bash
# Overall stats for all your listings
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://webhooks.xswarm.ai/buzz/stats

# Stats for a specific listing
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://webhooks.xswarm.ai/buzz/stats?listing_id=LISTING_ID
```

**Metrics Provided:**
- Total views
- Total clicks
- Click-through rate (CTR)
- Daily breakdown (last 30 days)
- Interaction types (views, clicks, shares, reports)

### Updating a Listing

```bash
curl -X PUT https://webhooks.xswarm.ai/buzz/listings/LISTING_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "price_range": "50_200"
  }'
```

### Renewing a Listing

Listings expire after 90 days. Contact admin to renew, or wait for the auto-renewal system (coming soon).

## For Visitors

### Browsing Listings

Visit the Buzz portal: `https://xswarm.ai/buzz.html`

Or use the API:
```bash
# Browse all listings
curl https://webhooks.xswarm.ai/buzz/listings

# Search
curl https://webhooks.xswarm.ai/buzz/listings?search=automation

# Filter by category
curl https://webhooks.xswarm.ai/buzz/listings?category=saas

# Filter by price type
curl https://webhooks.xswarm.ai/buzz/listings?price_type=free

# Sort by most viewed
curl https://webhooks.xswarm.ai/buzz/listings?sort=views_desc

# Combine filters
curl https://webhooks.xswarm.ai/buzz/listings?category=saas&price_type=freemium&sort=views_desc
```

### Viewing a Listing

```bash
# View details (tracks view)
curl https://webhooks.xswarm.ai/buzz/listings/LISTING_ID
```

### Visiting a Product

Click the "Visit Product" button on the portal, or:
```bash
# Tracks click and redirects to product URL
curl -X POST https://webhooks.xswarm.ai/buzz/listings/LISTING_ID/click
```

### Reporting Inappropriate Content

```bash
curl -X POST https://webhooks.xswarm.ai/buzz/listings/LISTING_ID/report
```

## For Admins

### Approving a Listing

```javascript
import { approveListing } from './packages/server/src/lib/buzz-admin.js';

const listing = await approveListing('LISTING_ID', env);
// Sets status to 'approved'
// Sets expires_at to 90 days from now
```

### Rejecting a Listing

```javascript
import { rejectListing } from './packages/server/src/lib/buzz-admin.js';

const listing = await rejectListing('LISTING_ID', env);
```

### Featuring a Listing

```javascript
import { featureListing } from './packages/server/src/lib/buzz-admin.js';

// Feature
const listing = await featureListing('LISTING_ID', true, env);

// Unfeature
const listing = await featureListing('LISTING_ID', false, env);
```

### Viewing Moderation Queue

```javascript
import { getModerationQueue } from './packages/server/src/lib/buzz-admin.js';

const pending = await getModerationQueue(env, 50, 0);
// Returns listings with status 'pending_review'
```

### Viewing Reported Listings

```javascript
import { getReportedListings } from './packages/server/src/lib/buzz-admin.js';

const reported = await getReportedListings(env, 3); // Min 3 reports
```

### Viewing Analytics Dashboard

```javascript
import { getAdminAnalytics } from './packages/server/src/lib/buzz-admin.js';

const analytics = await getAdminAnalytics(env);
// Returns:
// - Overall stats
// - Category breakdown
// - Recent activity (30 days)
// - Top listings by views
// - Top listings by clicks
```

### Bulk Operations

```javascript
import {
  bulkApproveListings,
  bulkRejectListings,
  bulkDeleteListings
} from './packages/server/src/lib/buzz-admin.js';

// Approve multiple
await bulkApproveListings(['id1', 'id2', 'id3'], env);

// Reject multiple
await bulkRejectListings(['id4', 'id5'], env);

// Delete multiple
await bulkDeleteListings(['id6', 'id7'], env);
```

### Auto-Expire Old Listings

```javascript
import { expireListings } from './packages/server/src/lib/buzz-admin.js';

// Run this daily via cron job
const expiredCount = await expireListings(env);
console.log(`Expired ${expiredCount} listings`);
```

## Database Migration

Run once to create tables:

```bash
node scripts/migrate-buzz.js
```

## Response Examples

### List Listings Response
```json
{
  "success": true,
  "listings": [
    {
      "id": "uuid-here",
      "user_id": "user-uuid",
      "team_id": null,
      "title": "Awesome SaaS Product",
      "description": "This product does amazing things...",
      "category": "saas",
      "url": "https://example.com",
      "image_url": "https://example.com/image.png",
      "price_type": "freemium",
      "price_range": "10_50",
      "tags": ["productivity", "ai"],
      "status": "approved",
      "featured": false,
      "view_count": 150,
      "click_count": 25,
      "expires_at": "2025-04-29T10:00:00Z",
      "created_at": "2025-01-29T10:00:00Z",
      "updated_at": "2025-01-29T10:00:00Z",
      "approved_at": "2025-01-29T11:00:00Z"
    }
  ],
  "pagination": {
    "total": 42,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

### Stats Response (Individual Listing)
```json
{
  "success": true,
  "listing": {
    "id": "uuid-here",
    "title": "Awesome SaaS Product",
    "status": "approved",
    "created_at": "2025-01-29T10:00:00Z",
    "approved_at": "2025-01-29T11:00:00Z",
    "expires_at": "2025-04-29T10:00:00Z"
  },
  "stats": {
    "view_count": 150,
    "click_count": 25,
    "ctr": 16.67,
    "interactions": {
      "view": { "count": 150, "first": "...", "last": "..." },
      "click": { "count": 25, "first": "...", "last": "..." },
      "share": { "count": 5, "first": "...", "last": "..." },
      "report": { "count": 0 }
    },
    "daily_stats": [
      { "date": "2025-01-29", "view": 15, "click": 3 },
      { "date": "2025-01-28", "view": 20, "click": 4 }
    ]
  }
}
```

### Stats Response (User Summary)
```json
{
  "success": true,
  "summary": {
    "total_listings": 5,
    "approved_listings": 3,
    "pending_listings": 1,
    "draft_listings": 1,
    "rejected_listings": 0,
    "expired_listings": 0,
    "featured_listings": 1,
    "total_views": 450,
    "total_clicks": 75,
    "overall_ctr": 16.67,
    "listings_remaining": 2
  },
  "top_listings": [
    {
      "id": "uuid-here",
      "title": "Top Product",
      "category": "saas",
      "status": "approved",
      "view_count": 200,
      "click_count": 40,
      "ctr": 20.00,
      "created_at": "2025-01-15T10:00:00Z",
      "approved_at": "2025-01-15T11:00:00Z"
    }
  ]
}
```

## Common Use Cases

### 1. Promote Your New SaaS
```bash
curl -X POST https://webhooks.xswarm.ai/buzz/listings \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TaskMaster Pro",
    "description": "AI-powered task management that learns your workflow and optimizes your productivity. Never miss a deadline again!",
    "category": "saas",
    "url": "https://taskmasterpro.com",
    "image_url": "https://taskmasterpro.com/screenshot.png",
    "price_type": "freemium",
    "price_range": "10_50",
    "tags": ["productivity", "ai", "task-management"]
  }'
```

### 2. Find AI Tools
```bash
curl "https://webhooks.xswarm.ai/buzz/listings?search=ai&category=tool&sort=views_desc"
```

### 3. Monitor Your Listing Performance
```bash
# Get stats
STATS=$(curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "https://webhooks.xswarm.ai/buzz/stats?listing_id=YOUR_LISTING_ID")

# Extract CTR
echo $STATS | jq '.stats.ctr'
```

### 4. Update Pricing After Launch
```bash
curl -X PUT https://webhooks.xswarm.ai/buzz/listings/YOUR_LISTING_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"price_type": "paid", "price_range": "50_200"}'
```

## Tips for Success

### Writing Great Listings

1. **Title**: Clear, concise, memorable (max 100 chars)
2. **Description**: Focus on benefits, not features (10-500 chars)
3. **Image**: Use high-quality screenshots or product logos
4. **Tags**: Use relevant, searchable keywords
5. **Category**: Choose the most accurate category
6. **Pricing**: Be honest and transparent

### Maximizing Engagement

1. **Featured Status**: Request featuring from admin for premium visibility
2. **Regular Updates**: Keep description and pricing current
3. **Monitor Analytics**: Track CTR and optimize based on data
4. **Renew Promptly**: Don't let listings expire
5. **Respond to Reports**: Address any flagged content quickly

### Analytics Best Practices

1. **Track CTR**: Aim for >10% click-through rate
2. **A/B Test**: Try different descriptions and see what works
3. **Monitor Trends**: Check daily stats for patterns
4. **Compare Performance**: Use top_listings to benchmark
5. **Act on Data**: Update low-performing listings

## Troubleshooting

### "Pro+ subscription required"
- You need AI Project Manager or AI CTO tier
- Upgrade at: https://xswarm.ai

### "Maximum listings reached"
- Delete or wait for expiration of existing listings
- Limit: 5 active (approved + pending) per user

### "Listing not found"
- Check listing ID is correct
- Listing may have been deleted
- You may not have permission to view it

### "Already reported"
- You can only report once per 24 hours
- Prevents spam reporting

### Migration fails
- Ensure TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are in .env
- Check database connection
- Verify migrations haven't already been applied

## Support

For issues or questions:
- Email: support@xswarm.ai
- Documentation: https://docs.xswarm.ai
- GitHub: https://github.com/xswarm-dev/xswarm-boss/issues
