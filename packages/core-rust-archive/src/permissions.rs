// macOS Permissions Module
//
// This module handles requesting and checking system permissions on macOS,
// specifically for microphone access needed by audio components.

use anyhow::Result;
use tracing::{info, warn};

#[cfg(target_os = "macos")]
use std::process::Command;

/// Check if microphone permission is granted on macOS
#[cfg(target_os = "macos")]
pub fn check_microphone_permission() -> bool {
    // Use AppleScript to check microphone permission status
    let script = r#"
        tell application "System Events"
            return (do shell script "sqlite3 '/Library/Application Support/com.apple.TCC/TCC.db' \"SELECT service FROM access WHERE service='kTCCServiceMicrophone' AND client='com.apple.Terminal' AND auth_value=1\" 2>/dev/null || echo ''")
        end tell
    "#;

    match Command::new("osascript")
        .arg("-e")
        .arg(script)
        .output()
    {
        Ok(output) => {
            let result = String::from_utf8_lossy(&output.stdout);
            !result.trim().is_empty()
        }
        Err(_) => false,
    }
}

/// Request microphone permission on macOS by attempting to access the device
///
/// This triggers the system permission dialog by actually trying to create an audio stream.
/// The permission dialog only appears the first time an app tries to access the microphone.
///
/// This function is designed to work silently in TUI environments - all output goes to logs only.
#[cfg(target_os = "macos")]
pub fn request_microphone_permission() -> Result<()> {
    info!("Starting microphone permission request on macOS");

    // Try to access the microphone to trigger the permission dialog
    // This will fail if permission is denied, which is expected
    use std::sync::mpsc;
    use std::time::Duration;

    // Log permission request (no console output to avoid disrupting TUI)
    info!("Requesting microphone access - system permission dialog may appear");

    // Spawn a thread to attempt audio access (this triggers the permission dialog)
    let (tx, rx) = mpsc::channel();
    std::thread::spawn(move || {
        // Try to create a CPAL host and access default input device
        // This will trigger the macOS permission dialog on first run
        #[cfg(target_os = "macos")]
        {
            use cpal::traits::{DeviceTrait, HostTrait};
            let result = (|| -> Result<()> {
                info!("Creating CPAL host");
                let host = cpal::default_host();
                info!("Getting default input device");
                let device = host.default_input_device()
                    .ok_or_else(|| anyhow::anyhow!("No input device found"))?;

                info!("Getting device name to trigger permission");
                // Get device name to ensure we have permission - this should trigger the dialog
                let name = device.name()?;
                info!("Device name: {}", name);

                // Try to get supported configurations to really trigger permission
                info!("Getting supported configurations");
                let mut configs = device.supported_input_configs()?;
                if let Some(config) = configs.next() {
                    info!("Found config: {:?}", config);
                }

                info!("Microphone access granted successfully");
                Ok(())
            })();
            let _ = tx.send(result);
        }
    });

    // Wait for the permission check with a short timeout for fast startup
    match rx.recv_timeout(Duration::from_secs(2)) {
        Ok(Ok(())) => {
            info!("Microphone permission granted successfully");
            Ok(())
        }
        Ok(Err(e)) => {
            warn!("Microphone access check failed: {}", e);
            warn!("User may need to grant microphone permission in System Settings → Privacy & Security → Microphone");
            Err(e)
        }
        Err(_) => {
            warn!("Microphone permission check timed out");
            info!("Permission dialog may have appeared - user can try voice feature again after granting permission");
            Ok(())
        }
    }
}

/// Guide user to manually grant microphone permission
///
/// Logs instructions for granting microphone permission - designed for TUI environments.
#[cfg(target_os = "macos")]
pub fn show_permission_guide() {
    warn!("Microphone permission denied");
    info!("To enable microphone access:");
    info!("  1. Open System Preferences (or System Settings on macOS 13+)");
    info!("  2. Go to Security & Privacy → Privacy → Microphone");
    info!("  3. Find and enable your terminal application (Terminal.app, iTerm2, VSCode, etc.)");
    info!("  4. Restart this application");
    info!("Alternatively, run with --skip-audio-check to bypass this check.");
}

/// Check and request microphone permission if needed
#[cfg(target_os = "macos")]
pub fn ensure_microphone_permission(skip_check: bool) -> Result<bool> {
    if skip_check {
        warn!("Skipping microphone permission check (--skip-audio-check flag)");
        return Ok(true);
    }

    info!("Checking microphone permission on macOS");

    // Show guidance that permission will be requested
    request_microphone_permission()?;

    // Return true to allow the app to continue
    // The actual permission dialog will appear when CPAL tries to access devices
    Ok(true)
}

// Non-macOS platforms don't need permission checks
#[cfg(not(target_os = "macos"))]
pub fn check_microphone_permission() -> bool {
    true
}

#[cfg(not(target_os = "macos"))]
pub fn request_microphone_permission() -> Result<()> {
    Ok(())
}

#[cfg(not(target_os = "macos"))]
pub fn show_permission_guide() {
    // No-op on non-macOS platforms
}

#[cfg(not(target_os = "macos"))]
pub fn ensure_microphone_permission(_skip_check: bool) -> Result<bool> {
    Ok(true)
}

/// Handle CPAL device error gracefully
pub fn handle_device_error(error: &anyhow::Error) -> Result<()> {
    let error_msg = error.to_string();

    // Check for macOS permission error (os error 6 = Device not configured)
    if error_msg.contains("os error 6") || error_msg.contains("Device not configured") {
        #[cfg(target_os = "macos")]
        {
            show_permission_guide();
            anyhow::bail!(
                "Microphone permission denied. Please grant permission in System Preferences and restart."
            );
        }

        #[cfg(not(target_os = "macos"))]
        anyhow::bail!("Audio device error: {}", error);
    }

    // For other errors, just propagate them
    anyhow::bail!("Audio device error: {}", error)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_permission_check_compiles() {
        // Just ensure the functions compile on all platforms
        let _ = check_microphone_permission();
    }
}
