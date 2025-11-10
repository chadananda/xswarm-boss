# MOSHI Configuration Comparison: MLX vs Rust/Candle

**Date**: 2025-11-08
**Platform**: macOS M3 Max
**Result**: MLX produces clear speech ✅ | Rust produces garbled audio ❌

## Configuration Comparison Table

| Parameter | MLX (Working) | Rust/Candle (Garbled) | Match? |
|-----------|---------------|----------------------|--------|
| **LM Model Config** | | | |
| Total audio_codebooks | 16 | 16 | ✅ |
| Depformer num_slices (generated) | 8 | 8 | ✅ |
| Input codebooks (other) | 8 (16-8) | 8 (16-8) | ✅ |
| Text vocab size (in) | 32001 | 32001 | ✅ |
| Text vocab size (out) | 32000 | 32000 | ✅ |
| Audio vocab size | 2049 | 2049 | ✅ |
| **LM Generation Config** | | | |
| Generated codebooks | 8 | 8 | ✅ |
| Input codebooks | 8 | 8 | ✅ |
| Acoustic delay | (from delays) | 2 | ❓ |
| **MIMI Configuration** | | | |
| MIMI model loading | `rustymimi.StreamTokenizer(mimi_file)` | `moshi::mimi::load(..., Some(8), ...)` | ⚠️ |
| MIMI codebooks configured | **UNKNOWN (default)** | **8 explicit** | ❌ POTENTIAL ISSUE |
| Input data slicing | `[:, :8]` (slice AFTER encode) | No slicing (rely on config) | ❌ DIFFERENT |
| **Sampling Parameters** | | | |
| Temperature (text) | 0.8 | LogitsProcessor default | ❓ |
| Temperature (audio) | 0.8 | LogitsProcessor default | ❓ |
| Top-p (text) | 0.95 | LogitsProcessor default | ❓ |
| Top-p (audio) | 0.95 | LogitsProcessor default | ❓ |
| Top-k | None | 250 (in moshi-cli) | ❌ DIFFERENT |
| RNG seed | 299792458 | 123 (warmup in voice.rs:482) | ❌ DIFFERENT |

## Critical Differences Found

### 1. **MIMI Codebook Handling** ⚠️

**MLX Approach** (`local.py:129`):
```python
data = mx.array(data).transpose(1, 0)[:, :8]
```
- Loads MIMI with **default configuration** (likely 32 codebooks)
- **Slices to first 8 codebooks AFTER encoding**
- Uses `rustymimi.StreamTokenizer` (same Rust MIMI backend as us!)

**Rust Approach** (`voice.rs:349`):
```rust
let mimi_model = moshi::mimi::load(
    &config.mimi_model_file,
    Some(MIMI_NUM_CODEBOOKS),  // Explicitly set to 8
    mimi_device,
)
```
- Loads MIMI with **explicit 8 codebooks configuration**
- **No slicing** (assumes MIMI is configured correctly)

**Potential Issue**:
- If MIMI needs to be loaded with its full default configuration (32 codebooks) and then sliced, configuring it to only use 8 codebooks might cause the model weights to be loaded incorrectly or tensor shapes to mismatch
- The MLX code uses the SAME Rust MIMI implementation but doesn't configure codebooks - just slices output

### 2. **Sampling Parameters** ❓

**MLX Sampler Defaults** (`utils/sampling.py:136-142`):
```python
temp: float = 0.8
top_p: float = 0.95
top_k: int | None = None
min_p: float = 0.0
```

**Rust Sampling** (needs verification):
- Uses `candle_transformers::generation::LogitsProcessor`
- Warmup uses seed `123` (`voice.rs:482`)
- `moshi-cli` example uses `top_k=250, temperature=0.8` (`gen.rs:51`)
- Unknown what our actual voice.rs uses for sampling

### 3. **RNG Seeding** ❌

**MLX** (`local.py:97`):
```python
mx.random.seed(299792458)
```

**Rust** (`voice.rs:482`):
```rust
let mut lp = candle_transformers::generation::LogitsProcessor::new(123, None, None);
```

Different seeds could potentially cause divergence, but unlikely to be the root cause of completely garbled audio.

## Hypothesis: MIMI Configuration Issue

**Most Likely Root Cause**:

The MIMI model is designed to use all 32 codebooks, and the MLX implementation:
1. Loads MIMI with its default/full configuration (32 codebooks available)
2. Encodes audio → gets 32 codebooks
3. **Slices to first 8 codebooks** before passing to LM

Our Rust implementation:
1. Loads MIMI with **explicit 8 codebook configuration** (`Some(8)`)
2. This might cause:
   - Model weights to be subset incorrectly
   - Tensor shape mismatches internally
   - Quantization codebooks to be limited improperly
3. No slicing (assumes 8 codebooks is correct from start)

**Test Hypothesis**:
Change our MIMI loading from:
```rust
Some(MIMI_NUM_CODEBOOKS)  // Some(8)
```

To:
```rust
None  // Use default configuration, then slice output
```

Then slice the MIMI output to first 8 codebooks AFTER encoding, matching MLX's approach.

## Next Steps

1. **Verify MIMI default codebooks**: Check what `Config::v0_1(None)` returns for MIMI
2. **Test fix**: Load MIMI with `None` (default config) and slice output to `[:, :8]`
3. **Verify sampling params**: Check what LogitsProcessor defaults are in our voice.rs
4. **Compare other parameters**: Audio delays, transformer configs, etc.

## References

- **MLX config**: `tmp/venv-mlx/lib/python3.11/site-packages/moshi_mlx/models/lm.py:670-729`
- **MLX sampler**: `tmp/venv-mlx/lib/python3.11/site-packages/moshi_mlx/utils/sampling.py:136-166`
- **MLX local.py**: `tmp/venv-mlx/lib/python3.11/site-packages/moshi_mlx/local.py:129`
- **Rust LM config**: `packages/moshi/moshi-core/src/lm.rs:169-177` (`v0_1_streaming`)
- **Rust gen config**: `packages/moshi/moshi-core/src/lm_generate_multistream.rs:24-34` (`v0_1()`)
- **Rust voice.rs**: `packages/core/src/voice.rs:322, 349, 363`
