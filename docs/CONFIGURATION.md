# Configuration System

xSwarm Boss uses a unified configuration system with `config.cjs` as the single source of truth.

## Architecture

```
.env (secrets)              → config.cjs (source of truth) → config.json (Python)
                                         ↓
                                    wrangler.toml (Cloudflare)
```

## Files

### `config.cjs` (Committed)
**Single source of truth** for all configuration.

- Contains all non-secret settings
- Loads secrets from `.env`
- Generates deployment configs
- Provides CLI commands

### `.env` (Gitignored)
**Secrets only** - never committed.

Required secrets:
```bash
# AI Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Communication Services
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
SENDGRID_API_KEY=SG...

# Payment Processing
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Database
TURSO_AUTH_TOKEN=...

# Storage
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

### `config.json` (Generated, Gitignored)
**Python-compatible export** - secrets excluded.

Generated with: `node config.cjs export-json`

### `wrangler.toml` (Generated, Gitignored)
**Cloudflare Workers deployment config** - generated from config.cjs.

Generated with: `node config.cjs generate-wrangler`

## Usage

### Node.js
```javascript
const config = require('./config.cjs');

console.log(config.project.name);  // "xSwarm Boss"
console.log(config.ai.anthropic.apiKey);  // From .env
```

### Python
```python
import json

with open('config.json') as f:
    config = json.load(f)

print(config['project']['name'])  # "xSwarm Boss"
# Note: Secrets are NOT in config.json
```

### CLI Commands

Generate wrangler.toml:
```bash
node config.cjs generate-wrangler
```

Export config.json for Python:
```bash
node config.cjs export-json
```

Validate secrets:
```bash
node config.cjs validate
```

## Configuration Sections

### Project Metadata
```javascript
project: {
  name: 'xSwarm Boss',
  version: '0.1.1',
  description: 'AI-powered voice assistant with multi-tenant phone integration'
}
```

### Server Settings
```javascript
server: {
  host: 'localhost',  // From SERVER_HOST env var
  port: 8787,         // From SERVER_PORT env var
  apiBase: '/api',
  useHttps: false     // true in production
}
```

### Cloudflare Configuration
```javascript
cloudflare: {
  accountId: 'CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER',
  compatibilityDate: '2024-10-23',
  compatibilityFlags: ['nodejs_compat']
}
```

### AI Providers
```javascript
ai: {
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY,  // SECRET
    model: 'claude-sonnet-4-5-20250929'
  },
  openai: {
    apiKey: process.env.OPENAI_API_KEY,     // SECRET
    model: 'gpt-4-turbo-preview'
  },
  defaultTextProvider: 'anthropic',
  defaultVoiceProvider: 'moshi',
  models: {
    moshi: 'kyutai/moshika-mlx-q4'
  }
}
```

### Voice Configuration
```javascript
voice: {
  defaultPersona: 'boss',
  sampleRate: 24000,  // MOSHI requires 24kHz
  includePersonality: true,
  wakeWord: {
    enabled: true,
    sensitivity: 0.5,
    threshold: 0.5,
    keywords: ['hey_hal', 'hey_xswarm'],
    customModelsPath: '~/.xswarm/wake_words/',
    privacyMode: true,
    localProcessingOnly: true,
    audioLoggingEnabled: false,
    autoDeleteRecordings: true,
    retentionHours: 24
  },
  training: {
    enableCustomTraining: false,
    trainingSamplesCount: 20,
    voiceModelPath: '~/.xswarm/voice_models/'
  }
}
```

### Subscription Tiers
```javascript
subscriptions: {
  aiBuddy: {
    tier: 'ai_buddy',
    name: 'AI Buddy',
    price: 0,
    emailLimit: 100,
    voiceMinutes: 0,
    smsMessages: 0,
    phoneNumbers: 0
  },
  aiSecretary: {
    tier: 'ai_secretary',
    name: 'AI Secretary',
    price: 40,
    emailLimit: -1,  // Unlimited
    voiceMinutes: 500,
    smsMessages: 500,
    phoneNumbers: 1,
    overageRates: {
      voice: 0.013,
      sms: 0.0075,
      phone: 2.0
    }
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
    overageRates: {
      voice: 0.01,
      sms: 0.006,
      phone: 1.5
    }
  },
  aiCto: {
    tier: 'ai_cto',
    name: 'AI CTO',
    price: -1,  // Custom pricing
    emailLimit: -1,
    voiceMinutes: -1,
    smsMessages: -1,
    phoneNumbers: 10,
    teamManagement: true,
    prioritySupport: true,
    enterpriseFeatures: true,
    phoneSupport: true,
    dedicatedResources: true
  }
}
```

### Feature Flags
```javascript
features: {
  voiceEnabled: true,   // From VOICE_ENABLED env var
  smsEnabled: true,     // From SMS_ENABLED env var
  emailEnabled: true,   // From EMAIL_ENABLED env var
  stripeEnabled: true,  // From STRIPE_ENABLED env var
  directLineEnabled: true
}
```

## Deployment

### Development
1. Create `.env` with secrets
2. Run `node config.cjs export-json` to generate config.json for Python
3. Run `node config.cjs generate-wrangler` to generate wrangler.toml
4. Start development server: `npm run dev`

### Production
1. Set secrets in Cloudflare Workers:
   ```bash
   wrangler secret put ANTHROPIC_API_KEY
   wrangler secret put TWILIO_AUTH_TOKEN
   wrangler secret put SENDGRID_API_KEY
   wrangler secret put STRIPE_SECRET_KEY
   wrangler secret put STRIPE_WEBHOOK_SECRET
   wrangler secret put TURSO_AUTH_TOKEN
   wrangler secret put S3_ACCESS_KEY_ID
   wrangler secret put S3_SECRET_ACCESS_KEY
   ```

2. Deploy:
   ```bash
   npm run deploy
   ```

## Migration from Old Config

The old TOML files (`config.toml`, `wake-word.toml`) are no longer needed. All settings have been migrated to `config.cjs`.

To migrate custom settings:
1. Review old TOML files for any custom values
2. Update corresponding sections in `config.cjs`
3. Regenerate deployment configs:
   ```bash
   node config.cjs generate-wrangler
   node config.cjs export-json
   ```
4. Delete old TOML files (they're gitignored)

## Best Practices

1. **Never commit secrets** - Always use `.env` for secrets
2. **Regenerate after changes** - Run `node config.cjs export-json` after editing config.cjs
3. **Validate before deployment** - Run `node config.cjs validate` to check secrets
4. **Version config.cjs** - This is the only config file that should be committed
5. **Document changes** - Update this file when adding new config sections

## Troubleshooting

### Missing secrets error
```bash
❌ Missing required secrets in .env:
   - ANTHROPIC_API_KEY
```

**Solution**: Add the missing secret to `.env` file.

### Config out of sync
If `config.json` or `wrangler.toml` are out of sync with `config.cjs`:

```bash
node config.cjs export-json
node config.cjs generate-wrangler
```

### Python can't find config
Make sure `config.json` is generated:
```bash
node config.cjs export-json
```

### Cloudflare deployment fails
Regenerate `wrangler.toml`:
```bash
node config.cjs generate-wrangler
```
