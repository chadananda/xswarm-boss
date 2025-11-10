// Test Audio Output - Diagnostic tool for audio system
//
// This example tests the audio output system to ensure speakers are working
// Run with: cargo run --example test_audio_output

use anyhow::Result;
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::DEBUG)
        .with_target(false)
        .init();

    println!("\n=== xSwarm Audio Output Test ===\n");

    // Test 1: Device initialization
    println!("Test 1: Initializing audio output device...");
    let audio = match xswarm::audio_output::AudioOutputDevice::new() {
        Ok(device) => {
            println!("✓ Audio device initialized successfully");
            device
        }
        Err(e) => {
            eprintln!("✗ Failed to initialize audio device: {}", e);
            return Err(e);
        }
    };

    // Test 2: Play a simple 440Hz tone (A4 note)
    println!("\nTest 2: Playing 440Hz tone for 500ms...");
    println!("(You should hear a clear tone from your speakers)");
    match audio.play_tone(440.0, 500).await {
        Ok(_) => println!("✓ Tone playback completed"),
        Err(e) => {
            eprintln!("✗ Failed to play tone: {}", e);
            return Err(e);
        }
    }

    tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;

    // Test 3: Play the greeting tone sequence
    println!("\nTest 3: Playing greeting tone sequence (600Hz → 800Hz → 1000Hz)...");
    println!("(You should hear three ascending tones)");

    if let Err(e) = audio.play_tone(600.0, 150).await {
        eprintln!("✗ Failed to play first tone: {}", e);
        return Err(e);
    }
    tokio::time::sleep(tokio::time::Duration::from_millis(30)).await;

    if let Err(e) = audio.play_tone(800.0, 150).await {
        eprintln!("✗ Failed to play second tone: {}", e);
        return Err(e);
    }
    tokio::time::sleep(tokio::time::Duration::from_millis(30)).await;

    if let Err(e) = audio.play_tone(1000.0, 200).await {
        eprintln!("✗ Failed to play third tone: {}", e);
        return Err(e);
    }

    println!("✓ Greeting tone sequence completed");

    println!("\n=== All Audio Tests Passed ===");
    println!("\nIf you didn't hear any sound:");
    println!("1. Check your speaker volume");
    println!("2. Check System Preferences → Sound → Output");
    println!("3. Verify the correct output device is selected");
    println!("4. Check macOS audio permissions for this application\n");

    Ok(())
}
