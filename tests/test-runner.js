#!/usr/bin/env node

/**
 * Main Test Runner
 * Runs all tests in the test suite
 */

import { readdir } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRunner } from './utils/runner.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Find all test files recursively
 */
async function findTestFiles(dir, pattern = /\.test\.js$/) {
  const files = [];
  const entries = await readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = join(dir, entry.name);

    if (entry.isDirectory() && entry.name !== 'node_modules' && entry.name !== 'utils') {
      files.push(...(await findTestFiles(fullPath, pattern)));
    } else if (entry.isFile() && pattern.test(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Load and register test suite
 */
async function loadTestSuite(runner, filepath) {
  try {
    const module = await import(filepath);

    if (typeof module.default === 'function') {
      module.default(runner);
    } else if (typeof module.registerTests === 'function') {
      module.registerTests(runner);
    }
  } catch (error) {
    console.error(`Failed to load test file: ${filepath}`);
    console.error(error);
    throw error;
  }
}

/**
 * Main test runner
 */
async function main() {
  const args = process.argv.slice(2);

  // Parse CLI arguments
  const options = {
    pattern: args.find(arg => arg.startsWith('--pattern='))?.split('=')[1] || '*.test.js',
    filter: args.find(arg => arg.startsWith('--filter='))?.split('=')[1],
    verbose: args.includes('--verbose') || args.includes('-v'),
    saveResults: args.find(arg => arg.startsWith('--output='))?.split('=')[1],
  };

  console.log('\n🧪 xSwarm Test Suite\n');

  // Find test files
  const testFiles = await findTestFiles(__dirname);

  // Filter test files if pattern provided
  const filteredFiles = options.filter
    ? testFiles.filter(f => f.includes(options.filter))
    : testFiles;

  if (filteredFiles.length === 0) {
    console.log('No test files found.');
    process.exit(0);
  }

  console.log(`Found ${filteredFiles.length} test file(s)\n`);

  // Create runner
  const runner = createRunner();

  // Load all test suites
  for (const filepath of filteredFiles) {
    await loadTestSuite(runner, filepath);
  }

  // Run tests
  const exitCode = await runner.run();

  // Save results if requested
  if (options.saveResults) {
    await runner.saveResults(options.saveResults);
    console.log(`\n✓ Results saved to ${options.saveResults}`);
  }

  process.exit(exitCode);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('Test runner failed:', error);
    process.exit(1);
  });
}

export { main, findTestFiles, loadTestSuite };
