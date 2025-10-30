#!/usr/bin/env node

/**
 * Database Setup Script for Boss AI
 *
 * This script initializes the simple Boss AI database schema
 * and optionally loads sample data for development.
 *
 * Usage:
 *   npm run setup-db              # Setup schema only
 *   npm run setup-db -- --sample  # Setup schema + sample data
 *   npm run setup-db -- --reset   # Drop all tables and recreate
 *
 * Environment:
 *   TURSO_DATABASE_URL - Database URL (required)
 *   TURSO_AUTH_TOKEN   - Auth token (required)
 */

import { createClient } from '@libsql/client';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Get script directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Parse command line arguments
const args = process.argv.slice(2);
const options = {
  sample: args.includes('--sample'),
  reset: args.includes('--reset'),
  help: args.includes('--help') || args.includes('-h'),
};

// Show help
if (options.help) {
  console.log(`
Boss AI Database Setup

Usage:
  npm run setup-db              Setup schema only
  npm run setup-db -- --sample  Setup schema + sample data
  npm run setup-db -- --reset   Drop all tables and recreate

Environment Variables:
  TURSO_DATABASE_URL  Database URL (required)
  TURSO_AUTH_TOKEN    Auth token (required)

For local development, you can use SQLite:
  TURSO_DATABASE_URL=file:./test.db npm run setup-db -- --sample
  `);
  process.exit(0);
}

// Check environment variables
const dbUrl = process.env.TURSO_DATABASE_URL;
const authToken = process.env.TURSO_AUTH_TOKEN;

if (!dbUrl) {
  console.error('Error: TURSO_DATABASE_URL environment variable is required');
  console.error('For local testing, use: TURSO_DATABASE_URL=file:./test.db');
  process.exit(1);
}

// For file:// URLs, authToken is optional
const isLocalFile = dbUrl.startsWith('file:');
if (!authToken && !isLocalFile) {
  console.error('Error: TURSO_AUTH_TOKEN environment variable is required');
  process.exit(1);
}

// Create database client
console.log('Connecting to database...');
const db = createClient({
  url: dbUrl,
  authToken: authToken || '',
});

// Read SQL files
const migrationsDir = join(__dirname, '../migrations');
const schemaPath = join(migrationsDir, 'schema.sql');
const sampleDataPath = join(migrationsDir, 'sample-data.sql');

console.log(`Reading schema from: ${schemaPath}`);
const schemaSql = readFileSync(schemaPath, 'utf-8');

let sampleDataSql = null;
if (options.sample) {
  console.log(`Reading sample data from: ${sampleDataPath}`);
  sampleDataSql = readFileSync(sampleDataPath, 'utf-8');
}

/**
 * Parse SQL script into individual statements
 * Handles multi-line statements, strings, and triggers (BEGIN/END)
 */
function parseSqlStatements(sql) {
  const statements = [];
  let current = '';
  let inString = false;
  let stringChar = null;
  let inComment = false;
  let inTrigger = false;

  for (let i = 0; i < sql.length; i++) {
    const char = sql[i];
    const nextChar = sql[i + 1];

    // Handle line comments
    if (!inString && char === '-' && nextChar === '-') {
      inComment = true;
      continue;
    }

    if (inComment) {
      if (char === '\n') {
        inComment = false;
      }
      continue;
    }

    // Handle strings
    if ((char === "'" || char === '"') && !inString) {
      inString = true;
      stringChar = char;
      current += char;
      continue;
    }

    if (inString && char === stringChar) {
      // Check for escaped quotes
      if (nextChar === stringChar) {
        current += char + nextChar;
        i++; // Skip next char
        continue;
      }
      inString = false;
      stringChar = null;
      current += char;
      continue;
    }

    current += char;

    // Check if we're entering a trigger (has BEGIN...END block)
    if (!inString && !inTrigger) {
      const upperCurrent = current.toUpperCase();
      if (upperCurrent.includes('CREATE TRIGGER') && upperCurrent.includes('BEGIN')) {
        inTrigger = true;
      }
    }

    // Handle statement separator
    if (!inString && char === ';') {
      // If in trigger, check if we've reached the END
      if (inTrigger) {
        const upperCurrent = current.toUpperCase();
        if (upperCurrent.trim().endsWith('END;')) {
          inTrigger = false;
          const trimmed = current.trim();
          if (trimmed.length > 0) {
            statements.push(trimmed);
          }
          current = '';
        }
      } else {
        const trimmed = current.trim();
        if (trimmed.length > 0) {
          statements.push(trimmed);
        }
        current = '';
      }
      continue;
    }
  }

  // Add final statement if exists
  const trimmed = current.trim();
  if (trimmed.length > 0) {
    statements.push(trimmed);
  }

  return statements;
}

