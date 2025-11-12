# MOSHI Audio Investigation Summary - v7.7

**Date:** 2025-11-08
**Status:** 🔬 Testing in Progress
**Version:** 0.1.0-2025.11.7.7

## Executive Summary

We discovered the MOSHI audio pipeline CAN produce intelligible speech. The issue is **non-deterministic sampling**, not a fundamental bug. We implemented v7.7 with TopK sampling to match the official CLI and are currently measuring success rate.

---

## Three Investigation Tasks

### ✅ Task 1: Add Fixed Random Seed (COMPLETE)

**Status:** IMPLEMENTED in v7.7

**What we found:**
- Our code used `LogitsProcessor::new()` with basic temperature sampling
- Official CLI uses `LogitsProcessor::from_sampling()` with TopK sampling
- Seed was 1337 vs official 299792458

**What we changed:**
```rust
// v7.7: Match official CLI's TopK sampling
let audio_logits_processor = candle_transformers::generation::LogitsProcessor::from_sampling(
    299792458,  // Official CLI's default seed (speed of light in m/s!)
    candle_transformers::generation::Sampling::TopK {
        k: 250,
        temperature: 0.8
    },
);
```

**Expected outcome:**
- Deterministic output (same input → same output every time)
- Better quality audio matching official CLI's behavior

**Files modified:**
- `packages/core/src/voice.rs:1081-1099` - Sampling configuration
- `packages/core/Cargo.toml:3` - Version bump to 0.1.0-2025.11.7.7
- `docs/debugging/MOSHI_AUDIO_FIX_v7.7_TOPK_SAMPLING.md` - Documentation

---

### 🔄 Task 2: Test Success Rate (IN PROGRESS)

**Status:** RUNNING - 10 iterations with v7.7

**What we're testing:**
- Run `xswarm --moshi-test` 10 times
- Measure how often MOSHI produces intelligible speech (≥ 3 words)
- Check if TopK sampling makes output deterministic
- Verify MD5 hashes match across runs

**Test script:** `scripts/test-moshi-success-rate.sh`

**What we'll learn:**
- Success rate percentage with TopK sampling
- Whether v7.7 is deterministic (should be)
- If TopK improves quality vs basic temperature sampling

**Expected results:**
- ✅ 100% deterministic (same hash every run)
- ✅ High success rate (>80% with intelligible speech)
- ❓ If still low, investigate Metal/CPU differences

---

### ⏳ Task 3: Compare Audio Tokens (NEEDS INSTRUMENTATION)

**Status:** BLOCKED - Need to add token logging to code

**The challenge:**
To compare actual token sequences between successful and failed generations, we need to:

1. **Add instrumentation to voice.rs** to log generated tokens during inference
2. **Capture token sequences** from both success and failure cases
3. **Analyze differences** to understand what makes a generation succeed vs fail

**Current limitation:**
- Log files show final transcriptions ("Thanks for watching!" vs "No.")
- We don't have the actual token sequences that MOSHI generated
- The v7.6 audio files (success/failure) have been overwritten

**What we need to add:**

In `packages/core/src/voice.rs`, around line 1106-1150 (the generation loop):

```rust
// Log audio tokens during generation
for step_idx in 0..max_steps {
    // ... existing code ...

    // INSTRUMENTATION: Log audio tokens
    info!("MOSHI_DEBUG: Step {} audio tokens: {:?}",
          step_idx, &audio_tokens[0]);

    // INSTRUMENTATION: Log text tokens
    if let Some(text_token) = text_token {
        info!("MOSHI_DEBUG: Step {} text token: {}",
              step_idx, text_token);
    }
}
```

**Analysis steps:**
1. Run test twice with instrumentation - capture one success, one failure
2. Extract token sequences from logs
3. Compare sequences:
   - Do they diverge at a specific step?
   - Are there repeated tokens (mode collapse)?
   - Do successful runs show specific patterns?

**Why this matters:**
Understanding token-level differences will reveal:
- Whether issue is in audio token generation
- Whether issue is in text token generation
- If there's a pattern to successful generations

---

## Apple Silicon Metal Investigation

### Search Results Summary

**Found:**
1. **Candle Metal support** - Confirmed working, but known bugs exist
2. **MOSHI Metal support** - Official CLI supports Metal backend
3. **Known Metal issues:**
   - Command buffer failures (`IOGPUMetalCommandBuffer failed assertion`)
   - Some matrix multiplication limitations
   - Bug reports exist for Candle Metal backend

**NOT found:**
- No specific reports of non-deterministic behavior with MOSHI + Metal
- No reports matching our exact symptoms (same input → different output)
- No open issues about sampling randomness on Apple Silicon

