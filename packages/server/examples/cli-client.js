#!/usr/bin/env node
/**
 * Simple CLI Client for Boss AI Unified API
 *
 * Usage:
 *   node cli-client.js "What's my schedule today?"
 *   node cli-client.js "Schedule meeting tomorrow at 2pm"
 *   node cli-client.js help
 */

// Configuration
const API_URL = process.env.BOSS_API_URL || 'http://localhost:8787/api/message';
const USER_EMAIL = process.env.BOSS_USER_EMAIL || 'chadananda@gmail.com';

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

/**
 * Send message to Boss AI
 */
async function sendMessage(content) {
  try {
    console.log(`${colors.dim}Sending to: ${API_URL}${colors.reset}`);
    console.log(`${colors.dim}From: ${USER_EMAIL}${colors.reset}`);
    console.log(`${colors.dim}Message: "${content}"${colors.reset}\n`);

    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: USER_EMAIL,
        content: content,
        channel: 'cli',
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Display response
    if (data.success) {
      console.log(`${colors.green}${colors.bright}✓ Success${colors.reset}\n`);
      console.log(`${colors.cyan}Boss Response:${colors.reset}`);
      console.log(`${data.message}\n`);

      if (data.metadata?.user) {
        console.log(`${colors.dim}Processed for: ${data.metadata.user}${colors.reset}`);
      }
      if (data.timestamp) {
        console.log(`${colors.dim}Timestamp: ${data.timestamp}${colors.reset}`);
      }
    } else {
      console.log(`${colors.red}${colors.bright}✗ Error${colors.reset}\n`);
      console.log(`${colors.red}${data.message}${colors.reset}\n`);

      if (data.metadata?.reason) {
        console.log(`${colors.dim}Reason: ${data.metadata.reason}${colors.reset}`);
      }
    }

  } catch (error) {
    console.error(`${colors.red}${colors.bright}✗ Request Failed${colors.reset}\n`);
    console.error(`${colors.red}${error.message}${colors.reset}\n`);

    if (error.cause) {
      console.error(`${colors.dim}Cause: ${error.cause}${colors.reset}`);
    }

    process.exit(1);
  }
}

/**
 * Show usage information
 */
function showUsage() {
  console.log(`${colors.bright}Boss AI CLI Client${colors.reset}\n`);
  console.log(`${colors.cyan}Usage:${colors.reset}`);
  console.log(`  node cli-client.js "your message here"\n`);
  console.log(`${colors.cyan}Examples:${colors.reset}`);
  console.log(`  node cli-client.js "What's my schedule today?"`);
  console.log(`  node cli-client.js "Schedule meeting tomorrow at 2pm"`);
  console.log(`  node cli-client.js "Remind me to call John at 3pm"`);
  console.log(`  node cli-client.js help\n`);
  console.log(`${colors.cyan}Environment Variables:${colors.reset}`);
  console.log(`  BOSS_API_URL     API endpoint (default: http://localhost:8787/api/message)`);
  console.log(`  BOSS_USER_EMAIL  Your email address (default: chadananda@gmail.com)\n`);
  console.log(`${colors.cyan}Current Configuration:${colors.reset}`);
  console.log(`  API URL: ${API_URL}`);
  console.log(`  User Email: ${USER_EMAIL}\n`);
}

/**
 * Main function
 */
async function main() {
  const args = process.argv.slice(2);

  // Show usage if no arguments or --help flag
  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    showUsage();
    process.exit(0);
  }

  // Combine all arguments into a single message
  const message = args.join(' ');

  // Send the message
  await sendMessage(message);
}

// Run the CLI
main().catch((error) => {
  console.error(`${colors.red}Unexpected error: ${error.message}${colors.reset}`);
  process.exit(1);
});
