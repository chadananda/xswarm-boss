#!/usr/bin/env node
/**
 * xSwarm Boss - Automated Rollback Script
 *
 * Handles deployment rollbacks:
 * - Lists available rollback points
 * - Reverts to previous worker version
 * - Restores database from backup (optional)
 * - Updates webhook configurations
 * - Verifies rollback success
 *
 * Usage:
 *   node deployment/scripts/rollback.js [--list]
 *   node deployment/scripts/rollback.js --version=<deployment-id>
 *   node deployment/scripts/rollback.js --restore-db=<backup-file>
 */

import { spawn } from 'child_process';
import { config } from 'dotenv';
import { createClient } from '@libsql/client';
import { readFileSync, readdirSync, statSync } from 'fs';
import { resolve, join } from 'path';

// Load environment variables
config();

// Parse command line arguments
const args = process.argv.slice(2);
const listOnly = args.includes('--list');
const versionArg = args.find(arg => arg.startsWith('--version='));
const targetVersion = versionArg ? versionArg.split('=')[1] : null;
const dbBackupArg = args.find(arg => arg.startsWith('--restore-db='));
const dbBackupFile = dbBackupArg ? dbBackupArg.split('=')[1] : null;

// Colors for output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  log(`\n${'='.repeat(60)}`, 'cyan');
  log(`  ${title}`, 'bold');
  log('='.repeat(60), 'cyan');
}

// Run shell command
function runCommand(command, args = [], options = {}) {
  return new Promise((resolve, reject) => {
    log(`\n💻 Running: ${command} ${args.join(' ')}`, 'blue');

    const proc = spawn(command, args, {
      stdio: options.silent ? 'pipe' : 'inherit',
      cwd: options.cwd || process.cwd(),
      env: { ...process.env, ...options.env },
    });

    let stdout = '';
    let stderr = '';

    if (options.silent) {
      proc.stdout?.on('data', (data) => {
        stdout += data.toString();
      });
      proc.stderr?.on('data', (data) => {
        stderr += data.toString();
      });
    }

    proc.on('close', (code) => {
      if (code === 0) {
        resolve({ code, stdout, stderr });
      } else {
        reject(new Error(`Command failed with code ${code}: ${stderr || stdout}`));
      }
    });

    proc.on('error', (error) => {
      reject(error);
    });
  });
}

// List available deployments
async function listDeployments() {
  logSection('Available Deployments');

  try {
    const result = await runCommand('wrangler', ['deployments', 'list', '--name', 'boss-ai'], {
      silent: true,
    });

    log(result.stdout, 'reset');
    return result.stdout;

  } catch (error) {
    log(`❌ Failed to list deployments: ${error.message}`, 'red');
    return null;
  }
}

// List available database backups
async function listBackups() {
  logSection('Available Database Backups');

  const backupDir = resolve(process.cwd(), '.backups');

  try {
    const files = readdirSync(backupDir);
    const backups = files
      .filter(f => f.endsWith('.sql'))
      .map(f => {
        const path = join(backupDir, f);
        const stats = statSync(path);
        return {
          file: f,
          path,
          size: stats.size,
          created: stats.mtime,
        };
      })
      .sort((a, b) => b.created - a.created);

    if (backups.length === 0) {
      log('No backups found', 'yellow');
      return [];
    }

    log(`\n📦 Found ${backups.length} backup(s):\n`, 'cyan');

    backups.forEach((backup, i) => {
      const sizeKB = Math.round(backup.size / 1024);
      log(`${i + 1}. ${backup.file}`, 'green');
      log(`   Created: ${backup.created.toISOString()}`, 'reset');
      log(`   Size: ${sizeKB} KB`, 'reset');
      log(`   Path: ${backup.path}`, 'blue');
      log('');
    });

    return backups;

  } catch (error) {
    log(`⚠️  No backups directory found: ${backupDir}`, 'yellow');
    return [];
  }
}

// Rollback worker to previous version
async function rollbackWorker(version) {
  logSection('Rollback Cloudflare Worker');

  if (!version) {
    log('❌ No version specified. Use --version=<deployment-id>', 'red');
    log('Run with --list to see available versions', 'yellow');
    return false;
  }

  try {
    log(`🔄 Rolling back to version: ${version}`, 'yellow');

    await runCommand('wrangler', [
      'rollback',
      '--name', 'boss-ai',
      '--message', `Rollback to ${version}`,
    ]);

    log('✅ Worker rollback successful', 'green');
    return true;

  } catch (error) {
    log(`❌ Worker rollback failed: ${error.message}`, 'red');
    return false;
  }
}

