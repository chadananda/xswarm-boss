#!/usr/bin/env node
/**
 * Run Authentication Migration
 *
 * Applies auth.sql migration to add authentication fields to users table
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createClient } from '@libsql/client';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function runMigration() {
  console.log('🔄 Running authentication migration...\n');

  // Create database client
  const client = createClient({
    url: process.env.TURSO_DATABASE_URL,
    authToken: process.env.TURSO_AUTH_TOKEN,
  });

  try {
    // Read migration file
    const migrationPath = join(__dirname, '../migrations/auth.sql');
    const migrationSQL = readFileSync(migrationPath, 'utf8');

    console.log('📄 Migration file:', migrationPath);
    console.log('🗄️  Database:', process.env.TURSO_DATABASE_URL);
    console.log('');

    // Split SQL into individual statements
    const statements = migrationSQL
      .split(';')
      .map(s => s.trim())
      .filter(s => s.length > 0 && !s.startsWith('--'));

    console.log(`📊 Found ${statements.length} SQL statements\n`);

    // Execute each statement
    for (let i = 0; i < statements.length; i++) {
      const statement = statements[i];

      // Skip comments
      if (statement.startsWith('--')) {
        continue;
      }

      console.log(`▶️  Executing statement ${i + 1}/${statements.length}...`);

      try {
        await client.execute(statement);
        console.log(`✅ Success\n`);
      } catch (error) {
        // Check if error is "column already exists" or "index already exists"
        if (
          error.message.includes('duplicate column name') ||
          error.message.includes('already exists')
        ) {
          console.log(`⚠️  Already exists (skipping)\n`);
        } else {
          throw error;
        }
      }
    }

    console.log('✅ Migration completed successfully!\n');

    // Verify schema
    console.log('🔍 Verifying schema...\n');

    const schemaResult = await client.execute(`
      SELECT sql FROM sqlite_schema
      WHERE type = 'table' AND name = 'users'
    `);

    if (schemaResult.rows.length > 0) {
      console.log('📋 Users table schema:');
      console.log(schemaResult.rows[0].sql);
      console.log('');
    }

    // Check for new columns
    const columnsResult = await client.execute("PRAGMA table_info('users')");

    const authColumns = [
      'email_verified',
      'email_verification_token',
      'email_verification_expires',
      'password_hash',
      'password_reset_token',
      'password_reset_expires',
      'jwt_version',
    ];

    console.log('✅ Authentication columns:');
    for (const column of authColumns) {
      const exists = columnsResult.rows.some(row => row.name === column);
      console.log(`   ${exists ? '✅' : '❌'} ${column}`);
    }
    console.log('');

    // Check indexes
    const indexesResult = await client.execute(`
      SELECT name FROM sqlite_schema
      WHERE type = 'index'
      AND tbl_name = 'users'
      AND name LIKE 'idx_users_%'
    `);

    console.log(`✅ Created ${indexesResult.rows.length} indexes`);
    for (const row of indexesResult.rows) {
      console.log(`   - ${row.name}`);
    }
    console.log('');

    console.log('🎉 Migration complete! Authentication system is ready.\n');
  } catch (error) {
    console.error('❌ Migration failed:', error.message);
    console.error('');
    console.error('Stack trace:', error.stack);
    process.exit(1);
  }
}

// Run migration
runMigration();
