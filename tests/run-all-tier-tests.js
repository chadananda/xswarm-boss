#!/usr/bin/env node

/**
 * Unified Tier Test Runner
 *
 * Runs all tier-related tests in proper order with comprehensive reporting.
 * Supports filtering, coverage reports, and dependency management.
 */

import { readdir } from 'node:fs/promises';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRunner } from './utils/runner.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Test execution order (handles dependencies)
 */
const TEST_ORDER = [
  'unit',           // Unit tests first (no dependencies)
  'integration',    // Integration tests (database, APIs)
  'tier',           // Tier-specific tests (created in this sprint)
  'e2e',            // End-to-end tests last
];

/**
 * Test categories by tier feature
 */
const FEATURE_CATEGORIES = {
  personas: ['test-tier-integration.js'],
  voice: ['integration/database.test.js'],
  sms: ['integration/database.test.js'],
  calendar: ['test-oauth-flows.js'],
  email: ['test-oauth-flows.js'],
  collaboration: ['test-tier-integration.js'],
  all: ['test-tier-integration.js', 'test-oauth-flows.js'],
};

/**
 * Find test files in directory recursively
 */
async function findTestFiles(dir, pattern = /\.test\.js$/) {
  const files = [];

  try {
    const entries = await readdir(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = join(dir, entry.name);

      if (entry.isDirectory() && entry.name !== 'node_modules' && entry.name !== 'utils' && entry.name !== 'fixtures') {
        files.push(...(await findTestFiles(fullPath, pattern)));
      } else if (entry.isFile() && pattern.test(entry.name)) {
        files.push(fullPath);
      }
    }
  } catch (error) {
    // Directory might not exist, that's ok
  }

  return files;
}

/**
 * Sort test files by execution order
 */
function sortTestFiles(files) {
  return files.sort((a, b) => {
    const aCategory = TEST_ORDER.find(cat => a.includes(`/${cat}/`)) || 'other';
    const bCategory = TEST_ORDER.find(cat => b.includes(`/${cat}/`)) || 'other';

    const aIndex = TEST_ORDER.indexOf(aCategory);
    const bIndex = TEST_ORDER.indexOf(bCategory);

    if (aIndex !== bIndex) {
      return aIndex - bIndex;
    }

    return a.localeCompare(b);
  });
}

/**
 * Filter test files by tier or feature
 */
function filterTestFiles(files, filterType, filterValue) {
  if (filterType === 'tier') {
    // Filter by test directory or filename pattern
    return files.filter(f =>
      f.includes(`/tier/`) ||
      f.includes('tier-') ||
      f.includes('-tier.')
    );
  }

  if (filterType === 'feature') {
    // Filter by feature category
    const featureFiles = FEATURE_CATEGORIES[filterValue] || [];
    return files.filter(f =>
      featureFiles.some(pattern => f.includes(pattern))
    );
  }

  if (filterType === 'pattern') {
    // Custom pattern matching
    return files.filter(f => f.includes(filterValue));
  }

  return files;
}

/**
 * Load test suite module
 */
async function loadTestSuite(runner, filepath) {
  try {
    const module = await import(filepath);

    if (typeof module.default === 'function') {
      module.default(runner);
    } else if (typeof module.registerTests === 'function') {
      module.registerTests(runner);
    }

    return true;
  } catch (error) {
    console.error(`\n❌ Failed to load test file: ${filepath}`);
    console.error(`   ${error.message}`);
    return false;
  }
}

/**
 * Generate coverage summary
 */
function generateCoverage(runner, testFiles) {
  const stats = runner.reporter.stats;
  const coverage = {
    files_executed: testFiles.length,
    total_tests: stats.passed + stats.failed + stats.skipped,
    passed: stats.passed,
    failed: stats.failed,
    skipped: stats.skipped,
    pass_rate: stats.passed / (stats.passed + stats.failed) * 100,
    categories: {},
  };

  // Calculate per-category coverage
  TEST_ORDER.forEach(category => {
    const categoryFiles = testFiles.filter(f => f.includes(`/${category}/`));
    if (categoryFiles.length > 0) {
      coverage.categories[category] = {
        files: categoryFiles.length,
        // Additional stats would come from reporter if we tracked per-file
      };
    }
  });

  return coverage;
}

/**
 * Print coverage report
 */
function printCoverage(coverage) {
  console.log('\n📊 Test Coverage Summary\n');
  console.log(`   Files Executed:  ${coverage.files_executed}`);
  console.log(`   Total Tests:     ${coverage.total_tests}`);
  console.log(`   Passed:          ${coverage.passed}`);
  console.log(`   Failed:          ${coverage.failed}`);
  console.log(`   Skipped:         ${coverage.skipped}`);
  console.log(`   Pass Rate:       ${coverage.pass_rate.toFixed(2)}%`);

  if (Object.keys(coverage.categories).length > 0) {
    console.log('\n   By Category:');
    Object.entries(coverage.categories).forEach(([category, stats]) => {
      console.log(`     ${category.padEnd(15)} ${stats.files} files`);
    });
  }
}

