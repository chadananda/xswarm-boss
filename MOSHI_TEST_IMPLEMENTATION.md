# MOSHI Test Mode Implementation Summary

## Version: v0.1.0-2025.11.6.1

## What Was Built

A comprehensive automated testing system for debugging MOSHI audio quality issues using OpenAI Whisper API for objective verification.

## Key Features

### 1. Automated Test Mode (`xswarm --moshi_test`)
- Simple CLI flag to trigger automated testing
- No manual listening required
- Objective pass/fail based on Whisper transcription
- Automatic iteration through configurations

### 2. Test Audio Generation
- Generates 1-second quiet noise to trigger MOSHI
- 24kHz mono PCM format (MOSHI native)
- Amplitude ~0.001 to trigger voice activity detection
- No TTS required - pure Rust implementation

### 3. OpenAI Whisper API Integration
- Transcribes MOSHI output to verify intelligibility
- Returns actual text heard in the audio
- Pass criteria: ≥3 words and ≥10 characters
- Cost: ~$0.0003-$0.001 per test

### 4. Systematic Configuration Testing
- 5 pre-defined audio pipeline configurations
- Tests different resampler parameters:
  - sinc filter length (256, 512)
  - cutoff frequency (0.95, 0.99)
  - interpolation type (Linear, Cubic)
  - window functions (Blackman, BlackmanHarris2)
  - No resampling (special test)

### 5. Experiment Logging
- All results saved to `./tmp/experiments/`
- JSON format with full configuration details
- Prevents testing same config twice
- Provides complete test history
- Tracks transcriptions and intelligibility

### 6. Intelligent Iteration
- Automatically tries next config if current fails
- Stops when working config found
- Reports if all configs fail
- User just runs: `xswarm --moshi_test` repeatedly

## Files Created/Modified

### New Files
```
packages/core/src/moshi_test.rs              # New testing module (420 lines)
docs/MOSHI_TEST_MODE.md                      # User documentation
MOSHI_TEST_IMPLEMENTATION.md                 # This file
```

### Modified Files
```
packages/core/src/main.rs:
  - Added --moshi_test CLI flag (line 78)
  - Enhanced run_moshi_test_mode() function (lines 681-809)

packages/core/src/lib.rs:
  - Added pub mod moshi_test; (line 28)

packages/core/Cargo.toml:
  - Added "multipart" feature to reqwest (line 67)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ User runs: xswarm --moshi_test                                  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 1. Check OPENAI_API_KEY environment variable                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 2. Load experiment history from ./tmp/experiments/              │
│    - Check if working config already found                      │
│    - Get next untested configuration                            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 3. Generate test audio: ./tmp/test-user-hello.wav              │
│    - 1 second quiet noise (amplitude ~0.001)                    │
│    - 24kHz mono PCM format                                      │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 4. Initialize MOSHI voice bridge                                │
│    - Load LM model                                              │
│    - Load MIMI codec                                            │
│    - Load text tokenizer                                        │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 5. Process test audio through MOSHI                             │
│    - voice_bridge.run_test_mode()                               │
│    - MIMI encode → LM generate → MIMI decode                    │
│    - Save response: ./tmp/moshi-response.wav                    │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 6. Transcribe with OpenAI Whisper API                           │
│    - POST to api.openai.com/v1/audio/transcriptions            │
│    - Model: whisper-1                                           │
│    - Returns transcribed text                                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 7. Check intelligibility                                        │
│    - Count words and characters                                 │
│    - Pass: ≥3 words AND ≥10 characters                          │
│    - Fail: Otherwise                                            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 8. Log experiment result                                        │
│    - Save to ./tmp/experiments/experiment_TIMESTAMP.json        │
│    - Include config, transcription, intelligibility            │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   v
┌─────────────────────────────────────────────────────────────────┐
│ 9. Print report and next action                                 │
│    - ✅ Success: Report working config                          │
│    - ❌ Failure: Tell user to run again for next config         │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Test
```bash
# Set API key (one time)
export OPENAI_API_KEY=sk-your-key-here

# Run test
xswarm --moshi_test
```

### Iterate Until Success
```bash
# Keep running until working config found
while ! xswarm --moshi_test; do
    echo "Trying next configuration..."
done
```

### Reset and Start Over
```bash
# Clear experiment history
rm -rf ./tmp/experiments/

# Run fresh
xswarm --moshi_test
```

## Example Output

### First Run (Testing Config 1)
```
🧪 MOSHI AUDIO TEST MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Testing configuration: config_1_ultra_high_quality
   Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear

✅ Test audio generated: ./tmp/test-user-hello.wav
✅ MOSHI models loaded
✅ MOSHI generated response: ./tmp/moshi-response.wav
✅ Transcription complete

