# End-to-End Testing Guide

This guide covers the comprehensive end-to-end test suite for xSwarm Boss. These tests validate **actual real-world usage** with **real API integrations**, not just mock data.

## Overview

The E2E test suite validates the complete user experience across all communication channels:

- **Email**: SendGrid integration with Claude AI responses
- **SMS**: Twilio SMS with conversational AI
- **Voice**: Twilio voice calls with MOSHI voice AI
- **Database**: Turso/LibSQL data persistence
- **Dashboard**: Real-time TUI monitoring
- **Multi-channel**: Cross-channel context continuity

## Test Philosophy

**Real APIs, Real Usage, Real Confidence**

Unlike traditional unit tests that use mocks, these tests:
- ✅ Use actual API keys from `.env`
- ✅ Make real API calls to external services
- ✅ Validate end-to-end user experience
- ✅ Test business logic and integration
- ✅ Verify data persistence in real database
- ✅ Monitor actual system performance

## Prerequisites

### Required Services

1. **Anthropic API** (Claude AI)
   - Required for AI-powered responses
   - Get key: https://console.anthropic.com/

2. **SendGrid API** (Email)
   - Required for email sending/receiving
   - Get key: https://sendgrid.com/

3. **Twilio API** (SMS + Voice)
   - Required for SMS and voice calls
   - Get credentials: https://console.twilio.com/

4. **Turso Database** (Optional for remote DB)
   - Required for production database testing
   - Get auth token: https://turso.tech/

### Configuration Files

1. **`.env`** - API keys and secrets
2. **`config.toml`** - Non-secret configuration
3. **Server running** - For webhook tests (optional)

## Installation

Ensure all dependencies are installed:

```bash
pnpm install
```

## Test Structure

### Master Test Suite

**File**: `scripts/test-end-to-end.js`

Orchestrates all test scenarios and provides comprehensive reporting.

```bash
# Run all E2E tests
npm run test:e2e

# Run specific test category
npm run test:e2e email
npm run test:e2e sms
npm run test:e2e voice
npm run test:e2e database
npm run test:e2e dashboard
npm run test:e2e multi     # Multi-channel
npm run test:e2e error     # Error handling
```

### Individual Test Modules

Each test can also run standalone for focused testing:

#### 1. Email Self-Test
**File**: `scripts/test-boss-email-self.js`

Tests complete email loop:
- Boss sends email to itself
- SendGrid delivers email
- Webhook receives inbound email
- Claude AI processes and responds
- Response email sent back
- Database records interaction

```bash
npm run test:email-self
```

**What it validates:**
- SendGrid API integration
- Email sending via API
- Email delivery (manual verification)
- Inbound email webhook (requires server)
- Claude AI response generation
- Email database persistence

#### 2. SMS Conversation Test
**File**: `scripts/test-sms-conversation.js`

Tests multi-turn SMS conversation:
- Simulates incoming SMS messages
- Verifies Claude AI intelligent responses
- Tests conversation continuity
- Validates SMS rate limiting
- Confirms Twilio API integration

```bash
npm run test:sms-conversation
```

**What it validates:**
- Twilio SMS API integration
- Multi-turn conversation flow
- Claude AI contextual responses
- SMS rate limiting (optional)
- Conversation context preservation

#### 3. Voice Conversation Test
**File**: `scripts/test-voice-conversation.js`

Tests voice call integration:
- Initiates Twilio voice call
- Connects to MOSHI via WebSocket
- Processes voice input
- Generates AI voice response
- Tests full-duplex conversation

```bash
npm run test:voice-conversation
```

**What it validates:**
- Twilio Voice API integration
- Voice call initiation
- MOSHI WebSocket connection
- Voice transcription simulation
- TwiML response generation
- Call status tracking

#### 4. Database Persistence Test
**File**: `scripts/test-database-persistence.js`

Tests data storage and retrieval:
- Creates test records
- Verifies data storage
- Tests data retrieval
- Validates conversation history
- Tests query performance
- Cleans up test data

```bash
npm run test:database-persistence
```

**What it validates:**
- LibSQL/Turso database connection
- Record creation and storage
- Data retrieval and querying
- Multi-channel data persistence
- Conversation history retrieval
- Query performance metrics

#### 5. Dashboard Live Updates Test
**File**: `scripts/test-dashboard-live.js`

Tests real-time monitoring:
- Starts TUI dashboard
- Generates test events
- Verifies dashboard updates
- Tests responsiveness
- Validates statistics

```bash
npm run test:dashboard-live
```

**What it validates:**
- TUI dashboard initialization
- Real-time event processing
- Dashboard responsiveness
- Event throughput metrics
- Statistics accuracy

## Test Scenarios

### Scenario 1: Email Self-Conversation

