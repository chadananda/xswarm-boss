# Stripe API Reference

Comprehensive reference for Stripe API resources, operations, and patterns used in xSwarm.

> **Official Documentation:** https://docs.stripe.com/api

---

## Table of Contents

- [API Overview](#api-overview)
- [Authentication](#authentication)
- [Core Resources](#core-resources)
  - [Customers](#customers)
  - [Subscriptions](#subscriptions)
  - [PaymentIntents](#paymentintents)
  - [Invoices](#invoices)
  - [Products & Prices](#products--prices)
  - [Usage Records](#usage-records)
- [Webhooks](#webhooks)
- [Event Types](#event-types)
- [Best Practices](#best-practices)

---

## API Overview

### Architecture

The Stripe API is built on REST principles:

- **Base URL:** `https://api.stripe.com`
- **Request Format:** Form-encoded bodies or JSON
- **Response Format:** JSON
- **HTTP Methods:** GET, POST, DELETE
- **Authentication:** API key-based (determines test vs live mode)

### Key Characteristics

- **Idempotent:** Most POST requests support idempotency keys
- **Single Object per Request:** No bulk updates (process one object at a time)
- **Versioned:** API version is set per account
- **Account-Specific:** API behavior varies by account configuration

### Rate Limits

- Standard rate limit applies to all API calls
- Use exponential backoff for retries on 429 errors
- Webhooks are not rate-limited

---

## Authentication

### API Keys

Stripe uses two types of keys for each mode:

**Test Mode** (Development):
```bash
STRIPE_SECRET_KEY_TEST=sk_test_...
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_...
```

**Live Mode** (Production):
```bash
STRIPE_SECRET_KEY_LIVE=sk_live_...
STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_...
```

### Key Types

| Key Type | Prefix | Usage | Secret? |
|----------|--------|-------|---------|
| Secret Key | `sk_test_` / `sk_live_` | Server-side API calls | ✅ YES |
| Publishable Key | `pk_test_` / `pk_live_` | Client-side tokenization | ❌ NO |

### Authentication Headers

```bash
Authorization: Bearer sk_test_xxxxxxxxxxxxx
```

---

## Core Resources

### Customers

The Customer object represents a customer of your business. Used to track recurring charges, save payment info, and organize payments.

#### Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/customers` | POST |
| Retrieve | `/v1/customers/:id` | GET |
| Update | `/v1/customers/:id` | POST |
| Delete | `/v1/customers/:id` | DELETE |
| List | `/v1/customers` | GET |
| Search | `/v1/customers/search` | GET |

#### Key Attributes

```json
{
  "id": "cus_xxxxxxxxxxxxx",
  "email": "customer@example.com",
  "name": "John Doe",
  "phone": "+15551234567",
  "address": { ... },
  "shipping": { ... },
  "metadata": {
    "xswarm_user_id": "user123",
    "persona": "hal-9000"
  },
  "default_source": "card_xxxxxxxxxxxxx",
  "invoice_settings": {
    "default_payment_method": "pm_xxxxxxxxxxxxx"
  }
}
```

#### Example: Create Customer

```bash
curl https://api.stripe.com/v1/customers \
  -u sk_test_xxxxxxxxxxxxx: \
  -d "email=customer@example.com" \
  -d "name=John Doe" \
  -d "metadata[xswarm_user_id]=user123"
```

---

### Subscriptions

Create recurring charges to customers on a scheduled basis.

#### Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/subscriptions` | POST |
| Retrieve | `/v1/subscriptions/:id` | GET |
| Update | `/v1/subscriptions/:id` | POST |
| Cancel | `/v1/subscriptions/:id` | DELETE |
| Resume | `/v1/subscriptions/:id/resume` | POST |
| List | `/v1/subscriptions` | GET |
| Search | `/v1/subscriptions/search` | GET |

#### Key Attributes

```json
{
  "id": "sub_xxxxxxxxxxxxx",
  "customer": "cus_xxxxxxxxxxxxx",
  "status": "active",
  "items": {
    "data": [
      {
        "id": "si_xxxxxxxxxxxxx",
        "price": {
          "id": "price_xxxxxxxxxxxxx",
          "product": "prod_xxxxxxxxxxxxx",
          "unit_amount": 999,
          "recurring": {
            "interval": "month"
          }
        },
        "quantity": 1
      }
    ]
  },
  "current_period_start": 1234567890,
  "current_period_end": 1234567890,
  "cancel_at_period_end": false
}
```

#### Subscription Status Lifecycle

```
incomplete → active → past_due → canceled
                  ↓
                paused
```

| Status | Description |
|--------|-------------|
| `incomplete` | Initial creation, awaiting payment |
| `active` | Subscription is active and billing |
| `past_due` | Payment failed, in retry period |
| `canceled` | Subscription has been canceled |
| `paused` | Subscription is temporarily paused |

#### Example: Create Subscription

```bash
curl https://api.stripe.com/v1/subscriptions \
  -u sk_test_xxxxxxxxxxxxx: \
  -d "customer=cus_xxxxxxxxxxxxx" \
  -d "items[0][price]=price_xxxxxxxxxxxxx" \
  -d "items[1][price]=price_xxxxxxxxxxxxx"
```

---

### PaymentIntents

A PaymentIntent represents an intent to collect payment from a customer.

#### Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/payment_intents` | POST |
| Retrieve | `/v1/payment_intents/:id` | GET |
| Update | `/v1/payment_intents/:id` | POST |
| Confirm | `/v1/payment_intents/:id/confirm` | POST |
| Capture | `/v1/payment_intents/:id/capture` | POST |
| Cancel | `/v1/payment_intents/:id/cancel` | POST |
| List | `/v1/payment_intents` | GET |

#### Key Attributes

```json
{
  "id": "pi_xxxxxxxxxxxxx",
  "amount": 1099,
  "currency": "usd",
  "status": "succeeded",
  "customer": "cus_xxxxxxxxxxxxx",
  "payment_method": "pm_xxxxxxxxxxxxx",
  "metadata": {
    "order_id": "12345"
  }
}
```

#### PaymentIntent Status Flow

```
requires_payment_method → requires_confirmation → processing → succeeded
                                                             ↓
                                                           canceled
```

---

### Invoices

Invoices are statements of amounts owed by a customer.

#### Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/invoices` | POST |
| Retrieve | `/v1/invoices/:id` | GET |
| Update | `/v1/invoices/:id` | POST |
| Finalize | `/v1/invoices/:id/finalize` | POST |
| Pay | `/v1/invoices/:id/pay` | POST |
| Void | `/v1/invoices/:id/void` | POST |
| List | `/v1/invoices` | GET |

#### Key Attributes

```json
{
  "id": "in_xxxxxxxxxxxxx",
  "customer": "cus_xxxxxxxxxxxxx",
  "subscription": "sub_xxxxxxxxxxxxx",
  "amount_due": 999,
  "amount_paid": 999,
  "status": "paid",
  "currency": "usd",
  "lines": {
    "data": [...]
  }
}
```

---

### Products & Prices

Products represent items you sell. Prices represent how much and how often to charge for products.

#### Product Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/products` | POST |
| Retrieve | `/v1/products/:id` | GET |
| Update | `/v1/products/:id` | POST |
| Delete | `/v1/products/:id` | DELETE |
| List | `/v1/products` | GET |

#### Price Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/prices` | POST |
| Retrieve | `/v1/prices/:id` | GET |
| Update | `/v1/prices/:id` | POST |
| List | `/v1/prices` | GET |

#### Price Types

**Standard Pricing** (Fixed amount):
```json
{
  "id": "price_xxxxxxxxxxxxx",
  "product": "prod_xxxxxxxxxxxxx",
  "unit_amount": 999,
  "currency": "usd",
  "recurring": {
    "interval": "month"
  }
}
```

**Usage-Based Pricing** (Metered):
```json
{
  "id": "price_xxxxxxxxxxxxx",
  "product": "prod_xxxxxxxxxxxxx",
  "unit_amount": 13,
  "currency": "usd",
  "recurring": {
    "interval": "month",
    "usage_type": "metered"
  }
}
```

---

### Usage Records

Track usage for metered billing subscriptions.

#### Operations

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Create | `/v1/subscription_items/:id/usage_records` | POST |
| List | `/v1/subscription_items/:id/usage_record_summaries` | GET |

#### Key Attributes

```json
{
  "id": "mbur_xxxxxxxxxxxxx",
  "subscription_item": "si_xxxxxxxxxxxxx",
  "quantity": 50,
  "timestamp": 1234567890,
  "action": "increment"
}
```

#### Example: Report Usage

```bash
curl https://api.stripe.com/v1/subscription_items/si_xxxxxxxxxxxxx/usage_records \
  -u sk_test_xxxxxxxxxxxxx: \
  -d "quantity=50" \
  -d "timestamp=$(date +%s)" \
  -d "action=increment"
```

#### Usage Actions

| Action | Description |
|--------|-------------|
| `increment` | Add to current usage (most common) |
| `set` | Set usage to exact quantity |

---

## Webhooks

Webhooks send real-time notifications about events in your Stripe account.

### Setup

1. **Create Endpoint** in Stripe Dashboard:
   - Developers → Webhooks → Add endpoint
   - URL: `https://your-server.com/stripe/webhook`

2. **Get Signing Secret:**
   - After creation, reveal signing secret
   - Format: `***REMOVED***`

3. **Configure Events:**
   - Select specific events to receive
   - Or select "All events" for testing

### Webhook Request Format

```http
POST /stripe/webhook HTTP/1.1
Host: your-server.com
Content-Type: application/json
Stripe-Signature: t=1234567890,v1=xxxxxxxxxxxxx

{
  "id": "evt_xxxxxxxxxxxxx",
  "type": "customer.subscription.created",
  "data": {
    "object": { ... }
  },
  "created": 1234567890
}
```

### Verifying Webhook Signatures

**Always verify webhook signatures to prevent spoofing:**

```javascript
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

const event = stripe.webhooks.constructEvent(
  rawBody,                              // Raw request body
  req.headers['stripe-signature'],      // Signature header
  process.env.STRIPE_WEBHOOK_SECRET     // Signing secret
);
```

**If verification fails:**
- Return HTTP 400
- Log the failure
- Do not process the event

### Webhook Best Practices

1. **Return 200 Quickly:** Respond with 200 status before complex processing
2. **Process Asynchronously:** Queue events for background processing
3. **Idempotency:** Track event IDs to avoid duplicate processing
4. **HTTPS Only:** Use secure endpoints in production
5. **Retry Logic:** Stripe retries failed webhooks automatically

---

## Event Types

### Customer Events

| Event | Description |
|-------|-------------|
| `customer.created` | New customer created |
| `customer.updated` | Customer info changed |
| `customer.deleted` | Customer deleted |
| `customer.source.created` | Payment source added |
| `customer.source.updated` | Payment source updated |
| `customer.source.deleted` | Payment source removed |

### Subscription Events

| Event | Description |
|-------|-------------|
| `customer.subscription.created` | New subscription created |
| `customer.subscription.updated` | Subscription modified |
| `customer.subscription.deleted` | Subscription canceled |
| `customer.subscription.trial_will_end` | Trial ending in 3 days |
| `customer.subscription.paused` | Subscription paused |
| `customer.subscription.resumed` | Subscription resumed |

### Payment Events

| Event | Description |
|-------|-------------|
| `payment_intent.created` | Payment intent created |
| `payment_intent.succeeded` | Payment completed successfully |
| `payment_intent.payment_failed` | Payment attempt failed |
| `payment_intent.canceled` | Payment canceled |
| `payment_intent.requires_action` | Customer action required |
| `payment_intent.processing` | Payment being processed |

### Invoice Events

| Event | Description |
|-------|-------------|
| `invoice.created` | New invoice generated |
| `invoice.finalized` | Draft invoice finalized |
| `invoice.paid` | Invoice paid successfully |
| `invoice.payment_failed` | Invoice payment failed |
| `invoice.voided` | Invoice voided |
| `invoice.updated` | Invoice modified |
| `invoice.upcoming` | Upcoming invoice notification |

### Recommended Events for xSwarm

**Required for subscription management:**
```
✓ customer.subscription.created
✓ customer.subscription.updated
✓ customer.subscription.deleted
✓ invoice.payment_succeeded
✓ invoice.payment_failed
✓ customer.created
✓ customer.updated
```

---

## Best Practices

### API Usage

1. **Use Idempotency Keys:**
   ```bash
   curl -X POST https://api.stripe.com/v1/customers \
     -H "Idempotency-Key: unique_key_123"
   ```

2. **Handle Errors Gracefully:**
   - `400` - Bad request (invalid parameters)
   - `401` - Authentication failed
   - `402` - Request failed
   - `404` - Resource not found
   - `429` - Too many requests (rate limited)
   - `500` - Server error

3. **Use Metadata:**
   ```json
   {
     "metadata": {
       "xswarm_user_id": "user123",
       "persona": "hal-9000",
       "source": "web_signup"
     }
   }
   ```

### Security

1. **API Key Storage:**
   - Never commit API keys to version control
   - Use environment variables or secrets manager
   - Rotate keys periodically

2. **Webhook Security:**
   - Always verify signatures
   - Use HTTPS endpoints only
   - Implement rate limiting on webhook endpoint

3. **Client-Side:**
   - Only use publishable keys in frontend
   - Never expose secret keys
   - Tokenize payment info before sending to server

### Testing

1. **Use Test Mode:**
   - Test all flows before going live
   - Use test credit cards
   - Verify webhook delivery

2. **Test Cards:**
   ```
   Success: 4242 4242 4242 4242
   Decline: 4000 0000 0000 0002
   Insufficient funds: 4000 0000 0000 9995
   3D Secure: 4000 0025 0000 3155
   ```

3. **Stripe CLI:**
   ```bash
   # Forward webhooks to localhost
   stripe listen --forward-to localhost:3000/webhook

   # Trigger test events
   stripe trigger customer.subscription.created
   ```

### Performance

1. **Cache Product/Price IDs:**
   - Store in config, not database
   - Reduce API calls

2. **Batch Operations:**
   - Process webhooks asynchronously
   - Queue usage record updates

3. **Optimize Queries:**
   - Use `expand` parameter to include related objects
   - Use `limit` for list operations

---

## Common Patterns

### Pattern 1: Create Customer with Subscription

```bash
# 1. Create customer
POST /v1/customers
  email=customer@example.com
  payment_method=pm_xxxxxxxxxxxxx

# 2. Create subscription
POST /v1/subscriptions
  customer=cus_xxxxxxxxxxxxx
  items[0][price]=price_premium
  items[1][price]=price_voice_metered
  items[2][price]=price_sms_metered
```

### Pattern 2: Report Metered Usage

```bash
# After each billable event
POST /v1/subscription_items/si_xxxxxxxxxxxxx/usage_records
  quantity=1
  timestamp=$(date +%s)
  action=increment
```

### Pattern 3: Handle Failed Payment

```javascript
// Webhook handler
if (event.type === 'invoice.payment_failed') {
  const invoice = event.data.object;

  // 1. Notify customer
  await sendPaymentFailedEmail(invoice.customer);

  // 2. Schedule retry or downgrade
  await scheduleRetry(invoice.id, 3); // Retry in 3 days
}
```

### Pattern 4: Cancel Subscription at Period End

```bash
POST /v1/subscriptions/sub_xxxxxxxxxxxxx
  cancel_at_period_end=true
```

---

## Resources

- **API Documentation:** https://docs.stripe.com/api
- **Webhooks Guide:** https://docs.stripe.com/webhooks
- **Testing Guide:** https://docs.stripe.com/testing
- **Rust Library:** https://github.com/arlyon/async-stripe
- **Dashboard:** https://dashboard.stripe.com

---

**Last Updated:** 2025-10-24
