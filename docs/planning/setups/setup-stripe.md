# Stripe Setup Guide - Subscriptions & Usage-Based Billing

This guide walks you through setting up Stripe for xSwarm's subscription system with pay-as-you-go overage charges.

## Overview

xSwarm uses Stripe for a **hybrid billing model**:

1. **Fixed Monthly Subscription** - $9.99/month for Premium tier
2. **Usage-Based Billing** - Pay-as-you-go for overages:
   - Voice minutes over 100/month
   - SMS messages over 100/month
   - Additional phone numbers

**Key Features:**
- Automatic monthly billing
- Real-time usage tracking
- Prorated charges for mid-month upgrades
- Flexible overage pricing
- Self-service subscription management

---

## Pricing Structure

### Free Tier

| Feature | Limit | Cost |
|---------|-------|------|
| Email | 100/day | $0 |
| **Total** | | **$0/month** |

### Premium Tier

| Feature | Included | Overage Rate |
|---------|----------|--------------|
| **Base Subscription** | All features | **$9.99/month** |
| Email | Unlimited | Free |
| Toll-Free Phone Number | 1 number | $2/month per additional |
| Voice Minutes | 100 min/month | $0.013/min |
| SMS Messages | 100 messages/month | $0.0075/message |

**Example Bill:**
```
Premium Subscription         $9.99
Phone Number (1 included)    $0.00
Voice: 150 minutes           $0.65  (50 min overage × $0.013)
SMS: 120 messages            $0.15  (20 msg overage × $0.0075)
─────────────────────────────────
Total:                      $10.79
```

---

## Step 1: Create Stripe Account

### Signup

