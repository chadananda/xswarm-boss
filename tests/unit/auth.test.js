/**
 * Unit Tests - Authentication System
 * Tests for user signup, login, email verification, and password reset
 */

import { assert, assertValidJWT, assertValidEmail, assertRecentDate } from '../utils/assert.js';
import { post, get } from '../utils/http.js';
import { withCleanDatabase, createTestUser } from '../utils/database.js';

const BASE_URL = process.env.TEST_API_URL || 'http://localhost:8787';

/**
 * Register test suite
 */
export default function (runner) {
  runner.describe('Authentication System', async ctx => {
    // Test: User Signup - Free Tier
    await ctx.test('should signup user with free tier', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'free@example.com',
          name: 'Free User',
          password: 'SecurePassword123!',
          subscription_tier: 'free',
        });

        assert.strictEqual(response.status, 201, 'Should return 201 Created');
        assert.ok(response.data.token, 'Should return JWT token');
        assert.ok(response.data.user, 'Should return user object');
        assert.strictEqual(response.data.user.email, 'free@example.com');
        assert.strictEqual(response.data.user.subscription_tier, 'free');
        assertValidJWT(response.data.token);
      });
    });

    // Test: User Signup - AI Secretary Tier
    await ctx.test('should signup user with ai_secretary tier', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'secretary@example.com',
          name: 'Secretary User',
          password: 'SecurePassword123!',
          subscription_tier: 'ai_secretary',
        });

        assert.strictEqual(response.status, 201);
        assert.strictEqual(response.data.user.subscription_tier, 'ai_secretary');
      });
    });

    // Test: User Signup - AI Project Manager Tier
    await ctx.test('should signup user with ai_project_manager tier', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'pm@example.com',
          name: 'PM User',
          password: 'SecurePassword123!',
          subscription_tier: 'ai_project_manager',
        });

        assert.strictEqual(response.status, 201);
        assert.strictEqual(response.data.user.subscription_tier, 'ai_project_manager');
      });
    });

    // Test: User Signup - AI CTO Tier
    await ctx.test('should signup user with ai_cto tier', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'cto@example.com',
          name: 'CTO User',
          password: 'SecurePassword123!',
          subscription_tier: 'ai_cto',
        });

        assert.strictEqual(response.status, 201);
        assert.strictEqual(response.data.user.subscription_tier, 'ai_cto');
      });
    });

    // Test: Duplicate Email
    await ctx.test('should reject duplicate email signup', async () => {
      await withCleanDatabase(async db => {
        // First signup
        await post(`${BASE_URL}/api/auth/signup`, {
          email: 'duplicate@example.com',
          name: 'First User',
          password: 'Password123!',
        });

        // Duplicate signup
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'duplicate@example.com',
          name: 'Second User',
          password: 'Password123!',
        });

        assert.strictEqual(response.status, 400, 'Should return 400 Bad Request');
        assert.ok(
          response.data.error.includes('already exists') ||
            response.data.error.includes('duplicate'),
          'Should return appropriate error message'
        );
      });
    });

    // Test: Invalid Email Format
    await ctx.test('should reject invalid email format', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'not-an-email',
          name: 'Test User',
          password: 'Password123!',
        });

        assert.strictEqual(response.status, 400);
        assert.ok(
          response.data.error.includes('email') || response.data.error.includes('invalid'),
          'Should mention email validation error'
        );
      });
    });

    // Test: Weak Password
    await ctx.test('should reject weak password', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'test@example.com',
          name: 'Test User',
          password: '123',
        });

        assert.strictEqual(response.status, 400);
        assert.ok(
          response.data.error.includes('password'),
          'Should mention password validation error'
        );
      });
    });

    // Test: Login with Valid Credentials
    await ctx.test('should login with valid credentials', async () => {
      await withCleanDatabase(async db => {
        // Create user first
        await post(`${BASE_URL}/api/auth/signup`, {
          email: 'login@example.com',
          name: 'Login User',
          password: 'SecurePassword123!',
        });

        // Login
        const response = await post(`${BASE_URL}/api/auth/login`, {
          email: 'login@example.com',
          password: 'SecurePassword123!',
        });

        assert.strictEqual(response.status, 200);
        assert.ok(response.data.token, 'Should return JWT token');
        assertValidJWT(response.data.token);
      });
    });

    // Test: Login with Invalid Password
    await ctx.test('should reject login with invalid password', async () => {
      await withCleanDatabase(async db => {
        // Create user
        await post(`${BASE_URL}/api/auth/signup`, {
          email: 'badpass@example.com',
          name: 'User',
          password: 'CorrectPassword123!',
        });

        // Try wrong password
        const response = await post(`${BASE_URL}/api/auth/login`, {
          email: 'badpass@example.com',
          password: 'WrongPassword123!',
        });

        assert.strictEqual(response.status, 401, 'Should return 401 Unauthorized');
      });
    });

    // Test: Login with Non-existent Email
    await ctx.test('should reject login with non-existent email', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/login`, {
          email: 'nonexistent@example.com',
          password: 'Password123!',
        });

        assert.strictEqual(response.status, 401);
      });
    });

    // Test: Email Verification Token Generation
    await ctx.test('should generate email verification token on signup', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'verify@example.com',
          name: 'Verify User',
          password: 'Password123!',
        });

        assert.strictEqual(response.status, 201);

        // Check database for verification token
        const user = await db.execute({
          sql: 'SELECT email_verification_token, email_verified FROM users WHERE email = ?',
          args: ['verify@example.com'],
        });

        assert.ok(user.rows[0].email_verification_token, 'Should have verification token');
        assert.strictEqual(user.rows[0].email_verified, 0, 'Should not be verified yet');
      });
    });

    // Test: Password Hashing
    await ctx.test('should hash password before storing', async () => {
      await withCleanDatabase(async db => {
        const plainPassword = 'MySecurePassword123!';

        await post(`${BASE_URL}/api/auth/signup`, {
          email: 'hash@example.com',
          name: 'Hash User',
          password: plainPassword,
        });

        // Check that password is hashed in database
        const user = await db.execute({
          sql: 'SELECT password_hash FROM users WHERE email = ?',
          args: ['hash@example.com'],
        });

        assert.ok(user.rows[0].password_hash, 'Should have password hash');
        assert.notStrictEqual(
          user.rows[0].password_hash,
          plainPassword,
          'Password should be hashed'
        );
        assert.ok(
          user.rows[0].password_hash.startsWith('$2'),
          'Should use bcrypt hashing (starts with $2)'
        );
      });
    });

    // Test: JWT Token Contains User Info
    await ctx.test('should include user info in JWT token', async () => {
      await withCleanDatabase(async db => {
        const response = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'jwt@example.com',
          name: 'JWT User',
          password: 'Password123!',
          subscription_tier: 'ai_secretary',
        });

        // Decode JWT (without verification for testing)
        const token = response.data.token;
        const payload = JSON.parse(
          Buffer.from(token.split('.')[1], 'base64url').toString()
        );

        assert.ok(payload.userId, 'Token should contain userId');
        assert.strictEqual(payload.email, 'jwt@example.com', 'Token should contain email');
        assert.ok(payload.exp, 'Token should have expiration');
        assert.ok(payload.iat, 'Token should have issued-at');
      });
    });

    // Test: Get Current User with Valid Token
    await ctx.test('should get current user with valid token', async () => {
      await withCleanDatabase(async db => {
        const signupResponse = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'me@example.com',
          name: 'Me User',
          password: 'Password123!',
        });

        const token = signupResponse.data.token;

        const response = await get(`${BASE_URL}/api/auth/me`, {
          auth: token,
        });

        assert.strictEqual(response.status, 200);
        assert.strictEqual(response.data.email, 'me@example.com');
        assert.strictEqual(response.data.name, 'Me User');
      });
    });

    // Test: Reject Request with Invalid Token
    await ctx.test('should reject request with invalid token', async () => {
      const response = await get(`${BASE_URL}/api/auth/me`, {
        auth: 'invalid.token.here',
      });

      assert.strictEqual(response.status, 401);
    });

    // Test: Logout Invalidates Token
    await ctx.test('should invalidate token on logout', async () => {
      await withCleanDatabase(async db => {
        const signupResponse = await post(`${BASE_URL}/api/auth/signup`, {
          email: 'logout@example.com',
          name: 'Logout User',
          password: 'Password123!',
        });

        const token = signupResponse.data.token;

        // Logout
        const logoutResponse = await post(`${BASE_URL}/api/auth/logout`, null, {
          auth: token,
        });

        assert.strictEqual(logoutResponse.status, 200);

        // Try to use token after logout
        const meResponse = await get(`${BASE_URL}/api/auth/me`, {
          auth: token,
        });

        assert.strictEqual(meResponse.status, 401, 'Token should be invalidated');
      });
    });
  });
}
