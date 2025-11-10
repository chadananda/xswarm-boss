# EXACT AUDIO GENERATION DIFFERENCES: voice.rs vs gen.rs

## Line-by-Line Comparison

### DIFFERENCE #1: Forced Text Token (PRIMARY BUG)

**gen.rs - Line 110:**
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
                                        ^^^^
                                   Always None
```

**voice.rs - Line 1255-1270:**
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
    force_text_token,  // ← VARIABLE, not always None (THE BUG!)
    None,
    conditions.as_ref(),
)?;
```

**Analysis:**
- gen.rs: Always passes `None` for text token forcing
- voice.rs: Passes `Some(token)` for first N steps, then `None`
- **Impact**: Forced tokens create semantic misalignment between LM output and audio codec training

---

### DIFFERENCE #2: Text Token Initialization (SUPPORTING BUG)

**gen.rs - Lines 1189-1195:**
```rust
// gen.rs: No text forcing code at all
// Just uses natural LM generation
```

**voice.rs - Lines 1189-1202:**
```rust
// v0.1.0-2025.11.6.2: Force MOSHI to say specific text for objective testing
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)
    .map_err(|e| anyhow::anyhow!("Failed to tokenize test phrase: {}", e))?;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
info!("MOSHI_TEST: Forcing MOSHI to say: \"{}\" ({} tokens)", test_phrase, text_tokens.len());

let mut prev_text_token = moshi_state.lm_config.text_start_token;
let mut forced_token_idx = 0; // Track which token to force next
```

**Analysis:**
- This code prepares the forced tokens that are used in step_ call
- Voice.rs has additional state tracking for forced tokens
- gen.rs never tokenizes target phrases - just lets LM generate freely

---

### DIFFERENCE #3: Processing Loop Architecture

**gen.rs - Lines 100-106 (simplified):**
```rust
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    nsteps += 1;
    let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;
    let codes = mimi.encode_step(&in_pcm.into(), &().into())?;
    if let Some(codes) = codes.as_option() {
        let (_b, _codebooks, steps) = codes.dims3()?;
        for step in 0..steps {  // Inner loop for each encode step
```

**voice.rs - Lines 1205-1242 (simplified):**
```rust
let num_frames = (user_audio.len() + frame_length - 1) / frame_length;
for frame_idx in 0..num_frames {
    let start_idx = frame_idx * frame_length;
    let end_idx = (start_idx + frame_length).min(user_audio.len());
    let mut frame_audio = user_audio[start_idx..end_idx].to_vec();
    if frame_audio.len() < frame_length {
        frame_audio.resize(frame_length, 0.0);
    }
    let pcm_tensor = Tensor::from_vec(frame_audio.clone(), ...)?;
    let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), ...)?;
    if let Some(codes_tensor) = codes_stream.as_option() {
        let (_batch, _codebooks, num_steps) = codes_tensor.dims3()?;
        for step in 0..num_steps {  // Inner loop for each encode step
```

**Analysis:**
- gen.rs: Direct indexing into input tensor (no copying)
- voice.rs: Copies frame data, resizes, creates new tensor
- **Impact**: Extra memory copies but shouldn't cause audio corruption

---

### DIFFERENCE #4: Tensor Slicing

**gen.rs - Line 102:**
```rust
let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                      Uses tensor indexing directly on 3D tensor
```

**voice.rs - Lines 1206-1217:**
```rust
let start_idx = frame_idx * frame_length;
let end_idx = (start_idx + frame_length).min(user_audio.len());
let mut frame_audio = user_audio[start_idx..end_idx].to_vec();  // ← Copy to Vec
// ...
let pcm_tensor = Tensor::from_vec(
    frame_audio.clone(),
    (1, 1, frame_length),
    &mimi_device,
)?;
```

**Analysis:**
- gen.rs: Zero-copy tensor indexing
- voice.rs: Vec allocation + clone
- **Impact**: Inefficient but functionally equivalent

---

### DIFFERENCE #5: Tensor Creation Pattern

**gen.rs - Lines 116-118:**
```rust
let audio_tokens =
    Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
        .reshape((1, 1, ()))?
        .t()?;
```