**Objective**: Validate complete email loop

1. Send test email from Boss to Boss
2. Email delivered via SendGrid
3. Webhook receives inbound email (requires server)
4. Claude AI processes email content
5. AI generates intelligent response
6. Response sent via SendGrid
7. Database records all interactions

**Success Criteria**:
- ✅ Email sent successfully (SendGrid)
- ✅ Email delivered to inbox (manual check)
- ✅ Webhook processed (if server running)
- ✅ AI response generated (Claude)
- ✅ Response email sent (SendGrid)
- ✅ Database contains records

### Scenario 2: SMS Conversation Flow

**Objective**: Validate multi-turn SMS conversation

1. User sends "status" via SMS
2. Boss responds with current status
3. User asks follow-up question
4. Boss provides contextual answer
5. Conversation continues naturally
6. Rate limiting enforced (optional)

**Success Criteria**:
- ✅ All SMS messages processed
- ✅ AI responses are contextual
- ✅ Conversation flow is natural
- ✅ Rate limiting works (if enabled)
- ✅ Database tracks conversation

### Scenario 3: Voice Call Integration

**Objective**: Validate voice conversation

1. Initiate voice call via Twilio
2. Connect call to MOSHI WebSocket
3. Process voice input (transcription)
4. Generate AI response (TTS)
5. Handle full-duplex conversation
6. Track call status events

**Success Criteria**:
- ✅ Call initiated successfully
- ✅ WebSocket connection established
- ✅ Voice transcription accurate
- ✅ AI response generated
- ✅ TwiML properly formatted
- ✅ Call status tracked

### Scenario 4: Multi-Channel Communication

**Objective**: Validate cross-channel context

1. User sends email with question
2. Follow up with SMS
3. Make voice call about same topic
4. Context preserved across channels
5. Responses show awareness of previous interactions

**Success Criteria**:
- ✅ All channels receive messages
- ✅ Context preserved across channels
- ✅ Responses reference previous messages
- ✅ User preferences respected
- ✅ Channel-specific formatting applied

### Scenario 5: Database Persistence

**Objective**: Validate data integrity

1. Create test records (email, SMS, voice)
2. Verify immediate storage
3. Retrieve and validate data
4. Test conversation history
5. Measure query performance
6. Clean up test data

**Success Criteria**:
- ✅ All records stored correctly
- ✅ Data retrieved matches original
- ✅ Conversation history complete
- ✅ Query performance acceptable
- ✅ Test data cleaned up

### Scenario 6: Dashboard Monitoring

**Objective**: Validate real-time updates

1. Start TUI dashboard
2. Generate test events
3. Verify dashboard shows events
4. Test under load (burst events)
5. Validate statistics accuracy
6. Clean shutdown

**Success Criteria**:
- ✅ Dashboard starts successfully
- ✅ Events appear in real-time
- ✅ Statistics update correctly
- ✅ Handles burst events well
- ✅ Clean shutdown without errors

### Scenario 7: Error Handling

**Objective**: Validate system resilience

1. Test with invalid API keys
2. Test with network failures
3. Test with malformed data
4. Verify graceful degradation
5. Test automatic recovery

**Success Criteria**:
- ✅ Invalid keys handled gracefully
- ✅ Network errors don't crash system
- ✅ Malformed data rejected properly
- ✅ Fallback responses work
- ✅ System recovers automatically

## Running Tests

### Quick Start

```bash
# Run all E2E tests
npm run test:e2e

# Run with server (full integration)
npm run dev:server          # Terminal 1
npm run test:e2e            # Terminal 2
```

### Focused Testing

```bash
# Test specific functionality
npm run test:email-self          # Email integration
npm run test:sms-conversation    # SMS integration
npm run test:voice-conversation  # Voice integration
npm run test:database-persistence # Database
npm run test:dashboard-live      # Dashboard
```

### Selective Test Execution

```bash
# Run only email tests from master suite
npm run test:e2e email

# Run only SMS tests
npm run test:e2e sms

# Run database and dashboard tests
npm run test:e2e database dashboard
```

## Test Output

### Success Output

```
╔════════════════════════════════════════════════════════════╗
║          xSwarm Boss End-to-End Test Suite                 ║
╚════════════════════════════════════════════════════════════╝

🧪 Running: Email Self-Conversation Test
────────────────────────────────────────────────────────────
   📧 Sending email from Boss to Boss...
   ✅ Email sent successfully!
   Status: 202
   Message ID: abc123xyz
✅ PASSED: Email Self-Conversation Test (1234ms)

════════════════════════════════════════════════════════════
TEST SUMMARY
════════════════════════════════════════════════════════════
Total Tests:    7
✅ Passed:      7
❌ Failed:      0
⏭️  Skipped:     0
Duration:       45.32s

✅ All tests passed! The Boss assistant is working correctly.
```

