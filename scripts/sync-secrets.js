#!/usr/bin/env node
/**
 * Sync Secrets to Cloudflare Workers
 *
 * This script reads secrets from .env file and uploads them to Cloudflare Workers
 * using wrangler secret put. It never logs or displays secret values.
 *
 * Usage:
 *   node scripts/sync-secrets.js
 *   pnpm setup:secrets
 */

import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '..');

// Secrets mapping: .env variable -> Cloudflare Workers secret name
// Note: Some secrets have TEST/LIVE variants - we try both
// Note: TWILIO_ACCOUNT_SID is technically not a secret, but may be in .env for backwards compatibility
const SECRET_MAPPINGS = {
	// Twilio (tries TEST first, then LIVE)
	'TWILIO_ACCOUNT_SID': ['TWILIO_ACCOUNT_SID', 'TWILIO_ACCOUNT_ID'],  // Not a secret, but may be in .env
	'TWILIO_AUTH_TOKEN': ['TWILIO_AUTH_TOKEN_TEST', 'TWILIO_AUTH_TOKEN_LIVE', 'TWILIO_AUTH_TOKEN'],

	// Stripe (tries TEST first, then LIVE)
	'STRIPE_SECRET_KEY': ['STRIPE_SECRET_KEY_TEST', 'STRIPE_SECRET_KEY_LIVE', 'STRIPE_SECRET_KEY'],
	'STRIPE_WEBHOOK_SECRET': ['STRIPE_WEBHOOK_SECRET_TEST', 'STRIPE_WEBHOOK_SECRET_LIVE', 'STRIPE_WEBHOOK_SECRET_LOCAL', 'STRIPE_WEBHOOK_SECRET'],

	// Turso Database
	'TURSO_DATABASE_URL': ['TURSO_DATABASE_URL'],
	'TURSO_AUTH_TOKEN': ['TURSO_AUTH_TOKEN'],

	// Git LFS
	'LFS_AUTH_TOKEN_READ': ['LFS_AUTH_TOKEN_READ'],
	'LFS_AUTH_TOKEN_WRITE': ['LFS_AUTH_TOKEN_WRITE'],
};

/**
 * Parse .env file into key-value pairs
 * @param {string} envPath - Path to .env file
 * @returns {Object} Parsed environment variables
 */
function parseEnvFile(envPath) {
	try {
		const content = readFileSync(envPath, 'utf-8');
		const env = {};

		for (const line of content.split('\n')) {
			// Skip empty lines and comments
			const trimmed = line.trim();
			if (!trimmed || trimmed.startsWith('#')) continue;

			// Parse KEY=VALUE
			const match = trimmed.match(/^([^=]+)=(.*)$/);
			if (match) {
				const key = match[1].trim();
				let value = match[2].trim();

				// Remove quotes if present
				if ((value.startsWith('"') && value.endsWith('"')) ||
				    (value.startsWith("'") && value.endsWith("'"))) {
					value = value.slice(1, -1);
				}

				env[key] = value;
			}
		}

		return env;
	} catch (error) {
		console.error(`✗ Failed to read .env file: ${error.message}`);
		process.exit(1);
	}
}

/**
 * Set a Cloudflare Workers secret using wrangler
 * @param {string} secretName - Name of the secret
 * @param {string} secretValue - Value of the secret
 * @param {string} serverPath - Path to server package
 */
function setSecret(secretName, secretValue, serverPath) {
	try {
		// Use wrangler secret put (pipes value via stdin to avoid showing in process list)
		const command = `echo "${secretValue}" | pnpm wrangler secret put ${secretName}`;
		execSync(command, {
			cwd: serverPath,
			stdio: ['pipe', 'pipe', 'pipe']  // Suppress all output to avoid leaking secrets
		});
		console.log(`✓ Set secret: ${secretName}`);
	} catch (error) {
		// Never log the error message as it may contain secret values
		console.error(`✗ Failed to set secret ${secretName}`);
		throw new Error('Secret sync failed');
	}
}

/**
 * Main function
 */
async function main() {
	console.log('Syncing secrets to Cloudflare Workers...\n');

	// Read .env file
	const envPath = join(projectRoot, '.env');
	console.log(`Reading secrets from: ${envPath}`);
	const env = parseEnvFile(envPath);
	console.log(`Found ${Object.keys(env).length} variables in .env\n`);

	// Sync each secret
	const serverPath = join(projectRoot, 'packages', 'server');
	let successCount = 0;
	let skipCount = 0;
	const errors = [];

	for (const [secretName, possibleEnvKeys] of Object.entries(SECRET_MAPPINGS)) {
		// Try each possible env key (TEST, LIVE, or plain)
		let secretValue = null;
		let usedKey = null;

		for (const envKey of possibleEnvKeys) {
			if (env[envKey]) {
				secretValue = env[envKey];
				usedKey = envKey;
				break;
			}
		}

		if (!secretValue) {
			console.log(`⚠ Skipping ${secretName}: not found in .env (tried: ${possibleEnvKeys.join(', ')})`);
			skipCount++;
			continue;
		}

		console.log(`  Using ${usedKey} for ${secretName}`);
		try {
			setSecret(secretName, secretValue, serverPath);
			successCount++;
		} catch (error) {
			errors.push({ secretName });  // Don't store error message (may contain secrets)
		}
	}

	// Summary
	console.log('\n' + '='.repeat(60));
	console.log('SYNC SUMMARY');
	console.log('='.repeat(60));
	console.log(`✓ Synced: ${successCount}`);
	console.log(`⚠ Skipped: ${skipCount}`);
	console.log(`✗ Failed: ${errors.length}`);

	if (errors.length > 0) {
		console.log('\nErrors:');
		for (const { secretName } of errors) {
			console.log(`  - ${secretName}: Failed to sync`);
		}
		process.exit(1);
	}

	console.log('\n✓ All secrets synced successfully!');
	console.log('\nYou can now test the Boss call with:');
	console.log('  curl -X POST https://xswarm-webhooks.chadananda.workers.dev/api/boss/call \\');
	console.log('    -H "Content-Type: application/json" \\');
	console.log('    -d \'{"phone": "+19167656913", "user": "Chad"}\'');
}

main().catch(error => {
	console.error('\n✗ Fatal error:', error.message);
	process.exit(1);
});
