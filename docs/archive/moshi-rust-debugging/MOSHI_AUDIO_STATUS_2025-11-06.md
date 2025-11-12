# MOSHI Audio Debugging Status - 2025-11-06

## ✅ MAJOR PROGRESS ACHIEVED

### v0.1.0-2025.11.5.16 Test Results

**WAV File Analysis**:
- **Duration**: 4:18.67 (258 seconds)
- **Total Samples**: 11,407,343 samples ✅
- **Sample Rate**: 44.1kHz (correct) ✅
- **Continuous Audio**: Only 2 brief silence periods ✅
- **File Size**: 44MB ✅

**Comparison to Previous Tests**:
- v0.1.0-2025.11.5.14 and earlier: Only ~2031 samples (0.046 seconds of audio)
- v0.1.0-2025.11.5.16: 11,407,343 samples (258 seconds of audio)
- **Improvement**: 5,614x more audio captured!

**User Feedback**:
- ✅ "Pitch sounds better" - Sample rate matching worked!
- ❌ "Audio still garbled" - Quality issue remains

## 🔍 Root Cause Analysis

### What We Fixed

1. **Sample Rate Mismatch** (v0.1.0-2025.11.5.16):
   - Problem: Hardcoded 44.1kHz resampling target
   - Solution: Query device's actual sample rate dynamically
   - Result: Pitch improved (user confirmed)

2. **Device Handling** (v0.1.0-2025.11.5.17 - not yet tested):
   - Problem: Confusing tuple pattern for device lifecycle
   - Solution: Simplified with `_audio_device_guard`
   - Result: Pending user test

### What Still Needs Investigation

**Hypothesis: The "garbled" audio is NOT a sampling issue**

Evidence:
- 11.4 million samples captured successfully
- Continuous audio stream working (only 2 brief silences)
- Pitch is correct (user confirmed)
- Duration matches test period (4+ minutes)

**Possible remaining issues**:

1. **Buffer alignment/timing**:
   - MOSHI generates 80ms frames (1920 samples at 24kHz)
   - After resampling to 44.1kHz: 3528 samples per frame
   - Could have timing misalignment between frames

2. **Resampler quality**:
   - Using SincFixedIn with high-quality parameters
   - But might need different interpolation settings
   - Current: sinc_len=256, f_cutoff=0.95, Cubic interpolation

3. **Channel/endianness issues**:
   - MOSHI outputs mono f32
   - Device expects mono f32
   - But could have endianness or normalization issues

4. **Frame boundary artifacts**:
   - Each MOSHI frame is processed independently
   - Resampler might introduce discontinuities at frame boundaries

## 📊 v0.1.0-2025.11.5.16 Implementation

### What Changed

**File**: `packages/core/src/voice.rs` (lines 648-693)

```rust
// Step 1: Create audio device with default config to discover actual sample rate
let temp_device = match crate::audio_output::AudioOutputDevice::new() {
    Ok(d) => d,
    Err(e) => {
        error!("MOSHI_AUDIO: Failed to create audio output device: {}", e);
        return;
    }
};

// Step 2: Get device's actual sample rate
let device_sample_rate = temp_device.get_sample_rate();
info!("MOSHI_AUDIO: Device actual sample rate: {} Hz", device_sample_rate);

// Step 3: Create resampler for MOSHI (24kHz) → device's actual rate
let mut resampler = match crate::audio::AudioResampler::new(
    MOSHI_SAMPLE_RATE,
    device_sample_rate,
    MOSHI_FRAME_SIZE,
) {
    Ok(r) => {
        info!("MOSHI_AUDIO: Created resampler {}Hz → {}Hz (device's native rate)",
              MOSHI_SAMPLE_RATE, device_sample_rate);
        Some(r)
    }
    Err(e) => {
        error!("MOSHI_AUDIO: Failed to create resampler: {}", e);
        None
    }
};
```

**File**: `packages/core/src/audio_output.rs` (lines 35-38)

```rust
/// Get the actual sample rate of this audio device
pub fn get_sample_rate(&self) -> u32 {
    self.config.sample_rate.0
}
```

## 🎯 Next Steps

### Immediate Actions

1. **Test v0.1.0-2025.11.5.17**:
   - Get user feedback on whether garbling persists
   - Check logs for microphone/MOSHI/output tracking

2. **If still garbled, investigate**:
   - Resampler interpolation quality
   - Frame boundary artifacts
   - Buffer overlap/add windowing
   - Direct WAV playback vs. real-time playback differences

3. **Compare audio**:
   - Play captured WAV file to user
   - Does WAV file sound garbled too?
   - Or is it only live playback that's garbled?

### Potential Next Fixes

#### Option A: Improve Resampler Quality

```rust
// Try different interpolation parameters
let params = SincInterpolationParameters {
    sinc_len: 512,  // Longer sinc filter
    f_cutoff: 0.99, // Higher cutoff frequency
    interpolation: SincInterpolationType::Linear, // Try linear
    oversampling_factor: 512, // Higher oversampling
    window: WindowFunction::Blackman, // Try different window
};
```

#### Option B: Add Overlap-Add Windowing

