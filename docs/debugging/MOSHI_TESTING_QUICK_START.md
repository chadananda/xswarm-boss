# MOSHI Audio Testing - Quick Start Guide

## Current Status

✅ **Automated tests show MOSHI produces intelligible speech** (recorded audio)
❓ **Real-time playback needs verification** (user reported garbled audio)

## Quick Commands

### 1. Standard Test (Automated, uses quiet noise)
```bash
export OPENAI_API_KEY=your_openai_key_here  # Get from .env
./target/release/xswarm --moshi-test
```

**What this does:**
- Generates 1 second of quiet noise
- Processes through MOSHI
- Transcribes output with Whisper API
- Reports if audio is intelligible

**Expected result:** ✅ PASS (audio is intelligible)

### 2. Real Voice Test (Interactive, records your voice)
```bash
export OPENAI_API_KEY=your_openai_key_here  # Get from .env
./scripts/test-real-voice-input.sh
```

**What this does:**
- Records 3 seconds of your voice using sox
- Processes through MOSHI
- Transcribes output with Whisper API
- Shows what MOSHI understood and responded

**Requires:** sox (`brew install sox` on macOS)

### 3. Real-Time Conversation (CRITICAL TEST)
```bash
./target/release/xswarm --dev
# Then speak to MOSHI
# Listen carefully: Is the response garbled or clear?
```

**This is the most important test** because:
- Recorded tests show audio is intelligible ✅
- User reported real-time audio was garbled ❌
- This test will confirm if the issue is fixed

### 4. Custom Audio File Test
```bash
export OPENAI_API_KEY=your_openai_key_here  # Get from .env
export MOSHI_TEST_INPUT=./path/to/your/audio.wav
./target/release/xswarm --moshi-test
```

**Requirements:**
- Audio must be 24kHz, mono, 16-bit PCM WAV
- Any duration (typically 1-5 seconds)

## Test Results Location

All test outputs are in `./tmp/` (gitignored):

- `./tmp/test-user-hello.wav` - Auto-generated test input
- `./tmp/moshi-response.wav` - MOSHI's response ✅ Confirmed intelligible
- `./tmp/test-real-speech.wav` - Your recorded voice (from script)
- `./tmp/experiments/*.json` - Test result logs

## What We Know

### ✅ Working (Confirmed)
1. MIMI encode/decode with 8 codebooks (not 32)
2. Resampler with ultra-high quality settings
3. Recorded audio files are intelligible
4. Whisper API can transcribe MOSHI output

### ❓ Unknown (Needs Testing)
1. Real-time conversation audio quality
2. Response to actual speech input (not just noise)
3. Consistency across different voices/accents
4. Quality on different audio devices

### ❌ Known Issues (Fixed)
1. ~~MIMI used 32 codebooks instead of 8~~ → Fixed in commit c7efafd
2. ~~Whisper API hallucination~~ → Now understood, test designed around it

## Next Steps (Priority Order)

### 🔴 HIGH PRIORITY: Test Real-Time Playback
```bash
./target/release/xswarm --dev
```
**Goal:** Verify if the "garbled chunky nonsense" issue is resolved

### 🟡 MEDIUM PRIORITY: Test Real Voice
```bash
./scripts/test-real-voice-input.sh
```
**Goal:** Verify MOSHI handles real speech input correctly

### 🟢 LOW PRIORITY: Investigate Real-Time vs Recorded Difference
If real-time is garbled but recordings are clear:
- Issue is in `audio_output.rs` streaming
- Not in core MOSHI audio processing
- May need buffer management fixes

## Troubleshooting

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY=your_openai_key_here  # Get from .env
```

### "sox: command not found"
```bash
brew install sox
```

### "Failed to load test WAV file"
- Check file exists: `ls -lh ./tmp/test-user-hello.wav`
- Check format: `soxi ./tmp/test-user-hello.wav`
- Should be: 24kHz, mono, 16-bit PCM

### "All configurations tested"
Reset experiment history:
```bash
rm -rf ./tmp/experiments/
```

## Understanding Test Results

### ✅ Success (Intelligible)
```
║ 📝 Transcription:
║    "Hello! How can I help you today?"
║ 📊 Analysis:
║    Words detected: 7
║ ✅ SUCCESS: Audio contains recognizable speech!
```

### ❌ Failure (Garbled)
```
║ 📝 Transcription:
║    ""
║ 📊 Analysis:
║    Words detected: 0
║ ❌ FAILURE: No recognizable words detected
```

**Note:** Whisper may hallucinate text even from garbled audio! Check word count - if it varies between runs of the same audio, it's hallucinating.

## Cost

- Per test: ~$0.0006 (Whisper API for 2 seconds of audio)
- 100 tests: ~$0.06
- Very cheap for debugging!

## Recent Changes (v0.1.0-2025.11.6.3)

1. ✅ Support for `MOSHI_TEST_INPUT` environment variable
2. ✅ Created `scripts/test-real-voice-input.sh`
3. ✅ Updated `voice.rs` to use custom test input paths
4. ✅ Build successful with all changes

## Files Modified

- `packages/core/src/main.rs` - Lines 738-751 (custom input support)
- `packages/core/src/voice.rs` - Lines 1027-1028 (custom path)
- `scripts/test-real-voice-input.sh` - NEW (real voice testing)

---

**Version:** v0.1.0-2025.11.6.3
**Status:** Ready for real-time playback verification
**Next:** Run `./target/release/xswarm --dev` and test actual conversation
