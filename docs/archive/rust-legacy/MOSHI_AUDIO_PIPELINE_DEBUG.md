# MOSHI Audio Pipeline Debug Investigation

**Date Created:** November 3, 2025
**Status:** IN PROGRESS - Audio pipeline timing issue partially fixed, but MOSHI processing functions still not being called
**Priority:** HIGH - Voice conversation system non-functional despite showing "ready" status

## Executive Summary

The MOSHI voice conversation system shows "✅ MOSHI voice system ready!" in the TUI dashboard but produces no actual audio output. Investigation revealed and partially fixed a timing race condition in the audio pipeline, but deeper issues remain with MOSHI processing functions not being called.

## Current Problem Statement

**Symptoms:**
- TUI shows "✅ MOSHI voice system ready!" and "✓ Local voice conversation ready - speak"
- Microphone input is working (shows minimal activity: `Mic: ▎`)
- No audio output from MOSHI
- No debug logs from MOSHI processing functions
- System appears functional but produces no voice responses

**Expected Behavior:**
- User speaks into microphone
- MOSHI processes audio frames and generates response
- Audio output plays through speakers
- Debug logs show processing activity

## Technical Architecture

### Key Components

1. **Audio Pipeline Flow:**
   ```
   Microphone → Audio Broadcast Channel → MOSHI Processing → Speaker Output
   ```

2. **Critical Files:**
   - `packages/core/src/dashboard.rs` - Audio bridge and TUI
   - `packages/core/src/voice.rs` - MOSHI processing functions
   - `packages/core/src/main.rs` - Logging configuration

3. **MOSHI Processing Chain:**
   - `start_local_conversation()` - Main conversation loop
   - `process_with_lm()` - Core MOSHI processing
   - Audio frame reception and processing
   - Language model inference
   - Audio generation and output

## Investigation Timeline

### Phase 1: Initial Analysis (Previous sessions)
- MOSHI compilation issues resolved
- Memory system integration completed
- Basic audio pipeline established
- TUI showing ready status

### Phase 2: Timing Race Condition Fix (Current session)
**Problem Identified:** Late subscription to broadcast channel
- **Location:** `dashboard.rs:1055`
- **Issue:** MOSHI subscribed to audio broadcast AFTER frames were already being sent
- **Fix Applied:** Early subscription pattern (lines 824-828)

**Changes Made:**
```rust
// dashboard.rs:824-828 - Early subscription
info!("MOSHI SETUP: Pre-subscribing to audio broadcast BEFORE async initialization...");
let moshi_broadcast_rx = audio_broadcast_tx.subscribe();
info!("MOSHI SETUP: Pre-subscribed successfully - will receive all microphone frames");

// dashboard.rs:852 - Move receiver into async closure
let moshi_broadcast_rx = moshi_broadcast_rx;

// dashboard.rs:1055-1056 - Removed duplicate late subscription
// OLD: let mut moshi_broadcast_rx = audio_broadcast.subscribe(); // Too late!
// NEW: Uses the pre-created receiver
```

### Phase 3: Compilation Fixes
**Import Error Fixed:**
- **File:** `voice.rs:29`
- **Error:** `unresolved import 'crate::memory'`
- **Fix:** Changed to `use crate::ConversationMemory;`

**Logging Enabled:**
- **File:** `main.rs:745`
- **Change:** `LevelFilter::OFF` → `LevelFilter::INFO`

### Phase 4: Build and Test Results
- ✅ Clean compilation with no errors
- ✅ Release build completed successfully
- ✅ TUI shows ready status
- ❌ **No debug logs from MOSHI processing functions**
- ❌ **No actual audio processing occurring**

## Current Status

### What's Working ✅
1. **Authentication:** System logs in successfully
2. **TUI Dashboard:** Displays correctly with ready status
3. **Microphone:** Input detected and working
4. **Audio Visualizer:** Connected and showing activity
5. **MOSHI Models:** Loaded successfully
6. **Voice Bridge:** Online and connected
7. **Supervisor:** Online and connected
8. **Compilation:** Clean build with no errors

### What's Not Working ❌
1. **MOSHI Processing:** No evidence of `start_local_conversation()` being called
2. **Audio Output:** No voice responses generated
3. **Debug Logging:** Missing logs from processing functions
4. **Frame Processing:** No evidence frames reach MOSHI processing

### Key Evidence

**From `/tmp/xswarm_audio_test.log`:**
```
✅ Login successful!
🚀 DEV MODE - OFFLINE
✅ MOSHI voice system ready!
✓ Local voice conversation ready - speak
🔊 Playing greeting tones...
✓ Supervisor online
🎤 Starting local voice conversation..
✓ Voice bridge online
✓ Audio visualizer connected
✓ MOSHI models loaded
✓ Microphone permission granted
```

**Missing Debug Logs:**
- No "AUDIO_PIPELINE: [Frame #X] Received from microphone"
- No logs from `start_local_conversation()` function
- No logs from `process_with_lm()` function
- No MOSHI processing activity

## Failed Debugging Attempts

### Attempt 1: Broadcast Channel Timing Fix
- **Approach:** Fixed late subscription to audio broadcast channel
- **Result:** ✅ Compilation fixed, ❌ Still no processing
- **Learning:** Timing was one issue but not the root cause

