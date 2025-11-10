#!/bin/bash
# CPU vs Metal Backend Diagnostic Test for MOSHI Audio
# This will take longer than normal (CPU is slow) but we need to see if CPU produces clear audio

set -e

echo "🧪 MOSHI CPU vs Metal Diagnostic Test"
echo "======================================"
echo ""
echo "⚠️  NOTE: CPU mode will be SLOW - this is expected!"
echo "    We just need to generate ONE audio file to compare."
echo ""

# Clean up old results
echo "🧹 Cleaning old test results..."
rm -rf ./tmp/experiments/
rm -f ./tmp/moshi-response.wav
rm -f ./tmp/moshi-metal.wav
rm -f ./tmp/moshi-cpu.wav

echo "✅ Cleanup complete"
echo ""

# Test with Metal (current)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST 1: Metal Backend (GPU - Fast)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev 2>&1 | grep -E "(FORCING|Selected|SUCCESS|FAIL)" || true

if [ -f ./tmp/moshi-response.wav ]; then
    echo ""
    echo "✅ Metal audio generated"
    cp ./tmp/moshi-response.wav ./tmp/moshi-metal.wav

    echo "📊 Analyzing Metal audio quality..."
    METAL_SCORE=$(python3 scripts/analyze-waveform.py ./tmp/moshi-metal.wav 2>&1 | grep "Score:" | awk '{print $2}' | cut -d'/' -f1)
    echo "   Metal Score: $METAL_SCORE/100"

    echo ""
    echo "🔊 Playing Metal audio..."
    afplay ./tmp/moshi-metal.wav
else
    echo "❌ Metal test failed - no audio generated"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST 2: CPU Backend (Diagnostic - SLOW)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏳ Starting CPU test (this will take 2-5 minutes)..."
echo "   Please be patient - CPU inference is much slower!"
echo ""

# Clean for CPU test
rm -rf ./tmp/experiments/
rm -f ./tmp/moshi-response.wav

# Run with CPU
MOSHI_USE_CPU=1 MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev 2>&1 | grep -E "(FORCING|Selected|SUCCESS|FAIL)" || true

if [ -f ./tmp/moshi-response.wav ]; then
    echo ""
    echo "✅ CPU audio generated"
    cp ./tmp/moshi-response.wav ./tmp/moshi-cpu.wav

    echo "📊 Analyzing CPU audio quality..."
    CPU_SCORE=$(python3 scripts/analyze-waveform.py ./tmp/moshi-cpu.wav 2>&1 | grep "Score:" | awk '{print $2}' | cut -d'/' -f1)
    echo "   CPU Score: $CPU_SCORE/100"

    echo ""
    echo "🔊 Playing CPU audio..."
    afplay ./tmp/moshi-cpu.wav
else
    echo "❌ CPU test failed - no audio generated"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 COMPARISON RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Metal Backend: $METAL_SCORE/100"
echo "CPU Backend:   $CPU_SCORE/100"
echo ""

# Interpret results
if [ "$CPU_SCORE" -ge 60 ] && [ "$METAL_SCORE" -lt 60 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ DIAGNOSIS: Metal Backend Bug on M3 Max"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "CPU produces clear audio but Metal produces garbled audio."
    echo "This indicates a Candle Metal backend issue on M3 Max."
    echo ""
    echo "NEXT STEPS:"
    echo "1. Report to Candle GitHub with reproduction"
    echo "2. Use CPU for Mac development (slower)"
    echo "3. Deploy to Linux with CUDA for production"
    echo "4. Monitor Candle releases for Metal fixes"
    echo ""
elif [ "$CPU_SCORE" -lt 60 ] && [ "$METAL_SCORE" -lt 60 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "❌ DIAGNOSIS: Code Logic or Model Issue"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Both CPU and Metal produce garbled audio."
    echo "This indicates a code bug or Q8 model issue."
    echo ""
    echo "NEXT STEPS:"
    echo "1. Deep comparison with gen.rs implementation"
    echo "2. Test with bf16 safetensors model"
    echo "3. Investigate MIMI codec state management"
    echo "4. Consider Python MLX for reference"
    echo ""
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤔 UNEXPECTED: Need Human Verification"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Scores are ambiguous. Please listen to both files:"
    echo "  Metal: ./tmp/moshi-metal.wav"
    echo "  CPU:   ./tmp/moshi-cpu.wav"
    echo ""
fi

echo ""
echo "Audio files saved:"
echo "  Metal: ./tmp/moshi-metal.wav"
echo "  CPU:   ./tmp/moshi-cpu.wav"
echo ""
echo "You can replay them:"
echo "  afplay ./tmp/moshi-metal.wav"
echo "  afplay ./tmp/moshi-cpu.wav"
