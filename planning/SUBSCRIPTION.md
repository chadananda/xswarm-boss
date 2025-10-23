# Subscription Management System

Complete subscription lifecycle management for xSwarm, from signup to cancellation, including on-demand provisioning, usage tracking, and billing.

---

## Overview

xSwarm uses a **hybrid subscription model** that combines:

1. **Fixed monthly fee** - $9.99/month base subscription (premium tier)
2. **Included usage** - 100 voice minutes + 100 SMS per month
3. **Overage billing** - Pay-as-you-go for usage beyond included limits
4. **On-demand provisioning** - Resources (phone numbers) allocated when user upgrades

**Key Design Principles:**
- 💰 **Cost-effective** - Only provision expensive resources when paid for
- 🎯 **Usage-based** - Fair pricing based on actual consumption
- 🔄 **Flexible** - Upgrade/downgrade anytime, prorated billing
- 🚀 **Fast provisioning** - Phone numbers assigned within seconds of payment

---

## Subscription Tiers

### Free Tier

**Price:** $0/month

**Features:**
- Email communication (100 emails/day via SendGrid)
- Unique email address (`username@xswarm.ai`)
- Basic AI CTO capabilities
- Terminal-based voice interface (local only)

**Limitations:**
- ❌ No phone communication
- ❌ No SMS
- ❌ No mobile access
- ❌ Limited to local development

**Perfect for:** Individual developers, testing, local development

---

### Premium Tier

**Price:** $9.99/month

**Includes:**
- ✅ Everything in Free tier
- ✅ Email (unlimited)
- ✅ Toll-free phone number (1 number included)
- ✅ Voice calls (100 minutes/month included)
- ✅ SMS messages (100 messages/month included)
- ✅ Priority support
- ✅ Advanced AI features

**Overage Rates:**
- Voice: $0.013/minute
- SMS: $0.0075/message
- Additional phone numbers: $2/month each

**Perfect for:** Professional developers, remote work, production monitoring

---

### Enterprise Tier (Future)

**Price:** Custom pricing

**Includes:**
- ✅ Everything in Premium tier
- ✅ Multiple phone numbers
- ✅ Team features (shared access)
- ✅ Unlimited voice/SMS (pooled across team)
- ✅ Custom integrations
- ✅ White-label options
- ✅ Dedicated support

**Perfect for:** Development teams, organizations, SaaS companies

---

## Subscription Lifecycle

### 1. Free Tier (Default)

```
User signs up
    ↓
Create user account
    ↓
Provision email: username@xswarm.ai
    ↓
Configure SendGrid forwarding
    ↓
User can immediately receive emails
    ↓
[User stays on free tier]
```

