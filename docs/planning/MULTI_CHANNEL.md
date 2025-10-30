# Multi-Channel Communication System

xSwarm's intelligent communication system allows your AI CTO to reach you through **email, phone, or SMS** based on the urgency and context of the situation.

---

## Overview

Traditional AI assistants are stuck inside your terminal or browser. xSwarm breaks free with a complete communication infrastructure that gives your AI CTO three ways to reach you:

- 📧 **Email** - Low-urgency updates, reports, summaries
- 📱 **Phone** - Critical issues requiring immediate attention
- 💬 **SMS** - Medium-urgency notifications, status updates

**Key Feature:** The AI automatically selects the appropriate channel based on urgency, ensuring you're never interrupted unnecessarily but always alerted when it matters.

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────┐
│                  xSwarm AI CTO                      │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │      AI Channel Router                      │   │
│  │  (Urgency-Based Decision Engine)            │   │
│  └─────────────────────────────────────────────┘   │
│         │                │               │          │
│         │                │               │          │
│    [Critical]       [Medium]         [Low]          │
│         │                │               │          │
│         ▼                ▼               ▼          │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    │
│   │  Phone   │    │   SMS    │    │  Email   │    │
│   │  Twilio  │    │  Twilio  │    │ SendGrid │    │
│   └──────────┘    └──────────┘    └──────────┘    │
└─────────────────────────────────────────────────────┘
                    │
                    │ Internet
                    │
          ┌─────────┴─────────────┐
          │                       │
          ▼                       ▼
    ┌──────────┐            ┌──────────┐
    │Your Phone│            │Your Email│
    │+1555123  │            │you@ex.com│
    └──────────┘            └──────────┘
```

---

## Channel Selection Logic

The AI channel router uses contextual decision-making to select the best communication method:

### Decision Tree

```python
def select_channel(urgency: str, context: dict) -> Channel:
    """
    AI-powered channel selection based on urgency and context
    """

    if urgency == "CRITICAL":
        # Production down, deployment failed, security issue
        return Channel.PHONE

    elif urgency == "HIGH":
        # Build failed, tests breaking, dependency conflict
        if user.is_busy() or context.requires_approval():
            return Channel.SMS  # Quick notification
        else:
            return Channel.PHONE  # Can discuss immediately

    elif urgency == "MEDIUM":
        # PR ready for review, task completed, minor issue
        if context.requires_quick_response():
            return Channel.SMS
        else:
            return Channel.EMAIL

    elif urgency == "LOW":
        # Daily summary, documentation updated, metrics report
        return Channel.EMAIL

    else:
        # Default to least intrusive
        return Channel.EMAIL
```

### Urgency Classification

| Urgency | Examples | Typical Channel |
|---------|----------|----------------|
| **CRITICAL** | Production outage, security breach, data loss | 📱 Phone Call |
| **HIGH** | Deployment failed, CI/CD broken, API down | 💬 SMS or 📱 Phone |
| **MEDIUM** | Build failed, tests failing, PR needs review | 💬 SMS or 📧 Email |
| **LOW** | Task completed, daily report, metrics update | 📧 Email |

---

## Channel Details

### 📧 Email (Free Tier)

**Provider:** SendGrid
**Cost:** Free (100 emails/day)
**Best For:** Low-urgency updates, reports, summaries

**Features:**
- Rich HTML formatting
- Code snippets with syntax highlighting
- Attachments (logs, screenshots)
- Links to dashboards and PRs
- Thread-based conversations

**Example Email:**

```
From: HAL 9000 <hal@xswarm.ai>
To: you@example.com
Subject: Daily Development Summary - 8 Tasks Completed

Good evening, Dave.

I've completed your daily development tasks. Here's the summary:

✓ Refactored authentication service (api-gateway)
✓ Updated documentation (docs site deployed)
✓ Ran test suite: 247/247 passing
✓ Created PR #142: "Add email notifications"
✓ Fixed 3 security vulnerabilities (dependencies updated)
✓ Generated code coverage report (87% coverage)
✓ Optimized database queries (40% faster)
✓ Deployed to staging environment

All systems operational.

View full report: https://dashboard.xswarm.ai/reports/2025-10-22

Best regards,
HAL 9000
```

---

### 💬 SMS (Premium Tier)

**Provider:** Twilio
**Cost:** ~$0.0075 per SMS
**Best For:** Medium-urgency notifications, quick status updates

**Features:**
- Instant delivery (< 5 seconds)
- 160-character limit (concise updates)
- Two-way communication
- Read receipts
- Links for more details

**Example SMS:**

```
From: +18005551234 (HAL 9000)

⚠️ Build failed on api-gateway (main branch)
Error: TypeScript compile error in auth.ts:42
Fix required before deployment.
Details: https://ci.xswarm.ai/build/1234
```

**User Reply:**
```
To: +18005551234

Roll back and create ticket
```

**AI Response:**
```
From: +18005551234

