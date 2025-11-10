# MOSHI Integration Notes

Complete history of MOSHI voice integration, debugging, fixes, and lessons learned.

## Current Status (v0.1.0-2025.11.5.0)

### Working
- ✅ MIMI decoder (8 codebooks)
- ✅ Audio generation (1920 samples @ 24kHz per frame)
- ✅ Sample rate resampling (24kHz → 44.1kHz)
- ✅ Audio routing (MOSHI uses same system as greeting tones)
- ✅ Sample rate matching (device at 44.1kHz, audio at 44.1kHz)
- ✅ Audio quality (correct pitch/speed)
- ✅ Continuous audio streaming (buffer queue + single long-lived stream)
- ✅ GPU acceleration enabled (Metal for Apple Silicon, CUDA for NVIDIA)
- ✅ GPU detection API for dashboard display

### Known Requirements
- 🎯 GPU required for real-time performance - CPU mode is 37x too slow (5.25s per 80ms frame)
- 🎯 Apple Silicon (Metal) or NVIDIA GPU (CUDA) needed for usable conversation

## Problem History & Fixes

### Issue 1: MIMI Decoder Codebook Mismatch (v0.1.0-2025.11.3.3)

**Symptom**: "mismatch between the number of layers 31 and the code shape [7, 1, 1]"

**Root Cause**: MIMI initialized with 32 codebooks, MOSHI LM generates only 8 codebooks

**Fix**: Changed `MIMI_NUM_CODEBOOKS` from 32 → 8 in `packages/core/src/voice.rs:85`

**Lesson**: Always match codebook counts between MIMI and LM (8 is standard for MOSHI v0.1)

---

### Issue 2: Sample Rate Resampling Missing (v0.1.0-2025.11.3.5)

**Symptom**: Audio generated successfully but never reached speakers

**Root Cause**: MOSHI generates 24kHz audio, device uses 44.1kHz - no resampling between them

**Fix**: Added automatic resampling 24kHz → 44.1kHz using rubato's sinc interpolation
- `packages/core/src/voice.rs:603-622` - Create resampler
- `packages/core/src/voice.rs:641-661` - Apply resampling before playback

**Result**: 1920 samples @ 24kHz → 3528 samples @ 44.1kHz (same 80ms duration)

**Lesson**: Device sample rates vary - always resample to match device configuration

---

### Issue 3: Architectural Mismatch (v0.1.0-2025.11.4.0) - BREAKTHROUGH

**Symptom**: Audio generated and resampled but still no playback

**Root Cause Discovery**:
- Greeting tones use `AudioOutputDevice::new()` → `play_tone()` → WORKS ✓
- MOSHI used `playback_tx` channel → `playback_rx` → BROKEN ✗
- They were using **completely different audio systems**!

**Fix**: Made MOSHI use the SAME audio system as greeting tones
- `packages/core/src/voice.rs:624-634` - Create AudioOutputDevice in conversation loop
- `packages/core/src/voice.rs:675-691` - Replace `playback_tx.send()` with `audio_output.play_audio_samples()`

**Result**: User heard audio for first time! (but distorted)

**Lesson**: When one audio path works and another doesn't, they're probably using different systems. Use the working one!

---

### Issue 4: Sample Rate Mismatch (v0.1.0-2025.11.4.1)

**Symptom**: "low growl broken with 3-second silences"

**Root Cause**:
- AudioOutputDevice used device default sample rate (16kHz)
- We were sending 44.1kHz audio (3528 samples)
- Device played 44.1kHz audio at 16kHz speed = 0.36x speed = very low pitch "growl"

**Fix**: Modified `AudioOutputDevice::new()` to explicitly request 44.1kHz instead of device default
- `packages/core/src/audio_output.rs:25-121` - Complete rewrite
- Queries device for supported sample rates
- Requests 44.1kHz specifically
- Falls back to device default if not supported

**Result**: Audio now plays at correct pitch and speed!

**Lesson**: Never assume device default sample rate - always query and explicitly request what you need

---

### Issue 5: Frame-by-Frame Playback Gaps (v0.1.0-2025.11.4.2) - FIXED

**Symptom**: "0.5-second clips with 3-second silences"

**Root Cause**:
- Each `play_audio_samples()` creates NEW audio stream
- Plays 80ms of audio (one MOSHI frame)
- Destroys stream
- Waits ~3 seconds for MOSHI to generate next frame
- Repeats

