/**
 * OAuth Flow Integration Tests
 *
 * Tests complete OAuth2 flows for Google Calendar and Gmail integrations.
 * Includes token management, refresh mechanisms, and error handling.
 */

import './config.js'; // Load environment variables
import { assert, assertThrows } from './utils/assert.js';
import {
  createTestDb,
  setupTestDatabase,
  clearTestData,
  createTestUser,
} from './utils/database.js';

/**
 * Mock OAuth2 client for testing (simulates Google OAuth)
 */
class MockOAuth2Client {
  constructor() {
    this.tokens = null;
    this.authCode = null;
  }

  generateAuthUrl(options) {
    const params = new URLSearchParams({
      client_id: 'mock_client_id',
      redirect_uri: options.redirect_uri || 'http://localhost/callback',
      response_type: 'code',
      scope: Array.isArray(options.scope) ? options.scope.join(' ') : options.scope,
      access_type: options.access_type || 'offline',
      state: options.state || '',
      prompt: options.prompt || 'consent',
    });
    return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
  }

  async getToken(code) {
    if (!code || code === 'invalid_code') {
      throw new Error('Invalid authorization code');
    }

    // Simulate successful token exchange
    return {
      tokens: {
        access_token: `access_${code}_${Date.now()}`,
        refresh_token: `refresh_${code}_${Date.now()}`,
        expiry_date: Date.now() + 3600000, // 1 hour
        token_type: 'Bearer',
        scope: 'https://www.googleapis.com/auth/calendar',
      },
    };
  }

  setCredentials(tokens) {
    this.tokens = tokens;
  }

  async refreshAccessToken() {
    if (!this.tokens?.refresh_token) {
      throw new Error('No refresh token available');
    }

    if (this.tokens.refresh_token === 'invalid_refresh_token') {
      throw new Error('Invalid refresh token');
    }

    // Simulate successful token refresh
    return {
      credentials: {
        access_token: `access_refreshed_${Date.now()}`,
        expiry_date: Date.now() + 3600000,
        token_type: 'Bearer',
      },
    };
  }
}

/**
 * Store mock OAuth tokens in database
 */
async function storeMockTokens(db, userId, provider, tokens, permissions = []) {
  const expiresAt = new Date(tokens.expiry_date).toISOString();
  const now = new Date().toISOString();

  if (provider === 'google_calendar') {
    await db.execute({
      sql: `
        INSERT INTO calendar_integrations (
          user_id, provider, provider_account_id, access_token, refresh_token,
          token_expires_at, last_sync, created_at, updated_at
        ) VALUES (?, 'google', ?, ?, ?, ?, NULL, ?, ?)
        ON CONFLICT (user_id, provider, provider_account_id) DO UPDATE SET
          access_token = excluded.access_token,
          refresh_token = excluded.refresh_token,
          token_expires_at = excluded.token_expires_at,
          updated_at = excluded.updated_at
      `,
      args: [
        userId,
        'primary',
        tokens.access_token,
        tokens.refresh_token,
        expiresAt,
        now,
        now,
      ],
    });
  } else if (provider === 'gmail') {
    await db.execute({
      sql: `
        INSERT INTO email_integrations (
          user_id, provider, email_address, access_token, refresh_token,
          token_expires_at, permissions, sync_enabled, created_at, updated_at
        ) VALUES (?, 'gmail', ?, ?, ?, ?, ?, TRUE, ?, ?)
        ON CONFLICT (user_id, provider) DO UPDATE SET
          email_address = excluded.email_address,
          access_token = excluded.access_token,
          refresh_token = excluded.refresh_token,
          token_expires_at = excluded.token_expires_at,
          permissions = excluded.permissions,
          updated_at = excluded.updated_at
      `,
      args: [
        userId,
        'test@gmail.com',
        tokens.access_token,
        tokens.refresh_token,
        expiresAt,
        JSON.stringify(permissions),
        now,
        now,
      ],
    });
  }
}

/**
 * Get stored OAuth tokens from database
 */
