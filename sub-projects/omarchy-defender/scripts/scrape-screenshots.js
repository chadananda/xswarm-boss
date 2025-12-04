#!/usr/bin/env node

/**
 * Screenshot Scraper for Omarchy Documentation
 * Downloads application screenshots from learn.omacom.io
 * Renames files with xswarm prefix for SEO
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname, basename, extname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, '..');
const ASSETS_DIR = resolve(PROJECT_ROOT, 'assets');
const SCREENSHOTS_DIR = resolve(ASSETS_DIR, 'images/screenshots');

// Omarchy documentation URLs to scrape
const DOCS_URLS = [
  'https://learn.omacom.io/',
  'https://learn.omacom.io/getting-started/',
  'https://learn.omacom.io/applications/',
  'https://learn.omacom.io/keybindings/',
  'https://learn.omacom.io/customization/',
  'https://learn.omacom.io/tips-tricks/'
];

// Known applications to look for
const KNOWN_APPS = [
  'terminal', 'kitty', 'alacritty',
  'browser', 'firefox', 'chromium', 'brave',
  'file-manager', 'nautilus', 'thunar', 'nemo',
  'email', 'hey', 'thunderbird',
  'calendar',
  'ai-chat', 'chatgpt',
  'twitter', 'x',
  'music', 'spotify',
  'obsidian', 'notes',
  'neovim', 'nvim', 'editor',
  'btop', 'activity-monitor', 'system-monitor',
  'docker', 'lazydocker',
  'password', '1password', 'bitwarden',
  'signal', 'whatsapp', 'messages',
  'hyprland', 'waybar', 'rofi', 'wofi'
];

// Results tracking
const results = {
  found: [],
  downloaded: [],
  failed: [],
  missingApps: []
};

/**
 * Fetch HTML content from URL
 */
async function fetchHTML(url) {
  try {
    console.log(`  Fetching: ${url}`);
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; OmarchyDefender/1.0; Screenshot Scraper)'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.text();
  } catch (err) {
    console.error(`  Failed to fetch ${url}: ${err.message}`);
    return null;
  }
}

/**
 * Extract image URLs from HTML
 */
function extractImageURLs(html, baseUrl) {
  const images = [];

  // Match img tags with src attribute
  const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
  let match;

  while ((match = imgRegex.exec(html)) !== null) {
    let src = match[1];

    // Skip data URLs and icons
    if (src.startsWith('data:')) continue;
    if (src.includes('favicon')) continue;
    if (src.includes('icon') && !src.includes('screenshot')) continue;

    // Convert relative URLs to absolute
    if (!src.startsWith('http')) {
      if (src.startsWith('/')) {
        const urlObj = new URL(baseUrl);
        src = `${urlObj.protocol}//${urlObj.host}${src}`;
      } else {
        src = new URL(src, baseUrl).href;
      }
    }

    // Check if it's an image file
    if (/\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i.test(src)) {
      // Get alt text for context
      const altMatch = match[0].match(/alt=["']([^"']+)["']/i);
      const alt = altMatch ? altMatch[1] : '';

      images.push({ src, alt, source: baseUrl });
    }
  }

  // Also look for background images in style attributes
  const bgRegex = /url\(["']?([^"')]+)["']?\)/gi;
  while ((match = bgRegex.exec(html)) !== null) {
    let src = match[1];
    if (!src.startsWith('http') && !src.startsWith('data:')) {
      if (src.startsWith('/')) {
        const urlObj = new URL(baseUrl);
        src = `${urlObj.protocol}//${urlObj.host}${src}`;
      } else {
        src = new URL(src, baseUrl).href;
      }
    }

    if (/\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i.test(src)) {
      images.push({ src, alt: '', source: baseUrl });
    }
  }

  return images;
}

/**
 * Generate SEO-friendly filename
 */
function generateFilename(imageInfo) {
  let name = 'xswarm-omarchy';

  // Try to determine what the image shows
  const srcLower = imageInfo.src.toLowerCase();
  const altLower = (imageInfo.alt || '').toLowerCase();

  for (const app of KNOWN_APPS) {
    if (srcLower.includes(app) || altLower.includes(app)) {
      name += `-${app}`;
      break;
    }
  }

  // Add original filename hint
  const originalName = basename(imageInfo.src).replace(/\?.*$/, '');
  const ext = extname(originalName) || '.png';
  const baseName = basename(originalName, ext).replace(/[^a-z0-9-]/gi, '-');

  if (baseName && !name.includes(baseName)) {
    name += `-${baseName}`;
  }

  // Clean up
  name = name.replace(/--+/g, '-').replace(/-$/, '');

  return name + ext;
}

