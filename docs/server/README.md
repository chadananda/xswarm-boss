# Server Architecture

Cloudflare Workers backend for authentication, billing, and communication.

## Overview

JavaScript backend running on Cloudflare Workers edge compute:
- JWT authentication with email verification
- Stripe subscription billing (4 tiers)
- SendGrid email (transactional + inbound)
- Twilio SMS/voice
- Turso database (SQLite, distributed)

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 Cloudflare Workers                        │
├──────────────┬──────────────┬──────────────┬─────────────┤
│     Auth     │   Billing    │    Email     │  Database   │
│    (JWT)     │  (Stripe)    │ (SendGrid)   │  (Turso)    │
├──────────────┼──────────────┼──────────────┼─────────────┤
│ • Signup     │ • Checkout   │ • Templates  │ • Users     │
│ • Login     │ • Webhooks   │ • Inbound    │ • Personas  │
│ • Verify    │ • Portal     │ • Parse      │ • Memory    │
│ • Reset     │ • Metered    │ • Forward    │ • Usage     │
└──────────────┴──────────────┴──────────────┴─────────────┘
```

## Authentication System

### Routes (`src/routes/auth/`)

```
POST /auth/signup          - Register + send verification
POST /auth/verify-email    - Confirm email
POST /auth/login           - Get JWT
POST /auth/logout          - Invalidate token
POST /auth/forgot-password - Request reset
POST /auth/reset-password  - Set new password
GET  /auth/me              - Current user
```

### Security Features

- PBKDF2: 100,000 iterations, SHA-256, 128-bit salt
- JWT: HS256, 7-day expiration, version control for invalidation
- Email verification: 24-hour tokens, constant-time comparison
- Password reset: 1-hour tokens
- Cloudflare Workers compatible (no Node.js natives)

## SendGrid Email

Dual email system for transactional and inbound processing.

### Setup Requirements

- Domain verification for `@xswarm.ai`
- DNS records: SPF, DKIM, DMARC
- Inbound parse webhook configuration

### Outbound Email

Transactional emails from `noreply@xswarm.ai`:
- Email verification
- Password reset
- Daily briefings
- Task reminders
- Status notifications

### Inbound Email

Users receive email at `username@xswarm.ai`:
- Webhook parses incoming emails
- Whitelist-based security (contacts only)
- Routes to user's assistant for processing
- Stores in memory for context

### API Endpoints

```
POST /webhooks/sendgrid/inbound  - Parse incoming email
POST /api/email/send             - Send transactional email
GET  /api/email/templates        - List email templates
```

See `sendgrid-email.md` for DNS setup and webhook configuration.

## Twilio Phone & SMS

Voice calls and SMS messaging with MOSHI integration.

### Phone Numbers

- Toll-free numbers provisioned per user
- Voice and SMS capable
- Tier-based limits (1-10+ numbers)

### Voice Calls

```
Incoming Call → Twilio → Media Streams WebSocket → MOSHI Bridge
                                    ↓
                         Audio conversion (mulaw ↔ PCM)
                                    ↓
                              MOSHI response
```

### SMS Messaging

- Inbound: Parse and route to assistant
- Outbound: Notifications, reminders, task updates
- Delivery receipts tracked

### Webhooks

```
POST /webhooks/twilio/voice    - Incoming call handling
POST /webhooks/twilio/sms      - Incoming SMS
POST /webhooks/twilio/status   - Delivery receipts
```

### Usage Tracking

- Voice minutes per call
- SMS count per message
- Automatic overage billing

See `twilio-phone.md` for number provisioning and Media Streams setup.

## Turso Database

Distributed SQLite database with global replication.

### Connection

```javascript
import { createClient } from '@libsql/client';

