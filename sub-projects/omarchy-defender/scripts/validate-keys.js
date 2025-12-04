#!/usr/bin/env node

/**
 * API Key Validation Script
 * Tests all API keys in .env to ensure they have proper permissions
 *
 * Usage: node scripts/validate-keys.js
 */

import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');

// ANSI colors for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  dim: '\x1b[2m',
  bold: '\x1b[1m'
};

const log = {
  success: (msg) => console.log(`${colors.green}✓${colors.reset} ${msg}`),
  error: (msg) => console.log(`${colors.red}✗${colors.reset} ${msg}`),
  warn: (msg) => console.log(`${colors.yellow}⚠${colors.reset} ${msg}`),
  info: (msg) => console.log(`${colors.blue}ℹ${colors.reset} ${msg}`),
  header: (msg) => console.log(`\n${colors.bold}${msg}${colors.reset}`),
  dim: (msg) => console.log(`${colors.dim}  ${msg}${colors.reset}`)
};

// Load environment variables from .env file
const loadEnv = () => {
  const envPath = resolve(PROJECT_ROOT, '.env');

  if (!existsSync(envPath)) {
    log.error('.env file not found! Copy .env.example to .env and fill in your keys.');
    process.exit(1);
  }

  const envContent = readFileSync(envPath, 'utf-8');
  const env = {};

  for (const line of envContent.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;

    const key = trimmed.substring(0, eqIndex).trim();
    let value = trimmed.substring(eqIndex + 1).trim();

    // Remove surrounding quotes if present
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    env[key] = value;
  }

  return env;
};

