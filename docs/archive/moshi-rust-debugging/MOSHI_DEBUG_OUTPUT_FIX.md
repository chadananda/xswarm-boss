# MOSHI Debug Output Visibility Fix - Complete

## Status: ✅ SUCCESS

**Task**: Make `eprintln!()` debug output visible during MOSHI test mode (bypassing TUI)

**Approach Used**: Option 3 - Direct file logging

## Implementation Summary

### Changes Made

**File**: `packages/core/src/voice.rs`

1. **Added chrono import** (line 25):
   ```rust
   use chrono;
   ```

2. **Created debug_log() helper function** (lines 305-318):
   ```rust
   /// Debug logger that writes directly to file, bypassing tracing/TUI
   fn debug_log(msg: &str) {
       use std::io::Write;
       // Write to project-local tmp directory
       if let Ok(mut file) = std::fs::OpenOptions::new()
           .create(true)
           .append(true)
           .open("./tmp/moshi-debug.log")
       {
           let timestamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S%.3f");
           let _ = writeln!(file, "[{}] {}", timestamp, msg);
           let _ = file.flush();
       }
   }
   ```

3. **Replaced all eprintln!() calls** with `Self::debug_log()`:
   - Lines 338-340: CARGO_MANIFEST_DIR, config path, model file
   - Line 343: Config file read success
   - Line 347: Config file read error
   - Lines 353-354: TOML parse success + audio_codebooks value
   - Line 358: TOML parse error
   - Line 362: About to load LM model
   - Line 366: LM model load success
   - Line 370: LM model load error (THE CRITICAL ONE)

### Build Result
✅ **Compilation successful** (1m 43s, warnings only - no errors)

### Test Result
✅ **Debug logging working perfectly**

**Debug log location**: `./tmp/moshi-debug.log`

**Debug output captured**:
```
[2025-11-08 21:46:16.308] [DEBUG] CARGO_MANIFEST_DIR = /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core
[2025-11-08 21:46:16.308] [DEBUG] LM config path = /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/config/moshi-s2st-1b.toml
[2025-11-08 21:46:16.308] [DEBUG] LM model file = /Users/chad/.cache/huggingface/hub/models--kyutai--moshika-candle-q8/snapshots/4b4a873fc1d3b92ce32b3ae91ff8e95bbb62193f/model.q8.gguf
[2025-11-08 21:46:16.308] [DEBUG] Successfully read 998 bytes from config file
[2025-11-08 21:46:16.312] [DEBUG] Successfully parsed TOML config
[2025-11-08 21:46:16.312] [DEBUG] Config audio_codebooks = 16
[2025-11-08 21:46:16.312] [DEBUG] About to load LM model from: /Users/chad/.cache/huggingface/hub/models--kyutai--moshika-candle-q8/snapshots/4b4a873fc1d3b92ce32b3ae91ff8e95bbb62193f/model.q8.gguf
[2025-11-08 21:46:19.858] [ERROR] Failed to load LM model: shape mismatch for weight, got [32001, 1024], expected [48001, 1024]
```

## Root Cause Revealed

### The Actual Error

**ERROR**: `shape mismatch for weight, got [32001, 1024], expected [48001, 1024]`

This is a **vocabulary size mismatch** between the config file and the GGUF model:

- **Config expects**: 48001 tokens (vocabulary size)
- **GGUF model has**: 32001 tokens (vocabulary size)

### Analysis

1. **Config file** (`moshi-s2st-1b.toml`):
   - Successfully loaded (998 bytes)
   - Successfully parsed as TOML
   - Specifies `audio_codebooks = 16`
   - Expects vocabulary size of 48001

2. **GGUF model** (`model.q8.gguf`):
   - Located at: `~/.cache/huggingface/hub/models--kyutai--moshika-candle-q8/snapshots/4b4a873fc1d3b92ce32b3ae91ff8e95bbb62193f/model.q8.gguf`
   - Contains vocabulary size of 32001
   - This is the quantized Q8 model from Hugging Face

### Why This Happens

The GGUF quantized model (`model.q8.gguf`) appears to have a different vocabulary configuration than what the official TOML config expects. This could be:

1. **Version mismatch**: GGUF model is from a different version of MOSHI
2. **Quantization artifact**: The quantization process created a different vocab size
3. **Config mismatch**: The `moshi-s2st-1b.toml` config is for a different model variant

## Next Steps (Task 2)

Now that we can see the error, Task 2 should investigate:

1. **Check the TOML config file** (`packages/core/config/moshi-s2st-1b.toml`):
   - What vocabulary size is specified?
   - Is this the correct config for the Q8 model?

2. **Find the correct config** for the GGUF model:
   - Does the model repo have a different TOML file?
   - Should we use `moshi-s2st-1b-q8.toml` instead?

3. **Alternative solutions**:
   - Download a different model variant that matches the config
   - Modify the config to match the GGUF model's vocab size
   - Use a different loading method that doesn't require exact vocab match

## Files Modified

- `packages/core/src/voice.rs` - Added debug_log() function and replaced eprintln!() calls

## Testing Commands

**Run test**:
```bash
./target/release/xswarm --moshi-test
```

**Check debug log**:
```bash
cat ./tmp/moshi-debug.log
```

**Build**:
```bash
cargo build --release
```

## Success Criteria - ALL MET ✅

- ✅ Build succeeds without errors
- ✅ Debug output is visible in `./tmp/moshi-debug.log`
- ✅ Can see actual error message explaining why model load failed
- ✅ Uses project-local `./tmp/` directory (not `~/tmp`)
- ✅ Timestamped debug logs with millisecond precision
- ✅ All debug messages captured (config loading, TOML parsing, model loading)

## Implementation Notes

**Why this approach worked**:
1. Bypasses the tracing_subscriber that redirects to `~/.cache/xswarm/xswarm.log`
2. Writes directly to file handle, ensuring output is captured
3. Flushes after each write to ensure visibility even if process crashes
4. Uses project-local `./tmp/` directory (gitignored)
5. Includes millisecond timestamps for precise debugging

**Alternative approaches considered**:
- Option 1 (stderr redirect): Would conflict with TUI initialization
- Option 2 (delay TUI): Would require major refactoring of startup flow
- Option 3 (direct file logging): ✅ CHOSEN - Simple, effective, no side effects

---

**Task 1 Complete** - Debug output is now visible. Ready for Task 2: Fix the vocabulary size mismatch.
