# Stripe Setup - Quick Start Guide

Get your Stripe subscription products set up in 5 minutes.

## Prerequisites

1. **Stripe Account**: Sign up at https://stripe.com
2. **API Keys**: Get from Stripe Dashboard → Developers → API Keys

## Step 1: Add API Keys to .env

```bash
# Add to .env file
STRIPE_SECRET_KEY_TEST=<YOUR_STRIPE_TEST_KEY>
STRIPE_SECRET_KEY_LIVE=<YOUR_STRIPE_LIVE_KEY>
```

## Step 2: Run Setup Script

```bash
npm run setup:stripe
```

This will:
- Create 4 subscription products (Free, $40, $280, Enterprise)
- Create 3 metered usage prices (voice, SMS, phone)
- Update config.toml with all price IDs

## Step 3: Verify

Check Stripe Dashboard:
```
https://dashboard.stripe.com/test/products
```

You should see:
- AI Buddy ($0/month)
- AI Secretary ($40/month)
- AI Project Manager ($280/month)
- AI CTO (Custom pricing)
- Voice Minutes (Overage)
- SMS Messages (Overage)
- Additional Phone Numbers

## Step 4: Test Subscriptions

```bash
npm run test:stripe
```

Answer "yes" when prompted to create a test subscription.

## Step 5: Setup Webhooks

```bash
npm run setup:webhooks
```

## Done!

Your Stripe products are now configured. For production:

```bash
node scripts/setup-stripe-products.js --live
```

## Troubleshooting

**Missing API keys?**
```bash
# Check .env file exists and has keys
cat .env | grep STRIPE
```

**Want to start fresh?**
```bash
npm run setup:stripe -- --force
```

**Need help?**
See full documentation: `planning/STRIPE_PRODUCTS_SETUP.md`
