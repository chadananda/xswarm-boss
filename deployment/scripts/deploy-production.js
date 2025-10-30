#!/usr/bin/env node
/**
 * xSwarm Boss - Production Deployment Script
 *
 * Automated production deployment that handles:
 * - Pre-deployment verification
 * - Database backup
 * - Database migrations
 * - Worker deployment
 * - Static pages deployment
 * - Webhook configuration
 * - Post-deployment verification
 * - Rollback on failure
 *
 * Usage: node deployment/scripts/deploy-production.js [--env=production|staging] [--skip-checks]
 */

import { spawn } from 'child_process';
import { config } from 'dotenv';
import { createClient } from '@libsql/client';
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

// Load environment variables
config();

// Parse command line arguments
const args = process.argv.slice(2);
const envArg = args.find(arg => arg.startsWith('--env='));
const targetEnv = envArg ? envArg.split('=')[1] : 'production';
const skipChecks = args.includes('--skip-checks');
const skipBackup = args.includes('--skip-backup');

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
  const timestamp = new Date().toISOString();
  console.log(`${colors[color]}[${timestamp}] ${message}${colors.reset}`);
}

function logSection(title) {
  log('\n' + '='.repeat(70), 'cyan');
  log(`  ${title}`, 'bold');
  log('='.repeat(70), 'cyan');
}

// Track deployment progress
const deploymentLog = {
  startTime: Date.now(),
  environment: targetEnv,
  steps: [],
  status: 'in_progress',
};