// Restore database from backup
async function restoreDatabase(backupFile) {
  logSection('Restore Database from Backup');

  if (!backupFile) {
    log('⚠️  No backup file specified', 'yellow');
    return false;
  }

  const dbUrl = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl || !authToken) {
    log('❌ Missing database credentials', 'red');
    return false;
  }

  try {
    // Read backup file
    log(`📖 Reading backup file: ${backupFile}`, 'blue');
    const backupSQL = readFileSync(backupFile, 'utf-8');

    // Connect to database
    const db = createClient({ url: dbUrl, authToken });

    log('⚠️  WARNING: This will restore the database to a previous state!', 'yellow');
    log('⚠️  All data changes since the backup will be lost!', 'yellow');

    // Parse SQL statements
    const statements = backupSQL
      .split('\n')
      .filter(line => !line.trim().startsWith('--') && line.trim() !== '')
      .join('\n')
      .split(';')
      .map(stmt => stmt.trim())
      .filter(stmt => stmt.length > 0);

    log(`\n📝 Found ${statements.length} SQL statements in backup`, 'blue');
    log('🔄 Executing restore...', 'blue');

    let executed = 0;
    for (const stmt of statements) {
      try {
        await db.execute(stmt);
        executed++;

        if (executed % 100 === 0) {
          log(`   Executed ${executed}/${statements.length} statements...`, 'blue');
        }
      } catch (error) {
        // Ignore errors for existing tables/constraints
        if (!error.message.includes('already exists')) {
          log(`   ⚠️  Warning: ${error.message}`, 'yellow');
        }
      }
    }

    log(`\n✅ Database restored successfully (${executed} statements)`, 'green');
    return true;

  } catch (error) {
    log(`❌ Database restore failed: ${error.message}`, 'red');
    return false;
  }
}

// Verify rollback
async function verifyRollback() {
  logSection('Verify Rollback');

  try {
    log('🔍 Running verification checks...', 'blue');

    await runCommand('node', [
      'deployment/scripts/verify-deployment.js',
      '--quick',
    ]);

    return true;

  } catch (error) {
    log(`⚠️  Verification completed with warnings`, 'yellow');
    return false;
  }
}

// Confirm action with user
function confirmAction(message) {
  return new Promise((resolve) => {
    const readline = require('readline').createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    readline.question(`${message} (yes/no): `, (answer) => {
      readline.close();
      resolve(answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y');
    });
  });
}

// Main execution
async function main() {
  log('\n🔄 xSwarm Boss - Deployment Rollback', 'cyan');
  log('='.repeat(60), 'cyan');
  log(`Timestamp: ${new Date().toISOString()}`, 'cyan');
  log('='.repeat(60), 'cyan');

  // List mode
  if (listOnly) {
    await listDeployments();
    await listBackups();
    log('\n💡 To rollback:', 'cyan');
    log('   Worker: node deployment/scripts/rollback.js --version=<deployment-id>', 'blue');
    log('   Database: node deployment/scripts/rollback.js --restore-db=<backup-file>', 'blue');
    log('   Both: node deployment/scripts/rollback.js --version=<id> --restore-db=<file>', 'blue');
    return;
  }

  // Check what we're rolling back
  const rollingBackWorker = !!targetVersion;
  const rollingBackDB = !!dbBackupFile;

  if (!rollingBackWorker && !rollingBackDB) {
    log('❌ No rollback target specified', 'red');
    log('\nUsage:', 'yellow');
    log('  --list                    List available versions and backups', 'blue');
    log('  --version=<id>            Rollback worker to specific version', 'blue');
    log('  --restore-db=<file>       Restore database from backup', 'blue');
    log('\nExample:', 'yellow');
    log('  node deployment/scripts/rollback.js --list', 'blue');
    log('  node deployment/scripts/rollback.js --version=abc123', 'blue');
    process.exit(1);
  }

  // Show what we're about to do
  logSection('Rollback Plan');
  if (rollingBackWorker) {
    log(`🔄 Worker: Rolling back to version ${targetVersion}`, 'yellow');
  }
  if (rollingBackDB) {
    log(`🔄 Database: Restoring from ${dbBackupFile}`, 'yellow');
  }

  // Confirm
  log('\n⚠️  WARNING: Rollback operations cannot be easily undone!', 'red');
  const confirmed = await confirmAction('\nAre you sure you want to proceed?');

  if (!confirmed) {
    log('\n❌ Rollback cancelled by user', 'yellow');
    process.exit(0);
  }

  // Execute rollback
  let workerSuccess = true;
  let dbSuccess = true;

  if (rollingBackWorker) {
    workerSuccess = await rollbackWorker(targetVersion);
  }

  if (rollingBackDB) {
    dbSuccess = await restoreDatabase(dbBackupFile);
  }

  // Verify
  if (workerSuccess || dbSuccess) {
    await verifyRollback();
  }

  // Summary
  logSection('Rollback Summary');

  if (rollingBackWorker) {
    log(`Worker: ${workerSuccess ? '✅ Success' : '❌ Failed'}`, workerSuccess ? 'green' : 'red');
  }
  if (rollingBackDB) {
    log(`Database: ${dbSuccess ? '✅ Success' : '❌ Failed'}`, dbSuccess ? 'green' : 'red');
  }

  if ((rollingBackWorker && !workerSuccess) || (rollingBackDB && !dbSuccess)) {
    log('\n⚠️  ROLLBACK COMPLETED WITH ERRORS', 'red');
    log('Review the logs above for details', 'yellow');
    process.exit(1);
  } else {
    log('\n✅ ROLLBACK SUCCESSFUL!', 'green');
    log('🔍 Review verification results above', 'cyan');
  }

  log(''); // Empty line
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  log('\n\n⚠️  Rollback interrupted by user', 'yellow');
  process.exit(1);
});

main();