// Validation functions for each API
const validators = {

  // ============================================================
  // GEMINI API
  // ============================================================
  async gemini(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`
      );

      if (response.ok) {
        const data = await response.json();
        const models = data.models?.map(m => m.name.split('/').pop()).slice(0, 5) || [];
        return {
          valid: true,
          info: `Access to ${data.models?.length || 0} models including: ${models.join(', ')}...`
        };
      } else {
        const error = await response.json();
        return { valid: false, error: error.error?.message || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // ELEVENLABS API
  // ============================================================
  async elevenLabs(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    try {
      const response = await fetch('https://api.elevenlabs.io/v1/user/subscription', {
        headers: { 'xi-api-key': apiKey }
      });

      if (response.ok) {
        const data = await response.json();
        return {
          valid: true,
          info: `Tier: ${data.tier || 'unknown'}, Characters remaining: ${data.character_count || 0}/${data.character_limit || 0}`
        };
      } else {
        const error = await response.json();
        return { valid: false, error: error.detail?.message || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // STRIPE API
  // ============================================================
  async stripe(secretKey, publishableKey) {
    const results = { secret: null, publishable: null };

    // Validate secret key format
    if (!secretKey) {
      results.secret = { valid: false, error: 'Key not provided' };
    } else if (!secretKey.startsWith('sk_test_') && !secretKey.startsWith('sk_live_')) {
      results.secret = { valid: false, error: 'Invalid format. Should start with sk_test_ or sk_live_' };
    } else {
      try {
        const response = await fetch('https://api.stripe.com/v1/balance', {
          headers: { 'Authorization': `Bearer ${secretKey}` }
        });

        if (response.ok) {
          const isTest = secretKey.startsWith('sk_test_');
          results.secret = {
            valid: true,
            info: `${isTest ? 'TEST' : 'LIVE'} mode - Balance API accessible`
          };
        } else {
          const error = await response.json();
          results.secret = { valid: false, error: error.error?.message || response.statusText };
        }
      } catch (e) {
        results.secret = { valid: false, error: e.message };
      }
    }

    // Validate publishable key format
    if (!publishableKey) {
      results.publishable = { valid: false, error: 'Key not provided' };
    } else if (!publishableKey.startsWith('pk_test_') && !publishableKey.startsWith('pk_live_')) {
      results.publishable = {
        valid: false,
        error: `Invalid format. Should start with pk_test_ or pk_live_ (got: ${publishableKey.substring(0, 10)}...)`
      };
    } else {
      const isTest = publishableKey.startsWith('pk_test_');
      results.publishable = {
        valid: true,
        info: `${isTest ? 'TEST' : 'LIVE'} mode - Format valid (frontend key)`
      };
    }

    return results;
  },

  // ============================================================
  // TURSO DATABASE
  // ============================================================
  async turso(url, token) {
    if (!url || !token) {
      return { valid: false, error: 'URL or token not provided' };
    }

    if (!url.startsWith('libsql://')) {
      return { valid: false, error: 'URL should start with libsql://' };
    }

    try {
      // Convert libsql:// to https:// for HTTP API
      const httpUrl = url.replace('libsql://', 'https://');

      const response = await fetch(`${httpUrl}/v2/pipeline`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          requests: [
            { type: 'execute', stmt: { sql: 'SELECT 1 as test' } },
            { type: 'close' }
          ]
        })
      });

      if (response.ok) {
        return { valid: true, info: 'Database connection successful' };
      } else {
        const text = await response.text();
        return { valid: false, error: text || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // CLOUDFLARE API
  // ============================================================
  async cloudflare(accountId, apiToken) {
    if (!accountId || !apiToken) {
      return { valid: false, error: 'Account ID or API token not provided' };
    }

    try {
      const response = await fetch(
        `https://api.cloudflare.com/client/v4/accounts/${accountId}`,
        { headers: { 'Authorization': `Bearer ${apiToken}` } }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          return { valid: true, info: `Account: ${data.result?.name || accountId}` };
        } else {
          return { valid: false, error: data.errors?.[0]?.message || 'Unknown error' };
        }
      } else {
        return { valid: false, error: response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // ANTHROPIC API
  // ============================================================
  async anthropic(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    if (!apiKey.startsWith('sk-ant-')) {
      return { valid: false, error: 'Invalid format. Should start with sk-ant-' };
    }

    try {
      // Use a minimal request to validate the key
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': '2023-06-01',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'claude-3-haiku-20240307',
          max_tokens: 1,
          messages: [{ role: 'user', content: 'Hi' }]
        })
      });

      if (response.ok) {
        return { valid: true, info: 'API access confirmed (Claude models available)' };
      } else {
        const error = await response.json();
        // 400 errors with valid auth still mean the key works
        if (response.status === 400 && error.error?.type !== 'authentication_error') {
          return { valid: true, info: 'API key valid (request format issue, but auth works)' };
        }
        return { valid: false, error: error.error?.message || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // OPENAI API
  // ============================================================
  async openai(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    if (!apiKey.startsWith('sk-')) {
      return { valid: false, error: 'Invalid format. Should start with sk-' };
    }

    try {
      const response = await fetch('https://api.openai.com/v1/models', {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      });

      if (response.ok) {
        const data = await response.json();
        const gptModels = data.data?.filter(m => m.id.includes('gpt')).length || 0;
        return { valid: true, info: `Access to ${data.data?.length || 0} models (${gptModels} GPT models)` };
      } else {
        const error = await response.json();
        return { valid: false, error: error.error?.message || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // SENDGRID API
  // ============================================================
  async sendgrid(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    if (!apiKey.startsWith('SG.')) {
      return { valid: false, error: 'Invalid format. Should start with SG.' };
    }

    try {
      const response = await fetch('https://api.sendgrid.com/v3/user/profile', {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      });

      if (response.ok) {
        const data = await response.json();
        return { valid: true, info: `Account: ${data.username || 'verified'}` };
      } else if (response.status === 401) {
        return { valid: false, error: 'Invalid API key or insufficient permissions' };
      } else {
        return { valid: false, error: response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // PERPLEXITY API
  // ============================================================
  async perplexity(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    if (!apiKey.startsWith('pplx-')) {
      return { valid: false, error: 'Invalid format. Should start with pplx-' };
    }

    try {
      // Perplexity uses OpenAI-compatible API
      const response = await fetch('https://api.perplexity.ai/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'sonar',
          messages: [{ role: 'user', content: 'Hi' }],
          max_tokens: 1
        })
      });

      if (response.ok) {
        return { valid: true, info: 'API access confirmed' };
      } else {
        const error = await response.json();
        // Check if it's just a model issue but auth works
        if (error.error?.message?.includes('Invalid model')) {
          return { valid: true, info: 'API key valid (model list may have changed)' };
        }
        return { valid: false, error: error.error?.message || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // MISTRAL API
  // ============================================================
  async mistral(apiKey) {
    if (!apiKey) return { valid: false, error: 'Key not provided' };

    try {
      const response = await fetch('https://api.mistral.ai/v1/models', {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      });

      if (response.ok) {
        const data = await response.json();
        return { valid: true, info: `Access to ${data.data?.length || 0} models` };
      } else {
        const error = await response.json();
        return { valid: false, error: error.message || response.statusText };
      }
    } catch (e) {
      return { valid: false, error: e.message };
    }
  },

  // ============================================================
  // S3/R2 CREDENTIALS
  // ============================================================
  async s3r2(accessKeyId, secretAccessKey, accountId) {
    if (!accessKeyId || !secretAccessKey) {
      return { valid: false, error: 'Access key ID or secret not provided' };
    }

    // For R2, we'd need to make a signed request which is complex
    // Just validate the format for now
    if (accessKeyId.length < 20) {
      return { valid: false, error: 'Access key ID appears too short' };
    }

    if (secretAccessKey.length < 40) {
      return { valid: false, error: 'Secret access key appears too short' };
    }

    return {
      valid: true,
      info: 'Credentials format valid (full validation requires signed request)'
    };
  }
};

// Main validation runner
const runValidation = async () => {
  console.log('\n' + '='.repeat(60));
  console.log('  OMARCHY DEFENDER - API KEY VALIDATION');
  console.log('='.repeat(60));

  const env = loadEnv();
  let allValid = true;
  const results = {};

  // Gemini
  log.header('Google Gemini API');
  results.gemini = await validators.gemini(env.GEMINI_API_KEY);
  if (results.gemini.valid) {
    log.success('GEMINI_API_KEY - Valid');
    log.dim(results.gemini.info);
  } else {
    log.error(`GEMINI_API_KEY - ${results.gemini.error}`);
    allValid = false;
  }

  // ElevenLabs
  log.header('ElevenLabs API');
  results.elevenLabs = await validators.elevenLabs(env.ELEVENLABS_API_KEY);
  if (results.elevenLabs.valid) {
    log.success('ELEVENLABS_API_KEY - Valid');
    log.dim(results.elevenLabs.info);
  } else {
    log.error(`ELEVENLABS_API_KEY - ${results.elevenLabs.error}`);
    allValid = false;
  }

  // Stripe
  log.header('Stripe API');
  results.stripe = await validators.stripe(env.STRIPE_SECRET_KEY, env.STRIPE_PUBLISHABLE_KEY);

  if (results.stripe.secret.valid) {
    log.success('STRIPE_SECRET_KEY - Valid');
    log.dim(results.stripe.secret.info);
  } else {
    log.error(`STRIPE_SECRET_KEY - ${results.stripe.secret.error}`);
    allValid = false;
  }

  if (results.stripe.publishable.valid) {
    log.success('STRIPE_PUBLISHABLE_KEY - Valid');
    log.dim(results.stripe.publishable.info);
  } else {
    log.error(`STRIPE_PUBLISHABLE_KEY - ${results.stripe.publishable.error}`);
    allValid = false;
  }

  if (env.STRIPE_WEBHOOK_SECRET) {
    if (env.STRIPE_WEBHOOK_SECRET.startsWith('whsec_')) {
      log.success('STRIPE_WEBHOOK_SECRET - Format valid');
    } else {
      log.error('STRIPE_WEBHOOK_SECRET - Should start with whsec_');
      allValid = false;
    }
  }

  // Turso
  log.header('Turso Database');
  results.turso = await validators.turso(env.TURSO_DATABASE_URL, env.TURSO_AUTH_TOKEN);
  if (results.turso.valid) {
    log.success('TURSO - Valid');
    log.dim(results.turso.info);
  } else {
    log.error(`TURSO - ${results.turso.error}`);
    allValid = false;
  }

  // Cloudflare
  log.header('Cloudflare API');
  results.cloudflare = await validators.cloudflare(env.CLOUDFLARE_ACCOUNT_ID, env.CLOUDFLARE_API_TOKEN);
  if (results.cloudflare.valid) {
    log.success('CLOUDFLARE - Valid');
    log.dim(results.cloudflare.info);
  } else {
    log.error(`CLOUDFLARE - ${results.cloudflare.error}`);
    allValid = false;
  }

  // S3/R2
  log.header('Cloudflare R2 (S3-compatible)');
  results.s3r2 = await validators.s3r2(env.S3_ACCESS_KEY_ID, env.S3_SECRET_ACCESS_KEY, env.CLOUDFLARE_ACCOUNT_ID);
  if (results.s3r2.valid) {
    log.success('S3/R2 Credentials - Valid');
    log.dim(results.s3r2.info);
  } else {
    log.error(`S3/R2 - ${results.s3r2.error}`);
    allValid = false;
  }

  // SendGrid
  log.header('SendGrid Email API');
  results.sendgrid = await validators.sendgrid(env.SENDGRID_API_KEY);
  if (results.sendgrid.valid) {
    log.success('SENDGRID_API_KEY - Valid');
    log.dim(results.sendgrid.info);
  } else {
    log.error(`SENDGRID_API_KEY - ${results.sendgrid.error}`);
    allValid = false;
  }

  // Anthropic
  log.header('Anthropic API (Claude)');
  results.anthropic = await validators.anthropic(env.ANTHROPIC_API_KEY);
  if (results.anthropic.valid) {
    log.success('ANTHROPIC_API_KEY - Valid');
    log.dim(results.anthropic.info);
  } else {
    log.error(`ANTHROPIC_API_KEY - ${results.anthropic.error}`);
    allValid = false;
  }

  // OpenAI
  log.header('OpenAI API');
  results.openai = await validators.openai(env.OPENAI_API_KEY);
  if (results.openai.valid) {
    log.success('OPENAI_API_KEY - Valid');
    log.dim(results.openai.info);
  } else {
    log.error(`OPENAI_API_KEY - ${results.openai.error}`);
    allValid = false;
  }

  // Perplexity
  log.header('Perplexity API');
  results.perplexity = await validators.perplexity(env.PERPLEXITY_API_KEY);
  if (results.perplexity.valid) {
    log.success('PERPLEXITY_API_KEY - Valid');
    log.dim(results.perplexity.info);
  } else {
    log.error(`PERPLEXITY_API_KEY - ${results.perplexity.error}`);
    allValid = false;
  }

  // Mistral
  log.header('Mistral API');
  results.mistral = await validators.mistral(env.MISTRAL_API_KEY);
  if (results.mistral.valid) {
    log.success('MISTRAL_API_KEY - Valid');
    log.dim(results.mistral.info);
  } else {
    log.error(`MISTRAL_API_KEY - ${results.mistral.error}`);
    allValid = false;
  }

  // Summary
  console.log('\n' + '='.repeat(60));
  if (allValid) {
    log.success('ALL API KEYS VALIDATED SUCCESSFULLY!');
  } else {
    log.warn('Some API keys have issues. Please review above.');
  }
  console.log('='.repeat(60) + '\n');

  return allValid;
};

// Run validation
runValidation().catch(console.error);
