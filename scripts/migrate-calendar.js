#!/usr/bin/env node
/**
 * Calendar Migration Script
 *
 * Applies calendar integration schema to Turso database.
 */

import { createClient } from '@libsql/client';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { config } from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
config({ path: resolve(__dirname, '../.env') });

// Colors for output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

async function main() {
  log('\n📅 Calendar Integration - Database Migration', 'cyan');
  log('Applying calendar schema to Turso database...\n', 'cyan');

  // Check environment variables
  const dbUrl = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl || !authToken) {
    log('❌ Error: Missing database credentials', 'red');
    log('Please set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env', 'red');
    process.exit(1);
  }

  // Read schema file
  const schemaPath = resolve(__dirname, '../packages/server/migrations/calendar.sql');
  let schema;

  try {
    schema = readFileSync(schemaPath, 'utf-8');
    log(`✅ Loaded schema from ${schemaPath}`, 'green');
  } catch (error) {
    log(`❌ Error reading schema file: ${error.message}`, 'red');
    process.exit(1);
  }

  // Create database client
  const db = createClient({
    url: dbUrl,
    authToken: authToken,
  });

  log('🔗 Connecting to database...', 'blue');

  try {
    // Split schema into individual statements
    const statements = schema
      .split('\n')
      .filter((line) => !line.trim().startsWith('--') && line.trim() !== '')
      .join('\n')
      .split(';')
      .map((stmt) => stmt.trim())
      .filter((stmt) => stmt.length > 0);

    log(`📝 Found ${statements.length} SQL statements`, 'blue');

    // Execute each statement
    for (let i = 0; i < statements.length; i++) {
      const stmt = statements[i];

      if (!stmt.trim()) continue;

      try {
        await db.execute(stmt);

        // Log what we created
        if (stmt.includes('CREATE TABLE')) {
          const match = stmt.match(/CREATE TABLE IF NOT EXISTS (\w+)/);
          if (match) {
            log(`  ✅ Table: ${match[1]}`, 'green');
          }
        } else if (stmt.includes('CREATE INDEX')) {
          const match = stmt.match(/CREATE INDEX IF NOT EXISTS (\w+)/);
          if (match) {
            log(`  ✅ Index: ${match[1]}`, 'green');
          }
        } else if (stmt.includes('CREATE VIEW')) {
          const match = stmt.match(/CREATE VIEW IF NOT EXISTS (\w+)/);
          if (match) {
            log(`  ✅ View: ${match[1]}`, 'green');
          }
        } else if (stmt.includes('CREATE TRIGGER')) {
          const match = stmt.match(/CREATE TRIGGER IF NOT EXISTS (\w+)/);
          if (match) {
            log(`  ✅ Trigger: ${match[1]}`, 'green');
          }
        }
      } catch (error) {
        if (!error.message.includes('already exists')) {
          log(`  ⚠️  Warning: ${error.message}`, 'yellow');
        }
      }
    }

    log('\n✅ Calendar migration completed successfully!', 'green');

    // Verify tables exist
    log('\n🔍 Verifying calendar tables...', 'blue');

    const tables = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='table' AND name LIKE 'calendar%'
      OR name LIKE 'ical%'
      ORDER BY name;
    `);

    log(`\nCalendar Tables (${tables.rows.length}):`, 'cyan');
    tables.rows.forEach((row) => {
      log(`  • ${row.name}`, 'green');
    });

    const views = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='view' AND name LIKE 'calendar%'
      ORDER BY name;
    `);

    if (views.rows.length > 0) {
      log(`\nCalendar Views (${views.rows.length}):`, 'cyan');
      views.rows.forEach((row) => {
        log(`  • ${row.name}`, 'green');
      });
    }

    log('\n✅ Calendar database is ready!', 'green');
    log('', 'reset');

  } catch (error) {
    log(`\n❌ Error during migration: ${error.message}`, 'red');
    console.error(error);
    process.exit(1);
  }
}

main().catch((error) => {
  log(`\n❌ Unexpected error: ${error.message}`, 'red');
  console.error(error);
  process.exit(1);
});
