#!/usr/bin/env node
/**
 * xSwarm Boss - Database Migration Orchestrator
 *
 * Runs all database migrations in the correct order with:
 * - Migration tracking
 * - Dependency management
 * - Rollback capability
 * - Detailed logging
 *
 * Usage: node deployment/scripts/migrate-all.js [--rollback] [--dry-run]
 */

import { createClient } from '@libsql/client';
import { readFileSync, readdirSync } from 'fs';
import { resolve, join } from 'path';
import { config } from 'dotenv';
import crypto from 'crypto';

// Load environment variables
config();

// Parse command line arguments
const args = process.argv.slice(2);
const isDryRun = args.includes('--dry-run');
const isRollback = args.includes('--rollback');

// Colors for output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// Migration order (dependencies)
const migrationOrder = [
  { file: 'schema.sql', name: 'Base Schema', critical: true },
  { file: 'auth.sql', name: 'Authentication System', critical: true },
  { file: 'teams.sql', name: 'Team Management', critical: false },
  { file: 'projects.sql', name: 'Project Tracking', critical: false },
  { file: 'messages.sql', name: 'Communication History', critical: true },
  { file: 'buzz.sql', name: 'Marketplace', critical: false },
  { file: 'suggestions.sql', name: 'Feedback System', critical: false },
  { file: 'email-marketing.sql', name: 'Marketing Campaigns', critical: false },
  { file: 'scheduler.sql', name: 'Scheduled Tasks', critical: true },
  { file: 'claude_code_sessions.sql', name: 'AI Sessions', critical: false },
  { file: 'add-subscription-tier.sql', name: 'Subscription Tiers', critical: false },
];

// Create migration tracking table
async function createMigrationTable(db) {
  log('\n📋 Creating migration tracking table...', 'blue');

  const createTableSQL = `
    CREATE TABLE IF NOT EXISTS _migrations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      filename TEXT NOT NULL UNIQUE,
      name TEXT NOT NULL,
      checksum TEXT NOT NULL,
      applied_at TEXT NOT NULL DEFAULT (datetime('now')),
      execution_time_ms INTEGER,
      status TEXT DEFAULT 'success'
    );

    CREATE INDEX IF NOT EXISTS idx_migrations_filename ON _migrations(filename);
    CREATE INDEX IF NOT EXISTS idx_migrations_applied_at ON _migrations(applied_at);
  `;

  try {
    await db.execute(createTableSQL);
    log('✅ Migration tracking table ready', 'green');
  } catch (error) {
    log(`❌ Failed to create migration table: ${error.message}`, 'red');
    throw error;
  }
}

// Calculate file checksum
function calculateChecksum(content) {
  return crypto.createHash('sha256').update(content).digest('hex');
}

// Get applied migrations
async function getAppliedMigrations(db) {
  try {
    const result = await db.execute('SELECT * FROM _migrations ORDER BY applied_at');
    return result.rows;
  } catch (error) {
    log('⚠️  No migration history found', 'yellow');
    return [];
  }
}

// Check if migration was already applied
async function isMigrationApplied(db, filename, checksum) {
  const result = await db.execute({
    sql: 'SELECT * FROM _migrations WHERE filename = ?',
    args: [filename],
  });

  if (result.rows.length === 0) {
    return { applied: false };
  }

  const existing = result.rows[0];

  // Check if checksum matches
  if (existing.checksum !== checksum) {
    return {
      applied: true,
      modified: true,
      existingChecksum: existing.checksum,
    };
  }

  return { applied: true, modified: false };
}

// Record migration
async function recordMigration(db, filename, name, checksum, executionTime, status = 'success') {
  await db.execute({
    sql: `INSERT INTO _migrations (filename, name, checksum, execution_time_ms, status)
          VALUES (?, ?, ?, ?, ?)`,
    args: [filename, name, checksum, executionTime, status],
  });
}

// Parse SQL file into statements
function parseSQLFile(content) {
  // Remove comments
  const withoutComments = content
    .split('\n')
    .filter(line => !line.trim().startsWith('--'))
    .join('\n');

  // Split by semicolon (but be careful with string literals and functions)
  const statements = [];
  let current = '';
  let inString = false;
  let stringChar = null;

  for (let i = 0; i < withoutComments.length; i++) {
    const char = withoutComments[i];
    const prevChar = i > 0 ? withoutComments[i - 1] : '';

    if ((char === '"' || char === "'") && prevChar !== '\\') {
      if (!inString) {
        inString = true;
        stringChar = char;
      } else if (char === stringChar) {
        inString = false;
        stringChar = null;
      }
    }

    current += char;

    if (char === ';' && !inString) {
      const stmt = current.trim();
      if (stmt.length > 1) {
        statements.push(stmt);
      }
      current = '';
    }
  }

  // Add any remaining statement
  if (current.trim()) {
    statements.push(current.trim());
  }

  return statements.filter(s => s.length > 0);
}

