#!/usr/bin/env node

/**
 * Install Stripe CLI Binary
 *
 * Downloads the Stripe CLI binary for the current platform and stores it
 * in scripts/bin for use in development.
 *
 * This runs as a postinstall script to ensure the CLI is available without
 * requiring external installation (no brew/apt/scoop).
 */

import { existsSync, mkdirSync, chmodSync, writeFileSync, createWriteStream } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';
import https from 'https';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const binDir = join(__dirname, 'bin');
const stripePath = join(binDir, 'stripe');

// GitHub API for latest release
const GITHUB_API_URL = 'https://api.github.com/repos/stripe/stripe-cli/releases/latest';

/**
 * Detect platform and architecture
 */
function getPlatformInfo() {
  const platform = process.platform;
  const arch = process.arch;

  // Map to Stripe CLI naming
  let osName, archName;

  switch (platform) {
    case 'darwin':
      osName = 'mac-os';
      break;
    case 'linux':
      osName = 'linux';
      break;
    case 'win32':
      osName = 'windows';
      break;
    default:
      throw new Error(`Unsupported platform: ${platform}`);
  }

  switch (arch) {
    case 'x64':
      archName = 'x86_64';
      break;
    case 'arm64':
      archName = 'arm64';
      break;
    default:
      throw new Error(`Unsupported architecture: ${arch}`);
  }

  return { osName, archName, platform };
}

/**
 * Fetch latest version from GitHub API
 */
async function getLatestVersion() {
  return new Promise((resolve, reject) => {
    const options = {
      headers: {
        'User-Agent': 'xswarm-stripe-cli-installer'
      }
    };

    https.get(GITHUB_API_URL, options, (response) => {
      if (response.statusCode !== 200) {
        reject(new Error(`GitHub API returned ${response.statusCode}`));
        return;
      }

      let data = '';
      response.on('data', chunk => data += chunk);
      response.on('end', () => {
        try {
          const release = JSON.parse(data);
          resolve(release.tag_name); // e.g., "v1.31.1"
        } catch (error) {
          reject(new Error('Failed to parse GitHub API response'));
        }
      });
      response.on('error', reject);
    }).on('error', reject);
  });
}

/**
 * Download file from URL
 */
function download(url) {
  return new Promise((resolve, reject) => {
    console.log(`  Downloading from: ${url}`);

    https.get(url, (response) => {
      // Handle redirects
      if (response.statusCode === 302 || response.statusCode === 301) {
        return download(response.headers.location).then(resolve).catch(reject);
      }

      if (response.statusCode !== 200) {
        reject(new Error(`HTTP ${response.statusCode}: ${response.statusMessage}`));
        return;
      }

      const chunks = [];
      response.on('data', chunk => chunks.push(chunk));
      response.on('end', () => resolve(Buffer.concat(chunks)));
      response.on('error', reject);
    }).on('error', reject);
  });
}

/**
 * Extract tar.gz archive using system tar command
 */
async function extractTarGz(buffer, targetDir) {
  // Write buffer to temp file
  const tempFile = join(targetDir, 'stripe-cli.tar.gz');
  writeFileSync(tempFile, buffer);

  try {
    // Extract using system tar
    execSync(`tar -xzf "${tempFile}" -C "${targetDir}"`, {
      stdio: 'pipe'
    });

    // Clean up temp file
    execSync(`rm "${tempFile}"`);
  } catch (error) {
    // Clean up on error
    if (existsSync(tempFile)) {
      execSync(`rm "${tempFile}"`);
    }
    throw error;
  }
}

/**
 * Main installation
 */
async function install() {
  console.log('📦 Installing Stripe CLI\n');

  // Check if already installed
  if (existsSync(stripePath)) {
    console.log('✓ Stripe CLI already installed');
    console.log(`  Location: ${stripePath}\n`);
    return;
  }

  try {
    // Detect platform
    const { osName, archName, platform } = getPlatformInfo();
    console.log(`  Platform: ${osName}`);
    console.log(`  Architecture: ${archName}\n`);

    // Fetch latest version from GitHub
    console.log('  Fetching latest version...');
    const version = await getLatestVersion();
    console.log(`  Latest version: ${version}\n`);

    // Construct download URL
    const ext = platform === 'win32' ? 'zip' : 'tar.gz';
    const filename = `stripe_${version.substring(1)}_${osName}_${archName}.${ext}`;
    const downloadUrl = `https://github.com/stripe/stripe-cli/releases/download/${version}/${filename}`;

    // Create bin directory
    if (!existsSync(binDir)) {
      mkdirSync(binDir, { recursive: true });
    }

    // Download
    console.log('  Downloading Stripe CLI...');
    const buffer = await download(downloadUrl);
    console.log(`  ✓ Downloaded ${(buffer.length / 1024 / 1024).toFixed(2)} MB\n`);

    // Extract
    console.log('  Extracting...');
    if (platform === 'win32') {
      // TODO: Handle zip extraction for Windows
      throw new Error('Windows support not yet implemented. Please download Stripe CLI manually.');
    } else {
      // Extract tar.gz to bin directory
      await extractTarGz(buffer, binDir);

      // Verify stripe binary exists
      if (!existsSync(stripePath)) {
        throw new Error('Stripe binary not found after extraction');
      }
    }

    // Make executable (Unix only)
    if (platform !== 'win32') {
      chmodSync(stripePath, 0o755);
    }

    console.log('  ✓ Extracted\n');
    console.log('✅ Stripe CLI installed successfully!');
    console.log(`   Location: ${stripePath}`);
    console.log(`   Version: ${version}\n`);

  } catch (error) {
    console.error('❌ Installation failed:', error.message);
    console.error('\n📝 Manual installation:');
    console.error('   macOS:   brew install stripe/stripe-cli/stripe');
    console.error('   Linux:   Download from https://github.com/stripe/stripe-cli/releases');
    console.error('   Windows: scoop install stripe\n');
    process.exit(1);
  }
}

// Run installation
install().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
