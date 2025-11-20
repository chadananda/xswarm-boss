# Suggestions System - Quick Start Guide

## Deployment Steps

### 1. Run Database Migration
```bash
# Using Wrangler with Cloudflare D1
wrangler d1 execute DB --file=packages/server/migrations/suggestions.sql

# Or using local SQLite
sqlite3 your-database.db < packages/server/migrations/suggestions.sql
```

### 2. Set Environment Variables
```bash
# Add to .env or Cloudflare Workers environment
ADMIN_EMAIL=admin@xswarm.ai
SENDGRID_API_KEY=your-sendgrid-key
```

### 3. Configure Cron Jobs
Add to `wrangler.toml`:
```toml
[triggers]
crons = [
  "0 9 * * 1",  # Weekly digest every Monday at 9am
  "0 2 * * *"   # Daily auto-prioritize at 2am
]
```

### 4. Deploy
```bash
cd packages/server
wrangler deploy
```

### 5. Test Endpoints
```bash
# Submit a suggestion
curl -X POST https://your-domain.workers.dev/api/suggestions \
  -H "Content-Type: application/json" \
  -d '{
    "category": "feature_request",
    "title": "Test suggestion",
    "description": "This is a test suggestion to verify the system works",
    "email": "test@example.com"
  }'

# List suggestions
curl https://your-domain.workers.dev/api/suggestions

# Get stats (requires admin auth)
curl https://your-domain.workers.dev/api/suggestions/stats \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

## API Quick Reference

### Public Endpoints

#### Submit Suggestion
```
POST /api/suggestions
Content-Type: application/json

{
  "category": "feature_request" | "bug_report" | "improvement" | "general",
  "title": "string (1-100 chars)",
  "description": "string (10-2000 chars)",
  "email": "string" (required for anonymous)
}
```

#### List Suggestions
```
GET /api/suggestions?category=feature_request&status=new&sort=upvotes&limit=50&offset=0
```

Query parameters:
- `category`: filter by category
- `status`: filter by status
- `search`: full-text search
- `sort`: `upvotes` or `created_at`
- `order`: `asc` or `desc`
- `limit`: results per page (default: 50)
- `offset`: pagination offset (default: 0)

#### Get Suggestion
```
GET /api/suggestions/:id
```

### Authenticated Endpoints

#### Vote on Suggestion
```
POST /api/suggestions/:id/vote
Authorization: Bearer YOUR_TOKEN
```

#### Remove Vote
```
DELETE /api/suggestions/:id/vote
Authorization: Bearer YOUR_TOKEN
```

### Admin Endpoints

#### Update Suggestion
```
PUT /api/suggestions/:id
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json

{
  "status": "new" | "reviewed" | "in_progress" | "completed" | "rejected",
  "priority": "low" | "medium" | "high" | "critical",
  "admin_notes": "string",
  "implementation_effort": 1-5
}
```

#### Delete Suggestion
```
DELETE /api/suggestions/:id
Authorization: Bearer ADMIN_TOKEN
```

#### Get Analytics
```
GET /api/suggestions/stats
Authorization: Bearer ADMIN_TOKEN
```

## Admin Utilities

### Using the Admin Library

```javascript
import {
  findPotentialDuplicates,
  bulkUpdateStatus,
  getSuggestionsNeedingAttention,
  exportSuggestionsToCSV,
  getRoadmapSuggestions
} from './lib/suggestions-admin.js';

// Find duplicates
const duplicates = findPotentialDuplicates(
  "Add dark mode",
  "I would like a dark theme option"
);

// Bulk update status
const updated = bulkUpdateStatus(
  ['id1', 'id2', 'id3'],
  'reviewed',
  'Thanks for the suggestions! We\'re reviewing these.'
);

// Get suggestions needing attention
const needsReview = getSuggestionsNeedingAttention();

// Export to CSV for planning
const csv = exportSuggestionsToCSV({
  status: 'reviewed',
  priority: 'high'
});

// Get roadmap-ready suggestions
const roadmap = getRoadmapSuggestions(20);
```

## Manual Cron Triggers

### Trigger Weekly Digest
```bash
curl -X POST https://your-domain.workers.dev/api/suggestions/cron/weekly-digest \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### Trigger Auto-Prioritize
```bash
curl -X POST https://your-domain.workers.dev/api/suggestions/cron/auto-prioritize \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## Web Interface

Access the public suggestion portal at:
```
https://your-domain.com/suggestions.html
```

Features:
- Submit suggestions anonymously or while logged in
- Browse and search existing suggestions
- Filter by category and status
- Sort by votes or date
- Vote on suggestions (requires login)

## Monitoring

### Key Metrics to Track

```sql
-- Total suggestions
SELECT COUNT(*) FROM suggestions;

