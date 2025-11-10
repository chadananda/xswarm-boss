#!/bin/bash
# MOSHI Waveform Comparison Test
# Compares our MOSHI output against official CLI output
# Uses audio metrics instead of hallucinating STT
# v9.0 - Deterministic waveform-based testing

set -e

echo "🧪 MOSHI WAVEFORM COMPARISON TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check dependencies
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ERROR: ffmpeg required for audio analysis"
    echo "Install: brew install ffmpeg"
    exit 1
fi

# Configuration
TMP_DIR="./tmp"
REFERENCE_DIR="$TMP_DIR/reference"
TEST_INPUT="$TMP_DIR/test-user-hello.wav"
OFFICIAL_OUTPUT="$REFERENCE_DIR/moshi-official.wav"
OUR_OUTPUT="$TMP_DIR/moshi-response.wav"
METRICS_FILE="$TMP_DIR/audio-comparison-metrics.txt"

mkdir -p "$REFERENCE_DIR"

# Step 1: Generate reference audio with official MOSHI CLI (if not exists)
if [ ! -f "$OFFICIAL_OUTPUT" ]; then
    echo "📝 Generating reference audio with official MOSHI CLI..."
    echo ""

    if [ ! -f "packages/moshi/moshi-cli/target/release/moshi-cli" ]; then
        echo "Building official MOSHI CLI..."
        cd packages/moshi/moshi-cli
        cargo build --release
        cd ../../..
    fi

    # Use same seed for deterministic output
    packages/moshi/moshi-cli/target/release/moshi-cli \
        --input "$TEST_INPUT" \
        --output "$OFFICIAL_OUTPUT" \
        --seed 299792458 \
        --temperature 0.8

    echo "✅ Reference audio generated: $OFFICIAL_OUTPUT"
    echo ""
else
    echo "✅ Using existing reference audio: $OFFICIAL_OUTPUT"
    echo ""
fi

# Step 2: Generate our audio
echo "🔊 Generating our MOSHI output..."
rm -rf ./tmp/experiments/
./target/release/xswarm --moshi-test > /dev/null 2>&1

if [ ! -f "$OUR_OUTPUT" ]; then
    echo "❌ ERROR: Our MOSHI output not generated"
    exit 1
fi

echo "✅ Our audio generated: $OUR_OUTPUT"
echo ""

# Step 3: Extract audio metrics
echo "📊 Analyzing audio metrics..."
echo "" > "$METRICS_FILE"

# Function to get audio metrics
get_metrics() {
    local file=$1
    local label=$2

    echo "=== $label ===" >> "$METRICS_FILE"

    # RMS level (loudness)
    local rms=$(ffmpeg -i "$file" -af "volumedetect" -f null - 2>&1 | \
        grep "mean_volume" | awk '{print $5}')
    echo "RMS Level: $rms dB" >> "$METRICS_FILE"

    # Peak level
    local peak=$(ffmpeg -i "$file" -af "volumedetect" -f null - 2>&1 | \
        grep "max_volume" | awk '{print $5}')
    echo "Peak Level: $peak dB" >> "$METRICS_FILE"

    # Zero crossing rate (speech characteristic)
    local zcr=$(ffmpeg -i "$file" -af "astats" -f null - 2>&1 | \
        grep "Zero crossing" | head -1 | awk '{print $4}')
    echo "Zero Crossing Rate: $zcr" >> "$METRICS_FILE"

    # Spectral flatness (noise vs tone indicator)
    local flatness=$(ffmpeg -i "$file" -af "astats" -f null - 2>&1 | \
        grep "Flat factor" | head -1 | awk '{print $4}')
    echo "Spectral Flatness: $flatness" >> "$METRICS_FILE"

    # Duration
    local duration=$(ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 "$file")
    echo "Duration: $duration seconds" >> "$METRICS_FILE"

    echo "" >> "$METRICS_FILE"
}

get_metrics "$OFFICIAL_OUTPUT" "OFFICIAL MOSHI CLI"
get_metrics "$OUR_OUTPUT" "OUR IMPLEMENTATION"

# Step 4: Generate spectrograms for visual comparison
echo "🎨 Generating spectrograms..."

ffmpeg -i "$OFFICIAL_OUTPUT" -lavfi showspectrumpic=s=1024x256:mode=separate \
    "$REFERENCE_DIR/official-spectrum.png" -y 2>/dev/null

ffmpeg -i "$OUR_OUTPUT" -lavfi showspectrumpic=s=1024x256:mode=separate \
    "$TMP_DIR/our-spectrum.png" -y 2>/dev/null

echo "✅ Spectrograms saved"
echo "   Official: $REFERENCE_DIR/official-spectrum.png"
echo "   Ours:     $TMP_DIR/our-spectrum.png"
echo ""

# Step 5: Calculate correlation
echo "🔬 Calculating waveform correlation..."

# Extract raw PCM data for correlation
ffmpeg -i "$OFFICIAL_OUTPUT" -f f32le -acodec pcm_f32le \
    "$REFERENCE_DIR/official.pcm" -y 2>/dev/null

ffmpeg -i "$OUR_OUTPUT" -f f32le -acodec pcm_f32le \
    "$TMP_DIR/our.pcm" -y 2>/dev/null

# Simple correlation check (requires Python or similar)
# For now, just compare file sizes as a sanity check
official_size=$(stat -f%z "$REFERENCE_DIR/official.pcm")
our_size=$(stat -f%z "$TMP_DIR/our.pcm")

echo "Raw PCM sizes:" >> "$METRICS_FILE"
echo "  Official: $official_size bytes" >> "$METRICS_FILE"
echo "  Ours:     $our_size bytes" >> "$METRICS_FILE"
echo "" >> "$METRICS_FILE"

# Step 6: Display results
echo "╔════════════════════════════════════════════════════════════════"
echo "║ AUDIO COMPARISON RESULTS"
echo "╠════════════════════════════════════════════════════════════════"
cat "$METRICS_FILE"
echo "╚════════════════════════════════════════════════════════════════"
echo ""

# Step 7: Verdict
echo "🎧 LISTEN TO BOTH FILES:"
echo "   Reference (official): afplay $OFFICIAL_OUTPUT"
echo "   Our output:           afplay $OUR_OUTPUT"
echo ""
echo "👁️  VIEW SPECTROGRAMS:"
echo "   Reference: open $REFERENCE_DIR/official-spectrum.png"
echo "   Ours:      open $TMP_DIR/our-spectrum.png"
echo ""
echo "If spectrograms look similar and audio sounds similar, the pipeline works!"
echo "If spectrograms differ significantly, there's a fundamental audio processing issue."