**What gets provisioned:**
- User database record
- Email routing (`username@xswarm.ai` → user's real email)
- Configuration file (`~/.config/xswarm/config.toml`)

**Stripe interaction:** None (free tier doesn't require payment)

---

### 2. Upgrade to Premium

```
User runs: xswarm subscribe premium
    ↓
Display pricing: $9.99/month + overages
    ↓
User confirms
    ↓
Redirect to Stripe Checkout
    ↓
User enters payment details
    ↓
Stripe processes payment
    ↓
[WEBHOOK: customer.subscription.created]
    ↓
Provision toll-free number (Twilio API)
    ↓
Update user config with phone number
    ↓
Send welcome email with details
    ↓
User can immediately make/receive calls
```

**What gets provisioned:**
- Stripe customer record
- Stripe subscription with 3 items:
  1. Base subscription ($9.99/month)
  2. Voice metered billing (item ID saved)
  3. SMS metered billing (item ID saved)
- Toll-free phone number from Twilio pool
- Twilio webhook configuration
- Updated user config with phone details

**Timeline:** < 30 seconds from payment to fully provisioned

---

### 3. Usage Tracking (Premium)

```
User makes phone call
    ↓
Call completes (duration: 15 minutes)
    ↓
Twilio webhook: call.completed
    ↓
xSwarm calculates usage (15 min)
    ↓
Report to Stripe:
  subscription_item: voice_item_id
  quantity: 15
  timestamp: now
    ↓
Stripe updates billing period usage
    ↓
User config.toml updated:
  voice_minutes: 15 (running total)
```

**Real-time usage reporting:**
- After each voice call: Report minutes to Stripe
- After each SMS: Report message count to Stripe
- Daily summary: Email user with current usage

**Billing cycle:**
- Usage resets on monthly anniversary
- Included: 100 minutes + 100 SMS
- Overage: Billed on next invoice

---

### 4. Billing & Invoicing

```
Monthly billing date arrives
    ↓
Stripe generates invoice:
  - Base subscription: $9.99
  - Voice overage: (150 - 100) × $0.013 = $0.65
  - SMS overage: (120 - 100) × $0.0075 = $0.15
  Total: $10.79
    ↓
Stripe charges payment method
    ↓
[WEBHOOK: invoice.payment_succeeded]
    ↓
Reset usage counters:
  config.voice_minutes = 0
  config.sms_messages = 0
    ↓
Send email receipt
    ↓
Next billing period starts
```

**Invoice line items:**
```
xSwarm Premium (Nov 1 - Dec 1)          $9.99
Voice Minutes (50 overage)               $0.65
SMS Messages (20 overage)                $0.15
────────────────────────────────────────────
Subtotal                                $10.79
Tax (if applicable)                      $0.00
────────────────────────────────────────────
Total                                   $10.79
```

---

### 5. Downgrade to Free

```
User runs: xswarm subscription cancel
    ↓
Confirm cancellation
    ↓
Cancel Stripe subscription:
  cancel_at_period_end = true
    ↓
[WEBHOOK: customer.subscription.updated]
    ↓
Send email confirmation:
  "Access until [date], then downgrade to free"
    ↓
[On billing period end]
    ↓
[WEBHOOK: customer.subscription.deleted]
    ↓
Release toll-free number back to Twilio pool
    ↓
Update user config:
  tier = "free"
  phone_enabled = false
  xswarm_phone = null
    ↓
Send final invoice (with any overages)
    ↓
User reverts to free tier
```

**Grace period:** User keeps premium access until end of paid period

**Data retention:**
- Phone number released (available for new users)
- Call/SMS history retained (for records)
- Usage statistics archived
- Email address unchanged

---

### 6. Payment Failure

```
Stripe attempts to charge card
    ↓
Payment fails (insufficient funds)
    ↓
[WEBHOOK: invoice.payment_failed]
    ↓
Send urgent email:
  "Payment failed, update payment method"
    ↓
Grace period: 3 days
    ↓
[If payment method updated]
    ↓
Stripe retries → success → continue premium
    ↓
[If payment still fails after 3 days]
    ↓
[WEBHOOK: customer.subscription.deleted]
    ↓
Auto-downgrade to free tier
    ↓
Release phone number
    ↓
Send downgrade notification email
```

**Recovery flow:**
- User gets email with "Update Payment Method" link
- Opens Stripe Customer Portal
- Updates credit card
- Stripe automatically retries charge
- Premium access restored immediately

---

## Configuration Files

### Free Tier Config

```toml
# ~/.config/xswarm/config.toml

[subscription]
active = false
tier = "free"
expires_at = null

[communication]
user_email = "you@example.com"
xswarm_email = "alice@xswarm.ai"

[communication.channels]
email_enabled = true
phone_enabled = false
sms_enabled = false
```

---

### Premium Tier Config

```toml
# ~/.config/xswarm/config.toml

[subscription]
active = true
tier = "premium"
expires_at = "2026-01-15T00:00:00Z"

[subscription.stripe]
customer_id = "cus_xxxxxxxxxxxxx"
subscription_id = "sub_xxxxxxxxxxxxx"

[subscription.stripe.subscription_items]
voice_item_id = "si_xxxxxxxxxxxxx"
sms_item_id = "si_xxxxxxxxxxxxx"

[subscription.stripe.usage]
voice_minutes = 25        # Current billing period
sms_messages = 10
phone_numbers = 1
period_start = "2025-11-01T00:00:00Z"
period_end = "2025-12-01T00:00:00Z"

[communication]
user_email = "you@example.com"
user_phone = "+15551234567"
xswarm_email = "alice@xswarm.ai"
xswarm_phone = "+18005551001"  # Toll-free

[communication.channels]
email_enabled = true
phone_enabled = true
sms_enabled = true
accept_inbound_calls = true
accept_inbound_sms = true
accept_inbound_email = true
```

---

## Resource Provisioning

### Toll-Free Phone Numbers

**Twilio Pool Management:**

```rust
// Provision phone number on upgrade
async fn provision_phone_number(customer_id: &str) -> Result<String> {
    let twilio = TwilioClient::new();

    // Search for available toll-free number
    let available = twilio.available_phone_numbers
        .toll_free("US")
        .list()
        .await?;

    if available.is_empty() {
        return Err("No toll-free numbers available");
    }

    // Purchase first available number
    let number = twilio.incoming_phone_numbers
        .create(available[0].phone_number)
        .await?;

    // Configure webhook
    twilio.incoming_phone_numbers
        .update(number.sid)
        .voice_url(format!("https://xswarm.ai/voice/{}", customer_id))
        .sms_url(format!("https://xswarm.ai/sms/{}", customer_id))
        .await?;

    // Save to database
    database.update_user_phone(customer_id, &number.phone_number).await?;

    Ok(number.phone_number)
}

// Release phone number on downgrade
async fn release_phone_number(phone_number: &str) -> Result<()> {
    let twilio = TwilioClient::new();

    // Find phone number SID
    let numbers = twilio.incoming_phone_numbers.list().await?;
    let number = numbers.iter()
        .find(|n| n.phone_number == phone_number)
        .ok_or("Phone number not found")?;

    // Release number
    twilio.incoming_phone_numbers
        .delete(&number.sid)
        .await?;

    Ok(())
}
```

---

## CLI Commands

### Subscription Management

```bash
# View current subscription
xswarm subscription status

# Output:
# Tier: Premium
# Status: Active
# Next billing: December 1, 2025
# Usage this period:
#   Voice: 45/100 minutes (45%)
#   SMS: 22/100 messages (22%)
# Estimated bill: $9.99 (no overage)

# Upgrade to premium
xswarm subscribe premium
# Opens Stripe Checkout → user enters payment → provisioning happens

# View usage
xswarm subscription usage

# Output:
# Billing Period: Nov 1 - Dec 1, 2025
# Voice Minutes: 45 / 100 (45 remaining)
# SMS Messages: 22 / 100 (78 remaining)
# Estimated overage: $0.00

# Manage billing (opens Stripe portal)
xswarm subscription manage
# Opens Stripe Customer Portal in browser

# Cancel subscription
xswarm subscription cancel

# Confirm:
#   Your premium access will continue until Dec 1, 2025
#   After that, you'll revert to free tier (email only)
#   Proceed? (yes/no): yes
```

---

## Webhook Handlers

### Subscription Created

```rust
async fn handle_subscription_created(subscription: Subscription) -> Result<()> {
    let customer_id = &subscription.customer;

    // 1. Update user tier
    database.update_user_tier(customer_id, "premium").await?;

    // 2. Extract subscription item IDs
    let voice_item = subscription.items.data.iter()
        .find(|item| item.price.id == env::var("STRIPE_PRICE_VOICE")?)
        .ok_or("Voice item not found")?;

    let sms_item = subscription.items.data.iter()
        .find(|item| item.price.id == env::var("STRIPE_PRICE_SMS")?)
        .ok_or("SMS item not found")?;

    // 3. Save subscription info
    database.save_subscription(customer_id, SubscriptionInfo {
        subscription_id: subscription.id.clone(),
        voice_item_id: voice_item.id.clone(),
        sms_item_id: sms_item.id.clone(),
        period_start: subscription.current_period_start,
        period_end: subscription.current_period_end,
    }).await?;

    // 4. Provision phone number
    let phone_number = provision_phone_number(customer_id).await?;

    // 5. Update config file
    update_user_config(customer_id, |config| {
        config.subscription.active = true;
        config.subscription.tier = "premium".to_string();
        config.communication.xswarm_phone = Some(phone_number.clone());
        config.communication.channels.phone_enabled = true;
        config.communication.channels.sms_enabled = true;
    }).await?;

    // 6. Send welcome email
    send_welcome_email(customer_id, &phone_number).await?;

    Ok(())
}
```

---

### Subscription Deleted (Cancellation)

```rust
async fn handle_subscription_deleted(subscription: Subscription) -> Result<()> {
    let customer_id = &subscription.customer;

    // 1. Get user's phone number
    let user = database.get_user(customer_id).await?;
    if let Some(phone_number) = user.xswarm_phone {
        // 2. Release phone number
        release_phone_number(&phone_number).await?;
    }

    // 3. Update user tier
    database.update_user_tier(customer_id, "free").await?;

    // 4. Update config file
    update_user_config(customer_id, |config| {
        config.subscription.active = false;
        config.subscription.tier = "free".to_string();
        config.subscription.stripe = None;
        config.communication.xswarm_phone = None;
        config.communication.channels.phone_enabled = false;
        config.communication.channels.sms_enabled = false;
    }).await?;

    // 5. Send downgrade notification
    send_downgrade_email(customer_id).await?;

    Ok(())
}
```

---

### Invoice Payment Failed

```rust
async fn handle_payment_failed(invoice: Invoice) -> Result<()> {
    let customer_id = &invoice.customer;

    // 1. Send urgent notification via email
    send_payment_failed_email(customer_id, &invoice).await?;

    // 2. Send SMS if phone enabled
    if let Some(user_phone) = database.get_user_phone(customer_id).await? {
        send_sms(
            &user_phone,
            "⚠️ xSwarm payment failed. Update payment method to keep premium access."
        ).await?;
    }

    // 3. Schedule auto-downgrade in 3 days
    schedule_task(Duration::days(3), async move {
        // Check if payment was resolved
        let subscription = stripe.subscriptions.retrieve(&invoice.subscription?).await?;

        if subscription.status == "past_due" {
            // Still not paid, cancel subscription
            stripe.subscriptions.delete(&subscription.id).await?;
        }
    });

    Ok(())
}
```

---

## Testing

### Test Subscription Flow

```bash
# 1. Test upgrade (uses test mode Stripe)
xswarm subscribe premium --test

# 2. Test card: 4242 4242 4242 4242
#    Expiry: 12/30
#    CVC: 123

# 3. Verify provisioning
xswarm subscription status
# Should show: Premium, phone number, 0/100 usage

# 4. Simulate voice call (report usage)
xswarm test call --duration 15

# 5. Check usage
xswarm subscription usage
# Should show: 15/100 minutes

# 6. Test cancellation
xswarm subscription cancel --test

# 7. Verify downgrade
xswarm subscription status
# Should show: Free tier
```

---

## Monitoring & Alerts

### Admin Dashboard Metrics

- Active subscriptions (free vs premium)
- Monthly recurring revenue (MRR)
- Average usage (voice minutes, SMS)
- Churn rate
- Failed payments requiring attention

### User Notifications

**Usage Alerts:**
- 50% usage: "You've used 50 of 100 included minutes"
- 80% usage: "You've used 80 of 100 included minutes, overage rates apply soon"
- 100% usage: "You've exceeded included usage, overage charges will apply"

**Billing Alerts:**
- Payment successful
- Payment failed (with action required)
- Subscription cancelled
- Upcoming renewal (3 days before)

---

## Security

### PCI Compliance

- ✅ **Never handle credit cards** - Stripe Checkout handles all payment details
- ✅ **No card data storage** - Only store Stripe customer/subscription IDs
- ✅ **HTTPS only** - All webhook endpoints secured with TLS
- ✅ **Webhook signature verification** - Validate all incoming webhooks

### API Key Security

- Store Stripe keys in environment variables
- Use restricted API keys (minimum required permissions)
- Rotate keys periodically
- Monitor API usage for anomalies

---

## Related Documentation

- [STRIPE_SETUP.md](./STRIPE_SETUP.md) - Stripe configuration guide
- [TWILIO_SETUP.md](./TWILIO_SETUP.md) - Twilio phone setup
- [SENDGRID_SETUP.md](./SENDGRID_SETUP.md) - SendGrid email setup
- [MULTI_CHANNEL.md](./MULTI_CHANNEL.md) - Multi-channel communication
- [DIRECT_LINE.md](./DIRECT_LINE.md) - Phone calling architecture

---

**Next:** Implement subscription module in Rust.
