/**
 * Tier Integration Tests
 *
 * Comprehensive tier-based feature access and limit enforcement testing.
 * Tests cross-feature restrictions, upgrade CTAs, and data isolation.
 */

import './config.js'; // Load environment variables
import { assert } from './utils/assert.js';
import {
  createTestDb,
  setupTestDatabase,
  clearTestData,
  createTestUser,
  createTestTeam,
  countRecords,
} from './utils/database.js';
import { TIER_FEATURES, hasFeature, checkLimit, generateUpgradeMessage } from '../packages/server/src/lib/features.js';

/**
 * Create test personas for a user
 */
async function createTestPersonas(db, userId, count) {
  const personas = [];
  for (let i = 0; i < count; i++) {
    const id = `persona_${userId}_${i}_${Date.now()}`;
    await db.execute({
      sql: `
        INSERT INTO personas (id, user_id, name, description, system_prompt, voice_id, active)
        VALUES (?, ?, ?, ?, ?, ?, TRUE)
      `,
      args: [
        id,
        userId,
        `Persona ${i + 1}`,
        `Test persona ${i + 1}`,
        `You are test persona ${i + 1}`,
        'default',
      ],
    });
    personas.push(id);
  }
  return personas;
}

/**
 * Simulate usage tracking
 */
async function trackUsage(db, userId, usageType, amount) {
  const now = new Date().toISOString();
  const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();

  await db.execute({
    sql: `
      INSERT INTO usage_tracking (user_id, usage_type, amount, period_start, created_at)
      VALUES (?, ?, ?, ?, ?)
      ON CONFLICT (user_id, usage_type, period_start) DO UPDATE SET
        amount = amount + excluded.amount
    `,
    args: [userId, usageType, amount, monthStart, now],
  });
}

/**
 * Get user usage for a specific type
 */
async function getUsage(db, userId, usageType) {
  const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();

  const result = await db.execute({
    sql: `
      SELECT amount FROM usage_tracking
      WHERE user_id = ? AND usage_type = ? AND period_start = ?
    `,
    args: [userId, usageType, monthStart],
  });

  return result.rows[0]?.amount || 0;
}

/**
 * Register test suite
 */