/**
 * Download image to screenshots directory
 */
async function downloadImage(imageInfo) {
  const filename = generateFilename(imageInfo);
  const filepath = resolve(SCREENSHOTS_DIR, filename);

  // Skip if already exists
  if (existsSync(filepath)) {
    console.log(`  Skipped (exists): ${filename}`);
    return { success: true, skipped: true, filename };
  }

  try {
    console.log(`  Downloading: ${imageInfo.src}`);
    const response = await fetch(imageInfo.src, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; OmarchyDefender/1.0; Screenshot Scraper)'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const buffer = await response.arrayBuffer();
    writeFileSync(filepath, Buffer.from(buffer));

    console.log(`  Saved: ${filename} (${formatSize(buffer.byteLength)})`);
    return { success: true, filename, size: buffer.byteLength };
  } catch (err) {
    console.error(`  Failed to download: ${err.message}`);
    return { success: false, error: err.message };
  }
}

/**
 * Scrape a single documentation page
 */
async function scrapePage(url) {
  const html = await fetchHTML(url);
  if (!html) return [];

  const images = extractImageURLs(html, url);
  console.log(`  Found ${images.length} images`);

  return images;
}

/**
 * Check which known apps are missing screenshots
 */
function checkMissingApps() {
  const downloadedNames = results.downloaded.map(f => f.toLowerCase());
  const missing = [];

  for (const app of KNOWN_APPS) {
    const found = downloadedNames.some(name => name.includes(app));
    if (!found) {
      missing.push(app);
    }
  }

  return missing;
}

/**
 * Format file size
 */
function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Main scraping function
 */
async function main() {
  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║           OMARCHY SCREENSHOT SCRAPER                        ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  // Ensure screenshots directory exists
  if (!existsSync(SCREENSHOTS_DIR)) {
    mkdirSync(SCREENSHOTS_DIR, { recursive: true });
    console.log(`Created directory: ${SCREENSHOTS_DIR}\n`);
  }

  // Collect all images from documentation
  console.log('Phase 1: Scanning documentation pages...\n');

  const allImages = [];
  const seenUrls = new Set();

  for (const url of DOCS_URLS) {
    console.log(`\nScanning: ${url}`);
    const images = await scrapePage(url);

    for (const img of images) {
      if (!seenUrls.has(img.src)) {
        seenUrls.add(img.src);
        allImages.push(img);
        results.found.push(img);
      }
    }
  }

  console.log(`\n\nPhase 2: Downloading ${allImages.length} unique images...\n`);

  // Download all images
  for (const img of allImages) {
    const result = await downloadImage(img);
    if (result.success && !result.skipped) {
      results.downloaded.push(result.filename);
    } else if (!result.success) {
      results.failed.push({ url: img.src, error: result.error });
    }
  }

  // Check for missing apps
  results.missingApps = checkMissingApps();

  // Generate report
  console.log('\n\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║                     SCRAPE RESULTS                          ║');
  console.log('╠══════════════════════════════════════════════════════════════╣');
  console.log(`║  Images Found:     ${results.found.length.toString().padEnd(40)}║`);
  console.log(`║  Downloaded:       ${results.downloaded.length.toString().padEnd(40)}║`);
  console.log(`║  Failed:           ${results.failed.length.toString().padEnd(40)}║`);
  console.log(`║  Missing Apps:     ${results.missingApps.length.toString().padEnd(40)}║`);
  console.log('╚══════════════════════════════════════════════════════════════╝');

  if (results.missingApps.length > 0) {
    console.log('\n⚠️  Missing screenshots for these applications:');
    results.missingApps.forEach(app => console.log(`   • ${app}`));
    console.log('\n   Consider adding manual screenshots for these apps.');
  }

  if (results.failed.length > 0) {
    console.log('\n❌ Failed downloads:');
    results.failed.forEach(f => console.log(`   • ${f.url}: ${f.error}`));
  }

  // Save results log
  const logPath = resolve(SCREENSHOTS_DIR, 'scrape-log.json');
  writeFileSync(logPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    sources: DOCS_URLS,
    results
  }, null, 2));
  console.log(`\n📄 Results saved to: ${logPath}`);

  console.log('\n✅ Scraping complete!\n');
}

// Run
main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
