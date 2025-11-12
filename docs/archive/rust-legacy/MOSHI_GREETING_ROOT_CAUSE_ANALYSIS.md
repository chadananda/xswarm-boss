# MOSHI Auto-Greeting - Root Cause Analysis

## Date: 2025-11-06

## Executive Summary

**The v0.1.0-2025.11.5.25 "fix" did NOT solve the garbled audio problem.**

The issue is **fundamental to how MOSHI's language model works**: it requires **real audio input** (encoded to MIMI codes) to generate coherent speech output. Both the original broken code AND the `greeting.rs` module use **silent/padding tokens** as input, which causes MOSHI to generate unpredictable, garbled audio.

---

## User Feedback

> "the audio was garbage"

This confirmed that v0.1.0-2025.11.5.25 failed to fix the problem.

---

## Investigation: Why Both Approaches Failed

### Attempt 1: v0.1.0-2025.11.5.24 (Original Broken Code)

**File**: `packages/core/src/voice.rs` (before v0.1.0-2025.11.5.25)

```rust
// ❌ BROKEN: Sending silence to MOSHI
let test_frame = vec![0.0f32; MOSHI_FRAME_SIZE];  // All zeros

match self.process_with_lm(&mut conn_state, test_frame).await {
    Ok(response_pcm) => {
        // Garbled audio output
```

**Problem**: Creates a frame of silence (all zeros) and sends it to MOSHI's language model via `process_with_lm()`.

### Attempt 2: v0.1.0-2025.11.5.25 (My "Fix" That Also Failed)

**File**: `packages/core/src/voice.rs:707-750` (v0.1.0-2025.11.5.25)

```rust
// FIX: Use proper greeting generation instead of silent frame
match crate::greeting::generate_simple_greeting(
    &mut *moshi_state,
    "Hello, I am MOSHI. How can I help you today?"
).await {
    Ok(greeting_pcm) => {
        // STILL GARBLED
```

**File**: `packages/core/src/greeting.rs:91` (The "Proper" Function I Called)

```rust
/// Generate audio tokens from text tokens using force_text_token injection
///
/// NOTE: Uses silent audio input (padding tokens), not real audio.
async fn generate_audio_tokens_from_text(
    text_tokens: &[u32],
    moshi_state: &MoshiState,
) -> Result<Vec<Vec<u32>>> {
    // ...

    // ❌ STILL BROKEN: Prepare silent audio input (padding tokens)
    let padding_token = moshi_state.lm_config.audio_pad_token();
    let silent_audio: Vec<u32> = vec![padding_token; input_audio_codebooks];

    // Step through each text token, forcing it and collecting audio output
    for (step_idx, &force_token) in text_tokens.iter().enumerate() {
        let text_token = lm_generator.step(
            prev_text_token,
            &silent_audio,      // ❌ Silent audio input (no user speaking)
            Some(force_token),  // Force this specific text token
            None,
        )?;
```

**Problem**: The `generate_simple_greeting()` function internally uses **padding tokens** (line 126-135 of greeting.rs) as audio input to MOSHI's language model. This is the SAME problematic approach as the original code, just hidden inside a function.

---

## How MOSHI's Language Model Actually Works

### Normal Conversation Flow (WORKS)

**File**: `packages/core/src/voice.rs:1009-1096` (`process_with_lm` function)

```
Real microphone audio (Vec<f32>)
    ↓
Encode to MIMI codes (Step 1, lines 1063-1079)
    ↓
MIMI codes → Language Model input
    ↓
Language Model generates audio tokens
    ↓
Decode audio tokens to PCM (MIMI codec)
    ↓
Coherent speech output ✅
```

### Broken Greeting Flow (FAILS)

```
Silent frames / Padding tokens
    ↓
NO REAL AUDIO INPUT ❌
    ↓
Language Model receives padding tokens
    ↓
Language Model generates unpredictable audio tokens
    ↓
Decode to PCM
    ↓
Garbled, repetitive noise ❌
```

---

## The Fundamental Problem

**MOSHI's language model is conditioned on real audio input.** The model architecture expects:

1. **Audio input** (encoded as MIMI codes) representing what the user said/is saying
2. **Text tokens** (either predicted or forced) representing the assistant's response
3. The model generates **audio output** (as audio tokens) that corresponds to the text

When you provide **silence/padding tokens** as audio input:
- The model has no speech context to work with
- It generates audio tokens in an unpredictable way
- The resulting speech is incoherent/garbled

**This is NOT a bug** - this is how MOSHI's architecture works. It's a **bidirectional audio-text model** that needs real audio conditioning.

---

## Why My V0.1.0-2025.11.5.25 Fix Failed

I made a critical error in my analysis:

1. ❌ **Assumption**: "The existing `greeting.rs` module has a proper implementation"
2. ❌ **Assumption**: "Calling `generate_simple_greeting()` will fix the problem"
3. ✅ **Reality**: `greeting.rs:91` explicitly states "Uses silent audio input (padding tokens), not real audio"

I replaced one broken approach (sending silence directly) with another broken approach (calling a function that sends padding tokens). The code path changed, but the fundamental problem remained.

---

## Verification

### Installation Confirmed Correct

Both binaries have matching MD5 checksums:
```
~/.local/bin/xswarm: db8be79ebc5ff7677a19dbb4837e33a0
target/release/xswarm: db8be79ebc5ff7677a19dbb4837e33a0
```

