# MOSHI Tensor Shape Investigation

## Critical Finding: Three Different Tensor Creation Approaches

### 1. CLI gen.rs (lines 116-118)
```rust
let audio_tokens =
    Tensor::new(&audio_tokens[..generated_audio_codebooks], dev)?
        .reshape((1, 1, ()))?
        .t()?;  // TRANSPOSE!
```

**Result shape (for 8 codebooks):**
- `Tensor::new(&audio_tokens[..8])` → shape `[8]`
- `.reshape((1, 1, ()))` → shape `[1, 1, 8]`
- `.t()` transposes last two dims → shape `[1, 8, 1]`

### 2. Server lm.rs (line 190)
```rust
Tensor::from_slice(&audio_tokens[..cb], (1, cb, 1), &dev)?
```

**Result shape:** `[1, 8, 1]` directly

### 3. Our Implementation (voice.rs:1177-1181)
```rust
let audio_tensor = Tensor::from_slice(
    audio_tokens_slice,
    (1, generated_codebooks, 1),
    &mimi_device,
)?;
```

**Result shape:** `[1, 8, 1]` directly

## Analysis

### Same Final Shape
All three approaches produce the SAME final tensor shape: `[1, 8, 1]`
- Dimension 0: batch = 1
- Dimension 1: codebooks = 8
- Dimension 2: time = 1

### BUT: Data Layout Might Differ!

**Critical Question:** Does `Tensor::new()` + `reshape()` + `t()` produce the SAME data layout as `Tensor::from_slice()` with shape `(1, 8, 1)`?

**Hypothesis:** The data might be in a different order in memory even with the same shape!

### Tensor::new vs Tensor::from_slice

From Candle documentation:
- `Tensor::new(data, device)` - Creates tensor from data, infers shape
- `Tensor::from_slice(data, shape, device)` - Creates tensor with explicit shape

The `.t()` transpose operation might change the **stride** (memory layout) even though the final shape is the same!

## Next Steps

### Test 1: Use CLI Approach
Change our code to match the CLI gen.rs pattern exactly:
```rust
let audio_tensor = Tensor::new(audio_tokens_slice, mimi_device)?
    .reshape((1, 1, ()))?
    .t()?;
```

### Test 2: Check Tensor Strides
Log the tensor strides before decode_step:
```rust
debug!("Tensor shape: {:?}, strides: {:?}", audio_tensor.shape(), audio_tensor.stride());
```

### Test 3: Compare with Working Example
Run the official moshi-cli gen and log its tensor properties, compare with ours.

## Hypothesis

The garbled audio might be caused by:
1. **Incorrect data layout in memory** despite correct shape
2. **Stride mismatch** - data is in wrong order for MIMI decoder
3. **Transpose operation** in CLI creates different memory pattern than direct from_slice

The fact that Whisper CAN transcribe suggests the phonetic content is present but the temporal structure is wrong - this could be explained by data being in the wrong memory order.

---

**Date:** 2025-11-07
**Status:** New hypothesis to test
**Next:** Try CLI tensor creation approach
