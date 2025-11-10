# CRITICAL AUDIO GENERATION COMPARISON: voice.rs vs gen.rs

## EXECUTIVE SUMMARY

**THE PROBLEM: Garbled/backwards audio in voice.rs despite Whisper API "success"**

Found a **CRITICAL DIFFERENCE** in how the condition is extracted and passed to LM step:

- **gen.rs (WORKING)**: Extracts condition object directly, passes it as-is
- **voice.rs (BROKEN)**: Wraps condition in Option, potentially corrupting it

---

## SIDE-BY-SIDE COMPARISON

### 1. CONDITION SETUP - Lines 55-69 (gen.rs) vs 1175-1187 (voice.rs)

#### gen.rs (WORKING) - Lines 55-69
```rust
let conditions = match lm_model.condition_provider() {
    None => None,
    Some(cp) => {
        let conditions = if args.cfg_alpha.is_some() {
            use moshi::conditioner::Condition::AddToInput;
            let AddToInput(c1) = cp.condition_lut("description", "very_good")?;
            let AddToInput(c2) = cp.condition_lut("description", "very_bad")?;
            AddToInput(Tensor::cat(&[c1, c2], 0)?)
        } else {
            cp.condition_lut("description", "very_good")?  // ← Direct return
        };
        tracing::info!(?conditions, "generated conditions");
        Some(conditions)  // ← Wrapped in Some()
    }
};
```

#### voice.rs (BROKEN) - Lines 1175-1187
```rust
let conditions = match moshi_state.lm_model.condition_provider() {
    None => {
        info!("MOSHI_TEST: No condition provider available");
        None
    }
    Some(cp) => {
        use moshi::conditioner::Condition::AddToInput;
        let cond = cp.condition_lut("description", "very_good")
            .context("Failed to create 'very_good' condition")?;
        info!("MOSHI_TEST: Using 'very_good' quality condition (CRITICAL FOR AUDIO QUALITY)");
        Some(cond)  // ← Same wrapping
    }
};
```

**Status**: Both look similar here - probably not the issue.

---

### 2. LM GENERATOR STEP CALL - Line 110 (gen.rs) vs Line 1264 (voice.rs)

#### gen.rs (WORKING) - Line 110
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
```

#### voice.rs (BROKEN) - Lines 1264-1270
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,         // ← DIFFERENCE #1: voice.rs uses force_text_token
    None,
    conditions.as_ref(),      // ← Both use conditions.as_ref()
).context(format!("LM step failed at frame {} step {}", frame_idx, step))?;
```

**KEY DIFFERENCE #1: Forced Text Token**
- **gen.rs**: Uses `None` for the forced text token (let LM generate naturally)
- **voice.rs**: Uses `force_text_token` which can be `Some(token)` or `None`

This could corrupt the LM's internal state during generation!

---

### 3. AUDIO TOKEN EXTRACTION - Lines 114-123 (gen.rs) vs 1275-1311 (voice.rs)

#### gen.rs (WORKING) - Lines 114-123
```rust
if let Some(audio_tokens) = state.last_audio_tokens() {
    let audio_tokens =
        Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
            .reshape((1, 1, ()))?
            .t()?;
    let out_pcm = mimi.decode_step(&audio_tokens.into(), &().into())?;
    if let Some(out_pcm) = out_pcm.as_option() {
        out_pcms.push(out_pcm.clone());
    }
}
```

**Key steps:**
1. `Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?` - Create tensor from slice
2. `.reshape((1, 1, ()))?` - Reshape to (1, 1, n)
3. `.t()?` - Transpose

#### voice.rs (BROKEN) - Lines 1286-1304
```rust
let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
    .reshape((1, 1, ()))?
    .t()  // ← Returns Result, not unwrapped!
    .context(format!("Failed to create audio tensor for frame {} step {}", frame_idx, step))?;
```

**KEY DIFFERENCE #2: Transpose Error Handling**
- **gen.rs**: `.t()?` - Correctly unwraps/propagates error
- **voice.rs**: `.t()` then `.context()` - This is CORRECT

Wait, let me check more carefully...

---

### 4. TENSOR CREATION - CRITICAL LOOK

Let me examine the tensor creation more closely:

#### gen.rs (WORKING)
```rust
let audio_tokens =
    Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
        .reshape((1, 1, ()))?
        .t()?;
```

- Input: `&audio_tokens[..generated_audio_codebooks]` - a **reference to the slice**
- Shape after new(): dimension based on slice length
- reshape to (1, 1, n)
- transpose

#### voice.rs (BROKEN)
```rust
let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
    .reshape((1, 1, ()))?
    .t()
    .context(format!("Failed to create audio tensor...", frame_idx, step))?;
```

- Input: `audio_tokens_slice` - same reference
- Same reshape and transpose

**Both look identical in tensor handling**

---

### 5. DECODING STEP - Lines 119-121 (gen.rs) vs 1299-1304 (voice.rs)

#### gen.rs (WORKING) - Line 119
```rust
let out_pcm = mimi.decode_step(&audio_tokens.into(), &().into())?;
if let Some(out_pcm) = out_pcm.as_option() {
    out_pcms.push(out_pcm.clone());
}
```

#### voice.rs (BROKEN) - Lines 1299-1304
```rust
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())
    .context(format!("MIMI decode failed for frame {} step {}", frame_idx, step))?;

if let Some(pcm_tensor) = decoded.as_option() {
    out_pcm_tensors.push(pcm_tensor.clone());
    ...
}
```

**STATUS**: Functionally identical, just different variable names.

---

### 6. CONCATENATION & EXTRACTION - Lines 134-136 (gen.rs) vs 1376-1383 (voice.rs)

