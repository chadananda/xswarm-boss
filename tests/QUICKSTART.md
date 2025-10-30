# Test Suite Quick Start Guide

## 1. Setup (One-time)

```bash
# 1. Copy environment file
cp tests/.env.example tests/.env

# 2. Configure test database
# Edit tests/.env and set TEST_DATABASE_URL

# 3. Install dependencies (if not already done)
pnpm install
```

## 2. Start Test Server

```bash
# In one terminal, start the development server
pnpm run dev:server

# The server should be running at http://localhost:8787
```

## 3. Run Tests

### Run All Tests
```bash
pnpm test
```

### Run Specific Test Categories
```bash
# Unit tests only
pnpm run test:unit

# Integration tests only
pnpm run test:integration

# E2E tests only
pnpm run test:e2e:full

# Performance tests
pnpm run test:performance

# Security tests
pnpm run test:security
```

### Run Specific Test File
```bash
# Run auth tests only
node tests/test-runner.js --filter=auth

# Run database tests only
node tests/test-runner.js --filter=database
```

### Verbose Output
```bash
pnpm run test:verbose
```

### Save Results
```bash
pnpm run test:ci
# Results saved to test-results.json
```

## 4. Test Output

### Successful Run
```
🧪 xSwarm Test Suite

Found 2 test file(s)

Starting test run...

Authentication System (1234ms)
  ✓ should signup user with free tier (123ms)
  ✓ should signup user with ai_secretary tier (98ms)
  ✓ should reject duplicate email signup (67ms)
  ...
  10 passed, 0 failed

Database Integration (2345ms)
  ✓ should enforce foreign key constraints (45ms)
  ✓ should cascade delete user data (89ms)
  ...
  15 passed, 0 failed

──────────────────────────────────────────────────
Overall Results
Total:    25 tests
Passed:   25
Failed:   0
Skipped:  0
Duration: 3579ms
Pass rate: 100.00%
──────────────────────────────────────────────────
```

### Failed Tests
```
Authentication System
  ✓ should signup user with free tier (123ms)
  ✗ should reject duplicate email signup (67ms)
    Expected status 400, got 200
      at auth.test.js:52:10
  ...
  9 passed, 1 failed
```

## 5. Common Issues

### Database Connection Error
```
Error: Database URL not configured
```
**Solution**: Set `TEST_DATABASE_URL` in `tests/.env`

### Server Not Running
```
Error: connect ECONNREFUSED 127.0.0.1:8787
```
**Solution**: Start the dev server with `pnpm run dev:server`

### Import Errors
```
Error: Cannot find module
```
**Solution**: Run `pnpm install` to install dependencies

## 6. Writing New Tests

### Create Test File
```bash
# Create in appropriate directory
touch tests/unit/my-feature.test.js
```

### Basic Test Template
```javascript
import { assert } from '../utils/assert.js';
import { post, get } from '../utils/http.js';
import { withCleanDatabase } from '../utils/database.js';

const BASE_URL = process.env.TEST_API_URL || 'http://localhost:8787';

export default function (runner) {
  runner.describe('My Feature', async ctx => {

    await ctx.test('should do something', async () => {
      await withCleanDatabase(async db => {
        // Test code here
        const response = await get(`${BASE_URL}/api/endpoint`);
        assert.strictEqual(response.status, 200);
      });
    });

  });
}
```

### Run Your New Test
```bash
node tests/test-runner.js --filter=my-feature
```

## 7. Best Practices

1. **Clean Database**: Always use `withCleanDatabase()` to ensure test isolation
2. **Meaningful Names**: Use descriptive test names that explain what is being tested
3. **One Assertion Focus**: Each test should focus on testing one specific behavior
4. **Fast Tests**: Keep unit tests under 100ms, integration tests under 1000ms
5. **No Hardcoded Data**: Use test utilities to generate unique test data
6. **Cleanup**: Tests should clean up after themselves

## 8. CI/CD Integration

Tests run automatically on:
- Every pull request
- Commits to main branch
- Nightly builds

View test results in GitHub Actions workflow.

## 9. Coverage

Track test coverage with:
```bash
pnpm run test:ci
cat test-results.json | jq '.stats'
```

## 10. Getting Help

- Check `tests/README.md` for detailed documentation
- Review existing tests for examples
- Ask in #testing channel on Discord