### Attempt 2: Logging Level Adjustment
- **Approach:** Changed from `LevelFilter::OFF` to `LevelFilter::INFO`
- **Result:** ✅ Enabled logging, ❌ Still no MOSHI logs
- **Learning:** Logging is working but MOSHI functions not called

### Attempt 3: Multiple Debug Runs
- **Approach:** Various test runs with different logging configurations
- **Result:** ❌ Consistent pattern of ready status but no processing
- **Learning:** Issue is systematic, not environmental

## Anticipated Root Cause Analysis

### Hypothesis 1: Async Task Not Starting
**Theory:** The async task that should run `start_local_conversation()` is not being spawned or is failing silently.

**Evidence Supporting:**
- TUI shows "🎤 Starting local voice conversation.." but no subsequent logs
- No debug output from the conversation loop
- System shows ready but no processing occurs

**Investigation Needed:**
- Add debug logging around the async task spawn in `dashboard.rs`
- Verify the task is actually created and running
- Check for silent panics or errors in the async context

### Hypothesis 2: Channel Communication Failure
**Theory:** While the timing race condition was fixed, there may be another communication issue between components.

**Evidence Supporting:**
- Audio visualizer works (receives frames)
- MOSHI doesn't show frame reception
- Possible channel configuration mismatch

**Investigation Needed:**
- Add debug logging in the MOSHI receiver loop
- Verify channel capacity and configuration
- Test direct frame injection

### Hypothesis 3: MOSHI Initialization Problem
**Theory:** MOSHI models are loaded but not properly initialized for conversation mode.

**Evidence Supporting:**
- Models load successfully
- No error messages during initialization
- Ready status shown but no processing

**Investigation Needed:**
- Add detailed initialization logging
- Verify conversation mode setup
- Check model state and readiness

## Next Steps Action Plan

### Immediate Actions (Next Session)

1. **Add Detailed Debug Logging**
   - Add logs around async task creation in `dashboard.rs`
   - Add logs at the start of `start_local_conversation()`
   - Add logs in the frame reception loop
   - Add logs around MOSHI model interactions

2. **Verify Async Task Execution**
   - Confirm the conversation task is spawned
   - Check for task panics or silent failures
   - Verify task runtime and execution context

3. **Test Frame Flow Manually**
   - Add synthetic frame injection for testing
   - Bypass microphone input temporarily
   - Test MOSHI processing in isolation

### Medium-term Actions

1. **Channel Architecture Review**
   - Verify all channel configurations
   - Test channel capacity and buffering
   - Consider alternative communication patterns

2. **MOSHI Integration Testing**
   - Create minimal test for MOSHI processing
   - Verify model initialization sequence
   - Test conversation mode setup

3. **Error Handling Audit**
   - Review all error handling in the audio pipeline
   - Add explicit error logging where missing
   - Ensure no silent failures

## Code Locations Reference

### Key Functions to Debug
```rust
// dashboard.rs - Audio bridge setup
async fn start_voice_bridge() // Line ~850
async fn start_moshi_voice_system() // Line ~1020

// voice.rs - MOSHI processing
pub async fn start_local_conversation() // Line ~576
async fn process_with_lm() // Line ~886
```

### Critical Debug Points
```rust
// Expected logs that are missing:
"AUDIO_PIPELINE: [Frame #X] Received from microphone"
"Starting conversation loop"
"Processing audio frame with MOSHI"
"Generated audio response"
```

### Files Modified in This Session
1. `dashboard.rs:824-828, 852, 1055-1056` - Early subscription fix
2. `voice.rs:29` - Import fix
3. `main.rs:745` - Logging level fix

## Background Context

### Project Structure
- **xSwarm Boss:** Voice-enabled AI assistant system
- **MOSHI:** Kyutai's real-time voice conversation model
- **Architecture:** Rust core with TUI dashboard
- **Development Mode:** Offline mode for testing

### Technical Stack
- **Language:** Rust with Tokio async runtime
- **Audio:** 24kHz sampling, broadcast channels
- **UI:** TUI with real-time status display
- **Models:** MOSHI loaded via Candle framework
- **Logging:** Tracing framework with configurable levels

### Previous Work Completed
- MOSHI model integration
- Memory system implementation
- Audio pipeline architecture
- TUI dashboard development
- Basic conversation framework

## Environment Information

**Working Directory:** `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core`
**Platform:** macOS (Darwin 23.4.0)
**Rust Version:** Latest stable
**Build Target:** Release mode for performance
**Test Environment:** Development mode with offline services

## Success Criteria

The issue will be considered resolved when:

1. ✅ User speaks into microphone
2. ✅ Debug logs show frame reception in MOSHI processing
3. ✅ MOSHI generates audio response
4. ✅ Audio output plays through speakers
5. ✅ Full conversation loop is functional
6. ✅ Performance is acceptable for real-time conversation

## Notes for Next Session

- Focus on async task execution verification first
- The timing race condition fix was successful but insufficient
- System architecture is sound, likely a communication or initialization issue
- All background bash processes should be cleaned up before starting
- User expects thorough testing before declaring success
- This is a proof-of-concept system, debugging and fixes are expected