# Q8 Model Testing with Official CLI - Result

**Date**: 2025-11-09
**Result**: ❌ Official CLI does not support Q8 GGUF format

---

## Test Attempt

Tried to run official `gen.rs` with Q8 GGUF model:

```bash
./target/release/moshi-cli gen \
  --lm-model-file model.q8.gguf \
  --mimi-model-file mimi.safetensors \
  ...
```

## Error

```
Error: cannot find tensor encoder.model.0.conv.conv.weight_g
```

The official CLI expects **safetensors format**, not GGUF format.

---

## What This Tells Us

### Q8 GGUF is NOT Officially Supported

- The official `gen.rs` and CLI don't have Q8 GGUF support
- Q8 GGUF appears to be a community/experimental export
- No way to validate if Q8 "should" work with reference implementation

### Our Code Successfully Loads Q8

- ✅ Our implementation CAN load Q8 GGUF + MIMI safetensors
- ✅ Models load without errors
- ❌ But audio output is garbled

### Implications

Since we can't test Q8 with the official implementation, and:
- Both CPU and Metal produce identical garbled audio
- Q8 lacks quality conditioning weights
- Q8 uses different architecture config
- No official support for Q8 in reference CLI

**Conclusion**: Q8 GGUF model is likely broken/untested

---

## Recommendation

**Switch to bf16 safetensors model** - the format the official implementation uses and tests:

- `kyutai/moshika-candle-bf16` (female voice)
- `kyutai/moshiko-candle-bf16` (male voice)

These models:
- ✅ Are officially supported
- ✅ Have quality conditioning
- ✅ Use standard 48001 vocabulary
- ✅ Can be validated with official gen.rs
- ⚠️ Are larger (~3GB vs ~1.5GB)
- ⚠️ Are slower (~2x inference time)

---

## Next Steps

1. **Download bf16 model**
2. **Update VoiceConfig** to use bf16
3. **Use s2st-1b.toml** config (48001 vocab)
4. **Test audio generation**
5. **Validate with official CLI** if needed

If bf16 produces clear audio → Q8 is broken (as suspected)

---

**Status**: Ready to switch to bf16 safetensors model
