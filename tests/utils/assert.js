/**
 * Test Assertion Utilities
 * Enhanced assertions built on Node.js assert module
 */

import assert from 'node:assert';

/**
 * Assert that an async function throws an error
 */
export async function assertThrows(fn, expectedError) {
  let thrown = false;
  let error = null;

  try {
    await fn();
  } catch (e) {
    thrown = true;
    error = e;
  }

  assert.strictEqual(thrown, true, 'Expected function to throw an error');

  if (expectedError) {
    if (typeof expectedError === 'string') {
      assert.ok(
        error.message.includes(expectedError),
        `Expected error message to include "${expectedError}", got "${error.message}"`
      );
    } else if (expectedError instanceof RegExp) {
      assert.ok(
        expectedError.test(error.message),
        `Expected error message to match ${expectedError}, got "${error.message}"`
      );
    } else if (typeof expectedError === 'function') {
      assert.ok(
        error instanceof expectedError,
        `Expected error to be instance of ${expectedError.name}, got ${error.constructor.name}`
      );
    }
  }

  return error;
}

/**
 * Assert that an async function does not throw
 */
export async function assertDoesNotThrow(fn) {
  try {
    await fn();
  } catch (error) {
    assert.fail(`Expected function not to throw, but got: ${error.message}`);
  }
}

/**
 * Assert that a value is within a range
 */
export function assertInRange(value, min, max, message) {
  assert.ok(
    value >= min && value <= max,
    message || `Expected ${value} to be between ${min} and ${max}`
  );
}

/**
 * Assert that an object has all expected keys
 */
export function assertHasKeys(obj, keys, message) {
  const objKeys = Object.keys(obj);
  const missingKeys = keys.filter(key => !objKeys.includes(key));

  assert.strictEqual(
    missingKeys.length,
    0,
    message || `Expected object to have keys: ${missingKeys.join(', ')}`
  );
}

/**
 * Assert that an array contains an item matching predicate
 */
export function assertArrayContains(arr, predicate, message) {
  const found = arr.some(predicate);
  assert.ok(found, message || 'Expected array to contain matching item');
}

/**
 * Assert that an array does not contain an item matching predicate
 */
export function assertArrayDoesNotContain(arr, predicate, message) {
  const found = arr.some(predicate);
  assert.ok(!found, message || 'Expected array not to contain matching item');
}

/**
 * Assert that a response has expected HTTP status
 */
export function assertStatus(response, expectedStatus) {
  assert.strictEqual(
    response.status,
    expectedStatus,
    `Expected status ${expectedStatus}, got ${response.status}`
  );
}

/**
 * Assert that a response is successful (2xx)
 */
export function assertSuccess(response) {
  assert.ok(
    response.status >= 200 && response.status < 300,
    `Expected successful status, got ${response.status}`
  );
}

/**
 * Assert that a response is a client error (4xx)
 */
export function assertClientError(response) {
  assert.ok(
    response.status >= 400 && response.status < 500,
    `Expected client error status, got ${response.status}`
  );
}

/**
 * Assert that a response is a server error (5xx)
 */
export function assertServerError(response) {
  assert.ok(
    response.status >= 500 && response.status < 600,
    `Expected server error status, got ${response.status}`
  );
}

/**
 * Assert that a value is a valid JWT token
 */
export function assertValidJWT(token) {
  assert.ok(typeof token === 'string', 'Expected token to be a string');
  const parts = token.split('.');
  assert.strictEqual(parts.length, 3, 'Expected JWT to have 3 parts');

  // Verify each part is valid base64url
  parts.forEach((part, index) => {
    assert.ok(
      /^[A-Za-z0-9_-]+$/.test(part),
      `Expected JWT part ${index} to be valid base64url`
    );
  });
}

/**
 * Assert that a value is a valid email
 */
export function assertValidEmail(email) {
  assert.ok(typeof email === 'string', 'Expected email to be a string');
  assert.ok(
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),
    `Expected "${email}" to be a valid email address`
  );
}

/**
 * Assert that a value is a valid UUID
 */
export function assertValidUUID(uuid) {
  assert.ok(typeof uuid === 'string', 'Expected UUID to be a string');
  assert.ok(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(uuid),
    `Expected "${uuid}" to be a valid UUID`
  );
}

/**
 * Assert that a date string is recent (within specified seconds)
 */
export function assertRecentDate(dateStr, maxAgeSeconds = 60) {
  const date = new Date(dateStr);
  const now = new Date();
  const ageSeconds = (now - date) / 1000;

  assert.ok(
    ageSeconds >= 0 && ageSeconds <= maxAgeSeconds,
    `Expected date to be within last ${maxAgeSeconds} seconds, but was ${ageSeconds}s ago`
  );
}

// Re-export all assert methods
export { assert };
export default assert;
