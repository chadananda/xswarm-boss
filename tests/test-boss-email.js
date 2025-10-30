#!/usr/bin/env node
/**
 * Test Boss App Email Functionality
 *
 * Tests the actual Boss app sending email via its API
 */

const TUNNEL_URL = "https://tion-fifteen-substantial-jimmy.trycloudflare.com";

const emailData = {
  to: "chadananda@gmail.com",
  subject: "🤖 Boss Communication Test - FROM THE BOSS APP",
  message: `Hello Chad!

This message is being sent BY THE BOSS APP, not by Claude directly. This is the proper way to test the Boss assistant communication system.

The Boss app can now:
✅ Send you progress reports via email
✅ Receive your directions when you reply
✅ Process your voice calls through MOSHI
✅ Receive your SMS messages

To test bidirectional communication:
1. Reply to this email - it will be processed by the Boss webhook
2. Call +18447472899 to speak with the Boss via MOSHI voice AI
3. Send SMS to +18447472899 to send text messages to the Boss

This is the REAL Boss app in action!

Best,
Your Boss Assistant 🤖`
};

console.log('🤖 Testing Boss App Email Functionality');
console.log('======================================\n');

try {
  const response = await fetch(`${TUNNEL_URL}/api/boss/email`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(emailData),
  });

  const result = await response.json();

  if (response.ok) {
    console.log('✅ Boss app successfully sent email!');
    console.log(`📧 From Boss App to: ${emailData.to}`);
    console.log(`📧 Subject: ${emailData.subject}`);
    console.log('\n🎯 Check your inbox for the Boss app email!');
  } else {
    console.log('❌ Boss app email failed:');
    console.log(result);
  }
} catch (error) {
  console.error('❌ Error testing Boss app email:', error.message);
}