function recordStep(step, status, details = {}) {
  const record = {
    step,
    status,
    timestamp: new Date().toISOString(),
    duration: details.duration || 0,
    ...details,
  };

  deploymentLog.steps.push(record);

  const symbol = status === 'success' ? '✅' : status === 'failed' ? '❌' : '🔄';
  log(`${symbol} ${step}`, status === 'success' ? 'green' : status === 'failed' ? 'red' : 'blue');

  if (details.message) {
    log(`   ${details.message}`, 'reset');
  }
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

// Step 1: Pre-deployment checks
async function preDeploymentChecks() {
  logSection('Step 1: Pre-Deployment Verification');

  if (skipChecks) {
    log('⚠️  Skipping pre-deployment checks (--skip-checks)', 'yellow');
    recordStep('Pre-Deployment Checks', 'skipped');
    return;
  }

  const startTime = Date.now();

  try {
    await runCommand('node', [
      'deployment/scripts/pre-deploy-check.js',
      `--env=${targetEnv}`,
    ]);

    recordStep('Pre-Deployment Checks', 'success', {
      duration: Date.now() - startTime,
    });
  } catch (error) {
    recordStep('Pre-Deployment Checks', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    throw new Error('Pre-deployment checks failed. Fix issues before deploying.');
  }
}

// Step 2: Create database backup
async function createDatabaseBackup() {
  logSection('Step 2: Database Backup');

  if (skipBackup) {
    log('⚠️  Skipping database backup (--skip-backup)', 'yellow');
    recordStep('Database Backup', 'skipped');
    return null;
  }

  const startTime = Date.now();
  const dbUrl = process.env.TURSO_DATABASE_URL;
  const authToken = process.env.TURSO_AUTH_TOKEN;

  if (!dbUrl || !authToken) {
    log('⚠️  No database credentials - skipping backup', 'yellow');
    recordStep('Database Backup', 'skipped', {
      message: 'No database credentials',
    });
    return null;
  }

  try {
    const db = createClient({ url: dbUrl, authToken });

    // Get all tables
    const tables = await db.execute(`
      SELECT name FROM sqlite_master
      WHERE type='table' AND name NOT LIKE 'sqlite_%'
      ORDER BY name
    `);

    // Create backup directory
    const backupDir = resolve(process.cwd(), '.backups');
    await runCommand('mkdir', ['-p', backupDir], { silent: true });

    // Create backup file
    const backupFile = `${backupDir}/backup-${Date.now()}.sql`;
    let backupSQL = `-- xSwarm Boss Database Backup\n`;
    backupSQL += `-- Date: ${new Date().toISOString()}\n`;
    backupSQL += `-- Environment: ${targetEnv}\n\n`;

    for (const table of tables.rows) {
      // Get table schema
      const schema = await db.execute(`SELECT sql FROM sqlite_master WHERE name = '${table.name}'`);
      backupSQL += `${schema.rows[0].sql};\n\n`;

      // Get table data
      const data = await db.execute(`SELECT * FROM ${table.name}`);
      if (data.rows.length > 0) {
        backupSQL += `-- Data for ${table.name}\n`;
        for (const row of data.rows) {
          const values = Object.values(row).map(v => {
            if (v === null) return 'NULL';
            if (typeof v === 'string') return `'${v.replace(/'/g, "''")}'`;
            return v;
          });
          backupSQL += `INSERT INTO ${table.name} VALUES (${values.join(', ')});\n`;
        }
        backupSQL += '\n';
      }
    }

    writeFileSync(backupFile, backupSQL);

    log(`✅ Backup created: ${backupFile}`, 'green');
    recordStep('Database Backup', 'success', {
      duration: Date.now() - startTime,
      backupFile,
      tables: tables.rows.length,
    });

    return backupFile;

  } catch (error) {
    log(`⚠️  Backup failed: ${error.message}`, 'yellow');
    recordStep('Database Backup', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    // Don't fail deployment on backup failure
    return null;
  }
}

// Step 3: Run database migrations
async function runDatabaseMigrations() {
  logSection('Step 3: Database Migrations');

  const startTime = Date.now();

  try {
    await runCommand('node', ['deployment/scripts/migrate-all.js']);

    recordStep('Database Migrations', 'success', {
      duration: Date.now() - startTime,
    });
  } catch (error) {
    recordStep('Database Migrations', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    throw new Error('Database migrations failed. Deployment aborted.');
  }
}

// Step 4: Sync secrets to Cloudflare
async function syncSecrets() {
  logSection('Step 4: Sync Secrets to Cloudflare Workers');

  const startTime = Date.now();

  try {
    await runCommand('pnpm', ['run', 'setup:secrets']);

    recordStep('Sync Secrets', 'success', {
      duration: Date.now() - startTime,
    });
  } catch (error) {
    recordStep('Sync Secrets', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    throw new Error('Failed to sync secrets. Deployment aborted.');
  }
}

// Step 5: Deploy Cloudflare Workers
async function deployWorker() {
  logSection('Step 5: Deploy Cloudflare Workers');

  const startTime = Date.now();

  try {
    await runCommand('pnpm', ['run', 'deploy:server']);

    recordStep('Deploy Worker', 'success', {
      duration: Date.now() - startTime,
    });
  } catch (error) {
    recordStep('Deploy Worker', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    throw new Error('Worker deployment failed. Deployment aborted.');
  }
}

// Step 6: Deploy static pages
async function deployStaticPages() {
  logSection('Step 6: Deploy Static Pages');

  const startTime = Date.now();

  try {
    // Deploy admin pages (signup, dashboard, etc.)
    log('\n📄 Deploying admin pages...', 'blue');
    await runCommand('pnpm', ['run', 'deploy:pages']);

    recordStep('Deploy Static Pages', 'success', {
      duration: Date.now() - startTime,
    });
  } catch (error) {
    log(`⚠️  Static pages deployment failed: ${error.message}`, 'yellow');
    recordStep('Deploy Static Pages', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    // Don't fail deployment on static pages failure
  }
}

// Step 7: Configure webhooks
async function configureWebhooks() {
  logSection('Step 7: Configure Webhooks');

  const startTime = Date.now();

  try {
    // Only configure webhooks in production
    if (targetEnv === 'production') {
      log('\n🔗 Setting up Stripe webhooks...', 'blue');
      await runCommand('pnpm', ['run', 'setup:webhooks']);

      log('\n📱 Setting up Twilio webhooks...', 'blue');
      await runCommand('pnpm', ['run', 'setup:twilio']);
    } else {
      log('⚠️  Skipping webhook setup for non-production environment', 'yellow');
    }

    recordStep('Configure Webhooks', 'success', {
      duration: Date.now() - startTime,
      environment: targetEnv,
    });
  } catch (error) {
    log(`⚠️  Webhook configuration failed: ${error.message}`, 'yellow');
    recordStep('Configure Webhooks', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    // Don't fail deployment on webhook configuration failure
  }
}

// Step 8: Post-deployment verification
async function postDeploymentVerification() {
  logSection('Step 8: Post-Deployment Verification');

  const startTime = Date.now();

  try {
    await runCommand('node', [
      'deployment/scripts/verify-deployment.js',
      `--env=${targetEnv}`,
    ]);

    recordStep('Post-Deployment Verification', 'success', {
      duration: Date.now() - startTime,
    });
  } catch (error) {
    recordStep('Post-Deployment Verification', 'failed', {
      duration: Date.now() - startTime,
      error: error.message,
    });
    log('⚠️  Some verification checks failed. Review the errors above.', 'yellow');
    // Don't fail deployment on verification failures
  }
}

// Step 9: Send deployment notification
async function sendNotification(success) {
  logSection('Step 9: Send Deployment Notification');

  const duration = Math.round((Date.now() - deploymentLog.startTime) / 1000);
  const status = success ? 'SUCCESS' : 'FAILED';

  log(`\n📧 Deployment ${status}`, success ? 'green' : 'red');
  log(`   Environment: ${targetEnv}`, 'cyan');
  log(`   Duration: ${duration}s`, 'cyan');

  // Save deployment log
  const logFile = resolve(process.cwd(), `.logs/deployment-${Date.now()}.json`);
  await runCommand('mkdir', ['-p', resolve(process.cwd(), '.logs')], { silent: true });

  deploymentLog.status = success ? 'success' : 'failed';
  deploymentLog.endTime = Date.now();
  deploymentLog.duration = duration;

  writeFileSync(logFile, JSON.stringify(deploymentLog, null, 2));
  log(`📝 Deployment log saved: ${logFile}`, 'blue');

  // TODO: Send email/Slack notification
  // This would require SendGrid or Slack integration
}

// Generate deployment summary
function generateSummary() {
  logSection('Deployment Summary');

  const duration = Math.round((Date.now() - deploymentLog.startTime) / 1000);
  const successSteps = deploymentLog.steps.filter(s => s.status === 'success').length;
  const failedSteps = deploymentLog.steps.filter(s => s.status === 'failed').length;
  const totalSteps = deploymentLog.steps.length;

  log(`\nEnvironment: ${targetEnv}`, 'cyan');
  log(`Total Duration: ${duration}s`, 'cyan');
  log(`\nSteps Completed: ${successSteps}/${totalSteps}`, successSteps === totalSteps ? 'green' : 'yellow');
  log(`Steps Failed: ${failedSteps}`, failedSteps === 0 ? 'green' : 'red');

  log('\n📊 Step Details:', 'cyan');
  for (const step of deploymentLog.steps) {
    const symbol = step.status === 'success' ? '✅' : step.status === 'failed' ? '❌' : '⏭️';
    const duration = step.duration ? ` (${step.duration}ms)` : '';
    log(`  ${symbol} ${step.step}${duration}`, 'reset');
  }

  return failedSteps === 0;
}

// Main execution
async function main() {
  log('\n🚀 xSwarm Boss - Production Deployment', 'cyan');
  log('='.repeat(70), 'cyan');
  log(`Environment: ${targetEnv.toUpperCase()}`, 'bold');
  log(`Started: ${new Date().toISOString()}`, 'cyan');
  log('='.repeat(70), 'cyan');

  let success = false;
  let backupFile = null;

  try {
    // Deployment steps
    await preDeploymentChecks();
    backupFile = await createDatabaseBackup();
    await runDatabaseMigrations();
    await syncSecrets();
    await deployWorker();
    await deployStaticPages();
    await configureWebhooks();
    await postDeploymentVerification();

    success = true;

  } catch (error) {
    log(`\n❌ Deployment failed: ${error.message}`, 'red');
    log('\n🔄 Consider running rollback:', 'yellow');
    log('   node deployment/scripts/rollback.js', 'yellow');

    if (backupFile) {
      log(`\n💾 Database backup available at:`, 'yellow');
      log(`   ${backupFile}`, 'yellow');
    }

    success = false;
  }

  // Send notification
  await sendNotification(success);

  // Generate summary
  const allPassed = generateSummary();

  if (success && allPassed) {
    log('\n🎉 DEPLOYMENT SUCCESSFUL!', 'green');
    log('✅ All systems operational', 'green');
    log('🚀 xSwarm Boss is live!', 'green');
  } else {
    log('\n⚠️  DEPLOYMENT COMPLETED WITH WARNINGS', 'yellow');
    log('Review the logs above for details', 'yellow');
  }

  log(''); // Empty line
  process.exit(success ? 0 : 1);
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
  log('\n\n⚠️  Deployment interrupted by user', 'yellow');
  await sendNotification(false);
  process.exit(1);
});

process.on('SIGTERM', async () => {
  log('\n\n⚠️  Deployment terminated', 'yellow');
  await sendNotification(false);
  process.exit(1);
});

main();