1. Go to [stripe.com](https://stripe.com)
2. Click **Start now**
3. Complete signup with email
4. Verify email address
5. Complete business profile

### Test Mode vs Live Mode

Stripe provides two environments:

**Test Mode** (Development):
- Use test API keys
- Test credit cards (4242 4242 4242 4242)
- No real charges
- Full webhook testing

**Live Mode** (Production):
- Real API keys
- Real credit cards
- Actual charges
- Production webhooks

**🔧 Always start in Test Mode!**

---

## Step 2: Create Products & Prices

### Product 1: Premium Subscription (Fixed Price)

1. **In Stripe Dashboard:**
   - Products → **Create product**

2. **Product Details:**
   ```
   Name: xSwarm Premium
   Description: AI CTO with multi-channel communication (Email, Phone, SMS)
   Statement descriptor: XSWARM PREMIUM
   ```

3. **Pricing:**
   ```
   Pricing model: Standard pricing
   Price: $9.99 USD
   Billing period: Monthly
   ```

4. **Save** → Note the **Price ID**: `price_xxxxxxxxxxxxxxxxxxxxx`

### Product 2: Voice Minutes (Metered Billing)

1. **Create product:**
   ```
   Name: Voice Minutes
   Description: Outbound/inbound voice call minutes
   ```

2. **Pricing:**
   ```
   Pricing model: Usage-based pricing
   Price: $0.013 USD per minute
   Billing period: Monthly
   Usage is metered
   Charge for metered usage: During each billing period
   ```

3. **Save** → Note the **Price ID**: `price_xxxxxxxxxxxxxxxxxxxxx`

### Product 3: SMS Messages (Metered Billing)

1. **Create product:**
   ```
   Name: SMS Messages
   Description: Outbound/inbound text messages
   ```

2. **Pricing:**
   ```
   Pricing model: Usage-based pricing
   Price: $0.0075 USD per message
   Billing period: Monthly
   Charge for metered usage: During each billing period
   ```

3. **Save** → Note the **Price ID**: `price_xxxxxxxxxxxxxxxxxxxxx`

### Product 4: Additional Phone Numbers

1. **Create product:**
   ```
   Name: Additional Phone Number
   Description: Toll-free phone number (beyond first included number)
   ```

2. **Pricing:**
   ```
   Pricing model: Standard pricing
   Price: $2.00 USD
   Billing period: Monthly
   ```

3. **Save** → Note the **Price ID**: `price_xxxxxxxxxxxxxxxxxxxxx`

---

## Step 3: Get API Keys

### Test Mode Keys (Development)

1. **In Stripe Dashboard:**
   - Developers → **API keys**
   - Toggle to **Test mode** (top right)

2. **Copy Keys:**
   ```
   Publishable key: pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   Secret key: ***REMOVED***xxxxx
   ```

3. **Add to `.env`:**
   ```bash
   STRIPE_SECRET_KEY="***REMOVED***xxxxx"
   STRIPE_PUBLISHABLE_KEY="pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

   # Product Price IDs (Test Mode)
   STRIPE_PRICE_PREMIUM="price_xxxxxxxxxxxxxxxxxxxxx"
   STRIPE_PRICE_VOICE="price_xxxxxxxxxxxxxxxxxxxxx"
   STRIPE_PRICE_SMS="price_xxxxxxxxxxxxxxxxxxxxx"
   STRIPE_PRICE_PHONE="price_xxxxxxxxxxxxxxxxxxxxx"
   ```

### Live Mode Keys (Production)

⚠️ **Only use after thorough testing!**

1. Toggle to **Live mode**
2. Repeat product creation in Live mode
3. Copy Live API keys
4. Store securely (environment variables, secrets manager)

---

## Step 4: Configure Webhooks

Webhooks notify your server about subscription events (created, updated, cancelled, payment failed).

### Create Webhook Endpoint

1. **In Stripe Dashboard:**
   - Developers → **Webhooks**
   - Click **Add endpoint**

2. **Configure Endpoint:**
   ```
   Endpoint URL: https://your-server.com/stripe/webhook

   Events to send:
   ✓ customer.subscription.created
   ✓ customer.subscription.updated
   ✓ customer.subscription.deleted
   ✓ invoice.payment_succeeded
   ✓ invoice.payment_failed
   ✓ customer.created
   ✓ customer.updated
   ```

3. **Signing Secret:**
   - After creating, reveal **Signing secret**
   - Copy: `***REMOVED***`
   - Add to `.env`:
     ```bash
     STRIPE_WEBHOOK_SECRET="***REMOVED***"
     ```

### Test Webhook Locally

Use Stripe CLI for local webhook testing:

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login to Stripe
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:3000/stripe/webhook

# Test webhook
stripe trigger customer.subscription.created
```

---

## Step 5: Create Subscription Flow

### Backend Implementation (Rust)

```rust
// Create customer and subscription
use stripe::{Client, Customer, Subscription, CreateSubscription};

async fn create_premium_subscription(
    user_email: &str,
    payment_method: &str,
) -> Result<Subscription> {
    let client = Client::new(env::var("STRIPE_SECRET_KEY")?);

    // 1. Create customer
    let customer = Customer::create(&client, CreateCustomer {
        email: Some(user_email),
        ..Default::default()
    }).await?;

    // 2. Attach payment method
    PaymentMethod::attach(&client, payment_method, AttachPaymentMethod {
        customer: customer.id.clone(),
    }).await?;

    // 3. Set default payment method
    Customer::update(&client, &customer.id, UpdateCustomer {
        invoice_settings: Some(InvoiceSettings {
            default_payment_method: Some(payment_method),
            ..Default::default()
        }),
        ..Default::default()
    }).await?;

    // 4. Create subscription with base + metered items
    let subscription = Subscription::create(&client, CreateSubscription {
        customer: customer.id,
        items: vec![
            // Base subscription ($9.99/month)
            CreateSubscriptionItems {
                price: env::var("STRIPE_PRICE_PREMIUM")?,
                ..Default::default()
            },
            // Metered: Voice minutes
            CreateSubscriptionItems {
                price: env::var("STRIPE_PRICE_VOICE")?,
                ..Default::default()
            },
            // Metered: SMS messages
            CreateSubscriptionItems {
                price: env::var("STRIPE_PRICE_SMS")?,
                ..Default::default()
            },
        ],
        ..Default::default()
    }).await?;

    Ok(subscription)
}
```

### Report Usage for Metered Billing

```rust
// Report voice minutes used
async fn report_voice_usage(
    subscription_item_id: &str,
    minutes: u32,
) -> Result<()> {
    let client = Client::new(env::var("STRIPE_SECRET_KEY")?);

    UsageRecord::create(&client, subscription_item_id, CreateUsageRecord {
        quantity: minutes,
        timestamp: Some(Utc::now().timestamp()),
        action: Some(UsageRecordAction::Increment),
        ..Default::default()
    }).await?;

    Ok(())
}

// Report SMS usage
async fn report_sms_usage(
    subscription_item_id: &str,
    messages: u32,
) -> Result<()> {
    let client = Client::new(env::var("STRIPE_SECRET_KEY")?);

    UsageRecord::create(&client, subscription_item_id, CreateUsageRecord {
        quantity: messages,
        timestamp: Some(Utc::now().timestamp()),
        action: Some(UsageRecordAction::Increment),
        ..Default::default()
    }).await?;

    Ok(())
}
```

### Usage Tracking Strategy

**Real-time reporting:**
```rust
// After each voice call
async fn handle_call_completed(call: &Call) -> Result<()> {
    let duration_minutes = (call.duration / 60) + 1; // Round up

    report_voice_usage(
        &call.user.stripe_voice_item_id,
        duration_minutes
    ).await?;

    Ok(())
}

// After each SMS
async fn handle_sms_sent(sms: &Sms) -> Result<()> {
    report_sms_usage(
        &sms.user.stripe_sms_item_id,
        1
    ).await?;

    Ok(())
}
```

---

## Step 6: Handle Webhook Events

```rust
// Webhook handler
async fn handle_stripe_webhook(
    payload: String,
    signature: String,
) -> Result<()> {
    let webhook_secret = env::var("STRIPE_WEBHOOK_SECRET")?;

    // Verify webhook signature
    let event = Webhook::construct_event(
        &payload,
        &signature,
        &webhook_secret
    )?;

    match event.type_ {
        EventType::CustomerSubscriptionCreated => {
            let subscription: Subscription = event.data.object.into();
            handle_subscription_created(subscription).await?;
        }

        EventType::CustomerSubscriptionUpdated => {
            let subscription: Subscription = event.data.object.into();
            handle_subscription_updated(subscription).await?;
        }

        EventType::CustomerSubscriptionDeleted => {
            let subscription: Subscription = event.data.object.into();
            handle_subscription_cancelled(subscription).await?;
        }

        EventType::InvoicePaymentSucceeded => {
            let invoice: Invoice = event.data.object.into();
            handle_payment_succeeded(invoice).await?;
        }

        EventType::InvoicePaymentFailed => {
            let invoice: Invoice = event.data.object.into();
            handle_payment_failed(invoice).await?;
        }

        _ => {
            println!("Unhandled event type: {:?}", event.type_);
        }
    }

    Ok(())
}

async fn handle_subscription_created(subscription: Subscription) -> Result<()> {
    // Update user to premium tier
    database.update_user_subscription(
        &subscription.customer,
        SubscriptionTier::Premium,
        Some(subscription.id),
    ).await?;

    // Provision phone number
    provision_phone_number(&subscription.customer).await?;

    Ok(())
}

async fn handle_subscription_cancelled(subscription: Subscription) -> Result<()> {
    // Downgrade user to free tier
    database.update_user_subscription(
        &subscription.customer,
        SubscriptionTier::Free,
        None,
    ).await?;

    // Release phone number
    release_phone_number(&subscription.customer).await?;

    Ok(())
}

async fn handle_payment_failed(invoice: Invoice) -> Result<()> {
    // Notify user via email
    send_payment_failed_email(&invoice.customer).await?;

    // Grace period: 3 days before downgrade
    schedule_downgrade(&invoice.customer, Duration::days(3)).await?;

    Ok(())
}
```

---

## Step 7: Testing

### Test Credit Cards

Stripe provides test cards for different scenarios:

```
Success: 4242 4242 4242 4242
Decline: 4000 0000 0000 0002
Insufficient funds: 4000 0000 0000 9995
3D Secure required: 4000 0025 0000 3155
```

**CVC:** Any 3 digits
**Expiry:** Any future date
**ZIP:** Any 5 digits

### Test Subscription Creation

```bash
# Run test script
npm run test:stripe

# Or manually test via Stripe CLI
stripe subscriptions create \
  --customer cus_xxxxxxxxxxxxx \
  --items[0][price]=price_xxxxxxxxxxxxx
```

### Test Metered Billing

```bash
# Report usage
stripe usage-records create \
  --subscription-item si_xxxxxxxxxxxxx \
  --quantity 50 \
  --timestamp $(date +%s)

# View usage in dashboard
# Billing → Subscriptions → [Select subscription] → View usage
```

### Verify Webhook Delivery

1. Stripe Dashboard → Developers → Webhooks
2. Click your endpoint
3. View **Event logs** to see delivered events
4. Check **Response** status (should be 200 OK)

---

## Step 8: Customer Portal

Stripe provides a hosted customer portal for self-service subscription management.

### Enable Customer Portal

1. **In Stripe Dashboard:**
   - Settings → **Billing**
   - **Customer portal** → Turn on

2. **Configure Features:**
   ```
   ✓ Update payment method
   ✓ View invoices
   ✓ Cancel subscription
   ✓ Update billing information
   ```

### Generate Portal Link

```rust
// Create customer portal session
async fn create_portal_session(customer_id: &str) -> Result<String> {
    let client = Client::new(env::var("STRIPE_SECRET_KEY")?);

    let session = BillingPortalSession::create(&client, CreateBillingPortalSession {
        customer: customer_id.to_string(),
        return_url: Some("https://xswarm.ai/dashboard".to_string()),
        ..Default::default()
    }).await?;

    Ok(session.url)
}
```

**User clicks "Manage Subscription" → redirected to Stripe portal → self-service billing**

---

## CLI Commands

```bash
# Subscribe to premium
xswarm subscribe premium

# View subscription status
xswarm subscription status

# View current usage
xswarm subscription usage

# Manage billing (opens Stripe portal)
xswarm subscription manage

# Cancel subscription
xswarm subscription cancel
```

---

## Security Best Practices

### API Key Security

- ✅ Store API keys in environment variables (never commit to git)
- ✅ Use restricted API keys in production (limit permissions)
- ✅ Rotate keys periodically
- ✅ Monitor API key usage in Stripe dashboard

### Webhook Security

- ✅ **Always verify webhook signatures**
- ✅ Use HTTPS for webhook endpoint
- ✅ Validate event data before processing
- ✅ Implement idempotency (handle duplicate events)

```rust
// Example: Idempotent webhook processing
async fn process_webhook_event(event: Event) -> Result<()> {
    // Check if event already processed
    if database.event_exists(&event.id).await? {
        return Ok(()); // Already processed, skip
    }

    // Process event
    handle_event(event).await?;

    // Mark as processed
    database.save_event_id(&event.id).await?;

    Ok(())
}
```

---

## Troubleshooting

### Payment Fails During Subscription Creation

**Cause:** Invalid payment method or card decline
**Solution:**
- Verify test card numbers in test mode
- Check card expiry date
- Ensure sufficient funds (in live mode)
- Review Stripe logs for error details

### Webhook Not Receiving Events

**Cause:** Incorrect endpoint URL or firewall blocking
**Solution:**
- Verify endpoint URL is publicly accessible
- Check firewall/security group allows Stripe IPs
- Use Stripe CLI to forward webhooks locally
- Check webhook logs in Stripe dashboard

### Usage Not Being Charged

**Cause:** Missing subscription item or incorrect reporting
**Solution:**
- Verify subscription has metered price items
- Check `subscription_item_id` is correct
- Ensure `UsageRecord::create` is being called
- View usage in Stripe dashboard → Subscriptions

---

## Pricing Calculator

Estimate monthly costs based on usage:

```
Base Premium: $9.99

Voice minutes:
  Included: 100 minutes
  Used: 250 minutes
  Overage: 150 minutes × $0.013 = $1.95

SMS messages:
  Included: 100 messages
  Used: 180 messages
  Overage: 80 messages × $0.0075 = $0.60

Additional phone numbers:
  Extra numbers: 2
  Cost: 2 × $2.00 = $4.00

─────────────────────────────
Total: $16.54/month
```

**Usage-based billing ensures you only pay for what you use beyond the included limits.**

---

## Resources

- [Stripe Documentation](https://stripe.com/docs)
- [Subscriptions Guide](https://stripe.com/docs/billing/subscriptions/overview)
- [Metered Billing](https://stripe.com/docs/billing/subscriptions/usage-based)
- [Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Rust Library](https://github.com/arlyon/async-stripe)
- [Test Cards](https://stripe.com/docs/testing)

---

**Next:** Integrate Stripe API into xSwarm subscription module.
