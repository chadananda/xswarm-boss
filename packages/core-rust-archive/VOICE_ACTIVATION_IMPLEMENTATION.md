# Voice System Activation Implementation

## Overview
Added functionality to start the voice/audio system from within the dev mode dashboard on demand, allowing users to activate voice services when needed instead of automatically starting them.

## Changes Made

### 1. Dashboard State Updates
**File**: `/packages/core/src/dashboard.rs`

- Added `voice_system_starting: bool` field to `DashboardState` to track activation state
- Added `voice_bridge_handle` and `supervisor_handle` to `Dashboard` struct to manage voice service tasks
- Both handles are `Arc<RwLock<Option<JoinHandle>>>` for thread-safe async task management

### 2. Voice System Startup Method
**Method**: `Dashboard::start_voice_system()`

**Flow**:
1. Check if voice system is already running (avoid duplicate instances)
2. Mark system as starting in state
3. Check microphone permissions on macOS (using existing `permissions::ensure_microphone_permission`)
4. Create voice bridge configuration
5. Initialize and start `VoiceBridge`
6. Spawn voice bridge server task (async)
7. Initialize and start `SupervisorServer` with MOSHI state
8. Spawn supervisor server task (async)
9. Update dashboard state with online status
10. Add system event to activity feed

**Error Handling**:
- Microphone permission errors → Show initialization error panel
- Voice bridge initialization errors → Log to activity feed and show error
- All errors are gracefully handled and displayed in the TUI

### 3. Hotkey Handler
**Key**: `V` (case insensitive)

Added keyboard handler in `run_ui_loop()`:
```rust
KeyCode::Char('v') | KeyCode::Char('V') => {
    // Start voice system
    if let Err(e) = self.start_voice_system().await {
        warn!("Failed to start voice system: {}", e);
        // Error already logged to activity feed in start_voice_system
    }
}
```

### 4. UI Updates

#### Footer Help Text
Added `[V]oice Start` option to footer, styled in green to indicate it's an action command:
```
[Q]uit | [R]efresh | [C]lear Activity | [V]oice Start | [S]ave to Clipboard
```

#### Status Panel
Updated voice bridge status rendering to show three states:
- "Starting..." (Yellow) - When voice system is initializing
- "Online" (Green) - When voice system is running
- "Offline" (Gray) - When voice system is not running

### 5. Cleanup Handling
Added proper cleanup in `Dashboard::run()`:
- Voice bridge handle is aborted on dashboard exit
- Supervisor handle is aborted on dashboard exit
- Handles are properly taken and dropped to prevent resource leaks

## Usage

### In Dev Mode
1. Start dashboard with: `cargo run --bin xswarm -- --dev`
2. Login with dev credentials
3. Press `V` to start the voice system
4. Activity feed will show:
   - "Starting voice system..."
   - "Voice system started - Bridge: ws://127.0.0.1:9998, Supervisor: ws://127.0.0.1:9999"
5. Status panel will update to show "Online" for both services

### In Normal Mode
Same behavior - press `V` to activate voice services on demand.

## Benefits

1. **On-Demand Activation**: Voice services only start when needed
2. **Dev Mode Friendly**: Can run dashboard without voice in dev mode, activate when testing voice features
3. **Clear Feedback**: Status updates in activity feed and status panel
4. **Error Recovery**: Microphone permission errors shown with recovery instructions
5. **Resource Efficient**: Voice services not running until explicitly activated

## Integration Points

### Dependencies
- `crate::voice::VoiceBridge` - Voice bridge service
- `crate::supervisor::SupervisorServer` - Supervisor WebSocket server
- `crate::permissions::ensure_microphone_permission` - macOS permission check

### State Synchronization
- Voice bridge online status updates `state.voice_bridge_online`
- Supervisor connection status updates `state.supervisor_connected`
- Activity events logged for all state changes

## Testing Checklist

- [ ] Dashboard starts without voice system in dev mode
- [ ] Pressing `V` triggers voice system startup
- [ ] Activity feed shows startup progress
- [ ] Status panel updates to "Starting..." then "Online"
- [ ] Microphone permission errors are handled gracefully
- [ ] Voice system doesn't duplicate if already running
- [ ] Dashboard cleanup properly aborts voice tasks
- [ ] Works in both dev mode and normal mode
- [ ] Footer shows `[V]oice Start` option

## Future Enhancements

1. Add `[V]oice Stop` option to shut down voice system
2. Add voice system health monitoring
3. Show voice connection count in status panel
4. Add voice system restart capability
5. Voice system auto-recovery on errors
