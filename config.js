/**
 * xSwarm Boss - Unified Configuration
 *
 * Single source of truth for all configuration.
 * Secrets loaded from .env (gitignored)
 *
 * Usage:
 *   Node.js:  import config from './config.js'
 *   Python:   import json; config = json.load(open('./tmp/config.json'))
 *   CLI:      node config.js generate-wrangler
 */

import 'dotenv/config';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const config = {
  // =============================================================================
  // Project Metadata
  // =============================================================================
  project: {
    name: 'xSwarm Boss',
    version: '0.1.1',
    description: 'AI-powered voice assistant with multi-tenant phone integration',
  },

  // =============================================================================
  // Server Configuration
  // =============================================================================
  server: {
    host: process.env.SERVER_HOST || 'localhost',
    port: parseInt(process.env.SERVER_PORT || '8787'),
    apiBase: '/api',
    useHttps: process.env.NODE_ENV === 'production',
  },

  // =============================================================================
  // Cloudflare Configuration
  // =============================================================================
  cloudflare: {
    accountId: process.env.CLOUDFLARE_ACCOUNT_ID || 'CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER',
    compatibilityDate: '2024-10-23',
    compatibilityFlags: ['nodejs_compat'],
  },

  // =============================================================================
  // Twilio Configuration (Voice & SMS)
  // =============================================================================
  twilio: {
    accountSid: process.env.TWILIO_ACCOUNT_SID || 'TWILIO_ACCOUNT_SID_PLACEHOLDER',
    authToken: process.env.TWILIO_AUTH_TOKEN, // SECRET - from .env
    testAccountSid: 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    testReceiveNumber: '+15559876543',
    testSendNumber: '+15551234567',
    testReceiveWebhook: 'https://demo.twilio.com/welcome/voice/',
  },

  // =============================================================================
  // Stripe Configuration (Payments & Subscriptions)
  // =============================================================================
  stripe: {
    publishableKeyTest: 'pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    publishableKeyLive: process.env.STRIPE_PUBLISHABLE_KEY || 'pk_live_xxxxxxxxxxxxxxxx',
    secretKey: process.env.STRIPE_SECRET_KEY, // SECRET - from .env
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET, // SECRET - from .env
    prices: {
      aiBuddy: 'price_1SNfOARfk9upK3BeVL15MBCo',
      aiSecretary: 'price_1SNfOBRfk9upK3BepnFbldcs',
      aiProjectManager: 'price_1SNfOdRfk9upK3BegXBAYz0z',
      aiCto: 'price_1SNfOeRfk9upK3Benxw8PKds',
      voice: 'price_1SNfOfRfk9upK3BeqSfse2OH',
      sms: 'price_1SNfOgRfk9upK3BeZTkdPV9R',
      phone: 'price_1SNfOhRfk9upK3Be0t9n94vl',
    },
  },

  // =============================================================================
  // SendGrid Configuration (Email)
  // =============================================================================
  sendgrid: {
    apiKey: process.env.SENDGRID_API_KEY, // SECRET - from .env
    domain: 'xswarm.ai',
    fromEmail: process.env.SENDGRID_FROM_EMAIL || 'boss@xswarm.ai',
    fromName: process.env.SENDGRID_FROM_NAME || 'Boss AI',
    testUserEmail: 'xswarm-testuser@xswarm.ai',
    testXswarmEmail: 'xswarm-testboss@xswarm.ai',
  },

  // =============================================================================
  // Turso Database Configuration
  // =============================================================================
  turso: {
    databaseName: 'xswarm',
    organization: 'your-org-name',
    databaseUrl: process.env.TURSO_DATABASE_URL || 'TURSO_DATABASE_URL_PLACEHOLDER',
    authToken: process.env.TURSO_AUTH_TOKEN, // SECRET - from .env
    primaryRegion: 'pdx',
    replicaRegions: ['iad', 'fra', 'nrt'],
    localReplica: {
      enabled: true,
      syncIntervalSeconds: 60,
      localDbPath: '~/.local/share/xswarm/users.db',
    },
    backup: {
      enabled: true,
      retentionDays: 30,
      manualBackupEnabled: false,
      backupSchedule: '0 2 * * *',
    },
  },

  // =============================================================================
  // R2 Storage Configuration
  // =============================================================================
  storage: {
    provider: 'r2',
    bucketName: 'xswarm-boss',
    devBucketName: 'xswarm-boss-dev',
    assetsPrefix: 'assets/',
    region: 'auto',
    endpoint: 'https://CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.r2.cloudflarestorage.com',
    publicUrl: 'https://assets.xswarm.ai',
    accessKeyId: process.env.S3_ACCESS_KEY_ID, // SECRET - from .env
    secretAccessKey: process.env.S3_SECRET_ACCESS_KEY, // SECRET - from .env
    backup: {
      enabled: true,
      backupsPrefix: 'backups/',
      retentionDays: 90,
      backupSchedule: '0 3 * * *',
    },
  },

  // =============================================================================
  // AI Provider Configuration
  // =============================================================================
  ai: {
    anthropic: {
      apiKey: process.env.ANTHROPIC_API_KEY, // SECRET - from .env
      model: 'claude-sonnet-4-5-20250929',
    },
    openai: {
      apiKey: process.env.OPENAI_API_KEY, // SECRET - from .env
      model: 'gpt-4-turbo-preview',
    },
    defaultTextProvider: 'anthropic',
    defaultVoiceProvider: 'moshi',
    models: {
      moshi: 'kyutai/moshika-mlx-q4',
    },
  },

  // =============================================================================
  // Voice Configuration
  // =============================================================================
  voice: {
    defaultPersona: 'boss',
    sampleRate: 24000, // MOSHI requires 24kHz
    includePersonality: true,
    wakeWord: {
      enabled: true,
      sensitivity: 0.5,
      threshold: 0.5,
      keywords: ['hey_hal', 'hey_xswarm'],
      customModelsPath: '~/.xswarm/wake_words/',
      enableSuggestions: true,
      suggestionIntervalMinutes: 30,
      privacyMode: true,
      localProcessingOnly: true,
      audioLoggingEnabled: false,
      autoDeleteRecordings: true,
      retentionHours: 24,
    },
    training: {
      enableCustomTraining: false,
      trainingSamplesCount: 20,
      voiceModelPath: '~/.xswarm/voice_models/',
    },
  },

  // =============================================================================
  // Feature Flags
  // =============================================================================
  features: {
    voiceEnabled: process.env.VOICE_ENABLED !== 'false',
    smsEnabled: process.env.SMS_ENABLED !== 'false',
    emailEnabled: process.env.EMAIL_ENABLED !== 'false',
    stripeEnabled: process.env.STRIPE_ENABLED !== 'false',
    directLineEnabled: true,
  },

  // =============================================================================
  // Subscription Tiers
  // =============================================================================
  subscriptions: {
    aiBuddy: {
      tier: 'ai_buddy',
      name: 'AI Buddy',
      price: 0,
      emailLimit: 100,
      voiceMinutes: 0,
      smsMessages: 0,
      phoneNumbers: 0,
      teamManagement: false,
      prioritySupport: false,
      enterpriseFeatures: false,
    },
    aiSecretary: {
      tier: 'ai_secretary',
      name: 'AI Secretary',
      price: 40,
      emailLimit: -1,
      voiceMinutes: 500,
      smsMessages: 500,
      phoneNumbers: 1,
      teamManagement: false,
      prioritySupport: false,
      enterpriseFeatures: false,
      overageRates: {
        voice: 0.013,
        sms: 0.0075,
        phone: 2.0,
      },
    },
    aiProjectManager: {
      tier: 'ai_project_manager',
      name: 'AI Project Manager',
      price: 280,
      emailLimit: -1,
      voiceMinutes: 2000,
      smsMessages: 2000,
      phoneNumbers: 3,
      teamManagement: true,
      prioritySupport: true,
      enterpriseFeatures: false,
      overageRates: {
        voice: 0.01,
        sms: 0.006,
        phone: 1.5,
      },
    },
    aiCto: {
      tier: 'ai_cto',
      name: 'AI CTO',
      price: -1, // Custom pricing
      emailLimit: -1,
      voiceMinutes: -1,
      smsMessages: -1,
      phoneNumbers: 10,
      teamManagement: true,
      prioritySupport: true,
      enterpriseFeatures: true,
      phoneSupport: true,
      dedicatedResources: true,
    },
  },

  // =============================================================================
  // Test User Configuration
  // =============================================================================
  testUser: {
    email: 'testuser@example.com',
    phone: '+15551234567',
    subscriptionTier: 'ai_secretary',
    persona: 'boss',
    wakeWord: 'hey boss',
    xswarmEmail: 'testuser@xswarm.ai',
    xswarmPhone: '+18005551001',
  },

  // =============================================================================
  // Admin User Configuration
  // =============================================================================
  admin: {
    username: 'admin',
    name: 'Admin User',
    email: 'admin@xswarm.dev',
    phone: '+15559876543',
    xswarmEmail: 'admin@xswarm.ai',
    xswarmPhone: '+18005559876',
    persona: 'boss',
    wakeWord: 'hey boss',
    subscriptionTier: 'admin',
    accessLevel: 'superadmin',
    permissions: {
      canProvisionNumbers: true,
      canViewAllUsers: true,
      canManageSubscriptions: true,
      canManageConfig: true,
      canAccessAllChannels: true,
    },
  },

  // =============================================================================
  // Development Settings
  // =============================================================================
  development: {
    debug: process.env.DEBUG === 'true',
    useTestCredentials: process.env.NODE_ENV !== 'production',
    serverPort: 8787,
    serverHost: 'localhost',
  },
};

