# MOSHI Test Mode - Automated Audio Quality Verification

## Overview

The MOSHI test mode provides systematic, automated testing of MOSHI audio output quality using OpenAI's Whisper API for objective verification. This eliminates the need for manual listening and allows rapid iteration through different audio processing configurations.

## Quick Start

### 1. Set up OpenAI API Key

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### 2. Run the test

```bash
xswarm --moshi_test
```

Or alternatively:

```bash
MOSHI_TEST_MODE=1 xswarm
```

## What It Does

The test mode automatically:

1. **Generates test audio** - Creates a 1-second quiet noise file to trigger MOSHI
2. **Processes through MOSHI** - Feeds the test audio through the MOSHI pipeline
3. **Transcribes output** - Sends MOSHI's response to OpenAI Whisper API
4. **Checks intelligibility** - Determines if the audio contains recognizable speech
5. **Logs results** - Saves experiment data to avoid testing the same config twice
6. **Iterates configs** - If audio is garbled, tries next configuration on next run

## Expected Output

### Success (Intelligible Audio)

```
🧪 MOSHI AUDIO TEST MODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This test will:
  1. Generate a simple test audio input
  2. Process it through MOSHI
  3. Transcribe the output with OpenAI Whisper API
  4. Check if the audio is intelligible
  5. If not, try next configuration automatically

🔧 Testing configuration: config_1_ultra_high_quality
   Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear

✅ Test audio generated: ./tmp/test-user-hello.wav

🔊 Initializing MOSHI voice models...
   (This may take 30-60 seconds for first-time model download)

✅ MOSHI models loaded

🎤 Processing test audio through MOSHI...
   Input: ./tmp/test-user-hello.wav

✅ MOSHI generated response: ./tmp/moshi-response.wav

🔍 Transcribing with OpenAI Whisper API...
✅ Transcription complete

╔════════════════════════════════════════════════════════════════
║ MOSHI AUDIO TEST RESULTS
╠════════════════════════════════════════════════════════════════
║ Configuration: config_1_ultra_high_quality
║ Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear
╠════════════════════════════════════════════════════════════════
║ 📝 Transcription:
║    "Hello! I'm your AI assistant. How can I help you?"
╠════════════════════════════════════════════════════════════════
║ 📊 Analysis:
║    Words detected: 9
║    Text length: 53 characters
║    Audio file: ./tmp/moshi-response.wav
╠════════════════════════════════════════════════════════════════
║ ✅ SUCCESS: Audio contains recognizable speech!
║
║ The audio pipeline is working correctly. MOSHI output is
║ intelligible and can be transcribed by Whisper API.
╚════════════════════════════════════════════════════════════════

🎉 SUCCESS! The audio pipeline is working correctly!

Configuration that worked: config_1_ultra_high_quality
Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear
```

### Failure (Garbled Audio)

```
╔════════════════════════════════════════════════════════════════
║ MOSHI AUDIO TEST RESULTS
╠════════════════════════════════════════════════════════════════
║ Configuration: config_1_ultra_high_quality
║ Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear
╠════════════════════════════════════════════════════════════════
║ 📝 Transcription:
║    ""
╠════════════════════════════════════════════════════════════════
║ 📊 Analysis:
║    Words detected: 0
║    Text length: 0 characters
║    Audio file: ./tmp/moshi-response.wav
╠════════════════════════════════════════════════════════════════
║ ❌ FAILURE: No recognizable words detected
║
║ The audio is still garbled. Will try next configuration...
╚════════════════════════════════════════════════════════════════

⏭️  Will try next configuration on next run.
   Run again: xswarm --moshi_test
```

## Configurations Tested

The test mode systematically tries these configurations in order:

1. **config_1_ultra_high_quality**
   - sinc_len=512, f_cutoff=0.99, Linear interpolation
   - Ultra-high quality resampling with long sinc filter

2. **config_2_cubic_interpolation**
   - sinc_len=512, f_cutoff=0.99, Cubic interpolation
   - Try Cubic instead of Linear

3. **config_3_lower_cutoff**
   - sinc_len=512, f_cutoff=0.95, Linear interpolation
   - Lower cutoff frequency to reduce artifacts

4. **config_4_shorter_sinc**
   - sinc_len=256, f_cutoff=0.95, Cubic interpolation
   - Shorter sinc filter with BlackmanHarris2 window

