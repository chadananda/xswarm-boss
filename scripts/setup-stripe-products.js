#!/usr/bin/env node

/**
 * Stripe Products & Prices Setup Script
 *
 * Programmatically creates all subscription products and prices for the
 * 4-tier xSwarm subscription structure using the Stripe API.
 *
 * Creates:
 * - 4 Subscription products (AI Buddy, AI Secretary, AI Project Manager, AI CTO)
 * - Base subscription prices for each tier
 * - 3 Metered usage prices (voice minutes, SMS messages, phone numbers)
 *
 * Updates config.toml with the generated price IDs.
 *
 * Usage:
 *   node scripts/setup-stripe-products.js           # Test mode (default)
 *   node scripts/setup-stripe-products.js --live    # Live mode (production)
 *   node scripts/setup-stripe-products.js --force   # Force recreate products
 *
 * Requirements:
 *   - STRIPE_SECRET_KEY_TEST in .env (for test mode)
 *   - STRIPE_SECRET_KEY_LIVE in .env (for live mode)
 */

import Stripe from 'stripe';
import { loadConfig } from './load-config.js';
import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..');
const configPath = join(rootDir, 'config.toml');

// Parse command line arguments
const args = process.argv.slice(2);
const useLive = args.includes('--live');
const forceRecreate = args.includes('--force');

// Load secrets and config
const { secrets, config } = loadConfig();

// Determine which API key to use
const STRIPE_SECRET_KEY = useLive ? secrets.STRIPE_SECRET_KEY_LIVE : secrets.STRIPE_SECRET_KEY_TEST;

if (!STRIPE_SECRET_KEY) {
  const keyName = useLive ? 'STRIPE_SECRET_KEY_LIVE' : 'STRIPE_SECRET_KEY_TEST';
  console.error(`❌ ${keyName} not found in .env`);
  console.error('\nPlease add your Stripe secret key to .env:');
  console.error(`   ${keyName}=sk_test_...`);
  process.exit(1);
}

// Initialize Stripe
const stripe = new Stripe(STRIPE_SECRET_KEY);

// Detect mode from API key
const isTestMode = STRIPE_SECRET_KEY.startsWith('sk_test_');
const mode = isTestMode ? 'Test' : 'Live';

console.log('\n💳 Stripe Products & Prices Setup\n');
console.log(`Mode: ${mode}`);
console.log(`Force recreate: ${forceRecreate ? 'Yes' : 'No'}\n`);

if (!isTestMode) {
  console.error('⚠️  WARNING: You are using LIVE mode API keys!');
  console.error('   This will create real products in production.\n');

  // Require explicit confirmation for live mode
  if (!useLive) {
    console.error('❌ Live mode detected but --live flag not provided.');
    console.error('   Use --live flag to confirm you want to create production products.');
    process.exit(1);
  }
}

/**
 * Product and price configurations
 */
const PRODUCTS_CONFIG = [
  {
    id: 'ai_buddy',
    name: 'AI Buddy',
    description: 'Free tier - Email communication only with basic AI assistance',
    tier: 'ai_buddy',
    price: 0,
    interval: 'month',
    features: [
      '100 emails per day',
      'Basic AI assistance',
      'Community support',
    ],
    metadata: {
      tier: 'ai_buddy',
      email_limit: '100',
      voice_minutes: '0',
      sms_messages: '0',
      phone_numbers: '0',
    }
  },
  {
    id: 'ai_secretary',
    name: 'AI Secretary',
    description: 'Professional tier - Email, SMS, and voice communication with AI secretary',
    tier: 'ai_secretary',
    price: 4000, // $40.00 in cents
    interval: 'month',
    features: [
      'Unlimited emails',
      '500 voice minutes/month',
      '500 SMS messages/month',
      '1 phone number included',
      'Priority support',
    ],
    metadata: {
      tier: 'ai_secretary',
      email_limit: '-1',
      voice_minutes_included: '500',
      sms_messages_included: '500',
      phone_numbers_included: '1',
    }
  },
  {
    id: 'ai_project_manager',
    name: 'AI Project Manager',
    description: 'Team tier - All features plus team management and advanced automation',
    tier: 'ai_project_manager',
    price: 28000, // $280.00 in cents
    interval: 'month',
    features: [
      'Unlimited emails',
      '2000 voice minutes/month',
      '2000 SMS messages/month',
      '3 phone numbers included',
      'Team management',
      'Advanced automation',
      'Priority support',
    ],
    metadata: {
      tier: 'ai_project_manager',
      email_limit: '-1',
      voice_minutes_included: '2000',
      sms_messages_included: '2000',
      phone_numbers_included: '3',
      team_management: 'true',
    }
  },
  {
    id: 'ai_cto',
    name: 'AI CTO',
    description: 'Enterprise tier - Custom pricing with unlimited usage and dedicated resources',
    tier: 'ai_cto',
    price: null, // Custom pricing
    interval: null,
    features: [
      'Unlimited everything',
      '10+ phone numbers',
      'Dedicated resources',
      'Custom integrations',
      'Phone support',
      '24/7 priority support',
      'SLA guarantees',
    ],
    metadata: {
      tier: 'ai_cto',
      email_limit: '-1',
      voice_minutes_included: '-1',
      sms_messages_included: '-1',
      phone_numbers_included: '10',
      team_management: 'true',
      enterprise_features: 'true',
    }
  }
];

