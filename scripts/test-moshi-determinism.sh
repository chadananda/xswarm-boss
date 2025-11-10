#!/bin/bash
# Test MOSHI determinism - run 3 times, check if transcriptions are consistent
# If consistent → MOSHI is deterministic, we can establish baseline
# If inconsistent → Generation is broken

set -e

OPENAI_API_KEY="${OPENAI_API_KEY}"
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY environment variable not set"
    exit 1
fi

echo "🧪 MOSHI DETERMINISM TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Testing if seeded MOSHI generation is deterministic..."
echo "Running 3 iterations with same seed (299792458)"
echo ""

# Clean up
rm -rf ./tmp/determinism-test
mkdir -p ./tmp/determinism-test

# Run 3 times
for i in 1 2 3; do
    echo "Run $i/3..."

    # Clear cache to force fresh generation
    rm -rf ./tmp/experiments ./tmp/moshi-response.wav ./tmp/test-user-hello.wav

    # Generate
    ./target/release/xswarm --moshi-test > ./tmp/determinism-test/run-$i.log 2>&1

    # Copy output
    if [ -f ./tmp/moshi-response.wav ]; then
        cp ./tmp/moshi-response.wav ./tmp/determinism-test/output-$i.wav
    else
        echo "ERROR: No output generated on run $i"
        exit 1
    fi

    # Extract transcription from log
    grep "Transcription:" ./tmp/determinism-test/run-$i.log | \
        sed 's/.*Transcription:[[:space:]]*//' | \
        sed 's/"//g' > ./tmp/determinism-test/transcription-$i.txt

    echo "  Generated: $(cat ./tmp/determinism-test/transcription-$i.txt)"
done

echo ""
echo "╔════════════════════════════════════════════════════════════════"
echo "║ DETERMINISM RESULTS"
echo "╠════════════════════════════════════════════════════════════════"

# Compare transcriptions
trans1=$(cat ./tmp/determinism-test/transcription-1.txt)
trans2=$(cat ./tmp/determinism-test/transcription-2.txt)
trans3=$(cat ./tmp/determinism-test/transcription-3.txt)

echo "║ Run 1: $trans1"
echo "║ Run 2: $trans2"
echo "║ Run 3: $trans3"
echo "╠════════════════════════════════════════════════════════════════"

if [ "$trans1" = "$trans2" ] && [ "$trans2" = "$trans3" ]; then
    echo "║ ✅ DETERMINISTIC: All 3 runs produced identical transcriptions"
    echo "║"
    echo "║ Baseline established: \"$trans1\""
    echo "║"
    echo "║ Next steps:"
    echo "║ 1. Listen to output: afplay ./tmp/determinism-test/output-1.wav"
    echo "║ 2. If it sounds garbled but transcribes correctly:"
    echo "║    → Whisper is hallucinating (unreliable for testing)"
    echo "║ 3. If it sounds clear and matches transcription:"
    echo "║    → Audio pipeline is working correctly!"
else
    echo "║ ❌ NON-DETERMINISTIC: Runs produced different transcriptions"
    echo "║"
    echo "║ This indicates a problem with:"
    echo "║ - Random seed not being applied correctly"
    echo "║ - Non-deterministic operations in MOSHI generation"
    echo "║ - Different code paths being taken between runs"
fi

echo "╚════════════════════════════════════════════════════════════════"
echo ""

# Compare audio files at binary level
echo "🔬 Binary comparison of audio files..."
if cmp -s ./tmp/determinism-test/output-1.wav ./tmp/determinism-test/output-2.wav; then
    echo "✅ output-1.wav and output-2.wav are IDENTICAL (byte-for-byte)"
else
    echo "❌ output-1.wav and output-2.wav DIFFER at binary level"
fi

if cmp -s ./tmp/determinism-test/output-2.wav ./tmp/determinism-test/output-3.wav; then
    echo "✅ output-2.wav and output-3.wav are IDENTICAL (byte-for-byte)"
else
    echo "❌ output-2.wav and output-3.wav DIFFER at binary level"
fi

echo ""
echo "📁 Results saved to: ./tmp/determinism-test/"
echo "   Logs: run-{1,2,3}.log"
echo "   Audio: output-{1,2,3}.wav"
echo "   Transcriptions: transcription-{1,2,3}.txt"
