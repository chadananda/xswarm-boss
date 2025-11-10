# Audio Pipeline Debug Implementation

## Date: 2025-11-02

## Problem Statement
The MOSHI voice system initializes successfully and the microphone captures audio, but no voice responses are generated. The `start_local_conversation()` function appears to never receive audio frames from the microphone input.

## Root Cause Hypothesis
The audio pipeline has a connection issue between:
1. Microphone input detection (LocalAudioSystem)
2. Broadcast channel forwarding
3. MOSHI conversation handler (`start_local_conversation()`)

## Debug Infrastructure Added

### Location 1: Audio Broadcast System (dashboard.rs:764-799)
Added comprehensive logging to trace microphone frames as they're broadcast to subscribers:

```rust
// Log every frame received from microphone
info!(
    "AUDIO_BROADCAST: [Frame #{}] Received from microphone - samples={}, broadcasting to {} subscribers",
    frame_count,
    audio_frame.samples.len(),
    audio_broadcast_tx_clone.receiver_count()
);

// Log broadcast success/failure
match audio_broadcast_tx_clone.send(audio_frame) {
    Ok(subscriber_count) => {
        info!("AUDIO_BROADCAST: [Frame #{}] Successfully broadcast to {} subscribers", ...);
    }
    Err(e) => {
        error!("AUDIO_BROADCAST: [Frame #{}] Broadcast failed: {} - no receivers, stopping", ...);
    }
}
```

**Expected Output:**
```
AUDIO_BROADCAST: Starting to forward microphone frames to broadcast channel
AUDIO_BROADCAST: [Frame #1] Received from microphone - samples=1024, broadcasting to 2 subscribers
AUDIO_BROADCAST: [Frame #1] Successfully broadcast to 2 subscribers
AUDIO_BROADCAST: [Frame #2] Received from microphone - samples=1024, broadcasting to 2 subscribers
...
```

### Location 2: Audio Bridge Forwarding Task (dashboard.rs:1030-1051)
Added logging to trace frames as they're forwarded from broadcast to MOSHI unbounded channel:

```rust
tokio::spawn(async move {
    info!("AUDIO_BRIDGE: Forwarding task started - listening for broadcast frames");
    let mut frame_count = 0u64;

    while let Ok(frame) = moshi_broadcast_rx.recv().await {
        frame_count += 1;
        info!(
            "AUDIO_BRIDGE: [Frame #{}] Received from broadcast - samples={}, forwarding to MOSHI channel",
            frame_count,
            frame.samples.len()
        );

        if let Err(e) = moshi_tx.send(frame) {
            error!("AUDIO_BRIDGE: [Frame #{}] Failed to forward to MOSHI channel: {}", frame_count, e);
            break;
        }

        info!("AUDIO_BRIDGE: [Frame #{}] Successfully forwarded to MOSHI channel", frame_count);
    }

    error!("AUDIO_BRIDGE: Forwarding task stopped after {} frames", frame_count);
});
```

**Expected Output:**
```
AUDIO_BRIDGE: Forwarding task started - listening for broadcast frames
AUDIO_BRIDGE: [Frame #1] Received from broadcast - samples=1024, forwarding to MOSHI channel
AUDIO_BRIDGE: [Frame #1] Successfully forwarded to MOSHI channel
AUDIO_BRIDGE: [Frame #2] Received from broadcast - samples=1024, forwarding to MOSHI channel
...
```

### Location 3: Manual Start Forwarding Task (dashboard.rs:2353-2374)
Same logging added to the manual start path (when user presses a key to start conversation).

### Location 4: MOSHI Conversation Loop (voice.rs:577-692)
Already has 8 "AUDIO_PIPELINE:" debug logs that trace frame processing through MOSHI.

