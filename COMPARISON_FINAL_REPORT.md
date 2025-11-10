# FINAL COMPARISON REPORT: voice.rs vs gen.rs Audio Generation

## QUICK ANSWER

**ROOT CAUSE OF GARBLED AUDIO:**

The forced text token logic in voice.rs (lines 1189-1270) forces the LM to output specific text tokens while generating audio. This creates semantic misalignment between the text and audio tokens, causing MIMI to decode corrupted waveforms.

**THE BUG:** Line 1264-1270 in voice.rs
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,  // ← THE BUG (should always be None like gen.rs)
    None,
    conditions.as_ref(),
)?;
```

**vs CORRECT (gen.rs line 110):**
```rust
prev_text_token = state.step_(
    Some(prev_text_token), &codes, None, None, conditions.as_ref()
)?;
// Always None - natural generation
```

---

## DETAILED FILE ANALYSIS

### File 1: packages/core/src/voice.rs (BROKEN)

**Key Sections:**

**Lines 1189-1195: Tokenize forced phrase**
```rust
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)?;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
info!("MOSHI_TEST: Forcing MOSHI to say: \"{}\" ({} tokens)", test_phrase, text_tokens.len());
let mut prev_text_token = moshi_state.lm_config.text_start_token;
let mut forced_token_idx = 0;  // Track which token to force next
```

**Status:** PROBLEMATIC - This code doesn't exist in gen.rs

---

**Lines 1200-1210: Frame processing loop**
```rust
let mut out_pcm_tensors: Vec<Tensor> = Vec::new();
let mut forced_token_idx = 0; // Track which token to force next

