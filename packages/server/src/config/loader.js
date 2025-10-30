/**
 * Configuration Loader for Node.js Server
 *
 * Loads configuration from:
 * 1. config.toml in project root (via R2 or local filesystem)
 * 2. Environment variables (from .dev.vars or production secrets)
 *
 * Note: This is a simplified loader for Cloudflare Workers.
 * In production, config.toml should be stored in R2 or KV.
 */

// Hardcoded config for now (TODO: Load from R2/KV in production)
// This matches the structure in config.toml
const DEFAULT_CONFIG = {
  admin: {
    username: 'admin',
    name: 'Admin User',
    email: 'admin@xswarm.dev',
    phone: '+15559876543',
    xswarm_email: 'admin@xswarm.ai',
    xswarm_phone: '+18005559876',
    persona: 'boss',
    wake_word: 'hey boss',
    subscription_tier: 'admin',
    access_level: 'superadmin',
    can_provision_numbers: true,
    can_view_all_users: true,
    can_manage_subscriptions: true,
    can_manage_config: true,
    can_access_all_channels: true,
  },
  server: {
    host: 'localhost',
    port: 8787,
    api_base: '/api',
    use_https: false,
  },
  twilio: {
    account_sid: null,
    test_account_sid: null,
    test_receive_number: null,
    test_send_number: null,
    test_receive_webhook: null,
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
    test_user_email: null,
    test_xswarm_email: null,
  },
  turso: {
    database_name: null,
    organization: null,
    database_url: null,
    primary_region: 'sjc',
    replica_regions: [],
    local_replica: {
      enabled: true,
      sync_interval_seconds: 60,
      local_db_path: null,
    },
    backup: {
      enabled: true,
      retention_days: 30,
      manual_backup_enabled: false,
      backup_schedule: null,
    },
  },
  features: {
    voice_enabled: true,
    sms_enabled: true,
    email_enabled: true,
    stripe_enabled: true,
    direct_line_enabled: true,
  },
  ai: {
    default_text_provider: 'anthropic',
    default_voice_provider: 'moshi',
    models: {
      anthropic_model: 'claude-sonnet-4-5-20250929',
      moshi_model: 'kyutai/moshika-mlx-q4',
    },
  },
  voice: {
    default_persona: 'boss',
    default_wake_word: 'hey boss',
    sample_rate: 24000,
    include_personality: true,
  },
  development: {
    debug: true,
    use_test_credentials: true,
    server_port: 8787,
    server_host: 'localhost',
  },
};

/**
 * Load configuration (merges default config with environment variables)
 * @param {Object} env - Cloudflare Workers environment bindings
 * @returns {Object} Merged configuration
 */
export async function loadConfig(env) {
  // Start with default config
  const config = { ...DEFAULT_CONFIG };

  // Override with environment variables if available
  if (env.TWILIO_ACCOUNT_SID) {
    config.twilio.account_sid = env.TWILIO_ACCOUNT_SID;
  }
  if (env.STRIPE_PUBLISHABLE_KEY) {
    config.stripe.publishable_key = env.STRIPE_PUBLISHABLE_KEY;
  }
  if (env.SENDGRID_DOMAIN) {
    config.sendgrid.domain = env.SENDGRID_DOMAIN;
  }
  if (env.TURSO_DATABASE_URL) {
    config.turso.database_url = env.TURSO_DATABASE_URL;
  }

  // TODO: Load from R2 bucket in production
  // if (env.CONFIG_BUCKET) {
  //   const configFile = await env.CONFIG_BUCKET.get('config.toml');
  //   if (configFile) {
  //     const configText = await configFile.text();
  //     // Parse TOML and merge with config
  //   }
  // }

  return config;
}

/**
 * Get admin user from configuration
 * @param {Object} env - Cloudflare Workers environment bindings
 * @returns {Object} Admin user configuration
 */
export async function getAdminUser(env) {
  const config = await loadConfig(env);
  return config.admin;
}
