# Team Management API Documentation

Complete API reference for the xSwarm Team Management system. Team features are available for AI Project Manager and AI CTO subscription tiers.

## Table of Contents

- [Authentication](#authentication)
- [Subscription Tiers](#subscription-tiers)
- [Permissions](#permissions)
- [API Endpoints](#api-endpoints)
  - [Create Team](#create-team)
  - [List Teams](#list-teams)
  - [Get Team](#get-team)
  - [Update Team](#update-team)
  - [Delete Team](#delete-team)
  - [Invite Member](#invite-member)
  - [Join Team](#join-team)
  - [Remove Member](#remove-member)
  - [Change Member Role](#change-member-role)
- [Error Handling](#error-handling)
- [Quickstart Guide](#quickstart-guide)

## Authentication

All team endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

Get your JWT token by logging in via the `/auth/login` endpoint.

## Subscription Tiers

Team features are available for the following subscription tiers:

| Tier | Max Members | Features |
|------|-------------|----------|
| **AI Project Manager** | 10 | Basic team collaboration |
| **AI CTO** | Unlimited | Advanced team features |
| Free/AI Secretary | ❌ No access | Individual use only |

## Permissions

### Role Hierarchy

1. **Owner** - Full control over team
   - Delete team
   - Manage all members
   - Change member roles
   - All admin permissions

2. **Admin** - Team management
   - Invite members
   - Remove members
   - Update team settings
   - All member permissions

3. **Member** - Standard access
   - Use team features
   - View team information
   - Collaborate with team

4. **Viewer** - Read-only access
   - View team information
   - Read-only team resources

## API Endpoints

### Create Team

Create a new team (Pro+ tier only).

**Endpoint:** `POST /teams`

**Authentication:** Required

**Tier Requirement:** `ai_project_manager` or `ai_cto`

**Request Body:**

```json
{
  "name": "My Development Team",
  "description": "Team for building awesome products"
}
```

**Response:** `201 Created`

```json
{
  "success": true,
  "team": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Development Team",
    "description": "Team for building awesome products",
    "owner_id": "user-123",
    "subscription_tier": "ai_cto",
    "max_members": -1,
    "created_at": "2025-10-29T12:00:00Z",
    "updated_at": "2025-10-29T12:00:00Z"
  }
}
```

**Errors:**
- `400` - Invalid request (missing name, invalid length)
- `401` - Authentication required
- `403` - Insufficient subscription tier

---

### List Teams

List all teams the authenticated user is a member of.

**Endpoint:** `GET /teams`

**Authentication:** Required

**Response:** `200 OK`

```json
{
  "success": true,
  "teams": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Development Team",
      "description": "Team for building awesome products",
      "owner_id": "user-123",
      "subscription_tier": "ai_cto",
      "max_members": -1,
      "created_at": "2025-10-29T12:00:00Z",
      "updated_at": "2025-10-29T12:00:00Z",
      "user_role": "owner",
      "member_count": 5
    }
  ]
}
```

---

### Get Team

Get detailed information about a specific team, including members.

**Endpoint:** `GET /teams/:teamId`

**Authentication:** Required

**Permission:** Team membership required

**Response:** `200 OK`

```json
{
  "success": true,
  "team": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Development Team",
    "description": "Team for building awesome products",
    "owner_id": "user-123",
    "subscription_tier": "ai_cto",
    "max_members": -1,
    "created_at": "2025-10-29T12:00:00Z",
    "updated_at": "2025-10-29T12:00:00Z",
    "user_role": "owner",
    "member_count": 5,
    "members": [
      {
        "id": "member-1",
        "team_id": "550e8400-e29b-41d4-a716-446655440000",
        "user_id": "user-123",
        "user_name": "John Doe",
        "user_email": "john@example.com",
        "role": "owner",
        "invited_by": null,
        "joined_at": "2025-10-29T12:00:00Z",
        "invited_at": null
      }
    ]
  }
}
```

**Errors:**
- `403` - Not a team member
- `404` - Team not found

---

### Update Team

Update team details (name and/or description).

**Endpoint:** `PUT /teams/:teamId`

**Authentication:** Required

**Permission:** Admin or Owner

**Request Body:**

```json
{
  "name": "Updated Team Name",
  "description": "Updated description"
}
```

**Response:** `200 OK`

```json
{
  "success": true,
  "team": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Updated Team Name",
    "description": "Updated description",
    "owner_id": "user-123",
    "subscription_tier": "ai_cto",
    "max_members": -1,
    "created_at": "2025-10-29T12:00:00Z",
    "updated_at": "2025-10-29T12:30:00Z"
  }
}
```

**Errors:**
- `400` - Invalid request (invalid name/description length)
- `403` - Insufficient permissions (requires admin/owner)

---

### Delete Team

Delete a team permanently (owner only).

**Endpoint:** `DELETE /teams/:teamId`

**Authentication:** Required

**Permission:** Owner only

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Team deleted successfully"
}
```

**Note:** This cascades and deletes all team members and pending invitations.

**Errors:**
- `403` - Only the team owner can delete the team
- `404` - Team not found

---

### Invite Member

Invite a new member to the team via email.

**Endpoint:** `POST /teams/:teamId/invite`

**Authentication:** Required

**Permission:** Admin or Owner

**Request Body:**

```json
{
  "email": "newmember@example.com",
  "role": "member"
}
```

**Valid Roles:** `admin`, `member`, `viewer`

**Response:** `201 Created`

```json
{
  "success": true,
  "invitation": {
    "id": "invite-123",
    "email": "newmember@example.com",
    "role": "member",
    "expires_at": "2025-11-05T12:00:00Z",
    "created_at": "2025-10-29T12:00:00Z"
  }
}
```

**Note:** An invitation email is automatically sent to the invitee. The invitation expires in 7 days.

**Errors:**
- `400` - Invalid email or role
- `403` - Team has reached member limit (for Project Manager tier)
- `403` - Insufficient permissions (requires admin/owner)

---

### Join Team

Accept a team invitation and join the team.

**Endpoint:** `POST /teams/join/:token`

**Authentication:** Required

**Note:** The invitation token is sent via email.

**Response:** `200 OK`

```json
{
  "success": true,
  "team": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "My Development Team",
    "description": "Team for building awesome products",
    "role": "member"
  },
  "message": "Successfully joined team"
}
```

**Note:** A welcome email is sent to the new member.

**Errors:**
- `403` - Email doesn't match invitation
- `404` - Invalid or expired invitation
- `409` - Already a member of the team

---

### Remove Member

Remove a member from the team.

**Endpoint:** `DELETE /teams/:teamId/members/:userId`

**Authentication:** Required

**Permission:** Admin or Owner

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Member removed successfully"
}
```

**Note:** A removal notification email is sent to the removed member.

**Restrictions:**
- Cannot remove the team owner (transfer ownership first)
- Cannot remove yourself (use leave endpoint instead)

**Errors:**
- `403` - Cannot remove owner
- `403` - Insufficient permissions

---

### Change Member Role

Change a team member's role.

**Endpoint:** `PUT /teams/:teamId/members/:userId/role`

**Authentication:** Required

**Permission:** Owner only

**Request Body:**

```json
{
  "role": "admin"
}
```

**Valid Roles:** `admin`, `member`, `viewer`

**Response:** `200 OK`

```json
{
  "success": true,
  "message": "Member role updated successfully",
  "role": "admin"
}
```

**Restrictions:**
- Cannot change the owner's role (transfer ownership not yet implemented)
- Only the team owner can change roles

**Errors:**
- `400` - Invalid role
- `403` - Cannot change owner's role
- `403` - Only owner can change roles

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

- `200` - Success
- `201` - Created (resource created successfully)
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (authentication required/invalid)
- `403` - Forbidden (insufficient permissions or tier)
- `404` - Not Found (resource doesn't exist)
- `409` - Conflict (duplicate resource)
- `500` - Internal Server Error

### Common Error Messages

- `"Authentication required"` - No JWT token provided
- `"Email not verified"` - User must verify email before using team features
- `"Team features require AI Project Manager or AI CTO subscription tier"` - Insufficient tier
- `"You are not a member of this team"` - User not in team
- `"This action requires admin or owner role"` - Insufficient permissions
- `"Team has reached maximum member limit of 10"` - Member limit reached (Project Manager tier)

---

## Quickstart Guide

### 1. Create a Team

```bash
curl -X POST https://api.xswarm.ai/teams \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Team",
    "description": "Our awesome team"
  }'
```

### 2. Invite a Team Member

```bash
curl -X POST https://api.xswarm.ai/teams/TEAM_ID/invite \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teammate@example.com",
    "role": "member"
  }'
```

### 3. List Your Teams

```bash
curl https://api.xswarm.ai/teams \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 4. Get Team Details

```bash
curl https://api.xswarm.ai/teams/TEAM_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Update Team

```bash
curl -X PUT https://api.xswarm.ai/teams/TEAM_ID \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Team Name"
  }'
```

---

## Database Schema

The team system uses three main tables:

### teams
- `id` - Unique team identifier
- `name` - Team name
- `description` - Optional team description
- `owner_id` - User who created the team
- `subscription_tier` - Required tier (ai_project_manager, ai_cto)
- `max_members` - Member limit based on tier (10 or -1 for unlimited)
- `created_at`, `updated_at` - Timestamps

### team_members
- `id` - Unique membership identifier
- `team_id` - Team reference
- `user_id` - User reference
- `role` - Member role (owner, admin, member, viewer)
- `invited_by` - Who invited this member
- `joined_at`, `invited_at` - Timestamps

### team_invitations
- `id` - Unique invitation identifier
- `team_id` - Team reference
- `email` - Invitee email
- `role` - Intended role
- `token` - Secure invitation token (sent via email)
- `expires_at` - Expiration (7 days from creation)
- `created_by` - Who created the invitation
- `created_at` - Timestamp

---

## Support

For questions or issues with the Team Management API:

- Documentation: https://docs.xswarm.ai/teams
- Email: support@xswarm.ai
- GitHub: https://github.com/xswarm/xswarm-boss

---

**Last Updated:** 2025-10-29
