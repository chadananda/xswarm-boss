# Tier Features Integration - Comprehensive Test Suite

## Overview
Create a complete test suite for all newly implemented tier-based features from the tier-features.md specification.

## Test Categories

### 1. Foundation Layer Tests
- [ ] 1.1: Test tier naming system (free/personal/professional/enterprise)
- [ ] 1.2: Test feature gating middleware for all tier restrictions
- [ ] 1.3: Test Stripe integration with webhook handlers
- [ ] 1.4: Test usage tracking and overage calculations

### 2. Semantic Memory System Tests
- [ ] 2.1: Test vector embedding generation and storage
- [ ] 2.2: Test cosine similarity search and retrieval
- [ ] 2.3: Test fact extraction from conversations
- [ ] 2.4: Test entity recognition (people, places, companies)
- [ ] 2.5: Test tier-based retention policies (30/365/730/unlimited days)
- [ ] 2.6: Test GDPR data deletion
- [ ] 2.7: Test memory statistics and metadata

### 3. Custom Persona Management Tests
- [ ] 3.1: Test persona creation with Big Five traits
- [ ] 3.2: Test tier limits (Free: 3 personas, Personal+: unlimited)
- [ ] 3.3: Test persona trait customization without voice retraining
- [ ] 3.4: Test persona list, get, update, delete operations
- [ ] 3.5: Test persona voice model references
- [ ] 3.6: Test persona validation and error handling

### 4. Task Management System Tests
- [ ] 4.1: Test natural language task parsing (chrono-node)
- [ ] 4.2: Test task CRUD operations (create, read, update, delete, complete)
- [ ] 4.3: Test recurring task patterns (daily, weekly, monthly)
- [ ] 4.4: Test smart reminder scheduling based on priority
- [ ] 4.5: Test conflict detection and scheduling
- [ ] 4.6: Test natural language queries (today, tomorrow, week, overdue)
- [ ] 4.7: Test task summaries with statistics
- [ ] 4.8: Test subtasks and task relationships

### 5. Google Calendar Integration Tests
- [ ] 5.1: Test OAuth2 flow (authorization URL generation)
- [ ] 5.2: Test OAuth callback handling and token storage
- [ ] 5.3: Test calendar event syncing
- [ ] 5.4: Test natural language calendar queries
- [ ] 5.5: Test daily briefing generation
- [ ] 5.6: Test event creation (Personal+ tier only)
- [ ] 5.7: Test iCal subscription support
- [ ] 5.8: Test conflict detection across calendars
- [ ] 5.9: Test calendar read-only vs read-write access by tier

### 6. Gmail Integration Tests
- [ ] 6.1: Test Gmail OAuth2 flow
- [ ] 6.2: Test email reading (inbox, sent, drafts)
- [ ] 6.3: Test email search and filtering
- [ ] 6.4: Test read-only access (Free tier)
- [ ] 6.5: Test write access - drafting replies (Personal+ tier)
- [ ] 6.6: Test email sending on behalf of user
- [ ] 6.7: Test thread summarization
- [ ] 6.8: Test email triage and categorization

### 7. Voice-First Task Management Tests
- [ ] 7.1: Test voice command parsing for task creation
- [ ] 7.2: Test voice command parsing for task updates
- [ ] 7.3: Test voice-optimized query responses
- [ ] 7.4: Test natural language date/time extraction
- [ ] 7.5: Test priority detection from voice input
- [ ] 7.6: Test category inference from context

### 8. Feature Gating Integration Tests
- [ ] 8.1: Test requireFeature() middleware blocks unauthorized access
- [ ] 8.2: Test requireTier() middleware enforces minimum tier
- [ ] 8.3: Test checkUsageLimit() validates and tracks usage
- [ ] 8.4: Test softGate() allows access with upgrade CTA
- [ ] 8.5: Test tierBasedRateLimit() varies by tier
- [ ] 8.6: Test automatic upgrade CTA generation
- [ ] 8.7: Test overage handling and billing calculations

### 9. Billing & Subscription Tests
- [ ] 9.1: Test Stripe subscription creation
- [ ] 9.2: Test tier upgrade flow
- [ ] 9.3: Test tier downgrade flow
- [ ] 9.4: Test usage-based billing (voice minutes, SMS)
- [ ] 9.5: Test webhook processing for subscription events
- [ ] 9.6: Test payment failure handling
- [ ] 9.7: Test trial period handling