/**
 * Execute SQL script (handles multiple statements)
 */
async function executeScript(sql, description) {
  console.log(`\n${description}...`);

  const statements = parseSqlStatements(sql);
  let successCount = 0;
  let errorCount = 0;

  for (const statement of statements) {
    try {
      // Skip empty statements
      if (statement.length === 0) continue;

      await db.execute(statement);
      successCount++;

      // Show progress for CREATE statements
      if (statement.toUpperCase().startsWith('CREATE')) {
        const match = statement.match(/CREATE\s+(TABLE|VIEW|INDEX|TRIGGER)\s+(?:IF NOT EXISTS\s+)?(\w+)/i);
        if (match) {
          console.log(`  ✓ Created ${match[1].toLowerCase()}: ${match[2]}`);
        }
      }
    } catch (error) {
      // Ignore "already exists" errors if not in reset mode
      if (error.message.includes('already exists') && !options.reset) {
        successCount++;
        continue;
      }
      console.error(`  ✗ Error executing statement: ${error.message}`);
      console.error(`    Statement: ${statement.substring(0, 100)}...`);
      errorCount++;
    }
  }

  console.log(`\n${description} complete: ${successCount} successful, ${errorCount} errors`);
  return { successCount, errorCount };
}

/**
 * Drop all tables (for reset)
 */
async function dropAllTables() {
  console.log('\nDropping all tables...');

  const tables = ['messages', 'reminders', 'events', 'users'];

  for (const table of tables) {
    try {
      await db.execute(`DROP TABLE IF EXISTS ${table}`);
      console.log(`  ✓ Dropped table: ${table}`);
    } catch (error) {
      console.error(`  ✗ Error dropping ${table}: ${error.message}`);
    }
  }

  // Drop views
  const views = [
    'todays_events',
    'upcoming_events',
    'pending_reminders',
    'overdue_reminders',
    'recent_messages',
    'conversation_threads'
  ];

  for (const view of views) {
    try {
      await db.execute(`DROP VIEW IF EXISTS ${view}`);
      console.log(`  ✓ Dropped view: ${view}`);
    } catch (error) {
      // Views might not exist, that's ok
    }
  }
}

/**
 * Verify database setup
 */
async function verifySetup() {
  console.log('\nVerifying database setup...');

  const checks = [
    { name: 'users table', query: 'SELECT COUNT(*) as count FROM users' },
    { name: 'events table', query: 'SELECT COUNT(*) as count FROM events' },
    { name: 'reminders table', query: 'SELECT COUNT(*) as count FROM reminders' },
    { name: 'messages table', query: 'SELECT COUNT(*) as count FROM messages' },
  ];

  for (const check of checks) {
    try {
      const result = await db.execute(check.query);
      const count = result.rows[0].count;
      console.log(`  ✓ ${check.name}: ${count} records`);
    } catch (error) {
      console.error(`  ✗ ${check.name}: ${error.message}`);
    }
  }
}

/**
 * Main setup function
 */
async function main() {
  try {
    console.log('Boss AI Database Setup');
    console.log('======================\n');
    console.log(`Database URL: ${dbUrl}`);
    console.log(`Reset mode: ${options.reset}`);
    console.log(`Load sample data: ${options.sample}`);

    // Reset if requested
    if (options.reset) {
      await dropAllTables();
    }

    // Execute schema
    const schemaResult = await executeScript(schemaSql, 'Setting up database schema');

    // Load sample data if requested
    if (options.sample && sampleDataSql) {
      const dataResult = await executeScript(sampleDataSql, 'Loading sample data');
    }

    // Verify setup
    await verifySetup();

    console.log('\n✓ Database setup complete!\n');

    if (options.sample) {
      console.log('Sample users created:');
      console.log('  Admin: +1234567890 / admin@example.com (is_admin: true)');
      console.log('  Alice: +1234567891 / alice@example.com');
      console.log('  Bob:   +1234567892 / bob@example.com');
      console.log('  Carol: +1234567893 / carol@example.com\n');
    }

    process.exit(0);
  } catch (error) {
    console.error('\n✗ Setup failed:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// Run setup
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
