# macOS Microphone Permission Fix

## Problem

The xSwarm voice bridge command was failing with "Device not configured (os error 6)" on macOS because CPAL (the audio library) was trying to access audio devices without proper system permissions.

## Solution Implemented

### 1. Created Permissions Module (`src/permissions.rs`)

A new module that handles macOS microphone permissions with the following features:

- **Automatic Permission Guidance**: Shows user-friendly instructions when microphone access is needed
- **Platform-Specific**: Uses conditional compilation to only run on macOS
- **Error Handling**: Provides clear guidance if permission is denied
- **Graceful Fallback**: Handles "os error 6" gracefully with helpful messages

### 2. Integration with Voice Bridge

The `voice-bridge` command now:

1. Checks if running on macOS
2. Shows permission guidance to the user
3. Allows the system to trigger the permission dialog when CPAL accesses devices
4. Provides clear instructions if permission is denied

### 3. Key Functions

```rust
// Show permission guidance (macOS only)
permissions::ensure_microphone_permission(skip_check: bool) -> Result<bool>

// Handle CPAL device errors gracefully
permissions::handle_device_error(error: &anyhow::Error) -> Result<()>

// Show manual permission instructions
permissions::show_permission_guide()
```

## Usage

### Running the Voice Bridge

```bash
cargo run --bin xswarm voice-bridge
```

When you run this command on macOS for the first time, you'll see:

```
🎤 Microphone Access Required
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This application needs access to your microphone for voice features.

If you see a permission dialog, please:
  1. Click "OK" or "Allow" to grant microphone access
  2. The application will continue automatically

If you don't see a dialog, you may need to manually grant permission:
  1. Open System Preferences → Security & Privacy → Privacy
  2. Select "Microphone" from the list
  3. Check the box next to your terminal app or xswarm
  4. Restart this application
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Manual Permission Grant

If the automatic dialog doesn't appear:

1. Open **System Preferences** (or **System Settings** on macOS 13+)
2. Go to **Security & Privacy** → **Privacy** → **Microphone**
3. Enable your terminal application:
   - Terminal.app
   - iTerm2
   - VSCode
   - Or whichever app you're running xswarm from
4. Restart the application

## Technical Details

### How macOS Permissions Work

macOS requires explicit user permission for apps to access:
- Microphone
- Camera
- Screen Recording
- Accessibility features
- etc.

When an app first tries to access a protected resource, macOS shows a system dialog. The user must approve or deny access.

### CPAL Behavior

CPAL (Cross-Platform Audio Library) attempts to enumerate and access audio devices. On macOS, this triggers the permission check. If permission hasn't been granted, the OS returns error code 6 ("Device not configured").

### Our Solution

Instead of letting CPAL fail silently or crash:

1. We show guidance BEFORE accessing devices
2. We catch the error if it occurs
3. We provide clear instructions for manual permission grant
4. We make the error message user-friendly

## Dashboard Command

The dashboard command does NOT access audio devices and should run without microphone permissions. If you encounter audio-related errors with the dashboard, this is likely a different issue.

## Testing

### Test Voice Bridge

```bash
# Should show permission guidance on first run
cargo run --bin xswarm voice-bridge

# Expected output includes permission instructions
# Then the app starts normally if permission is granted
```

### Test Dashboard

```bash
# Should run without requiring microphone access
cargo run --bin xswarm dashboard

# Uses keyboard input (q to quit, r to refresh, c to clear)
```

## Platform Support

- **macOS**: Full permission handling with user guidance
- **Linux**: No permission checks needed (handled by system)
- **Windows**: No permission checks needed (handled by system)

## Future Improvements

Potential enhancements:

1. Programmatically check if permission is already granted (currently shows guidance on every run)
2. Add `--skip-audio-check` flag to bypass permission check during development
3. Use Objective-C runtime to directly query TCC (Transparency, Consent, and Control) database
4. Create a `.app` bundle with proper Info.plist for better permission dialogs

## Related Files

- `/packages/core/src/permissions.rs` - Permission handling module
- `/packages/core/src/main.rs` - Integration with voice-bridge command
- `/packages/core/src/lib.rs` - Module export
- `/Cargo.toml` - No new dependencies needed (uses std only)

## References

- [Apple TCC Documentation](https://developer.apple.com/documentation/avfoundation/cameras_and_media_capture/requesting_authorization_for_media_capture_on_macos)
- [CPAL GitHub](https://github.com/RustAudio/cpal)
- [macOS Security Guide](https://support.apple.com/guide/security/welcome/web)
