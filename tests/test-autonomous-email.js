#!/usr/bin/env node
/**
 * Test Autonomous Email Response System
 * Simulates inbound email processing with Claude AI
 */

const TUNNEL_URL = "https://tion-fifteen-substantial-jimmy.trycloudflare.com";

// Simulate inbound email data (what SendGrid would send)
const emailData = new URLSearchParams({
  from: 'Chad Jones <chadananda@gmail.com>',
  to: 'Boss <chadananda@gmail.com>',
  subject: 'Test Autonomous Response: Project Status Request',
  text: `Hi Boss,

I need an update on the current status of the xSwarm project. Specifically:

1. What's the current state of the SMS integration?
2. Are there any blocking issues with the voice calls?
3. When will the autonomous response system be fully operational?

Also, can you explain how the Claude AI integration works and what capabilities it provides?

Thanks,
Chad`,
  html: ''
});

console.log('🤖 Testing Autonomous Email Response System');
console.log('==========================================\n');

console.log('📧 Simulating inbound email:');
console.log(`From: chadananda@gmail.com`);
console.log(`To: Boss (chadananda@gmail.com)`);
console.log(`Subject: Test Autonomous Response: Project Status Request`);
console.log(`\nProcessing with Claude AI...\n`);

try {
  const response = await fetch(`${TUNNEL_URL}/email/inbound`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: emailData.toString(),
  });

  if (response.ok) {
    console.log('✅ Email processed successfully!');
    console.log('📬 Claude AI should be generating an intelligent response...');
    console.log('\n🎯 Check your Gmail inbox for the autonomous response!');

    // Give it a moment to process
    console.log('\n⏳ Waiting 5 seconds for email to send...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    console.log('✨ If you received an intelligent email response, the autonomous system is working!');
  } else {
    console.log('❌ Error processing email:');
    console.log(`Status: ${response.status}`);
    console.log(`Response: ${await response.text()}`);
  }
} catch (error) {
  console.error('❌ Error testing autonomous email:', error.message);
}