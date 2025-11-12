# Audio Pipeline Routing Fix

## Issue Summary
The microphone-to-MOSHI audio pipeline was broken - microphone input was being captured and visualized, but audio frames were never reaching the MOSHI processing pipeline for voice generation.

## Root Cause
The audio bridge forwarding task (responsible for routing broadcast audio frames to MOSHI) had a critical flaw:

1. **No error handling for lag**: The task used `while let Ok(frame) = receiver.recv().await`, which would exit immediately on ANY error, including `RecvError::Lagged`
2. **Missing debug logs**: No logs at task spawn time to verify the task actually started
3. **Broadcast lag vulnerability**: With a 1000-frame buffer and slow model initialization, the broadcast channel could lag before MOSHI subscribed, causing immediate task exit

## The Fix

### File: `packages/core/src/dashboard.rs`

**Lines 1047-1103** (auto-start path):
- Added immediate debug logs when task spawns
- Changed from `while let Ok()` to `loop` with proper `match` on recv result
- Added explicit handling for `RecvError::Lagged` - continues instead of exiting
- Added explicit handling for `RecvError::Closed` - clean exit
- Added lag counter to track how many times the channel lagged
- Added comprehensive logging at each step

**Lines 2378-2434** (manual start path):
- Same fixes applied to the manual start code path

### Key Changes

#### Before (Broken):
```rust
tokio::spawn(async move {
    info!("AUDIO_BRIDGE: Forwarding task started");
    let mut frame_count = 0u64;

    while let Ok(frame) = moshi_broadcast_rx.recv().await {
        // Process frame...
    }

    error!("AUDIO_BRIDGE: Forwarding task stopped");
});
```

**Problem**: Exits immediately on `RecvError::Lagged`, no logs to confirm spawn.

#### After (Fixed):
```rust
let forwarding_handle = tokio::spawn(async move {
    info!("========================================");
    info!("AUDIO_BRIDGE: Forwarding task SPAWNED and STARTING");
    info!("========================================");

    let mut frame_count = 0u64;
    let mut lag_count = 0u64;

    loop {
        match moshi_broadcast_rx.recv().await {
            Ok(frame) => {
                // Process frame with logging
            }
            Err(RecvError::Lagged(skipped)) => {
                lag_count += 1;
                warn!("Broadcast lagged, skipped {} frames - continuing", skipped);
                // Continue receiving - don't exit!
            }
            Err(RecvError::Closed) => {
                error!("Broadcast channel closed - exiting");
                break;
            }
        }
    }

    error!("Forwarding task stopped - frames={}, lags={}", frame_count, lag_count);
});
```

**Benefits**:
- Immediate confirmation that task spawned
- Continues processing even when broadcast lags
- Tracks lag events for monitoring
- Only exits on channel close or send failure
- Comprehensive logging for debugging

## Expected Behavior After Fix

When the system runs, you should now see:

```
MOSHI SETUP: Subscribing to audio broadcast...
MOSHI SETUP: Successfully subscribed to audio broadcast
MOSHI SETUP: Created unbounded channel for MOSHI conversation
========================================
AUDIO_BRIDGE: Forwarding task SPAWNED and STARTING
AUDIO_BRIDGE: This task forwards broadcast frames to MOSHI
========================================
AUDIO_BRIDGE: [Frame #1] Received from broadcast - samples=480, forwarding to MOSHI channel
AUDIO_BRIDGE: [Frame #1] Successfully forwarded to MOSHI channel
AUDIO_PIPELINE: [Frame #1] Received from microphone - samples=480
AUDIO_PIPELINE: [Frame #1] Added to buffer - buffer_size=480
...
AUDIO_PIPELINE: [Frame #4] MOSHI frame ready - extracted 1920 samples
AUDIO_PIPELINE: [Frame #4] CALLING process_with_lm() - frame_size=1920
MOSHI_DEBUG: ========== process_with_lm() called - audio_len=1920 ==========
MOSHI_DEBUG: Step 1 - Encoding 1920 audio samples to MIMI codes
...
```

## Testing Instructions

1. Build the fixed code:
   ```bash
   cd packages/core
   cargo build --release
   ```

2. Run the system:
   ```bash
   ./target/release/xswarm
   ```

3. Watch for the new debug logs:
   - "AUDIO_BRIDGE: Forwarding task SPAWNED and STARTING"
   - "AUDIO_BRIDGE: [Frame #N] Received from broadcast"
   - "AUDIO_PIPELINE: [Frame #N] Received from microphone"
   - "MOSHI_DEBUG: process_with_lm() called"

4. If you see lag warnings:
   ```
   AUDIO_BRIDGE: [Lag #1] Broadcast lagged, skipped 50 frames - continuing
   ```
   This is NORMAL and the system will continue processing.

## Files Modified

- `/packages/core/src/dashboard.rs`:
  - Lines 1047-1103: Auto-start audio bridge (fixed)
  - Lines 2378-2434: Manual-start audio bridge (fixed)

## Build Status

✅ Code compiles successfully
✅ All tests pass
✅ Release build completed

## Impact

This fix ensures that:
1. Audio frames from the microphone reliably reach the MOSHI processing pipeline
2. The system gracefully handles broadcast channel lag instead of crashing
3. Comprehensive logging allows debugging of any future audio routing issues
4. The forwarding task won't exit prematurely due to temporary lags

This was the final blocking issue preventing MOSHI from generating voice responses.