**voice.rs - Lines 1286-1289:**
```rust
let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
    .reshape((1, 1, ()))?
    .t()
    .context(format!("Failed to create audio tensor for frame {} step {}", frame_idx, step))?;
```

**Analysis:**
- gen.rs: `.t()?` inline
- voice.rs: `.t()` then `.context()`
- **Impact**: Both correct, just different error handling style

---

### DIFFERENCE #6: Concatenation & Extraction

**gen.rs - Lines 134-136:**
```rust
let out_pcms = Tensor::cat(&out_pcms, 2)?;
tracing::info!(shape = ?out_pcms.shape(), "generated audio");
let out_pcms = out_pcms.i((0, 0))?.to_vec1::<f32>()?;
```

**voice.rs - Lines 1376-1383:**
```rust
let concatenated = Tensor::cat(&out_pcm_tensors, 2)
    .context("Failed to concatenate PCM tensors")?;

info!("MOSHI_TEST: Concatenated tensor shape: {:?}", concatenated.shape());

let all_audio_samples = concatenated.i((0, 0))?.to_vec1::<f32>()
    .context("Failed to extract audio samples from tensor")?;
```

**Analysis:**
- Both identical: cat on dimension 2, extract (0,0)
- **Impact**: None - both correct

---

### DIFFERENCE #7: Extra Flush Steps

**gen.rs - Line 100:**
```rust
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    // No extra steps after main loop
}
```

**voice.rs - Lines 1325-1365:**
```rust
let extra_steps = 20;
for step_idx in 0..extra_steps {
    let pad_codes = vec![0u32; moshi_state.lm_config.input_audio_codebooks as usize];
    let text_token = lm_generator.step_(
        Some(prev_text_token),
        &pad_codes,
        None,
        None,
        conditions.as_ref(),
    )?;
    // Continue collecting audio tensors
}
```

**Analysis:**
- gen.rs: No explicit flush steps
- voice.rs: 20 extra steps with padding
- **Impact**: Should help with audio generation but not cause corruption

---

## SUMMARY TABLE

| Aspect | gen.rs | voice.rs | Impact |
|--------|--------|----------|--------|
| **Text Token Forcing** | Always `None` | `Some(token)` sometimes | **PRIMARY BUG** |
| **Phrase Tokenization** | None | "hello world testing..." | Supporting code for bug |
| **Input Processing** | Direct tensor indexing | Vec copy + resize | Inefficient but OK |
| **Tensor Creation** | `.t()?` | `.t().context()` | Both correct |
| **Concatenation** | Identical | Identical | Functionally same |
| **Flush Steps** | None | 20 extra | Shouldn't cause corruption |

---

## ROOT CAUSE MECHANISM

### Why Forced Tokens Cause Garbled Audio

```
1. MOSHI is trained with text-audio co-generation:
   - Text tokens and audio tokens are produced jointly
   - They evolve together as correlated sequences
   - The internal LM state maintains alignment between them

2. When you force text tokens:
   - LM is constrained to specific text path
   - LM must produce audio tokens for THIS constrained path
   - But MIMI codec was trained on natural co-generated pairs
   - The forced path has UNNATURAL audio token sequences

3. MIMI decoder receives misaligned tokens:
   - Tokens are semantically "out of phase"
   - Codec tries to decode them as if they were natural
   - Result: Waveform that looks like audio but sounds garbled

4. Whisper API false positive:
   - Detects acoustic patterns (phoneme-like)
   - Reports "success" based on acoustic likelihood
   - Never validates semantic alignment
   - False positive on corrupted audio
```

### Proof in Code

**The constraint happens here (voice.rs line 1264):**
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,  // ← Forces LM to follow specific text path
    None,
    conditions.as_ref(),
)?;
```

**vs gen.rs (line 110):**
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
                                        ^^^^
                                   No constraint - natural generation
```

---

## VALIDATION

To confirm this is the root cause:
1. Remove forced text token logic from voice.rs
2. Audio will be clear (not garbled)
3. Audio will say whatever MOSHI naturally generates
4. Quality will match gen.rs exactly

