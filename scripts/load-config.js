/**
 * Config Loader Utility
 *
 * Loads both secrets (.env) and configuration (config.toml)
 * Usage:
 *   import { loadConfig } from './scripts/load-config.js';
 *   const { secrets, config } = loadConfig();
 */

import 'dotenv/config';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');

/**
 * Get current environment (development, staging, or production)
 * Checks ENVIRONMENT or NODE_ENV environment variables
 * Defaults to "development" if not set
 *
 * @returns {string} Current environment
 */
export function getEnvironment() {
  return process.env.ENVIRONMENT || process.env.NODE_ENV || 'development';
}

/**
 * Check if running in production environment
 * @returns {boolean}
 */
export function isProduction() {
  return getEnvironment() === 'production';
}

/**
 * Check if running in development environment
 * @returns {boolean}
 */
export function isDevelopment() {
  const env = getEnvironment();
  return env === 'development' || env === 'dev';
}

/**
 * Load project configuration from config.toml and .env
 *
 * @returns {Object} { secrets, config, environment }
 */
export function loadConfig() {
  // Load secrets from .env (already loaded by dotenv/config)
  const secrets = {
    // AI Providers
    ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY,
    OPENAI_API_KEY: process.env.OPENAI_API_KEY,

    // Twilio (test + live + fallback to single token)
    TWILIO_AUTH_TOKEN_TEST: process.env.TWILIO_AUTH_TOKEN_TEST || process.env.TWILIO_TEST_AUTH_TOKEN || process.env.TWILIO_AUTH_TOKEN,
    TWILIO_AUTH_TOKEN_LIVE: process.env.TWILIO_AUTH_TOKEN_LIVE || process.env.TWILIO_AUTH_TOKEN,
    TWILIO_AUTH_TOKEN: process.env.TWILIO_AUTH_TOKEN,

    // SendGrid (test + live + fallback to single key)
    SENDGRID_API_KEY_TEST: process.env.SENDGRID_API_KEY_TEST || process.env.SENDGRID_API_KEY,
    SENDGRID_API_KEY_LIVE: process.env.SENDGRID_API_KEY_LIVE || process.env.SENDGRID_API_KEY,
    SENDGRID_API_KEY: process.env.SENDGRID_API_KEY,

    // Stripe (test + live)
    STRIPE_SECRET_KEY_TEST: process.env.STRIPE_SECRET_KEY_TEST,
    STRIPE_WEBHOOK_SECRET_TEST: process.env.STRIPE_WEBHOOK_SECRET_TEST,
    STRIPE_SECRET_KEY_LIVE: process.env.STRIPE_SECRET_KEY_LIVE,
    STRIPE_WEBHOOK_SECRET_LIVE: process.env.STRIPE_WEBHOOK_SECRET_LIVE,

    // Turso
    TURSO_AUTH_TOKEN: process.env.TURSO_AUTH_TOKEN,

    // S3-Compatible Storage (Cloudflare R2)
    S3_ACCESS_KEY_ID: process.env.S3_ACCESS_KEY_ID,
    S3_SECRET_ACCESS_KEY: process.env.S3_SECRET_ACCESS_KEY,

    // Cloudflare API
    CLOUDFLARE_API_TOKEN: process.env.CLOUDFLARE_API_TOKEN,

    // Optional
    RUNPOD_API_KEY: process.env.RUNPOD_API_KEY,
    MODAL_TOKEN_ID: process.env.MODAL_TOKEN_ID,
    MODAL_TOKEN_SECRET: process.env.MODAL_TOKEN_SECRET,
    ELEVENLABS_API_KEY: process.env.ELEVENLABS_API_KEY,
    DEEPGRAM_API_KEY: process.env.DEEPGRAM_API_KEY,
    MEILI_MASTER_KEY: process.env.MEILI_MASTER_KEY,
  };

  // Load config from config.toml
  let config = {};
  try {
    const configPath = join(rootDir, 'config.toml');
    const configContent = readFileSync(configPath, 'utf-8');
    config = parseToml(configContent);
  } catch (error) {
    console.warn('Warning: config.toml not found or invalid, using defaults');
    config = getDefaultConfig();
  }

  return {
    secrets,
    config,
    environment: getEnvironment()
  };
}

/**
 * Get default configuration
 * Note: Environment is detected from ENVIRONMENT or NODE_ENV env vars
 */
function getDefaultConfig() {
  return {
    twilio: {
      account_sid: null,
      test_account_sid: null,
    },
    stripe: {
      publishable_key: null,
      prices: {
        premium: null,
        voice: null,
        sms: null,
        phone: null,
      },
    },
    sendgrid: {
      domain: 'xswarm.ai',
    },
    turso: {
      database_url: null,
    },
    features: {
      voice_enabled: true,
      sms_enabled: true,
      email_enabled: true,
      stripe_enabled: true,
    },
  };
}
