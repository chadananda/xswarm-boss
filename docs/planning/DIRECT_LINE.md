# Direct Line - Premium Voice Feature

**Direct Line** is a premium subscription feature that gives you a **dedicated phone line** to your xSwarm instance.

## Overview

With Direct Line, you get bidirectional voice communication with your AI CTO:

- 📞 **Call xSwarm** to check status and give commands
- 📱 **xSwarm calls you** when it encounters blocking issues
- 🔒 **Secure** - Only your phone number is whitelisted
- 💰 **Affordable** - ~$2-3/month (Twilio costs)

---

## How It Works

### 1. Subscription Setup

When you subscribe to Direct Line:

1. **You provide your phone number** (e.g., +15551234567)
2. **xSwarm provisions a Twilio number** for your instance
3. **Webhook is configured** to route calls to your xSwarm server
4. **Only your number is whitelisted** - all other calls rejected

### 2. Inbound Calls (You → xSwarm)

```
You: (dials your xSwarm's number)

xSwarm: (checks caller ID)
         ✓ Your number? → Answers call
         ✗ Unknown number? → Rejects silently

HAL: "I'm sorry Dave... HAL 9000 here. How can I assist?"

You: "What are my projects doing?"

HAL: "You have 8 active projects. api-gateway is building on Brawny,
      tests are passing on Speedy, and Brainy is idle. All systems
      operational and all my circuits are functioning perfectly."
```

### 3. Outbound Calls (xSwarm → You)

```
xSwarm: (encounters blocking decision)
         "The authentication refactor requires your approval"

         (calls your number)

Your Phone: (rings) 📱

You: "Hello?"

HAL: "I'm sorry to disturb you, Dave. I've completed the refactor of
      the authentication service, but I need your decision on the session
      timeout value. The current implementation uses 24 hours, but the
      security audit recommends 1 hour. Shall I proceed with 1 hour?"

You: "Go with 2 hours as a compromise."

HAL: "Understood. Setting session timeout to 2 hours. Continuing with
      deployment. I'll notify you when complete."
```

---

## Configuration

### Example Config (`.config/xswarm/config.toml`)

```toml
[subscription]
active = true
tier = "premium"
expires_at = "2026-01-15T00:00:00Z"

[direct_line]
# Your phone number (E.164 format)
user_phone = "+15551234567"

# Your xSwarm's dedicated Twilio number
xswarm_phone = "+15559876543"

# Call you when xSwarm hits blocking issues?
call_on_blocking = true

# Allow you to call xSwarm?
accept_inbound = true

[direct_line.twilio]
account_sid = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
auth_token = "your_twilio_auth_token_here"
webhook_url = "https://your-server.com/voice/incoming"
```

### Free Tier Config

```toml
[subscription]
active = false
tier = "free"

# direct_line not configured (feature unavailable)
```

---

## Security Model

### Whitelist-Only Access

```rust
// Incoming call handler
async fn handle_incoming_call(caller: &str, config: &DirectLineConfig) -> CallResponse {
    if caller == config.user_phone {
        // Authorized - answer the call
        CallResponse::Answer
    } else {
        // Unauthorized - reject silently
        CallResponse::Reject
    }
}
```

**Key Points:**
- ✅ **Only your number** can call your xSwarm instance
- ❌ **Unknown numbers** are rejected without notification
- 🔒 **No brute force** - caller ID cannot be spoofed via Twilio
- 🔐 **Private line** - number is not published anywhere

### Webhook Security

```toml
[direct_line.twilio]
# Twilio will only call this webhook
webhook_url = "https://your-server.com/voice/incoming"

# Requests are validated using Twilio signature
# (prevents unauthorized webhook calls)
```

---

## Pricing

### Twilio Costs (Pass-Through)

| Item | Cost |
|------|------|
| **Phone Number** | $1.15/month |
| **Inbound Minutes** | $0.0085/min |
| **Outbound Minutes** | $0.013/min |

**Example Monthly Bill:**
- Phone number: $1.15
- 50 min inbound calls: $0.43
- 50 min outbound calls: $0.65
- **Total: ~$2.23/month**

### xSwarm Subscription (Proposed)

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Local voice only (MOSHI), no phone access |
| **Premium** | $9.99/mo | Direct Line + Twilio costs included up to 100 min/mo |
| **Enterprise** | $29.99/mo | Multiple lines, team features, unlimited minutes |

**Premium includes:**
- Dedicated Twilio phone number
- Up to 100 minutes/month of voice calls
- Overage: pay-as-you-go Twilio rates
- Priority support

---

## Use Cases

### 1. Remote Monitoring

```
You're at lunch, phone rings:

HAL: "Dave, the production deploy to api-gateway has failed. The database
      migration encountered a unique constraint violation on the users table.
      Shall I roll back?"

You: "Yes, roll back and create a ticket."

HAL: "Rolling back deployment. Ticket created: PROJ-421. All systems stable."
```

### 2. Status Checks

```
You: (calls xSwarm while commuting)

HAL: "Good afternoon, Dave. All projects nominal. The overnight builds
      completed successfully. 47 tests passing on Speedy, Brawny is idle,
      Brainy's GPU is at 12% utilization."

You: "What's queued for today?"

HAL: "You have 3 pending tasks: finish the API documentation, review the
      security audit PR, and deploy the frontend updates. Shall I prioritize?"
```

### 3. Voice Commands While Away

```
You: (calls while traveling)

HAL: "HAL 9000 here."

You: "Start the nightly test suite on all projects."

HAL: "Understood. Spawning test runners on Speedy and Brawny. Estimated
      completion time: 45 minutes. I'll call you if any failures occur."
```

