/**
 * Test Reporter
 * Collects and reports test results with performance metrics
 */

/**
 * ANSI color codes for terminal output
 */
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

/**
 * Test result collector
 */
export class TestReporter {
  constructor() {
    this.results = [];
    this.suites = [];
    this.currentSuite = null;
    this.startTime = null;
    this.endTime = null;
  }

  /**
   * Start a test suite
   */
  startSuite(name) {
    this.currentSuite = {
      name,
      tests: [],
      startTime: Date.now(),
      endTime: null,
    };
    this.suites.push(this.currentSuite);
  }

  /**
   * End current test suite
   */
  endSuite() {
    if (this.currentSuite) {
      this.currentSuite.endTime = Date.now();
      this.currentSuite = null;
    }
  }

  /**
   * Record a test result
   */
  addResult(result) {
    const testResult = {
      ...result,
      suite: this.currentSuite?.name || 'Unknown',
      timestamp: Date.now(),
    };

    this.results.push(testResult);

    if (this.currentSuite) {
      this.currentSuite.tests.push(testResult);
    }
  }

  /**
   * Start the test run
   */
  start() {
    this.startTime = Date.now();
    console.log(`${colors.bright}${colors.cyan}Starting test run...${colors.reset}\n`);
  }

  /**
   * End the test run
   */
  end() {
    this.endTime = Date.now();
  }

  /**
   * Get statistics
   */
  getStats() {
    const passed = this.results.filter(r => r.status === 'pass').length;
    const failed = this.results.filter(r => r.status === 'fail').length;
    const skipped = this.results.filter(r => r.status === 'skip').length;
    const total = this.results.length;
    const duration = this.endTime - this.startTime;

    return {
      total,
      passed,
      failed,
      skipped,
      duration,
      passRate: total > 0 ? (passed / total) * 100 : 0,
    };
  }

  /**
   * Print a single test result
   */
  printResult(result, verbose = false) {
    const icon = result.status === 'pass' ? '✓' : result.status === 'fail' ? '✗' : '○';
    const color =
      result.status === 'pass' ? colors.green : result.status === 'fail' ? colors.red : colors.yellow;

    const duration = result.duration ? ` ${colors.dim}(${result.duration}ms)${colors.reset}` : '';

    console.log(`  ${color}${icon} ${result.name}${duration}${colors.reset}`);

    if (result.status === 'fail' && result.error) {
      console.log(`    ${colors.red}${result.error.message}${colors.reset}`);

      if (verbose && result.error.stack) {
        const stack = result.error.stack
          .split('\n')
          .slice(1, 4)
          .map(line => `      ${colors.dim}${line.trim()}${colors.reset}`)
          .join('\n');
        console.log(stack);
      }
    }
  }

  /**
   * Print summary report
   */
  printSummary() {
    console.log(`\n${colors.bright}Test Summary${colors.reset}`);
    console.log('─'.repeat(50));

    const stats = this.getStats();

    // Print suite summaries
    for (const suite of this.suites) {
      const passed = suite.tests.filter(t => t.status === 'pass').length;
      const failed = suite.tests.filter(t => t.status === 'fail').length;
      const duration = suite.endTime - suite.startTime;

      const statusColor = failed > 0 ? colors.red : colors.green;

      console.log(
        `\n${colors.bright}${suite.name}${colors.reset} ${colors.dim}(${duration}ms)${colors.reset}`
      );

      for (const test of suite.tests) {
        this.printResult(test);
      }

      console.log(
        `  ${statusColor}${passed} passed${colors.reset}, ${colors.red}${failed} failed${colors.reset}`
      );
    }

    // Print overall stats
    console.log('\n' + '─'.repeat(50));
    console.log(`${colors.bright}Overall Results${colors.reset}`);
    console.log(`Total:    ${stats.total} tests`);
    console.log(`${colors.green}Passed:   ${stats.passed}${colors.reset}`);
    console.log(`${colors.red}Failed:   ${stats.failed}${colors.reset}`);
    console.log(`${colors.yellow}Skipped:  ${stats.skipped}${colors.reset}`);
    console.log(`Duration: ${stats.duration}ms`);
    console.log(`Pass rate: ${stats.passRate.toFixed(2)}%`);

    // Print performance warnings
    const slowTests = this.results.filter(r => r.duration && r.duration > 1000);
    if (slowTests.length > 0) {
      console.log(`\n${colors.yellow}⚠ Slow tests (>1000ms):${colors.reset}`);
      for (const test of slowTests) {
        console.log(`  ${test.name}: ${test.duration}ms`);
      }
    }

    console.log('─'.repeat(50) + '\n');

    // Exit code based on results
    return stats.failed === 0 ? 0 : 1;
  }

  /**
   * Export results as JSON
   */
  toJSON() {
    return {
      stats: this.getStats(),
      suites: this.suites,
      results: this.results,
    };
  }

  /**
   * Save results to file
   */
  async saveToFile(filename) {
    const fs = await import('node:fs/promises');
    await fs.writeFile(filename, JSON.stringify(this.toJSON(), null, 2));
  }
}

/**
 * Create a test reporter instance
 */
export function createReporter() {
  return new TestReporter();
}

export default {
  TestReporter,
  createReporter,
};
