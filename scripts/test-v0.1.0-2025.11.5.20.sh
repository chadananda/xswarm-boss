#!/bin/bash
# Test v0.1.0-2025.11.5.20 WAV format fix (16-bit PCM)

set +e  # Don't exit on errors

echo "🧪 Testing v0.1.0-2025.11.5.20 - 16-bit PCM WAV format fix"
echo ""

# Clean up old files
rm -f ./tmp/moshi-debug-audio.wav
rm -f ./tmp/xswarm-v0.1.0-2025.11.5.20-fresh-test.log

# Start xswarm with WAV export
echo "▶️  Starting xswarm with MOSHI_DEBUG_WAV=1..."
MOSHI_DEBUG_WAV=1 ~/.local/bin/xswarm --dev > ./tmp/xswarm-v0.1.0-2025.11.5.20-fresh-test.log 2>&1 &
TEST_PID=$!

echo "Process ID: $TEST_PID"
echo "Waiting 30 seconds for auto-greeting..."
echo ""

# Wait for auto-greeting
sleep 30

# Kill the process gracefully (SIGTERM first, then SIGKILL if needed)
kill $TEST_PID 2>/dev/null
sleep 2  # Grace period for WAV file finalization
kill -9 $TEST_PID 2>/dev/null  # Force kill if still running
wait $TEST_PID 2>/dev/null

echo "Test complete. Checking results..."
echo ""

# Check if WAV file was generated
if [ -f ./tmp/moshi-debug-audio.wav ]; then
  echo "✅ WAV file generated:"
  ls -lh ./tmp/moshi-debug-audio.wav
  echo ""

  echo "📊 WAV file format:"
  ffmpeg -i ./tmp/moshi-debug-audio.wav -hide_banner 2>&1 | grep -E "(Duration|Audio:)"
  echo ""

  echo "🔊 Testing afplay..."
  if afplay ./tmp/moshi-debug-audio.wav 2>&1; then
    echo "✅ ✅ ✅ WAV FILE PLAYS SUCCESSFULLY! ✅ ✅ ✅"
    echo ""
    echo "🎉 v0.1.0-2025.11.5.20 WAV format fix WORKS!"
    exit 0
  else
    echo "❌ afplay failed"
    afplay ./tmp/moshi-debug-audio.wav 2>&1 | head -5
    exit 1
  fi
else
  echo "❌ No WAV file generated"
  echo ""
  echo "📋 Last 30 lines of log:"
  tail -30 ./tmp/xswarm-v0.1.0-2025.11.5.20-fresh-test.log
  exit 1
fi
