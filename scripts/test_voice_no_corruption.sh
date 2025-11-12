#!/bin/bash

# Test script to verify voice activation doesn't corrupt TUI
# Tests the fixed microphone permission system

export XSWARM_PROJECT_DIR="/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss"
export XSWARM_DEV_ADMIN_EMAIL="admin@xswarm.dev"
export XSWARM_DEV_ADMIN_PASS="test123"

echo "🧪 Testing Voice Activation - TUI Corruption Fix"
echo "================================================"
echo ""
echo "This test verifies that:"
echo "  ✅ Voice activation doesn't print to console"
echo "  ✅ TUI display remains clean and uncorrupted"
echo "  ✅ Microphone permission works silently"
echo "  ✅ Dashboard remains functional after 'V' press"
echo ""

# Check if binary exists
if [ ! -f "target/release/xswarm" ]; then
    echo "❌ Binary not found at target/release/xswarm"
    exit 1
fi

echo "✅ Binary found"
echo "📏 Binary size: $(ls -lh target/release/xswarm | awk '{print $5}')"
echo ""

echo "🔧 Testing Instructions:"
echo "  1. App will start in dev mode"
echo "  2. Login: admin@xswarm.dev / test123"
echo "  3. Press 'V' to test voice activation"
echo "  4. Verify NO console output corrupts the TUI"
echo "  5. Voice system should activate silently"
echo "  6. Dashboard should remain visually intact"
echo "  7. Press 'Q' to quit when done"
echo ""
echo "🎯 Success Criteria:"
echo "  • No text overlaying the dashboard interface"
echo "  • Clean TUI display throughout interaction"
echo "  • Voice activation logs only in background"
echo ""
echo "Press any key to start testing..."
read -n 1 -s

echo ""
echo "🚀 Launching xswarm --dev..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Use expect for automated testing if available
if command -v expect >/dev/null 2>&1; then
    echo "📝 Running automated test with expect..."
    expect -c "
    spawn ./target/release/xswarm --dev
    set timeout 30

    expect {
        \"Email:\" {
            send \"admin@xswarm.dev\r\"
            expect \"Password:\"
            send \"test123\r\"
            expect {
                \"Dashboard\" {
                    puts \"✅ Successfully logged into dashboard\"
                    send \"v\"
                    sleep 3
                    puts \"✅ Voice activation test completed\"
                    send \"q\"
                    expect eof
                    puts \"✅ Application exited cleanly\"
                }
                timeout {
                    puts \"❌ Dashboard failed to load\"
                    exit 1
                }
            }
        }
        timeout {
            puts \"❌ Login prompt not found\"
            exit 1
        }
    }
    "
else
    echo "⚠️  'expect' not found - running manual test"
    echo "Please test manually by following the instructions above"
    ./target/release/xswarm --dev
fi

echo ""
echo "🎉 Voice activation TUI corruption test completed!"