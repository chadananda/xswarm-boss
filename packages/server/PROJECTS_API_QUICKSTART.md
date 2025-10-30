# Project Management API - Quick Start Guide

## 1. Deploy the API

```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/server

# Deploy to Cloudflare Workers
npm run deploy
```

## 2. Set Environment Variables

Ensure these are set in Cloudflare Workers:

```
TURSO_DATABASE_URL=libsql://your-database.turso.io
TURSO_AUTH_TOKEN=your-auth-token
```

## 3. Run Database Migration

```bash
# Apply the projects schema
turso db shell your-database < migrations/projects.sql
```

## 4. Quick Test Workflow

### Step 1: Create a Project

```bash
curl -X POST https://your-worker.workers.dev/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "name": "My First Project",
    "description": "Testing the project API",
    "path": "/Users/me/projects/test",
    "priority": 1
  }'
```

Expected response:
```json
{
  "id": "proj_abc123",
  "name": "My First Project",
  "status": "active",
  "progress_percentage": 0
}
```

Save the `id` for next steps!

### Step 2: Add Some Tasks

```bash
PROJECT_ID="proj_abc123"  # Use the ID from step 1

# Task 1
curl -X POST https://your-worker.workers.dev/api/projects/$PROJECT_ID/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Set up project structure",
    "priority": 1,
    "estimated_hours": 2
  }'

# Task 2
curl -X POST https://your-worker.workers.dev/api/projects/$PROJECT_ID/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement core features",
    "priority": 2,
    "estimated_hours": 8
  }'

# Task 3
curl -X POST https://your-worker.workers.dev/api/projects/$PROJECT_ID/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Write tests",
    "priority": 2,
    "estimated_hours": 4
  }'
```

### Step 3: List All Tasks

```bash
curl https://your-worker.workers.dev/api/projects/$PROJECT_ID/tasks
```

Expected response:
```json
{
  "tasks": [
    {
      "id": "task_1",
      "title": "Set up project structure",
      "status": "pending",
      "priority": 1
    },
    {
      "id": "task_2",
      "title": "Implement core features",
      "status": "pending",
      "priority": 2
    },
    {
      "id": "task_3",
      "title": "Write tests",
      "status": "pending",
      "priority": 2
    }
  ],
  "total": 3
}
```

### Step 4: Update Task Status

```bash
TASK_ID="task_1"  # Use the ID from step 3

# Mark as in progress
curl -X PUT https://your-worker.workers.dev/api/projects/$PROJECT_ID/tasks/$TASK_ID \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress",
    "actual_hours": 1.5
  }'
```

### Step 5: Complete a Task

```bash
# Complete the task
curl -X POST https://your-worker.workers.dev/api/projects/$PROJECT_ID/tasks/$TASK_ID/complete
```

This automatically:
- Sets status to "completed"
- Sets completed_at timestamp
- Updates project progress percentage
- Updates project last_activity

### Step 6: Assign an Agent

```bash
curl -X POST https://your-worker.workers.dev/api/projects/$PROJECT_ID/assign \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "claude-code",
    "cost_budget": 50.00
  }'
```

### Step 7: Track Agent Costs

```bash
curl -X POST https://your-worker.workers.dev/api/agents/claude-code/costs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123",
    "cost": 2.50
  }'
```

### Step 8: Check Project Status

```bash
curl https://your-worker.workers.dev/api/projects/$PROJECT_ID/status
```

Expected response:
```json
{
  "project": {
    "id": "proj_abc123",
    "name": "My First Project",
    "status": "active",
    "progress_percentage": 33,
    "health_score": 0.65
  },
  "tasks": {
    "total": 3,
    "completed": 1,
    "in_progress": 0,
    "pending": 2,
    "blocked": 0
  },
  "git": {
    "total_commits": 0,
    "last_commit": null,
    "commits_today": 0
  },
  "agent": {
    "assigned_to": "claude-code",
    "cost_used": 2.50,
    "cost_budget": 50.00,
    "last_activity": "2025-10-29T12:00:00Z"
  }
}
```

### Step 9: Get Project Health Score

```bash
curl https://your-worker.workers.dev/api/projects/$PROJECT_ID/health
```

Expected response:
```json
{
  "project_id": "proj_abc123",
  "health_score": 0.65,
  "status": "active",
  "progress": 33,
  "last_activity": "2025-10-29T12:00:00Z"
}
```

### Step 10: View Analytics Dashboard

```bash
# All projects analytics
curl https://your-worker.workers.dev/api/projects/analytics

# User-specific analytics
curl "https://your-worker.workers.dev/api/projects/analytics?user_id=user_123"
```

Expected response:
```json
{
  "total_projects": 1,
  "active_projects": 1,
  "completed_projects": 0,
  "blocked_projects": 0,
  "total_tasks": 3,
  "completed_tasks": 1,
  "in_progress_tasks": 0,
  "blocked_tasks": 0,
  "total_commits": 0,
  "average_progress": 33.0
}
```

## 5. Common Patterns

### List Projects with Filters

```bash
# All active projects
curl "https://your-worker.workers.dev/api/projects?status=active"

# Projects assigned to specific agent
curl "https://your-worker.workers.dev/api/projects?assigned_agent=claude-code"

# Combine filters
curl "https://your-worker.workers.dev/api/projects?user_id=user_123&status=active&limit=10"
```

### Get Stalled Projects

```bash
curl https://your-worker.workers.dev/api/projects/stalled
```

This returns projects with no activity in 7+ days.

### Agent Workload

```bash
curl https://your-worker.workers.dev/api/agents/workload
```

