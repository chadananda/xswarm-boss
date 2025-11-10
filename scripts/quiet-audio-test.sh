#!/bin/bash
# Quiet MOSHI Audio Quality Test
# Tests audio output quality by transcribing with Whisper

set -e

VERSION=${1:-"v0.1.0-2025.11.5.18"}
TEST_DURATION=${2:-10}

echo "🔇 Quiet MOSHI Audio Test - $VERSION"
echo "Duration: ${TEST_DURATION}s"
echo ""

# Clean up old files
rm -f ./tmp/moshi-debug-audio.wav
rm -f ./tmp/xswarm-test.log

# Start MOSHI with WAV export (user should mute volume)
echo "▶️  Starting MOSHI (please mute your volume)..."
env MOSHI_DEBUG_WAV=1 ~/.local/bin/xswarm --dev > ./tmp/xswarm-test.log 2>&1 &
XSWARM_PID=$!

echo "Process ID: $XSWARM_PID"
echo "Waiting ${TEST_DURATION}s for audio capture..."
echo ""

# Wait for test duration
sleep ${TEST_DURATION}

# Kill xswarm
kill $XSWARM_PID 2>/dev/null || true
sleep 1

# Check if WAV file was created
if [ ! -f ./tmp/moshi-debug-audio.wav ]; then
    echo "❌ No WAV file generated"
    exit 1
fi

# Analyze WAV file
echo "📊 WAV File Analysis:"
ffmpeg -i ./tmp/moshi-debug-audio.wav -hide_banner 2>&1 | grep -E "(Duration|Audio:)" || true
echo ""

# Get sample count
SAMPLES=$(ffmpeg -i ./tmp/moshi-debug-audio.wav -f null - 2>&1 | grep -o '[0-9]* samples' | head -1 || echo "0 samples")
echo "Total samples: $SAMPLES"
echo ""

# Transcribe with Whisper if available
if command -v whisper &> /dev/null; then
    echo "🎯 Transcribing with Whisper..."
    whisper ./tmp/moshi-debug-audio.wav --model tiny --language en --output_dir ./tmp/ --output_format txt 2>/dev/null || true

    if [ -f ./tmp/moshi-debug-audio.txt ]; then
        echo ""
        echo "📝 Transcription:"
        cat ./tmp/moshi-debug-audio.txt
        echo ""

        # Check if transcription is meaningful (not empty, has words)
        WORD_COUNT=$(wc -w < ./tmp/moshi-debug-audio.txt | tr -d ' ')
        if [ "$WORD_COUNT" -gt 5 ]; then
            echo "✅ Audio appears intelligible ($WORD_COUNT words transcribed)"
            exit 0
        else
            echo "⚠️  Audio may be garbled (only $WORD_COUNT words transcribed)"
            exit 1
        fi
    fi
else
    echo "⚠️  Whisper not installed - install with: pip install openai-whisper"
    echo "Skipping transcription test"
    exit 0
fi