async function getStoredTokens(db, userId, provider) {
  let result;

  if (provider === 'google_calendar') {
    result = await db.execute({
      sql: `
        SELECT access_token, refresh_token, token_expires_at
        FROM calendar_integrations
        WHERE user_id = ? AND provider = 'google'
      `,
      args: [userId],
    });
  } else if (provider === 'gmail') {
    result = await db.execute({
      sql: `
        SELECT access_token, refresh_token, token_expires_at, permissions
        FROM email_integrations
        WHERE user_id = ? AND provider = 'gmail'
      `,
      args: [userId],
    });
  }

  return result.rows[0] || null;
}

/**
 * Register test suite
 */
export default function (runner) {
  runner.describe('OAuth Flow Integration', async ctx => {
    let db;
    let mockOAuth;

    ctx.beforeAll(async () => {
      db = createTestDb();
      await setupTestDatabase(db);
    });

    ctx.beforeEach(async () => {
      mockOAuth = new MockOAuth2Client();
    });

    ctx.afterEach(async () => {
      await clearTestData(db);
    });

    ctx.afterAll(async () => {
      db.close();
    });

    // Test: Google Calendar OAuth URL generation
    await ctx.test('should generate correct Google Calendar OAuth URL', async () => {
      const user = await createTestUser(db, { subscription_tier: 'free' });

      const authUrl = mockOAuth.generateAuthUrl({
        access_type: 'offline',
        scope: ['https://www.googleapis.com/auth/calendar.readonly'],
        state: user.id,
        prompt: 'consent',
      });

      assert.ok(authUrl.includes('accounts.google.com'), 'Should use Google auth endpoint');
      assert.ok(authUrl.includes('access_type=offline'), 'Should request offline access');
      assert.ok(authUrl.includes('calendar.readonly'), 'Should request calendar scope');
      assert.ok(authUrl.includes(`state=${user.id}`), 'Should include user ID in state');
    });

    // Test: OAuth code exchange for tokens
    await ctx.test('should exchange authorization code for tokens', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });
      const authCode = 'test_auth_code_123';

      const { tokens } = await mockOAuth.getToken(authCode);

      assert.ok(tokens.access_token, 'Should receive access token');
      assert.ok(tokens.refresh_token, 'Should receive refresh token');
      assert.ok(tokens.expiry_date, 'Should receive expiry date');
      assert.strictEqual(tokens.token_type, 'Bearer', 'Should use Bearer token type');
    });

    // Test: Invalid authorization code handling
    await ctx.test('should handle invalid authorization code', async () => {
      await assertThrows(
        async () => {
          await mockOAuth.getToken('invalid_code');
        },
        'Invalid authorization code'
      );
    });

    // Test: Store Calendar OAuth tokens in database
    await ctx.test('should store Google Calendar tokens in database', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });
      const { tokens } = await mockOAuth.getToken('valid_code');

      await storeMockTokens(db, user.id, 'google_calendar', tokens);

      const stored = await getStoredTokens(db, user.id, 'google_calendar');
      assert.ok(stored, 'Should store tokens');
      assert.strictEqual(stored.access_token, tokens.access_token, 'Should store access token');
      assert.strictEqual(stored.refresh_token, tokens.refresh_token, 'Should store refresh token');
    });

    // Test: Token refresh mechanism
    await ctx.test('should refresh expired access tokens', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });
      const { tokens } = await mockOAuth.getToken('valid_code');

      // Store tokens with expiry in the past
      const expiredTokens = {
        ...tokens,
        expiry_date: Date.now() - 3600000, // 1 hour ago
      };

      await storeMockTokens(db, user.id, 'google_calendar', expiredTokens);

      // Simulate token refresh
      mockOAuth.setCredentials(expiredTokens);
      const { credentials } = await mockOAuth.refreshAccessToken();

      assert.ok(credentials.access_token, 'Should receive new access token');
      assert.ok(credentials.access_token !== expiredTokens.access_token, 'Should be different token');
    });

    // Test: Missing refresh token error
    await ctx.test('should handle missing refresh token', async () => {
      mockOAuth.setCredentials({ access_token: 'test_token' });

      await assertThrows(
        async () => {
          await mockOAuth.refreshAccessToken();
        },
        'No refresh token available'
      );
    });

    // Test: Invalid refresh token error
    await ctx.test('should handle invalid refresh token', async () => {
      mockOAuth.setCredentials({
        access_token: 'test_token',
        refresh_token: 'invalid_refresh_token',
      });

      await assertThrows(
        async () => {
          await mockOAuth.refreshAccessToken();
        },
        'Invalid refresh token'
      );
    });

    // Test: Gmail OAuth with incremental authorization
    await ctx.test('should support Gmail incremental authorization', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });

      // First authorization: readonly
      const { tokens: readTokens } = await mockOAuth.getToken('read_code');
      await storeMockTokens(db, user.id, 'gmail', readTokens, ['readonly']);

      let stored = await getStoredTokens(db, user.id, 'gmail');
      const permissions = JSON.parse(stored.permissions);
      assert.ok(permissions.includes('readonly'), 'Should have readonly permission');

      // Second authorization: add compose permission
      const { tokens: composeTokens } = await mockOAuth.getToken('compose_code');
      await storeMockTokens(db, user.id, 'gmail', composeTokens, ['readonly', 'compose']);

      stored = await getStoredTokens(db, user.id, 'gmail');
      const updatedPermissions = JSON.parse(stored.permissions);
      assert.ok(updatedPermissions.includes('readonly'), 'Should keep readonly permission');
      assert.ok(updatedPermissions.includes('compose'), 'Should add compose permission');
    });

    // Test: Gmail permission scopes
    await ctx.test('should handle different Gmail permission scopes', async () => {
      const user = await createTestUser(db, { subscription_tier: 'professional' });

      const permissionSets = [
        ['readonly'],
        ['readonly', 'compose'],
        ['readonly', 'compose', 'send'],
        ['readonly', 'send', 'modify'],
      ];

      for (const permissions of permissionSets) {
        const { tokens } = await mockOAuth.getToken(`code_${permissions.join('_')}`);
        await storeMockTokens(db, user.id, 'gmail', tokens, permissions);

        const stored = await getStoredTokens(db, user.id, 'gmail');
        const storedPerms = JSON.parse(stored.permissions);

        permissions.forEach(perm => {
          assert.ok(storedPerms.includes(perm), `Should include ${perm} permission`);
        });
      }
    });

    // Test: Cross-service OAuth isolation
    await ctx.test('should isolate Calendar and Gmail OAuth tokens', async () => {
      const user = await createTestUser(db, { subscription_tier: 'professional' });

      // Connect both services
      const { tokens: calTokens } = await mockOAuth.getToken('calendar_code');
      const { tokens: gmailTokens } = await mockOAuth.getToken('gmail_code');

      await storeMockTokens(db, user.id, 'google_calendar', calTokens);
      await storeMockTokens(db, user.id, 'gmail', gmailTokens, ['readonly']);

      // Verify both are stored independently
      const calStored = await getStoredTokens(db, user.id, 'google_calendar');
      const gmailStored = await getStoredTokens(db, user.id, 'gmail');

      assert.ok(calStored, 'Should store calendar tokens');
      assert.ok(gmailStored, 'Should store gmail tokens');
      assert.ok(calStored.access_token !== gmailStored.access_token, 'Should have different tokens');
    });

    // Test: Token expiry detection
    await ctx.test('should detect token expiry correctly', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });
      const { tokens } = await mockOAuth.getToken('valid_code');

      // Store token expiring soon (4 minutes)
      const expiringSoon = {
        ...tokens,
        expiry_date: Date.now() + 4 * 60 * 1000,
      };

      await storeMockTokens(db, user.id, 'google_calendar', expiringSoon);
      const stored = await getStoredTokens(db, user.id, 'google_calendar');

      const expiresAt = new Date(stored.token_expires_at);
      const now = new Date();
      const bufferTime = 5 * 60 * 1000; // 5 minutes

      const needsRefresh = now >= new Date(expiresAt.getTime() - bufferTime);
      assert.strictEqual(needsRefresh, true, 'Should detect token needs refresh');
    });

    // Test: Multiple user token isolation
    await ctx.test('should isolate tokens between different users', async () => {
      const user1 = await createTestUser(db, { subscription_tier: 'personal' });
      const user2 = await createTestUser(db, { subscription_tier: 'professional' });

      const { tokens: tokens1 } = await mockOAuth.getToken('user1_code');
      const { tokens: tokens2 } = await mockOAuth.getToken('user2_code');

      await storeMockTokens(db, user1.id, 'google_calendar', tokens1);
      await storeMockTokens(db, user2.id, 'google_calendar', tokens2);

      const stored1 = await getStoredTokens(db, user1.id, 'google_calendar');
      const stored2 = await getStoredTokens(db, user2.id, 'google_calendar');

      assert.ok(stored1.access_token !== stored2.access_token, 'Should have different tokens');
      assert.strictEqual(stored1.access_token, tokens1.access_token, 'User 1 should have correct token');
      assert.strictEqual(stored2.access_token, tokens2.access_token, 'User 2 should have correct token');
    });

    // Test: Token update on reconnection
    await ctx.test('should update tokens on reconnection', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });

      // First connection
      const { tokens: firstTokens } = await mockOAuth.getToken('first_code');
      await storeMockTokens(db, user.id, 'gmail', firstTokens, ['readonly']);

      // Reconnect with new permissions
      const { tokens: secondTokens } = await mockOAuth.getToken('second_code');
      await storeMockTokens(db, user.id, 'gmail', secondTokens, ['readonly', 'send']);

      const stored = await getStoredTokens(db, user.id, 'gmail');
      assert.strictEqual(stored.access_token, secondTokens.access_token, 'Should update to new token');

      const permissions = JSON.parse(stored.permissions);
      assert.ok(permissions.includes('send'), 'Should have updated permissions');
    });

    // Test: Last sync timestamp tracking
    await ctx.test('should track last sync timestamp', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });
      const { tokens } = await mockOAuth.getToken('valid_code');

      await storeMockTokens(db, user.id, 'google_calendar', tokens);

      // Update last sync
      await db.execute({
        sql: `
          UPDATE calendar_integrations
          SET last_sync = CURRENT_TIMESTAMP
          WHERE user_id = ? AND provider = 'google'
        `,
        args: [user.id],
      });

      const result = await db.execute({
        sql: 'SELECT last_sync FROM calendar_integrations WHERE user_id = ? AND provider = ?',
        args: [user.id, 'google'],
      });

      assert.ok(result.rows[0].last_sync, 'Should have last sync timestamp');
    });

    // Test: OAuth state parameter validation
    await ctx.test('should include and validate OAuth state parameter', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });
      const state = JSON.stringify({ userId: user.id, nonce: 'random_nonce' });

      const authUrl = mockOAuth.generateAuthUrl({
        access_type: 'offline',
        scope: ['https://www.googleapis.com/auth/calendar'],
        state,
      });

      assert.ok(authUrl.includes('state='), 'Should include state parameter');

      // Verify state can be decoded
      const urlParams = new URLSearchParams(authUrl.split('?')[1]);
      const decodedState = JSON.parse(urlParams.get('state'));

      assert.strictEqual(decodedState.userId, user.id, 'State should contain user ID');
      assert.ok(decodedState.nonce, 'State should contain nonce');
    });

    // Test: Scope verification
    await ctx.test('should request correct OAuth scopes', async () => {
      // Calendar readonly (free tier)
      const readonlyUrl = mockOAuth.generateAuthUrl({
        scope: ['https://www.googleapis.com/auth/calendar.readonly'],
      });
      assert.ok(readonlyUrl.includes('calendar.readonly'), 'Should request readonly scope');

      // Calendar read/write (personal+ tier)
      const readwriteUrl = mockOAuth.generateAuthUrl({
        scope: [
          'https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events',
        ],
      });
      assert.ok(readwriteUrl.includes('calendar.readonly'), 'Should request readonly scope');
      assert.ok(readwriteUrl.includes('calendar.events'), 'Should request events scope');
    });

    // Test: Error recovery on token refresh failure
    await ctx.test('should handle token refresh failure gracefully', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });

      // Store expired token with invalid refresh token
      const expiredTokens = {
        access_token: 'expired_access',
        refresh_token: 'invalid_refresh_token',
        expiry_date: Date.now() - 3600000,
      };

      await storeMockTokens(db, user.id, 'google_calendar', expiredTokens);
      mockOAuth.setCredentials(expiredTokens);

      // Attempt refresh should fail
      await assertThrows(
        async () => {
          await mockOAuth.refreshAccessToken();
        },
        'Invalid refresh token'
      );

      // User should need to reconnect
      const stored = await getStoredTokens(db, user.id, 'google_calendar');
      assert.ok(stored.refresh_token, 'Should still have stored refresh token');
    });
  });
}
