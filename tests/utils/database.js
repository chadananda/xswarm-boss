/**
 * Database Test Utilities
 * Helper functions for managing test database state
 */

import { createClient } from '@libsql/client';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Create a database client for testing
 */
export function createTestDb() {
  const url = process.env.TURSO_DATABASE_URL || process.env.TEST_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN || process.env.TEST_AUTH_TOKEN;

  if (!url) {
    throw new Error('TEST_DATABASE_URL or TURSO_DATABASE_URL must be set');
  }

  return createClient({
    url,
    authToken: authToken || undefined,
  });
}

/**
 * Run a SQL migration file
 */
export async function runMigration(db, migrationName) {
  const migrationPath = join(
    __dirname,
    '../../packages/server/migrations',
    migrationName
  );

  const sql = readFileSync(migrationPath, 'utf-8');

  // Split by semicolon and execute each statement
  const statements = sql
    .split(';')
    .map(s => s.trim())
    .filter(s => s.length > 0 && !s.startsWith('--'));

  for (const statement of statements) {
    await db.execute(statement);
  }
}

/**
 * Setup test database with all migrations
 */
export async function setupTestDatabase(db) {
  // Run migrations in order
  const migrations = [
    'schema.sql',
    'auth.sql',
    'add-subscription-tier.sql',
    'teams.sql',
    'email-marketing.sql',
    'suggestions.sql',
    'buzz.sql',
  ];

  for (const migration of migrations) {
    try {
      await runMigration(db, migration);
    } catch (error) {
      // Ignore errors for already existing tables
      if (!error.message.includes('already exists')) {
        throw error;
      }
    }
  }
}

/**
 * Clear all test data from database
 */
export async function clearTestData(db) {
  // Delete in reverse order of dependencies
  const tables = [
    'email_sends',
    'user_email_subscriptions',
    'email_sequences',
    'email_campaigns',
    'suggestion_votes',
    'suggestions',
    'buzz_interactions',
    'buzz_listings',
    'team_invitations',
    'team_members',
    'teams',
    'users',
  ];

  for (const table of tables) {
    try {
      await db.execute(`DELETE FROM ${table}`);
    } catch (error) {
      // Ignore if table doesn't exist
      if (!error.message.includes('no such table')) {
        console.warn(`Warning: Could not clear table ${table}:`, error.message);
      }
    }
  }
}

/**
 * Create a test user
 */
export async function createTestUser(db, userData = {}) {
  const id = userData.id || `user_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const email = userData.email || `test_${id}@example.com`;
  const name = userData.name || `Test User ${id}`;
  const subscriptionTier = userData.subscription_tier || 'free';

  const result = await db.execute({
    sql: `
      INSERT INTO users (id, email, name, phone, subscription_tier, email_verified, created_at)
      VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
      RETURNING *
    `,
    args: [
      id,
      email,
      name,
      userData.phone || null,
      subscriptionTier,
      userData.email_verified !== false ? 1 : 0,
    ],
  });

  return result.rows[0];
}

/**
 * Create a test team
 */
export async function createTestTeam(db, ownerId, teamData = {}) {
  const id = teamData.id || `team_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  const name = teamData.name || `Test Team ${id}`;
  const subscriptionTier = teamData.subscription_tier || 'ai_project_manager';
  const maxMembers = teamData.max_members || 10;

  const result = await db.execute({
    sql: `
      INSERT INTO teams (id, name, description, owner_id, subscription_tier, max_members, created_at)
      VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
      RETURNING *
    `,
    args: [id, name, teamData.description || null, ownerId, subscriptionTier, maxMembers],
  });

  // Add owner as team member
  await db.execute({
    sql: `
      INSERT INTO team_members (id, team_id, user_id, role, joined_at)
      VALUES (?, ?, ?, 'owner', datetime('now'))
    `,
    args: [`member_${id}_owner`, id, ownerId],
  });

  return result.rows[0];
}

/**
 * Create a test suggestion
 */
export async function createTestSuggestion(db, userId, suggestionData = {}) {
  const id = suggestionData.id || `sugg_${Date.now()}_${Math.random().toString(36).slice(2)}`;

  const result = await db.execute({
    sql: `
      INSERT INTO suggestions (
        id, user_id, email, category, title, description,
        priority, status, upvotes, created_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
      RETURNING *
    `,
    args: [
      id,
      userId,
      suggestionData.email || null,
      suggestionData.category || 'feature_request',
      suggestionData.title || 'Test Suggestion',
      suggestionData.description || 'This is a test suggestion description.',
      suggestionData.priority || 'medium',
      suggestionData.status || 'new',
      suggestionData.upvotes || 0,
    ],
  });

  return result.rows[0];
}

/**
 * Create a test buzz listing
 */
export async function createTestBuzzListing(db, userId, listingData = {}) {
  const id = listingData.id || `buzz_${Date.now()}_${Math.random().toString(36).slice(2)}`;

  const result = await db.execute({
    sql: `
      INSERT INTO buzz_listings (
        id, user_id, team_id, title, description, category,
        url, image_url, price_type, price_range, tags,
        status, featured, view_count, click_count,
        expires_at, created_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
      RETURNING *
    `,
    args: [
      id,
      userId,
      listingData.team_id || null,
      listingData.title || 'Test Listing',
      listingData.description || 'This is a test listing description.',
      listingData.category || 'saas',
      listingData.url || 'https://example.com',
      listingData.image_url || null,
      listingData.price_type || 'freemium',
      listingData.price_range || '10_50',
      listingData.tags || '[]',
      listingData.status || 'approved',
      listingData.featured ? 1 : 0,
      listingData.view_count || 0,
      listingData.click_count || 0,
      listingData.expires_at || null,
    ],
  });

  return result.rows[0];
}

/**
 * Get user by ID
 */
export async function getUser(db, userId) {
  const result = await db.execute({
    sql: 'SELECT * FROM users WHERE id = ?',
    args: [userId],
  });

  return result.rows[0] || null;
}

/**
 * Get user by email
 */
export async function getUserByEmail(db, email) {
  const result = await db.execute({
    sql: 'SELECT * FROM users WHERE email = ?',
    args: [email],
  });

  return result.rows[0] || null;
}

/**
 * Count records in a table
 */
export async function countRecords(db, tableName, whereClause = '') {
  const sql = whereClause
    ? `SELECT COUNT(*) as count FROM ${tableName} WHERE ${whereClause}`
    : `SELECT COUNT(*) as count FROM ${tableName}`;

  const result = await db.execute(sql);
  return result.rows[0].count;
}

/**
 * Cleanup helper - runs before/after tests
 */
export async function withCleanDatabase(testFn) {
  const db = createTestDb();

  try {
    // Setup database
    await setupTestDatabase(db);

    // Clear existing test data
    await clearTestData(db);

    // Run test
    await testFn(db);
  } finally {
    // Cleanup after test
    await clearTestData(db);
    db.close();
  }
}

export default {
  createTestDb,
  runMigration,
  setupTestDatabase,
  clearTestData,
  createTestUser,
  createTestTeam,
  createTestSuggestion,
  createTestBuzzListing,
  getUser,
  getUserByEmail,
  countRecords,
  withCleanDatabase,
};