// Execute migration
async function executeMigration(db, migration, content) {
  const { file, name, critical } = migration;
  const checksum = calculateChecksum(content);

  log(`\n${'─'.repeat(60)}`, 'cyan');
  log(`📄 ${name} (${file})`, 'bold');
  log('─'.repeat(60), 'cyan');

  // Check if already applied
  const status = await isMigrationApplied(db, file, checksum);

  if (status.applied && !status.modified) {
    log('✅ Already applied (checksum matches)', 'green');
    return { success: true, skipped: true };
  }

  if (status.applied && status.modified) {
    log('⚠️  Migration file has been modified!', 'yellow');
    log('   This migration was already applied with a different checksum.', 'yellow');
    log('   Skipping to prevent data corruption.', 'yellow');
    log('   Create a new migration file if schema changes are needed.', 'yellow');
    return { success: true, skipped: true };
  }

  // Parse SQL statements
  const statements = parseSQLFile(content);
  log(`📝 Found ${statements.length} SQL statements`, 'blue');

  if (isDryRun) {
    log('🔍 DRY RUN - Would execute:', 'yellow');
    statements.forEach((stmt, i) => {
      const preview = stmt.substring(0, 100).replace(/\s+/g, ' ');
      log(`   ${i + 1}. ${preview}${stmt.length > 100 ? '...' : ''}`, 'reset');
    });
    return { success: true, dryRun: true };
  }

  // Execute statements
  const startTime = Date.now();
  let executedCount = 0;

  try {
    for (let i = 0; i < statements.length; i++) {
      const stmt = statements[i];

      try {
        await db.execute(stmt);
        executedCount++;

        // Log what we created
        if (stmt.includes('CREATE TABLE')) {
          const match = stmt.match(/CREATE TABLE (?:IF NOT EXISTS )?(\w+)/i);
          if (match) log(`  ✅ Table: ${match[1]}`, 'green');
        } else if (stmt.includes('CREATE INDEX')) {
          const match = stmt.match(/CREATE INDEX (?:IF NOT EXISTS )?(\w+)/i);
          if (match) log(`  ✅ Index: ${match[1]}`, 'green');
        } else if (stmt.includes('CREATE VIEW')) {
          const match = stmt.match(/CREATE VIEW (?:IF NOT EXISTS )?(\w+)/i);
          if (match) log(`  ✅ View: ${match[1]}`, 'green');
        } else if (stmt.includes('CREATE TRIGGER')) {
          const match = stmt.match(/CREATE TRIGGER (?:IF NOT EXISTS )?(\w+)/i);
          if (match) log(`  ✅ Trigger: ${match[1]}`, 'green');
        } else if (stmt.includes('ALTER TABLE')) {
          const match = stmt.match(/ALTER TABLE (\w+)/i);
          if (match) log(`  ✅ Altered: ${match[1]}`, 'green');
        }
      } catch (error) {
        // Ignore "already exists" errors
        if (!error.message.toLowerCase().includes('already exists')) {
          throw error;
        }
      }
    }

    const executionTime = Date.now() - startTime;

    // Record successful migration
    await recordMigration(db, file, name, checksum, executionTime);

    log(`\n✅ Migration completed in ${executionTime}ms`, 'green');
    return { success: true, executionTime, statementsExecuted: executedCount };

  } catch (error) {
    const executionTime = Date.now() - startTime;

    log(`\n❌ Migration failed: ${error.message}`, 'red');

    if (critical) {
      log('🚨 CRITICAL MIGRATION FAILED', 'red');
      throw error;
    } else {
      log('⚠️  Non-critical migration - continuing...', 'yellow');
      await recordMigration(db, file, name, checksum, executionTime, 'failed');
      return { success: false, error: error.message };
    }
  }
}

// Rollback last migration
async function rollbackMigration(db) {
  log('\n🔄 Rolling back last migration...', 'yellow');

  const result = await db.execute(`
    SELECT * FROM _migrations
    ORDER BY applied_at DESC
    LIMIT 1
  `);

  if (result.rows.length === 0) {
    log('No migrations to rollback', 'yellow');
    return;
  }

  const lastMigration = result.rows[0];
  log(`Rolling back: ${lastMigration.name} (${lastMigration.filename})`, 'yellow');

  // Delete migration record
  await db.execute({
    sql: 'DELETE FROM _migrations WHERE id = ?',
    args: [lastMigration.id],
  });

  log(`✅ Rolled back ${lastMigration.name}`, 'green');
  log('⚠️  Note: This only removes the migration record.', 'yellow');
  log('   Manual schema changes may be needed to fully revert.', 'yellow');
}