**Timeline**:
```
[00:00.00] Play 80ms audio
[00:00.08] Stream destroyed
[00:00.08-00:03.00] Wait for MOSHI to generate next frame (3 seconds)
[00:03.00] Play next 80ms audio
[00:03.08] Stream destroyed
...repeat
```

**Why This Happens**:
- MOSHI is a real-time conversational AI
- Generates one frame (80ms) at a time
- Takes ~3 seconds to generate each frame
- OLD architecture: generate → play → wait → repeat

**Fix**: Implemented continuous audio streaming with buffer queue

**Implementation**:
1. **Created `start_continuous_stream()` method** (`audio_output.rs:385-546`)
   - Creates VecDeque buffer queue (Arc<Mutex<>>)
   - Spawns tokio task to receive frames and fill queue
   - Creates single long-lived CPAL audio stream
   - Stream callback continuously pops from queue
   - Plays silence when queue empty (prevents gaps)
   - Leaks stream with `Box::leak()` (lives until program exit)

2. **Modified voice.rs conversation loop** (lines 626-640, 681-695)
   - Calls `start_continuous_stream()` once at conversation start
   - Gets `mpsc::Sender<Vec<f32>>` for sending frames
   - Sends each MOSHI frame to stream via channel
   - No more create/destroy per frame!

3. **Solved Send trait issue**
   - CPAL Stream is not Send (contains platform callbacks)
   - Can't move to thread or tokio task
   - Solution: `Box::leak(Box::new(stream))` - intentionally leak it
   - Stream lives for entire program, keeps audio continuous

**Result**: Continuous audio playback without gaps!

**Timeline After Fix**:
```
[00:00.00] Create continuous stream (once)
[00:00.00] Stream playing silence (queue empty)
[00:03.00] MOSHI generates frame 1 → send to queue
[00:03.00] Stream plays frame 1 (80ms)
[00:06.00] MOSHI generates frame 2 → send to queue
[00:03.08] Stream plays frame 2 (80ms) ← no gap!
[00:09.00] MOSHI generates frame 3 → send to queue
[00:06.08] Stream plays frame 3 (80ms) ← no gap!
...continuous audio
```

**Lesson**: For continuous playback, use single long-lived stream + buffer queue, not per-frame streams

---

### Issue 6: GPU Acceleration Not Enabled (v0.1.0-2025.11.5.0) - CRITICAL FIX

**Symptom**: MOSHI takes 5.25 seconds to generate 80ms of audio (37x slower than real-time)

**Root Cause Discovery**:
- Analyzed logs: `lm_generator.step()` takes 5.25 seconds per frame
- This would make real-time conversation impossible (need <200ms per frame)
- Investigated why: Found Candle dependency had **NO GPU features enabled**!
- `Cargo.toml` line 48: `candle = { version = "0.9.1", package = "candle-core" }` ❌
- Missing features: `metal` (Apple Silicon) and `cuda` (NVIDIA)

**Fix**: Enabled GPU acceleration in workspace Cargo.toml
```toml
# Before (CPU-only):
candle = { version = "0.9.1", package = "candle-core" }

# After (GPU-enabled):
candle = { version = "0.9.1", package = "candle-core", features = ["metal", "cuda"] }
```

**Additional Improvements**:
1. Added `GpuInfo` struct for dashboard display
2. Created `detect_gpu()` function to check GPU capabilities
3. Returns cross-platform GPU information (CUDA/Metal/CPU)
4. Dashboard can now show users if real-time MOSHI is possible

**Expected Result**:
- CPU mode: ~5 seconds per frame (unusable for conversation)
- GPU mode: <200ms per frame (real-time conversation possible!)
- This is a **37x performance improvement**

**Files Modified**:
- `Cargo.toml:49` - Added Metal and CUDA features
- `packages/core/src/voice.rs:155-168` - Added GpuInfo struct
- `packages/core/src/voice.rs:374-402` - Added detect_gpu() function
- `packages/core/src/lib.rs:67` - Re-exported GpuInfo for dashboard

**Lesson**: Always enable GPU features for ML inference libraries! CPU-only is too slow for real-time AI.

---

## Architecture Overview

### Audio Pipeline (Current - v0.1.0-2025.11.4.1)