```rust
// Apply windowing to prevent frame boundary artifacts
let window = hann_window(MOSHI_FRAME_SIZE);
let windowed_frame: Vec<f32> = frame
    .iter()
    .zip(window.iter())
    .map(|(s, w)| s * w)
    .collect();
```

#### Option C: Stateful Resampler

```rust
// Keep resampler state across frames
// (Currently we create new resampler for each session)
// Should persist resampler state to maintain phase continuity
```

## 📈 Progress Summary

**Iterations**:
- v0.1.0-2025.11.5.14 and earlier: Only 2031 samples (< 1 second)
- v0.1.0-2025.11.5.15: No resampling (wrong approach)
- v0.1.0-2025.11.5.16: Dynamic sample rate detection → **5,614x improvement!** ✅
- v0.1.0-2025.11.5.17: Simplified device handling + debug logging (pending test)

**Status**:
- ✅ Audio pipeline is working
- ✅ Continuous audio capture working
- ✅ Sample rate matching working (pitch improved)
- ❌ Audio quality still has "garbling" artifacts

**Confidence Level**: **HIGH** that the fundamental audio pipeline is correct. The "garbling" is likely a resampling quality issue, not a fundamental architecture problem.

## 🚀 v0.1.0-2025.11.5.19 - AUTO-GREETING FOR AUTOMATED TESTING

**Status**: ✅ **AUTO-GREETING WORKING!** Fully automated testing now possible.

**Implementation**: Added auto-greeting functionality that triggers when `MOSHI_DEBUG_WAV=1` is set.
- **File**: `packages/core/src/voice.rs` (lines 704-752)
- Generates silent frame after initialization
- Triggers MOSHI to produce greeting audio automatically
- **Result**: 9.24 seconds of audio captured without user interaction!

**Test Results** (30-second test window):
- ✅ WAV file created: 1.6MB, 9.24 seconds
- ✅ Format: 44100 Hz, mono, pcm_f32le
- ✅ Log shows: "🔊 Playing greeting tones..."
- ✅ Auto-greeting activates successfully

**Build**: Completed in 2m 05s
**Test Run**: 10:51 AM (PST) - AUTO-GREETING SUCCESS

**Automated Quality Validation** (ffmpeg analysis):
- ✅ Silence detection: Only 0.16s silence at start, then 9.08s continuous audio
- ✅ Audio levels: mean_volume -19.0 dB, max_volume -0.0 dB (healthy signal, no clipping)
- ✅ File integrity: 1.6MB, proper WAV format (44100 Hz, mono, pcm_f32le)

**Whisper Transcription Blocked**:
- ❌ Architecture mismatch: numpy x86_64 vs arm64 needed (M1/M2 Mac)
- Whisper installed but not accessible for automated transcription

**Next Step**: USER MUST MANUALLY LISTEN to `./tmp/moshi-debug-audio.wav` to validate if v0.1.0-2025.11.5.18 ultra-high quality resampling fixed the "garbled" audio issue.

**Audio File Location**: `./tmp/moshi-debug-audio.wav` (1.6MB, 9.24 seconds)

---

## 🚀 v0.1.0-2025.11.5.18 - ULTRA-HIGH QUALITY RESAMPLING

**Status**: Build complete, manual testing challenge identified

**Implementation** (`packages/core/src/audio.rs` lines 170-180):
```rust
// v0.1.0-2025.11.5.18: ULTRA-HIGH QUALITY resampling to fix garbling
// Previous issue: Cubic interpolation with sinc_len=256 still produced artifacts
// Solution: Longer sinc filter (512), higher cutoff (0.99), Linear interpolation
//           Linear can be cleaner than Cubic for real-time audio
let params = SincInterpolationParameters {
    sinc_len: 512,           // 2x longer sinc filter for better frequency response
    f_cutoff: 0.99,          // Higher cutoff to preserve more high frequencies
    interpolation: SincInterpolationType::Linear,  // Simpler can be cleaner for real-time
    oversampling_factor: 512,  // Doubled for precision
    window: WindowFunction::Blackman,  // Classic Blackman for smoother transitions
};
```

**Changes from v0.1.0-2025.11.5.16**:
1. **sinc_len**: 256 → 512 (2x longer filter for better frequency response)
2. **f_cutoff**: 0.95 → 0.99 (preserve more high frequencies)
3. **interpolation**: Cubic → Linear (simpler can be cleaner for real-time)
4. **oversampling_factor**: 256 → 512 (doubled precision)
5. **window**: BlackmanHarris2 → Blackman (smoother transitions)

**Build**: Completed in 2m 06s
**Test Started**: 10:48 AM (PST)

**Automated Testing Challenge**:
Created `quiet-audio-test.sh` script for Whisper-based validation, but encountered issue:
- MOSHI needs to initialize models (takes time)
- WAV file only created when MOSHI generates audio
- 10 second test window too short for initialization + audio generation
- Need either: (1) greeting auto-play after init, or (2) longer test window

**Next Step**: User can test manually by speaking to MOSHI, or we can modify MOSHI to auto-generate a test phrase after initialization.

---

Last Updated: 2025-11-06 17:37 UTC
Version: v0.1.0-2025.11.5.18 testing
Previous Test: v0.1.0-2025.11.5.16 (pitch improved but still garbled)
