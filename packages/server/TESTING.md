# Testing Guide for Simple Message Router

## Philosophy

This codebase follows **best testing practices** by:

1. **Separating pure logic from side effects** - Business logic is pure and easily testable
2. **Minimizing mocks** - Only the database layer needs mocking
3. **Testing pure functions directly** - No mocks needed for business logic
4. **Using integration tests** - Test complete workflows when appropriate

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│ Pure Functions (Business Logic)            │
│ - No side effects                          │
│ - Easy to test without mocks               │
│ - Deterministic outputs                    │
├─────────────────────────────────────────────┤
│ Examples:                                  │
│ • parseDateTime()                          │
│ • extractHour()                           │
│ • detectCommand()                         │
│ • buildScheduleResponse()                 │
│ • routeMessage()                          │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Database Interface Layer                   │
│ - Minimal abstraction over database        │
│ - Only place where mocks are needed        │
│ - Small surface area for testing           │
├─────────────────────────────────────────────┤
│ Functions:                                 │
│ • db.findUser()                           │
│ • db.logMessage()                         │
│ • db.createAppointment()                  │
│ • db.createReminder()                     │
│ • db.getAppointments()                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ Command Handlers (Orchestration)          │
│ - Combine pure functions + DB calls        │
│ - Can be tested with DB mocks              │
│ - Clear separation of concerns             │
├─────────────────────────────────────────────┤
│ Handlers:                                  │
│ • handleScheduleCommand()                 │
│ • handleReminderCommand()                 │
│ • handleCalendarCommand()                 │
└─────────────────────────────────────────────┘
```

## Test Structure

### 1. Pure Function Tests (No Mocks)

These tests validate business logic without any mocking:

```javascript
test('parseDateTime - handles "tomorrow at 2pm"', () => {
  const referenceDate = new Date('2024-01-15T10:00:00.000Z');
  const result = parseDateTime('schedule meeting tomorrow at 2pm', referenceDate);
  const parsed = new Date(result);

  assert.strictEqual(parsed.getUTCDate(), 16); // Next day
  assert.strictEqual(parsed.getUTCHours(), 14); // 2pm
});
```

**Benefits:**
- Fast execution
- No dependencies
- Easy to understand
- Deterministic results
- No setup/teardown needed

### 2. Database Layer Tests (Minimal Mocking)

The database layer has a minimal interface that can be easily mocked:

```javascript
test('db mock - test appointment creation flow', async () => {
  const appointments = [];

  const mockDb = {
    async createAppointment(userId, title, startTime, endTime, env) {
      const id = 'mock-id-' + appointments.length;
      appointments.push({ id, userId, title, startTime, endTime });
      return id;
    },
  };

  const id = await mockDb.createAppointment(
    '123',
    'Test Meeting',
    '2024-01-15T14:00:00.000Z',
    '2024-01-15T15:00:00.000Z',
    {}
  );

  assert.strictEqual(id, 'mock-id-0');
  assert.strictEqual(appointments.length, 1);
});
```

**Benefits:**
- Only 5 database functions to mock
- Mocks are simple and focused
- Test database operations in isolation
- Can use in-memory structures for testing

### 3. Integration Tests (Complete Workflows)

Integration tests validate entire workflows using pure functions:

```javascript
test('integration - schedule command workflow', () => {
  const content = 'schedule team meeting tomorrow at 2pm';

  // Step 1: Detect command (pure function)
  const commandType = detectCommand(content);
  assert.strictEqual(commandType, 'schedule');

  // Step 2: Parse data (pure functions)
  const title = extractTitle(content);
  const startTime = parseDateTime(content, referenceDate);

  // Step 3: Validate results
  assert.strictEqual(title, 'team');
  const parsed = new Date(startTime);
  assert.strictEqual(parsed.getUTCDate(), 16);
});
```

**Benefits:**
- Test real user workflows
- Validate function composition
- No mocks needed (all pure functions)
- Catches integration issues

## Running Tests

```bash
# Run all tests
npm test