// =============================================================================
// Export Functions
// =============================================================================

/**
 * Ensure ./tmp/ directory exists
 */
function ensureTmpDir() {
  const tmpDir = path.join(__dirname, 'tmp');
  if (!fs.existsSync(tmpDir)) {
    fs.mkdirSync(tmpDir, { recursive: true });
  }
  return tmpDir;
}

/**
 * Generate wrangler.toml from config
 */
function generateWranglerToml() {
  const tmpDir = ensureTmpDir();
  const wranglerContent = `# Generated from config.js - DO NOT EDIT MANUALLY
# To update: node config.js generate-wrangler

name = "boss-ai"
main = "packages/server/src/index.js"
compatibility_date = "${config.cloudflare.compatibilityDate}"
compatibility_flags = ${JSON.stringify(config.cloudflare.compatibilityFlags)}

account_id = "${config.cloudflare.accountId}"

[dev]
port = ${config.server.port}
local_protocol = "${config.server.useHttps ? 'https' : 'http'}"

[[r2_buckets]]
binding = "R2_BUCKET"
bucket_name = "${config.storage.bucketName}"
preview_bucket_name = "${config.storage.devBucketName}"

[vars]
ENVIRONMENT = "${process.env.NODE_ENV || 'production'}"
TURSO_DATABASE_URL = "${config.turso.databaseUrl}"
SENDGRID_FROM_EMAIL = "${config.sendgrid.fromEmail}"
SENDGRID_FROM_NAME = "${config.sendgrid.fromName}"
VOICE_ENABLED = "${config.features.voiceEnabled}"
SMS_ENABLED = "${config.features.smsEnabled}"
EMAIL_ENABLED = "${config.features.emailEnabled}"

# =============================================================================
# SECRETS (Managed separately - NOT in this file)
# =============================================================================
# Set using: wrangler secret put <KEY>
#
# Required secrets:
#   - ANTHROPIC_API_KEY
#   - OPENAI_API_KEY
#   - TWILIO_AUTH_TOKEN
#   - SENDGRID_API_KEY
#   - STRIPE_SECRET_KEY
#   - STRIPE_WEBHOOK_SECRET
#   - TURSO_AUTH_TOKEN
#   - S3_ACCESS_KEY_ID
#   - S3_SECRET_ACCESS_KEY
`;

  fs.writeFileSync(path.join(tmpDir, 'wrangler.toml'), wranglerContent);
  console.log('✅ Generated ./tmp/wrangler.toml from config.js');
}

