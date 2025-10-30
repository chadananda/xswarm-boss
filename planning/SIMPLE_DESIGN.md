# Boss AI: Simple & Elegant Design

**Philosophy:** Minimal, testable, easy to understand, easy to extend

## Core Concept

Boss AI is a **message router** that:
1. Receives messages from any channel (SMS/Email/Voice)
2. Routes admin messages to Claude Code
3. Handles simple commands (calendar, reminders)
4. Responds back through the same channel

## Simple Architecture

```
┌─────────────────────────────────────────┐
│              Boss AI                     │
├─────────────────────────────────────────┤
│  Message Router (1 file)                │
│  ┌─────────┬─────────┬─────────────────┐ │
│  │   SMS   │  Email  │  Claude Code    │ │
│  │ Handler │ Handler │   Connector     │ │
│  └─────────┴─────────┴─────────────────┘ │
├─────────────────────────────────────────┤
│  Simple Services (3 files)              │
│  ┌─────────┬─────────┬─────────────────┐ │
│  │Calendar │Reminders│    Projects     │ │
│  │ (basic) │(basic)  │   (minimal)     │ │
│  └─────────┴─────────┴─────────────────┘ │
├─────────────────────────────────────────┤
│  Storage (1 database, 4 tables)         │
│  ┌─────────┬─────────┬─────────────────┐ │
│  │  users  │  events │   reminders     │ │
│  │         │         │   messages      │ │
│  └─────────┴─────────┴─────────────────┘ │
└─────────────────────────────────────────┘
```

## File Structure (Minimal)

```
packages/
├── server/                     # Node.js/Cloudflare Workers
│   ├── src/
│   │   ├── index.js           # Main router (200 lines)
│   │   ├── auth.js            # Simple auth (50 lines)
│   │   ├── calendar.js        # Basic calendar (150 lines)
│   │   ├── reminders.js       # Simple reminders (100 lines)
│   │   └── claude.js          # Claude Code connector (100 lines)
│   └── package.json
├── core/                       # Rust client (optional)
│   ├── src/
│   │   ├── main.rs            # CLI commands (200 lines)
│   │   └── client.rs          # HTTP client (100 lines)
│   └── Cargo.toml
└── database/
    └── schema.sql             # 4 tables (50 lines)
```

**Total: ~900 lines of code**

## Database Schema (4 Simple Tables)

```sql
-- Users (who can talk to Boss)
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    phone TEXT,
    email TEXT,
    name TEXT,
    is_admin BOOLEAN DEFAULT FALSE
);

-- Events (calendar appointments)
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    start_time TEXT,  -- ISO 8601
    end_time TEXT,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Reminders (simple notifications)
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    text TEXT,
    due_time TEXT,    -- ISO 8601
    method TEXT,      -- 'sms', 'email'
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Messages (conversation log)
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    channel TEXT,     -- 'sms', 'email', 'voice'
    direction TEXT,   -- 'in', 'out'
    content TEXT,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Core Functions (Simple & Testable)

### 1. Message Router (`index.js`)

```javascript
// Main message router - handles ALL incoming messages
export async function handleMessage(channel, from, content, env) {
  const user = await findUser(from, env);
  if (!user) return { error: 'Unknown user' };

  await logMessage(user.id, channel, 'in', content, env);

  // Route admin messages to Claude Code
  if (user.is_admin) {
    const response = await routeToClaudeCode(user.id, content, channel, env);
    await logMessage(user.id, channel, 'out', response, env);
    return { message: response };
  }

  // Handle simple commands
  const response = await handleCommand(user.id, content, env);
  await logMessage(user.id, channel, 'out', response, env);
  return { message: response };
}