-- Suggestions by status
SELECT status, COUNT(*)
FROM suggestions
GROUP BY status;

-- Top voted suggestions
SELECT title, upvotes, status
FROM suggestions
ORDER BY upvotes DESC
LIMIT 10;

-- Suggestions needing review
SELECT * FROM suggestions_need_review;

-- Weekly activity
SELECT
  DATE(created_at) as date,
  COUNT(*) as count
FROM suggestions
WHERE created_at >= datetime('now', '-7 days')
GROUP BY DATE(created_at);
```

## Troubleshooting

### No emails being sent
1. Check `SENDGRID_API_KEY` environment variable
2. Verify `ADMIN_EMAIL` is set
3. Check SendGrid API quota and status
4. Review Cloudflare Workers logs

### Duplicate detection not working
1. Ensure FTS5 table is populated: `SELECT COUNT(*) FROM suggestions_fts;`
2. Check triggers are created: `.schema suggestions_fts_insert`
3. Re-populate FTS: `INSERT INTO suggestions_fts SELECT id, title, description, category FROM suggestions;`

### Votes not counting
1. Check triggers exist: `.schema increment_suggestion_upvotes`
2. Verify vote table has data: `SELECT COUNT(*) FROM suggestion_votes;`
3. Check for foreign key constraints

### Rate limiting too strict
Adjust in `suggestions.js`:
```javascript
if (recentSubmissions?.count >= 5) {  // Change from 3 to 5
  // ...
}
```

## Best Practices

### For Administrators

1. **Review suggestions weekly**: Check `suggestions_need_review` view
2. **Respond promptly**: Update status within 7 days of submission
3. **Add notes**: Always include admin_notes when changing status
4. **Merge duplicates**: Use `mergeDuplicateSuggestions()` to consolidate
5. **Export regularly**: Create CSV exports for product planning meetings
6. **Monitor trends**: Use analytics to identify popular categories

### For Users

1. **Search first**: Check if suggestion already exists before submitting
2. **Be specific**: Include details about use case and benefits
3. **Vote wisely**: Upvote suggestions you genuinely want
4. **Check status**: Follow up on your suggestions via email notifications

## Email Notification Examples

### Confirmation Email (to user)
- Sent immediately after submission
- Includes tracking link
- Styled with xSwarm theme

### Admin Notification (to admin)
- Sent for each new suggestion
- Includes full details
- Link to admin management

### Status Update (to user)
- Sent when admin changes status
- Includes admin notes if provided
- Color-coded by status type

### Weekly Digest (to admin)
- Sent every Monday at 9am
- Summary statistics
- Top suggestions of the week
- Suggestions needing attention

## Advanced Features

### Custom Priority Scoring

Modify in `suggestions-admin.js`:
```javascript
const totalScore =
  (suggestion.upvotes * 10) +        // Vote weight
  (priorityScore * 5) +              // Priority weight
  (effortScore * 10) +               // Effort weight
  (ageScore * 5);                    // Recency weight
```

### Export Filters

```javascript
const csv = exportSuggestionsToCSV({
  status: 'reviewed',
  category: 'feature_request',
  priority: 'high'
});
```

### Bulk Operations

```javascript
// Review all high-priority suggestions
const highPriority = getSuggestionsByStatus('new', 100)
  .filter(s => s.upvotes >= 10);

const ids = highPriority.map(s => s.id);
bulkUpdateStatus(ids, 'reviewed', 'High-priority batch review');
```

## Support

For issues or questions:
1. Check logs in Cloudflare Workers dashboard
2. Review database schema and indexes
3. Verify environment variables
4. Test API endpoints with curl
5. Check email delivery in SendGrid dashboard

## Updates and Maintenance

### Database Backup
```bash
# Backup suggestions
wrangler d1 execute DB --command="SELECT * FROM suggestions" > suggestions-backup.sql
```

### Clean Old Rejected Suggestions
```sql
DELETE FROM suggestions
WHERE status = 'rejected'
  AND updated_at <= datetime('now', '-90 days');
```

### Reset Vote Counts (if needed)
```sql
UPDATE suggestions
SET upvotes = (
  SELECT COUNT(*)
  FROM suggestion_votes
  WHERE suggestion_id = suggestions.id
);
```

## Next Steps

1. ✅ Deploy the system
2. ✅ Test all endpoints
3. ✅ Verify email delivery
4. ✅ Add link to navigation
5. ✅ Announce to users
6. ✅ Monitor submissions
7. ✅ Review weekly digest
8. ✅ Plan roadmap based on feedback

---

**System Status**: ✅ Production Ready
**Version**: 1.0.0
**Last Updated**: 2025-10-29