# Run tests with Node's built-in test runner
node --test src/simple-index.test.js
```

## Test Coverage

Current test suite includes:

### Pure Functions (35 tests)
- ✅ Date/time parsing (parseDateTime)
- ✅ Hour extraction (extractHour)
- ✅ Title extraction (extractTitle)
- ✅ Reminder text extraction (extractReminderText)
- ✅ Command detection (detectCommand)
- ✅ User formatting (formatUser)
- ✅ Response building (buildScheduleResponse, buildReminderResponse, buildCalendarResponse)
- ✅ Message routing (routeMessage)

### Database Layer (4 tests)
- ✅ User lookup mock
- ✅ Appointment creation mock
- ✅ Reminder creation mock
- ✅ Appointments retrieval mock

### Integration Tests (8 tests)
- ✅ Schedule command workflow
- ✅ Reminder command workflow
- ✅ Calendar view workflow
- ✅ Admin routing workflow
- ✅ Regular user routing workflow
- ✅ Edge cases (past times, multiple formats, etc.)

## Why This Approach Works

### 1. Minimal Mocking
**Problem:** Mocks are a code smell - they couple tests to implementation details and can mask real bugs.

**Solution:** By separating pure functions from database calls, we only mock the thin database layer (5 functions).

### 2. Easy to Test
**Problem:** Testing functions with side effects is hard and requires complex mocking.

**Solution:** Pure functions are deterministic - same input always produces same output. No setup needed.

### 3. Fast Tests
**Problem:** Tests with database connections or external dependencies are slow.

**Solution:** Pure function tests run in milliseconds. 47 tests complete in ~270ms.

### 4. Maintainable
**Problem:** Tests break when implementation details change.

**Solution:** Tests focus on behavior (inputs/outputs), not implementation. Pure functions can be refactored without breaking tests.

### 5. Real Validation
**Problem:** Over-mocked tests can pass while real code fails.

**Solution:** Integration tests use actual pure functions to validate complete workflows.

## Best Practices

### DO ✅

1. **Write pure functions whenever possible**
   ```javascript
   // Pure - no side effects, easy to test
   export function parseDateTime(text, referenceDate = new Date()) {
     // Logic here
     return isoString;
   }
   ```

2. **Keep database interface minimal**
   ```javascript
   // Small, focused database interface
   export const db = {
     async findUser(identifier, env) { /* ... */ },
     async createAppointment(userId, title, startTime, endTime, env) { /* ... */ },
   };
   ```

3. **Test pure functions directly**
   ```javascript
   // No mocks needed!
   test('parseDateTime works correctly', () => {
     const result = parseDateTime('tomorrow at 2pm', referenceDate);
     assert.strictEqual(result, expected);
   });
   ```

4. **Use integration tests for workflows**
   ```javascript
   // Test the complete flow
   test('schedule command workflow', () => {
     const command = detectCommand(content);
     const title = extractTitle(content);
     const time = parseDateTime(content, ref);
     // Validate complete workflow
   });
   ```

### DON'T ❌

1. **Don't mix business logic with database calls**
   ```javascript
   // BAD - hard to test
   async function scheduleAppointment(content, env) {
     const db = getDbClient(env); // Side effect!
     const title = extractTitle(content); // Pure logic
     await db.execute(...); // Side effect!
     return formatResponse(title); // Pure logic
   }
   ```

2. **Don't create mocks for pure functions**
   ```javascript
   // BAD - unnecessary mock
   const mockParseDateTime = jest.fn().mockReturnValue('2024-01-15T14:00:00Z');

   // GOOD - just call the real function
   const result = parseDateTime('tomorrow at 2pm', referenceDate);
   ```

3. **Don't test implementation details**
   ```javascript
   // BAD - tests how it works
   expect(parseDateTime).toHaveBeenCalledWith('tomorrow');

   // GOOD - tests what it returns
   assert.strictEqual(result, '2024-01-15T14:00:00Z');
   ```

## Adding New Features

When adding new features, follow this pattern:

1. **Extract pure logic functions**
   - Write deterministic functions with no side effects
   - Add tests without mocks

2. **Add database functions if needed**
   - Keep them in the `db` object
   - Create minimal mock for testing

3. **Write command handlers**
   - Orchestrate pure functions + database calls
   - Test with database mocks

4. **Add integration tests**
   - Test complete user workflows
   - Use pure functions (no mocks needed)

## Example: Adding a New Command

```javascript
// 1. Pure function for parsing
export function extractEventDetails(text) {
  // Pure logic - easy to test
  return { name, location, attendees };
}

// 2. Database function (if needed)
db.createEvent = async (userId, details, env) => {
  const client = getDbClient(env);
  await client.execute(...);
};

// 3. Command handler
async function handleEventCommand(userId, content, env) {
  // Pure function call
  const details = extractEventDetails(content);

  // Database call
  await db.createEvent(userId, details, env);

  // Pure function call
  return buildEventResponse(details);
}

// 4. Tests
test('extractEventDetails - parses event info', () => {
  const result = extractEventDetails('party at home with friends');
  assert.strictEqual(result.name, 'party');
  assert.strictEqual(result.location, 'home');
});
```

## Debugging Failed Tests

### Pure Function Test Fails
- Check input/output directly
- No external dependencies to debug
- Use console.log to trace logic

### Database Mock Test Fails
- Verify mock structure matches interface
- Check if all required parameters are provided
- Ensure mock returns expected format

### Integration Test Fails
- Break down into individual function calls
- Test each pure function separately
- Verify the workflow logic

## Performance

Current test suite performance:
- **47 tests** in ~270ms
- **No external dependencies** (database, network, etc.)
- **Pure function tests** run in <1ms each
- **Integration tests** complete in <1ms each

## Summary

This testing approach provides:
- ✅ **Fast tests** - No database or network calls
- ✅ **Reliable tests** - Deterministic, no flakiness
- ✅ **Easy to write** - Pure functions need no setup
- ✅ **Easy to maintain** - Tests focus on behavior, not implementation
- ✅ **Minimal mocks** - Only database layer (5 functions)
- ✅ **Real validation** - Integration tests use actual code

**Key Principle:** Mocks are a code smell. Minimize them by separating pure logic from side effects.
