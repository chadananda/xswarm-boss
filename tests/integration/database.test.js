/**
 * Integration Tests - Database
 * Tests for database operations, constraints, triggers, and views
 */

import { assert } from '../utils/assert.js';
import {
  createTestDb,
  setupTestDatabase,
  clearTestData,
  createTestUser,
  createTestTeam,
  createTestSuggestion,
  createTestBuzzListing,
  countRecords,
} from '../utils/database.js';

/**
 * Register test suite
 */
export default function (runner) {
  runner.describe('Database Integration', async ctx => {
    let db;

    ctx.beforeAll(async () => {
      db = createTestDb();
      await setupTestDatabase(db);
    });

    ctx.afterEach(async () => {
      await clearTestData(db);
    });

    ctx.afterAll(async () => {
      db.close();
    });

    // Test: Foreign Key Constraints
    await ctx.test('should enforce foreign key constraints', async () => {
      const user = await createTestUser(db);

      // Try to create team member for non-existent team
      try {
        await db.execute({
          sql: 'INSERT INTO team_members (id, team_id, user_id, role) VALUES (?, ?, ?, ?)',
          args: ['member_1', 'nonexistent_team', user.id, 'member'],
        });
        assert.fail('Should have thrown foreign key constraint error');
      } catch (error) {
        assert.ok(
          error.message.includes('FOREIGN KEY') || error.message.includes('constraint'),
          'Should throw foreign key constraint error'
        );
      }
    });

    // Test: Cascade Delete - User Deletion
    await ctx.test('should cascade delete user data', async () => {
      const user = await createTestUser(db);
      const team = await createTestTeam(db, user.id);

      // Create related data
      await createTestSuggestion(db, user.id);
      await createTestBuzzListing(db, user.id);

      // Count records before deletion
      const suggestionsBefore = await countRecords(db, 'suggestions');
      const buzzBefore = await countRecords(db, 'buzz_listings');

      assert.ok(suggestionsBefore > 0, 'Should have suggestions');
      assert.ok(buzzBefore > 0, 'Should have buzz listings');

      // Delete user
      await db.execute({
        sql: 'DELETE FROM users WHERE id = ?',
        args: [user.id],
      });

      // Check that related data was deleted
      const suggestionsAfter = await countRecords(db, 'suggestions');
      const buzzAfter = await countRecords(db, 'buzz_listings');
      const teamsAfter = await countRecords(db, 'teams');

      assert.strictEqual(suggestionsAfter, 0, 'Suggestions should be deleted');
      assert.strictEqual(buzzAfter, 0, 'Buzz listings should be deleted');
      assert.strictEqual(teamsAfter, 0, 'Teams should be deleted');
    });

    // Test: Unique Constraints
    await ctx.test('should enforce unique email constraint', async () => {
      const email = 'unique@test.com';

      await createTestUser(db, { email });

      // Try to create duplicate
      try {
        await createTestUser(db, { email });
        assert.fail('Should have thrown unique constraint error');
      } catch (error) {
        assert.ok(
          error.message.includes('UNIQUE') || error.message.includes('constraint'),
          'Should throw unique constraint error'
        );
      }
    });

    // Test: Check Constraints - Subscription Tier
    await ctx.test('should enforce subscription tier check constraint', async () => {
      try {
        await createTestUser(db, {
          subscription_tier: 'invalid_tier',
        });
        assert.fail('Should have thrown check constraint error');
      } catch (error) {
        assert.ok(
          error.message.includes('CHECK') || error.message.includes('constraint'),
          'Should throw check constraint error'
        );
      }
    });

    // Test: Auto-increment Triggers
    await ctx.test('should auto-update timestamps on modification', async () => {
      const user = await createTestUser(db);

      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 100));

      // Update user
      await db.execute({
        sql: 'UPDATE users SET name = ? WHERE id = ?',
        args: ['Updated Name', user.id],
      });

      // Check updated_at was set
      const result = await db.execute({
        sql: 'SELECT updated_at FROM users WHERE id = ?',
        args: [user.id],
      });

      assert.ok(result.rows[0].updated_at, 'Should have updated_at timestamp');
    });

    // Test: Vote Count Triggers
    await ctx.test('should auto-update suggestion upvote count', async () => {
      const user1 = await createTestUser(db);
      const user2 = await createTestUser(db);
      const suggestion = await createTestSuggestion(db, user1.id);

      // Initial upvote count should be 0
      assert.strictEqual(suggestion.upvotes, 0);

      // Add vote
      await db.execute({
        sql: 'INSERT INTO suggestion_votes (id, suggestion_id, user_id) VALUES (?, ?, ?)',
        args: ['vote_1', suggestion.id, user2.id],
      });

      // Check upvote count increased
      const result = await db.execute({
        sql: 'SELECT upvotes FROM suggestions WHERE id = ?',
        args: [suggestion.id],
      });

      assert.strictEqual(result.rows[0].upvotes, 1, 'Upvotes should be incremented');
    });

    // Test: View Queries - Active Buzz Listings
    await ctx.test('should query active buzz listings view', async () => {
      const user = await createTestUser(db);

      // Create approved listing
      await createTestBuzzListing(db, user.id, {
        status: 'approved',
        expires_at: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
      });

      // Create expired listing
      await createTestBuzzListing(db, user.id, {
        status: 'approved',
        expires_at: new Date(Date.now() - 86400000).toISOString(), // Yesterday
      });

      // Query view
      const result = await db.execute('SELECT * FROM active_buzz_listings');

      assert.strictEqual(result.rows.length, 1, 'Should only return active listing');
      assert.ok(
        result.rows[0].days_until_expiry > 0,
        'Should calculate days until expiry'
      );
    });

    // Test: View Queries - Campaign Analytics
    await ctx.test('should calculate campaign analytics', async () => {
      const user = await createTestUser(db);

      // Create campaign
      const campaignId = `campaign_${Date.now()}`;
      await db.execute({
        sql: `
          INSERT INTO email_campaigns (id, name, from_tier, to_tier, active)
          VALUES (?, ?, ?, ?, TRUE)
        `,
        args: [campaignId, 'Test Campaign', 'free', 'ai_secretary'],
      });

      // Enroll user
      const subscriptionId = `sub_${Date.now()}`;
      await db.execute({
        sql: `
          INSERT INTO user_email_subscriptions
          (id, user_id, campaign_id, status, unsubscribe_token)
          VALUES (?, ?, ?, 'active', ?)
        `,
        args: [subscriptionId, user.id, campaignId, `token_${Date.now()}`],
      });

      // Query analytics view
      const result = await db.execute({
        sql: 'SELECT * FROM campaign_analytics WHERE campaign_id = ?',
        args: [campaignId],
      });

      assert.strictEqual(result.rows.length, 1);
      assert.strictEqual(result.rows[0].total_enrolled, 1);
      assert.strictEqual(result.rows[0].active_subscribers, 1);
    });

    // Test: Index Performance
    await ctx.test('should use indexes for common queries', async () => {
      // Create multiple users
      for (let i = 0; i < 100; i++) {
        await createTestUser(db, {
          email: `user${i}@test.com`,
        });
      }

      const startTime = Date.now();

      // Query by email (should use index)
      await db.execute({
        sql: 'SELECT * FROM users WHERE email = ?',
        args: ['user50@test.com'],
      });

      const duration = Date.now() - startTime;

      // Query should be fast (<100ms)
      assert.ok(duration < 100, `Query should be fast, took ${duration}ms`);
    });

    // Test: Transaction Integrity
    await ctx.test('should maintain transaction integrity', async () => {
      const user = await createTestUser(db);

      // Start transaction
      const result = await db.batch(
        [
          {
            sql: 'INSERT INTO teams (id, name, owner_id, subscription_tier, max_members) VALUES (?, ?, ?, ?, ?)',
            args: ['team_1', 'Team 1', user.id, 'ai_project_manager', 10],
          },
          {
            sql: 'INSERT INTO team_members (id, team_id, user_id, role) VALUES (?, ?, ?, ?)',
            args: ['member_1', 'team_1', user.id, 'owner'],
          },
        ],
        'write'
      );

      // Both operations should succeed
      const teamCount = await countRecords(db, 'teams');
      const memberCount = await countRecords(db, 'team_members');

      assert.strictEqual(teamCount, 1, 'Team should be created');
      assert.strictEqual(memberCount, 1, 'Member should be created');
    });

    // Test: Full-Text Search
    await ctx.test('should support full-text search on suggestions', async () => {
      const user = await createTestUser(db);

      // Create suggestions with different text
      await createTestSuggestion(db, user.id, {
        title: 'Add dark mode feature',
        description: 'Users want dark mode for better eye comfort',
      });

      await createTestSuggestion(db, user.id, {
        title: 'Fix login bug',
        description: 'Users cannot login with social auth',
      });

      // Search for "dark mode"
      const result = await db.execute({
        sql: `
          SELECT s.* FROM suggestions_fts
          JOIN suggestions s ON suggestions_fts.id = s.id
          WHERE suggestions_fts MATCH ?
        `,
        args: ['dark mode'],
      });

      assert.strictEqual(result.rows.length, 1);
      assert.ok(result.rows[0].title.includes('dark mode'));
    });

    // Test: Suggestion Status Validation
    await ctx.test('should validate suggestion status values', async () => {
      const user = await createTestUser(db);

      try {
        await db.execute({
          sql: `
            INSERT INTO suggestions (id, user_id, category, title, description, status)
            VALUES (?, ?, ?, ?, ?, ?)
          `,
          args: [
            'sugg_1',
            user.id,
            'feature_request',
            'Test',
            'Test description',
            'invalid_status',
          ],
        });
        assert.fail('Should have thrown check constraint error');
      } catch (error) {
        assert.ok(
          error.message.includes('CHECK') || error.message.includes('constraint'),
          'Should validate status values'
        );
      }
    });
  });
}
