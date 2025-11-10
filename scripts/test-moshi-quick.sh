#!/bin/bash
# Quick MOSHI test script - fast iteration
# Usage: ./scripts/test-moshi-quick.sh

set -e

echo "🧪 QUICK MOSHI TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Configuration
INPUT_AUDIO="./tmp/test-user-hello.wav"
OUTPUT_AUDIO="./tmp/quick-moshi-output.wav"
TEST_NUM=${1:-1}  # Allow passing test number as argument

# MOSHI CLI paths
MOSHI_DIR="./packages/moshi/moshi-cli"
LM_MODEL="$HOME/.cache/huggingface/hub/models--kyutai--moshiko-pytorch-bf16/snapshots/*/model.safetensors"
LM_CONFIG="$MOSHI_DIR/lm_config.toml"
MIMI_MODEL="$HOME/.cache/huggingface/hub/models--kyutai--mimi/snapshots/*/model.safetensors"
TEXT_TOKENIZER="$HOME/.cache/huggingface/hub/models--kyutai--moshiko-pytorch-bf16/snapshots/*/tokenizer_spm_32k_3.model"

# Expand wildcards
LM_MODEL=$(echo $LM_MODEL)
MIMI_MODEL=$(echo $MIMI_MODEL)
TEXT_TOKENIZER=$(echo $TEXT_TOKENIZER)

echo "1️⃣  Building MOSHI CLI (if needed)..."
cd $MOSHI_DIR
if [ ! -f "../../target/release/moshi-cli" ]; then
    cargo build --release 2>&1 | grep -E "(Compiling|Finished)" | tail -5
fi
cd -
echo "   ✅ MOSHI CLI ready"
echo

echo "2️⃣  Running MOSHI CLI..."
echo "   Input: $INPUT_AUDIO"
echo "   Output: $OUTPUT_AUDIO"
echo

./target/release/moshi-cli gen \
    --lm-model-file "$LM_MODEL" \
    --lm-config-file "$LM_CONFIG" \
    --mimi-model-file "$MIMI_MODEL" \
    --audio-input-file "$INPUT_AUDIO" \
    --text-tokenizer "$TEXT_TOKENIZER" \
    --audio-output-file "$OUTPUT_AUDIO" \
    --seed 299792458

echo
echo "3️⃣  Versioning output..."
cp "$OUTPUT_AUDIO" "./tmp/moshi-quick-test${TEST_NUM}.wav"
VERSIONED_FILE="./tmp/moshi-quick-test${TEST_NUM}.wav"
echo "   ✅ Saved to: $VERSIONED_FILE"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ TEST COMPLETE!"
echo
echo "🎧 Listen to output:"
echo "   afplay $VERSIONED_FILE"
echo
echo "📊 Check MD5:"
MD5_HASH=$(md5 -q "$VERSIONED_FILE")
echo "   $MD5_HASH"
echo
echo "📏 File size:"
ls -lh "$VERSIONED_FILE" | awk '{print "   " $5 " - " $9}'
