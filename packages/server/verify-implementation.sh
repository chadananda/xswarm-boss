#!/bin/bash

# Boss AI Unified API - Implementation Verification Script
# This script verifies that all components are working correctly

set -e  # Exit on error

echo ""
echo "============================================"
echo "Boss AI Unified API - Verification"
echo "============================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

# Test function
test_step() {
    echo -n "Testing: $1... "
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Error: $1"
    ((FAILED++))
}

# Change to server directory
cd "$(dirname "$0")"

# 1. Check file structure
test_step "File structure"
if [ -f "src/lib/unified-message.js" ] && \
   [ -f "src/index.js" ] && \
   [ -f "test-integration.js" ] && \
   [ -f "examples/cli-client.js" ]; then
    pass
else
    fail "Missing required files"
fi

# 2. Check JSON import syntax
test_step "JSON import syntax"
if grep -q "with { type: 'json' }" src/lib/unified-message.js && \
   grep -q "with { type: 'json' }" src/routes/sms.js && \
   grep -q "with { type: 'json' }" src/routes/email.js; then
    pass
else
    fail "JSON imports not updated"
fi

# 3. Check unified API integration
test_step "Unified API integration in index.js"
if grep -q "handleCLIMessage" src/index.js && \
   grep -q "handleSMSMessage" src/index.js && \
   grep -q "handleEmailMessage" src/index.js && \
   grep -q "/api/message" src/index.js; then
    pass
else
    fail "Unified API not properly integrated"
fi

# 4. Check documentation
test_step "Documentation files"
if [ -f "UNIFIED_API_ARCHITECTURE.md" ] && \
   [ -f "IMPLEMENTATION_SUMMARY.md" ] && \
   [ -f "examples/README.md" ] && \
   [ -f "QUICK_REFERENCE.md" ]; then
    pass
else
    fail "Missing documentation files"
fi

# 5. Run unit tests
test_step "Unit tests"
if node src/test-unified-api.js > /tmp/boss-unit-test.log 2>&1; then
    pass
else
    fail "Unit tests failed (see /tmp/boss-unit-test.log)"
fi

# 6. Run integration tests
test_step "Integration tests"
if node test-integration.js > /tmp/boss-integration-test.log 2>&1; then
    pass
else
    fail "Integration tests failed (see /tmp/boss-integration-test.log)"
fi

# 7. Check CLI client
test_step "CLI client executable"
if [ -x "examples/cli-client.js" ]; then
    pass
else
    chmod +x examples/cli-client.js
    pass
fi

# 8. Check package.json scripts
test_step "Package.json scripts"
if grep -q '"test"' package.json; then
    pass
else
    fail "Test script not in package.json"
fi

# 9. Verify core functions exist
test_step "Core functions in unified-message.js"
if grep -q "export function normalizeCLIMessage" src/lib/unified-message.js && \
   grep -q "export function normalizeSMSMessage" src/lib/unified-message.js && \
   grep -q "export function normalizeEmailMessage" src/lib/unified-message.js && \
   grep -q "export function processUnifiedMessage" src/lib/unified-message.js && \
   grep -q "export function findUserByIdentifier" src/lib/unified-message.js && \
   grep -q "export function validateMessageAuthorization" src/lib/unified-message.js; then
    pass
else
    fail "Core functions not found"
fi

# 10. Check backward compatibility
test_step "Backward compatibility preserved"
if grep -q "handleVoiceWebhook" src/index.js && \
   grep -q "handleSmsWebhook" src/index.js && \
   grep -q "handleInboundEmail" src/index.js && \
   grep -q "sendBossEmail" src/index.js; then
    pass
else
    fail "Legacy handlers removed"
fi

echo ""
echo "============================================"
echo "Verification Summary"
echo "============================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All verification checks passed!${NC}"
    echo ""
    echo "Implementation is ready for use."
    echo ""
    echo "Next steps:"
    echo "  1. Start dev server: wrangler dev"
    echo "  2. Test CLI client: node examples/cli-client.js \"help\""
    echo "  3. Deploy: wrangler deploy"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some verification checks failed${NC}"
    echo ""
    echo "Please review the errors above and fix any issues."
    echo ""
    exit 1
fi