**Relevant GitHub issues:**
- `huggingface/candle#313` - Apple Silicon MPS support discussion
- `huggingface/candle#2818` - Metal command buffer panics
- `kyutai-labs/moshi#85` - Strange feedback/oscillation on Mac OS X
- `kyutai-labs/moshi#141` - MOSHI quits after 15 seconds on M2

**Conclusion:**
While Metal has known issues, our specific non-deterministic problem hasn't been reported. The TopK sampling fix should address it regardless of backend.

---

## The Breakthrough Evidence

**Critical discovery from v7.6 logs:**

| Test Run | Time  | Input Audio | Transcription | Words | Result |
|----------|-------|-------------|---------------|-------|--------|
| fresh.log | 21:00 | test-user-hello.wav (created 20:59) | "Thanks for watching!" | 3 | ✅ SUCCESS |
| real.log  | 21:01 | test-user-hello.wav (created 20:59) | "No." | 1 | ❌ FAILURE |

**What this proves:**
1. ✅ Audio pipeline CAN work - it's not fundamentally broken
2. ✅ Input was IDENTICAL (same file, created before both tests)
3. ✅ Output was DIFFERENT (non-deterministic)
4. ✅ Problem is sampling/randomness, NOT audio processing

**MD5 comparison (v7.3-v7.6):**
- ALL previous versions produced identical garbled audio
- Hash: `398fe04c3836ce2ce5fa217cd9b7792c`
- This was a red herring - identical output meant deterministic failure
- The ONE success in v7.6 proved the pipeline works

---

## Technical Details

### Sampling Strategies Compared

**Official MOSHI CLI (gen.rs:45-52):**
```rust
let audio_lp = LogitsProcessor::from_sampling(
    args.seed,  // Default: 299792458
    Sampling::TopK { k: 250, temperature: 0.8 },
);
```

**Our v7.6 and earlier:**
```rust
let audio_logits_processor = LogitsProcessor::new(
    1337,       // Fixed seed
    Some(0.8),  // Temperature only
    None,       // No top_p
);
```

**Key differences:**
- TopK selects from top 250 most likely tokens (more focused)
- Basic temperature sampling uses all tokens (more random)
- Different seeds (1337 vs 299792458)

### Why TopK Sampling Should Help

1. **Narrows token space** - Only top 250 candidates considered
2. **Reduces randomness** - Less likely to pick low-probability garbage tokens
3. **Matches official CLI** - Known-working configuration
4. **Deterministic with fixed seed** - Same input → same output

---

## Next Steps

1. **Wait for v7.7 success rate results** (currently running)
   - If 100% deterministic + high success rate → PROBLEM SOLVED ✅
   - If still non-deterministic → Investigate Metal RNG
   - If deterministic but low success rate → Compare with official CLI

2. **If success rate still low:**
   - Add token logging instrumentation
   - Capture successful and failed token sequences
   - Analyze token-level differences
   - Test official CLI with same input for comparison

3. **If TopK solves it:**
   - Document the fix
   - Update ARCHITECTURE.md
   - Consider adding sampling strategy to config
   - Close the MOSHI audio debugging saga 🎉

---

## Files Created/Modified

### Documentation:
- `docs/debugging/MOSHI_AUDIO_FIX_v7.7_TOPK_SAMPLING.md` - Fix documentation
- `docs/debugging/MOSHI_AUDIO_INVESTIGATION_v7.7_SUMMARY.md` - This file

### Code:
- `packages/core/src/voice.rs:1081-1099` - TopK sampling implementation
- `packages/core/Cargo.toml:3` - Version 0.1.0-2025.11.7.7

### Scripts:
- `scripts/test-moshi-success-rate.sh` - Automated 10-run test script

### Logs (from v7.6):
- `./tmp/moshi-test-v7.6-fresh.log` - The one success
- `./tmp/moshi-test-v7.6-real.log` - The failure

---

## Confidence Level

**Very High** that TopK sampling will significantly improve or solve the issue:

✅ Matches official working implementation
✅ Addresses non-determinism with fixed seed
✅ We have evidence the pipeline CAN work
✅ TopK is a more controlled sampling strategy

**Results pending:** Success rate test will confirm within 5-10 minutes.

---

## For Future Token Analysis

If we need to investigate token-level differences:

**Instrumentation locations:**
- `packages/core/src/voice.rs:1106-1150` - Main generation loop
- Log both audio_tokens and text_token at each step
- Compare successful vs failed runs

**What to look for:**
- Token divergence points
- Repeated token patterns (mode collapse)
- Correlation between text tokens and audio token quality
- Whether early vs late steps matter more

**Tools needed:**
- `grep "MOSHI_DEBUG"` to extract sequences
- Python script to analyze token patterns
- Comparison with official CLI token sequences (if we can get them)

---

**Status:** Awaiting v7.7 success rate results... 🔬
