#!/usr/bin/env node

/**
 * Generate All Images
 * Batch generates all pending images using the asset manager API
 */

const API_BASE = 'http://localhost:3000';

async function main() {
  console.log(`
╔══════════════════════════════════════════════════════════════╗
║           OMARCHY DEFENDER - BATCH IMAGE GENERATION          ║
╚══════════════════════════════════════════════════════════════╝
`);

  // Fetch current image status
  console.log('Fetching image manifest...');
  const res = await fetch(`${API_BASE}/api/images`);
  const data = await res.json();

  console.log(`\nStats: ${data.stats.generated}/${data.stats.total} generated (${data.stats.pending} pending)\n`);

  // Collect all pending images
  const pending = [];
  for (const [category, items] of Object.entries(data.categories)) {
    for (const item of items) {
      if (!item.generated) {
        pending.push({ ...item, category });
      }
    }
  }

  if (pending.length === 0) {
    console.log('✅ All images already generated!');
    return;
  }

  console.log(`Found ${pending.length} pending images:\n`);
  for (const img of pending) {
    console.log(`  • ${img.category}/${img.filename}`);
  }

  console.log('\n' + '═'.repeat(64) + '\n');

  // Generate each image
  let success = 0;
  let failed = 0;

  for (let i = 0; i < pending.length; i++) {
    const img = pending[i];
    const progress = `[${i + 1}/${pending.length}]`;

    process.stdout.write(`${progress} Generating ${img.category}/${img.filename}...`);

    try {
      const genRes = await fetch(`${API_BASE}/api/openai/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: img.prompt,
          style: img.style,
          size: img.size,
          filename: img.filename,
          category: img.category
        })
      });

      const result = await genRes.json();

      if (result.error) {
        console.log(` ❌ ${result.error}`);
        failed++;
      } else {
        console.log(` ✅`);
        success++;
      }
    } catch (e) {
      console.log(` ❌ ${e.message}`);
      failed++;
    }

    // Rate limiting - wait between requests
    if (i < pending.length - 1) {
      await new Promise(r => setTimeout(r, 1000));
    }
  }

  console.log(`
${'═'.repeat(64)}

Generation Complete!

  ✅ Succeeded: ${success}
  ❌ Failed:    ${failed}
  📊 Total:     ${pending.length}

${'═'.repeat(64)}
`);
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
