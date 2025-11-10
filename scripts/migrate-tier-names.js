#!/usr/bin/env node

/**
 * Tier Name Migration Script
 *
 * Migrates subscription tier names from legacy to standardized naming:
 * - ai_buddy → free
 * - ai_secretary → personal
 * - ai_project_manager → professional
 * - ai_cto → enterprise
 *
 * Usage:
 *   node scripts/migrate-tier-names.js [--dry-run] [--rollback]
 *
 * Options:
 *   --dry-run   Show what would be migrated without making changes
 *   --rollback  Reverse the migration (new names → old names)
 */

import { createClient } from '@libsql/client';
import { config } from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables from project root
const projectRoot = join(__dirname, '..');
config({ path: join(projectRoot, '.env') });

// Tier name mappings
const TIER_MIGRATIONS = {
  forward: {
    ai_buddy: 'free',
    ai_secretary: 'personal',
    ai_project_manager: 'professional',
    ai_cto: 'enterprise',
    admin: 'admin', // unchanged
  },
  backward: {
    free: 'ai_buddy',
    personal: 'ai_secretary',
    professional: 'ai_project_manager',
    enterprise: 'ai_cto',
    admin: 'admin', // unchanged
  },
};

// Parse command line arguments
const args = process.argv.slice(2);
const isDryRun = args.includes('--dry-run');
const isRollback = args.includes('--rollback');
const mapping = isRollback ? TIER_MIGRATIONS.backward : TIER_MIGRATIONS.forward;

/**
 * Create database client
 */
function createDbClient() {
  const url = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!url || !authToken) {
    console.error('❌ Missing required environment variables:');
    console.error('   TURSO_DATABASE_URL');
    console.error('   TURSO_AUTH_TOKEN');
    process.exit(1);
  }

  console.log(`🔗 Connecting to: ${url.substring(0, 30)}...`);
  return createClient({ url, authToken });
}

/**
 * Get tier migration statistics
 */
async function getTierStats(db) {
  const result = await db.execute(`
    SELECT
      subscription_tier,
      COUNT(*) as count
    FROM users
    WHERE subscription_tier IS NOT NULL
    GROUP BY subscription_tier
    ORDER BY count DESC
  `);

  return result.rows.map(row => ({
    tier: row.subscription_tier,
    count: Number(row.count),
    newTier: mapping[row.subscription_tier] || row.subscription_tier,
  }));
}

/**
 * Migrate a single tier
 */
async function migrateTier(db, oldTier, newTier, dryRun = false) {
  // Get affected users
  const countResult = await db.execute({
    sql: 'SELECT COUNT(*) as count FROM users WHERE subscription_tier = ?',
    args: [oldTier],
  });

  const count = Number(countResult.rows[0].count);

  if (count === 0) {
    console.log(`   ⏭️  ${oldTier} → ${newTier}: No users found`);
    return { updated: 0, skipped: 0 };
  }

  if (dryRun) {
    console.log(`   🔍 ${oldTier} → ${newTier}: Would update ${count} users`);
    return { updated: 0, skipped: count };
  }

  // Perform migration
  const updateResult = await db.execute({
    sql: 'UPDATE users SET subscription_tier = ?, updated_at = ? WHERE subscription_tier = ?',
    args: [newTier, new Date().toISOString(), oldTier],
  });

  console.log(`   ✅ ${oldTier} → ${newTier}: Updated ${count} users`);
  return { updated: count, skipped: 0 };
}

/**
 * Migrate team subscription tiers
 */
async function migrateTeamTiers(db, dryRun = false) {
  console.log('\n📦 Migrating team subscription tiers...');

  const stats = await db.execute(`
    SELECT
      subscription_tier,
      COUNT(*) as count
    FROM teams
    WHERE subscription_tier IS NOT NULL
    GROUP BY subscription_tier
  `);

  let totalUpdated = 0;
  let totalSkipped = 0;

  for (const row of stats.rows) {
    const oldTier = row.subscription_tier;
    const newTier = mapping[oldTier] || oldTier;
    const count = Number(row.count);

    if (oldTier === newTier) {
      console.log(`   ⏭️  ${oldTier}: Already using new name (${count} teams)`);
      totalSkipped += count;
      continue;
    }

    if (dryRun) {
      console.log(`   🔍 ${oldTier} → ${newTier}: Would update ${count} teams`);
      totalSkipped += count;
    } else {
      await db.execute({
        sql: 'UPDATE teams SET subscription_tier = ?, updated_at = ? WHERE subscription_tier = ?',
        args: [newTier, new Date().toISOString(), oldTier],
      });
      console.log(`   ✅ ${oldTier} → ${newTier}: Updated ${count} teams`);
      totalUpdated += count;
    }
  }

  return { updated: totalUpdated, skipped: totalSkipped };
}

/**
 * Main migration function
 */
async function migrate() {
  console.log('🚀 Tier Name Migration Script\n');
  console.log(`Mode: ${isRollback ? 'ROLLBACK' : 'FORWARD'}`);
  console.log(`Dry Run: ${isDryRun ? 'YES' : 'NO'}\n`);

  const db = createDbClient();

  try {
    // Show current tier distribution
    console.log('📊 Current tier distribution:');
    const stats = await getTierStats(db);

    if (stats.length === 0) {
      console.log('   No users found in database');
      return;
    }

    stats.forEach(({ tier, count, newTier }) => {
      const arrow = tier === newTier ? '  ' : '→';
      const newTierDisplay = tier === newTier ? '' : ` ${arrow} ${newTier}`;
      console.log(`   ${tier}: ${count} users${newTierDisplay}`);
    });

    console.log('\n📝 Starting migration...');

    let totalUpdated = 0;
    let totalSkipped = 0;

    // Migrate each tier
    for (const [oldTier, newTier] of Object.entries(mapping)) {
      if (oldTier === newTier) {
        // Count users that don't need migration
        const result = await db.execute({
          sql: 'SELECT COUNT(*) as count FROM users WHERE subscription_tier = ?',
          args: [oldTier],
        });
        const count = Number(result.rows[0].count);
        if (count > 0) {
          console.log(`   ⏭️  ${oldTier}: Already using new name (${count} users)`);
          totalSkipped += count;
        }
        continue;
      }

      const { updated, skipped } = await migrateTier(db, oldTier, newTier, isDryRun);
      totalUpdated += updated;
      totalSkipped += skipped;
    }

    // Migrate team tiers
    const teamResults = await migrateTeamTiers(db, isDryRun);
    totalUpdated += teamResults.updated;
    totalSkipped += teamResults.skipped;

    // Show summary
    console.log('\n📈 Migration Summary:');
    console.log(`   Updated: ${totalUpdated} records`);
    console.log(`   Skipped: ${totalSkipped} records`);

    if (isDryRun) {
      console.log('\n💡 This was a dry run. No changes were made.');
      console.log('   Run without --dry-run to apply changes.');
    } else if (totalUpdated > 0) {
      console.log('\n✅ Migration completed successfully!');

      if (isRollback) {
        console.log('\n⚠️  Database has been rolled back to legacy tier names.');
      } else {
        console.log('\n🎉 All tier names have been updated to the new standardized format!');
      }
    } else {
      console.log('\n✅ All tier names are already up to date!');
    }

  } catch (error) {
    console.error('\n❌ Migration failed:', error.message);
    console.error('\nStack trace:', error.stack);
    process.exit(1);
  }
}

// Run migration
migrate();
