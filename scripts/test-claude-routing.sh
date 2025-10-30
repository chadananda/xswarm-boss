#!/bin/bash

# Test Claude Code Message Routing
# This script tests the message routing system by simulating messages from different channels

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Claude Code Routing Test Script${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Configuration
SUPERVISOR_URL="${SUPERVISOR_URL:-ws://localhost:9999}"
SERVER_URL="${SERVER_URL:-http://localhost:8787}"
SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-dev-token-12345}"

# Admin configuration (from config.toml)
ADMIN_PHONE="+15559876543"
ADMIN_EMAIL="admin@xswarm.dev"
ADMIN_USER_ID="admin"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Supervisor URL: $SUPERVISOR_URL"
echo "  Server URL: $SERVER_URL"
echo "  Admin Phone: $ADMIN_PHONE"
echo "  Admin Email: $ADMIN_EMAIL"
echo ""

# Function to test SMS routing
test_sms_routing() {
    echo -e "${BLUE}[1/3] Testing SMS Routing...${NC}"

    local sms_payload=$(cat <<EOF
{
    "From": "$ADMIN_PHONE",
    "To": "+18005559876",
    "Body": "Test SMS: What is the current project status?"
}
EOF
)

    echo "  Sending SMS webhook..."
    response=$(curl -s -X POST "$SERVER_URL/api/webhooks/sms" \
        -H "Content-Type: application/json" \
        -d "$sms_payload")

    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} SMS webhook received"
        echo "  Response: $response"
    else
        echo -e "  ${RED}✗${NC} Failed to send SMS webhook"
        return 1
    fi

    echo ""
}

# Function to test Email routing
test_email_routing() {
    echo -e "${BLUE}[2/3] Testing Email Routing...${NC}"

    local email_payload=$(cat <<EOF
{
    "from": "$ADMIN_EMAIL",
    "to": "boss@xswarm.ai",
    "subject": "Test Email: Project Discussion",
    "body": "Can you provide an update on the Claude Code integration?"
}
EOF
)

    echo "  Sending Email webhook..."
    response=$(curl -s -X POST "$SERVER_URL/api/webhooks/email" \
        -H "Content-Type: application/json" \
        -d "$email_payload")

    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Email webhook received"
        echo "  Response: $response"
    else
        echo -e "  ${RED}✗${NC} Failed to send Email webhook"
        return 1
    fi

    echo ""
}

# Function to check Claude Code session status
check_session_status() {
    echo -e "${BLUE}[3/3] Checking Claude Code Session Status...${NC}"

    # Build and run the status command
    cd "$(dirname "$0")/.."

    echo "  Querying active sessions..."
    cargo run --quiet --bin xswarm -- claude status 2>/dev/null || {
        echo -e "  ${YELLOW}⚠${NC}  No active sessions found (or cargo run failed)"
        echo "  This is normal if Claude Code is not running or no messages were routed"
        return 0
    }

    echo ""
}

# Function to check Claude Code costs
check_costs() {
    echo -e "${BLUE}Checking Claude Code Costs...${NC}"

    cd "$(dirname "$0")/.."

    echo "  Querying costs for admin user..."
    cargo run --quiet --bin xswarm -- claude cost --user-id admin 2>/dev/null || {
        echo -e "  ${YELLOW}⚠${NC}  No cost data available"
        return 0
    }

    echo ""
}

# Main test sequence
main() {
    echo -e "${YELLOW}Prerequisites:${NC}"
    echo "  1. Boss voice bridge must be running with --enable-claude-code"
    echo "  2. Claude Code WebSocket server must be running on ws://localhost:8080"
    echo "  3. Node.js server must be running on port 8787"
    echo ""

    read -p "Press Enter to start tests (or Ctrl+C to cancel)..."
    echo ""

    # Run tests
    test_sms_routing
    sleep 2

    test_email_routing
    sleep 2

    check_session_status
    sleep 1

    check_costs

    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}Testing Complete!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo ""
    echo -e "${YELLOW}What to check:${NC}"
    echo "  1. Boss logs should show 'Admin SMS/Email detected - routing to Claude Code'"
    echo "  2. Claude Code should have received the messages"
    echo "  3. Responses should be sent back via SMS/Email"
    echo "  4. Session status should show active sessions"
    echo "  5. Costs should be tracked"
    echo ""
    echo -e "${YELLOW}View Boss logs:${NC}"
    echo "  Look for lines containing 'Admin' and 'Claude Code' in the voice bridge output"
    echo ""
}

# Run main function
main