/**
 * Save coverage report to file
 */
async function saveCoverage(coverage, filepath) {
  const { writeFile } = await import('node:fs/promises');
  await writeFile(filepath, JSON.stringify(coverage, null, 2));
}

/**
 * Main test runner
 */
async function main() {
  const args = process.argv.slice(2);

  // Parse CLI arguments
  const options = {
    tier: args.includes('--tier'),
    feature: args.find(arg => arg.startsWith('--feature='))?.split('=')[1],
    pattern: args.find(arg => arg.startsWith('--pattern='))?.split('=')[1],
    verbose: args.includes('--verbose') || args.includes('-v'),
    coverage: args.includes('--coverage') || args.includes('-c'),
    saveCoverage: args.find(arg => arg.startsWith('--coverage-output='))?.split('=')[1],
    saveResults: args.find(arg => arg.startsWith('--output='))?.split('=')[1],
    help: args.includes('--help') || args.includes('-h'),
  };

  // Show help
  if (options.help) {
    console.log(`
🧪 xSwarm Tier Test Runner

Usage: node run-all-tier-tests.js [options]

Options:
  --tier                  Run only tier-related tests
  --feature=<name>        Run tests for specific feature (personas, voice, sms, calendar, email, etc.)
  --pattern=<string>      Filter tests by filename pattern
  --verbose, -v           Verbose output
  --coverage, -c          Show coverage report
  --coverage-output=<file> Save coverage to JSON file
  --output=<file>         Save test results to JSON file
  --help, -h              Show this help message

Examples:
  node run-all-tier-tests.js                           # Run all tests
  node run-all-tier-tests.js --tier                    # Run tier tests only
  node run-all-tier-tests.js --feature=personas        # Run persona feature tests
  node run-all-tier-tests.js --pattern=oauth           # Run OAuth-related tests
  node run-all-tier-tests.js --coverage -v             # Verbose with coverage
`);
    process.exit(0);
  }

  console.log('\n🧪 xSwarm Tier Test Suite\n');

  // Find all test files
  const allFiles = await findTestFiles(__dirname);

  // Apply filters
  let testFiles = allFiles;

  if (options.tier) {
    testFiles = filterTestFiles(testFiles, 'tier', null);
    console.log('🎯 Running tier tests only\n');
  } else if (options.feature) {
    testFiles = filterTestFiles(testFiles, 'feature', options.feature);
    console.log(`🎯 Running ${options.feature} feature tests\n`);
  } else if (options.pattern) {
    testFiles = filterTestFiles(testFiles, 'pattern', options.pattern);
    console.log(`🎯 Running tests matching: ${options.pattern}\n`);
  }

  // Sort by execution order
  testFiles = sortTestFiles(testFiles);

  if (testFiles.length === 0) {
    console.log('⚠️  No test files found matching criteria\n');
    process.exit(0);
  }

  console.log(`📂 Found ${testFiles.length} test file(s):\n`);
  testFiles.forEach(f => {
    const category = TEST_ORDER.find(cat => f.includes(`/${cat}/`)) || 'other';
    console.log(`   [${category}] ${basename(f)}`);
  });
  console.log('');

  // Create runner
  const runner = createRunner();

  // Load all test suites
  let loadedCount = 0;
  for (const filepath of testFiles) {
    const loaded = await loadTestSuite(runner, filepath);
    if (loaded) loadedCount++;
  }

  if (loadedCount === 0) {
    console.log('❌ No test suites loaded successfully\n');
    process.exit(1);
  }

  console.log(`✅ Loaded ${loadedCount}/${testFiles.length} test suite(s)\n`);
  console.log('🏃 Running tests...\n');

  // Run tests
  const exitCode = await runner.run();

  // Generate and display coverage
  if (options.coverage || options.saveCoverage) {
    const coverage = generateCoverage(runner, testFiles);
    printCoverage(coverage);

    if (options.saveCoverage) {
      await saveCoverage(coverage, options.saveCoverage);
      console.log(`\n✅ Coverage saved to ${options.saveCoverage}`);
    }
  }

  // Save detailed results
  if (options.saveResults) {
    await runner.saveResults(options.saveResults);
    console.log(`\n✅ Results saved to ${options.saveResults}`);
  }

  process.exit(exitCode);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('\n❌ Test runner failed:', error);
    process.exit(1);
  });
}

export { main, findTestFiles, sortTestFiles, filterTestFiles };
