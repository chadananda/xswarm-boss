# Claude Code Bridge Integration

## Overview

The Claude Code Bridge connects the Boss Assistant's multi-channel communication system (SMS + Email) with development task execution capabilities. Users can send development requests via SMS or email and have them automatically detected, validated, and executed.

## Architecture

```
User Message (SMS/Email)
    ↓
Message Router (sms.js / email.js)
    ↓
Claude Service (claude.js)
    ↓
Claude Code Bridge (claude-code-bridge.js)
    ↓
Task Detection → Validation → Execution → Results
    ↓
Formatted Response (SMS/Email)
```

## Features

### 1. Intelligent Task Detection

The system automatically detects development tasks from natural language:

```javascript
// Examples of detected tasks:
"Check git status"        → GIT task (safe)
"Run the test suite"      → TEST task (safe)
"Build the project"       → BUILD task (low risk)
"Deploy to production"    → DEPLOY task (high risk)
"Update dependencies"     → DEPENDENCIES task (medium risk)
"Fix the bug in auth.js"  → DEBUG task (medium risk)
```

### 2. Risk-Based Safety System

Tasks are classified by risk level:

- **SAFE**: Read-only operations (git status, list files, run tests)
- **LOW**: Non-destructive changes (npm install, git pull, build)
- **MEDIUM**: Potentially risky operations (git commit, npm update)
- **HIGH**: Destructive operations (deploy, git push)
- **CRITICAL**: Requires explicit confirmation (force push, system operations)

### 3. Command Whitelisting

Only pre-approved commands can be executed:

```javascript
SAFE operations:
  - git status, git log, git diff
  - npm list
  - ls, cat, grep, find

LOW risk operations:
  - npm install, npm update
  - git pull, git checkout
  - npm run build, npm run test

MEDIUM risk operations:
  - git commit, git push
  - npm publish

HIGH risk operations:
  - git reset --hard
  - npm run deploy
  - rm -rf

CRITICAL operations:
  - git push --force
  - git rebase
  - system operations
```

### 4. Confirmation Flow for Risky Tasks

High-risk tasks require explicit user confirmation:

**Step 1: User sends task**
```
SMS: "Deploy to production"
```

**Step 2: System requests confirmation**
```
⚠️ "Deploy to production" is a high risk operation.

Commands:
• npm run deploy

Reply "CONFIRM" to proceed or "CANCEL" to abort.

- Boss
```

**Step 3: User confirms**
```
SMS: "CONFIRM"
```

**Step 4: Task executes**
```
✅ DEPLOY completed in 12s

Deployed successfully to production
Build: 1.2.3
Status: Live

- Boss
```

### 5. Multi-Channel Support

#### SMS Format (Concise)
```
✅ GIT completed in 2s

On branch main
Your branch is up to date
No changes to commit

- Boss
```

#### Email Format (Detailed)
```
Hello Test User,

✅ Task Completed: Check git status

**Task Details:**
- Type: git
- Risk Level: safe
- Execution Time: 2s
- Completed: 2024-01-15 10:30:00

**Commands Executed:**
  $ git status
  $ git diff --stat

**Output:**
```
On branch main
Your branch is up to date with 'origin/main'.
Nothing to commit, working tree clean
```

Task completed successfully!

Best regards,
Your Boss Assistant 🤖
```

## Task Types

### GIT Operations
- **Status check**: "Check git status", "What changed?"
- **Pull changes**: "Pull latest", "Sync with remote"
- **Commit**: "Commit these changes", "Save my work"
- **Push**: "Push to origin", "Upload changes"
- **Branch**: "Create new branch", "Switch to main"

### BUILD Operations
- **Build**: "Build the project", "Compile the code"
- **Bundle**: "Bundle for production"
- **Compile**: "Run the compiler"

### TEST Operations
- **Run tests**: "Run tests", "Test everything"
- **Specific tests**: "Test the auth module"
- **Coverage**: "Check test coverage"

