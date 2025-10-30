#!/usr/bin/env node

/**
 * Example: Using the Claude Code Bridge
 *
 * This demonstrates how the Boss Assistant processes development tasks
 * from user messages via SMS or email.
 */

import {
  detectTask,
  processDevTask,
  formatResultsForSMS,
  formatResultsForEmail
} from '../packages/server/src/lib/claude-code-bridge.js';

// Example user
const user = {
  name: 'Chad Ananda',
  username: 'chadananda',
  email: 'chadananda@gmail.com',
  phone: '+15551234567',
  bossEmail: 'chad@xswarm.ai',
  bossPhone: '+15559876543'
};

console.log('🤖 Boss Assistant - Development Task Example\n');
console.log('═'.repeat(70));

// Example 1: Simple Status Check (Safe)
console.log('\n📱 Example 1: SMS - Check Git Status (Safe Operation)\n');
console.log('-'.repeat(70));

const example1Message = 'Check git status';
console.log(`User SMS: "${example1Message}"`);

const task1 = detectTask(example1Message);
console.log(`\nDetected: ${task1.type} task`);
console.log(`Risk Level: ${task1.risk}`);
console.log(`Confirmation needed: ${task1.needsConfirmation ? 'YES' : 'NO'}`);

const result1 = await processDevTask(user, example1Message, { mockMode: true });

if (result1.success) {
  console.log('\nBoss Response (SMS):');
  console.log('─'.repeat(70));
  console.log(formatResultsForSMS(result1.results));
  console.log('─'.repeat(70));
}

// Example 2: Run Tests (Safe)
console.log('\n\n📧 Example 2: Email - Run Test Suite (Safe Operation)\n');
console.log('-'.repeat(70));

const example2Message = 'Run the test suite and send me the results';
console.log(`User Email: "${example2Message}"`);

const task2 = detectTask(example2Message);
console.log(`\nDetected: ${task2.type} task`);
console.log(`Risk Level: ${task2.risk}`);

const result2 = await processDevTask(user, example2Message, { mockMode: true });

if (result2.success) {
  console.log('\nBoss Response (Email):');
  console.log('─'.repeat(70));
  console.log(formatResultsForEmail(result2.results, task2, user));
  console.log('─'.repeat(70));
}

// Example 3: Deploy (High Risk - Needs Confirmation)
console.log('\n\n📱 Example 3: SMS - Deploy to Production (High Risk)\n');
console.log('-'.repeat(70));

const example3Message = 'Deploy to production';
console.log(`User SMS: "${example3Message}"`);

const task3 = detectTask(example3Message);
console.log(`\nDetected: ${task3.type} task`);
console.log(`Risk Level: ${task3.risk}`);
console.log(`Confirmation needed: ${task3.needsConfirmation ? 'YES ⚠️' : 'NO'}`);

// First attempt without confirmation
const result3a = await processDevTask(user, example3Message, {
  mockMode: true,
  forceConfirmed: false
});

if (!result3a.success && result3a.needsConfirmation) {
  console.log('\n⚠️ Boss asks for confirmation:');
  console.log('─'.repeat(70));
  const { getConfirmationMessage } = await import('../packages/server/src/lib/claude-code-bridge.js');
  console.log(getConfirmationMessage(task3, 'sms'));
  console.log('─'.repeat(70));

  // User confirms
  console.log('\n✅ User replies: "CONFIRM"\n');

  const result3b = await processDevTask(user, 'CONFIRM ' + example3Message, {
    mockMode: true,
    forceConfirmed: true
  });

  if (result3b.success) {
    console.log('Boss Response (After Confirmation):');
    console.log('─'.repeat(70));
    console.log(formatResultsForSMS(result3b.results));
    console.log('─'.repeat(70));
  }
}

// Example 4: Force Push (Critical Risk - Always Requires Confirmation)
console.log('\n\n📧 Example 4: Email - Force Push (Critical Risk)\n');
console.log('-'.repeat(70));

const example4Message = 'Force push to main';
console.log(`User Email: "${example4Message}"`);

const task4 = detectTask(example4Message);
console.log(`\nDetected: ${task4.type} task`);
console.log(`Risk Level: ${task4.risk} 🚨`);
console.log(`Confirmation needed: ALWAYS (critical operation)`);

const result4 = await processDevTask(user, example4Message, {
  mockMode: true,
  forceConfirmed: false
});

if (!result4.success) {
  console.log('\n🚨 Boss blocks critical operation:');
  console.log('─'.repeat(70));
  const { getConfirmationMessage } = await import('../packages/server/src/lib/claude-code-bridge.js');
  console.log(getConfirmationMessage(task4, 'email'));
  console.log('─'.repeat(70));
}

// Example 5: Multiple Tasks in One Message
console.log('\n\n📱 Example 5: SMS - Multiple Tasks Detection\n');
console.log('-'.repeat(70));

const multiTaskMessages = [
  'Build and test the project',
  'Pull latest changes and run tests',
  'Check status'
];

for (const msg of multiTaskMessages) {
  const task = detectTask(msg);
  console.log(`\n"${msg}"`);
  console.log(`  → ${task.type} (${task.risk})`);
}

// Summary
console.log('\n\n' + '═'.repeat(70));
console.log('\n✅ Examples Complete!\n');
console.log('Key Takeaways:');
console.log('  • Safe tasks execute immediately (git status, tests, builds)');
console.log('  • Medium tasks ask for confirmation (commits, pushes)');
console.log('  • High tasks require explicit confirmation (deploys)');
console.log('  • Critical tasks always blocked without confirmation (force operations)');
console.log('  • Responses formatted for SMS (concise) or Email (detailed)');
console.log('  • All executions in mock mode for safety\n');
console.log('═'.repeat(70) + '\n');

console.log('💡 Try it yourself:');
console.log('   1. Send SMS to your Boss number: "Run tests"');
console.log('   2. Send email to boss@xswarm.ai: "Deploy to staging"');
console.log('   3. Reply "CONFIRM" to approve high-risk operations\n');
