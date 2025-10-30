# Boss AI Examples

This directory contains example clients and usage patterns for the Boss AI Unified API.

## CLI Client

Simple command-line client for sending messages to Boss AI.

### Usage

```bash
# Basic usage
node cli-client.js "What's my schedule today?"

# Schedule commands
node cli-client.js "Schedule meeting tomorrow at 2pm"

# Reminders
node cli-client.js "Remind me to call John at 3pm"

# Help
node cli-client.js help
```

### Configuration

Set environment variables to customize:

```bash
# Set API endpoint (default: http://localhost:8787/api/message)
export BOSS_API_URL="https://boss.xswarm.ai/api/message"

# Set your email address (default: chadananda@gmail.com)
export BOSS_USER_EMAIL="your-email@example.com"

# Use the client
node cli-client.js "status"
```

### Example Session

```bash
$ node cli-client.js "What can you help me with?"
Sending to: http://localhost:8787/api/message
From: chadananda@gmail.com
Message: "What can you help me with?"

✓ Success

Boss Response:
Hello Chad Jones,

I'm your Boss Assistant with full access to your development environment. Here's what I can help you with:

🗓️ Calendar Management:
- Schedule: "schedule meeting tomorrow at 2pm"
- View: "what's on my calendar today?"
- Reminders: "remind me to call John at 3pm"

📊 Status & Updates:
- "status" - Get current project status
- "what are you working on?" - See active tasks

💻 Development Tasks:
- Give me code to write
- Request features or fixes
- Ask technical questions

How can I help you today?

Processed for: Chad Jones
Timestamp: 2025-10-29T16:30:00.000Z
```

## cURL Examples

### Send CLI Message

```bash
curl -X POST http://localhost:8787/api/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "chadananda@gmail.com",
    "content": "What is my schedule today?",
    "channel": "cli"
  }'
```

Response:
```json
{
  "success": true,
  "message": "Here's your schedule for today:\n- 9:00 AM: Team standup\n- 2:00 PM: Client meeting",
  "metadata": {
    "user": "Chad Jones",
    "processedAt": "2025-10-29T16:30:00.000Z"
  },
  "timestamp": "2025-10-29T16:30:00.000Z"
}
```

### Schedule Appointment

```bash
curl -X POST http://localhost:8787/api/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "chadananda@gmail.com",
    "content": "schedule team meeting tomorrow at 3pm"
  }'
```

### Get Help

```bash
curl -X POST http://localhost:8787/api/message \
  -H "Content-Type: application/json" \
  -d '{
    "from": "chadananda@gmail.com",
    "content": "help"
  }'
```

## JavaScript/TypeScript Client

### Simple Fetch Client

```javascript
async function sendToBoss(message) {
  const response = await fetch('https://boss.xswarm.ai/api/message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: 'your-email@example.com',
      content: message,
      channel: 'cli',
    }),
  });

  const data = await response.json();

  if (data.success) {
    console.log('Boss says:', data.message);
  } else {
    console.error('Error:', data.message);
  }
}

// Usage
await sendToBoss('What is my schedule today?');
```

### Boss Client Class

```javascript
class BossClient {
  constructor(email, apiUrl = 'http://localhost:8787/api/message') {
    this.email = email;
    this.apiUrl = apiUrl;
  }

  async send(message, channel = 'cli') {
    try {
      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from: this.email,
          content: message,
          channel,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Failed to send message:', error);
      throw error;
    }
  }

  async schedule(title, when) {
    const message = `schedule ${title} ${when}`;
    return await this.send(message);
  }

  async remind(task, when) {
    const message = `remind me to ${task} ${when}`;
    return await this.send(message);
  }

  async getSchedule(when = 'today') {
    const message = `what's on my schedule ${when}?`;
    return await this.send(message);
  }

  async status() {
    return await this.send('status');
  }
}

// Usage
const boss = new BossClient('your-email@example.com');

// Schedule meeting
await boss.schedule('team standup', 'tomorrow at 9am');

// Set reminder
await boss.remind('call John', 'at 3pm');

// Get schedule
const schedule = await boss.getSchedule('today');
console.log(schedule.message);

// Get status
const status = await boss.status();
console.log(status.message);
```

## Python Client

```python
import requests
import json

class BossClient:
    def __init__(self, email, api_url='http://localhost:8787/api/message'):
        self.email = email
        self.api_url = api_url

    def send(self, message, channel='cli'):
        response = requests.post(
            self.api_url,
            headers={'Content-Type': 'application/json'},
            json={
                'from': self.email,
                'content': message,
                'channel': channel,
            }
        )

        response.raise_for_status()
        return response.json()

    def schedule(self, title, when):
        return self.send(f'schedule {title} {when}')

    def remind(self, task, when):
        return self.send(f'remind me to {task} {when}')

    def get_schedule(self, when='today'):
        return self.send(f"what's on my schedule {when}?")

    def status(self):
        return self.send('status')

# Usage
boss = BossClient('your-email@example.com')

# Schedule meeting
result = boss.schedule('team standup', 'tomorrow at 9am')
print(result['message'])

# Set reminder
result = boss.remind('call John', 'at 3pm')
print(result['message'])

# Get schedule
result = boss.get_schedule('today')
print(result['message'])

# Get status
result = boss.status()
print(result['message'])
```

## Testing

Run the integration tests to verify everything works:

```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/server
node test-integration.js
```

Expected output:
```
Boss AI - Unified API Integration Tests

Testing: Health check endpoint... ✓ PASS
Testing: POST /api/message with valid user... ✓ PASS
Testing: POST /api/message with unauthorized user... ✓ PASS
Testing: POST /api/message with empty content... ✓ PASS
Testing: POST /sms/inbound with valid SMS... ✓ PASS
Testing: POST /email/inbound with valid email... ✓ PASS
Testing: OPTIONS request (CORS preflight)... ✓ PASS
Testing: GET /invalid-endpoint returns 404... ✓ PASS
Testing: POST /api/message with different valid user... ✓ PASS
Testing: POST /api/message with schedule command... ✓ PASS

Test Summary
Passed: 10
Failed: 0
Total: 10

✓ All tests passed!
```

## Architecture

For a detailed explanation of the unified API architecture, see:
[UNIFIED_API_ARCHITECTURE.md](../UNIFIED_API_ARCHITECTURE.md)

## Support

For questions or issues:
1. Check the [UNIFIED_API_ARCHITECTURE.md](../UNIFIED_API_ARCHITECTURE.md) documentation
2. Run tests: `node test-integration.js`
3. Check logs: `wrangler tail` (for deployed version)
4. Open an issue on GitHub