✓ Rolled back to commit abc123
✓ Created ticket PROJ-421
All systems stable.
```

---

### 📱 Phone (Premium Tier)

**Provider:** Twilio Voice
**Cost:** ~$0.013 per minute
**Best For:** Critical issues requiring immediate attention

**Features:**
- Voice-to-voice conversation
- Real-time decision making
- Interrupt handling
- Context-aware responses
- HAL 9000 voice persona

**Example Call:**

```
[Your phone rings]

You: "Hello?"

HAL: "I'm sorry to disturb you, Dave. This is HAL 9000. I have a critical
      issue requiring your immediate attention. The production deployment
      to api-gateway has failed due to a database migration error. The
      service is currently offline, affecting approximately 1,200 users.

      I have three options:

      Option 1: Roll back to the previous stable version. ETA 2 minutes.
      Option 2: Fix the migration and retry deployment. ETA 15 minutes.
      Option 3: Switch to backup database and investigate. ETA 5 minutes.

      What would you like me to do?"

You: "Roll back immediately, then investigate the migration issue."

HAL: "Understood. Initiating rollback now. I'll send you a full report
      via email once the service is restored. Estimated time: 90 seconds."

[2 minutes later - SMS notification]

✓ Rollback complete. Service restored.
All systems operational.
Full report sent to your email.
```

---

## Configuration

### Free Tier (Email Only)

```toml
# ~/.config/xswarm/config.toml

[subscription]
tier = "free"

[communication]
user_email = "you@example.com"
xswarm_email = "username@xswarm.ai"

[communication.channels]
email_enabled = true
phone_enabled = false
sms_enabled = false
```

### Premium Tier (Email + Phone + SMS)

```toml
[subscription]
tier = "premium"

[communication]
user_email = "you@example.com"
user_phone = "+15551234567"
xswarm_email = "username@xswarm.ai"
xswarm_phone = "+18005551234"  # Toll-free

[communication.channels]
email_enabled = true
phone_enabled = true
sms_enabled = true

# Channel preferences
accept_inbound_calls = true
accept_inbound_sms = true
accept_inbound_email = true
```

---

## Security Model

### Whitelist-Only Communication

All channels enforce strict whitelist security:

```rust
/// Validates incoming communication against whitelist
async fn validate_sender(
    channel: Channel,
    sender: &str,
    config: &CommunicationConfig
) -> Result<()> {
    match channel {
        Channel::Email => {
            if sender != config.user_email {
                return Err("Unauthorized email sender");
            }
        }
        Channel::Phone | Channel::SMS => {
            if sender != config.user_phone {
                return Err("Unauthorized phone number");
            }
        }
    }

    Ok(())
}
```

**Key Points:**
- ✅ **Only your email/phone** can communicate with your xSwarm instance
- ❌ **Unknown contacts** are rejected silently (no notification)
- 🔒 **No brute force** - sender validation happens server-side
- 🔐 **Private addresses** - xSwarm email/phone not published publicly

---

## Pricing Breakdown

### Free Tier

| Feature | Included | Cost |
|---------|----------|------|
| Email (SendGrid) | 100/day | $0 |
| **Total** | | **$0/month** |

### Premium Tier

| Feature | Included | Cost |
|---------|----------|------|
| Email | 100/day | $0 (included) |
| Toll-Free Phone Number | 1 number | $2/month |
| Inbound Calls | 100 min/month | $0.85 |
| Outbound Calls | 100 min/month | $1.30 |
| SMS (Send/Receive) | 100 messages | $0.75 |
| **Subtotal** | | **$4.90/month** |
| **xSwarm Premium** | | **$9.99/month** |

**Premium includes up to 100 minutes of voice + 100 SMS messages per month.**

Overage rates:
- Voice: $0.013/min
- SMS: $0.0075/message

---

## Multi-User Architecture

Each user gets isolated communication channels:

```
User 1:
- Email: alice@xswarm.ai → alice@example.com
- Phone: +18005551001 → +15551111111

User 2:
- Email: bob@xswarm.ai → bob@example.com
- Phone: +18005551002 → +15552222222
```

### Shared Infrastructure

- **Single SendGrid account** (domain: xswarm.ai)
- **Single Twilio account** (toll-free number pool)
- **Per-user isolation** (whitelist security)

### Email Routing

All emails to `*@xswarm.ai` arrive at a single webhook:

```rust
/// Routes incoming email to correct user instance
async fn route_email(to: &str) -> Result<UserId> {
    // Extract username from "username@xswarm.ai"
    let username = to.split('@').next()
        .ok_or("Invalid email format")?;

    // Look up user in database
    let user = database.find_user_by_email(to).await?;

    // Forward to user's xSwarm instance
    user.xswarm_instance.handle_email(...).await
}
```

---

## Use Cases

### 1. Critical Production Issue

```
Time: 2:30 AM

xSwarm detects:
- Production API response time > 5 seconds
- Error rate spiking to 15%
- Database connection pool exhausted

Decision: CRITICAL → Phone Call