/**
 * Metered usage configurations
 */
const METERED_CONFIG = [
  {
    id: 'voice',
    name: 'Voice Minutes (Overage)',
    description: 'Additional voice minutes beyond included amount',
    price: 13, // $0.013 per minute in cents
    unit: 'minute',
    metadata: {
      usage_type: 'voice_minutes',
      tier: 'metered'
    }
  },
  {
    id: 'sms',
    name: 'SMS Messages (Overage)',
    description: 'Additional SMS messages beyond included amount',
    price: 8, // $0.0075 rounded to $0.008 per message in cents (Stripe minimum)
    unit: 'message',
    metadata: {
      usage_type: 'sms_messages',
      tier: 'metered'
    }
  },
  {
    id: 'phone',
    name: 'Additional Phone Numbers',
    description: 'Additional phone numbers beyond included amount',
    price: 200, // $2.00 per number per month in cents
    unit: 'number',
    metadata: {
      usage_type: 'phone_numbers',
      tier: 'metered'
    }
  }
];

/**
 * Find existing product by metadata
 */
async function findExistingProduct(tier) {
  try {
    const products = await stripe.products.list({
      limit: 100,
      active: true,
    });

    return products.data.find(p => p.metadata.tier === tier);
  } catch (error) {
    console.error(`Error finding existing product: ${error.message}`);
    return null;
  }
}

/**
 * Create or update a product
 */
async function createOrUpdateProduct(productConfig) {
  console.log(`\n📦 ${productConfig.name}...`);

  try {
    // Check if product already exists
    let product = await findExistingProduct(productConfig.tier);

    if (product && !forceRecreate) {
      console.log(`  ℹ️  Product already exists: ${product.id}`);

      // Update product details
      product = await stripe.products.update(product.id, {
        name: productConfig.name,
        description: productConfig.description,
        metadata: productConfig.metadata,
      });
      console.log(`  ✓ Product updated: ${product.id}`);
    } else {
      // Archive old product if force recreate
      if (product && forceRecreate) {
        console.log(`  🗑️  Archiving old product: ${product.id}`);
        await stripe.products.update(product.id, { active: false });
      }

      // Create new product
      product = await stripe.products.create({
        name: productConfig.name,
        description: productConfig.description,
        metadata: productConfig.metadata,
      });
      console.log(`  ✓ Product created: ${product.id}`);
    }

    // Create or find price for this product
    let price = null;

    if (productConfig.price !== null) {
      // Find existing active price for this product
      const prices = await stripe.prices.list({
        product: product.id,
        active: true,
        limit: 10,
      });

      const existingPrice = prices.data.find(p =>
        p.unit_amount === productConfig.price &&
        p.recurring?.interval === productConfig.interval
      );

      if (existingPrice && !forceRecreate) {
        price = existingPrice;
        console.log(`  ℹ️  Price already exists: ${price.id}`);
      } else {
        // Archive old prices if force recreate
        if (forceRecreate && prices.data.length > 0) {
          console.log(`  🗑️  Archiving ${prices.data.length} old price(s)...`);
          for (const oldPrice of prices.data) {
            await stripe.prices.update(oldPrice.id, { active: false });
          }
        }

        // Create new price
        price = await stripe.prices.create({
          product: product.id,
          unit_amount: productConfig.price,
          currency: 'usd',
          recurring: {
            interval: productConfig.interval,
          },
          metadata: {
            tier: productConfig.tier,
          }
        });
        console.log(`  ✓ Price created: ${price.id} ($${(productConfig.price / 100).toFixed(2)}/${productConfig.interval})`);
      }
    } else {
      console.log(`  ℹ️  Enterprise tier - No standard price (custom pricing)`);

      // For enterprise, create a placeholder $0 price for signup flow
      const prices = await stripe.prices.list({
        product: product.id,
        active: true,
        limit: 10,
      });

      const existingPrice = prices.data.find(p => p.unit_amount === 0);

      if (existingPrice && !forceRecreate) {
        price = existingPrice;
        console.log(`  ℹ️  Placeholder price exists: ${price.id}`);
      } else {
        if (forceRecreate && prices.data.length > 0) {
          for (const oldPrice of prices.data) {
            await stripe.prices.update(oldPrice.id, { active: false });
          }
        }

        price = await stripe.prices.create({
          product: product.id,
          unit_amount: 0,
          currency: 'usd',
          metadata: {
            tier: productConfig.tier,
            custom_pricing: 'true',
          }
        });
        console.log(`  ✓ Placeholder price created: ${price.id} (contact sales)`);
      }
    }

    return { product, price };
  } catch (error) {
    console.error(`  ❌ Failed to create product: ${error.message}`);
    throw error;
  }
}