// Simple command parser
async function handleCommand(userId, content, env) {
  const text = content.toLowerCase();

  if (text.includes('schedule') || text.includes('appointment')) {
    return await handleScheduleCommand(userId, content, env);
  }

  if (text.includes('remind')) {
    return await handleReminderCommand(userId, content, env);
  }

  if (text.includes('calendar') || text.includes('today')) {
    return await handleCalendarCommand(userId, content, env);
  }

  return "I can help with: schedule, reminders, calendar. Try 'schedule meeting tomorrow 2pm'";
}
```

### 2. Calendar Service (`calendar.js`)

```javascript
// Parse natural language dates (simple version)
export function parseDateTime(text) {
  const now = new Date();

  if (text.includes('tomorrow')) {
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    tomorrow.setHours(9, 0, 0, 0); // Default 9am
    return tomorrow.toISOString();
  }

  if (text.includes('today')) {
    now.setHours(9, 0, 0, 0);
    return now.toISOString();
  }

  // Extract time if present
  const timeMatch = text.match(/(\d{1,2})\s*(am|pm)/i);
  if (timeMatch) {
    let hour = parseInt(timeMatch[1]);
    if (timeMatch[2].toLowerCase() === 'pm' && hour !== 12) hour += 12;
    if (timeMatch[2].toLowerCase() === 'am' && hour === 12) hour = 0;

    const date = text.includes('tomorrow') ?
      new Date(now.getTime() + 24 * 60 * 60 * 1000) : now;
    date.setHours(hour, 0, 0, 0);
    return date.toISOString();
  }

  return now.toISOString();
}

