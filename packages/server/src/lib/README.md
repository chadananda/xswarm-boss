# Server Library Components

## Overview

Core library modules for the xSwarm Boss server running on Cloudflare Workers.

## Modules

### `claude.js`
Main Claude AI integration service.

**Functions:**
- `getClaudeResponse(user, message, channel, env)` - Get AI response for user messages
- `processDevTask(user, taskDescription, env, channel)` - Process development tasks
- `parseMessageType(message)` - Classify message type (status, help, task, question)
- `getStatusResponse(user)` - Quick status response
- `getHelpResponse(user, channel)` - Help message for user

**Usage:**
```javascript
import { getClaudeResponse, processDevTask } from './claude.js';

// Get AI response
const response = await getClaudeResponse(user, 'How do I deploy?', 'sms', env);

// Execute development task
const result = await processDevTask(user, 'Run tests', env, 'sms');
```

### `claude-code-bridge.js`
Development task detection, validation, and execution bridge.

**Core Functions:**
- `detectTask(message)` - Detect and classify development tasks
- `processDevTask(user, message, options)` - Execute tasks with safety checks
- `isDevTask(message)` - Check if message is a dev task
- `validateTaskExecution(task, user, options)` - Validate task safety
- `formatResultsForSMS(results)` - Format for SMS
- `formatResultsForEmail(results, task, user)` - Format for email
- `getConfirmationMessage(task, channel)` - Generate confirmation request

**Task Types:**
- `GIT` - Git operations (status, commit, push, etc.)
- `BUILD` - Build and compilation tasks
- `TEST` - Test execution
- `DEPLOY` - Deployment operations
- `DEPENDENCIES` - Package management
- `CODE_ANALYSIS` - Linting, formatting, type checking
- `DEBUG` - Bug fixing and debugging
- `FILE_OPERATIONS` - File system operations

**Risk Levels:**
- `SAFE` - Read-only operations (no confirmation needed)
- `LOW` - Non-destructive changes (no confirmation needed)
- `MEDIUM` - Potentially risky (confirmation required)
- `HIGH` - Destructive operations (confirmation required)
- `CRITICAL` - Dangerous operations (always requires confirmation)

**Usage:**
```javascript
import { detectTask, processDevTask } from './claude-code-bridge.js';

// Detect task type
const task = detectTask('Run the test suite');
console.log(task.type); // 'test'
console.log(task.risk); // 'safe'

// Execute in mock mode (safe for testing)
const result = await processDevTask(user, 'Build the project', {
  mockMode: true,
  forceConfirmed: false
});

if (result.success) {
  console.log(formatResultsForSMS(result.results));
}
```

**Safety Features:**
1. **Command Whitelisting** - Only approved commands can execute
2. **Risk-Based Validation** - Tasks classified by danger level
3. **Confirmation Flow** - High-risk tasks require user confirmation
4. **Mock Mode** - Default safe simulation mode
5. **User Authentication** - Only authorized users can execute

### `auth.js`
Authentication and authorization for webhook endpoints.

**Functions:**
- Authentication validation
- User verification
- Token management

### `database.js`
Turso database integration for user data and subscriptions.

**Functions:**
- Database connection management
- User CRUD operations
- Subscription tracking

### `twilio.js`
Twilio API integration for voice and SMS.

**Functions:**
- Send SMS messages
- Initiate voice calls
- Handle webhooks
- TwiML generation

### `outbound.js`
Outbound communication management (SMS, email, voice).

**Functions:**
- Send notifications
- Progress reports
- Multi-channel messaging

## Testing

### Test Claude Code Bridge
```bash
# Run comprehensive test suite
node scripts/test-claude-code-bridge.js
```

Tests include:
- Task detection accuracy
- Risk classification
- Validation logic
- Mock execution
- Response formatting
- Edge cases

### Test Webhooks
```bash
# Test webhook integrations
node scripts/test-webhooks.js
```

## Configuration

### Environment Variables
Required in Cloudflare Workers secrets:

```bash
ANTHROPIC_API_KEY=sk-ant-...        # Claude AI API key
TWILIO_AUTH_TOKEN=...               # Twilio authentication
SENDGRID_API_KEY=SG...              # SendGrid for email
TURSO_AUTH_TOKEN=...                # Turso database token
```