#### gen.rs (WORKING) - Lines 134-136
```rust
let out_pcms = Tensor::cat(&out_pcms, 2)?;
tracing::info!(shape = ?out_pcms.shape(), "generated audio");
let out_pcms = out_pcms.i((0, 0))?.to_vec1::<f32>()?;
```

#### voice.rs (BROKEN) - Lines 1376-1383
```rust
let concatenated = Tensor::cat(&out_pcm_tensors, 2)
    .context("Failed to concatenate PCM tensors")?;

info!("MOSHI_TEST: Concatenated tensor shape: {:?}", concatenated.shape());

let all_audio_samples = concatenated.i((0, 0))?.to_vec1::<f32>()
    .context("Failed to extract audio samples from tensor")?;
```

**STATUS**: Functionally identical - concatenate on dimension 2, extract (0,0).

---

## CRITICAL DIFFERENCE FOUND!

### THE FORCED TEXT TOKEN BUG (Difference #1)

**Line 1255-1270 in voice.rs:**
```rust
// Step 2b: Run LM step with audio codes, forcing specific text tokens
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
    force_text_token,  // ← FORCING TEXT TOKENS
    None,
    conditions.as_ref(),
)?;
```

**This is UNIQUE to voice.rs and NOT in gen.rs!**

gen.rs always passes `None` for forced text token:
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
```

### WHY THIS CAUSES GARBLED AUDIO

When you force specific text tokens:
1. The LM's internal state gets constrained to follow the forced path
2. This path might not match what the audio codec expects
3. The audio tokens produced are semantically misaligned with what MIMI expects
4. Result: MIMI decodes them into garbled/reversed sounding audio
5. Whisper API gives false positive ("success") because it's still detecting *something* as speech

The forced text tokens in voice.rs are:
```rust
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)
    .map_err(|e| anyhow::anyhow!("Failed to tokenize test phrase: {}", e))?;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
```

**But gen.rs doesn't force ANY text tokens - it lets MOSHI generate naturally!**

---

## SECONDARY DIFFERENCES

### 1. Frame-based vs Window-based Processing

**gen.rs (Window-based):** Line 100-102
```rust
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    nsteps += 1;
    let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;
    let codes = mimi.encode_step(&in_pcm.into(), &().into())?;
```

- Processes fixed 1920-sample windows
- Simple index-based slicing

**voice.rs (Frame-based):** Lines 1205-1208
```rust
for frame_idx in 0..num_frames {
    let start_idx = frame_idx * frame_length;
    let end_idx = (start_idx + frame_length).min(user_audio.len());
    let mut frame_audio = user_audio[start_idx..end_idx].to_vec();
```

- Computes frame_length from MIMI config
- Clones audio data (extra memory copy!)
- Pads last frame if needed

**Impact**: Frame-based should work fine, but the cloning adds memory pressure.

### 2. Extra Flush Steps

**gen.rs**: Only processes real audio frames

**voice.rs** (Lines 1325-1365): Adds 20 extra flush steps
```rust
let extra_steps = 20;
for step_idx in 0..extra_steps {
    let pad_codes = vec![0u32; moshi_state.lm_config.input_audio_codebooks as usize];
    // ... continues LM generation with padding
}
```

**Impact**: This is actually good for flushing audio, but shouldn't cause garbling.

---

## ROOT CAUSE DIAGNOSIS

### PRIMARY ISSUE: Forced Text Tokens
- **Location**: Lines 1255-1270 in voice.rs
- **Symptom**: Garbled, backwards-sounding audio
- **Cause**: Forcing text tokens constrains LM output, misaligning audio tokens with codec expectations
- **Fix**: Remove forced text token logic, let MOSHI generate naturally like gen.rs does

### FALSE POSITIVE WHISPER DETECTION
- Whisper API detects the garbled audio as "valid speech" because:
  - The waveform still has speech-like characteristics (phoneme patterns)
  - Garbling doesn't destroy all phonemic information
  - Whisper can recognize *something* even in corrupted audio

### WHY gen.rs WORKS
1. No text token forcing - LM generates freely
2. Audio tokens naturally align with trained codec behavior
3. MIMI decodes properly semantically-aligned tokens
4. Result: Clear, intelligible speech

---

## IMPLEMENTATION NOTES

### audio_tokens_slice handling
Both files correctly slice to `generated_audio_codebooks`:
```rust
// Both do this:
let audio_tokens_slice = &audio_tokens[..generated_audio_codebooks.min(audio_tokens.len())];
```

### Conditions as_ref()
Both correctly pass conditions:
```rust
conditions.as_ref()  // Works for Option<T>
```

### Tensor operations
Both use identical tensor patterns:
```rust
Tensor::new(slice, device)?
    .reshape((1, 1, ()))?
    .t()?
```

---

## RECOMMENDATION

**DELETE THE FORCED TEXT TOKEN LOGIC** (lines 1189-1195, 1255-1270 in voice.rs)

Instead, follow gen.rs pattern:
```rust
// REMOVE THIS:
// let test_phrase = "hello world testing...";
// let text_tokens = tokenize(test_phrase);
// ...
// let force_text_token = if forced_token_idx < text_tokens.len() { Some(...) } else { None };
// lm_generator.step_(..., force_text_token, ...);

// USE THIS (gen.rs pattern):
lm_generator.step_(
    Some(prev_text_token),
    &codes,
    None,  // ← No forced token
    None,
    conditions.as_ref(),
)?;
```

This will allow MOSHI to generate audio and text naturally without semantic constraint corruption.

---

## TEST PREDICTION

After removing forced text token logic:
- Audio will be **clear and intelligible** (not garbled)
- Audio may not say "hello world testing one two three" (it will say something else)
- But the audio quality will be **excellent** and match gen.rs output
- Whisper transcription will be **accurate** to what MOSHI actually generated