for frame_idx in 0..num_frames {
    let start_idx = frame_idx * frame_length;
    let end_idx = (start_idx + frame_length).min(user_audio.len());
    let mut frame_audio = user_audio[start_idx..end_idx].to_vec();
    
    if frame_audio.len() < frame_length {
        frame_audio.resize(frame_length, 0.0);
    }
```

**Status:** OK but slightly different from gen.rs approach (copies data instead of tensor slicing)

---

**Lines 1241-1248: Extract codes from encode_step**
```rust
let codes = codes_tensor.i((0, .., 0))?.to_vec1::<u32>()?
    .context("Failed to convert codes to vec")?;

if frame_idx == 0 && step < 3 {
    info!("MOSHI_TEST: Frame {} Step {}: Extracted {} codes", frame_idx, step, codes.len());
}
```

**vs gen.rs Line 107-108:**
```rust
let codes = codes.i((0, .., 0))?.to_vec1::<u32>()?;
```

**Status:** Same extraction logic, just with logging

---

**Lines 1255-1270: THE CRITICAL BUG**
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
    force_text_token,  // ← FORCES TEXT TOKEN (THE BUG!)
    None,
    conditions.as_ref(),
)?;
```

**vs gen.rs Line 109-110:**
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
                                        ^^^^
                                   Always None - no forcing
```

**Status:** CRITICAL DIFFERENCE - This is the root cause of audio garbling

---

**Lines 1286-1304: Audio tensor creation and decode**
```rust
let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
    .reshape((1, 1, ()))?
    .t()
    .context(format!("Failed to create audio tensor for frame {} step {}", frame_idx, step))?;

let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;

if let Some(pcm_tensor) = decoded.as_option() {
    out_pcm_tensors.push(pcm_tensor.clone());
}
```

**vs gen.rs Lines 116-121:**
```rust
let audio_tokens = Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
    .reshape((1, 1, ()))?
    .t()?;
let out_pcm = mimi.decode_step(&audio_tokens.into(), &().into())?;
if let Some(out_pcm) = out_pcm.as_option() {
    out_pcms.push(out_pcm.clone());
}
```

**Status:** Functionally identical (just different variable names and error handling style)

---

**Lines 1325-1365: Extra flush steps**
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
    
    prev_text_token = text_token;
    
    if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
        let generated_codebooks = moshi_state.lm_config.generated_audio_codebooks as usize;
        let audio_tokens_slice = &audio_tokens[..generated_codebooks.min(audio_tokens.len())];
        
        let audio_tensor = Tensor::new(audio_tokens_slice, &mimi_device)?
            .reshape((1, 1, ()))?
            .t()?;
        
        let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;
        
        if let Some(pcm_tensor) = decoded.as_option() {
            out_pcm_tensors.push(pcm_tensor.clone());
        }
    }
}
```

**vs gen.rs:** No flush steps after main loop

**Status:** Not in gen.rs but uses `None` for forced token (correct)

---

**Lines 1376-1383: Tensor concatenation and extraction**
```rust
let concatenated = Tensor::cat(&out_pcm_tensors, 2)
    .context("Failed to concatenate PCM tensors")?;

info!("MOSHI_TEST: Concatenated tensor shape: {:?}", concatenated.shape());

let all_audio_samples = concatenated.i((0, 0))?.to_vec1::<f32>()?
    .context("Failed to extract audio samples from tensor")?;
```

**vs gen.rs Lines 134-136:**
```rust
let out_pcms = Tensor::cat(&out_pcms, 2)?;
let out_pcms = out_pcms.i((0, 0))?.to_vec1::<f32>()?;
```

**Status:** Functionally identical (just different logging)

---

### File 2: packages/moshi/moshi-cli/src/gen.rs (WORKING)

**Key Sections:**

**Lines 45-52: Setup LogitsProcessors**
```rust
let audio_lp = candle_transformers::generation::LogitsProcessor::from_sampling(
    args.seed,
    candle_transformers::generation::Sampling::TopK { k: 250, temperature: 0.8 },
);
let text_lp = candle_transformers::generation::LogitsProcessor::from_sampling(
    args.seed,
    candle_transformers::generation::Sampling::TopK { k: 250, temperature: 0.8 },
);
```

**Status:** Same as voice.rs lines 1138-1152

---

**Lines 55-69: Condition setup**
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
            cp.condition_lut("description", "very_good")?
        };
        tracing::info!(?conditions, "generated conditions");
        Some(conditions)
    }
};
```

**Status:** Similar to voice.rs lines 1175-1187 (just different logging)

---

**Lines 100-126: THE MAIN INFERENCE LOOP**
```rust
for start_index in 0..(in_pcm_len / 1920).min(max_steps) {
    nsteps += 1;
    let in_pcm = in_pcm.i((.., .., start_index * 1920..(start_index + 1) * 1920))?;
    let codes = mimi.encode_step(&in_pcm.into(), &().into())?;
    if let Some(codes) = codes.as_option() {
        let (_b, _codebooks, steps) = codes.dims3()?;
        for step in 0..steps {
            let codes = codes.i((.., .., step..step + 1))?;
            let codes = codes.i((0, .., 0))?.to_vec1::<u32>()?;
            prev_text_token =
                state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
            if prev_text_token != 0 && prev_text_token != 3 {
                text_tokens.push(prev_text_token)
            }
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
        }
    }
}
```

**Key Points:**
- Line 110: `None` for forced text token (always)
- No text forcing code before the loop
- Simple, clean generation flow

**Status:** CORRECT - This works perfectly

---

**Lines 134-139: Concatenation and final output**
```rust
let out_pcms = Tensor::cat(&out_pcms, 2)?;
tracing::info!(shape = ?out_pcms.shape(), "generated audio");
let out_pcms = out_pcms.i((0, 0))?.to_vec1::<f32>()?;
let mut out_wav = std::fs::File::create(&args.audio_output_file)?;
moshi::wav::write_pcm_as_wav(&mut out_wav, &out_pcms, 24_000)?;
```

**Status:** Standard concatenation and WAV writing

---

## CRITICAL DIFFERENCES SUMMARY

### Primary Bug: Forced Text Token Logic

| Feature | gen.rs | voice.rs | Status |
|---------|--------|----------|--------|
| **Text token forcing** | `None` (always) | `Some(token)` or `None` | **BUG** |
| **Pre-processing tokenization** | None | Tokenize "hello world..." | **BUG** |
| **Forced token tracking** | N/A | `forced_token_idx` | **BUG** |
| **Step_ call parameter** | Fixed `None` | Variable `force_text_token` | **BUG** |

### Secondary Differences: Processing Approach

| Feature | gen.rs | voice.rs | Impact |
|---------|--------|----------|--------|
| **Input slicing** | Direct tensor indexing | Copy to Vec, then create tensor | Inefficient |
| **Frame size** | Fixed 1920 samples | Config-based frame_length | Same result |
| **Flush steps** | None | 20 extra steps | Should help, not hurt |
| **Error handling** | `.t()?` | `.t().context()` | Same functionality |

### Tensor Operations: Identical

| Feature | gen.rs | voice.rs | Status |
|---------|--------|----------|--------|
| **Audio token extraction** | `.i((0, .., 0))` | `.i((0, .., 0))` | Identical |
| **Tensor reshape** | `(1, 1, ())` | `(1, 1, ())` | Identical |
| **Transpose** | `.t()` | `.t()` | Identical |
| **Concatenation** | `Tensor::cat(..., 2)` | `Tensor::cat(..., 2)` | Identical |
| **Final extraction** | `.i((0, 0))` | `.i((0, 0))` | Identical |

---

## WHY THIS CAUSES GARBLING

### The Technical Explanation

1. **MOSHI Architecture:**
   - Language model (LM) generates text AND audio tokens jointly
   - Text and audio tokens evolve together as correlated sequences
   - Internal LM state maintains semantic alignment between them
   - MIMI codec trained to decode tokens from this natural co-evolution

2. **When You Force Text Tokens (voice.rs):**
   - LM is constrained: "output these specific text tokens"
   - LM adapts internal state to match forced text path
   - But audio tokens generated on this forced path are unnatural
   - They don't match the co-generation training distribution

3. **MIMI Decoder Receives Misaligned Tokens:**
   - Tokens are valid but semantically "out of phase"
   - Decoder expects natural text-audio correlation
   - Misalignment causes decoder to produce wrong PCM
   - Result: Garbled waveform that sounds backwards/choppy

4. **Why Whisper Reports "Success" (False Positive):**
   - Whisper uses acoustic likelihood, not semantic alignment
   - Garbled audio still has phoneme-like patterns
   - Whisper detects "something speech-like" → "success"
   - Never validates that text and audio are semantically aligned
   - This is a fundamental limitation of Whisper for validation

### Proof: The Bug Location

**voice.rs Line 1264 (THE BUG):**
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    force_text_token,  // ← Constrains LM to specific text path
    None,
    conditions.as_ref(),
)?;
```

