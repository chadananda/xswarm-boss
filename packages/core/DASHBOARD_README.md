# xSwarm Boss Dashboard

Real-time TUI (Terminal User Interface) dashboard for monitoring xSwarm Boss activity across all communication channels.

## Features

### Real-time Activity Feed
- SMS messages (received/sent) with sender/recipient and preview
- Email messages (received/sent) with sender/recipient and subject
- Voice calls (incoming/outgoing) with caller information
- Live WebSocket events from supervisor (user speech, AI responses)
- System events and errors

### Statistics Section
- Daily message counts (SMS received/sent, Emails received/sent)
- Voice call counts and duration
- Usage limits (voice minutes remaining, SMS messages remaining)
- Updates automatically based on activity

### System Status
- **Voice Bridge**: Status and port (9998)
- **Supervisor**: WebSocket connection status and port (9999)
- **Server**: Connection status and health
- **User Identity**: Current user information from server API

### Layout

```
╔════════════════════════════════════════════════════════════════╗
║ xSwarm Boss Dashboard | User: Chad Jones | Server: Online     ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║ Recent Activity                    │ Statistics               ║
║ ───────────────────                │ ──────────               ║
║ 15:32 📧 Email from john@...       │ Today:                   ║
║ 15:31 📱 SMS from +1234567890      │ • 12 SMS received        ║
║ 15:29 📞 Voice call from +098...   │ • 8 SMS sent             ║
║ 15:28 💬 User said: How are you?   │ • 3 Emails received      ║
║ 15:27 🔊 AI spoke: I'm great!      │ • 2 Emails sent          ║
║                                    │ • 3 Voice calls          ║
║                                    │                          ║
║                                    │ Limits:                  ║
║                                    │ • Voice mins left: 95    ║
║                                    │ • SMS left: 88           ║
║                                    │                          ║
║                                    │ System Status            ║
║                                    │ ──────────               ║
║                                    │ Voice Bridge:            ║
║                                    │ • Status: Online         ║
║                                    │ • Port: 9998             ║
║                                    │                          ║
║                                    │ Supervisor:              ║
║                                    │ • Status: Online         ║
║                                    │ • Port: 9999             ║
╠════════════════════════════════════════════════════════════════╣
║ [Q]uit | [R]efresh | [C]lear Activity | [H]elp                ║
╚════════════════════════════════════════════════════════════════╝
```

## Usage

### Starting the Dashboard

```bash
# Start the dashboard
cargo run --bin xswarm -- dashboard

# Or if xswarm is installed
xswarm dashboard
```

### Keyboard Controls

- **Q** or **Esc**: Quit the dashboard
- **R**: Force refresh server data and user identity
- **C**: Clear activity feed
- **H**: Show help (future)

## Configuration

The dashboard uses configuration from `config.toml`:

```toml
[server]
host = "localhost"
port = 8787
api_base = "/api"
use_https = false
```

### Environment Variables

- `XSWARM_AUTH_TOKEN`: Authentication token for server API
- `SUPERVISOR_TOKEN`: Authentication token for supervisor WebSocket (default: "dev-token-12345")

## Architecture

### Data Sources

1. **Supervisor WebSocket** (`ws://127.0.0.1:9999`)
   - Real-time events from voice bridge
   - User speech transcriptions
   - AI suggestions and responses
   - SMS/Email webhook events

2. **Server HTTP API** (`http://localhost:8787/api`)
   - User identity and configuration
   - Health checks
   - Authentication validation

3. **Voice Bridge Status** (Port 9998)
   - MOSHI model status
   - Active call information

### Event Types

The dashboard displays these activity event types:

- **📱 SMS Received**: Incoming text message
- **📤 SMS Sent**: Outgoing text message
- **📧 Email Received**: Incoming email
- **📨 Email Sent**: Outgoing email
- **📞 Voice Call Incoming**: Inbound phone call
- **📞 Voice Call Outgoing**: Outbound phone call
- **🎤 User Speech**: User spoke (with duration)
- **💬 User Transcription**: What the user said (transcribed by MOSHI)
- **💡 AI Suggestion**: AI context injected into conversation
- **🔊 AI Spoke**: AI response synthesized to speech
- **ℹ️ System Event**: Dashboard/system status updates
- **❌ Error**: Error messages and failures

### Background Tasks

The dashboard runs two background tasks:

1. **WebSocket Listener**: Connects to supervisor and streams real-time events
2. **Health Checker**: Polls server health and fetches user identity every 5 seconds

## Prerequisites

### 1. Start the Voice Bridge and Supervisor

Before running the dashboard, start the voice bridge with supervisor:

```bash
cargo run --bin xswarm -- voice-bridge --host 127.0.0.1 --port 9998 --supervisor-port 9999
```

This starts both:
- Voice bridge WebSocket on port 9998
- Supervisor WebSocket on port 9999

### 2. Start the Node.js Server (Optional)

For server health monitoring and user identity:

```bash
cd packages/server
pnpm dev
```

The server runs on `http://localhost:8787` by default.

## Troubleshooting

### "Supervisor: Offline"

The supervisor WebSocket is not running. Start the voice bridge:

```bash
cargo run --bin xswarm -- voice-bridge
```

### "Server: Offline"

The Node.js server is not running. Start it:

```bash
cd packages/server
pnpm dev
```

### "No activity showing"

1. Make sure supervisor is running and connected
2. Check that webhooks are configured to forward events
3. Send a test SMS or email to trigger activity

### Terminal rendering issues

The dashboard uses `ratatui` for TUI rendering. Make sure:
- Terminal supports ANSI colors
- Terminal size is at least 80x24 characters
- No other process is using raw terminal mode

## Development

### Adding New Event Types

1. Add variant to `ActivityEvent` enum in `dashboard.rs`
2. Implement `to_list_item()` formatting for the event
3. Add conversion in `convert_supervisor_event()` if from supervisor
4. Update statistics in `add_event()` if needed

### Customizing Layout

The layout is defined in `render_ui()`:
- Header: 3 lines
- Content: Split 65% activity feed, 35% stats/status
- Footer: 3 lines

Modify constraints in `Layout::default()` to adjust proportions.

### Adding New Keyboard Commands

Add handlers in `run_ui_loop()`:

```rust
KeyCode::Char('n') | KeyCode::Char('N') => {
    // Your command here
}
```

## Future Enhancements

- [ ] Scrollable activity feed (arrow keys)
- [ ] Filtering by event type
- [ ] Export activity to file
- [ ] Interactive help screen
- [ ] Voice bridge controls (start/stop/restart)
- [ ] Real-time charts and graphs
- [ ] Multi-user support (view other users' activity)
- [ ] Notification alerts for specific events