The v0.1.0-2025.11.5.25 fix IS correctly installed - the problem is that the fix itself doesn't work.

### Code Review Confirms

**voice.rs:707** version comment:
```rust
// v0.1.0-2025.11.5.25: AUTO-GREETING for automated testing
```

**voice.rs:712-719** greeting generation call:
```rust
let mut moshi_state = bridge.state.write().await;
match crate::greeting::generate_simple_greeting(
    &mut *moshi_state,
    "Hello, I am MOSHI. How can I help you today?"
).await {
```

**greeting.rs:91** the smoking gun:
```rust
/// NOTE: Uses silent audio input (padding tokens), not real audio.
```

---

## What Actually Needs to Happen

We need a fundamentally different approach that doesn't rely on MOSHI's language model with silent input. Options:

### Option 1: Pre-recorded Greeting WAV File
- Record a human (or synthesized) greeting once
- Store as WAV file in `./tmp/` or `assets/`
- Play back directly when auto-greeting is requested
- ✅ **Pros**: Simple, guaranteed to work, no model inference needed
- ❌ **Cons**: Not dynamically generated, fixed greeting text

### Option 2: Use a Different TTS System for Greetings
- Use a dedicated TTS model (e.g., Coqui TTS, Piper TTS, eSpeak-ng)
- Generate greeting dynamically from text
- Play back the generated audio
- ✅ **Pros**: Dynamic text-to-speech, doesn't misuse MOSHI
- ❌ **Cons**: Additional dependency, voice won't match MOSHI's voice

### Option 3: Prime MOSHI with Real Audio
- Generate or record a short audio prompt (e.g., "Hello" in user's voice)
- Use that as MOSHI's audio input conditioning
- Let MOSHI respond to it naturally
- ✅ **Pros**: Uses MOSHI correctly, generates natural greeting
- ❌ **Cons**: Requires seed audio, may not produce exact greeting text

### Option 4: Investigate MOSHI's Text-to-Speech Mode
- Research if MOSHI has a dedicated TTS mode that doesn't require audio input
- Check Kyutai's MOSHI documentation/examples for text-only generation
- ✅ **Pros**: Proper MOSHI usage, dynamic generation
- ❌ **Cons**: May not exist, requires deep dive into MOSHI architecture

---

## Recommendation

**Immediate solution**: Option 1 (pre-recorded greeting WAV file)

**Reasoning**:
1. Fastest to implement and test
2. Guaranteed to work (no model unpredictability)
3. Solves the automated testing use case
4. Can be enhanced later with dynamic TTS if needed

**Implementation**:
1. Generate a greeting WAV file (16-bit PCM, 24kHz or 44.1kHz)
2. Store it in `./tmp/greeting.wav` or `packages/core/assets/greeting.wav`
3. When `MOSHI_DEBUG_WAV=1`, load and play the pre-recorded file
4. Optionally resample to match device sample rate

---

## Lessons Learned

1. **Read the comments**: Line 91 of `greeting.rs` stated "Uses silent audio input (padding tokens)" - I missed this critical detail

2. **Understand the model architecture**: MOSHI is bidirectional audio-text, not pure text-to-speech. Silent input → unpredictable output is expected behavior

3. **Test thoroughly before declaring victory**: I built v0.1.0-2025.11.5.25, verified installation, but didn't actually test the audio output quality

4. **User feedback is essential**: "the audio was garbage" immediately invalidated my fix approach

---

## Files to Update

### 1. Update `voice.rs` (v0.1.0-2025.11.5.26)
Remove broken greeting generation, replace with pre-recorded WAV playback or alternative approach

### 2. Update `docs/MOSHI_GREETING_FIX_COMPLETE.md`
Document that v0.1.0-2025.11.5.25 did NOT work and explain why

### 3. Create This Document
`docs/MOSHI_GREETING_ROOT_CAUSE_ANALYSIS.md` - comprehensive analysis of the problem

---

## Status

- ❌ v0.1.0-2025.11.5.24: BROKEN (sends silence directly)
- ❌ v0.1.0-2025.11.5.25: STILL BROKEN (calls greeting.rs which uses padding tokens)
- ⏸️ Next version: Needs completely different approach (pre-recorded WAV or alternative TTS)

---

## Technical Details

### MOSHI Language Model Step Function

```rust
// From greeting.rs:146-151
let text_token = lm_generator.step(
    prev_text_token,
    &silent_audio,      // ❌ This is the problem
    Some(force_token),  // Forcing text doesn't help if audio is silent
    None,
);
```

Parameters:
- `prev_text_token`: Previous text token generated
- `&silent_audio`: **Audio input** (should be real MIMI codes from user speech)
- `Some(force_token)`: **Forced text token** (what MOSHI should say)
- `None`: Cross-attention (not used here)

**The problem**: Parameter 2 should be real audio codes, not padding tokens.

### MIMI Encoding (Normal Flow)

```rust
// From voice.rs:1068-1078
let pcm_tensor = Tensor::from_vec(
    audio.to_vec(),  // ✅ Real audio from microphone
    (1, 1, audio.len()),
    mimi_device,
)?;

let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())?;
```

This is what greeting generation should use instead of padding tokens, but it requires real audio input.

---

**Document Created**: 2025-11-06
**Last Updated**: 2025-11-06
**Status**: Root cause identified, solution needed