```
Microphone (44.1kHz)
   ↓
Downsample to 24kHz (MOSHI input)
   ↓
MOSHI Processing
   - Transcription
   - LM generates audio tokens (8 codebooks)
   - MIMI decoder generates PCM (1920 samples @ 24kHz)
   ↓
Resample to 44.1kHz (3528 samples)
   ↓
AudioOutputDevice::play_audio_samples()
   - Create new audio stream
   - Play 80ms audio
   - Destroy stream
   ↓
Speakers (44.1kHz)
```

### Audio Pipeline (Needed for Continuous Playback)

```
Microphone (44.1kHz)
   ↓
Downsample to 24kHz
   ↓
MOSHI Processing (continuous generation)
   ↓
Audio Buffer Queue
   - Queue frames as they're generated
   - Always keep buffer ahead of playback
   ↓
Single Long-Lived Audio Stream
   - Continuously consume from queue
   - No gaps between frames
   ↓
Speakers (44.1kHz)
```

## Key Technical Details

### Sample Rates

**MOSHI Native**: 24,000 Hz
- Frame size: 1920 samples
- Frame duration: 1920 / 24000 = 80ms

**Device Output**: 44,100 Hz (CD quality)
- Frame size: 3528 samples (after resampling)
- Frame duration: 3528 / 44100 = 80ms ✓
- Resampling ratio: 44100 / 24000 = 1.8375

**Why 44.1kHz?**
- Standard CD quality
- Supported by virtually all modern devices
- Nyquist frequency 22.05kHz covers human hearing (20Hz-20kHz)
- MOSHI's 24kHz resamples cleanly (1.8375x ratio)

### Codebook Configuration

**MOSHI v0.1 Standard**:
- `MIMI_NUM_CODEBOOKS = 8`
- `generated_audio_codebooks = 8`
- Tensor shape: `[1, 8, 1]` per frame

**DO NOT use 32 codebooks** (wrong assumption, causes decoder errors)

### Audio Stream Lifecycle

**Current (Frame-by-Frame)**:
```rust
// For EACH 80ms frame:
1. Create stream with device.build_output_stream()
2. stream.play()
3. Wait for duration (80ms + 20ms buffer)
4. drop(stream)  // Destroys stream
5. Wait ~3 seconds for next MOSHI frame
6. Repeat
```

**Needed (Continuous)**:
```rust
// Once at startup:
1. Create stream with device.build_output_stream()
2. stream.play()
3. Stream callback continuously reads from queue
4. Queue fills as MOSHI generates frames
5. Stream stays alive for entire conversation
6. drop(stream) only when conversation ends
```

## Code Locations

### Voice Processing
- `packages/core/src/voice.rs:85` - MIMI_NUM_CODEBOOKS constant (8)
- `packages/core/src/voice.rs:603-622` - Resampler creation (24kHz → 44.1kHz)
- `packages/core/src/voice.rs:624-634` - AudioOutputDevice creation
- `packages/core/src/voice.rs:641-661` - Resampling before playback
- `packages/core/src/voice.rs:675-691` - Direct audio playback

### Audio Output
- `packages/core/src/audio_output.rs:25-121` - AudioOutputDevice initialization (44.1kHz)
- `packages/core/src/audio_output.rs:106-237` - play_audio_samples() (frame-by-frame)

### MIMI Codec
- `packages/moshi/moshi-core/src/mimi.rs:214-222` - MIMI decode_step
- `packages/moshi/moshi-core/src/quantization.rs:234-251` - Codebook validation

### Audio Resampling
- `packages/core/src/audio.rs:153-223` - AudioResampler (rubato sinc)

## Next Steps

### Priority 1: Fix 3-Second Gaps

**Goal**: Continuous audio playback without gaps

**Approach**:
1. Create audio buffer queue (Arc<Mutex<VecDeque<Vec<f32>>>>)
2. Producer: MOSHI generates frames → push to queue
3. Consumer: Audio stream callback → pop from queue
4. Keep stream alive for entire conversation
5. Handle underflow gracefully (play silence if queue empty)

**Implementation Plan**:
- Modify `voice.rs` conversation loop to push frames to queue
- Create single long-lived audio stream at conversation start
- Stream callback reads from queue continuously
- Add queue monitoring (warn if buffer too low/high)

**Expected Result**: Smooth, continuous audio playback

### Priority 2: Optimize Latency

