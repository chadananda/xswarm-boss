# Twilio Setup Guide - Quick Start

Complete setup guide for testing Direct Line voice feature with Twilio.

---

## Step 1: Sign Up for Twilio (FREE $15 Credit)

1. **Go to:** https://www.twilio.com/try-twilio

2. **Create account:**
   - Enter email and password
   - Click "Start your free trial"
   - Verify email (check inbox)

3. **Verify your phone number:**
   - They'll send you a verification code
   - This becomes your first **verified caller ID**
   - ⚠️ On trial accounts, you can ONLY call/receive from verified numbers

4. **Get $15 free credit:**
   - No credit card required
   - Good for ~1000 minutes of testing
   - Valid for 90 days

---

## Step 2: Get a Twilio Phone Number

1. **Dashboard** → Click **"Get a Trial Phone Number"**

2. **Twilio will suggest a number:**
   - Voice-enabled (required)
   - SMS optional (not needed)

3. **Click "Choose this number"**

4. **Copy your number** (format: `+15551234567`)
   - You'll need this for your `.env` file

**Trial Account Limitation:**
- ✅ Can call/receive from **verified numbers only**
- ❌ Cannot call random numbers
- Perfect for testing!

---

## Step 3: Get Your API Credentials

1. **Twilio Console** → **Account** section (top right)

2. **Copy these values:**

   **Account SID:** (starts with `AC...`)
   ```
   ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

   **Auth Token:** (click 👁️ eye icon to reveal)
   ```
   xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

⚠️ **Keep these secret!** They're like passwords to your Twilio account.

---

## Step 4: Configure xSwarm

Edit your `.env` file:

```bash
# Open .env in your editor
code .env
# or
vim .env
```

**Update these values:**

```bash
# Twilio Account Credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Your Twilio Phone Number (from Step 2)
TWILIO_PHONE_NUMBER=+15551234567

# Your Personal Phone Number (the one you verified in Step 1)
USER_PHONE_NUMBER=+15559876543
```

**Format rules:**
- Phone numbers must be in **E.164 format**: `+[country code][number]`
- US example: `+15551234567` (not `555-123-4567`)
- No spaces, dashes, or parentheses

---

## Step 5: Test the Connection

Run the test script:

```bash
pnpm test:twilio
```

**What this tests:**
1. ✓ Verifies Twilio credentials
2. ✓ Checks account balance
3. ✓ Confirms phone number ownership
4. ✓ Checks verified caller IDs (trial limitation)
5. ✓ Makes a test call (optional)

**Expected output:**

```
🔧 Twilio Direct Line Test

✓ Environment variables configured
  Account SID: AC12345678...
  Twilio Number: +15551234567
  Your Number: +15559876543

📡 Test 1: Verifying Twilio credentials...
✓ Account verified: My Twilio Account
  Status: active
  Type: Trial

💰 Test 2: Checking account balance...
✓ Balance: USD 15.00
  (Trial account - $15 free credit)

📞 Test 3: Verifying Twilio phone number...
✓ Phone number verified: +15551234567
  Friendly Name: (555) 123-4567
  Voice Enabled: true
  SMS Enabled: true

🔒 Test 4: Checking verified caller IDs (trial limitation)...
✓ Your number is verified: +15559876543
  Friendly Name: My Phone

📲 Test 5: Ready to make test call!
   From: +15551234567
   To: +15559876543

Do you want to make a test call? (yes/no)
> yes

📞 Calling your phone...
✓ Call initiated! SID: CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  Status: queued

📱 Your phone should be ringing now!

  Answer the call to hear HAL 9000's test message.

Monitoring call status...
  [1s] Status: ringing
  [2s] Status: in-progress
  [8s] Status: completed

✓ Call completed
  Duration: 6 seconds
```

**If you answer the call, you'll hear:**
> "Hello! This is a test call from your xSwarm Direct Line system. I'm sorry Dave, I mean... this is HAL 9000. If you can hear this message, your Twilio integration is working perfectly. All systems operational. Goodbye."

---

## Troubleshooting

### Error: "Authentication failed"

**Cause:** Wrong Account SID or Auth Token

**Fix:**
1. Double-check your credentials in Twilio Console
2. Make sure you copied the entire string (no spaces)
3. Update `.env` file

### Error: "Phone number not found"

**Cause:** `TWILIO_PHONE_NUMBER` doesn't match your Twilio account

**Fix:**
1. Go to Twilio Console → Phone Numbers → Manage → Active Numbers
2. Copy the exact number (with +1 country code)
3. Update `.env` file

### Error: "This number is not verified" (Error Code 21608)

**Cause:** Trial accounts can only call verified numbers

**Fix:**
1. Go to: Twilio Console → Phone Numbers → Verified Caller IDs
2. Click "Add a new Caller ID"
3. Enter your phone number
4. Verify with the code they send

### Call doesn't ring / goes straight to voicemail

**Possible causes:**
- Phone is on Do Not Disturb
- Number is blocked
- Network issues

**Fix:**
- Make sure your phone can receive calls
- Try from a different number
- Check Twilio Console → Monitor → Logs for details

---

## Trial Account Limitations

| Feature | Trial | Paid |
|---------|-------|------|
| **Inbound calls** | ✅ From any number | ✅ From any number |
| **Outbound calls** | ❌ Only to verified numbers | ✅ To any number |
| **Credit** | $15 free | Pay-as-you-go |
| **Call quality** | Full quality | Full quality |
| **Twilio branding** | "You have a trial account" message | No branding |

**To remove trial limitations:**
- Upgrade to paid account (no monthly fee, just pay-as-you-go)
- Costs: ~$0.01/min for calls, $1.15/month for phone number

---

## Next Steps

Once your test call works:

1. **Configure Direct Line in xSwarm:**
   ```bash
   cargo run -- config set subscription.active true
   cargo run -- config set subscription.tier premium
   ```

2. **Set up webhook endpoint** (for receiving calls)
   - Use ngrok for local testing
   - See `planning/DIRECT_LINE.md` for architecture

3. **Implement voice handler** (coming soon)
   - Rust webhook server
   - STT → Claude → TTS pipeline

---

## Cost Calculator

**Example usage:**
- Phone number: $1.15/month
- 50 minutes inbound: 50 × $0.0085 = $0.43
- 50 minutes outbound: 50 × $0.013 = $0.65
- **Total: $2.23/month**

**Free trial:**
- $15 credit = ~1,100 minutes
- Test extensively before paying anything!

---

## Resources

- **Twilio Console:** https://console.twilio.com/
- **Twilio Docs:** https://www.twilio.com/docs/voice
- **Pricing:** https://www.twilio.com/en-us/voice/pricing/us
- **Test Script:** `scripts/test-twilio.js`
- **Architecture:** `planning/DIRECT_LINE.md`

---

## Quick Reference

```bash
# Test Twilio connection
pnpm test:twilio

# Check account balance
# (add to scripts/twilio-balance.js if needed)

# List phone numbers
# (view in Twilio Console → Phone Numbers)

# View call logs
# (Twilio Console → Monitor → Logs → Calls)
```

---

**You're ready to build Direct Line!** 🚀

Once the test call works, you've successfully:
- ✅ Created Twilio account
- ✅ Got a phone number
- ✅ Verified API credentials
- ✅ Made your first voice call
- ✅ Ready to integrate with xSwarm

Next: Build the webhook handler to receive calls and have conversations with HAL/Sauron/JARVIS!
