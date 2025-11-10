# Sprint 1: Critical Test Gaps (HIGH PRIORITY)

## Goal
Create unified test suite that validates all tier-based features work together with proper restrictions.

## Tasks

### Task 1.1: Create Unified Test Runner
**What:** Master test suite that runs all existing feature tests
**Why:** Currently tests are scattered, need single command to validate everything
**Files to create:**
- /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tests/run-all-tier-tests.js
- /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tests/suites/tier-features-suite.js

**Requirements:**
- Discovers and runs all test-*.js files in packages/server
- Runs all test files in tests/unit and tests/integration
- Provides summary report (pass/fail counts, duration)
- Returns exit code 0 if all pass, 1 if any fail
- Shows which features passed/failed
- Saves detailed results to tests/results/latest.json

**Acceptance Criteria:**
- Single command `node tests/run-all-tier-tests.js` runs everything
- Clear output showing which features are tested
- Summary at end with pass/fail counts
- Failed tests show error details

### Task 1.2: Tier-Based Integration Tests
**What:** Validate tier restrictions work across ALL features
**Why:** Individual features tested, but need to verify tier gating works everywhere
**File to create:**
- /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tests/integration/tier-restrictions.test.js

**Test Cases:**
1. Free tier user CANNOT:
   - Create >3 personas
   - Write to calendar (only read)
   - Send emails (only read)
   - Use >30 days memory retention
   - Access voice minutes (0 included)
   - Access SMS (0 included)

2. Personal tier user CAN:
   - Create unlimited personas
   - Write to calendar
   - Send emails
   - Use 365-day memory retention
   - Use 100 voice minutes/mo
   - Use 100 SMS/mo

3. Personal tier user CANNOT:
   - Create teams
   - Access Buzz workspace
   - Exceed limits without overages

4. Professional tier gets all Personal + teams + buzz

5. Enterprise tier gets unlimited everything

**Acceptance Criteria:**
- Test each tier's feature access matrix
- Test limit enforcement
- Test upgrade CTAs appear when feature locked
- Test overage calculations for metered features
- All tests pass with correct tier restrictions

### Task 1.3: OAuth Flow Integration Tests
**What:** Test Google Calendar and Gmail OAuth flows end-to-end
**Why:** OAuth is critical but not fully integration tested
**Files to create:**
- /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tests/integration/oauth-google-calendar.test.js
- /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/tests/integration/oauth-gmail.test.js

**Test Cases (Calendar):**
1. Generate auth URL with correct scopes
2. Handle callback with valid code
3. Store encrypted tokens in database
4. Refresh expired tokens automatically
5. Sync calendar events after authorization
6. Respect tier-based read-only vs read-write access
7. Handle authorization denial gracefully
8. Test disconnecting calendar integration

**Test Cases (Gmail):**
1. Generate auth URL with Gmail scopes
2. Handle callback and store tokens
3. Read emails after authorization
4. Test read-only access (Free tier)
5. Test email sending (Personal+ tier)
6. Test automatic token refresh
7. Handle Gmail API rate limits
8. Test disconnecting Gmail integration

**Acceptance Criteria:**
- Mock OAuth flows work (don't require real Google login)
- Token storage and encryption tested
- Token refresh logic tested
- Tier-based access control tested
- Error handling tested (denial, expired tokens, API failures)
- All OAuth tests pass

## Deliverables

After Sprint 1 completion:
1. ✅ Single command runs all tier feature tests
2. ✅ Comprehensive tier restriction validation
3. ✅ OAuth flows tested end-to-end
4. ✅ Test report showing all results
5. ✅ Documentation on running tests

## Success Metrics
- All existing tests still pass
- New integration tests pass
- Test coverage report shows >90% for tier features
- CI/CD ready (can run in GitHub Actions)
- Clear documentation for developers

## Time Estimate
8-10 hours total:
- Task 1.1: 2-3 hours
- Task 1.2: 3-4 hours
- Task 1.3: 3-4 hours

## Dependencies
- Existing test infrastructure (tests/utils)
- Existing feature tests (packages/server/test-*.js)
- Test database
- Mock OAuth credentials

## Next Steps After Sprint 1
- Sprint 2: E2E workflow tests & security tests
- Sprint 3: Playwright visual tests
- Sprint 4: Performance & error recovery tests
