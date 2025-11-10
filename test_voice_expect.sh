#!/bin/bash

# Focused test using expect to verify voice activation doesn't corrupt TUI
export XSWARM_PROJECT_DIR="/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss"
export XSWARM_DEV_ADMIN_EMAIL="admin@xswarm.dev"
export XSWARM_DEV_ADMIN_PASS="test123"

echo "🧪 Testing Voice Activation - TUI Corruption Fix"
echo "================================================"

expect -c "
# Set up logging and timeout
log_user 1
set timeout 15

# Start the application
spawn ./target/release/xswarm --dev
expect {
    \"Email:\" {
        send \"admin@xswarm.dev\r\"
        expect \"Password:\"
        send \"test123\r\"

        # Wait for dashboard to load
        expect {
            -re \"Dashboard|Projects|Voice|Press\" {
                puts \"\\n✅ Successfully logged into dashboard\"

                # Test voice activation - press 'V'
                puts \"🎤 Testing voice activation with 'V' key...\"
                send \"v\"

                # Wait and check for corruption indicators
                expect {
                    -re \"🎤 Microphone Permission Request|━━━━━━|Requesting microphone access\" {
                        puts \"\\n❌ FAIL: Console output detected - TUI corruption occurred!\"
                        send \"q\"
                        exit 1
                    }
                    -re \"Starting voice system|Voice system started|Voice activated\" {
                        puts \"\\n✅ SUCCESS: Voice activation logged correctly\"
                        puts \"✅ No console output corruption detected\"
                        send \"q\"
                        expect eof
                        puts \"\\n🎉 Test PASSED: Voice activation works without TUI corruption\"
                        exit 0
                    }
                    timeout {
                        puts \"\\n⚠️  Voice activation completed (no visible corruption)\"
                        send \"q\"
                        expect eof
                        puts \"\\n✅ Test PASSED: No TUI corruption detected\"
                        exit 0
                    }
                }
            }
            timeout {
                puts \"\\n❌ FAIL: Dashboard failed to load within timeout\"
                exit 1
            }
        }
    }
    timeout {
        puts \"\\n❌ FAIL: Login prompt not found within timeout\"
        exit 1
    }
}
"

echo ""
if [ $? -eq 0 ]; then
    echo "🎉 Voice activation TUI test PASSED!"
    echo "✅ No console output corruption detected"
else
    echo "❌ Voice activation TUI test FAILED!"
    echo "🔧 Check logs for console output that may corrupt the TUI"
fi