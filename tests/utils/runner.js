/**
 * Test Runner
 * Simple test runner using Node.js built-in test functionality
 */

import { createReporter } from './reporter.js';

/**
 * Test context for organizing tests
 */
class TestContext {
  constructor(name, reporter) {
    this.name = name;
    this.reporter = reporter;
    this.beforeEachHooks = [];
    this.afterEachHooks = [];
    this.beforeAllHooks = [];
    this.afterAllHooks = [];
  }

  /**
   * Register a before-each hook
   */
  beforeEach(fn) {
    this.beforeEachHooks.push(fn);
  }

  /**
   * Register an after-each hook
   */
  afterEach(fn) {
    this.afterEachHooks.push(fn);
  }

  /**
   * Register a before-all hook
   */
  beforeAll(fn) {
    this.beforeAllHooks.push(fn);
  }

  /**
   * Register an after-all hook
   */
  afterAll(fn) {
    this.afterAllHooks.push(fn);
  }

  /**
   * Run a test
   */
  async test(name, fn, options = {}) {
    const { skip = false, timeout = 30000 } = options;

    if (skip) {
      this.reporter.addResult({
        name,
        status: 'skip',
        duration: 0,
      });
      return;
    }

    const startTime = Date.now();
    let status = 'pass';
    let error = null;

    try {
      // Run before-each hooks
      for (const hook of this.beforeEachHooks) {
        await hook();
      }

      // Run test with timeout
      await Promise.race([
        fn(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error(`Test timeout (${timeout}ms)`)), timeout)
        ),
      ]);
    } catch (err) {
      status = 'fail';
      error = err;
    } finally {
      // Run after-each hooks
      for (const hook of this.afterEachHooks) {
        try {
          await hook();
        } catch (hookError) {
          if (status === 'pass') {
            status = 'fail';
            error = hookError;
          }
        }
      }
    }

    const duration = Date.now() - startTime;

    this.reporter.addResult({
      name,
      status,
      duration,
      error,
    });
  }

  /**
   * Run setup hooks
   */
  async runSetup() {
    for (const hook of this.beforeAllHooks) {
      await hook();
    }
  }

  /**
   * Run teardown hooks
   */
  async runTeardown() {
    for (const hook of this.afterAllHooks) {
      await hook();
    }
  }
}

/**
 * Test suite runner
 */
export class TestRunner {
  constructor() {
    this.reporter = createReporter();
    this.suites = [];
  }

  /**
   * Define a test suite
   */
  describe(name, fn) {
    const context = new TestContext(name, this.reporter);
    this.suites.push({ name, context, fn });
  }

  /**
   * Run all test suites
   */
  async run() {
    this.reporter.start();

    for (const suite of this.suites) {
      this.reporter.startSuite(suite.name);

      try {
        // Run setup
        await suite.context.runSetup();

        // Run suite
        await suite.fn(suite.context);

        // Run teardown
        await suite.context.runTeardown();
      } catch (error) {
        this.reporter.addResult({
          name: 'Suite setup/teardown',
          status: 'fail',
          error,
        });
      }

      this.reporter.endSuite();
    }

    this.reporter.end();

    // Print summary
    const exitCode = this.reporter.printSummary();

    return exitCode;
  }

  /**
   * Save results to file
   */
  async saveResults(filename) {
    await this.reporter.saveToFile(filename);
  }
}

/**
 * Create a test runner
 */
export function createRunner() {
  return new TestRunner();
}

/**
 * Convenience function to run a test file
 */
export async function runTestFile(testFn) {
  const runner = createRunner();

  // Pass describe function to test file
  await testFn((name, fn) => runner.describe(name, fn));

  // Run tests
  const exitCode = await runner.run();

  return exitCode;
}

/**
 * Helper to create a test suite
 */
export function describe(runner, name, fn) {
  runner.describe(name, fn);
}

/**
 * Helper for individual test
 */
export function it(context, name, fn, options) {
  return context.test(name, fn, options);
}

export default {
  TestRunner,
  createRunner,
  runTestFile,
  describe,
  it,
};
