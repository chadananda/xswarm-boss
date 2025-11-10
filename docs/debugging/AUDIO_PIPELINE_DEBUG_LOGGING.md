# Audio Pipeline Debug Logging Implementation

## Summary

Added comprehensive debug logging to trace the audio flow from microphone input to MOSHI processing in the local voice conversation loop.

## Implementation Date

2025-11-02

## Problem Statement

Previous debugging showed:
- MOSHI system initializes successfully (shows "✅ MOSHI voice system ready!")
- Dashboard shows microphone activity: "Mic: ▍ ▎ ▌"
- But the 29 "MOSHI_DEBUG:" logs inside the `process_with_lm()` function were not appearing
- This suggested MOSHI's `process_with_lm()` function was not being called at all

## Root Cause Hypothesis

The issue appears to be in the audio pipeline between:
1. Microphone capturing audio frames
2. Frames being sent through the channel
3. Frames arriving at the conversation loop
4. MOSHI processing being invoked

## Solution: Audio Pipeline Tracing

Added detailed logging at each stage of the audio pipeline with "AUDIO_PIPELINE:" prefix for easy filtering.

### Modified File

**`/packages/core/src/voice.rs`**

### Debug Logging Added

#### 1. **Loop Initialization**
```rust
info!("AUDIO_PIPELINE: Conversation loop initialized, waiting for microphone frames");
```
- Confirms the conversation loop starts successfully
- Indicates readiness to receive microphone data

#### 2. **Frame Reception**
```rust
info!(
    "AUDIO_PIPELINE: [Frame #{}] Received from microphone - samples={}",
    frame_count,
    audio_frame.samples.len()
);
```
- Logs EVERY frame received from the microphone
- Tracks frame sequence number
- Shows sample count per frame

#### 3. **Audio Data Validation**
```rust
let non_zero_count = audio_frame.samples.iter().filter(|&&s| s.abs() > 0.001).count();
let rms = /* RMS calculation */;

info!(
    "AUDIO_PIPELINE: [Frame #{}] Audio data - non_zero_samples={}/{}, rms={:.6}",
    frame_count,
    non_zero_count,
    audio_frame.samples.len(),
    rms
);
```
- Counts non-zero samples (detects silence vs. actual audio)
- Calculates RMS amplitude (signal strength)
- Helps identify if microphone is sending valid audio data

#### 4. **Buffer Status**
```rust
info!(
    "AUDIO_PIPELINE: [Frame #{}] Added to buffer - buffer_size={}, MOSHI_FRAME_SIZE={}, ready={}",
    frame_count,
    audio_buffer.len(),
    MOSHI_FRAME_SIZE,
    audio_buffer.len() >= MOSHI_FRAME_SIZE
);
```
- Shows buffer accumulation status
- Indicates when buffer has enough samples for MOSHI processing
- Confirms buffer logic is working correctly

#### 5. **MOSHI Frame Extraction**
```rust
info!(
    "AUDIO_PIPELINE: [Frame #{}] MOSHI frame ready - extracted {} samples, {} remaining in buffer",
    frame_count,
    frame.len(),
    audio_buffer.len()
);
```
- Confirms when a full MOSHI frame (1920 samples) is extracted
- Shows remaining buffer size after extraction

#### 6. **Before MOSHI Processing**
```rust
let frame_rms = /* Calculate RMS of frame about to be processed */;

info!(
    "AUDIO_PIPELINE: [Frame #{}] CALLING process_with_lm() - frame_size={}, frame_rms={:.6}",
    frame_count,
    frame.len(),
    frame_rms
);
```
- **CRITICAL**: Shows exactly when `process_with_lm()` is being called
- Includes frame RMS to verify audio quality
- This log should trigger the 29 "MOSHI_DEBUG:" logs inside `process_with_lm()`

