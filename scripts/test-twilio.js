#!/usr/bin/env node

/**
 * Twilio Connection Test Script
 *
 * Tests Twilio API credentials and makes a test call
 *
 * Usage:
 *   node scripts/test-twilio.js
 */

import 'dotenv/config';
import twilio from 'twilio';

const {
  TWILIO_ACCOUNT_ID,
  TWILIO_ACCOUNT_SID = TWILIO_ACCOUNT_ID,  // Fallback to TWILIO_ACCOUNT_ID
  TWILIO_AUTH_TOKEN,
  TWILIO_TEST_RECEIVE_NUMBER,
  TWILIO_TEST_SEND_NUMBER,
  TWILIO_PHONE_NUMBER = TWILIO_TEST_RECEIVE_NUMBER,  // Fallback
  USER_PHONE_NUMBER = TWILIO_TEST_SEND_NUMBER        // Fallback
} = process.env;

// Validate environment variables
function validateEnv() {
  const missing = [];

  if (!TWILIO_ACCOUNT_SID) {
    missing.push('TWILIO_ACCOUNT_ID or TWILIO_ACCOUNT_SID');
  }
  if (!TWILIO_AUTH_TOKEN) {
    missing.push('TWILIO_AUTH_TOKEN');
  }
  if (!TWILIO_PHONE_NUMBER) {
    missing.push('TWILIO_TEST_RECEIVE_NUMBER or TWILIO_PHONE_NUMBER');
  }
  if (!USER_PHONE_NUMBER) {
    missing.push('TWILIO_TEST_SEND_NUMBER or USER_PHONE_NUMBER');
  }

  if (missing.length > 0) {
    console.error('❌ Missing or unconfigured environment variables:');
    missing.forEach(key => console.error(`   - ${key}`));
    console.error('\nPlease update your .env file with Twilio credentials.');
    console.error('See TWILIO_SETUP.md for setup instructions.');
    process.exit(1);
  }
}

