#!/bin/bash

# Test script for voice activation feature
# Tests the new 'V' key voice activation and mouse selection

export XSWARM_PROJECT_DIR="/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss"
export XSWARM_DEV_ADMIN_EMAIL="admin@xswarm.dev"
export XSWARM_DEV_ADMIN_PASS="test123"

echo "🧪 Testing Voice Activation Feature"
echo "=================================="
echo ""

# Check if binary exists
if [ ! -f "target/release/xswarm" ]; then
    echo "❌ Binary not found at target/release/xswarm"
    exit 1
fi

echo "✅ Binary found"
echo "📏 Binary size: $(ls -lh target/release/xswarm | awk '{print $5}')"
echo ""

echo "🔧 Starting xswarm in dev mode..."
echo "Instructions for testing:"
echo "  1. The app should start in dev mode automatically"
echo "  2. Login with admin@xswarm.dev / test123 when prompted"
echo "  3. Once in dashboard, press 'V' to activate voice system"
echo "  4. Try selecting text with mouse (should work for copy/paste)"
echo "  5. Press 'Q' to quit when done testing"
echo ""
echo "Press any key to start testing..."
read -n 1 -s

echo "🚀 Launching xswarm --dev..."
./target/release/xswarm --dev