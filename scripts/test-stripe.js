#!/usr/bin/env node

/**
 * Stripe Connection Test Script
 *
 * Tests Stripe API credentials and subscription setup
 *
 * Usage:
 *   node scripts/test-stripe.js
 */

import 'dotenv/config';
import Stripe from 'stripe';

const {
  STRIPE_SECRET_KEY,
  STRIPE_PUBLISHABLE_KEY,
  STRIPE_PRICE_PREMIUM,
  STRIPE_PRICE_VOICE,
  STRIPE_PRICE_SMS,
  STRIPE_PRICE_PHONE,
  TEST_USER_EMAIL = 'test@example.com'
} = process.env;

// Validate environment variables
function validateEnv() {
  const missing = [];

  if (!STRIPE_SECRET_KEY) {
    missing.push('STRIPE_SECRET_KEY');
  }
  if (!STRIPE_PUBLISHABLE_KEY) {
    missing.push('STRIPE_PUBLISHABLE_KEY');
  }

  if (missing.length > 0) {
    console.error('❌ Missing or unconfigured environment variables:');
    missing.forEach(key => console.error(`   - ${key}`));
    console.error('\nPlease update your .env file with Stripe credentials.');
    console.error('See planning/STRIPE_SETUP.md for setup instructions.');
    process.exit(1);
  }
}