╔════════════════════════════════════════════════════════════════
║ MOSHI AUDIO TEST RESULTS
╠════════════════════════════════════════════════════════════════
║ 📝 Transcription: ""
║ 📊 Analysis: Words detected: 0
║ ❌ FAILURE: No recognizable words detected
╚════════════════════════════════════════════════════════════════

⏭️  Will try next configuration on next run.
   Run again: xswarm --moshi_test
```

### Second Run (Testing Config 2)
```
📋 Previous Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ config_1_ultra_high_quality - 0 words - 20251106_143022
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Testing configuration: config_2_cubic_interpolation
   Try Cubic interpolation instead of Linear

...
```

### Success (Config 3 Works)
```
📋 Previous Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ config_1_ultra_high_quality - 0 words - 20251106_143022
❌ config_2_cubic_interpolation - 0 words - 20251106_143145
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 Testing configuration: config_3_lower_cutoff
   Lower cutoff frequency (0.95 instead of 0.99)

✅ MOSHI generated response: ./tmp/moshi-response.wav
✅ Transcription complete

╔════════════════════════════════════════════════════════════════
║ MOSHI AUDIO TEST RESULTS
╠════════════════════════════════════════════════════════════════
║ 📝 Transcription: "Hello! I'm your AI assistant."
║ 📊 Analysis: Words detected: 5
║ ✅ SUCCESS: Audio contains recognizable speech!
╚════════════════════════════════════════════════════════════════

🎉 SUCCESS! The audio pipeline is working correctly!

Configuration that worked: config_3_lower_cutoff
Lower cutoff frequency (0.95 instead of 0.99)
```

## Benefits

1. **Objective Testing** - No more "does this sound garbled?" - Whisper gives yes/no
2. **Fast Iteration** - Test 5 configs in ~5 minutes vs. hours of manual testing
3. **Reproducible** - Exact same test every time, logged results
4. **Automated** - Just run `xswarm --moshi_test` repeatedly
5. **No Python Bridge** - Pure Rust implementation (except Whisper API call)
6. **Cost Effective** - ~$0.005 to test all configs
7. **Comprehensive Logs** - Full history of what was tested and results

## What This Reveals

When a configuration works, it tells us:
- **Exact resampler parameters** that produce clean audio
- **Whether resampling is the issue** (if config_5 no-resampling works)
- **Pattern of failures** (do any configs produce partial words?)

When all configurations fail, it tells us:
- Issue is NOT in resampling parameters
- Problem is deeper in the pipeline:
  - MIMI codec encoding/decoding
  - Sample format conversion
  - Byte ordering
  - Frame assembly

## Next Steps After Finding Working Config

1. **Update audio.rs** with working parameters
2. **Test in real conversation** with `xswarm --dev`
3. **Verify quality** is acceptable for production use
4. **Document the fix** in ARCHITECTURE.md

## Debugging Deeper Issues

If all configs fail:

### Check MIMI Codec
```rust
// Test MIMI encode → decode roundtrip
let test_audio = vec![0.1f32; 1920]; // 80ms at 24kHz
let encoded = mimi.encode(&test_audio)?;
let decoded = mimi.decode(&encoded)?;
// decoded should ≈ test_audio
```

### Check Sample Format
```rust
// Log sample values before/after conversion
info!("f32 samples: {:?}", &samples[0..10]);
let i16_samples: Vec<i16> = samples.iter()
    .map(|&s| (s * 32767.0) as i16)
    .collect();
info!("i16 samples: {:?}", &i16_samples[0..10]);
```

### Check Byte Ordering
```rust
// Force little-endian
let bytes = i16_val.to_le_bytes();
// vs
let bytes = i16_val.to_be_bytes();
```

## Performance

- **Test duration**: ~60-90 seconds per config
  - Model loading: 30-60s (first time only)
  - MOSHI processing: 10-20s
  - Whisper API: 5-10s
  - Logging: <1s

- **Total time for all 5 configs**: ~5-10 minutes

- **Cost**: ~$0.005 total for all configs

## Success Criteria

The test mode is considered successful when:
1. One configuration produces ≥3 words in transcription
2. Transcription is coherent (not random syllables)
3. Can be reproduced consistently
4. Works in real conversation mode

## Known Limitations

1. **Requires OpenAI API key** - Free tier is sufficient
2. **Network required** - For Whisper API calls
3. **Not testing real-time performance** - Only audio quality
4. **Simple test input** - Real speech might reveal different issues

## Future Enhancements

- Test with actual recorded speech samples
- Test different audio devices
- Test different sample rates
- Parallel testing of multiple configs
- Integration with CI/CD
- Audio quality metrics (SNR, spectral analysis)

---

**Status:** ✅ Ready for Testing
**Build:** Successful (v0.1.0-2025.11.6.1)
**Documentation:** Complete
**Next Action:** User should run `export OPENAI_API_KEY=sk-... && xswarm --moshi_test`
