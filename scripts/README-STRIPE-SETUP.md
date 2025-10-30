# Stripe Products Setup Script

Quick reference for `setup-stripe-products.js`

## Quick Start

```bash
# Test mode (safe for development)
npm run setup:stripe

# Live mode (production)
node scripts/setup-stripe-products.js --live

# Force recreate all products
node scripts/setup-stripe-products.js --force
```

## What It Does

1. Creates 4 subscription products in Stripe
2. Creates 3 metered usage prices for overages
3. Updates `config.toml` with generated price IDs
4. Idempotent (safe to run multiple times)

## Products Created

### Subscriptions
- **AI Buddy**: $0/month (free tier)
- **AI Secretary**: $40/month (professional)
- **AI Project Manager**: $280/month (team)
- **AI CTO**: Custom pricing (enterprise)

### Metered Usage
- **Voice**: $0.013 per minute
- **SMS**: $0.008 per message
- **Phone**: $2.00 per number/month

## Requirements

Add to `.env`:
```bash
STRIPE_SECRET_KEY_TEST=sk_test_51...
STRIPE_SECRET_KEY_LIVE=sk_live_51...
```

## Verification

After running, check:
1. Stripe Dashboard: https://dashboard.stripe.com/test/products
2. Config file: `grep "price_" config.toml`
3. Test script: `npm run test:stripe`

## Full Documentation

See: `planning/STRIPE_PRODUCTS_SETUP.md`
