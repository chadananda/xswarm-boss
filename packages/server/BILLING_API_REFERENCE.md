# Billing & Phone API Quick Reference

Quick reference for using the billing and phone provisioning APIs.

## Authentication

All endpoints require JWT authentication:
```
Authorization: Bearer <jwt_token>
```

## Billing Endpoints

### GET /api/billing/usage
Get current usage and overage information.

**Response:**
```json
{
  "period": {
    "start": "2025-10-01T00:00:00Z",
    "end": "2025-10-31T23:59:59Z"
  },
  "usage": {
    "voice_minutes": 150,
    "sms_messages": 120,
    "email_count": 45
  },
  "limits": {
    "voice_minutes": 100,
    "sms_messages": 100,
    "has_voice": true,
    "has_sms": true
  },
  "overages": {
    "voice_minutes": 50,
    "sms_messages": 20
  },
  "costs": {
    "voice_overage": "0.65",
    "sms_overage": "0.15",
    "phone_number": "5.00",
    "total_overage": "5.80"
  },
  "usage_percentages": {
    "voice": 150,
    "sms": 120
  }
}
```

---

### GET /api/billing/history
Get billing history and events.

**Response:**
```json
{
  "history": [
    {
      "id": "bill_123",
      "amount": "45.80",
      "status": "paid",
      "description": "Monthly subscription",
      "invoice_url": "https://invoice.stripe.com/...",
      "period_start": "2025-10-01T00:00:00Z",
      "period_end": "2025-10-31T23:59:59Z",
      "created_at": "2025-10-01T00:00:00Z"
    }
  ],
  "events": [
    {
      "event_type": "payment_succeeded",
      "amount": "45.80",
      "description": "Payment received: $45.80",
      "processed_at": "2025-10-01T00:00:00Z"
    }
  ]
}
```

---

### POST /api/billing/estimate
Estimate costs for tier change.

**Request:**
```json
{
  "target_tier": "ai_project_manager"
}
```

**Response:**
```json
{
  "current_tier": "ai_secretary",
  "new_tier": "ai_project_manager",
  "proration": {
    "unused_credit": 20.00,
    "prorated_charge": 140.00,
    "net_charge": "120.00"
  },
  "new_limits": {
    "voice_minutes": 500,
    "sms_messages": 500
  },
  "billing_date": "2025-10-31T23:59:59Z",
  "summary": {
    "immediate_charge": "120.00",
    "monthly_price": "280.00"
  }
}
```

---

### GET /api/billing/upcoming
Get upcoming invoice preview.

**Response:**
```json
{
  "amount_due": 4580,
  "amount_dollars": "45.80",
  "period_start": "2025-11-01T00:00:00Z",
  "period_end": "2025-11-30T23:59:59Z",
  "next_payment_attempt": "2025-11-01T00:00:00Z",
  "lines": [
    {
      "description": "AI Secretary subscription",
      "amount": 4000,
      "amount_dollars": "40.00"
    },
    {
      "description": "Voice overage: 50 minutes @ $0.0130/min",
      "amount": 65,
      "amount_dollars": "0.65"
    }
  ]
}
```

## Phone Endpoints

### POST /api/phone/provision
Provision a new phone number.

**Request (optional):**
```json
{
  "area_code": "415",
  "phone_number": "+14155551234"
}
```

**Response:**
```json
{
  "message": "Phone number provisioned successfully",
  "phone_number": "+14155551234",
  "capabilities": {
    "voice": true,
    "sms": true,
    "mms": true
  }
}
```

**Errors:**
- 403: Phone provisioning requires a paid subscription
- 400: Phone number already provisioned
- 404: No phone numbers available in that area code

---

### DELETE /api/phone/release
Release provisioned phone number.

**Response:**
```json
{
  "message": "Phone number released successfully"
}
```

**Errors:**
- 400: No phone number to release

---

### GET /api/phone/details
Get details of provisioned phone number.

**Response:**
```json
{
  "phone_number": "+14155551234",
  "sid": "PN123...",
  "friendly_name": "xSwarm - User usr_123",
  "voice_url": "https://your-domain.com/voice/inbound",
  "sms_url": "https://your-domain.com/sms/inbound",
  "status_callback": "https://your-domain.com/phone/status/usr_123",
  "capabilities": {
    "voice": true,
    "sms": true,
    "mms": true
  },
  "date_created": "2025-10-01T00:00:00Z",
  "date_updated": "2025-10-01T00:00:00Z"
}
```

**Errors:**
- 404: No phone number provisioned

---

### GET /api/phone/search
Search available phone numbers.

