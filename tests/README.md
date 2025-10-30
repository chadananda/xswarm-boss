# xSwarm Test Suite

Comprehensive testing coverage for all xSwarm SaaS features including authentication, team management, email marketing, suggestions, xSwarm Buzz platform, and dashboard.

## Directory Structure

```
tests/
├── unit/              # Unit tests for individual components
├── integration/       # Integration tests for API endpoints and database
├── e2e/              # End-to-end user flow tests
├── performance/      # Performance and load tests
├── security/         # Security and authorization tests
├── fixtures/         # Test data fixtures
├── utils/            # Test utilities and helpers
│   ├── assert.js     # Enhanced assertion library
│   ├── http.js       # HTTP request helpers
│   ├── database.js   # Database test utilities
│   ├── reporter.js   # Test result reporter
│   └── runner.js     # Test runner implementation
├── config.js         # Test configuration
├── test-runner.js    # Main test runner script
└── README.md         # This file
```

## Quick Start

### Prerequisites

1. **Environment Setup**
   ```bash
   # Copy .env.example to .env and configure
   cp .env.example .env

   # Set test-specific environment variables
   export TEST_DATABASE_URL="your_test_database_url"
   export TEST_API_URL="http://localhost:8787"
   ```

2. **Install Dependencies**
   ```bash
   pnpm install
   ```

3. **Start Test Server** (in separate terminal)
   ```bash
   pnpm run dev:server
   ```

### Running Tests

```bash
# Run all tests
pnpm run test

# Run specific test suite
node tests/test-runner.js --filter=auth

# Run with verbose output
node tests/test-runner.js --verbose

# Save results to file
node tests/test-runner.js --output=test-results.json
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation:

- **auth.test.js** - Authentication system (signup, login, JWT, email verification)
- **teams.test.js** - Team management (creation, invitations, roles, permissions)
- **marketing.test.js** - Email marketing campaigns and sequences
- **suggestions.test.js** - Suggestion collection and voting
- **buzz.test.js** - xSwarm Buzz listing platform
- **dashboard.test.js** - Dashboard analytics and metrics

### Integration Tests (`tests/integration/`)

Test interactions between components:

- **database.test.js** - Database operations, constraints, triggers
- **api-endpoints.test.js** - Complete API endpoint testing
- **email-delivery.test.js** - Email sending via SendGrid
- **stripe-payments.test.js** - Payment processing and webhooks

### E2E Tests (`tests/e2e/`)

Test complete user workflows:

- **user-signup.test.js** - Complete signup flow for all tiers
- **team-workflow.test.js** - Team collaboration workflows
- **subscription-management.test.js** - Tier upgrades and billing
- **marketing-funnel.test.js** - Email campaign enrollment and conversion

### Performance Tests (`tests/performance/`)

Test system performance under load:

- **api-load.test.js** - API endpoint load testing
- **database-queries.test.js** - Database query performance

### Security Tests (`tests/security/`)

Test security and authorization:

- **auth-validation.test.js** - Authentication security
- **permission-checks.test.js** - Authorization and access control

## Writing Tests

### Basic Test Structure

```javascript
import { assert } from '../utils/assert.js';
import { post, get } from '../utils/http.js';
import { withCleanDatabase } from '../utils/database.js';

export default function (runner) {
  runner.describe('Feature Name', async ctx => {

    // Setup hook (runs once before all tests)
    ctx.beforeAll(async () => {
      // Setup code
    });

    // Cleanup hook (runs after each test)
    ctx.afterEach(async () => {
      // Cleanup code
    });

    // Individual test
    await ctx.test('should do something', async () => {
      await withCleanDatabase(async db => {
        // Test code
        const response = await post('/api/endpoint', { data });
        assert.strictEqual(response.status, 200);
      });
    });
  });
}
```

### Using Assertions

```javascript
import {
  assert,
  assertValidJWT,
  assertValidEmail,
  assertStatus,
  assertHasKeys
} from '../utils/assert.js';

// Basic assertions
assert.strictEqual(actual, expected);
assert.ok(value);
assert.deepStrictEqual(obj1, obj2);

// Custom assertions
assertValidJWT(token);
assertValidEmail('test@example.com');
assertStatus(response, 200);
assertHasKeys(obj, ['id', 'name', 'email']);
```

### HTTP Requests

```javascript
import { get, post, put, del, login, signup } from '../utils/http.js';

// Simple requests
const response = await get('/api/endpoint');
const response = await post('/api/endpoint', { data });

// With authentication
const { token, client } = await login(BASE_URL, credentials);
const response = await client.get('/api/protected');

// With query params
const response = await get('/api/search', {
  query: { q: 'test', limit: 10 }
});
```

### Database Utilities

```javascript
import {
  createTestDb,
  withCleanDatabase,
  createTestUser,
  createTestTeam
} from '../utils/database.js';

// Clean database for each test
await withCleanDatabase(async db => {
  const user = await createTestUser(db, {
    email: 'test@example.com',
    subscription_tier: 'ai_secretary'
  });

  const team = await createTestTeam(db, user.id);
});
```

## Test Data Fixtures

Test fixtures are located in `tests/fixtures/`:

- `users.json` - Sample user data
- `teams.json` - Sample team data
- `campaigns.json` - Sample marketing campaigns
- `suggestions.json` - Sample suggestions
- `buzz-listings.json` - Sample Buzz listings

## Environment Variables

### Required

- `TEST_DATABASE_URL` or `TURSO_DATABASE_URL` - Test database URL
- `TEST_API_URL` - API endpoint (default: http://localhost:8787)

### Optional

- `TEST_AUTH_TOKEN` or `TURSO_AUTH_TOKEN` - Database auth token
- `SENDGRID_API_KEY` - For email delivery tests
- `STRIPE_SECRET_KEY` - For payment tests
- `STRIPE_WEBHOOK_SECRET` - For webhook tests
- `RUN_INTEGRATION_TESTS` - Enable/disable integration tests (default: true)
- `RUN_E2E_TESTS` - Enable/disable E2E tests (default: true)
- `RUN_PERFORMANCE_TESTS` - Enable/disable performance tests (default: true)

## Coverage Goals

- **Unit Tests**: 100% of business logic functions
- **Integration Tests**: All API endpoints and database operations
- **E2E Tests**: Critical user flows for all tiers
- **Performance Tests**: Baseline metrics established for all endpoints
- **Security Tests**: All authentication and authorization paths

## CI/CD Integration

Tests are automatically run on:

- Pull requests
- Commits to main branch
- Nightly builds

### GitHub Actions Workflow

```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: pnpm/action-setup@v2
      - run: pnpm install
      - run: pnpm test
```

## Troubleshooting

### Database Connection Issues

```bash
# Check database URL
echo $TEST_DATABASE_URL

# Verify database is accessible
curl $TEST_DATABASE_URL
```

### API Server Not Running

```bash
# Start dev server
pnpm run dev:server

# Or use production build
pnpm run deploy:dev
```

### Test Failures

```bash
# Run with verbose output
node tests/test-runner.js --verbose

# Run specific failing test
node tests/test-runner.js --filter=auth
```

## Contributing

1. Write tests for all new features
2. Ensure all tests pass before submitting PR
3. Maintain test coverage above 80%
4. Follow existing test structure and naming conventions

## License

MIT