async function testStripeConnection() {
  console.log('💳 Stripe Subscription Test\n');

  // Validate environment
  validateEnv();

  // Detect test vs live mode
  const isTestMode = STRIPE_SECRET_KEY.startsWith('sk_test_');
  const mode = isTestMode ? 'Test Mode' : 'Live Mode';

  console.log('✓ Environment variables configured');
  console.log(`  Mode: ${mode}`);
  console.log(`  Secret Key: ${STRIPE_SECRET_KEY.substring(0, 15)}...`);
  console.log(`  Publishable Key: ${STRIPE_PUBLISHABLE_KEY.substring(0, 15)}...`);

  if (!isTestMode) {
    console.error('\n⚠️  WARNING: You are using LIVE mode API keys!');
    console.error('   This will create real charges. Use test mode for development.\n');
  } else {
    console.log('  ✓ Using test mode (safe for development)\n');
  }

  // Initialize Stripe client
  const stripe = new Stripe(STRIPE_SECRET_KEY);

  try {
    // Test 1: Verify API key
    console.log('🔑 Test 1: Verifying Stripe API key...');
    const balance = await stripe.balance.retrieve();
    console.log(`✓ API key verified`);
    console.log(`  Available: ${balance.available[0]?.amount / 100 || 0} ${balance.available[0]?.currency?.toUpperCase() || 'USD'}`);
    console.log(`  Pending: ${balance.pending[0]?.amount / 100 || 0} ${balance.pending[0]?.currency?.toUpperCase() || 'USD'}\n`);

    // Test 2: Check products and prices
    console.log('📦 Test 2: Checking product configuration...');

    if (STRIPE_PRICE_PREMIUM) {
      try {
        const premiumPrice = await stripe.prices.retrieve(STRIPE_PRICE_PREMIUM);
        console.log(`✓ Premium subscription price found`);
        console.log(`  Price: ${premiumPrice.unit_amount / 100} ${premiumPrice.currency.toUpperCase()}/${premiumPrice.recurring?.interval || 'one-time'}`);
        console.log(`  Product: ${premiumPrice.product}`);
      } catch (err) {
        console.warn(`⚠️  Premium price ID not found: ${STRIPE_PRICE_PREMIUM}`);
      }
    } else {
      console.warn(`⚠️  STRIPE_PRICE_PREMIUM not configured in .env`);
    }

    if (STRIPE_PRICE_VOICE) {
      try {
        const voicePrice = await stripe.prices.retrieve(STRIPE_PRICE_VOICE);
        console.log(`✓ Voice minutes price found`);
        console.log(`  Price: ${voicePrice.unit_amount / 100} ${voicePrice.currency.toUpperCase()} per ${voicePrice.recurring?.usage_type || 'unit'}`);
      } catch (err) {
        console.warn(`⚠️  Voice price ID not found: ${STRIPE_PRICE_VOICE}`);
      }
    } else {
      console.warn(`⚠️  STRIPE_PRICE_VOICE not configured in .env`);
    }

    if (STRIPE_PRICE_SMS) {
      try {
        const smsPrice = await stripe.prices.retrieve(STRIPE_PRICE_SMS);
        console.log(`✓ SMS messages price found`);
        console.log(`  Price: ${smsPrice.unit_amount / 100} ${smsPrice.currency.toUpperCase()} per ${smsPrice.recurring?.usage_type || 'unit'}`);
      } catch (err) {
        console.warn(`⚠️  SMS price ID not found: ${STRIPE_PRICE_SMS}`);
      }
    } else {
      console.warn(`⚠️  STRIPE_PRICE_SMS not configured in .env`);
    }

    console.log();

    // Test 3: List recent customers
    console.log('👥 Test 3: Checking recent customers...');
    const customers = await stripe.customers.list({ limit: 5 });
    console.log(`✓ Found ${customers.data.length} recent customers`);
    if (customers.data.length > 0) {
      customers.data.forEach((customer, i) => {
        console.log(`  ${i + 1}. ${customer.email || 'No email'} (${customer.id})`);
      });
    } else {
      console.log('  (No customers yet)');
    }
    console.log();

    // Test 4: Test subscription creation (dry run)
    console.log('💰 Test 4: Ready to test subscription creation!\n');
    console.log('This will create a test customer and subscription in Stripe.');
    console.log('It\'s safe in test mode and can be deleted afterwards.\n');

    if (!isTestMode) {
      console.error('❌ Skipping subscription test in LIVE mode (safety precaution).');
      console.error('   Use test mode API keys for testing.\n');
      process.exit(0);
    }

    console.log('Do you want to create a test subscription? (yes/no)');

    // Simple prompt for confirmation
    const readline = await import('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.question('> ', async (answer) => {
      if (answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y') {
        console.log('\n📝 Creating test subscription...');

        try {
          // Step 1: Create test customer
          console.log('  Step 1: Creating test customer...');
          const customer = await stripe.customers.create({
            email: TEST_USER_EMAIL,
            description: 'xSwarm Test Customer',
            metadata: {
              environment: 'test',
              created_by: 'test-stripe.js'
            }
          });
          console.log(`  ✓ Customer created: ${customer.id}`);

          // Step 2: Create test payment method (test card)
          console.log('  Step 2: Creating test payment method...');
          const paymentMethod = await stripe.paymentMethods.create({
            type: 'card',
            card: {
              number: '4242424242424242',  // Test card
              exp_month: 12,
              exp_year: 2030,
              cvc: '123',
            },
          });
          console.log(`  ✓ Payment method created: ${paymentMethod.id}`);

          // Step 3: Attach payment method to customer
          console.log('  Step 3: Attaching payment method...');
          await stripe.paymentMethods.attach(paymentMethod.id, {
            customer: customer.id,
          });
          console.log(`  ✓ Payment method attached`);

          // Step 4: Set default payment method
          console.log('  Step 4: Setting default payment method...');
          await stripe.customers.update(customer.id, {
            invoice_settings: {
              default_payment_method: paymentMethod.id,
            },
          });
          console.log(`  ✓ Default payment method set`);

          // Step 5: Create subscription
          console.log('  Step 5: Creating subscription with metered billing...');

          const subscriptionItems = [];

          // Add base premium subscription
          if (STRIPE_PRICE_PREMIUM) {
            subscriptionItems.push({ price: STRIPE_PRICE_PREMIUM });
          }

          // Add metered voice minutes
          if (STRIPE_PRICE_VOICE) {
            subscriptionItems.push({ price: STRIPE_PRICE_VOICE });
          }

          // Add metered SMS
          if (STRIPE_PRICE_SMS) {
            subscriptionItems.push({ price: STRIPE_PRICE_SMS });
          }

          if (subscriptionItems.length === 0) {
            console.error('\n❌ No price IDs configured in .env');
            console.error('   Please set STRIPE_PRICE_PREMIUM, STRIPE_PRICE_VOICE, and STRIPE_PRICE_SMS');
            console.error('   See planning/STRIPE_SETUP.md for setup instructions\n');
            rl.close();
            return;
          }

          const subscription = await stripe.subscriptions.create({
            customer: customer.id,
            items: subscriptionItems,
            metadata: {
              environment: 'test',
              tier: 'premium'
            }
          });

          console.log(`  ✓ Subscription created: ${subscription.id}`);
          console.log(`  Status: ${subscription.status}`);
          console.log(`  Current period: ${new Date(subscription.current_period_start * 1000).toLocaleDateString()} - ${new Date(subscription.current_period_end * 1000).toLocaleDateString()}`);

          // Show subscription items
          console.log('\n  Subscription Items:');
          subscription.items.data.forEach((item, i) => {
            console.log(`    ${i + 1}. ${item.price.id} (${item.id})`);
          });

          // Test 5: Report usage for metered items
          console.log('\n  Step 6: Testing usage reporting...');

          // Find metered subscription items
          const voiceItem = subscription.items.data.find(item => item.price.id === STRIPE_PRICE_VOICE);
          const smsItem = subscription.items.data.find(item => item.price.id === STRIPE_PRICE_SMS);

          if (voiceItem) {
            console.log('  Reporting 25 voice minutes...');
            await stripe.subscriptionItems.createUsageRecord(
              voiceItem.id,
              {
                quantity: 25,
                timestamp: Math.floor(Date.now() / 1000),
                action: 'increment'
              }
            );
            console.log(`  ✓ Voice usage reported`);
          }

          if (smsItem) {
            console.log('  Reporting 10 SMS messages...');
            await stripe.subscriptionItems.createUsageRecord(
              smsItem.id,
              {
                quantity: 10,
                timestamp: Math.floor(Date.now() / 1000),
                action: 'increment'
              }
            );
            console.log(`  ✓ SMS usage reported`);
          }

          // Show upcoming invoice
          console.log('\n  Step 7: Fetching upcoming invoice...');
          const upcomingInvoice = await stripe.invoices.retrieveUpcoming({
            customer: customer.id,
          });

          console.log(`  ✓ Upcoming invoice preview:`);
          console.log(`    Subtotal: $${(upcomingInvoice.subtotal / 100).toFixed(2)}`);
          console.log(`    Total: $${(upcomingInvoice.total / 100).toFixed(2)}`);
          console.log(`    Due: ${new Date(upcomingInvoice.period_end * 1000).toLocaleDateString()}`);

          console.log('\n✅ Test subscription created successfully!');
          console.log(`\nView in Stripe Dashboard:`);
          console.log(`  Customer: https://dashboard.stripe.com/test/customers/${customer.id}`);
          console.log(`  Subscription: https://dashboard.stripe.com/test/subscriptions/${subscription.id}`);
          console.log(`\nTo clean up, delete the test customer in Stripe Dashboard.\n`);

          rl.close();

        } catch (err) {
          console.error(`\n❌ Subscription creation failed: ${err.message}`);

          if (err.type === 'StripeInvalidRequestError') {
            console.error('\nPossible causes:');
            console.error('- Invalid price IDs in .env');
            console.error('- Products not created in Stripe Dashboard');
            console.error('- API key lacks required permissions');
          }

          rl.close();
        }
      } else {
        console.log('\n✓ Skipping subscription test.');
        console.log('\n✅ All Stripe connection tests passed!');
        console.log('   You can run this script again to create a test subscription.\n');
        rl.close();
      }
    });

  } catch (error) {
    console.error(`\n❌ Stripe API Error: ${error.message}`);

    if (error.type === 'StripeAuthenticationError') {
      console.error('\nAuthentication failed. Check your API keys.');
      console.error('Get keys: Stripe Dashboard → Developers → API Keys');
    } else if (error.type === 'StripePermissionError') {
      console.error('\nAPI key lacks required permissions.');
      console.error('Create a new key with full access or appropriate restrictions.');
    }

    process.exit(1);
  }
}

// Run tests
testStripeConnection().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