**Goal**: Reduce ~3 second generation time per frame

**Approaches**:
1. Async frame generation (generate next while playing current)
2. Model optimization (smaller/faster MOSHI variant)
3. GPU acceleration (if available)
4. Frame prefetching

**Future work** - focus on continuous playback first

## Lessons Learned

### 1. Audio Architecture
- **Use working audio paths**: When one path works (greeting tones) and another doesn't (MOSHI), use the working one
- **Same system = consistency**: Don't create separate audio systems for different features
- **Test early, test often**: Small audio test cases (beeps) help validate the pipeline

### 2. Sample Rates
- **Never assume device defaults**: Always query and explicitly request sample rate
- **Resample everything**: Different components may use different sample rates (MOSHI 24kHz, device 44.1kHz)
- **Log sample rates**: Always log actual device configuration for debugging
- **Standard rates**: 44.1kHz and 48kHz are most common, 16kHz/24kHz need resampling

### 3. Debugging Audio Issues
- **Start from working examples**: Greeting tones worked - used same system for MOSHI
- **Check the pipeline**: Audio generation → resampling → routing → playback (test each stage)
- **Log everything**: Sample counts, sample rates, RMS amplitude, channel operations
- **Compare with working code**: moshi-backend uses 8 codebooks, we should too

### 4. MOSHI-Specific
- **8 codebooks is standard**: Don't use 32 (wrong assumption from old docs)
- **Match LM config**: generated_audio_codebooks must equal MIMI_NUM_CODEBOOKS
- **Frame-by-frame generation**: MOSHI generates 80ms frames, need buffering for continuity
- **Real-time processing**: ~3 seconds per frame is current generation speed

### 5. Rust/CPAL Audio
- **Stream lifecycle matters**: Creating/destroying streams is expensive and causes gaps
- **One stream per conversation**: Keep stream alive, feed it continuously
- **Box::leak() for non-Send streams**: CPAL Stream is not Send - intentionally leak it with Box::leak()
- **Buffer queue pattern**: VecDeque + Arc<Mutex<>> + mpsc channel = smooth playback
- **Buffer underflow handling**: Always have fallback (silence) when queue is empty

### 6. Development Process
- **Incremental fixes**: Each version fixed one specific issue
- **Version tracking**: Clear version numbers help track which fix did what
- **Log analysis**: Logs revealed each issue (codebook mismatch, sample rate, etc.)
- **User feedback essential**: "low growl" → sample rate mismatch, "3-second gaps" → frame-by-frame

## Version History

- **v0.1.0-2025.11.3.3**: Fixed MIMI codebook mismatch (32→8)
- **v0.1.0-2025.11.3.4**: Added playback channel debug logging
- **v0.1.0-2025.11.3.5**: Added sample rate resampling (24kHz→44.1kHz)
- **v0.1.0-2025.11.3.6**: Added playback receiver diagnostics
- **v0.1.0-2025.11.4.0**: Fixed audio architecture (MOSHI uses greeting tone system)
- **v0.1.0-2025.11.4.1**: Fixed sample rate mismatch (device at 44.1kHz)
- **v0.1.0-2025.11.4.2**: Fixed 3-second gaps (continuous audio streaming with buffer queue)
- **v0.1.0-2025.11.5.0**: Enabled GPU acceleration (Metal/CUDA) + GPU detection API - **CURRENT**

## References

### MOSHI Documentation
- Kyutai MOSHI: https://github.com/kyutai-labs/moshi
- MIMI Codec: https://kyutai.org/mimi.html
- moshi-backend config: Uses 8 codebooks consistently

### Audio Processing
- CPAL (Cross-Platform Audio Library): https://github.com/RustAudio/cpal
- rubato (Rust resampling): https://github.com/HEnquist/rubato
- Sample rate conversion: https://en.wikipedia.org/wiki/Sample-rate_conversion

### Testing
- Log file: `~/.cache/xswarm/xswarm.log`
- Build command: `cargo build --release --bin xswarm`
- Install: `cp target/release/xswarm ~/.local/bin/xswarm`
- Run: `xswarm --dev`

---

**Last Updated**: 2025-11-05 (v0.1.0-2025.11.5.0)
**Status**: GPU acceleration enabled! Continuous audio streaming working. MOSHI should now run in real-time on systems with Metal (Apple Silicon) or CUDA (NVIDIA GPU).
