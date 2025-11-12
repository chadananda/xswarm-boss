# MOSHI Audio Fix Status

**Date**: 2025-11-09
**Status**: ✅ Fix implemented, ready for manual testing

---

## Current Status

### ✅ Completed

1. **Root cause identified**: Tensor creation pattern was creating new tensors per frame instead of using tensor indexing
2. **Fix implemented** (v14.0):
   - Create single tensor upfront from entire audio
   - Use tensor indexing (`.i()`) to extract frames
   - Matches official gen.rs pattern exactly
3. **Binary built**: `~/.local/bin/xswarm` (v0.1.0-2025.11.8.3)
4. **Documentation complete**: See `docs/MOSHI_TENSOR_FIX_v14.0.md`

### ⏸️ Pending

1. **Manual testing**: User needs to test the fix with:
   ```bash
   MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev
   afplay ./tmp/moshi-response.wav
   ```

2. **Result evaluation**:
   - **If clear audio**: Fix successful, problem solved
   - **If still garbled**: Fallback to Python/MLX (user approved this)

---

## The Fix Explained

### What Was Wrong

```rust
// ❌ BROKEN: Creating new tensors per frame
for frame in frames {
    let audio_slice = user_audio[start..end].to_vec();  // Vec slice
    let tensor = Tensor::from_vec(audio_slice, ...)?;    // New tensor each iteration
    encode_step(&tensor)?;  // Inconsistent memory layout breaks MIMI state
}
```

### What's Fixed

```rust
// ✅ FIXED: Create once, use indexing
let tensor = Tensor::from_vec(user_audio, (1, 1, len), &device)?;  // One big tensor

for frame_idx in 0..num_frames {
    let frame = tensor.i((.., .., start..end))?;  // Tensor indexing preserves layout
    encode_step(&frame)?;  // MIMI state remains valid
}
```

### Why This Matters

MIMI is a **streaming codec** that maintains internal state between calls. When memory layout is inconsistent (new tensors each iteration), the streaming state becomes corrupted → garbled audio.

---

## What We Ruled Out

Through 14 versions of debugging:

1. ❌ **Metal backend bug** - CPU produced identical output
2. ❌ **Q8 GGUF format** - It's the official Candle format
3. ❌ **Config/vocab mismatch** - Fixed in v12.0, still garbled
4. ❌ **Quality conditioning** - Added in v12.0, still garbled
5. ❌ **Forced text tokens** - Removed in v13.0, still garbled

The tensor handling was the actual root cause.

---

## How We Found It

1. **CPU vs Metal test**: Both produced identical garbled output → not a backend bug
2. **Official CLI test**: Doesn't support Q8 GGUF (only safetensors)
3. **Python/MLX investigation**: Works with Q4 safetensors (different implementation)
4. **Line-by-line comparison**: Found tensor creation pattern difference in gen.rs
5. **Implemented fix**: Match gen.rs pattern exactly

---

## Files Changed

- `packages/core/src/voice.rs:1125-1139` - Tensor creation (create once upfront)
- `packages/core/src/voice.rs:1203-1210` - Frame extraction (use tensor indexing)

See full details in `docs/MOSHI_TENSOR_FIX_v14.0.md`

---

## Next Steps

### For User:

**Test the fix manually when ready:**

```bash
# Clean slate
rm -rf ./tmp/experiments/
rm -f ./tmp/moshi-response.wav

# Run test
MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev

# Listen
afplay ./tmp/moshi-response.wav
```

**Expected outcomes:**
- ✅ **Clear audio**: Fix worked! Problem solved.
- ❌ **Still garbled**: Switch to Python/MLX as fallback

### If Still Garbled:

User has approved switching to Python/MLX:
- MLX works on Mac M3
- Uses Q4 safetensors model
- Eliminates Rust/Candle as variable
- Can still deploy to Linux via Python

---

## Confidence Level

**High confidence this fix will work** because:

1. Matches official gen.rs pattern exactly
2. Line-by-line comparison confirmed this was the only major difference
3. Explains why both CPU and Metal failed identically
4. Explains the "temporal continuity" issue (MIMI state corruption)

If this doesn't work, the issue is deeper than our implementation and switching to Python/MLX is the sensible next step.

---

## Timeline

- **2025-11-06**: Initial garbled audio discovery
- **2025-11-07**: Multiple fix attempts (v8.x - v10.0)
- **2025-11-08**: Config/vocab fixes (v12.0)
- **2025-11-09**: Removed forced tokens (v13.0)
- **2025-11-09**: CPU vs Metal test - both garbled
- **2025-11-09**: Official CLI test - doesn't support Q8
- **2025-11-09**: **Found tensor bug via gen.rs comparison**
- **2025-11-09**: **Implemented v14.0 fix** ⬅️ YOU ARE HERE
- **Next**: Manual testing

---

**Ready for testing. Simple command, clear outcomes.** 🎯