const db = createClient({
  url: process.env.TURSO_DATABASE_URL,
  authToken: process.env.TURSO_AUTH_TOKEN
});
```

### Core Tables

```sql
users (id, email, password_hash, subscription_tier, stripe_customer_id, email_verified, jwt_version)
personas (id, user_id, name, traits, theme, active)
memory_sessions (id, user_id, summary, embedding, created_at)
memory_facts (id, user_id, fact_text, confidence, category, embedding)
memory_entities (id, user_id, entity_type, name, attributes)
tasks (id, user_id, title, due_date, priority, status, recurring)
usage_records (id, user_id, feature, quantity, recorded_at)
```

### Migrations

```bash
cd packages/server
node scripts/migrate-db.js
```

### GDPR Compliance

- Right to deletion: `DELETE /api/memory/all`
- Data export: Full user data via API
- Retention policies: Automatic cleanup by tier
- Audit trail: Timestamps on all records

See `turso-database.md` for schema details and query patterns.

## Stripe Billing

4-tier subscription with metered usage for overages.

### Products

| Tier | Price | Voice | SMS | Phones |
|------|-------|-------|-----|--------|
| AI Buddy | $0 | 0 | 0 | 0 |
| AI Secretary | $40/mo | 500 min | 500 | 1 |
| AI Project Manager | $280/mo | 2000 min | 2000 | 3 |
| AI CTO | Custom | Unlimited | Unlimited | 10+ |

### Metered Usage

- Voice: $0.013/min overage
- SMS: $0.008/msg overage
- Phone numbers: $2.00/number/mo

### Setup

```bash
npm run setup:stripe              # Test mode
npm run setup:stripe -- --live    # Live mode
npm run setup:stripe -- --force   # Force recreate
```

### Webhooks

```
POST /webhooks/stripe
```

Events handled:
- `checkout.session.completed` - New subscription
- `customer.subscription.updated` - Plan change
- `customer.subscription.deleted` - Cancellation
- `invoice.payment_failed` - Failed payment

### API Endpoints

```
GET  /billing/subscription - Current plan
POST /billing/checkout     - Create checkout session
POST /billing/portal       - Customer portal link
GET  /billing/usage        - Current usage stats
```

See `stripe-payments.md` for product setup and webhook handling.

## Legal Documents

Privacy policy, terms of service, and compliance.

### Required Documents

- Privacy Policy (`/legal/privacy`)
- Terms of Service (`/legal/terms`)
- Acceptable Use Policy (`/legal/acceptable-use`)
- Cookie Policy (`/legal/cookies`)

### Data Handling

- User data stored in Turso (US regions)
- Embeddings via OpenAI API
- Email via SendGrid
- Voice via Twilio
- Payments via Stripe

### Compliance Features

- GDPR: Right to access, deletion, portability
- CCPA: Do not sell, access requests
- SOC 2: Audit logging, encryption at rest

See `legal-documents.md` for policy templates and compliance checklist.

## Feature Gating

Tier-based access control in `src/lib/features.js`:

```javascript
import { hasFeature, checkLimit } from './lib/features.js';

if (hasFeature(tier, 'voice_minutes')) {
  const limit = checkLimit(tier, 'voice_minutes', current);
  if (!limit.allowed) {
    return generateUpgradeMessage('voice_minutes', tier);
  }
}
```

See `tier-features.md` for complete feature matrix.

## Environment Variables

```bash
# Database
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...

# Authentication
JWT_SECRET=<openssl rand -base64 64>
BASE_URL=https://xswarm.ai

# Stripe
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email
SENDGRID_API_KEY=SG....
FROM_EMAIL=noreply@xswarm.ai

# Twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
```

## Cloudflare Workers Constraints

### No Node.js Natives

Cannot use: `crypto`, `fs`, `child_process`, native addons

### Workarounds

- `@noble/hashes` for PBKDF2
- `jsonwebtoken` for JWT
- Turso for database (HTTP-based)

## Development

```bash
cd packages/server
pnpm install
pnpm run dev  # http://localhost:8787
```

## Deployment

```bash
wrangler deploy
wrangler secret put JWT_SECRET
wrangler secret put STRIPE_SECRET_KEY
wrangler secret put SENDGRID_API_KEY
wrangler secret put TWILIO_AUTH_TOKEN
```

## Detailed Documentation

- `tier-features.md` - Complete 4-tier feature matrix with limits and overages
- `sendgrid-email.md` - Email setup, DNS, inbound parsing
- `twilio-phone.md` - Number provisioning, Media Streams, SMS
- `turso-database.md` - Schema, migrations, query patterns
- `stripe-payments.md` - Products, webhooks, metered billing
- `legal-documents.md` - Privacy policy, ToS, compliance

## Testing

```bash
cd packages/server
pnpm run test
```