/**
 * Export config as JSON for Python
 */
function exportConfigJson() {
  const tmpDir = ensureTmpDir();
  const jsonConfig = JSON.parse(JSON.stringify(config, (key, value) => {
    // Don't export secrets to JSON file
    if (key === 'apiKey' || key === 'authToken' || key === 'secretKey' ||
        key === 'webhookSecret' || key === 'accessKeyId' || key === 'secretAccessKey') {
      return undefined;
    }
    return value;
  }));

  fs.writeFileSync(
    path.join(tmpDir, 'config.json'),
    JSON.stringify(jsonConfig, null, 2)
  );
  console.log('✅ Exported ./tmp/config.json (secrets excluded)');
}

// CLI Commands
if (import.meta.url === `file://${process.argv[1]}`) {
  const command = process.argv[2];

  switch (command) {
    case 'generate-wrangler':
      generateWranglerToml();
      break;
    case 'export-json':
      exportConfigJson();
      break;
    case 'validate':
      console.log('Validating configuration...');
      const missing = [];
      if (!config.ai.anthropic.apiKey) missing.push('ANTHROPIC_API_KEY');
      if (!config.twilio.authToken) missing.push('TWILIO_AUTH_TOKEN');
      if (!config.sendgrid.apiKey) missing.push('SENDGRID_API_KEY');
      if (!config.stripe.secretKey) missing.push('STRIPE_SECRET_KEY');
      if (!config.turso.authToken) missing.push('TURSO_AUTH_TOKEN');

      if (missing.length > 0) {
        console.error('❌ Missing required secrets in .env:');
        missing.forEach(key => console.error(`   - ${key}`));
        process.exit(1);
      } else {
        console.log('✅ All required secrets present');
      }
      break;
    default:
      console.log('Usage:');
      console.log('  node config.js generate-wrangler  # Generate ./tmp/wrangler.toml');
      console.log('  node config.js export-json        # Export ./tmp/config.json for Python');
      console.log('  node config.js validate           # Validate secrets');
  }
}

export default config;