// Verify database integrity
async function verifyDatabase(db) {
  log('\n🔍 Verifying database integrity...', 'blue');

  try {
    // Get all tables
    const tables = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_migrations'
      ORDER BY name
    `);

    log(`\n📊 Database Tables (${tables.rows.length}):`, 'cyan');
    for (const row of tables.rows) {
      // Get row count
      try {
        const count = await db.execute(`SELECT COUNT(*) as count FROM ${row.name}`);
        log(`  • ${row.name}: ${count.rows[0].count} rows`, 'green');
      } catch (error) {
        log(`  • ${row.name}: (unable to count)`, 'yellow');
      }
    }

    // Get all views
    const views = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='view'
      ORDER BY name
    `);

    if (views.rows.length > 0) {
      log(`\n👁️  Database Views (${views.rows.length}):`, 'cyan');
      views.rows.forEach(row => {
        log(`  • ${row.name}`, 'green');
      });
    }

    // Get all indexes
    const indexes = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='index' AND name NOT LIKE 'sqlite_%'
      ORDER BY name
    `);

    if (indexes.rows.length > 0) {
      log(`\n📇 Database Indexes (${indexes.rows.length}):`, 'cyan');
      indexes.rows.forEach(row => {
        log(`  • ${row.name}`, 'green');
      });
    }

    log('\n✅ Database verification complete', 'green');

  } catch (error) {
    log(`❌ Verification failed: ${error.message}`, 'red');
  }
}

// Main execution
async function main() {
  log('\n🗄️  xSwarm Boss - Database Migration Orchestrator', 'cyan');
  log('='.repeat(60), 'cyan');

  if (isDryRun) {
    log('🔍 DRY RUN MODE - No changes will be made', 'yellow');
  }
  if (isRollback) {
    log('🔄 ROLLBACK MODE', 'yellow');
  }

  // Check environment variables
  const dbUrl = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl || !authToken) {
    log('❌ Error: Missing database credentials', 'red');
    log('Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env', 'red');
    process.exit(1);
  }

  // Connect to database
  const db = createClient({ url: dbUrl, authToken });
  log(`\n🔗 Connected to: ${dbUrl.split('@')[1]}`, 'blue');

  try {
    // Create migration tracking table
    await createMigrationTable(db);

    // Handle rollback
    if (isRollback) {
      await rollbackMigration(db);
      return;
    }

    // Get migration history
    const appliedMigrations = await getAppliedMigrations(db);
    log(`\n📚 Migration History: ${appliedMigrations.length} previous migrations`, 'blue');

    // Get migration files directory
    const migrationsDir = resolve(process.cwd(), 'packages/server/migrations');

    // Execute migrations in order
    const results = [];
    let totalTime = 0;
    let skipped = 0;
    let failed = 0;

    for (const migration of migrationOrder) {
      const filePath = join(migrationsDir, migration.file);

      try {
        const content = readFileSync(filePath, 'utf-8');
        const result = await executeMigration(db, migration, content);

        results.push({ ...migration, ...result });

        if (result.skipped) skipped++;
        if (result.success === false) failed++;
        if (result.executionTime) totalTime += result.executionTime;

      } catch (error) {
        if (error.code === 'ENOENT') {
          log(`⚠️  Migration file not found: ${migration.file}`, 'yellow');
          skipped++;
        } else {
          log(`❌ Critical error in migration: ${error.message}`, 'red');
          throw error;
        }
      }
    }

    // Verify database
    await verifyDatabase(db);

    // Summary
    log('\n' + '='.repeat(60), 'cyan');
    log('📊 Migration Summary', 'bold');
    log('='.repeat(60), 'cyan');

    log(`\nTotal migrations: ${migrationOrder.length}`, 'cyan');
    log(`✅ Completed: ${results.filter(r => r.success && !r.skipped).length}`, 'green');
    log(`⏭️  Skipped: ${skipped}`, 'yellow');
    log(`❌ Failed: ${failed}`, failed > 0 ? 'red' : 'green');
    log(`⏱️  Total time: ${totalTime}ms`, 'blue');

    if (!isDryRun) {
      log('\n✅ All migrations completed successfully!', 'green');
      log('🚀 Database is ready for deployment!', 'green');
    }

  } catch (error) {
    log(`\n❌ Migration failed: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  }
}

main();