#### 7. **After MOSHI Processing**
```rust
// On success:
info!(
    "AUDIO_PIPELINE: [Frame #{}] process_with_lm() SUCCESS - response_samples={}",
    frame_count,
    response_pcm.len()
);

// On error:
error!("AUDIO_PIPELINE: [Frame #{}] process_with_lm() FAILED: {}", frame_count, e);
```
- Confirms successful processing
- Shows response size
- Logs any errors during processing

#### 8. **Speaker Output**
```rust
info!(
    "AUDIO_PIPELINE: [Frame #{}] Response sent to speakers - samples={}",
    frame_count,
    response_pcm.len()
);
```
- Confirms audio was sent to playback system
- Shows final output sample count

## Expected Behavior

With these logs, we should see:

1. **If microphone is working:**
   - "AUDIO_PIPELINE: Conversation loop initialized"
   - "AUDIO_PIPELINE: [Frame #1] Received from microphone"
   - "AUDIO_PIPELINE: [Frame #1] Audio data - non_zero_samples=..."
   - Continues for every frame

2. **If buffer accumulation works:**
   - "AUDIO_PIPELINE: [Frame #X] Added to buffer - ready=true"
   - "AUDIO_PIPELINE: [Frame #X] MOSHI frame ready - extracted 1920 samples"

3. **If MOSHI processing is called:**
   - "AUDIO_PIPELINE: [Frame #X] CALLING process_with_lm()"
   - **Then we should see the 29 "MOSHI_DEBUG:" logs**
   - "AUDIO_PIPELINE: [Frame #X] process_with_lm() SUCCESS"

4. **If MOSHI processing is NOT called:**
   - We'll see microphone frames arriving and buffer filling
   - But NO "CALLING process_with_lm()" logs
   - This pinpoints the exact failure point

## Diagnostic Questions Answered

These logs will definitively answer:

- **Q1**: Are microphone frames arriving at the conversation loop?
  - **A**: Check for "Received from microphone" logs

- **Q2**: Is the audio data valid (not silence)?
  - **A**: Check `non_zero_samples` and `rms` values

- **Q3**: Is the buffer accumulating correctly?
  - **A**: Check "Added to buffer" logs showing increasing `buffer_size`

- **Q4**: Is MOSHI frame extraction working?
  - **A**: Check for "MOSHI frame ready - extracted 1920 samples"

- **Q5**: Is `process_with_lm()` being called?
  - **A**: Check for "CALLING process_with_lm()" logs

- **Q6**: If called, does it succeed or fail?
  - **A**: Check for "SUCCESS" or "FAILED" logs after the call

## How to Use

### View All Audio Pipeline Logs
```bash
cargo run --release 2>&1 | grep "AUDIO_PIPELINE:"
```

### View Just Frame Reception
```bash
cargo run --release 2>&1 | grep "AUDIO_PIPELINE:.*Received from microphone"
```

### View Just MOSHI Calls
```bash
cargo run --release 2>&1 | grep "AUDIO_PIPELINE:.*process_with_lm"
```

### View Combined Pipeline + MOSHI Debug
```bash
cargo run --release 2>&1 | grep -E "(AUDIO_PIPELINE:|MOSHI_DEBUG:)"
```

## Next Steps

1. Run the application with these logs enabled
2. Identify which stage of the pipeline is failing
3. Based on findings:
   - **If no frames received**: Issue with microphone channel setup
   - **If frames are silence**: Issue with microphone capture or permissions
   - **If buffer not filling**: Issue with buffer logic
   - **If MOSHI not called**: Issue with frame extraction logic
   - **If MOSHI called but fails**: Issue inside MOSHI processing (29 debug logs will show where)

## Files Modified

- `/packages/core/src/voice.rs` - Added audio pipeline debug logging to `start_local_conversation()` function

## Compilation Status

✅ Successfully compiled with `cargo build --release`
- Added logging does not affect runtime performance significantly
- All logs use `info!()` level for visibility during debugging
- Can be filtered easily with grep for targeted analysis
