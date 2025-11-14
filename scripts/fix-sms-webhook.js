#!/usr/bin/env node
/**
 * Fix Twilio SMS Webhook Configuration
 * Update the webhook URL to use the correct /sms/inbound endpoint
 */

import twilio from 'twilio';
import dotenv from 'dotenv';

// Load environment variables from .env
dotenv.config();

const ACCOUNT_SID = '***REMOVED***';
const AUTH_TOKEN = '***REMOVED***';
const PHONE_NUMBER = process.env.ADMIN_ASSISTANT_PHONE_NUMBER || '+18447472899';
const WEBHOOK_URL = 'https://tion-fifteen-substantial-jimmy.trycloudflare.com/sms/inbound';

console.log('🔧 Fixing Twilio SMS Webhook Configuration');
console.log('=========================================\n');

try {
  const client = twilio(ACCOUNT_SID, AUTH_TOKEN);

  console.log(`📱 Phone Number: ${PHONE_NUMBER}`);
  console.log(`🔗 New Webhook URL: ${WEBHOOK_URL}`);
  console.log('');

  // Find the phone number resource
  const phoneNumbers = await client.incomingPhoneNumbers.list({
    phoneNumber: PHONE_NUMBER
  });

  if (phoneNumbers.length === 0) {
    console.log('❌ Phone number not found in your Twilio account');
    process.exit(1);
  }

  const phoneNumberSid = phoneNumbers[0].sid;
  console.log(`📞 Found phone number SID: ${phoneNumberSid}`);

  // Update the SMS webhook URL
  const updatedNumber = await client.incomingPhoneNumbers(phoneNumberSid).update({
    smsUrl: WEBHOOK_URL,
    smsMethod: 'POST'
  });

  console.log('✅ SMS webhook updated successfully!');
  console.log(`🔗 SMS URL: ${updatedNumber.smsUrl}`);
  console.log(`📋 Method: ${updatedNumber.smsMethod}`);
  console.log('');
  console.log('🎯 Ready to receive SMS messages at /sms/inbound');

} catch (error) {
  console.error('❌ Error updating webhook:', error.message);
  if (error.code) {
    console.error(`Error code: ${error.code}`);
  }
  process.exit(1);
}