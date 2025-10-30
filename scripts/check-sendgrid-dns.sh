#!/bin/bash
##
# SendGrid DNS Configuration Checker
#
# Checks DNS records required for SendGrid inbound email parsing
##

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          SendGrid DNS Configuration Checker                      ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Get boss email from users.json
BOSS_EMAIL=$(node -e "
  const fs = require('fs');
  const config = JSON.parse(fs.readFileSync('./packages/server/src/config/users.json', 'utf-8'));
  console.log(config.users[0].boss_email);
")

echo -e "${BLUE}Boss Email:${NC} $BOSS_EMAIL"
echo ""

# Extract subdomain and domain
SUBDOMAIN=$(echo "$BOSS_EMAIL" | cut -d@ -f1)
DOMAIN=$(echo "$BOSS_EMAIL" | cut -d@ -f2)
FULL_HOSTNAME="${SUBDOMAIN}.${DOMAIN}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: Checking MX Record for $FULL_HOSTNAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if dig is available
if ! command -v dig &> /dev/null; then
    echo -e "${YELLOW}⚠️  'dig' command not found. Trying nslookup...${NC}"

    if ! command -v nslookup &> /dev/null; then
        echo -e "${RED}❌ Neither 'dig' nor 'nslookup' found. Cannot check DNS.${NC}"
        echo ""
        echo "Please install dig (dnsutils) or use an online DNS checker:"
        echo "  - https://mxtoolbox.com/SuperTool.aspx?action=mx:${FULL_HOSTNAME}"
        echo "  - https://toolbox.googleapps.com/apps/dig/#MX/${FULL_HOSTNAME}"
        exit 1
    fi

    # Use nslookup
    echo "Checking MX record with nslookup..."
    echo ""
    nslookup -type=mx "$FULL_HOSTNAME" || true
    echo ""
else
    # Use dig
    echo "Checking MX record with dig..."
    echo ""
    dig MX "$FULL_HOSTNAME" +short || true
    echo ""
fi

# Expected MX record
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Expected Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}MX Record should be:${NC}"
echo "  Host/Name: $SUBDOMAIN"
echo "  Type: MX"
echo "  Priority: 10"
echo "  Value: mx.sendgrid.net"
echo "  TTL: 3600 (or automatic)"
echo ""

# Check if mx.sendgrid.net is present
if dig MX "$FULL_HOSTNAME" +short 2>/dev/null | grep -q "mx.sendgrid.net"; then
    echo -e "${GREEN}✅ MX record is correctly configured!${NC}"
    echo ""
elif nslookup -type=mx "$FULL_HOSTNAME" 2>/dev/null | grep -q "mx.sendgrid.net"; then
    echo -e "${GREEN}✅ MX record is correctly configured!${NC}"
    echo ""
else
    echo -e "${RED}❌ MX record NOT found or incorrectly configured${NC}"
    echo ""
    echo -e "${YELLOW}Action Required:${NC}"
    echo "1. Log in to your DNS provider (where $DOMAIN is registered)"
    echo "2. Add or update the MX record with the configuration above"
    echo "3. Wait 5-60 minutes for DNS propagation"
    echo "4. Run this script again to verify"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: Checking Domain Authentication (SPF, DKIM)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check SPF record for main domain
echo "Checking SPF record for $DOMAIN..."
if command -v dig &> /dev/null; then
    dig TXT "$DOMAIN" +short | grep "v=spf1" || echo "  No SPF record found"
else
    nslookup -type=txt "$DOMAIN" | grep "v=spf1" || echo "  No SPF record found"
fi
echo ""

# Check DKIM records (SendGrid uses specific subdomains)
echo "Checking DKIM records..."
echo "  (SendGrid DKIM records are under specific subdomains)"
echo "  Check at: https://app.sendgrid.com/settings/sender_auth"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Configuration Status:"
echo ""
echo "Email Address: $BOSS_EMAIL"
echo "DNS Hostname: $FULL_HOSTNAME"
echo ""
echo "Next Steps:"
echo "1. Ensure MX record is configured (see above)"
echo "2. Run: node scripts/diagnose-sendgrid.js"
echo "3. Run: node scripts/fix-sendgrid.js"
echo "4. Test by sending email to: $BOSS_EMAIL"
echo ""
echo "Online DNS Checkers:"
echo "  - https://mxtoolbox.com/SuperTool.aspx?action=mx:${FULL_HOSTNAME}"
echo "  - https://toolbox.googleapps.com/apps/dig/#MX/${FULL_HOSTNAME}"
echo ""
