#!/bin/bash
# Test MOSHI with real voice input instead of quiet noise
# This helps verify if the issue is specific to certain input types

set -e

echo "🎙️  REAL VOICE INPUT TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This test will:"
echo "  1. Record 3 seconds of your voice"
echo "  2. Process it through MOSHI"
echo "  3. Transcribe the output with Whisper API"
echo "  4. Verify if MOSHI response is intelligible"
echo ""
echo "Press ENTER when ready to record, then speak clearly for 3 seconds..."
read

# Check if sox is installed
if ! command -v sox &> /dev/null; then
    echo "❌ Error: sox is not installed"
    echo "Install with: brew install sox"
    exit 1
fi

# Create tmp directory if it doesn't exist
mkdir -p ./tmp

# Record 3 seconds of speech at 24kHz (MOSHI native rate)
echo ""
echo "🔴 Recording... (3 seconds)"
echo "Say something like: \"Hello MOSHI, how are you today?\""
echo ""

sox -d -r 24000 -c 1 -b 16 ./tmp/test-real-speech.wav trim 0 3 2>/dev/null

echo "✅ Recording complete: ./tmp/test-real-speech.wav"
echo ""

# Show audio info
echo "📊 Audio file info:"
soxi ./tmp/test-real-speech.wav
echo ""

# Now set the environment variable to use this input and run test
echo "🔧 Processing through MOSHI with real voice input..."
echo ""

export MOSHI_TEST_INPUT=./tmp/test-real-speech.wav

# Run the test
./target/release/xswarm --moshi-test

echo ""
echo "✅ Test complete!"
echo ""
echo "Results:"
echo "  - Input: ./tmp/test-real-speech.wav (your voice)"
echo "  - Output: ./tmp/moshi-response.wav (MOSHI response)"
echo ""
echo "To listen to the files:"
echo "  play ./tmp/test-real-speech.wav"
echo "  play ./tmp/moshi-response.wav"
