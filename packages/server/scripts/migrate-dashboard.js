/**
 * Dashboard Database Migration
 *
 * Creates tables for usage tracking and billing history.
 * Run with: node scripts/migrate-dashboard.js
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
  console.log('Starting dashboard migration...');

  try {
    // Create usage_records table
    console.log('Creating usage_records table...');
    await db.execute(`
      CREATE TABLE IF NOT EXISTS usage_records (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        voice_minutes INTEGER DEFAULT 0,
        sms_messages INTEGER DEFAULT 0,
        email_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Create indexes for usage_records
    console.log('Creating indexes for usage_records...');
    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_usage_user_period
      ON usage_records(user_id, period_start)
    `);

    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_usage_period
      ON usage_records(period_start, period_end)
    `);

    // Create billing_history table
    console.log('Creating billing_history table...');
    await db.execute(`
      CREATE TABLE IF NOT EXISTS billing_history (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT NOT NULL,
        description TEXT,
        invoice_url TEXT,
        period_start TEXT,
        period_end TEXT,
        stripe_invoice_id TEXT,
        stripe_payment_intent_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
      )
    `);

    // Create indexes for billing_history
    console.log('Creating indexes for billing_history...');
    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_billing_user
      ON billing_history(user_id, created_at DESC)
    `);

    await db.execute(`
      CREATE INDEX IF NOT EXISTS idx_billing_stripe_invoice
      ON billing_history(stripe_invoice_id)
    `);

    console.log('Migration completed successfully!');

  } catch (error) {
    console.error('Migration failed:', error);
    process.exit(1);
  }
}

migrate();
