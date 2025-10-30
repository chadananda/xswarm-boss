# Claude Code Integration - Quick Start Guide

## Overview

This feature enables you (as Admin) to communicate with Claude Code through Boss using SMS, Email, or Voice. Your messages are automatically routed to Claude Code for processing, and responses come back through the same channel.

## Quick Start

### 1. Set Up Environment

```bash
# Required: Server authentication
export XSWARM_AUTH_TOKEN="your-server-token"

# Optional: Claude Code authentication
export CLAUDE_CODE_AUTH_TOKEN="your-token-here"

# Optional: Supervisor authentication
export SUPERVISOR_TOKEN="dev-token-12345"
```

### 2. Start Boss with Claude Code Integration

```bash
cargo run --bin xswarm -- voice-bridge \
  --enable-claude-code \
  --claude-code-url ws://localhost:8080
```

You should see:
```
🤖 Claude Code integration enabled
   Admin messages will be routed to Claude Code at: ws://localhost:8080
🎤 MOSHI Voice Bridge is running!

📞 Voice WebSocket: ws://127.0.0.1:9998
🔧 Supervisor WebSocket: ws://127.0.0.1:9999

Press Ctrl+C to stop
```

### 3. Use It!

Now you can:

**Send SMS:**
- Text Boss phone number from your Admin phone
- Message is routed to Claude Code
- Response comes back via SMS

**Send Email:**
- Email Boss email address from your Admin email
- Email is routed to Claude Code with subject
- Response comes back via email with "Re:" subject

**Call (Voice):**
- Call Boss phone number from your Admin phone
- Speak your message (transcribed by MOSHI)
- Transcription routed to Claude Code
- Response synthesized to speech and played back

## Commands

### Check Active Sessions

```bash
# View all active Claude Code sessions
cargo run --bin xswarm -- claude status

# View specific session
cargo run --bin xswarm -- claude status --session-id <session-id>
```

### Monitor Costs

```bash
# View total costs across all users
cargo run --bin xswarm -- claude cost

# View costs for your user
cargo run --bin xswarm -- claude cost --user-id admin
```

### Connect to Existing Session

```bash
cargo run --bin xswarm -- claude connect --session-id <session-id>
```

## How It Detects Admin

The system identifies you as Admin by:

1. **Server Identity:** Fetches your user data from the server
2. **Permission Check:** Verifies you have `can_provision_numbers` permission
3. **Contact Match:** Confirms your phone/email matches Admin configuration

**Only Admin messages are routed to Claude Code.** Regular users' messages are acknowledged but not forwarded.

## Message Context

Each message includes metadata so Claude Code knows where it came from:

**SMS:**
```json
{
  "channel": "sms",
  "from": "+15551234567",
  "to": "+18005551001"
}
```

**Email:**
```json
{
  "channel": "email",
  "from": "admin@example.com",
  "to": "boss@xswarm.ai",
  "subject": "Project Discussion"
}
```

**Voice:**
```json
{
  "channel": "voice",
  "user_id": "admin"
}
```

## Session Management

**Automatic Creation:**
- First message creates a new session
- Subsequent messages reuse the active session
- Sessions automatically clean up after 5 minutes of inactivity

**Session Limits:**
- Max 10 concurrent sessions per user
- Each session tracks costs independently
- Sessions can be manually disconnected

## What Gets Tracked

Every interaction tracks:
- Message content
- Channel used
- Timestamp
- Session ID
- Cost (USD)
- Response time

View this data with `cargo run --bin xswarm -- claude status`

## Debugging

### Enable Verbose Logging

```bash
RUST_LOG=debug cargo run --bin xswarm -- voice-bridge --enable-claude-code
```

### Common Issues

**"No response from Claude Code"**
- Check that Claude Code WebSocket server is running on the specified URL
- Verify network connectivity
- Check firewall rules

**"Admin not detected"**
- Verify server client connection (`XSWARM_AUTH_TOKEN` is set)
- Check that your phone/email matches Admin configuration
- Confirm server is returning correct user identity

**"Session creation fails"**
- Check if max_sessions limit (10) is reached
- View active sessions: `cargo run --bin xswarm -- claude status`
- Disconnect old sessions if needed

**"WebSocket connection fails"**
- Verify Claude Code WebSocket URL is correct
- Check that Claude Code is running and accepting connections
- Test manually: `wscat -c ws://localhost:8080`

## Example Conversations

### SMS Conversation

**You:** (Text to Boss) "What's the status of the xswarm project?"

**Boss:** (Response via SMS) "The xswarm project is progressing well. Current status:
- Voice bridge: ✅ Implemented
- Claude Code routing: ✅ Just completed
- Testing: 🔄 In progress
- Cost tracking: ✅ Implemented

Next steps: Integration testing and documentation review."

### Email Conversation

**You:** (Email to Boss)
```
Subject: Need help with Rust error

I'm getting a compilation error in supervisor.rs. Can you help?
```

**Boss:** (Response via Email)
```
Subject: Re: Need help with Rust error

I'd be happy to help! To diagnose the issue, I need:

1. The exact error message from cargo
2. The code around line number mentioned in the error
3. Any recent changes you made

Could you share these details?
```

### Voice Conversation

**You:** (Call Boss, speak) "Hey Boss, can you explain how the message routing works?"

**Boss:** (Speaks back) "Sure! The message routing system works in three steps:

First, when you send a message through any channel, it arrives at the supervisor.

Second, the supervisor checks if you're the admin user by verifying your identity with the server.

Third, if you're admin, your message is forwarded to Claude Code, which processes it and sends back a response through the same channel you used.

The system supports SMS, email, and voice channels, and all conversations are tracked with cost information."

## Tips for Best Results

1. **Be Specific:** Claude Code responds best to specific questions and directives
2. **Include Context:** Mention project names, file paths, or specific features
3. **Use Natural Language:** No need for special commands - just talk normally
4. **Check Costs:** Monitor usage with `cargo run --bin xswarm -- claude cost`
5. **Session Management:** Long conversations? They stay in the same session

## Advanced Usage

### Custom Claude Code URL

```bash
cargo run --bin xswarm -- voice-bridge \
  --enable-claude-code \
  --claude-code-url ws://remote-server:8080
```

### Custom Ports

```bash
cargo run --bin xswarm -- voice-bridge \
  --host 0.0.0.0 \
  --port 9998 \
  --supervisor-port 9999 \
  --enable-claude-code
```

### Running in Background

```bash
# Start in background
nohup cargo run --bin xswarm -- voice-bridge --enable-claude-code &

# View logs
tail -f nohup.out
```

## Security Notes

✅ **Only Admin can access Claude Code** - Permission checks prevent unauthorized access
✅ **Authenticated connections** - Multiple authentication layers
✅ **Logged activity** - All routing decisions are logged
✅ **Non-admin isolation** - Regular users don't get routed to Claude Code

## Next Steps

1. **Start the system** with Claude Code integration
2. **Send a test message** via SMS, Email, or Voice
3. **Check session status** to verify it's working
4. **Monitor costs** to track usage
5. **Explore the code** in `/packages/core/src/supervisor.rs`

## Need Help?

- **Documentation:** See `/planning/CLAUDE_CODE_ROUTING.md` for detailed architecture
- **Implementation:** See `docs/IMPLEMENTATION_SUMMARY.md` for technical details
- **Code:** Check `/packages/core/src/supervisor.rs` for routing logic
- **Logs:** Run with `RUST_LOG=debug` for verbose output

Enjoy seamless communication with Claude Code through Boss! 🤖📱📧📞
