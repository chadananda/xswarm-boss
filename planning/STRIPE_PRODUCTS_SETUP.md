# Stripe Products & Prices Setup Guide

Complete guide for setting up Stripe subscription products and metered billing for xSwarm's 4-tier subscription structure.

## Overview

The `setup-stripe-products.js` script programmatically creates all subscription products, prices, and metered usage items in your Stripe account using the Stripe API.

## What Gets Created

### Subscription Products (4 Tiers)

1. **AI Buddy** (Free Tier)
   - Price: $0.00/month
   - Features: 100 emails/day, basic AI assistance
   - Target: Free trial users, personal use

2. **AI Secretary** (Professional Tier)
   - Price: $40.00/month
   - Features: Unlimited email, 500 voice minutes, 500 SMS, 1 phone number
   - Target: Professionals, small businesses

3. **AI Project Manager** (Team Tier)
   - Price: $280.00/month
   - Features: All features, 2000 voice minutes, 2000 SMS, 3 phone numbers, team management
   - Target: Growing teams, agencies

4. **AI CTO** (Enterprise Tier)
   - Price: Custom (contact sales)
   - Features: Unlimited everything, 10+ phone numbers, dedicated resources
   - Target: Large enterprises, custom needs

### Metered Usage Prices (Overages)

1. **Voice Minutes**
   - Rate: $0.013 per minute
   - Applied when: User exceeds included voice minutes

2. **SMS Messages**
   - Rate: $0.008 per message
   - Applied when: User exceeds included SMS messages

3. **Additional Phone Numbers**
   - Rate: $2.00 per number per month
   - Applied when: User adds phone numbers beyond included amount

## Prerequisites

### 1. Stripe Account Setup

1. Create a Stripe account at https://stripe.com
2. Get your API keys:
   - Go to: Developers → API Keys
   - Copy **Secret Key** (starts with `sk_test_` or `sk_live_`)
   - Copy **Publishable Key** (starts with `pk_test_` or `pk_live_`)

### 2. Environment Configuration

Add your Stripe keys to `.env`:

```bash
# Test mode (for development)
STRIPE_SECRET_KEY_TEST=sk_test_51...
STRIPE_WEBHOOK_SECRET_TEST=whsec_...

# Live mode (for production)
STRIPE_SECRET_KEY_LIVE=sk_live_51...
STRIPE_WEBHOOK_SECRET_LIVE=whsec_...
```

Add publishable keys to `config.toml`:

```toml
[stripe]
publishable_key_test = "pk_test_51..."
publishable_key_live = "pk_live_51..."
```

## Usage

### Basic Usage (Test Mode)

Run the script in test mode (safe for development):

```bash
npm run setup:stripe
```

Or directly:

```bash
node scripts/setup-stripe-products.js
```

### Production Setup (Live Mode)

For production, use the `--live` flag:

```bash
node scripts/setup-stripe-products.js --live
```

**Warning:** This creates real products in your live Stripe account!

### Force Recreate

To archive old products and create fresh ones:

```bash
node scripts/setup-stripe-products.js --force
```

## What the Script Does

### Step 1: Verify Connection

- Validates Stripe API key
- Confirms connection to Stripe
- Shows available balance
- Detects test vs live mode

### Step 2: Create Products

For each tier:
1. Checks if product already exists (by metadata)
2. Creates new product OR updates existing product
3. Creates pricing for the product
4. Stores product and price IDs

### Step 3: Create Metered Prices

For each usage type:
1. Creates dedicated product for the metered item
2. Creates metered price with `usage_type: metered`
3. Configures per-unit billing

### Step 4: Update Config

- Automatically updates `config.toml` with all price IDs
- Maintains backward compatibility with legacy mappings
- Preserves other config sections

### Step 5: Display Summary

- Shows all created products and prices
- Provides Stripe Dashboard links
- Lists next steps

## Configuration File Updates

The script automatically updates `config.toml`:

```toml
[stripe.prices]
# New 4-tier subscription prices
ai_buddy = "price_1SNfOARfk9upK3BeVL15MBCo"           # Free tier
ai_secretary = "price_1SNfOBRfk9upK3BepnFbldcs"       # $40/month
ai_project_manager = "price_1SNfOdRfk9upK3BegXBAYz0z" # $280/month
ai_cto = "price_1SNfOeRfk9upK3Benxw8PKds"             # Enterprise

# Metered usage prices (for overages)
voice = "price_1SNfOfRfk9upK3BeqSfse2OH"    # Voice minutes (metered)
sms = "price_1SNfOgRfk9upK3BeZTkdPV9R"      # SMS messages (metered)
phone = "price_1SNfOhRfk9upK3Be0t9n94vl"    # Additional phone numbers

# Legacy tier mappings (for backward compatibility)
premium = "price_1SNfOBRfk9upK3BepnFbldcs"  # Maps to ai_secretary
```

## Idempotency & Safety

The script is designed to be **idempotent** (safe to run multiple times):

### First Run
- Creates all products and prices
- Updates config.toml

### Subsequent Runs
- Detects existing products by metadata
- Updates product details (name, description)
- Reuses existing prices (doesn't create duplicates)
- Updates config.toml with current IDs

### Force Recreate (`--force`)
- Archives old products (sets `active: false`)
- Creates brand new products and prices
- Use this if you need to start fresh

## Verification

### 1. Check Stripe Dashboard

Visit your Stripe Dashboard:
- Test mode: https://dashboard.stripe.com/test/products
- Live mode: https://dashboard.stripe.com/products

Verify all 4 subscription products exist:
- AI Buddy
- AI Secretary
- AI Project Manager
- AI CTO

And 3 metered usage products:
- Voice Minutes (Overage)
- SMS Messages (Overage)
- Additional Phone Numbers

### 2. Verify Config

Check that `config.toml` has real price IDs:

```bash
grep -A 10 "[stripe.prices]" config.toml
```

All price IDs should start with `price_` (not `price_xxx...`).

### 3. Test Subscription Creation

Run the Stripe test script:

```bash
npm run test:stripe
```

This will:
- Verify API connection
- Check all price IDs are valid
- Optionally create a test subscription
- Report usage for metered items

## Troubleshooting

### Authentication Error

```
❌ STRIPE_SECRET_KEY_TEST not found in .env
```

**Solution:** Add your Stripe secret key to `.env`:
```bash
STRIPE_SECRET_KEY_TEST=sk_test_51...
```

### Invalid Price ID

```
⚠️ Premium price ID not found: price_xxxxxxxxxxxxxxxxxxxxx
```

**Solution:** Run the setup script to create products:
```bash
npm run setup:stripe
```

### Live Mode Warning

```
⚠️ WARNING: You are using LIVE mode API keys!
```

**Solution:** This is intentional if you want to create production products. Use the `--live` flag to confirm:
```bash
node scripts/setup-stripe-products.js --live
```

For development, use test mode keys instead.

### Permission Error

```
❌ API key lacks required permissions
```

**Solution:** Create a new API key with these permissions:
- Products: Read & Write
- Prices: Read & Write
- Customers: Read & Write (for testing)

## Next Steps

After running the setup script:

### 1. Review Products

Open Stripe Dashboard and verify:
- Product names and descriptions are correct
- Prices are accurate
- Metadata is properly set

### 2. Test Subscription Flow

Create a test subscription:

```bash
npm run test:stripe
```

When prompted, answer "yes" to create a test subscription.

### 3. Setup Webhooks

Configure Stripe webhooks to receive events:

```bash
npm run setup:webhooks
```

This creates webhook endpoints for:
- Subscription created/updated/deleted
- Invoice payment succeeded/failed
- Customer created/updated

### 4. Deploy to Production

Once tested in test mode:

1. Run setup script in live mode:
   ```bash
   node scripts/setup-stripe-products.js --live
   ```

2. Commit updated config:
   ```bash
   git add config.toml
   git commit -m "Add Stripe product price IDs"
   ```

3. Deploy to production:
   ```bash
   npm run deploy:production
   ```

### 5. Setup Billing Portal

Configure Stripe Customer Portal:
1. Go to: Settings → Billing → Customer Portal
2. Enable customer portal
3. Configure features:
   - Update payment method
   - Update subscription
   - Cancel subscription
   - View invoices

## Pricing Strategy

### Base Subscription Tiers

| Tier | Monthly Price | Target Segment |
|------|--------------|----------------|
| AI Buddy | $0 | Free users, trials |
| AI Secretary | $40 | Professionals, solo |
| AI Project Manager | $280 | Teams, agencies |
| AI CTO | Custom | Enterprise, custom |

### Overage Rates

| Resource | Rate | Applied To |
|----------|------|------------|
| Voice Minutes | $0.013/min | AI Secretary, AI PM |
| SMS Messages | $0.008/msg | AI Secretary, AI PM |
| Phone Numbers | $2.00/number/mo | All paid tiers |

### Pricing Philosophy

1. **Free Tier**: Email-only to prove value
2. **Professional**: Affordable for individuals ($40)
3. **Team**: 7x price for 4x resources (volume discount)
4. **Enterprise**: Custom pricing for unlimited usage

## Script Architecture

### Key Components

1. **Product Configuration (`PRODUCTS_CONFIG`)**
   - Defines all subscription tiers
   - Includes metadata for feature checks
   - Specifies pricing and intervals

2. **Metered Configuration (`METERED_CONFIG`)**
   - Defines usage-based pricing
   - Per-unit rates for overages
   - Metadata for usage tracking

3. **Idempotency Logic**
   - Finds existing products by metadata
   - Reuses prices when possible
   - Only creates when necessary

4. **Config Update Logic**
   - Parses `config.toml`
   - Updates `[stripe.prices]` section
   - Preserves other config sections

### Error Handling

The script handles:
- Missing API keys
- Invalid credentials
- Network errors
- Duplicate products
- Permission errors

## Development

### Testing Changes

To test script changes without affecting production:

1. Use test mode (default):
   ```bash
   npm run setup:stripe
   ```

2. Check Stripe test dashboard
3. Verify config.toml updates
4. Run test suite:
   ```bash
   npm run test:stripe
   ```

### Modifying Pricing

To change prices:

1. Update `PRODUCTS_CONFIG` or `METERED_CONFIG` in the script
2. Run with `--force` to recreate:
   ```bash
   node scripts/setup-stripe-products.js --force
   ```
3. Old prices are archived (not deleted)
4. New prices are created and activated

### Adding New Tiers

To add a new subscription tier:

1. Add configuration to `PRODUCTS_CONFIG`
2. Add price ID field to `config.toml`
3. Run setup script
4. Update application code to handle new tier

## Best Practices

### Test Mode First

Always test in test mode before live:
```bash
# Test mode (safe)
npm run setup:stripe

# Review in dashboard
# Test subscription creation
# Verify everything works

# Then live mode
node scripts/setup-stripe-products.js --live
```

### Version Control

Commit config changes after setup:
```bash
git add config.toml
git commit -m "Update Stripe price IDs for new tier structure"
```

### Documentation

Keep pricing documentation in sync:
- Update marketing pages
- Update API documentation
- Update user-facing pricing page

### Monitoring

After deployment:
- Monitor webhook delivery
- Check subscription creation
- Verify usage reporting
- Review invoices

## Support

### Resources

- Stripe Dashboard: https://dashboard.stripe.com
- Stripe API Docs: https://stripe.com/docs/api
- xSwarm Docs: https://docs.xswarm.dev

### Getting Help

If you encounter issues:

1. Check this documentation
2. Review Stripe Dashboard logs
3. Check webhook delivery
4. Test with `npm run test:stripe`
5. Contact team lead or open GitHub issue

## Changelog

### v1.0.0 (2025-01-29)
- Initial release
- 4-tier subscription structure
- Metered usage for overages
- Automatic config.toml updates
- Idempotent operation
- Test and live mode support