[Your phone rings]

HAL: "I'm sorry to wake you, Dave, but we have a critical situation.
      The production API is experiencing severe performance degradation.
      Database connection pool is exhausted. I recommend immediate rollback
      to the previous version while I investigate. May I proceed?"

You: "Yes, roll back and page the on-call engineer."

HAL: "Understood. Initiating rollback and sending alert. I'll monitor
      the situation and send you a full incident report via email."
```

---

### 2. Build Failure (Medium Urgency)

```
Time: 3:00 PM (work hours)

xSwarm detects:
- CI/CD build failed on main branch
- TypeScript compilation error
- Blocking deployments

Decision: MEDIUM → SMS (during work hours)

[SMS arrives]

⚠️ Build failed: api-gateway (main)
Error: TS2345 in auth.ts:42
Type 'string' not assignable to 'User'
Fix needed before deployment.
View: https://ci.xswarm.ai/build/567
```

**User replies:**
```
Fix it and show me the diff
```

**AI responds:**
```
✓ Fixed type error
✓ Build passing
Diff: https://github.com/.../commit/abc123
Ready to deploy?
```

---

### 3. Daily Summary (Low Urgency)

```
Time: 6:00 PM (end of day)

xSwarm completes:
- All scheduled tasks
- Test suite runs
- Documentation updates
- Dependency updates

Decision: LOW → Email

[Email arrives]

From: HAL 9000 <hal@xswarm.ai>
Subject: Daily Summary - October 22, 2025

Good evening, Dave.

Today's accomplishments:

Projects (3 active):
✓ api-gateway: Deployed v2.4.1 to production
✓ frontend-app: Updated dependencies, 0 vulnerabilities
✓ docs-site: Published 4 new guides

Code Quality:
- Test coverage: 87% (+2%)
- 247 tests passing
- 0 linting errors
- Security: All clear

Performance:
- API response time: 145ms avg (↓ 12%)
- Database queries optimized
- Bundle size reduced by 23KB

Tomorrow's agenda:
1. Implement feature flag system
2. Refactor authentication service
3. Update CI/CD pipeline

All systems operational.

View dashboard: https://dashboard.xswarm.ai

Best regards,
HAL 9000
```

---

## CLI Commands

```bash
# Test communication channels
xswarm test email
xswarm test sms
xswarm test phone

# Configure communication preferences
xswarm config set communication.user_email "you@example.com"
xswarm config set communication.user_phone "+15551234567"

# Set channel preferences
xswarm config set communication.channels.accept_inbound_calls true
xswarm config set communication.channels.accept_inbound_sms true

# View communication history
xswarm logs email
xswarm logs sms
xswarm logs calls

# Upgrade to premium (phone + SMS)
xswarm subscribe premium
```

---

## Implementation Roadmap

### Phase 1: Email Foundation (Q1 2026) ✅
- ✅ SendGrid integration
- ✅ Domain verification (xswarm.ai)
- ✅ Inbound email webhook
- ✅ Whitelist security
- ✅ HTML email templates

### Phase 2: SMS Notifications (Q2 2026)
- 🔜 Twilio SMS integration
- 🔜 Two-way SMS conversations
- 🔜 SMS templates (alerts, confirmations)
- 🔜 Message threading

### Phase 3: Voice Calling (Q2 2026)
- 🔜 Twilio Voice integration
- 🔜 Inbound/outbound calling
- 🔜 Voice persona (HAL 9000)
- 🔜 Real-time conversation

### Phase 4: AI Channel Router (Q3 2026)
- 🔜 Urgency classification engine
- 🔜 Context-aware decision making
- 🔜 User preference learning
- 🔜 Multi-channel orchestration

### Phase 5: Advanced Features (Q3 2026)
- 🔜 Do Not Disturb mode
- 🔜 Scheduled quiet hours
- 🔜 Emergency override
- 🔜 Multi-user support (team features)

---

## FAQ

**Q: Can I disable certain channels?**
A: Yes, configure `communication.channels.*_enabled` to control each channel.

**Q: What happens if I don't answer a critical phone call?**
A: xSwarm will fall back to SMS immediately, then email with full details.

**Q: Can I set quiet hours?**
A: Yes, configure DND hours. Critical issues will still call during emergencies.

**Q: How does the AI decide what's "critical"?**
A: Production outages, security breaches, data loss, or user-impacting issues.

**Q: Can multiple people receive notifications?**
A: Enterprise tier supports team features with multiple recipients.

**Q: What if I'm traveling internationally?**
A: You can temporarily set email-only mode to avoid international calling charges.

---

## Related Documentation

- [DIRECT_LINE.md](./DIRECT_LINE.md) - Phone calling feature details
- [TWILIO_SETUP.md](./TWILIO_SETUP.md) - Twilio configuration guide
- [SENDGRID_SETUP.md](./SENDGRID_SETUP.md) - SendGrid configuration guide

---

**Next:** Implement the AI channel router and communication module.
