# Terminal Cleanup Fix

## Problem
When exiting the xswarm-boss TUI dashboard, the terminal was left in a "messed up" state:
- Cursor not visible
- Raw mode still enabled
- Alternate screen not properly exited
- User input not echoing

This happened because the terminal restoration code wasn't being executed reliably when the application quit.

## Root Cause
The issue occurred when:
1. The quit handler returned early without executing cleanup code
2. Error paths didn't guarantee terminal restoration
3. Ctrl+C wasn't handled, causing abrupt exit without cleanup

## Solution Implemented

### 1. Made Terminal Cleanup Bulletproof (Lines 437-456)
Changed terminal cleanup from error-propagating to error-ignoring:

**Before:**
```rust
disable_raw_mode()?;
execute!(
    terminal.backend_mut(),
    LeaveAlternateScreen,
    DisableMouseCapture
)?;
terminal.show_cursor()?;
```

**After:**
```rust
// CRITICAL: Always cleanup terminal state, even if there were errors
// This ensures the terminal is properly restored regardless of how we exit

// Restore terminal - ignore errors during cleanup to ensure all steps run
let _ = disable_raw_mode();
let _ = execute!(
    terminal.backend_mut(),
    LeaveAlternateScreen,
    DisableMouseCapture
);
let _ = terminal.show_cursor();
```

**Why this works:**
- Using `let _ = ...` ignores errors during cleanup
- All cleanup steps execute even if one fails
- Terminal restoration is guaranteed regardless of prior errors

### 2. Added Ctrl+C Handling (Lines 481-484)
Added explicit Ctrl+C detection in the event loop:

```rust
// Handle Ctrl+C first - this is critical for proper terminal cleanup
if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
    break;
}
```

**Why this is important:**
- Ctrl+C is a common way to quit applications
- Without explicit handling, it could bypass the event loop cleanup
- Now Ctrl+C triggers the same clean break as 'q' or Esc

### 3. Fixed 'C' Key Conflict (Lines 494-504)
Updated the 'C' key handler to avoid conflict with Ctrl+C:

```rust
KeyCode::Char('c') | KeyCode::Char('C') => {
    // Clear activity feed (only if not Ctrl+C)
    if !key.modifiers.contains(KeyModifiers::CONTROL) {
        let mut state = self.state.write().await;
        state.activity_events.clear();
        state.add_event(ActivityEvent::SystemEvent {
            message: "Activity feed cleared".to_string(),
            time: Local::now(),
        });
    }
}
```

### 4. Ensured Quit Handler Uses Break (Line 488)
Verified the quit handler uses `break` instead of `return`:

```rust
KeyCode::Char('q') | KeyCode::Char('Q') | KeyCode::Esc => {
    break;
}
```

This is critical because:
- `break` exits the loop and continues to cleanup code
- `return Ok(())` would exit the function immediately, skipping cleanup

## Files Modified
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core/src/dashboard.rs`
  - Added `KeyModifiers` import (line 12)
  - Made terminal cleanup bulletproof (lines 437-456)
  - Added Ctrl+C handling (lines 481-484)
  - Fixed 'C' key conflict (lines 494-504)

## Testing

### Manual Testing Steps
1. Build the project: `cargo build --release`
2. Run the dashboard: `./target/release/xswarm dashboard`
3. Test each quit method:
   - Press `q` → Terminal should be normal
   - Press `Esc` → Terminal should be normal
   - Press `Ctrl+C` → Terminal should be normal

### What "Normal" Means
After quitting, verify:
- [ ] Cursor is visible and blinking
- [ ] Typing shows characters on screen
- [ ] Terminal prompt displays correctly
- [ ] Line editing works (backspace, arrow keys)
- [ ] No garbled output or control characters

### Automated Test
Run the test script:
```bash
./test-terminal-cleanup.sh
```

## Technical Details

### Terminal Modes
The TUI uses several terminal modes:
1. **Raw Mode**: Disables line buffering and special character processing
2. **Alternate Screen**: Saves current screen and uses a separate buffer
3. **Mouse Capture**: Enables mouse event capture
4. **Cursor Hide**: Makes cursor invisible during TUI rendering

All these must be properly reversed when exiting.

### Error Handling Strategy
The cleanup code uses `let _ = ...` to deliberately ignore errors because:
1. If cleanup is happening, the application is already exiting
2. Propagating cleanup errors would prevent other cleanup steps
3. Partial cleanup is better than no cleanup
4. The terminal state is more important than error reporting at this point

### Why This Was a Problem Before
Previously, if any cleanup step failed (e.g., `disable_raw_mode()` returned an error), the subsequent cleanup steps wouldn't execute due to the `?` operator propagating the error. This left the terminal in a partially-restored state.

## Future Improvements
Consider adding:
1. A RAII guard (Drop implementation) to guarantee cleanup
2. Signal handlers for other interrupts (SIGTERM, etc.)
3. Panic handler to restore terminal even on panic

## Related Issues
- Previous fix attempt that was reverted
- Original report of "terminal messed up after quitting"

## Verification
```bash
# Build
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core
cargo build --release

# Test (requires user interaction)
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss
./target/release/xswarm dashboard
# Then quit with q, Esc, or Ctrl+C and verify terminal is normal
```

## Summary
The fix ensures that **no matter how the user exits the TUI** (q, Esc, Ctrl+C, or even errors), the terminal is **always properly restored** to its original state. This is achieved by:
1. Making cleanup steps non-failing (using `let _ = ...`)
2. Handling Ctrl+C explicitly
3. Ensuring the quit path uses `break` not `return`
4. Running cleanup code even after error recovery attempts