export default function (runner) {
  runner.describe('Tier Integration', async ctx => {
    let db;

    ctx.beforeAll(async () => {
      db = createTestDb();
      await setupTestDatabase(db);
    });

    ctx.afterEach(async () => {
      await clearTestData(db);
    });

    ctx.afterAll(async () => {
      db.close();
    });

    // Test: Free tier persona limit enforcement
    await ctx.test('should enforce free tier persona limit (3 max)', async () => {
      const user = await createTestUser(db, { subscription_tier: 'free' });

      // Create 3 personas (should succeed)
      await createTestPersonas(db, user.id, 3);
      const countAfter3 = await countRecords(db, 'personas', `user_id = '${user.id}'`);
      assert.strictEqual(countAfter3, 3, 'Should allow 3 personas on free tier');

      // Try to create 4th persona (should be blocked by app logic)
      const personaLimit = TIER_FEATURES.free.personas.limit;
      assert.strictEqual(personaLimit, 3, 'Free tier should have 3 persona limit');

      // Verify limit check works
      const limitCheck = checkLimit('free', 'personas', 3);
      assert.strictEqual(limitCheck.allowed, false, 'Should not allow 4th persona');
      assert.strictEqual(limitCheck.remaining, 0, 'Should have 0 remaining');
    });

    // Test: Personal tier unlimited personas
    await ctx.test('should allow unlimited personas on Personal+ tiers', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });

      // Create many personas
      await createTestPersonas(db, user.id, 10);
      const count = await countRecords(db, 'personas', `user_id = '${user.id}'`);
      assert.strictEqual(count, 10, 'Should allow 10+ personas on personal tier');

      // Verify no limit
      const personaLimit = TIER_FEATURES.personal.personas.limit;
      assert.strictEqual(personaLimit, null, 'Personal tier should have unlimited personas');
    });

    // Test: Free tier cannot access voice features
    await ctx.test('should block voice access for free tier users', async () => {
      const user = await createTestUser(db, { subscription_tier: 'free' });

      // Check voice feature access
      const hasVoice = hasFeature('free', 'voice_minutes');
      assert.strictEqual(hasVoice, false, 'Free tier should not have voice access');

      // Verify limit is 0
      const voiceLimit = TIER_FEATURES.free.voice_minutes.limit;
      assert.strictEqual(voiceLimit, 0, 'Free tier should have 0 voice minutes');
    });

    // Test: Personal tier voice limits
    await ctx.test('should enforce Personal tier voice minute limits', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });

      // Track usage up to limit
      await trackUsage(db, user.id, 'voice_minutes', 100);
      const usage = await getUsage(db, user.id, 'voice_minutes');
      assert.strictEqual(usage, 100, 'Should track 100 voice minutes');

      // Check limit
      const limitCheck = checkLimit('personal', 'voice_minutes', 100);
      assert.strictEqual(limitCheck.limit, 100, 'Personal tier should have 100 minute limit');
      assert.strictEqual(limitCheck.remaining, 0, 'Should have 0 minutes remaining');
      assert.strictEqual(limitCheck.allowed, true, 'Should allow overage');
      assert.strictEqual(limitCheck.overage_allowed, true, 'Overage should be allowed');
      assert.strictEqual(limitCheck.overage_rate, 0.013, 'Should have overage rate');
    });

    // Test: SMS limits enforcement
    await ctx.test('should enforce SMS message limits by tier', async () => {
      const freeUser = await createTestUser(db, { subscription_tier: 'free' });
      const personalUser = await createTestUser(db, { subscription_tier: 'personal' });

      // Free tier: 0 SMS
      const freeCheck = checkLimit('free', 'sms_messages', 0);
      assert.strictEqual(freeCheck.limit, 0, 'Free tier should have 0 SMS');
      assert.strictEqual(freeCheck.allowed, false, 'Free tier should not allow SMS');

      // Personal tier: 100 SMS
      await trackUsage(db, personalUser.id, 'sms_messages', 50);
      const personalCheck = checkLimit('personal', 'sms_messages', 50);
      assert.strictEqual(personalCheck.limit, 100, 'Personal tier should have 100 SMS');
      assert.strictEqual(personalCheck.remaining, 50, 'Should have 50 SMS remaining');
      assert.strictEqual(personalCheck.allowed, true, 'Should allow more SMS');
    });

    // Test: Calendar access restrictions
    await ctx.test('should enforce calendar access restrictions by tier', async () => {
      // Free tier: read-only
      const freeCalendar = TIER_FEATURES.free.calendar_access;
      assert.strictEqual(freeCalendar, 'read', 'Free tier should have read-only calendar');

      // Personal tier: read/write
      const personalCalendar = TIER_FEATURES.personal.calendar_access;
      assert.strictEqual(personalCalendar, 'write', 'Personal tier should have write calendar access');
    });

    // Test: Team collaboration feature gating
    await ctx.test('should block team features for Free and Personal tiers', async () => {
      const freeUser = await createTestUser(db, { subscription_tier: 'free' });
      const personalUser = await createTestUser(db, { subscription_tier: 'personal' });

      // Check team collaboration access
      const freeHasTeams = hasFeature('free', 'team_collaboration');
      const personalHasTeams = hasFeature('personal', 'team_collaboration');
      const professionalHasTeams = hasFeature('professional', 'team_collaboration');

      assert.strictEqual(freeHasTeams, false, 'Free tier should not have teams');
      assert.strictEqual(personalHasTeams, false, 'Personal tier should not have teams');
      assert.strictEqual(professionalHasTeams, true, 'Professional tier should have teams');
    });

    // Test: Professional tier team limits
    await ctx.test('should enforce Professional tier team member limits', async () => {
      const user = await createTestUser(db, { subscription_tier: 'professional' });
      const team = await createTestTeam(db, user.id, { subscription_tier: 'professional' });

      // Check team member limit
      const teamConfig = TIER_FEATURES.professional.team_collaboration;
      assert.strictEqual(teamConfig.limit, 10, 'Professional tier should allow 10 team members');

      // Verify team was created
      const teamCount = await countRecords(db, 'teams', `owner_id = '${user.id}'`);
      assert.strictEqual(teamCount, 1, 'Should create team for Professional tier');
    });

    // Test: Upgrade CTA generation
    await ctx.test('should generate correct upgrade CTAs for blocked features', async () => {
      // Free user trying to access voice
      const voiceUpgrade = generateUpgradeMessage('voice_minutes', 'free');
      assert.ok(voiceUpgrade.message.includes('AI Secretary'), 'Should suggest Personal tier for voice');
      assert.strictEqual(voiceUpgrade.cta.tier, 'personal', 'Should upgrade to personal tier');
      assert.strictEqual(voiceUpgrade.cta.price, '$29/month', 'Should show correct price');

      // Personal user trying to access teams
      const teamUpgrade = generateUpgradeMessage('team_collaboration', 'personal');
      assert.ok(teamUpgrade.message.includes('AI Project Manager'), 'Should suggest Professional tier for teams');
      assert.strictEqual(teamUpgrade.cta.tier, 'professional', 'Should upgrade to professional tier');
    });

    // Test: Cross-feature tier restrictions
    await ctx.test('should enforce multiple feature restrictions together', async () => {
      const user = await createTestUser(db, { subscription_tier: 'free' });

      // Free tier should be blocked from multiple features
      const restrictions = {
        voice: hasFeature('free', 'voice_minutes'),
        sms: hasFeature('free', 'sms_messages'),
        teams: hasFeature('free', 'team_collaboration'),
        buzz: hasFeature('free', 'buzz_workspace'),
        document_gen: hasFeature('free', 'document_generation'),
      };

      assert.strictEqual(restrictions.voice, false, 'Free tier blocked from voice');
      assert.strictEqual(restrictions.sms, false, 'Free tier blocked from SMS');
      assert.strictEqual(restrictions.teams, false, 'Free tier blocked from teams');
      assert.strictEqual(restrictions.buzz, false, 'Free tier blocked from Buzz');
      assert.strictEqual(restrictions.document_gen, false, 'Free tier blocked from doc generation');
    });

    // Test: Data isolation by tier
    await ctx.test('should isolate tier-specific data correctly', async () => {
      const freeUser = await createTestUser(db, { subscription_tier: 'free' });
      const proUser = await createTestUser(db, { subscription_tier: 'professional' });

      // Create personas for both users
      await createTestPersonas(db, freeUser.id, 3);
      await createTestPersonas(db, proUser.id, 10);

      // Verify data isolation
      const freePersonas = await countRecords(db, 'personas', `user_id = '${freeUser.id}'`);
      const proPersonas = await countRecords(db, 'personas', `user_id = '${proUser.id}'`);

      assert.strictEqual(freePersonas, 3, 'Free user should have 3 personas');
      assert.strictEqual(proPersonas, 10, 'Pro user should have 10 personas');
    });

    // Test: Memory retention limits
    await ctx.test('should enforce memory retention limits by tier', async () => {
      const freeRetention = TIER_FEATURES.free.memory_retention_days;
      const personalRetention = TIER_FEATURES.personal.memory_retention_days;
      const enterpriseRetention = TIER_FEATURES.enterprise.memory_retention_days;

      assert.strictEqual(freeRetention, 30, 'Free tier should have 30-day retention');
      assert.strictEqual(personalRetention, 365, 'Personal tier should have 365-day retention');
      assert.strictEqual(enterpriseRetention, null, 'Enterprise should have unlimited retention');
    });

    // Test: Storage limits
    await ctx.test('should enforce storage limits by tier', async () => {
      const freeStorage = TIER_FEATURES.free.storage_gb;
      const personalStorage = TIER_FEATURES.personal.storage_gb;
      const enterpriseStorage = TIER_FEATURES.enterprise.storage_gb;

      assert.strictEqual(freeStorage, 1, 'Free tier should have 1GB storage');
      assert.strictEqual(personalStorage, 10, 'Personal tier should have 10GB storage');
      assert.strictEqual(enterpriseStorage, null, 'Enterprise should have unlimited storage');
    });

    // Test: Project limits
    await ctx.test('should enforce project limits by tier', async () => {
      const freeProjects = TIER_FEATURES.free.max_projects;
      const personalProjects = TIER_FEATURES.personal.max_projects;
      const proProjects = TIER_FEATURES.professional.max_projects;

      assert.strictEqual(freeProjects, 3, 'Free tier should have 3 projects');
      assert.strictEqual(personalProjects, 25, 'Personal tier should have 25 projects');
      assert.strictEqual(proProjects, 100, 'Professional tier should have 100 projects');
    });

    // Test: API access by tier
    await ctx.test('should restrict API access by tier', async () => {
      const freeApi = TIER_FEATURES.free.api_access;
      const personalApi = TIER_FEATURES.personal.api_access;
      const proApi = TIER_FEATURES.professional.api_access;
      const enterpriseApi = TIER_FEATURES.enterprise.api_access;

      assert.strictEqual(freeApi, false, 'Free tier should not have API access');
      assert.strictEqual(personalApi, 'basic', 'Personal tier should have basic API access');
      assert.strictEqual(proApi, 'full', 'Professional tier should have full API access');
      assert.strictEqual(enterpriseApi, 'enterprise', 'Enterprise should have enterprise API access');
    });

    // Test: AI model access by tier
    await ctx.test('should restrict AI models by tier', async () => {
      const freeModels = TIER_FEATURES.free.ai_models;
      const personalModels = TIER_FEATURES.personal.ai_models;
      const enterpriseModels = TIER_FEATURES.enterprise.ai_models;

      assert.ok(Array.isArray(freeModels), 'Free tier should have model array');
      assert.strictEqual(freeModels.length, 1, 'Free tier should have 1 model');
      assert.ok(freeModels.includes('gpt-3.5-turbo'), 'Free tier should have GPT-3.5');

      assert.ok(personalModels.length > 1, 'Personal tier should have multiple models');
      assert.ok(personalModels.includes('gpt-4'), 'Personal tier should have GPT-4');

      assert.ok(enterpriseModels.includes('custom'), 'Enterprise should support custom models');
    });

    // Test: Wake word customization by tier
    await ctx.test('should restrict custom wake words by tier', async () => {
      const freeWakeWords = TIER_FEATURES.free.wake_words;
      const personalWakeWords = TIER_FEATURES.personal.wake_words;

      assert.ok(!freeWakeWords.includes('custom'), 'Free tier should not allow custom wake words');
      assert.ok(personalWakeWords.includes('custom'), 'Personal tier should allow custom wake words');
    });

    // Test: Overage cost calculation
    await ctx.test('should calculate overage costs correctly', async () => {
      const user = await createTestUser(db, { subscription_tier: 'personal' });

      // Track 150 voice minutes (50 over limit)
      await trackUsage(db, user.id, 'voice_minutes', 150);
      const limitCheck = checkLimit('personal', 'voice_minutes', 150);

      assert.strictEqual(limitCheck.overage, 50, 'Should calculate 50 minute overage');
      assert.strictEqual(limitCheck.overage_rate, 0.013, 'Should have correct overage rate');

      const overageCost = limitCheck.overage * limitCheck.overage_rate;
      assert.strictEqual(overageCost, 0.65, 'Should calculate $0.65 overage cost');
    });

    // Test: Admin tier has all features
    await ctx.test('should grant all features to admin tier', async () => {
      const adminUser = await createTestUser(db, { subscription_tier: 'admin' });

      // Admin should have access to everything
      const features = [
        'voice_minutes',
        'sms_messages',
        'team_collaboration',
        'buzz_workspace',
        'document_generation',
        'api_access',
        'custom_integrations',
      ];

      features.forEach(feature => {
        const access = hasFeature('admin', feature);
        assert.strictEqual(access, true, `Admin should have ${feature}`);
      });

      // Admin should have unlimited limits
      const voiceCheck = checkLimit('admin', 'voice_minutes', 999999);
      assert.strictEqual(voiceCheck.limit, null, 'Admin should have unlimited voice');
      assert.strictEqual(voiceCheck.allowed, true, 'Admin should always be allowed');
    });
  });
}