Shows how many projects each agent is working on.

### Update Project Details

```bash
curl -X PUT https://your-worker.workers.dev/api/projects/$PROJECT_ID \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "progress_percentage": 100
  }'
```

## 6. Testing Script

Save this as `test-project-api.sh`:

```bash
#!/bin/bash

API_BASE="https://your-worker.workers.dev"
USER_ID="test_user_123"

echo "=== Testing Project Management API ==="
echo ""

# 1. Create project
echo "1. Creating project..."
PROJECT_RESPONSE=$(curl -s -X POST $API_BASE/api/projects \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"$USER_ID\",
    \"name\": \"Test Project $(date +%s)\",
    \"description\": \"Automated test project\",
    \"path\": \"/tmp/test-project\",
    \"priority\": 1
  }")

PROJECT_ID=$(echo $PROJECT_RESPONSE | jq -r '.id')
echo "Created project: $PROJECT_ID"
echo ""

# 2. Create tasks
echo "2. Creating tasks..."
for i in 1 2 3; do
  TASK_RESPONSE=$(curl -s -X POST $API_BASE/api/projects/$PROJECT_ID/tasks \
    -H "Content-Type: application/json" \
    -d "{
      \"title\": \"Test Task $i\",
      \"priority\": $i,
      \"estimated_hours\": $(($i * 2))
    }")
  TASK_ID=$(echo $TASK_RESPONSE | jq -r '.id')
  echo "  Created task: $TASK_ID"
done
echo ""

# 3. List tasks
echo "3. Listing tasks..."
TASKS=$(curl -s $API_BASE/api/projects/$PROJECT_ID/tasks)
echo "  Total tasks: $(echo $TASKS | jq '.total')"
echo ""

# 4. Complete first task
echo "4. Completing first task..."
FIRST_TASK=$(echo $TASKS | jq -r '.tasks[0].id')
curl -s -X POST $API_BASE/api/projects/$PROJECT_ID/tasks/$FIRST_TASK/complete > /dev/null
echo "  Completed: $FIRST_TASK"
echo ""

# 5. Assign agent
echo "5. Assigning agent..."
curl -s -X POST $API_BASE/api/projects/$PROJECT_ID/assign \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "test-agent",
    "cost_budget": 100.00
  }' > /dev/null
echo "  Assigned: test-agent"
echo ""

# 6. Track costs
echo "6. Tracking costs..."
curl -s -X POST $API_BASE/api/agents/test-agent/costs \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"cost\": 5.00
  }" > /dev/null
echo "  Tracked: $5.00"
echo ""

# 7. Get status
echo "7. Getting project status..."
STATUS=$(curl -s $API_BASE/api/projects/$PROJECT_ID/status)
echo "  Progress: $(echo $STATUS | jq '.project.progress_percentage')%"
echo "  Health: $(echo $STATUS | jq '.project.health_score')"
echo "  Tasks completed: $(echo $STATUS | jq '.tasks.completed')/$(echo $STATUS | jq '.tasks.total')"
echo ""

# 8. Get analytics
echo "8. Getting analytics..."
ANALYTICS=$(curl -s "$API_BASE/api/projects/analytics?user_id=$USER_ID")
echo "  Total projects: $(echo $ANALYTICS | jq '.total_projects')"
echo "  Active projects: $(echo $ANALYTICS | jq '.active_projects')"
echo "  Average progress: $(echo $ANALYTICS | jq '.average_progress')%"
echo ""

echo "=== Test Complete ==="
echo "Project ID: $PROJECT_ID"
```

Make it executable:
```bash
chmod +x test-project-api.sh
./test-project-api.sh
```

## 7. Integration with Rust Supervisor

The Rust supervisor should:

1. **Monitor Projects**: Query `/api/projects?status=active` periodically
2. **Update Progress**: Call `PUT /api/projects/:id` when tasks complete
3. **Sync Git**: Implement Git operations and update via `/api/projects/:id/sync-git`
4. **Track Costs**: Report agent costs via `POST /api/agents/:name/costs`
5. **Health Monitoring**: Query `/api/projects/:id/health` for stalled projects

### Example Rust Integration

```rust
// In Rust supervisor
async fn sync_project_to_api(project: &Project) -> Result<()> {
    let client = reqwest::Client::new();

    // Update project status
    let response = client
        .put(&format!("http://localhost:8787/api/projects/{}", project.id))
        .json(&json!({
            "status": project.status,
            "progress_percentage": project.progress_percentage
        }))
        .send()
        .await?;

    Ok(())
}
```

## 8. Common Issues

### Issue: "Project not found"
**Solution**: Verify the project ID is correct and belongs to the user

### Issue: "Validation failed"
**Solution**: Check the error details array for specific validation errors

### Issue: "Database connection failed"
**Solution**: Verify TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are set correctly

### Issue: Git sync returns empty commits
**Solution**: Normal in Cloudflare Workers. Git operations should be handled by Rust supervisor

## 9. Next Steps

1. **Authentication**: Add user authentication layer
2. **WebSockets**: Set up real-time updates from Rust supervisor
3. **Monitoring**: Add logging and error tracking
4. **Testing**: Implement automated API tests
5. **Documentation**: Generate OpenAPI/Swagger spec

## 10. Support

For issues or questions:
- Check `/packages/server/src/routes/projects.test.md` for detailed API documentation
- See `/packages/server/PROJECTS_API_SUMMARY.md` for implementation details
- Review database schema in `/packages/server/migrations/projects.sql`

---

**Status: READY TO USE**

The Project Management API is fully functional and ready for integration with your xSwarm Boss orchestration system!
