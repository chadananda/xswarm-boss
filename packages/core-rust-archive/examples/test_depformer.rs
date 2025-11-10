// Test MOSHI Depformer Loading
//
// This example verifies that the MOSHI language model loads with depformer
// Run with: RUST_LOG=info cargo run --example test_depformer

use anyhow::{Context, Result};
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .with_target(false)
        .init();

    println!("\n=== Testing MOSHI Depformer Loading ===\n");

    // Create voice config (uses default model paths)
    let config = xswarm::voice::VoiceConfig::default();
    println!("Model file: {}", config.lm_model_file);
    println!("Loading MOSHI language model...\n");

    // Select device
    let device = if candle::utils::metal_is_available() {
        println!("Using Metal (Apple Silicon GPU)");
        candle::Device::new_metal(0)?
    } else if candle::utils::cuda_is_available() {
        println!("Using CUDA");
        candle::Device::new_cuda(0)?
    } else {
        println!("Using CPU");
        candle::Device::Cpu
    };

    // Load model
    let dtype = if device.is_cuda() {
        candle::DType::BF16
    } else {
        candle::DType::F32
    };

    let lm_model = moshi::lm::load_streaming(&config.lm_model_file, dtype, &device)
        .context("Failed to load language model")?;

    // Check depformer
    let generated_codebooks = lm_model.generated_audio_codebooks();
    println!("\n=== Depformer Status ===");
    println!("Generated audio codebooks: {}", generated_codebooks);

    if generated_codebooks == 0 {
        eprintln!("\n❌ CRITICAL: Depformer is MISSING!");
        eprintln!("   The model cannot generate audio tokens for voice responses.");
        eprintln!("   This means MOSHI will only transcribe but not speak.\n");
        anyhow::bail!("Depformer not found in model");
    } else {
        println!("\n✅ SUCCESS: Depformer loaded correctly!");
        println!("   MOSHI can generate {} audio codebooks for voice responses.\n", generated_codebooks);
    }

    Ok(())
}
