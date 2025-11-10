#!/bin/bash
# MOSHI Audio Testing Script with Whisper Transcription
#
# This script automates the process of:
# 1. Running xswarm with WAV export enabled
# 2. Capturing MOSHI audio output
# 3. Transcribing with Whisper
# 4. Verifying if audio is intelligible
#
# Usage: ./scripts/test-moshi-audio.sh [duration_seconds]

set -e

# Configuration
DURATION=${1:-10}  # Default: capture 10 seconds of audio
AUDIO_FILE="./tmp/moshi-debug-audio.wav"
TRANSCRIPTION_FILE="./tmp/moshi-transcription.txt"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎙️  MOSHI Audio Quality Test (Whisper-based)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Test Configuration:"
echo "   Audio capture duration: ${DURATION}s"
echo "   Audio output: $AUDIO_FILE"
echo "   Transcription output: $TRANSCRIPTION_FILE"
echo ""

# Clean up old files
rm -f "$AUDIO_FILE" "$TRANSCRIPTION_FILE"
mkdir -p ./tmp

# Kill any existing xswarm processes
echo "🧹 Cleaning up existing xswarm processes..."
pkill -9 xswarm 2>/dev/null || true
sleep 1

# Start xswarm with WAV export enabled
echo "🚀 Starting xswarm with WAV export..."
echo "   (Set MOSHI_DEBUG_WAV=1 to enable audio capture)"
echo ""

MOSHI_DEBUG_WAV=1 ~/.local/bin/xswarm --dev &
XSWARM_PID=$!

echo "   xswarm started (PID: $XSWARM_PID)"
echo ""

# Wait for initialization
echo "⏳ Waiting 5 seconds for initialization..."
sleep 5

# Capture audio
echo "🎵 Capturing MOSHI audio..."
echo "   Speak to MOSHI now! Recording for ${DURATION}s..."
echo ""

# Progress indicator
for i in $(seq 1 $DURATION); do
    echo -ne "   Recording... [$i/${DURATION}s]\r"
    sleep 1
done
echo ""
echo ""

# Stop xswarm
echo "🛑 Stopping xswarm..."
kill $XSWARM_PID 2>/dev/null || true
sleep 2
pkill -9 xswarm 2>/dev/null || true

# Check if audio file was created
if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ ERROR: Audio file not found at $AUDIO_FILE"
    echo "   Make sure MOSHI was running and generating audio."
    exit 1
fi

# Get file info
FILE_SIZE=$(ls -lh "$AUDIO_FILE" | awk '{print $5}')
echo "   Audio file created: $FILE_SIZE"
echo ""

# Transcribe with Whisper
echo "✍️  Transcribing audio with Whisper..."
echo "   (This may take 1-2 minutes to download model on first run)"
echo ""

cd packages/core
cargo run --example transcribe_moshi_audio --release 2>&1 | tee "../../$TRANSCRIPTION_FILE"
cd ../..

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test complete!"
echo ""
echo "📁 Results saved to:"
echo "   Audio: $AUDIO_FILE"
echo "   Transcription: $TRANSCRIPTION_FILE"
echo ""
echo "💡 Next Steps:"
echo "   - Review transcription to verify if speech is intelligible"
echo "   - If garbled, try next audio pipeline configuration"
echo "   - If clear, MOSHI audio is working correctly!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
