#!/usr/bin/env node

/**
 * Verification Script
 * Verifies that the test infrastructure is properly set up
 */

import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

let passed = 0;
let failed = 0;

function check(description, condition) {
  if (condition) {
    console.log(`${colors.green}✓${colors.reset} ${description}`);
    passed++;
  } else {
    console.log(`${colors.red}✗${colors.reset} ${description}`);
    failed++;
  }
}

console.log(`\n${colors.blue}Verifying Test Infrastructure Setup${colors.reset}\n`);

// Check directory structure
console.log('Directory Structure:');
check('tests/ directory exists', existsSync(join(__dirname)));
check('tests/unit/ directory exists', existsSync(join(__dirname, 'unit')));
check('tests/integration/ directory exists', existsSync(join(__dirname, 'integration')));
check('tests/e2e/ directory exists', existsSync(join(__dirname, 'e2e')));
check('tests/performance/ directory exists', existsSync(join(__dirname, 'performance')));
check('tests/security/ directory exists', existsSync(join(__dirname, 'security')));
check('tests/fixtures/ directory exists', existsSync(join(__dirname, 'fixtures')));
check('tests/utils/ directory exists', existsSync(join(__dirname, 'utils')));

// Check utility files
console.log('\nUtility Files:');
check('utils/assert.js exists', existsSync(join(__dirname, 'utils/assert.js')));
check('utils/http.js exists', existsSync(join(__dirname, 'utils/http.js')));
check('utils/database.js exists', existsSync(join(__dirname, 'utils/database.js')));
check('utils/reporter.js exists', existsSync(join(__dirname, 'utils/reporter.js')));
check('utils/runner.js exists', existsSync(join(__dirname, 'utils/runner.js')));

// Check test files
console.log('\nTest Files:');
check('unit/auth.test.js exists', existsSync(join(__dirname, 'unit/auth.test.js')));
check('integration/database.test.js exists', existsSync(join(__dirname, 'integration/database.test.js')));

// Check configuration files
console.log('\nConfiguration Files:');
check('config.js exists', existsSync(join(__dirname, 'config.js')));
check('test-runner.js exists', existsSync(join(__dirname, 'test-runner.js')));
check('.env.example exists', existsSync(join(__dirname, '.env.example')));

// Check documentation
console.log('\nDocumentation:');
check('README.md exists', existsSync(join(__dirname, 'README.md')));
check('QUICKSTART.md exists', existsSync(join(__dirname, 'QUICKSTART.md')));
check('IMPLEMENTATION_SUMMARY.md exists', existsSync(join(__dirname, 'IMPLEMENTATION_SUMMARY.md')));

// Check fixtures
console.log('\nFixtures:');
check('fixtures/users.json exists', existsSync(join(__dirname, 'fixtures/users.json')));

// Check GitHub Actions
console.log('\nCI/CD:');
check('.github/workflows/test.yml exists', existsSync(join(__dirname, '../.github/workflows/test.yml')));

// Test imports
console.log('\nModule Imports:');
try {
  await import('./utils/assert.js');
  check('utils/assert.js imports successfully', true);
} catch (error) {
  check('utils/assert.js imports successfully', false);
  console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
}

try {
  await import('./utils/http.js');
  check('utils/http.js imports successfully', true);
} catch (error) {
  check('utils/http.js imports successfully', false);
  console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
}

try {
  await import('./utils/database.js');
  check('utils/database.js imports successfully', true);
} catch (error) {
  check('utils/database.js imports successfully', false);
  console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
}

try {
  await import('./utils/reporter.js');
  check('utils/reporter.js imports successfully', true);
} catch (error) {
  check('utils/reporter.js imports successfully', false);
  console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
}

try {
  await import('./utils/runner.js');
  check('utils/runner.js imports successfully', true);
} catch (error) {
  check('utils/runner.js imports successfully', false);
  console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
}

try {
  await import('./config.js');
  check('config.js imports successfully', true);
} catch (error) {
  check('config.js imports successfully', false);
  console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
}

// Summary
console.log('\n' + '─'.repeat(50));
console.log(`${colors.blue}Summary${colors.reset}`);
console.log(`${colors.green}Passed: ${passed}${colors.reset}`);
console.log(`${colors.red}Failed: ${failed}${colors.reset}`);

if (failed === 0) {
  console.log(`\n${colors.green}✓ Test infrastructure is properly set up!${colors.reset}`);
  console.log(`\nNext steps:`);
  console.log(`1. Copy tests/.env.example to tests/.env`);
  console.log(`2. Configure TEST_DATABASE_URL in tests/.env`);
  console.log(`3. Start dev server: pnpm run dev:server`);
  console.log(`4. Run tests: pnpm test\n`);
  process.exit(0);
} else {
  console.log(`\n${colors.red}✗ Some checks failed. Please review the errors above.${colors.reset}\n`);
  process.exit(1);
}
