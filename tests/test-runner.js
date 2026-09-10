#!/usr/bin/env node
// Root test runner. Discovers the suites that can actually run here, aggregates their
// results, and prints a summary the quality gate can parse.
// Deps: node builtins only. Usage: node tests/test-runner.js [--filter=name] [--verbose]
//
// The gate treats a failing test as a hard bar rather than a ratchet, so this must report
// real numbers: a suite that cannot run is reported as SKIPPED and named, never counted as
// passing. Silence is what let `npm test` sit broken against a deleted file while the gate
// read "0 passed, 0 failed" and waved it through.

import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const verbose = argv.includes('--verbose');
const filter = (argv.find((a) => a.startsWith('--filter=')) || '').slice('--filter='.length);

// A suite declares how to run itself and how to know it is runnable. `available` keeps a
// missing toolchain honest — it becomes a named skip in the output, not a silent zero.
const SUITES = [
  {
    name: 'server',
    kind: 'unit',
    cwd: join(ROOT, 'packages/server'),
    available: () =>
      existsSync(join(ROOT, 'packages/server/node_modules')) ||
      'dependencies not installed (run `pnpm install` in packages/server)',
    cmd: ['node', ['--test', '--test-reporter=tap', 'src/simple-index.test.js']],
    parse: tapCounts,
  },
  {
    name: 'assistant',
    kind: 'unit',
    cwd: ROOT,
    available: () =>
      hasPytest() || 'pytest is not installed for this interpreter',
    cmd: ['python3', ['-m', 'pytest', '-q', 'tests/assistant', 'packages/voice']],
    parse: pytestCounts,
  },
];

function hasPytest() {
  return spawnSync('python3', ['-c', 'import pytest'], { stdio: 'ignore' }).status === 0;
}

// node --test --test-reporter=tap ends with "# pass N" / "# fail N".
function tapCounts(out) {
  const n = (re) => { const m = out.match(re); return m ? parseInt(m[1], 10) : 0; };
  return { passed: n(/^# pass (\d+)$/m), failed: n(/^# fail (\d+)$/m) };
}

// pytest -q ends with e.g. "3 failed, 44 passed in 0.42s".
function pytestCounts(out) {
  const n = (word) => { const m = out.match(new RegExp(`(\\d+) ${word}`)); return m ? parseInt(m[1], 10) : 0; };
  return { passed: n('passed'), failed: n('failed') + n('error') + n('errors') };
}

let passed = 0;
let failed = 0;
const skipped = [];

for (const suite of SUITES) {
  if (filter && !suite.name.includes(filter) && !suite.kind.includes(filter)) continue;

  const why = suite.available();
  if (why !== true) {
    skipped.push(`${suite.name}: ${why}`);
    console.log(`SKIP  ${suite.name} — ${why}`);
    continue;
  }

  const [bin, args] = suite.cmd;
  const r = spawnSync(bin, args, { cwd: suite.cwd, encoding: 'utf8', timeout: 600000 });
  const out = `${r.stdout || ''}${r.stderr || ''}`;
  if (verbose) console.log(out);

  const c = suite.parse(out);
  // A non-zero exit with no parsed failure means the suite died before reporting — a crash
  // must not read as "nothing failed".
  if (r.status !== 0 && c.failed === 0) {
    c.failed = 1;
    if (!verbose) console.log(out.split('\n').slice(-25).join('\n'));
  }
  passed += c.passed;
  failed += c.failed;
  console.log(`${c.failed ? 'FAIL' : 'ok  '}  ${suite.name} — ${c.passed} passed, ${c.failed} failed`);
}

if (skipped.length) {
  console.log(`\n${skipped.length} suite(s) skipped:`);
  for (const s of skipped) console.log(`  ${s}`);
}

// The line the gate reads.
console.log(`\nTests  ${failed} failed | ${passed} passed`);
process.exit(failed > 0 ? 1 : 0);