### DEPLOY Operations
- **Deploy**: "Deploy to production", "Deploy to staging"
- **Publish**: "Publish the package", "Release version 1.0"

### DEPENDENCIES Operations
- **Install**: "Install dependencies", "Add packages"
- **Update**: "Update all packages", "Upgrade dependencies"
- **List**: "Show dependencies", "List installed packages"

### CODE ANALYSIS Operations
- **Lint**: "Lint the code", "Run ESLint"
- **Format**: "Format with Prettier", "Fix formatting"
- **Type check**: "Check types", "Run TypeScript"

### DEBUG Operations
- **Fix bugs**: "Fix the bug in auth.js"
- **Debug**: "Debug the login issue"
- **Error tracking**: "Find the error"

## Usage Examples

### Via SMS

**Check Status**
```
User: status
Boss: ✅ All systems operational
      📊 Active projects: 3
      ⚡ No blocking issues
      - Boss
```

**Run Tests**
```
User: run tests
Boss: ✅ TEST completed in 3s

      PASS  All tests passed
      ✓ 47 tests passing

      - Boss
```

**Build Project**
```
User: build the project
Boss: ✅ BUILD completed in 5s

      webpack compiled successfully
      asset main.js 125 KiB

      - Boss
```

### Via Email

**Deploy Request**
```
Subject: Deploy to staging
Body: Please deploy the latest changes to staging

Response:
Subject: Re: Deploy to staging

Hello Test User,

You've requested a **high risk** operation:

**Task:** Deploy application

**Commands to be executed:**
`npm run deploy`

**⚠️ Warning:** This operation may make significant changes.

To proceed, reply with "CONFIRM" in the subject or body.
To cancel, reply with "CANCEL" or simply ignore this message.

Best regards,
Your Boss Assistant 🤖
```

**Confirmation**
```
Subject: Re: Deploy to staging
Body: CONFIRM

Response:
Subject: Re: Deploy to staging

Hello Test User,

✅ Task Completed: Deploy application

**Task Details:**
- Type: deploy
- Risk Level: high
- Execution Time: 12s
- Completed: 2024-01-15 10:35:00

**Commands Executed:**
  $ npm run deploy

**Output:**
```
Deploying to staging...
Build completed
Uploading assets...
Deployment successful
```

Task completed successfully!

Best regards,
Your Boss Assistant 🤖
```

## Security Features

### 1. User Authentication
- Only authorized users can execute tasks
- Phone/email validation against user database
- Boss-to-User pairing ensures isolation

### 2. Command Whitelisting
- Only pre-approved commands can execute
- Commands validated against whitelist
- Dangerous operations blocked by default

### 3. Risk-Based Confirmation
- High-risk tasks require explicit confirmation
- Critical tasks always blocked in production
- User must acknowledge risks

### 4. Mock Mode (Default)
- All tasks execute in mock mode by default
- Simulates execution without making changes
- Returns realistic output for testing
- Real execution requires explicit configuration

### 5. Execution Logging
- All tasks logged with user, timestamp, commands
- Audit trail for security review
- Error tracking and debugging

## Mock Mode vs Real Execution

### Mock Mode (Current Default)
```javascript
// Safe simulation mode - no actual commands run
const result = await processDevTask(user, message, {
  mockMode: true  // Default
});

// Returns realistic mock output:
// - Git status shows fake repository state
// - Tests show passing results
// - Builds show compilation output
// - All safe for testing
```

### Real Execution (Future)
```javascript
// Real command execution - requires Claude Code integration
const result = await processDevTask(user, message, {
  mockMode: false,  // Enable real execution
  forceConfirmed: true  // For high-risk tasks
});

// Actually runs commands:
// - git status -> real git output
// - npm test -> real test results
// - npm build -> real build process
```