**gen.rs Line 110 (THE FIX):**
```rust
prev_text_token =
    state.step_(Some(prev_text_token), &codes, None, None, conditions.as_ref())?;
                                        ^^^^
                                   No constraint - natural generation
```

---

## THE SOLUTION

### What to Delete from voice.rs

**Delete Lines 1189-1195:**
```rust
// DELETE THIS:
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)?;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
info!("MOSHI_TEST: Forcing MOSHI to say: \"{}\" ({} tokens)", test_phrase, text_tokens.len());
let mut prev_text_token = moshi_state.lm_config.text_start_token;
let mut forced_token_idx = 0;
```

**Delete Lines 1255-1270:**
```rust
// DELETE THIS:
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

### What to Replace It With

```rust
// REPLACE WITH THIS:
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    None,  // ← Always None - natural generation
    None,
    conditions.as_ref(),
)?;
```

---

## EXPECTED RESULTS

### Before Fix (Current)
- Audio: Garbled, backwards-sounding, choppy
- Whisper: Reports "success" (false positive)
- Quality: Unusable for speech

### After Fix
- Audio: Clear, intelligible, natural-sounding
- Whisper: Accurate transcription of actual generated speech
- Quality: Matches gen.rs output (excellent)
- Flexibility: MOSHI says whatever it naturally wants (not forced phrases)

---

## VALIDATION

To confirm this diagnosis:
1. Apply the fix (delete forced text token logic)
2. Run voice.rs again
3. Listen to moshi-response.wav
4. Run Whisper API on the output
5. Compare with gen.rs output

Expected: Audio quality will be identical to gen.rs (clear and intelligible).

