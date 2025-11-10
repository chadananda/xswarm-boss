#!/bin/bash
# Analyze MOSHI audio output without using hallucinating STT
# Uses ffmpeg for audio metrics and spectral analysis
# v1.0 - Direct audio analysis approach

set -e

echo "🔊 MOSHI AUDIO ANALYSIS (No STT)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check dependencies
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ERROR: ffmpeg required for audio analysis"
    echo "Install: brew install ffmpeg"
    exit 1
fi

# Configuration
AUDIO_FILE="./tmp/determinism-test/output-1.wav"

if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ ERROR: Audio file not found: $AUDIO_FILE"
    echo "Run determinism test first: ./scripts/test-moshi-determinism.sh"
    exit 1
fi

echo "📊 Analyzing: $AUDIO_FILE"
echo ""

# Get basic audio info
echo "═══ BASIC INFO ═══"
ffprobe -v error -show_entries format=duration,bit_rate,sample_rate \
    -show_entries stream=codec_name,channels,sample_rate \
    -of default=noprint_wrappers=1 "$AUDIO_FILE"
echo ""

# Volume analysis (detects if audio is too quiet/silent)
echo "═══ VOLUME ANALYSIS ═══"
ffmpeg -i "$AUDIO_FILE" -af volumedetect -f null - 2>&1 | grep -E "(mean_volume|max_volume|histogram)"
echo ""

# Audio statistics (detects noise vs speech characteristics)
echo "═══ AUDIO STATISTICS ═══"
ffmpeg -i "$AUDIO_FILE" -af astats -f null - 2>&1 | grep -E "(RMS|Peak|Dynamic range|Zero crossing|Flat factor|Crest factor)" | head -20
echo ""

# Generate spectrogram for visual inspection
echo "📊 Generating spectrogram..."
SPECTRUM_FILE="./tmp/determinism-test/spectrum-analysis.png"
ffmpeg -i "$AUDIO_FILE" -lavfi showspectrumpic=s=1024x512:mode=separate \
    "$SPECTRUM_FILE" -y 2>/dev/null

echo "✅ Spectrogram saved: $SPECTRUM_FILE"
echo ""

# Detect silence periods (speech should have varying levels)
echo "═══ SILENCE DETECTION ═══"
ffmpeg -i "$AUDIO_FILE" -af silencedetect=n=-40dB:d=0.5 -f null - 2>&1 | grep silence | head -10
echo ""

echo "╔════════════════════════════════════════════════════════════════"
echo "║ ANALYSIS INTERPRETATION"
echo "╠════════════════════════════════════════════════════════════════"
echo "║"
echo "║ 🔍 What to look for:"
echo "║"
echo "║ GOOD AUDIO (Clear speech):"
echo "║   • Mean volume: -20 to -30 dB"
echo "║   • Dynamic range: > 30 dB"
echo "║   • Zero crossing rate: 0.05-0.15 (speech varies)"
echo "║   • Spectral flatness: 0.1-0.3 (speech has structure)"
echo "║   • Spectrogram: Clear formant patterns, harmonic structure"
echo "║   • Silence: Natural pauses between words"
echo "║"
echo "║ BAD AUDIO (Garbled/noise):"
echo "║   • Mean volume: < -40 dB or > -10 dB"
echo "║   • Dynamic range: < 20 dB (compressed/flat)"
echo "║   • Zero crossing rate: > 0.3 (noisy) or near 0 (silent)"
echo "║   • Spectral flatness: > 0.7 (white noise)"
echo "║   • Spectrogram: Random noise pattern, no structure"
echo "║   • Silence: Mostly silent or constant noise"
echo "║"
echo "╚════════════════════════════════════════════════════════════════"
echo ""

echo "👁️  VIEW SPECTROGRAM:"
echo "   open $SPECTRUM_FILE"
echo ""
echo "🎧 LISTEN TO AUDIO:"
echo "   afplay $AUDIO_FILE"
echo ""
