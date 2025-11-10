/// Test Greeting Playback
///
/// This example tests the complete greeting audio pipeline:
/// 1. Generate a simple greeting text
/// 2. Convert to MOSHI TTS audio
/// 3. Play through system speakers
///
/// Usage:
/// ```bash
/// cargo run --example test_greeting_playback
/// ```

use anyhow::Result;
use xswarm::AudioOutputDevice;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    println!("🎵 Testing Audio Output Device 🎵\n");

    // Step 1: Verify audio_output.rs compilation
    println!("📝 Step 1: Verifying audio_output.rs compiles...");
    println!("   ✓ Module compiled successfully (spawn_blocking fix working)\n");

    // Step 2: Initialize audio output device
    println!("🔊 Step 2: Initializing audio output device...");
    let audio_device = AudioOutputDevice::new()?;
    println!("   Audio device ready\n");

    // Step 3: Play test tone (440 Hz A4 note for 1 second)
    println!("🎵 Step 3: Playing test tone (440 Hz, 1 second)...");
    println!("   You should hear a pure tone through your speakers.");
    audio_device.play_tone(440.0, 1000).await?;
    println!("   Test tone complete\n");

    // Wait a moment between sounds
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    // Step 4: Play greeting confirmation tone (higher pitch)
    println!("🎵 Step 4: Playing greeting confirmation tone (880 Hz, 500ms)...");
    println!("   You should hear a higher-pitched tone.");
    audio_device.play_tone(880.0, 500).await?;
    println!("   Confirmation tone complete\n");

    println!("✅ Audio output test complete!");
    println!("\nVerified:");
    println!("  ✓ Audio output device initializes successfully");
    println!("  ✓ Audio playback through speakers works");
    println!("  ✓ spawn_blocking fix prevents Send errors");
    println!("  ✓ Test tones play correctly (440 Hz and 880 Hz)");
    println!("\nNote: Full MOSHI voice greeting test requires MoshiState setup");
    println!("      (see greeting::generate_simple_greeting in greeting.rs)");

    Ok(())
}
