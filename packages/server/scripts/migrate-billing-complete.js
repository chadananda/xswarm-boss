/**
 * Billing System Complete Migration
 *
 * Adds billing_events table and updates users table with billing fields.
 * Run with: node scripts/migrate-billing-complete.js
 */

import { createClient } from '@libsql/client';
import * as dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load .env from project root
dotenv.config({ path: join(__dirname, '../../../.env') });

const db = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN,
});

async function migrate() {
  console.log('Starting billing system complete migration...');

  try {
    // Create billing_events table
    console.log('Creating billing_events table...');
    await db.execute(`
      CREATE TABLE IF NOT EXISTS billing_events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        amount_cents INTEGER,
        description TEXT,
        stripe_event_id TEXT UNIQUE,
        processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Create indexes for billing_events
    console.log('Creating indexes for billing_events...');
    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_billing_events_user
      ON billing_events(user_id, processed_at DESC)
    `);

    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_billing_events_stripe
      ON billing_events(stripe_event_id)
    `);

    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_billing_events_type
      ON billing_events(event_type, processed_at DESC)
    `);

    // Add billing cycle and trial fields to users table (if they don't exist)
    console.log('Adding billing fields to users table...');

    // Try to add columns - they might already exist, so we'll ignore errors
    try {
      await db.execute(`
        ALTER TABLE users ADD COLUMN billing_cycle_start TEXT
      `);
      console.log('Added billing_cycle_start column');
    } catch (error) {
      if (error.message.includes('duplicate column')) {
        console.log('billing_cycle_start column already exists');
      } else {
        throw error;
      }
    }

    try {
      await db.execute(`
        ALTER TABLE users ADD COLUMN trial_end_date TEXT
      `);
      console.log('Added trial_end_date column');
    } catch (error) {
      if (error.message.includes('duplicate column')) {
        console.log('trial_end_date column already exists');
      } else {
        throw error;
      }
    }

    console.log('Migration completed successfully!');
    console.log('');
    console.log('Summary:');
    console.log('- billing_events table created');
    console.log('- Indexes created for efficient querying');
    console.log('- Users table updated with billing fields');
    console.log('');
    console.log('You can now use the complete billing system with:');
    console.log('- Automated overage billing');
    console.log('- Usage counter resets');
    console.log('- Phone number provisioning');
    console.log('- Subscription lifecycle management');

  } catch (error) {
    console.error('Migration failed:', error);
    process.exit(1);
  }
}

migrate();