/**
 * Create metered usage price
 */
async function createMeteredPrice(meteredConfig) {
  console.log(`\n⚡ ${meteredConfig.name}...`);

  try {
    // Create a dedicated product for this metered usage
    let product = await findExistingProduct(`metered_${meteredConfig.id}`);

    if (product && !forceRecreate) {
      console.log(`  ℹ️  Product already exists: ${product.id}`);
    } else {
      if (product && forceRecreate) {
        console.log(`  🗑️  Archiving old product: ${product.id}`);
        await stripe.products.update(product.id, { active: false });
      }

      product = await stripe.products.create({
        name: meteredConfig.name,
        description: meteredConfig.description,
        metadata: {
          ...meteredConfig.metadata,
          tier: `metered_${meteredConfig.id}`,
        },
      });
      console.log(`  ✓ Product created: ${product.id}`);
    }

    // Find or create metered price
    const prices = await stripe.prices.list({
      product: product.id,
      active: true,
      limit: 10,
    });

    const existingPrice = prices.data.find(p =>
      p.unit_amount === meteredConfig.price &&
      p.recurring?.usage_type === 'metered'
    );

    let price;
    if (existingPrice && !forceRecreate) {
      price = existingPrice;
      console.log(`  ℹ️  Price already exists: ${price.id}`);
    } else {
      if (forceRecreate && prices.data.length > 0) {
        console.log(`  🗑️  Archiving ${prices.data.length} old price(s)...`);
        for (const oldPrice of prices.data) {
          await stripe.prices.update(oldPrice.id, { active: false });
        }
      }

      price = await stripe.prices.create({
        product: product.id,
        unit_amount: meteredConfig.price,
        currency: 'usd',
        recurring: {
          interval: 'month',
          usage_type: 'metered',
        },
        billing_scheme: 'per_unit',
        metadata: meteredConfig.metadata,
      });
      console.log(`  ✓ Price created: ${price.id} ($${(meteredConfig.price / 100).toFixed(4)}/unit)`);
    }

    return { product, price };
  } catch (error) {
    console.error(`  ❌ Failed to create metered price: ${error.message}`);
    throw error;
  }
}

/**
 * Update config.toml with new price IDs
 */
function updateConfigFile(priceIds) {
  console.log('\n📝 Updating config.toml...');

  try {
    // Read current config
    const configContent = readFileSync(configPath, 'utf-8');
    const lines = configContent.split('\n');

    // Find and update price IDs in [stripe.prices] section
    let inPricesSection = false;
    const updatedLines = lines.map(line => {
      // Detect when we enter the [stripe.prices] section
      if (line.trim() === '[stripe.prices]') {
        inPricesSection = true;
        return line;
      }

      // Detect when we leave the section (next section starts)
      if (inPricesSection && line.trim().startsWith('[') && line.trim() !== '[stripe.prices]') {
        inPricesSection = false;
        return line;
      }

      // Update price IDs in the prices section
      if (inPricesSection) {
        for (const [key, priceId] of Object.entries(priceIds)) {
          const regex = new RegExp(`^(${key}\\s*=\\s*)"[^"]*"`);
          if (regex.test(line)) {
            return line.replace(regex, `$1"${priceId}"`);
          }
        }
      }

      return line;
    });

    // Write updated config
    writeFileSync(configPath, updatedLines.join('\n'), 'utf-8');
    console.log('  ✓ config.toml updated with new price IDs');

    return true;
  } catch (error) {
    console.error(`  ❌ Failed to update config.toml: ${error.message}`);
    console.error('  Please update the price IDs manually in config.toml');
    return false;
  }
}