**Query Parameters:**
- `area_code` (optional): Area code to search (e.g., "415")
- `country` (optional): Country code (default: "US")

**Response:**
```json
{
  "count": 10,
  "numbers": [
    {
      "phone_number": "+14155551234",
      "friendly_name": "(415) 555-1234",
      "locality": "San Francisco",
      "region": "CA",
      "postal_code": "94105",
      "capabilities": {
        "voice": true,
        "sms": true,
        "mms": true
      }
    }
  ]
}
```

**Errors:**
- 403: Phone search requires a paid subscription

## Dashboard Endpoints

### POST /api/dashboard/upgrade
Initiate subscription upgrade.

**Request:**
```json
{
  "target_tier": "ai_secretary"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_test_..."
}
```

---

### POST /api/dashboard/downgrade
Downgrade subscription.

**Request:**
```json
{
  "target_tier": "ai_buddy"
}
```

**Response (downgrade to free):**
```json
{
  "message": "Subscription will be cancelled at the end of the current billing period",
  "downgrade_date": "2025-10-31T23:59:59Z"
}
```

**Response (downgrade to lower paid tier):**
```json
{
  "message": "Subscription updated successfully",
  "new_tier": "ai_secretary"
}
```

---

### POST /api/dashboard/cancel
Cancel subscription at period end.

**Response:**
```json
{
  "message": "Subscription will be cancelled at the end of the current billing period",
  "status": "pending_cancellation"
}
```

## Subscription Tiers

### ai_buddy (Free)
- Price: $0/month
- Voice: 0 minutes
- SMS: 0 messages
- Email: 100/day
- No phone provisioning

### ai_secretary
- Price: $40/month
- Voice: 100 minutes (overage: $0.013/min)
- SMS: 100 messages (overage: $0.0075/msg)
- Email: Unlimited
- Phone: $5/month (provisioned automatically)

### ai_project_manager
- Price: $280/month
- Voice: 500 minutes (overage: $0.013/min)
- SMS: 500 messages (overage: $0.0075/msg)
- Email: Unlimited
- Phone: $5/month (provisioned automatically)
- Teams: Enabled
- Buzz platform: Enabled

### ai_cto (Enterprise)
- Price: Custom
- Voice: Unlimited
- SMS: Unlimited
- Email: Unlimited
- Phone: Included
- Enterprise features

## Example Usage

### Node.js with fetch
```javascript
const token = 'your_jwt_token';

// Get current usage
const usage = await fetch('https://your-domain.com/api/billing/usage', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
}).then(r => r.json());

console.log(`Voice: ${usage.usage.voice_minutes}/${usage.limits.voice_minutes} minutes`);
console.log(`Overages: $${usage.costs.total_overage}`);
```

### curl
```bash
# Get usage
curl -H "Authorization: Bearer $TOKEN" \
  https://your-domain.com/api/billing/usage

# Estimate upgrade cost
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_tier": "ai_project_manager"}' \
  https://your-domain.com/api/billing/estimate

# Provision phone
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"area_code": "415"}' \
  https://your-domain.com/api/phone/provision
```

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

Common status codes:
- `400` - Bad request (invalid input)
- `401` - Unauthorized (invalid/missing JWT)
- `403` - Forbidden (subscription tier insufficient)
- `404` - Not found (resource doesn't exist)
- `500` - Internal server error

## Rate Limits

API endpoints are subject to rate limiting:
- Billing endpoints: 100 requests/hour per user
- Phone endpoints: 10 requests/hour per user
- Dashboard endpoints: 20 requests/hour per user

## Webhooks

The system processes these Stripe webhooks:
- `customer.subscription.created` - Provisions phone, activates features
- `customer.subscription.updated` - Handles tier changes
- `customer.subscription.deleted` - Releases phone, downgrades to free
- `customer.subscription.trial_will_end` - Sends notification
- `invoice.payment_succeeded` - Resets usage counters
- `invoice.payment_failed` - Sends notifications
- `invoice.upcoming` - Adds overage charges

## Testing

Use Stripe test mode for development:
```bash
# Test cards
4242 4242 4242 4242  # Success
4000 0000 0000 0002  # Declined
4000 0000 0000 9995  # Insufficient funds

# Trigger test webhooks
stripe trigger customer.subscription.created
stripe trigger invoice.payment_succeeded
```

## Support

For API issues:
1. Check authentication token is valid
2. Verify subscription tier for restricted endpoints
3. Review error response for details
4. Check server logs for webhook processing
5. Verify Stripe/Twilio credentials
