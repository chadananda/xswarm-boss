//! Minimal MOSHI test - fast compilation, easy iteration
//!
//! Usage: cargo run --example minimal_moshi_test --release
//!
//! This is a stripped-down version for rapid debugging iteration.

use anyhow::{Result, Context};
use candle::{Device, Tensor};
use hound::{WavWriter, WavSpec};
use std::path::Path;

// Import only what we need from moshi
use moshi::lm::StreamingLmModel;
use moshi::lm_generate::LmGenerate;

const SAMPLE_RATE: u32 = 24000; // MOSHI native sample rate
const NUM_CODEBOOKS: usize = 8;  // MIMI uses 8 codebooks
const GENERATED_CODEBOOKS: usize = 8;
const LM_SEED: u64 = 299792458; // Deterministic seed

fn main() -> Result<()> {
    println!("🧪 MINIMAL MOSHI TEST");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");

    // Step 1: Setup device
    println!("1️⃣  Setting up Metal device...");
    let device = Device::new_metal(0).context("Failed to create Metal device")?;
    println!("   ✅ Metal device ready\n");

    // Step 2: Load MOSHI models
    println!("2️⃣  Loading MOSHI models...");
    let moshi_weight = hf_hub::api::sync::Api::new()?
        .model("kyutai/moshiko-pytorch-bf16".to_string())
        .get("model.safetensors")?;

    let mimi_weight = hf_hub::api::sync::Api::new()?
        .model("kyutai/mimi".to_string())
        .get("model.safetensors")?;

    let lm_model = StreamingLmModel::from_safetensors(&moshi_weight, &device)?;
    let mimi_model = moshi::mimi_encoder_decoder::build_model(&mimi_weight, &device)?;
    println!("   ✅ Models loaded\n");

    // Step 3: Load test audio
    println!("3️⃣  Loading test audio...");
    let test_audio_path = "./tmp/test-user-hello.wav";
    let mut reader = hound::WavReader::open(test_audio_path)
        .context("Failed to open test audio")?;

    let samples: Vec<f32> = reader
        .samples::<i16>()
        .map(|s| s.unwrap() as f32 / 32768.0)
        .collect();

    println!("   ✅ Loaded {} samples\n", samples.len());

    // Step 4: Encode audio to codes
    println!("4️⃣  Encoding audio to MIMI codes...");
    let pcm_tensor = Tensor::from_vec(samples, (1, 1, samples.len()), &device)?;
    let codes_stream = mimi_model.encode_step(&pcm_tensor.into(), &().into())?;
    let codes_tensor = codes_stream.get_last_value().unwrap().value();
    let (_batch, _codebooks, num_steps) = codes_tensor.dims3()?;
    println!("   ✅ Encoded to {} steps\n", num_steps);

    // Step 5: Generate response with LM
    println!("5️⃣  Generating audio tokens with language model...");
    let mut lm_gen = LmGenerate::new(lm_model, NUM_CODEBOOKS, Some(LM_SEED));

    // Feed encoded user audio as text tokens
    for step in 0..num_steps {
        let step_codes = codes_tensor.i((.., .., step..step + 1))?;
        let codes = step_codes.i((0, 0..NUM_CODEBOOKS, 0))?.to_vec1::<u32>()?;
        lm_gen.step(&codes[..], &[])?;
    }

    // Generate 62 steps of response (≈2.5 seconds)
    let mut all_audio_tokens = Vec::new();
    for step_idx in 0..62 {
        let (_text_token, audio_tokens) = lm_gen.step(&[], &[])?;
        println!("   Step {}: Generated {} audio tokens", step_idx, audio_tokens.len());
        all_audio_tokens.push(audio_tokens);
    }
    println!("   ✅ Generated {} frames\n", all_audio_tokens.len());

    // Step 6: Decode audio tokens to PCM
    println!("6️⃣  Decoding audio tokens to PCM...");
    let mut all_samples = Vec::new();

    for (frame_idx, audio_tokens) in all_audio_tokens.iter().enumerate() {
        let audio_tokens_slice = &audio_tokens[..GENERATED_CODEBOOKS];

        // TEST DIFFERENT TENSOR CREATION PATTERNS HERE:

        // Pattern A (current - v8.3): reshape + transpose
        let audio_tensor = Tensor::new(audio_tokens_slice, &device)?
            .reshape((1, 1, ()))?
            .t()?;

        // Pattern B (direct): from_slice with shape
        // let audio_tensor = Tensor::from_slice(
        //     audio_tokens_slice,
        //     (1, GENERATED_CODEBOOKS, 1),
        //     &device,
        // )?;

        let decoded = mimi_model.decode_step(&audio_tensor.into(), &().into())?;
        let pcm_tensor = decoded.get_last_value().unwrap().value();
        let frame_samples = pcm_tensor.flatten_all()?.to_vec1::<f32>()?;

        if frame_idx % 20 == 0 {
            println!("   Decoded frame {}: {} samples", frame_idx, frame_samples.len());
        }

        all_samples.extend(frame_samples);
    }
    println!("   ✅ Decoded {} total samples\n", all_samples.len());

    // Step 7: Save WAV file
    println!("7️⃣  Saving WAV file...");
    let output_path = "./tmp/minimal-moshi-output.wav";
    let spec = WavSpec {
        channels: 1,
        sample_rate: SAMPLE_RATE,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };

    let mut writer = WavWriter::create(output_path, spec)?;
    for sample in all_samples {
        let sample_i16 = (sample * 32767.0).clamp(-32768.0, 32767.0) as i16;
        writer.write_sample(sample_i16)?;
    }
    writer.finalize()?;

    println!("   ✅ Saved to: {}\n", output_path);

    // Step 8: Show playback command
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("✅ COMPLETE!");
    println!("\n🎧 Listen to output:");
    println!("   afplay {}", output_path);
    println!("\n📊 Check MD5:");
    println!("   md5 {}", output_path);

    Ok(())
}
