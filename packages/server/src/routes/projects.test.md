# Project Management API - Testing Guide

## Overview

This document provides comprehensive testing examples for the Project Management API routes.

## Base URL

```
https://your-worker.workers.dev
```

## Authentication

All requests should include the user_id in the request body or query parameters for user-based filtering.

---

## Project CRUD Operations

### Create Project

```bash
curl -X POST https://your-worker.workers.dev/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "name": "xSwarm Boss",
    "description": "AI orchestration system",
    "path": "/Users/chad/Projects/xswarm-boss",
    "git_url": "https://github.com/user/xswarm-boss",
    "priority": 1
  }'
```

**Expected Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_123",
  "name": "xSwarm Boss",
  "description": "AI orchestration system",
  "path": "/Users/chad/Projects/xswarm-boss",
  "git_url": "https://github.com/user/xswarm-boss",
  "status": "active",
  "assigned_agent": null,
  "priority": 1,
  "progress_percentage": 0,
  "last_activity": "2025-10-29T12:00:00Z",
  "created_at": "2025-10-29T12:00:00Z",
  "updated_at": "2025-10-29T12:00:00Z"
}
```

### List Projects

```bash
# All projects for a user
curl "https://your-worker.workers.dev/api/projects?user_id=user_123"

# Filter by status
curl "https://your-worker.workers.dev/api/projects?user_id=user_123&status=active"

# Filter by assigned agent
curl "https://your-worker.workers.dev/api/projects?assigned_agent=claude-code"

# Pagination
curl "https://your-worker.workers.dev/api/projects?user_id=user_123&limit=10&offset=0"
```

**Expected Response:**
```json
{
  "projects": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "xSwarm Boss",
      "status": "active",
      "progress_percentage": 75,
      ...
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Get Project Details

```bash
curl "https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000"
```

### Update Project

```bash
curl -X PUT https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "progress_percentage": 100
  }'
```

### Delete Project

```bash
curl -X DELETE https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000
```

---

## Task Management

### Create Task

```bash
curl -X POST https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement project routes",
    "description": "Create comprehensive API routes for project management",
    "assigned_to": "claude-code",
    "priority": 1,
    "estimated_hours": 4.0
  }'
```

**Expected Response:**
```json
{
  "id": "task_123",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Implement project routes",
  "description": "Create comprehensive API routes for project management",
  "status": "pending",
  "assigned_to": "claude-code",
  "priority": 1,
  "estimated_hours": 4.0,
  "actual_hours": null,
  "created_at": "2025-10-29T12:00:00Z",
  "updated_at": "2025-10-29T12:00:00Z",
  "completed_at": null
}
```

### List Tasks

```bash
# All tasks for a project
curl "https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/tasks"

# Filter by status
curl "https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/tasks?status=in_progress"
```

### Update Task

```bash
curl -X PUT https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/tasks/task_123 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "actual_hours": 2.5
  }'
```

### Complete Task

```bash
curl -X POST https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/tasks/task_123/complete
```

### Delete Task

```bash
curl -X DELETE https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/tasks/task_123
```

---

## Git Integration

### Sync Git Repository

```bash
curl -X POST https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/sync-git
```

**Expected Response:**
```json
{
  "synced": true,
  "commits_processed": 10,
  "commits_inserted": 5
}
```

**Note:** Git operations are not supported directly in Cloudflare Workers. This endpoint is designed to trigger the Rust supervisor to perform Git operations and sync results to the database.

---

## Agent Management

### Assign Project to Agent

```bash
curl -X POST https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/assign \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "claude-code",
    "cost_budget": 50.00
  }'
```

**Expected Response:**
```json
{
  "id": "assignment_123",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "claude-code",
  "status": "active",
  "cost_budget": 50.00,
  "cost_used": 0.0,
  "assigned_at": "2025-10-29T12:00:00Z",
  "last_activity": "2025-10-29T12:00:00Z"
}
```

### Unassign Agent

```bash
curl -X DELETE https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/assign
```

### Get Agent Workload

```bash
curl "https://your-worker.workers.dev/api/agents/workload"
```

**Expected Response:**
```json
{
  "workload": [
    {
      "agent_name": "claude-code",
      "project_count": 5,
      "active_projects": 3,
      "completed_projects": 2,
      "avg_progress": 65.5,
      "last_activity": "2025-10-29T11:45:00Z"
    }
  ]
}
```

### Track Agent Costs

```bash
curl -X POST https://your-worker.workers.dev/api/agents/claude-code/costs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "cost": 2.50
  }'
```

---

## Analytics and Reporting

### Get Project Analytics

```bash
# All projects analytics
curl "https://your-worker.workers.dev/api/projects/analytics"

# User-specific analytics
curl "https://your-worker.workers.dev/api/projects/analytics?user_id=user_123"
```

**Expected Response:**
```json
{
  "total_projects": 10,
  "active_projects": 6,
  "completed_projects": 3,
  "blocked_projects": 1,
  "total_tasks": 45,
  "completed_tasks": 30,
  "in_progress_tasks": 10,
  "blocked_tasks": 5,
  "total_commits": 150,
  "average_progress": 67.5
}
```

### Get Stalled Projects

```bash
curl "https://your-worker.workers.dev/api/projects/stalled"
```

**Expected Response:**
```json
{
  "stalled_projects": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Old Project",
      "status": "active",
      "days_stalled": 14,
      "last_activity": "2025-10-15T12:00:00Z",
      ...
    }
  ]
}
```

### Get Project Status Report

```bash
curl "https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/status"
```

**Expected Response:**
```json
{
  "project": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "xSwarm Boss",
    "status": "active",
    "progress_percentage": 75,
    "health_score": 0.85
  },
  "tasks": {
    "total": 10,
    "completed": 7,
    "in_progress": 2,
    "pending": 0,
    "blocked": 1
  },
  "git": {
    "total_commits": 10,
    "last_commit": {
      "hash": "abc123",
      "message": "Add project routes",
      "author": "Developer <dev@example.com>",
      "date": "2025-10-29T11:30:00Z"
    },
    "commits_today": 3
  },
  "agent": {
    "assigned_to": "claude-code",
    "cost_used": 15.50,
    "cost_budget": 50.00,
    "last_activity": "2025-10-29T11:45:00Z"
  }
}
```

### Get Project Health Score

```bash
curl "https://your-worker.workers.dev/api/projects/550e8400-e29b-41d4-a716-446655440000/health"
```

**Expected Response:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "health_score": 0.85,
  "status": "active",
  "progress": 75,
  "last_activity": "2025-10-29T11:45:00Z"
}
```

---

## Error Responses

### Validation Error

```json
{
  "error": "Validation failed",
  "code": "VALIDATION_ERROR",
  "status": 400,
  "details": [
    "Priority must be between 1 and 5",
    "Name is required and must be 1-100 characters"
  ]
}
```

### Not Found

```json
{
  "error": "Project not found",
  "code": "PROJECT_NOT_FOUND",
  "status": 404
}
```

### Server Error

```json
{
  "error": "Failed to create project",
  "code": "CREATE_FAILED",
  "status": 500
}
```

---

## Health Score Algorithm

The health score is calculated based on multiple factors:

1. **Progress Factor (0.0 - 0.3)**: Based on project completion percentage
2. **Activity Factor (0.0 - 0.2)**: Recent activity (last 30 days)
3. **Task Completion Factor (0.0 - 0.3)**: Ratio of completed tasks
4. **Blocked Tasks Penalty (-0.2)**: Deduction for blocked tasks
5. **Recent Commits Bonus (0.0 - 0.2)**: Commits in last 7 days

**Formula:**
```
score = 0.5 (base)
  + (progress / 100) * 0.3
  + max(0, 0.2 - (days_since_activity / 30) * 0.2)
  + (completed_tasks / total_tasks) * 0.3
  - min(0.2, blocked_tasks * 0.05)
  + min(0.2, (recent_commits / 10) * 0.2)

