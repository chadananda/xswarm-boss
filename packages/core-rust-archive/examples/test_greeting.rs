// Test Greeting Tone - Tests the exact greeting sequence used by MOSHI
//
// This example tests the greeting tone that plays when voice system starts
// Run with: cargo run --example test_greeting

use anyhow::Result;
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging with INFO level to see all the detailed logs
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .init();

    println!("\n=== Testing MOSHI Greeting Tone ===\n");
    println!("This is the exact greeting sequence that plays when voice system starts.");
    println!("Listen carefully - you should hear three ascending tones.\n");

    // Call the same function that's called from the dashboard
    match xswarm::voice::generate_greeting_tone().await {
        Ok(()) => {
            println!("\n✓ Greeting tone sequence completed successfully!");
            println!("\nDid you hear three ascending tones?");
            println!("If YES: Audio output is working correctly!");
            println!("If NO: Check your speaker volume and output device selection.\n");
            Ok(())
        }
        Err(e) => {
            eprintln!("\n✗ Greeting tone failed: {}", e);
            eprintln!("\nError details: {:?}", e);
            Err(e)
        }
    }
}
