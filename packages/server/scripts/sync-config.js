#!/usr/bin/env node
/**
 * Sync Config to Cloudflare Workers
 *
 * Reads config.toml and generates a users.json file that gets deployed
 * This allows the worker to access user configuration without file I/O
 */

import { readFileSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { parse as parseToml } from 'smol-toml';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const projectRoot = join(__dirname, '../../..');

// Load config.toml
const configPath = join(projectRoot, 'config.toml');
const configContent = readFileSync(configPath, 'utf-8');
const config = parseToml(configContent);

// Extract users configuration
const users = config.users || [];

// Create users lookup by phone number
const usersConfig = {
  users: users.map(user => ({
    username: user.username,
    name: user.name,
    phone: user.phone,
    email: user.email,
    boss_phone: user.boss_phone,
    boss_email: user.boss_email,
    role: user.role,
    persona: user.persona || 'boss',
  })),
  // Create lookup map for fast authentication
  phoneToUser: Object.fromEntries(
    users.map(user => [user.phone, {
      username: user.username,
      name: user.name,
      phone: user.phone,
      email: user.email,
      boss_phone: user.boss_phone,
      boss_email: user.boss_email,
      role: user.role,
      persona: user.persona || 'boss',
    }])
  ),
};

// Write to src/config/users.json
const outputPath = join(__dirname, '../src/config/users.json');
writeFileSync(outputPath, JSON.stringify(usersConfig, null, 2));

console.log(`✓ Synced ${users.length} user(s) to ${outputPath}`);
users.forEach(user => {
  console.log(`  - ${user.name} (${user.phone})`);
});