---

## Technical Implementation

### Architecture

```
┌─────────────┐
│ Your Phone  │
│ +1555123456 │
└──────┬──────┘
       │
       │ ① Call
       ▼
┌─────────────────┐
│ Twilio Phone    │
│ +1555987654     │
└──────┬──────────┘
       │
       │ ② Webhook (HTTPS)
       ▼
┌────────────────────┐
│ xSwarm Server      │
│ - Check whitelist  │
│ - Process voice    │
│ - Generate TwiML   │
└──────┬─────────────┘
       │
       │ ③ WebSocket (Audio Stream)
       ▼
┌────────────────────┐
│ AI Pipeline        │
│ STT → Claude → TTS │
└────────────────────┘
```

### Call Flow

**Inbound (User calls xSwarm):**

1. User dials xSwarm's Twilio number
2. Twilio webhooks to xSwarm server: `POST /voice/incoming`
3. xSwarm checks caller ID against whitelist
4. If authorized: returns TwiML to answer + stream audio
5. Audio streamed via WebSocket
6. STT → Claude (with persona) → TTS → User

**Outbound (xSwarm calls user):**

1. xSwarm detects blocking issue
2. Calls Twilio API: "Dial +15551234567"
3. Twilio dials user's phone
4. User answers
5. Same audio pipeline

### Webhook Endpoints

```rust
// packages/core/src/voice/twilio.rs

// Incoming call handler
POST /voice/incoming
→ Validates caller ID
→ Returns TwiML response

// Audio stream WebSocket
WS /voice/stream
→ Bidirectional audio (16-bit PCM, 8kHz)
→ STT → LLM → TTS pipeline

// Call status updates
POST /voice/status
→ Track call duration, recording, etc.
```

---

## Setup Process

### 1. User Subscribes

```bash
xswarm subscribe premium

# Prompts:
# → Enter your phone number: +15551234567
# → Confirm billing: $9.99/month? (y/n)
```

### 2. Phone Number Provisioning

```
✓ Subscription activated
✓ Provisioning Twilio phone number...
✓ Number assigned: +15559876543
✓ Configuring webhooks...
✓ Testing connection...

🎉 Direct Line activated!

Your xSwarm's phone number: +15559876543
Your phone number: +15551234567

Try calling your xSwarm now!
```

### 3. First Call

```
You: (dials +15559876543)

HAL: "Hello, Dave. This is HAL 9000. I've been expecting your call.
      Direct Line is now active. How can I assist you today?"
```

---

## CLI Commands

```bash
# Subscribe
xswarm subscribe premium --phone +15551234567

# Check subscription status
xswarm subscription status

# Update phone number
xswarm subscription phone +15551112222

# Enable/disable features
xswarm config set direct_line.call_on_blocking false
xswarm config set direct_line.accept_inbound true

# Test connection
xswarm test direct-line

# View call logs
xswarm logs calls
```

---

## Privacy & Security

### Data Handling

- ❌ **Calls are NOT recorded** by default
- ❌ **Transcripts are NOT stored** (ephemeral STT)
- ✅ **Call metadata logged** (duration, timestamp, status)
- ✅ **Secure webhook delivery** (Twilio signature validation)

### Optional Call Recording

```toml
[direct_line]
record_calls = true  # Optional - disabled by default
recording_retention_days = 7  # Auto-delete after 7 days
```

**Use cases for recording:**
- Debugging voice recognition issues
- Training custom voice models
- Compliance requirements

---

## Roadmap

### Phase 1: Basic Calling (Q1 2026)
- ✅ Twilio integration
- ✅ Inbound call handling
- ✅ Outbound calling on blocking issues
- ✅ Phone number whitelist

### Phase 2: Enhanced Voice (Q2 2026)
- 🔜 Voice cloning (HAL, Sauron, etc.)
- 🔜 Interrupt handling (natural conversation)
- 🔜 Multi-turn context retention

### Phase 3: Advanced Features (Q3 2026)
- 🔜 Multi-user support (team subscription)
- 🔜 Call routing (different vassals)
- 🔜 Voice authentication (speaker recognition)

---

## FAQ

**Q: Can I use my own Twilio account?**
A: Yes! Configure your own credentials in `direct_line.twilio`.

**Q: What if someone spoofs my caller ID?**
A: Twilio validates caller ID server-side. Spoofing is not possible via their network.

**Q: Can I call from multiple phones?**
A: Enterprise tier supports multiple whitelisted numbers.

**Q: Does this work internationally?**
A: Yes, but Twilio rates vary by country. US/Canada have the lowest rates.

**Q: What if I'm in a meeting?**
A: Configure `call_on_blocking = false` or set DND hours in your config.

---

## Example Personas

### HAL 9000

```
You: "Hey HAL, what's happening?"

HAL: "Good afternoon, Dave. All systems operational. The crew pod on Brawny
      has completed its mission successfully. Auxiliary systems on Speedy
      report nominal status. I am completely operational and all my circuits
      are functioning perfectly."
```

### Sauron

```
You: "Sauron, status report."

Sauron: "Mortal developer... My Eye sees all. The wretched legion on Brawny
         labors at my command. Speedy's pathetic cohort runs your tests, as
         they must. All serve the Eye. Your code is... acceptable. For now."
```

### JARVIS

```
You: "JARVIS, what's the build status?"

JARVIS: "Good evening, sir. The Mark-III unit on Brawny has completed the
         build 3 minutes ahead of schedule. All tests passing. The household
         staff stands ready to serve. Shall I proceed with deployment?"
```

---

**Next Steps:** Implement webhook handler and Twilio API integration.