// Create calendar event
export async function createEvent(userId, title, startTime, endTime, env) {
  const id = crypto.randomUUID();
  await env.DB.prepare(`
    INSERT INTO events (id, user_id, title, start_time, end_time, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).bind(id, userId, title, startTime, endTime, new Date().toISOString()).run();

  return { id, title, start_time: startTime, end_time: endTime };
}

// Get today's events
export async function getTodaysEvents(userId, env) {
  const today = new Date().toISOString().split('T')[0];
  return await env.DB.prepare(`
    SELECT * FROM events
    WHERE user_id = ? AND date(start_time) = ?
    ORDER BY start_time
  `).bind(userId, today).all();
}
```

### 3. Claude Code Connector (`claude.js`)

```javascript
// Route admin messages to Claude Code
export async function routeToClaudeCode(userId, message, channel, env) {
  try {
    // Connect to Claude Code WebSocket (simplified)
    const response = await fetch('http://localhost:8080/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        user_id: userId,
        channel,
        context: 'boss-ai-routing'
      })
    });

    const data = await response.json();
    return data.response || "Claude Code is not available right now.";
  } catch (error) {
    console.error('Claude Code error:', error);
    return "I'm having trouble connecting to Claude Code. Please try again.";
  }
}

// Simple session management (in-memory for now)
const sessions = new Map();

export function createSession(userId) {
  const sessionId = crypto.randomUUID();
  sessions.set(sessionId, { userId, created: Date.now() });
  return sessionId;
}

export function getSession(sessionId) {
  return sessions.get(sessionId);
}
```

### 4. Rust CLI (Optional, `main.rs`)

```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Send a message to Boss
    Message { text: String },
    /// View today's calendar
    Calendar,
    /// List reminders
    Reminders,
    /// Start voice bridge
    Voice,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Message { text } => {
            let response = send_message(&text).await?;
            println!("{}", response);
        },
        Commands::Calendar => {
            let events = get_calendar().await?;
            for event in events {
                println!("{}: {}", event.start_time, event.title);
            }
        },
        Commands::Reminders => {
            let reminders = get_reminders().await?;
            for reminder in reminders {
                println!("{}: {}", reminder.due_time, reminder.text);
            }
        },
        Commands::Voice => {
            start_voice_bridge().await?;
        },
    }

    Ok(())
}

async fn send_message(text: &str) -> Result<String, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:8787/api/message")
        .json(&serde_json::json!({
            "channel": "cli",
            "from": "admin",
            "content": text
        }))
        .send()
        .await?;

    let data: serde_json::Value = response.json().await?;
    Ok(data["message"].as_str().unwrap_or("No response").to_string())
}
```

## API Endpoints (3 Simple Routes)

```javascript
// packages/server/src/index.js

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Webhook endpoints
    if (url.pathname === '/sms' && request.method === 'POST') {
      const body = await request.formData();
      return handleSMS(body, env);
    }

    if (url.pathname === '/email' && request.method === 'POST') {
      const body = await request.json();
      return handleEmail(body, env);
    }

    // API endpoint for CLI/direct usage
    if (url.pathname === '/api/message' && request.method === 'POST') {
      const body = await request.json();
      return handleAPI(body, env);
    }

    return new Response('Not found', { status: 404 });
  }
};

async function handleSMS(formData, env) {
  const from = formData.get('From');
  const body = formData.get('Body');

  const result = await handleMessage('sms', from, body, env);

  return new Response(`<?xml version="1.0" encoding="UTF-8"?>
    <Response>
      <Message>${result.message}</Message>
    </Response>`, {
    headers: { 'Content-Type': 'application/xml' }
  });
}

async function handleEmail(body, env) {
  const result = await handleMessage('email', body.from, body.text, env);

  // Send email response via SendGrid
  await sendEmail(body.from, 'Re: ' + body.subject, result.message, env);

  return new Response('OK');
}

async function handleAPI(body, env) {
  const result = await handleMessage(body.channel, body.from, body.content, env);
  return Response.json(result);
}
```

## Key Design Principles

### 1. **Single Responsibility**
- Each file has one clear purpose
- Functions do one thing well
- Easy to test in isolation

### 2. **Minimal Dependencies**
- Server: Standard Node.js + Cloudflare Workers
- Client: Basic Rust with minimal crates
- No complex frameworks or libraries

### 3. **Simple Data Flow**
```
Message In → Route → Process → Respond → Message Out
```

### 4. **Easy to Extend**
- Add new commands by extending `handleCommand()`
- Add new channels by adding webhook handlers
- Add new services by creating new files

### 5. **Testable Functions**
```javascript
// Every function is pure and testable
test('parseDateTime handles tomorrow', () => {
  expect(parseDateTime('tomorrow 2pm')).toMatch(/T14:00:00/);
});

test('handleCommand recognizes schedule', () => {
  expect(handleCommand('schedule meeting')).toContain('scheduled');
});
```

## Features (Minimal MVP)

### ✅ Core Features
- SMS/Email message routing
- Admin messages → Claude Code
- Basic calendar commands
- Simple reminders
- CLI interface

### 🚫 What We're NOT Building (Initially)
- Complex recurring events
- Multi-agent coordination
- Advanced Git integration
- Complex project management
- Advanced monitoring

### 🔄 Easy Extensions (Later)
- Add voice by extending message router
- Add recurring events by extending calendar
- Add projects by adding new table + service
- Add agents by extending Claude connector

## Development Workflow

### 1. **Setup (5 minutes)**
```bash
cd packages/server
npm install
wrangler dev

cd ../core
cargo run -- message "Hello Boss"
```

### 2. **Test (Simple)**
```bash
npm test                    # Test all functions
cargo test                  # Test Rust client
./test-sms.sh              # Integration test
```

### 3. **Deploy (1 command)**
```bash
wrangler deploy            # Deploy server
cargo build --release     # Build client
```

## Benefits of Simple Design

1. **Easy to Understand** - New developers can read the entire codebase in 1 hour
2. **Easy to Debug** - Clear data flow, minimal abstraction
3. **Easy to Test** - Pure functions, clear interfaces
4. **Easy to Extend** - Add features by extending existing patterns
5. **Reliable** - Fewer moving parts = fewer failure modes
6. **Fast** - Minimal overhead, direct function calls

This design gives us **80% of the functionality with 20% of the complexity**. We can always add sophisticated features later, but we start with a solid, simple foundation that actually works.

**Total Implementation Time: ~2-3 days instead of 2-3 weeks**