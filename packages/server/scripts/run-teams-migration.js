#!/usr/bin/env node
/**
 * Team Management Migration Script
 *
 * Runs all necessary migrations to enable team management features
 */

import { createClient } from '@libsql/client';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('Team Management Migration Script\n');
console.log('='.repeat(50));

async function runMigration() {
  // Get database connection details from environment
  const dbUrl = process.env.TURSO_DATABASE_URL || process.env.DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl) {
    console.error('\n❌ Error: Database URL not found');
    console.error('Set TURSO_DATABASE_URL or DATABASE_URL environment variable');
    process.exit(1);
  }

  console.log('\nConnecting to database...');
  console.log(`URL: ${dbUrl.substring(0, 30)}...`);

  const db = createClient({
    url: dbUrl,
    authToken: authToken,
  });

  try {
    // Test connection
    await db.execute('SELECT 1');
    console.log('✓ Connected successfully\n');

    // 1. Check if subscription_tier column exists
    console.log('1. Checking users table...');
    try {
      const result = await db.execute('PRAGMA table_info(users)');
      const hasSubscriptionTier = result.rows.some(row => row.name === 'subscription_tier');

      if (!hasSubscriptionTier) {
        console.log('   Adding subscription_tier column...');
        const subscriptionSQL = fs.readFileSync(
          path.join(__dirname, '../migrations/add-subscription-tier.sql'),
          'utf-8'
        );
        await db.executeMultiple(subscriptionSQL);
        console.log('   ✓ Subscription tier column added');
      } else {
        console.log('   ✓ Subscription tier column already exists');
      }
    } catch (error) {
      console.error('   ❌ Error checking users table:', error.message);
      throw error;
    }

    // 2. Run teams migration
    console.log('\n2. Creating team management tables...');
    try {
      const teamsSQL = fs.readFileSync(
        path.join(__dirname, '../migrations/teams.sql'),
        'utf-8'
      );
      await db.executeMultiple(teamsSQL);
      console.log('   ✓ Team tables created');
    } catch (error) {
      if (error.message.includes('already exists')) {
        console.log('   ✓ Team tables already exist');
      } else {
        console.error('   ❌ Error creating team tables:', error.message);
        throw error;
      }
    }

    // 3. Verify tables exist
    console.log('\n3. Verifying installation...');
    const requiredTables = ['teams', 'team_members', 'team_invitations'];

    for (const table of requiredTables) {
      const result = await db.execute({
        sql: `SELECT name FROM sqlite_master WHERE type='table' AND name=?`,
        args: [table],
      });

      if (result.rows.length === 0) {
        throw new Error(`Table ${table} not found!`);
      }
      console.log(`   ✓ Table '${table}' exists`);
    }

    // 4. Verify views exist
    const requiredViews = ['teams_with_stats', 'team_members_with_details', 'active_team_invitations'];

    for (const view of requiredViews) {
      const result = await db.execute({
        sql: `SELECT name FROM sqlite_master WHERE type='view' AND name=?`,
        args: [view],
      });

      if (result.rows.length === 0) {
        console.log(`   ⚠️  View '${view}' not found (optional)`);
      } else {
        console.log(`   ✓ View '${view}' exists`);
      }
    }

    console.log('\n' + '='.repeat(50));
    console.log('✅ Migration completed successfully!\n');
    console.log('Team management features are now available.');
    console.log('\nNext steps:');
    console.log('1. Update user subscription tiers as needed');
    console.log('2. Deploy the updated server code');
    console.log('3. Test the /teams endpoints');
    console.log('\nSee TEAMS_API.md for API documentation.\n');

  } catch (error) {
    console.error('\n❌ Migration failed:', error.message);
    console.error('\nStack trace:', error.stack);
    process.exit(1);
  } finally {
    db.close();
  }
}

runMigration();