5. **config_5_no_resampling**
   - Special config that skips resampling entirely
   - Matches device rate to MOSHI rate (24kHz)

## Experiment Logging

All test results are saved to `./tmp/experiments/experiment_TIMESTAMP.json`:

```json
{
  "timestamp": "20251106_143022",
  "config": {
    "name": "config_1_ultra_high_quality",
    "description": "Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear",
    "resampler_sinc_len": 512,
    "resampler_f_cutoff": 0.99,
    "resampler_interpolation": "Linear",
    "resampler_oversampling": 512,
    "resampler_window": "Blackman"
  },
  "transcription": "Hello! I'm your AI assistant.",
  "word_count": 5,
  "intelligible": true,
  "audio_path": "./tmp/moshi-response.wav"
}
```

This prevents testing the same configuration twice and provides a complete history of what's been tried.

## Files Generated

```
./tmp/
├── test-user-hello.wav          # Generated test input audio
├── moshi-response.wav           # MOSHI's response (last run)
└── experiments/
    ├── experiment_20251106_143022.json
    ├── experiment_20251106_143145.json
    └── ...
```

## Resetting Tests

To start fresh and test all configurations again:

```bash
rm -rf ./tmp/experiments/
```

## Cost Estimation

Each Whisper API transcription costs approximately:
- **$0.006 per minute** of audio
- MOSHI responses are typically **3-10 seconds**
- Cost per test: **~$0.0003 - $0.001**
- Testing all 5 configs: **~$0.002 - $0.005**

Extremely affordable for systematic debugging!

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"

Set your API key:
```bash
export OPENAI_API_KEY=sk-your-key-here
```

Get an API key from: https://platform.openai.com/api-keys

### "All configurations tested - none produced intelligible audio"

This indicates a deeper issue beyond resampling configuration. Possible causes:

1. **MIMI codec issue** - Check if MIMI encoding/decoding is working
2. **Sample format issue** - Check f32 → i16 conversion
3. **Byte ordering** - Check endianness
4. **Frame alignment** - Check how 80ms MOSHI frames are assembled

Review experiment logs in `./tmp/experiments/` and examine:
- Are any words being detected? (>0 but <3 might indicate partial success)
- Do different configs show different patterns?
- Is the WAV file playable in an external player?

### "Failed to call OpenAI Whisper API"

Check:
- API key is valid
- You have credits in your OpenAI account
- Network connection is working
- Audio file is valid WAV format

## Integration with Debugging

### Listen to the audio yourself

After a test run:

```bash
afplay ./tmp/moshi-response.wav  # macOS
# or
aplay ./tmp/moshi-response.wav   # Linux
```

### Check audio properties

```bash
ffprobe ./tmp/moshi-response.wav
```

### Export raw PCM data

```bash
ffmpeg -i ./tmp/moshi-response.wav -f s16le -ac 1 -ar 24000 output.raw
```

## What to Report

If all configurations fail, please report:

1. **Experiment logs**: `./tmp/experiments/*.json`
2. **Sample audio**: `./tmp/moshi-response.wav` (from failed run)
3. **Transcription attempts**: What Whisper returned for each config
4. **Your setup**:
   - OS and version
   - Audio device sample rate (check with `afplay` or `aplay -l`)
   - CPU/GPU being used for MOSHI

## Next Steps After Finding Working Config

Once a configuration produces intelligible audio:

1. The working config will be saved in experiment logs
2. Update `packages/core/src/audio.rs` to use those parameters
3. Test with real voice conversation (`xswarm --dev`)
4. Verify audio quality is acceptable in practice

## Advanced: Adding Custom Configurations

Edit `packages/core/src/moshi_test.rs` and add your config to the `get_next_config_to_test()` function:

```rust
AudioConfig {
    name: "config_6_my_custom".to_string(),
    description: "My custom configuration".to_string(),
    resampler_sinc_len: 256,
    resampler_f_cutoff: 0.98,
    resampler_interpolation: "Linear".to_string(),
    resampler_oversampling: 256,
    resampler_window: "Hann".to_string(),
},
```

Rebuild:
```bash
cargo build --release
```

Run test again:
```bash
xswarm --moshi_test
```

---

**Version:** v0.1.0-2025.11.6.1
**Last Updated:** 2025-11-06
**Author:** Claude Code (xSwarm Development)