Final score: max(0, min(1, score))
```

---

## Integration with Rust Supervisor

The Node.js API layer is designed to work seamlessly with the Rust ProjectManager system:

1. **Database Sync**: Both systems read/write to the same Turso database
2. **Git Operations**: Node.js API triggers Rust supervisor for Git operations
3. **Agent Coordination**: WebSocket messages for real-time updates
4. **Cost Tracking**: Shared database for agent cost management

### WebSocket Events

The Rust supervisor can send these events:

```json
{
  "type": "project_updated",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "progress": 80
}
```

```json
{
  "type": "task_completed",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": "task_123",
  "completed_at": "2025-10-29T12:00:00Z"
}
```

```json
{
  "type": "git_sync_complete",
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "commits_added": 5
}
```

---

## Best Practices

1. **User Isolation**: Always filter by `user_id` to ensure users only see their own projects
2. **Error Handling**: Check response status codes and handle errors appropriately
3. **Pagination**: Use `limit` and `offset` for large project lists
4. **Health Monitoring**: Regularly check project health scores and stalled projects
5. **Cost Tracking**: Update agent costs frequently for accurate budget tracking
6. **Git Sync**: Run Git sync periodically to keep commit history up to date

---

## Testing Checklist

- [ ] Create project with valid data
- [ ] Create project with invalid data (validation)
- [ ] List projects with filters
- [ ] Get project details
- [ ] Update project
- [ ] Delete project
- [ ] Create tasks
- [ ] Update task status
- [ ] Complete task
- [ ] Delete task
- [ ] Assign agent to project
- [ ] Track agent costs
- [ ] Unassign agent
- [ ] Get agent workload
- [ ] Get project analytics
- [ ] Get stalled projects
- [ ] Get project status report
- [ ] Get project health score
- [ ] Sync Git repository

---

## Database Schema Reference

This API integrates with the following database tables:

- `projects`: Main project records
- `project_tasks`: Task management
- `project_commits`: Git commit history
- `agent_assignments`: Agent coordination and cost tracking

See `/packages/server/migrations/projects.sql` for complete schema.