### 10. API Endpoint Tests
- [ ] 10.1: Test /api/memory/* endpoints (store, retrieve, facts, entities)
- [ ] 10.2: Test /api/personas/* endpoints (CRUD operations)
- [ ] 10.3: Test /api/tasks/* endpoints (voice, query, schedule)
- [ ] 10.4: Test /api/calendar/* endpoints (auth, query, events, briefing)
- [ ] 10.5: Test /api/email/* endpoints (OAuth, read, send)
- [ ] 10.6: Test /api/tiers/* endpoints (features, usage, upgrade)
- [ ] 10.7: Test /api/billing/* endpoints (subscription, payment methods)

### 11. Visual/Playwright Tests
- [ ] 11.1: Test signup flow for each tier
- [ ] 11.2: Test tier upgrade flow with Stripe checkout
- [ ] 11.3: Test dashboard displays correct tier features
- [ ] 11.4: Test feature locked modals show upgrade CTAs
- [ ] 11.5: Test usage meters display correctly
- [ ] 11.6: Test persona management UI
- [ ] 11.7: Test task management UI
- [ ] 11.8: Test calendar integration UI

### 12. Database & Data Persistence Tests
- [ ] 12.1: Test memory schema (sessions, facts, entities)
- [ ] 12.2: Test personas schema with traits
- [ ] 12.3: Test tasks schema with reminders
- [ ] 12.4: Test calendar integrations and events schema
- [ ] 12.5: Test usage tracking tables
- [ ] 12.6: Test database indexes and query performance
- [ ] 12.7: Test data cleanup and retention policies

### 13. Error Handling & Edge Cases
- [ ] 13.1: Test invalid tier names
- [ ] 13.2: Test missing OAuth credentials
- [ ] 13.3: Test expired OAuth tokens with refresh
- [ ] 13.4: Test API rate limiting across tiers
- [ ] 13.5: Test concurrent usage limit checks
- [ ] 13.6: Test malformed voice input
- [ ] 13.7: Test invalid date/time parsing
- [ ] 13.8: Test database connection failures
- [ ] 13.9: Test OpenAI API failures (embeddings)
- [ ] 13.10: Test Google API failures (calendar, gmail)

### 14. Security & Authorization Tests
- [ ] 14.1: Test JWT authentication on all protected endpoints
- [ ] 14.2: Test user isolation (users can only access their own data)
- [ ] 14.3: Test tier escalation prevention
- [ ] 14.4: Test OAuth token encryption
- [ ] 14.5: Test SQL injection protection
- [ ] 14.6: Test XSS prevention in user input
- [ ] 14.7: Test CSRF protection on state-changing operations

### 15. Integration & E2E Workflows
- [ ] 15.1: Test complete onboarding flow (signup -> persona -> tasks)
- [ ] 15.2: Test voice-first task creation -> calendar sync workflow
- [ ] 15.3: Test semantic memory -> task context workflow
- [ ] 15.4: Test calendar briefing -> task reminders workflow
- [ ] 15.5: Test tier upgrade -> feature unlock workflow
- [ ] 15.6: Test usage limit hit -> upgrade CTA -> purchase workflow
- [ ] 15.7: Test multi-channel communication (voice + SMS + email)

## Test Infrastructure Setup

### Required Test Files
- tests/unit/tier-system.test.js
- tests/unit/memory-system.test.js
- tests/unit/persona-management.test.js
- tests/unit/task-parsing.test.js
- tests/unit/calendar-queries.test.js
- tests/integration/feature-gating.test.js
- tests/integration/oauth-flows.test.js
- tests/integration/database-operations.test.js
- tests/e2e/tier-upgrade.test.js
- tests/e2e/voice-task-workflow.test.js
- tests/e2e/calendar-sync.test.js
- tests/playwright/ui-features.spec.js

### Test Fixtures Needed
- fixtures/users-by-tier.json
- fixtures/personas.json
- fixtures/tasks.json
- fixtures/calendar-events.json
- fixtures/memory-conversations.json

### Environment Configuration
- .env.test with test database URL
- Mock OAuth credentials
- Test Stripe keys
- Test OpenAI API key

## Success Criteria
- All API endpoints return correct responses
- Tier restrictions enforced properly
- OAuth flows work end-to-end
- Voice parsing extracts correct information
- Database operations persist correctly
- Visual tests show proper UI rendering
- Error handling prevents system failures
- Security tests prevent unauthorized access

## Implementation Notes
- Use existing test infrastructure in tests/ directory
- Follow patterns from test-memory-api.js and test-tasks-api.js
- Use Playwright for visual verification
- Mock external APIs (OpenAI, Google, Stripe) for unit tests
- Use real APIs for integration tests with test accounts
- Clean up test data after each test run
