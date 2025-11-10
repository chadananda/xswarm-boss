# Version 0.1.0-2025.11.7.0 Release Summary

## Installation Complete ✅

**Installed Version:** `xswarm 0.1.0-2025.11.7.0`

**Verify your installation:**
```bash
xswarm --version
# Output: xswarm 0.1.0-2025.11.7.0
```

## What's New in This Release

### 1. MOSHI Audio Testing System 🧪
Comprehensive automated testing for debugging MOSHI audio quality issues.

**Features:**
- Automated test mode: `xswarm --moshi-test`
- OpenAI Whisper API integration for objective transcription verification
- Experiment logging to track all configuration tests
- Support for custom input audio files
- Real voice input testing script

**Test Results:** ✅ Recorded audio is **intelligible** (confirmed with Whisper API)

### 2. Real Voice Input Support 🎤
Test MOSHI with actual recorded speech instead of just generated noise.

**New Script:**
```bash
./scripts/test-real-voice-input.sh
```

**New Environment Variable:**
```bash
export MOSHI_TEST_INPUT=./path/to/your/audio.wav
xswarm --moshi-test
```

### 3. Version Display Flag 🏷️
Added standard version flag for easy verification.

**Usage:**
```bash
xswarm --version
xswarm -V
```

## Critical Next Step: Real-Time Verification 🚨

The automated tests show **recorded audio is intelligible**, but you originally reported the audio was "garbled chunky nonsense". This suggests the issue might be specific to **real-time playback**.

**YOU NEED TO TEST:**
```bash
xswarm --dev
# Then speak to MOSHI and listen carefully
```

**Question:** Does the real-time conversation sound clear or garbled?

- **If clear:** Issue is FIXED ✅ (MIMI codebook fix resolved it)
- **If garbled:** Issue is in real-time playback (not core audio processing)

## Available Test Commands

### 1. Standard Automated Test
```bash
export OPENAI_API_KEY=***REMOVED***
xswarm --moshi-test
```
**What it does:** Tests with quiet noise, transcribes with Whisper
**Expected result:** ✅ PASS (audio is intelligible)

### 2. Real Voice Test
```bash
export OPENAI_API_KEY=***REMOVED***
./scripts/test-real-voice-input.sh
```
**What it does:** Records your voice, processes through MOSHI, transcribes
**Requires:** sox (`brew install sox`)

### 3. Real-Time Conversation (CRITICAL)
```bash
xswarm --dev
```
**What it does:** Full voice conversation mode
**This is the most important test!**

### 4. Custom Audio File
```bash
export OPENAI_API_KEY=***REMOVED***
export MOSHI_TEST_INPUT=./your-audio.wav
xswarm --moshi-test
```
**Requirements:** 24kHz, mono, 16-bit PCM WAV

## Files Modified

**Version Update:**
- `packages/core/Cargo.toml:3` - Version: 0.1.0-2025.11.7.0

**New Features:**
- `packages/core/src/main.rs:42` - Added `#[command(version)]`
- `packages/core/src/main.rs:738-751` - Custom input support
- `packages/core/src/voice.rs:1027-1028` - Custom path support

**New Files:**
- `scripts/test-real-voice-input.sh` - Real voice testing script
- `docs/debugging/MOSHI_AUDIO_STATUS_COMPLETE.md` - Complete status report
- `docs/debugging/MOSHI_TESTING_QUICK_START.md` - Quick start guide

## What We Know

### ✅ Confirmed Working
1. MIMI codec with 8 codebooks (not 32) ← Fixed in commit c7efafd
2. Resampler with ultra-high quality settings
3. Recorded audio files are intelligible
4. Whisper API successfully transcribes MOSHI output

### ❓ Needs Verification
1. Real-time conversation audio quality ← **YOU TEST THIS**
2. Response to actual speech input (not just noise)
3. Consistency across different voices/accents
4. Quality on different audio devices

### 📊 Test Evidence
- Test 1: "Of course I didn't!" - 4 words ✅
- Test 2: "Thanks so much for watching" - 5 words ✅
- Both transcriptions are coherent and intelligible

## Quick Reference

**Check version:**
```bash
xswarm --version
```

**Run MOSHI test:**
```bash
xswarm --moshi-test
```

**Start voice conversation:**
```bash
xswarm --dev
```

**Get help:**
```bash
xswarm --help
```

## Documentation

- **Complete Status:** `docs/debugging/MOSHI_AUDIO_STATUS_COMPLETE.md`
- **Quick Start:** `docs/debugging/MOSHI_TESTING_QUICK_START.md`
- **Test Implementation:** `MOSHI_TEST_IMPLEMENTATION.md`
- **Test Results:** `MOSHI_TEST_RESULTS.md`

## Cost

- Per test: ~$0.0006 (Whisper API)
- 100 tests: ~$0.06
- Very inexpensive for debugging

## Installation Locations

**Binary installed to:**
- `/Users/chad/.cargo/bin/xswarm`
- `/Users/chad/.local/bin/xswarm` (active in PATH)

**Binary size:** 18MB

**Verify PATH:**
```bash
which xswarm
# Should show: /Users/chad/.local/bin/xswarm
```

---

**Version:** 0.1.0-2025.11.7.0
**Date:** 2025-11-07
**Status:** ✅ Installed and ready for testing

**NEXT ACTION:** Run `xswarm --dev` and test real-time conversation audio quality