async function testTwilioConnection() {
  console.log('🔧 Twilio Direct Line Test\n');

  // Validate environment
  validateEnv();

  console.log('✓ Environment variables configured');
  console.log(`  Account SID: ${TWILIO_ACCOUNT_SID.substring(0, 10)}...`);
  console.log(`  Twilio Number: ${TWILIO_PHONE_NUMBER}`);
  console.log(`  Your Number: ${USER_PHONE_NUMBER}\n`);

  // Initialize Twilio client
  const client = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);

  try {
    // Test 1: Verify credentials
    console.log('📡 Test 1: Verifying Twilio credentials...');
    const account = await client.api.v2010.accounts(TWILIO_ACCOUNT_SID).fetch();
    console.log(`✓ Account verified: ${account.friendlyName}`);
    console.log(`  Status: ${account.status}`);
    console.log(`  Type: ${account.type}\n`);

    // Test 2: Check balance (trial accounts show $15 free credit)
    console.log('💰 Test 2: Checking account balance...');
    const balance = await client.balance.fetch();
    console.log(`✓ Balance: ${balance.currency} ${balance.balance}`);
    if (account.type === 'Trial') {
      console.log('  (Trial account - $15 free credit)\n');
    } else {
      console.log();
    }

    // Test 3: Verify phone number ownership
    console.log('📞 Test 3: Verifying Twilio phone number...');
    const phoneNumbers = await client.incomingPhoneNumbers.list();
    const ownedNumber = phoneNumbers.find(n => n.phoneNumber === TWILIO_PHONE_NUMBER);

    if (!ownedNumber) {
      console.error(`❌ Phone number ${TWILIO_PHONE_NUMBER} not found in your account!`);
      console.error('   Available numbers:');
      phoneNumbers.forEach(n => console.error(`   - ${n.phoneNumber}`));
      process.exit(1);
    }

    console.log(`✓ Phone number verified: ${ownedNumber.phoneNumber}`);
    console.log(`  Friendly Name: ${ownedNumber.friendlyName}`);
    console.log(`  Voice Enabled: ${ownedNumber.capabilities.voice}`);
    console.log(`  SMS Enabled: ${ownedNumber.capabilities.sms}\n`);

    // Test 4: Check verified caller IDs (trial account limitation)
    if (account.type === 'Trial') {
      console.log('🔒 Test 4: Checking verified caller IDs (trial limitation)...');
      const callerIds = await client.outgoingCallerIds.list();
      const verified = callerIds.find(c => c.phoneNumber === USER_PHONE_NUMBER);

      if (!verified) {
        console.warn(`⚠️  Your number ${USER_PHONE_NUMBER} is NOT verified!`);
        console.warn('   Trial accounts can only call verified numbers.');
        console.warn('   To verify: Twilio Console → Phone Numbers → Verified Caller IDs\n');
      } else {
        console.log(`✓ Your number is verified: ${verified.phoneNumber}`);
        console.log(`  Friendly Name: ${verified.friendlyName}\n`);
      }
    }

    // Test 5: Make a test call
    console.log('📲 Test 5: Ready to make test call!');
    console.log(`   From: ${TWILIO_PHONE_NUMBER}`);
    console.log(`   To: ${USER_PHONE_NUMBER}\n`);

    console.log('Do you want to make a test call? (yes/no)');

    // Simple prompt for confirmation
    const readline = await import('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.question('> ', async (answer) => {
      if (answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y') {
        console.log('\n📞 Calling your phone...');

        try {
          const call = await client.calls.create({
            from: TWILIO_PHONE_NUMBER,
            to: USER_PHONE_NUMBER,
            twiml: `
              <Response>
                <Say voice="man">
                  Hello! This is a test call from your xSwarm Direct Line system.
                  I'm sorry Dave, I mean... this is HAL 9000.
                  If you can hear this message, your Twilio integration is working perfectly.
                  All systems operational.
                  Goodbye.
                </Say>
              </Response>
            `
          });

          console.log(`✓ Call initiated! SID: ${call.sid}`);
          console.log(`  Status: ${call.status}`);
          console.log(`\n📱 Your phone should be ringing now!\n`);
          console.log('  Answer the call to hear HAL 9000\'s test message.\n');

          // Poll call status
          console.log('Monitoring call status...');
          let attempts = 0;
          const maxAttempts = 30; // 30 seconds

          const checkStatus = async () => {
            const updated = await client.calls(call.sid).fetch();
            console.log(`  [${++attempts}s] Status: ${updated.status}`);

            if (updated.status === 'completed' || updated.status === 'failed') {
              console.log(`\n✓ Call ${updated.status}`);
              console.log(`  Duration: ${updated.duration || 0} seconds`);
              if (updated.status === 'failed') {
                console.error(`  Error: ${updated.status}`);
              }
              rl.close();
            } else if (attempts < maxAttempts) {
              setTimeout(checkStatus, 1000);
            } else {
              console.log('\n⏱️  Call monitoring timeout (still in progress)');
              rl.close();
            }
          };

          setTimeout(checkStatus, 1000);

        } catch (err) {
          console.error(`\n❌ Call failed: ${err.message}`);
          if (err.code === 21608) {
            console.error('\nThis number is not verified for your trial account.');
            console.error('Go to: Twilio Console → Phone Numbers → Verified Caller IDs');
          }
          rl.close();
        }
      } else {
        console.log('\n✓ Skipping test call.');
        console.log('\n✅ All Twilio connection tests passed!');
        console.log('   You can run this script again to make a test call.\n');
        rl.close();
      }
    });

  } catch (error) {
    console.error(`\n❌ Twilio API Error: ${error.message}`);
    if (error.code === 20003) {
      console.error('\nAuthentication failed. Check your Account SID and Auth Token.');
    } else if (error.code) {
      console.error(`Error Code: ${error.code}`);
    }
    process.exit(1);
  }
}

// Run tests
testTwilioConnection().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
