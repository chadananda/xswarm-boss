#!/bin/bash
# MOSHI Audio Success Rate Tester
# Runs MOSHI test multiple times to measure success rate
# v7.7 - Testing TopK sampling fix

set -e

OPENAI_API_KEY="${OPENAI_API_KEY}"
if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY environment variable not set"
    exit 1
fi

# Configuration
NUM_TESTS=10
LOG_DIR="./tmp/moshi-test-runs"
RESULTS_FILE="$LOG_DIR/success-rate-results.txt"

# Ensure clean state
mkdir -p "$LOG_DIR"
rm -f "$LOG_DIR"/*.log
rm -f "$RESULTS_FILE"

echo "🧪 MOSHI Success Rate Test - v7.7"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Running $NUM_TESTS test iterations..."
echo "Each test will:"
echo "  1. Generate audio with MOSHI"
echo "  2. Transcribe with OpenAI Whisper API"
echo "  3. Check if output is intelligible (>= 3 words)"
echo ""

# Track results
SUCCESSES=0
FAILURES=0
declare -a TRANSCRIPTIONS

echo "Building v7.7..."
cargo build --release 2>&1 | tail -5

echo ""
echo "Starting tests..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for i in $(seq 1 $NUM_TESTS); do
    RUN_LOG="$LOG_DIR/run-${i}.log"

    echo -n "Test $i/$NUM_TESTS... "

    # Clean previous output
    rm -f ./tmp/moshi-response.wav

    # Run test
    export OPENAI_API_KEY
    ./target/release/xswarm --moshi-test > "$RUN_LOG" 2>&1

    # Extract transcription from log
    TRANSCRIPTION=$(grep -A 1 "Transcription:" "$RUN_LOG" | tail -1 | sed 's/^.*"\(.*\)".*$/\1/' || echo "")

    # Count words
    WORD_COUNT=$(echo "$TRANSCRIPTION" | wc -w | tr -d ' ')

    # Store transcription
    TRANSCRIPTIONS[$i]="$TRANSCRIPTION"

    # Check success (>= 3 words indicates intelligible speech)
    if [ "$WORD_COUNT" -ge 3 ]; then
        echo "✅ SUCCESS ($WORD_COUNT words): \"$TRANSCRIPTION\""
        ((SUCCESSES++))
    else
        echo "❌ FAILURE ($WORD_COUNT words): \"$TRANSCRIPTION\""
        ((FAILURES++))
    fi

    # Save result to file
    echo "Run $i: $WORD_COUNT words - \"$TRANSCRIPTION\"" >> "$RESULTS_FILE"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTS SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total tests:    $NUM_TESTS"
echo "Successes:      $SUCCESSES"
echo "Failures:       $FAILURES"
echo "Success rate:   $(echo "scale=1; $SUCCESSES * 100 / $NUM_TESTS" | bc)%"
echo ""

# Show unique transcriptions
echo "Unique transcriptions:"
printf '%s\n' "${TRANSCRIPTIONS[@]}" | sort | uniq -c | while read count text; do
    echo "  $count times: \"$text\""
done

echo ""
echo "Full results saved to: $RESULTS_FILE"
echo "Individual logs saved to: $LOG_DIR/run-*.log"
echo ""

# Analyze for determinism
UNIQUE_COUNT=$(printf '%s\n' "${TRANSCRIPTIONS[@]}" | sort | uniq | wc -l | tr -d ' ')
if [ "$UNIQUE_COUNT" -eq 1 ]; then
    echo "✅ OUTPUT IS DETERMINISTIC (same result every time)"
else
    echo "⚠️  OUTPUT IS NON-DETERMINISTIC ($UNIQUE_COUNT different results)"
fi

# Calculate MD5 of outputs
echo ""
echo "MD5 hashes of generated audio:"
for i in $(seq 1 $NUM_TESTS); do
    if [ -f "./tmp/moshi-response-run${i}.wav" ]; then
        MD5=$(md5 -q "./tmp/moshi-response-run${i}.wav")
        echo "  Run $i: $MD5"
    fi
done

echo ""
if [ "$SUCCESSES" -gt 5 ]; then
    echo "🎉 Success rate is promising! Audio pipeline is working."
elif [ "$SUCCESSES" -gt 0 ]; then
    echo "⚠️  Success rate is low. Further debugging needed."
else
    echo "❌ No successes. The fix did not resolve the issue."
fi