/**
 * Display summary
 */
function displaySummary(results) {
  console.log('\n' + '='.repeat(60));
  console.log('✅ Stripe Product Setup Complete!');
  console.log('='.repeat(60));

  console.log('\n📋 Subscription Products:');
  for (const tier of ['ai_buddy', 'ai_secretary', 'ai_project_manager', 'ai_cto']) {
    const result = results.subscriptions[tier];
    if (result) {
      console.log(`\n  ${result.config.name}:`);
      console.log(`    Product ID:  ${result.product.id}`);
      console.log(`    Price ID:    ${result.price.id}`);
      if (result.config.price !== null) {
        console.log(`    Amount:      $${(result.config.price / 100).toFixed(2)}/${result.config.interval}`);
      } else {
        console.log(`    Amount:      Custom pricing (contact sales)`);
      }
    }
  }

  console.log('\n⚡ Metered Usage Prices:');
  for (const [id, result] of Object.entries(results.metered)) {
    console.log(`\n  ${result.config.name}:`);
    console.log(`    Product ID:  ${result.product.id}`);
    console.log(`    Price ID:    ${result.price.id}`);
    console.log(`    Amount:      $${(result.config.price / 100).toFixed(4)}/unit`);
  }

  console.log('\n🔗 Stripe Dashboard:');
  const dashboardUrl = isTestMode
    ? 'https://dashboard.stripe.com/test'
    : 'https://dashboard.stripe.com';
  console.log(`  Products: ${dashboardUrl}/products`);
  console.log(`  Prices:   ${dashboardUrl}/prices`);

  console.log('\n📝 Next Steps:');
  console.log('  1. Review products in Stripe Dashboard');
  console.log('  2. Verify config.toml has been updated with price IDs');
  console.log('  3. Test subscription creation: npm run test:stripe');
  console.log('  4. Deploy updated config to production');

  if (isTestMode) {
    console.log('\n⚠️  Remember to run this script in LIVE mode for production:');
    console.log('     node scripts/setup-stripe-products.js --live');
  }

  console.log('');
}

/**
 * Main execution
 */
async function main() {
  try {
    // Verify Stripe API connection
    console.log('🔑 Verifying Stripe API connection...');
    const balance = await stripe.balance.retrieve();
    console.log(`✓ Connected to Stripe (${mode} mode)`);
    console.log(`  Available: $${(balance.available[0]?.amount / 100 || 0).toFixed(2)} ${balance.available[0]?.currency?.toUpperCase() || 'USD'}`);

    const results = {
      subscriptions: {},
      metered: {},
    };

    // Create subscription products and prices
    console.log('\n' + '='.repeat(60));
    console.log('Creating Subscription Products');
    console.log('='.repeat(60));

    for (const productConfig of PRODUCTS_CONFIG) {
      const result = await createOrUpdateProduct(productConfig);
      results.subscriptions[productConfig.id] = {
        ...result,
        config: productConfig,
      };
    }

    // Create metered usage prices
    console.log('\n' + '='.repeat(60));
    console.log('Creating Metered Usage Prices');
    console.log('='.repeat(60));

    for (const meteredConfig of METERED_CONFIG) {
      const result = await createMeteredPrice(meteredConfig);
      results.metered[meteredConfig.id] = {
        ...result,
        config: meteredConfig,
      };
    }

    // Collect all price IDs for config update
    const priceIds = {
      ai_buddy: results.subscriptions.ai_buddy.price.id,
      ai_secretary: results.subscriptions.ai_secretary.price.id,
      ai_project_manager: results.subscriptions.ai_project_manager.price.id,
      ai_cto: results.subscriptions.ai_cto.price.id,
      voice: results.metered.voice.price.id,
      sms: results.metered.sms.price.id,
      phone: results.metered.phone.price.id,
      // Keep legacy premium mapping to ai_secretary for backward compatibility
      premium: results.subscriptions.ai_secretary.price.id,
    };

    // Update config.toml
    updateConfigFile(priceIds);

    // Display summary
    displaySummary(results);

  } catch (error) {
    console.error('\n❌ Setup failed:', error.message);

    if (error.type === 'StripeAuthenticationError') {
      console.error('\nAuthentication failed. Check your API keys in .env');
    } else if (error.type === 'StripePermissionError') {
      console.error('\nAPI key lacks required permissions.');
      console.error('Create a new key with product and price write access.');
    }

    process.exit(1);
  }
}

// Run setup
main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
