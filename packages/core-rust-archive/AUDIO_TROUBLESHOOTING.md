# Audio Output Troubleshooting Guide

## Quick Diagnosis

If you see "MOSHI voice system started - greeting played" but hear **NO audio**:

### Step 1: Run the Audio Test
```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/core
cargo run --example test_greeting
```

### Step 2: Check the Output

#### ✅ If you see AND hear three tones:
**Audio system is working!** The issue is likely in how the dashboard runs the greeting.

#### ❌ If you see logs but hear NO sound:

**Check these in order:**

1. **System Volume**
   - Unmute your system
   - Increase volume to at least 50%

2. **Output Device Selection**
   - Open: System Preferences → Sound → Output
   - Look at the test logs for: `device_name=Ok("Your Device Name")`
   - Verify that device is selected in System Preferences
   - Try switching to a different output device

3. **Device Connection**
   - If using Bluetooth headphones: Check connection
   - If using USB headphones: Replug them
   - If using built-in speakers: Ensure they're not disabled

4. **Application Audio Permissions**
   - Go to: System Preferences → Security & Privacy → Privacy → Microphone
   - (Note: macOS doesn't require explicit audio OUTPUT permissions, but check anyway)

### Step 3: Test with Different Device

If still no audio:
1. Open System Preferences → Sound → Output
2. Select a different output device (e.g., "Built-in Speakers")
3. Run the test again: `cargo run --example test_greeting`

## Understanding the Logs

### Good Log Output:
```
INFO Found audio output device device_name=Ok("Bose QC Headphones")
INFO Playing tone through audio output frequency=600.0 duration_ms=150 device="Bose QC Headphones"
INFO Audio stream started successfully
INFO Audio playback complete samples_played=6615 total_samples=6615 playback_percentage=100
```

**What to look for:**
- `device_name=Ok("...")` - Shows which device is being used
- `playback_percentage=100` - Means all audio was sent to device
- No errors or warnings

### Bad Log Output:
```
ERROR Failed to initialize audio output device for greeting
```
OR
```
WARN Audio playback may have been incomplete (X/Y% played)
```

**What this means:**
- If you see ERROR: No audio device available or permission denied
- If you see WARN: Audio stream was interrupted

## Common Issues

### Issue 1: "No default audio output device found"
**Solution:**
- Ensure an audio output device is connected
- Check System Preferences → Sound → Output
- Restart the application after connecting a device

### Issue 2: Audio plays through wrong device
**Solution:**
- macOS uses the "default" output device
- Change default in: System Preferences → Sound → Output
- Click the device you want
- Run the test again

### Issue 3: Audio works in test but not in TUI
**Solution:**
- The TUI might be capturing audio output differently
- Check if the TUI has audio muted or redirected
- Try running outside of the TUI: `cargo run --bin xswarm`

## Advanced Debugging

### Enable Full Debug Logging

Run with debug logging:
```bash
RUST_LOG=debug cargo run --example test_greeting
```

This will show:
- Detailed CPAL device enumeration
- Sample buffer operations
- Stream state changes

### Check Audio Device List

On macOS, list all audio devices:
```bash
system_profiler SPAudioDataType
```

### Test with System Audio

Test if your speakers work at all:
```bash
say "Testing audio output"
```

If this works but the test doesn't, there may be a CPAL issue.

## Technical Notes

### Audio Stack
```
xSwarm Application
    ↓
audio_output.rs (Rust)
    ↓
CPAL (Cross-Platform Audio Library)
    ↓
CoreAudio (macOS)
    ↓
Hardware Audio Device
```

### Audio Parameters
- **Sample Rate**: 44100 Hz (CD quality)
- **Bit Depth**: 32-bit float (F32)
- **Channels**: 2 (Stereo)
- **Volume**: 50% (amplitude 0.5)

### Greeting Tones
- **600 Hz** → Low tone (150ms)
- **800 Hz** → Mid tone (150ms)
- **1000 Hz** → High tone (200ms)

## Still Not Working?

If none of the above solutions work:

1. **Capture the full log output:**
   ```bash
   cargo run --example test_greeting 2>&1 | tee audio_test.log
   ```

2. **Share the log file** for further analysis

3. **Check for known issues:**
   - CPAL doesn't support all audio devices
   - Some Bluetooth devices have latency issues
   - Virtual audio devices may not work

4. **Try a different audio device** if available

## Success Indicators

You'll know audio is working when you:
1. See all INFO logs without errors
2. See `playback_percentage=100` for each tone
3. **HEAR** three ascending tones (beep-beep-BEEP)

The tones should be clear, audible, and pleasant sounding.