### Mock Mode vs Real Execution

**Mock Mode (Default - Safe):**
```javascript
const result = await processDevTask(user, message, {
  mockMode: true  // Simulates execution, no real commands
});
```

**Real Execution (Future - Requires Setup):**
```javascript
const result = await processDevTask(user, message, {
  mockMode: false,  // Actually runs commands
  forceConfirmed: true  // For high-risk operations
});
```

⚠️ **Note**: Real execution is not yet implemented. System currently operates in safe mock mode only.

## Examples

### SMS Development Task Flow

**1. User sends task:**
```
SMS: "Run tests"
```

**2. System detects and executes:**
```javascript
// In sms.js webhook handler
const messageType = parseMessageType(message);

if (messageType === 'task') {
  const response = await processDevTask(user, message, env, 'sms');
  // Returns formatted SMS response
}
```

**3. User receives result:**
```
✅ TEST completed in 3s

PASS  All tests passed
✓ 47 tests passing

- Boss
```

### Email Development Task Flow

**1. User sends email:**
```
To: boss@xswarm.ai
Subject: Deploy to staging
Body: Please deploy the latest changes
```

**2. System requests confirmation (high-risk):**
```
Subject: Re: Deploy to staging

You've requested a **high risk** operation:

**Task:** Deploy application
**Commands:** npm run deploy

⚠️ Warning: This operation may make significant changes.

Reply "CONFIRM" to proceed or "CANCEL" to abort.
```

**3. User confirms:**
```
Subject: Re: Deploy to staging
Body: CONFIRM
```

**4. System executes and reports:**
```
Subject: Re: Deploy to staging

✅ Task Completed: Deploy application

**Task Details:**
- Type: deploy
- Risk Level: high
- Execution Time: 12s

**Commands Executed:**
  $ npm run deploy

**Output:**
```
Deployed successfully to staging
Build: 1.2.3
Status: Live
```

Task completed successfully!
```

## Security Considerations

### Whitelist Approach
Only specific commands are allowed. Unknown commands are blocked by default.

### Risk Escalation
Tasks are classified by potential danger:
- Read operations → SAFE (auto-approve)
- Installs/builds → LOW (auto-approve)
- Commits/pushes → MEDIUM (needs confirmation)
- Deploys/deletes → HIGH (needs confirmation)
- Force operations → CRITICAL (needs explicit confirmation)

### User Isolation
Each user can only execute tasks in their authorized scope. No cross-user access.

### Audit Trail
All task executions are logged with:
- User information
- Task details
- Commands executed
- Results and errors
- Timestamp

## Troubleshooting

### Task Not Detected
```javascript
// Check if message contains dev keywords
import { isDevTask } from './claude-code-bridge.js';

const isDev = isDevTask(message);
console.log('Is dev task:', isDev);
```

### Task Execution Fails
```javascript
// Check validation
import { detectTask, validateTaskExecution } from './claude-code-bridge.js';

const task = detectTask(message);
const validation = validateTaskExecution(task, user, { mockMode: true });

if (!validation.allowed) {
  console.error('Blocked:', validation.reason);
}
```

### Mock Output Not Realistic
Mock output is generated in `generateMockOutput()`. To add more realistic output for your use case, edit that function in `claude-code-bridge.js`.

## Future Development

### Phase 1: Real Execution
- [ ] Integrate actual command execution
- [ ] Sandboxed environment
- [ ] Real-time progress streaming
- [ ] Error recovery

### Phase 2: Advanced Features
- [ ] Multi-step task planning
- [ ] Parallel task execution
- [ ] Smart error recovery
- [ ] Task history and rollback

### Phase 3: AI Integration
- [ ] Natural language understanding
- [ ] Context-aware suggestions
- [ ] Automated code generation
- [ ] Intelligent debugging

## Documentation

For detailed documentation, see:
- `planning/CLAUDE_CODE_INTEGRATION.md` - Complete integration guide
- `planning/ARCHITECTURE.md` - System architecture
- `planning/SERVER_SETUP.md` - Server configuration

## Support

For issues or questions:
- Check server logs in Cloudflare Workers dashboard
- Run test scripts to verify functionality
- Review planning documentation
- Contact: admin@xswarm.ai
