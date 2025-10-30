# Team Management - Quickstart Guide

Get started with xSwarm team collaboration in 5 minutes.

## Prerequisites

- AI Project Manager or AI CTO subscription tier
- Verified email address
- JWT authentication token

## Installation

### 1. Run Database Migration

```bash
cd packages/server
node scripts/run-teams-migration.js
```

This will:
- Add subscription_tier column to users table
- Create teams, team_members, and team_invitations tables
- Set up indexes and views

### 2. Update User Tiers

```bash
# Connect to your database and update user tiers
sqlite3 your-database.db

# Set users to AI Project Manager (max 10 members)
UPDATE users SET subscription_tier = 'ai_project_manager' WHERE email = 'user@example.com';

# Or set to AI CTO (unlimited members)
UPDATE users SET subscription_tier = 'ai_cto' WHERE email = 'admin@example.com';
```

### 3. Deploy Server

The team routes are already integrated. Just deploy your updated server code.

## API Usage

### Get Your Auth Token

```bash
curl -X POST https://api.xswarm.ai/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "yourpassword"
  }'
```

Save the JWT token from the response.

### Create Your First Team

```bash
curl -X POST https://api.xswarm.ai/teams \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Team",
    "description": "Our awesome development team"
  }'
```

Response:
```json
{
  "success": true,
  "team": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Team",
    "description": "Our awesome development team",
    "owner_id": "your-user-id",
    "subscription_tier": "ai_cto",
    "max_members": -1,
    "created_at": "2025-10-29T12:00:00Z",
    "updated_at": "2025-10-29T12:00:00Z"
  }
}
```

### Invite a Team Member

```bash
curl -X POST https://api.xswarm.ai/teams/TEAM_ID/invite \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teammate@example.com",
    "role": "member"
  }'
```

Your teammate will receive an email with an invitation link.

### List Your Teams

```bash
curl https://api.xswarm.ai/teams \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Team Details

```bash
curl https://api.xswarm.ai/teams/TEAM_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Subscription Tiers

| Tier | Team Access | Max Members |
|------|-------------|-------------|
| Free | ❌ | 0 |
| AI Secretary | ❌ | 0 |
| **AI Project Manager** | ✅ | 10 |
| **AI CTO** | ✅ | Unlimited |

## Roles & Permissions

### Owner
- Created the team
- Full control
- Can delete team
- Can change member roles
- All admin permissions

### Admin
- Can invite members
- Can remove members
- Can update team settings
- All member permissions

### Member
- Can use team features
- Can view team information
- Can collaborate

### Viewer
- Read-only access
- Can view team info
- Cannot modify

## Common Tasks

### Update Team Name

```bash
curl -X PUT https://api.xswarm.ai/teams/TEAM_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New Team Name"
  }'
```

### Remove a Member

```bash
curl -X DELETE https://api.xswarm.ai/teams/TEAM_ID/members/USER_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Change Member Role

```bash
curl -X PUT https://api.xswarm.ai/teams/TEAM_ID/members/USER_ID/role \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

### Delete Team

```bash
curl -X DELETE https://api.xswarm.ai/teams/TEAM_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Warning**: This permanently deletes the team and all memberships.

## Testing

Run the integration test suite:

```bash
cd packages/server
node test-teams-api.js
```

All tests should pass ✅

## Troubleshooting

### "Team features require AI Project Manager or AI CTO subscription tier"

Your user's subscription tier is not high enough. Update it:

```sql
UPDATE users SET subscription_tier = 'ai_project_manager' WHERE email = 'your@email.com';
```

### "Authentication required"

Your JWT token is missing or invalid. Get a new token via `/auth/login`.

### "Email not verified"

Verify your email address via the verification link sent during signup.

### "Team has reached maximum member limit of 10"

You've reached the member limit for AI Project Manager tier. Upgrade to AI CTO for unlimited members.

## Email Notifications

Team members automatically receive emails for:

1. **Invitation** - When invited to a team
   - Includes role description
   - Accept invitation link
   - Expires in 7 days

2. **Welcome** - After joining a team
   - Team name and role
   - Link to dashboard

3. **Removal** - When removed from a team
   - Team name
   - Support contact info

## API Reference

For complete API documentation, see:
- **TEAMS_API.md** - Full API reference with examples
- **TEAMS_IMPLEMENTATION_SUMMARY.md** - Technical details

## Support

- **Documentation**: See TEAMS_API.md
- **Issues**: Report via GitHub
- **Email**: support@xswarm.ai

## Next Steps

1. ✅ Create your first team
2. ✅ Invite team members
3. ✅ Start collaborating
4. Read the full API documentation for advanced features
5. Integrate with your frontend application

---

**Need Help?** Check TEAMS_API.md for detailed documentation.
