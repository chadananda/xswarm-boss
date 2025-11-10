# Dashboard Timeout and Microphone Permission Fixes

## Issues Fixed

### 1. Dashboard Timeout Issue

**Problem**: The dashboard was timing out after 10 seconds instead of running properly.

**Root Cause**:
- In `main.rs`, the code was wrapping `dashboard.run()` with a 10-second timeout
- `dashboard.run()` is designed to run **indefinitely** until the user quits (with 'Q' or Ctrl+C)
- The timeout was treating the dashboard like a quick startup task instead of a long-running UI

**Files Changed**:
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/main.rs`

**Changes Made**:
1. **Line 600-614**: Removed timeout from dev mode dashboard
   - Changed from `tokio::time::timeout(Duration::from_secs(10), dashboard.run()).await`
   - To: `dashboard.run().await`

2. **Line 725-740**: Removed timeout from normal start mode dashboard
   - Changed from `tokio::time::timeout(Duration::from_secs(10), dashboard.run()).await`
   - To: `dashboard.run().await`

3. **Line 924-936**: Removed timeout from error fallback dashboard
   - Changed from `tokio::time::timeout(Duration::from_secs(5), dashboard.run()).await`
   - To: `let _ = dashboard.run().await`

4. **Line 949-960**: Removed timeout from generic error dashboard
   - Changed from `tokio::time::timeout(Duration::from_secs(5), dashboard.run()).await`
   - To: `let _ = dashboard.run().await`

**Result**: Dashboard now runs indefinitely as designed, until user explicitly quits.

---

### 2. Microphone Permission Dialog Issue

**Problem**: The microphone permission dialog was not appearing on macOS.

**Root Cause**:
- The old `request_microphone_permission()` function only printed instructions
- It never actually attempted to access the audio device
- macOS only shows the permission dialog when an app first tries to access the microphone
- Simply calling CPAL functions without actually accessing a device won't trigger the dialog

**Files Changed**:
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/permissions.rs`

**Changes Made**:
1. **Lines 35-106**: Rewrote `request_microphone_permission()` function
   - Now spawns a thread that attempts to access the default input device using CPAL
   - This triggers the macOS permission dialog on first run
   - Waits up to 3 seconds for the permission check to complete
   - Provides clear user guidance based on the result:
     - Success: Permission granted
     - Failure: Shows manual permission instructions
     - Timeout: Alerts user that dialog may be waiting

**Technical Implementation**:
```rust
// Spawns thread to access microphone (triggers permission dialog)
std::thread::spawn(move || {
    use cpal::traits::{DeviceTrait, HostTrait};
    let host = cpal::default_host();
    let device = host.default_input_device()?;
    let _name = device.name()?; // This line triggers the permission check
    Ok(())
});
```

**Result**:
- macOS permission dialog now appears when app first tries to access microphone
- Clear user feedback about permission status
- Helpful instructions if permission needs to be granted manually

---

## Testing

### Dev Mode
```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core
cargo run -- --dev
```

**Expected behavior**:
1. Login prompt appears
2. Microphone permission dialog appears (first run on macOS)
3. Dashboard launches and runs indefinitely
4. No timeout errors
5. Press 'Q' or Ctrl+C to quit

### Normal Mode
```bash
cargo run
```

**Expected behavior**:
1. Microphone permission dialog appears (first run on macOS)
2. Dashboard launches and connects to services
3. Runs indefinitely until user quits
4. No timeout errors

---

## Dev Mode Behavior

When running with `--dev` flag:
- External services are **BYPASSED** (supervisor, health checks)
- Authentication uses local `.env` file credentials
- Dashboard shows "DEV MODE (OFFLINE)" in header
- Yellow styling indicates development mode
- System status shows services as "BYPASSED"

This allows testing the UI without requiring the full backend stack.

---

## Build Status

All changes compile successfully:
```bash
cargo build
# Result: Finished `dev` profile [unoptimized + debuginfo] target(s) in 11.25s
```

Only warnings (no errors), all related to unused imports and variables in other modules.

---

## Summary

**Dashboard Timeout Fix**:
- Removed all timeouts from `dashboard.run()` calls
- Dashboard now runs until user quits (Q/Ctrl+C)
- Fixed in 4 locations in main.rs

**Microphone Permission Fix**:
- Rewrote permission request to actually access audio device
- This triggers macOS permission dialog
- Provides clear user feedback and instructions
- Implemented proper timeout and error handling

Both issues are now resolved and ready for testing.