**Expected Output:**
```
AUDIO_PIPELINE: Conversation loop initialized, waiting for microphone frames
AUDIO_PIPELINE: [Frame #1] Received from microphone - samples=1024
AUDIO_PIPELINE: [Frame #1] Audio data - non_zero_samples=512/1024, rms=0.025
AUDIO_PIPELINE: [Frame #1] Added to buffer - buffer_size=1024, MOSHI_FRAME_SIZE=1920, ready=false
AUDIO_PIPELINE: [Frame #2] Received from microphone - samples=1024
...
AUDIO_PIPELINE: [Frame #2] MOSHI frame ready - extracted 1920 samples, 128 remaining in buffer
AUDIO_PIPELINE: [Frame #2] CALLING process_with_lm() - frame_size=1920, frame_rms=0.032
MOSHI_DEBUG: ========== process_with_lm() called - audio_len=1920 ==========
...
```

## Complete Audio Flow with Debug Points

```
Microphone (CPAL)
    ↓
LocalAudioSystem.start()
    ↓ (blocking_recv)
[DEBUG POINT 1] AUDIO_BROADCAST: Received from microphone
    ↓
audio_broadcast_tx.send() → broadcast channel (clone for each subscriber)
    ↓
[DEBUG POINT 2] AUDIO_BRIDGE: Received from broadcast
    ↓
moshi_tx.send() → unbounded channel
    ↓
moshi_rx (in start_local_conversation)
    ↓
[DEBUG POINT 3] AUDIO_PIPELINE: Received from microphone
    ↓
Buffer frames (1920 samples = 80ms at 24kHz)
    ↓
[DEBUG POINT 4] AUDIO_PIPELINE: CALLING process_with_lm()
    ↓
MOSHI processing (29 MOSHI_DEBUG logs)
    ↓
[DEBUG POINT 5] AUDIO_PIPELINE: Response sent to speakers
    ↓
playback_tx.send() → speaker output
```

## Diagnostic Questions

When running the system with these debug logs, we can answer:

1. **Is the microphone capturing audio?**
   - Look for: `AUDIO_BROADCAST: [Frame #N] Received from microphone`

2. **Is the broadcast system working?**
   - Look for: `AUDIO_BROADCAST: [Frame #N] Successfully broadcast to X subscribers`
   - Check subscriber count (should be 2: visualizer + MOSHI)

3. **Is the forwarding task receiving frames?**
   - Look for: `AUDIO_BRIDGE: [Frame #N] Received from broadcast`

4. **Is the forwarding task sending to MOSHI?**
   - Look for: `AUDIO_BRIDGE: [Frame #N] Successfully forwarded to MOSHI channel`

5. **Is start_local_conversation receiving frames?**
   - Look for: `AUDIO_PIPELINE: [Frame #N] Received from microphone`

6. **Is MOSHI processing being called?**
   - Look for: `AUDIO_PIPELINE: [Frame #N] CALLING process_with_lm()`
   - Look for: `MOSHI_DEBUG: process_with_lm() called`

## Next Steps

1. **Run the system**: `cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core && cargo run --dev`

2. **Monitor logs**: Look for the debug output patterns above

3. **Identify the break point**: Find which debug point is NOT appearing in logs

4. **Fix the issue**: Based on where the pipeline breaks, implement the appropriate fix

## Implementation Summary

**Files Modified:**
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/dashboard.rs`
  - Added AUDIO_BROADCAST logging (lines 764-799)
  - Added AUDIO_BRIDGE logging (lines 1030-1051)
  - Added AUDIO_BRIDGE logging for manual start (lines 2353-2374)

**Total Debug Logs Added:**
- 8 logs in audio broadcast system
- 6 logs in primary forwarding task
- 6 logs in manual start forwarding task
- **Total: 20 new debug logs** (in addition to 37 existing MOSHI/AUDIO_PIPELINE logs)

**Compilation Status:**
✅ Compiled successfully with warnings (no errors)

**Ready for Testing:**
The system is now fully instrumented to trace the complete audio pipeline from microphone input through to MOSHI processing.