### Failure Output

```
❌ FAILED: Email Self-Conversation Test (567ms)
   Error: SendGrid API error: Invalid API key

════════════════════════════════════════════════════════════
TEST SUMMARY
════════════════════════════════════════════════════════════
Total Tests:    7
✅ Passed:      6
❌ Failed:      1
⏭️  Skipped:     0
Duration:       32.18s

ERRORS:
  1. Email Self-Conversation Test
     SendGrid API error: Invalid API key

❌ Some tests failed. Please review the errors above.
```

## Manual Verification Steps

Some tests require manual verification:

### Email Tests
1. Check inbox at Boss email address
2. Verify email was received
3. Check for AI-generated response
4. Validate email formatting

### SMS Tests
1. Check phone for received SMS
2. Verify message content
3. Check response timeliness
4. Validate formatting

### Voice Tests
1. Answer test call
2. Speak test phrases
3. Verify AI responses
4. Check call quality

## Troubleshooting

### Common Issues

#### 1. Missing API Keys

**Error**: `Missing required secrets: ANTHROPIC_API_KEY`

**Solution**:
```bash
# Check .env file
cat .env | grep ANTHROPIC_API_KEY

# Add missing key
echo 'ANTHROPIC_API_KEY=your_key_here' >> .env
```

#### 2. Server Not Running

**Error**: `ECONNREFUSED` or `fetch failed`

**Solution**:
```bash
# Start server in separate terminal
npm run dev:server

# Then run tests
npm run test:e2e
```

#### 3. Webhook Tests Failing

**Error**: `Webhook returned 404`

**Solution**:
```bash
# Ensure server is running and configured
npm run dev:server

# For local development, use webhook forwarding
npm run dev:webhooks
```

#### 4. Database Connection Failed

**Error**: `Database connection failed`

**Solution**:
```bash
# Check database URL in config.toml
# For local testing, use file://./local.db

# For remote Turso, verify auth token
echo $TURSO_AUTH_TOKEN
```

#### 5. Dashboard Won't Start

**Error**: `Dashboard failed to start`

**Solution**:
```bash
# Build Rust project first
cargo build

# Verify TUI binary exists
cargo run --bin xswarm-tui --help

# Check for Rust installation
cargo --version
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: pnpm install

      - name: Configure secrets
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          TWILIO_AUTH_TOKEN: ${{ secrets.TWILIO_AUTH_TOKEN }}
        run: |
          echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> .env
          echo "SENDGRID_API_KEY=$SENDGRID_API_KEY" >> .env
          echo "TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN" >> .env

      - name: Start server
        run: |
          npm run dev:server &
          sleep 5

      - name: Run E2E tests
        run: npm run test:e2e
```

## Best Practices

1. **Run tests against test/sandbox APIs** when available
2. **Clean up test data** after each run
3. **Use unique test identifiers** (timestamps)
4. **Prefix test data** with "TEST_" or "E2E_"
5. **Monitor API quotas** to avoid rate limits
6. **Review manual verification steps** for completeness
7. **Run full suite** before production deployments
8. **Keep test data separate** from production data

## Cost Considerations

These tests make real API calls which may incur costs:

- **Anthropic Claude**: ~$0.001 per test
- **SendGrid**: Free tier sufficient for testing
- **Twilio SMS**: ~$0.0075 per SMS
- **Twilio Voice**: ~$0.013 per minute
- **Turso**: Free tier sufficient for testing

**Estimated cost per full test run**: ~$0.10 - $0.50

## Security Notes

⚠️ **Important Security Considerations**:

1. **Never commit `.env` file** - Contains real API keys
2. **Use test/sandbox keys** when available
3. **Rotate keys regularly** for security
4. **Limit test frequency** to avoid quota exhaustion
5. **Monitor API usage** in service dashboards
6. **Use separate accounts** for testing if possible

## Contributing

When adding new tests:

1. Follow existing test structure
2. Use real APIs, not mocks
3. Add manual verification steps if needed
4. Document expected behavior
5. Include troubleshooting tips
6. Update this guide with new scenarios

## Support

If you encounter issues:

1. Check troubleshooting section above
2. Review service status pages
3. Verify API keys are valid
4. Check service quotas
5. Open issue on GitHub with full error details

## Future Enhancements

Planned improvements:

- [ ] Automated webhook response verification
- [ ] Email inbox monitoring API integration
- [ ] Voice call audio recording verification
- [ ] Performance benchmarking suite
- [ ] Load testing scenarios
- [ ] Multi-user concurrent testing
- [ ] Network failure simulation
- [ ] Backup/restore testing