**Note**: Real execution is not yet implemented. The system currently operates in mock mode for safety. Real execution will require:
1. Full Claude Code integration
2. Sandboxed execution environment
3. Additional security audits
4. Production-ready error handling

## Configuration

### Enable/Disable Features

In `config.toml`:
```toml
[features]
claude_code_enabled = true  # Enable task execution
mock_mode_default = true    # Use mock mode by default
require_confirmation = true # Require confirmation for high-risk

[claude_code]
max_execution_time = 300000  # 5 minutes
allowed_directories = ["/Users/chad/Projects"]
blocked_commands = ["rm -rf /", "sudo", "shutdown"]
```

### User Permissions

In users configuration:
```json
{
  "username": "admin",
  "permissions": {
    "execute_tasks": true,
    "deploy_production": true,
    "high_risk_operations": true
  }
}
```

## Testing

Run the test suite:

```bash
# Test task detection and execution
node scripts/test-claude-code-bridge.js

# Test via webhook simulation
node scripts/test-webhooks.js
```

Example test output:
```
🧪 Testing Claude Code Bridge

📋 Test 1: Task Detection
Message: "Check git status"
  Is Dev Task: ✅ YES
  Type: git
  Risk: safe
  Needs Confirmation: NO
  Description: Check git status
  Commands:
    - git status
    - git diff --stat

⚡ Test 3: Mock Execution
Executing: "Check git status"
  ✅ Success
  Task Type: git
  Execution Time: 1247ms
  Output Preview:
    On branch main
    Your branch is up to date
    No changes to commit
```

## Error Handling

### Invalid Tasks
```javascript
User: "Make me a sandwich"
Boss: This doesn't appear to be a development task.
      How can I help with your project?
```

### Blocked Commands
```javascript
User: "Delete everything"
Boss: ⚠️ Task failed: Command not whitelisted: rm
```

### Execution Errors
```javascript
User: "Deploy to production"
Boss: ⚠️ Task failed: Deployment script not found

      I'll investigate this issue and try again.
```

## Future Enhancements

### Phase 1: Real Execution (Next)
- [ ] Integrate with actual Claude Code environment
- [ ] Sandboxed command execution
- [ ] Real-time progress streaming
- [ ] Rollback on failure

### Phase 2: Advanced Features
- [ ] Multi-step task planning
- [ ] Dependency graph analysis
- [ ] Parallel task execution
- [ ] Smart error recovery

### Phase 3: AI Integration
- [ ] Natural language task interpretation
- [ ] Context-aware suggestions
- [ ] Automated code generation
- [ ] Intelligent debugging

### Phase 4: Collaboration
- [ ] Team task coordination
- [ ] Code review automation
- [ ] CI/CD integration
- [ ] Status broadcasting

## API Reference

### Main Functions

#### `detectTask(message)`
Analyze message and detect development task type.

```javascript
const task = detectTask("Run the test suite");
// Returns: {
//   type: 'test',
//   commands: ['npm run test'],
//   risk: 'safe',
//   needsConfirmation: false,
//   description: 'Run test suite'
// }
```

#### `processDevTask(user, message, options)`
Execute a development task with safety checks.

```javascript
const result = await processDevTask(user, "Build the project", {
  mockMode: true,
  forceConfirmed: false
});
// Returns execution results with output
```

#### `isDevTask(message)`
Check if message contains a development task.

```javascript
const isDev = isDevTask("Run tests");
// Returns: true
```

#### `validateTaskExecution(task, user, options)`
Validate if task is allowed to execute.

```javascript
const validation = validateTaskExecution(task, user, { mockMode: true });
// Returns: { allowed: true, reason: 'Task validated successfully' }
```

## Support

For issues or questions:
- Check logs in Cloudflare Workers dashboard
- Review planning/CLAUDE_CODE_INTEGRATION.md
- Test with scripts/test-claude-code-bridge.js
- Contact: admin@xswarm.ai

## License

Part of the xSwarm Boss project. See main README for license details.
