# AUDIO GARBLING ROOT CAUSE - FOUND!

## The Problem
- voice.rs produces GARBLED/backwards sounding audio
- Whisper API falsely reports "success" (false positive on corrupted audio)
- gen.rs produces CLEAR audio

## The ROOT CAUSE

**FORCED TEXT TOKEN LOGIC** in voice.rs (lines 1189-1270)

### Exact Locations in voice.rs

**Location 1: Lines 1189-1195** - Tokenize forced phrase
```rust
// v0.1.0-2025.11.6.2: Force MOSHI to say specific text for objective testing
// Tokenize test phrase: "hello world testing one two three"
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)
    .map_err(|e| anyhow::anyhow!("Failed to tokenize test phrase: {}", e))?;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
```

**Location 2: Lines 1255-1270** - Use forced tokens in LM step
```rust
let force_text_token = if forced_token_idx < text_tokens.len() {
    let token = text_tokens[forced_token_idx];
    forced_token_idx += 1;
    Some(token)
} else {
    None // After all tokens forced, let LM continue naturally
};

let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,  // ← THIS IS THE BUG
    None,
    conditions.as_ref(),
)?;
```

### Why This Breaks Audio

1. **Text-Audio Coupling**: When you force specific text tokens, the LM's internal state must follow a constrained path
2. **Audio Token Misalignment**: The audio tokens produced on this constrained path don't match the semantic content the MIMI codec was trained to expect
3. **Decoder Confusion**: MIMI decoder receives audio tokens that are semantically "out of phase" with the forced text
4. **Garbling Result**: Decoding valid-but-misaligned tokens produces garbled waveforms
5. **Whisper False Positive**: The garbled audio still has some speech-like characteristics, so Whisper detects "something" and reports success

### What gen.rs Does (CORRECT)

**gen.rs Line 110:**
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
    //                                   ^^^^
    //                             No forced token - LM generates freely
```

gen.rs lets MOSHI generate both text AND audio naturally, so they stay semantically aligned.

## THE FIX

Remove the forced text token logic entirely:

### Step 1: Delete lines 1189-1195
Delete this section:
```rust
// v0.1.0-2025.11.6.2: Force MOSHI to say specific text for objective testing
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)...;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
let forced_token_idx = 0;  // ← Also remove this initialization
```

### Step 2: Replace forced token logic (lines 1255-1270) with simple None

Replace:
```rust
let force_text_token = if forced_token_idx < text_tokens.len() {
    let token = text_tokens[forced_token_idx];
    forced_token_idx += 1;
    Some(token)
} else {
    None
};

let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,
    None,
    conditions.as_ref(),
)?;
```

With:
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    None,  // ← Always None - let LM generate naturally
    None,
    conditions.as_ref(),
)?;
```

### Step 3: Also simplify flush steps (lines 1332-1338)

Replace:
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &pad_codes,
    None, // No forced text token
    None, // No cross-attention
    conditions.as_ref(),
)?;
```

With same pattern (already correct).

## Expected Results After Fix

- Audio will be **CLEAR and INTELLIGIBLE** (not garbled)
- Audio will say whatever MOSHI naturally generates (not "hello world testing...")
- **Audio quality will match gen.rs** (excellent)
- Whisper transcription will be **accurate** to actual generated text
- No more backwards-sounding audio

## Files to Modify

- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/voice.rs`
  - Delete lines 1189-1195
  - Delete lines 1255-1270 (and surrounding variable tracking)
  - Replace with simple `None` in step_ call

## Why Whisper Reported "Success"

Whisper's confidence score is based on acoustic likelihood, not semantic accuracy:
- Garbled audio still has spectral features that look like speech
- Phoneme-like patterns exist even in corrupted audio
- So Whisper says "I detected something speech-like" = "success"
- But actual content is completely corrupted

This is why relying only on Whisper API for validation is dangerous - it can give false positives on semantically invalid audio.

