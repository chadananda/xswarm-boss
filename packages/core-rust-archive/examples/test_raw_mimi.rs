// Minimal test of MIMI encode/decode without LM generator
// This will tell us if the bug is in MIMI or in the LM processing

use anyhow::Result;
use candle::{Device, Tensor};
use hf_hub::{api::sync::Api, Repo, RepoType};
use hound;

fn main() -> Result<()> {
    println!("🧪 RAW MIMI ENCODE/DECODE TEST");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    // 1. Load test audio
    println!("📂 Loading test audio...");
    let mut reader = hound::WavReader::open("./tmp/test-user-hello.wav")?;
    let samples: Vec<f32> = reader
        .samples::<i16>()
        .map(|s| s.unwrap() as f32 / 32768.0)
        .collect();

    println!("   Loaded {} samples at {}Hz", samples.len(), reader.spec().sample_rate);

    // 2. Initialize MIMI model
    println!("\n🔧 Loading MIMI model...");
    let device = Device::new_metal(0)?;
    let api = Api::new()?;
    let repo = api.repo(Repo::with_revision(
        "kyutai/moshiko-pytorch-bf16".to_string(),
        RepoType::Model,
        "main".to_string(),
    ));

    let config_filename = repo.get("config.json")?;
    let tokenizer_filename = repo.get("tokenizer_spm_32k_3.model")?;
    let weights_filename = repo.get("model.safetensors")?;

    let config: moshi::lm_model::Config = serde_json::from_str(&std::fs::read_to_string(config_filename)?)?;
    let mimi_config = config.mimi_config();

    use candle_nn::VarBuilder;
    let vb = unsafe { VarBuilder::from_mmaped_safetensors(&[weights_filename], candle::DType::BF16, &device)? };
    let mut mimi_model = moshi::mimi::Mimi::new(&mimi_config, vb.pp("mimi"))?;

    println!("   ✅ MIMI loaded");

    // 3. Take first 1920 samples (80ms at 24kHz)
    let frame_length = 1920;
    let test_samples: Vec<f32> = if samples.len() >= frame_length {
        samples[..frame_length].to_vec()
    } else {
        let mut padded = samples.clone();
        padded.resize(frame_length, 0.0);
        padded
    };

    println!("\n🎤 Testing with {} samples", test_samples.len());

    // 4. Encode
    println!("   Encoding...");
    let pcm_tensor = Tensor::from_vec(
        test_samples.clone(),
        (1, 1, frame_length),
        &device,
    )?;

    let codes_stream = mimi_model.encode_step(&pcm_tensor.into(), &().into())?;

    if let Some(codes_tensor) = codes_stream.as_option() {
        let (batch, codebooks, steps) = codes_tensor.dims3()?;
        println!("   ✅ Encoded: {} batch, {} codebooks, {} steps", batch, codebooks, steps);

        // 5. Decode immediately (same model instance - should share state)
        println!("   Decoding...");
        let decoded_stream = mimi_model.decode_step(&codes_tensor.into(), &().into())?;

        if let Some(decoded_tensor) = decoded_stream.as_option() {
            let decoded_samples = decoded_tensor.flatten_all()?.to_vec1::<f32>()?;
            println!("   ✅ Decoded: {} samples", decoded_samples.len());

            // 6. Save output
            let output_path = "./tmp/mimi-raw-test-output.wav";
            let spec = hound::WavSpec {
                channels: 1,
                sample_rate: 24000,
                bits_per_sample: 16,
                sample_format: hound::SampleFormat::Int,
            };

            let mut writer = hound::WavWriter::create(output_path, spec)?;
            for &sample in &decoded_samples {
                let sample_i16 = (sample.clamp(-1.0, 1.0) * 32767.0) as i16;
                writer.write_sample(sample_i16)?;
            }
            writer.finalize()?;

            println!("\n✅ Saved to: {}", output_path);
            println!("\n📊 Comparison:");
            println!("   Input:  {} samples", test_samples.len());
            println!("   Output: {} samples", decoded_samples.len());

            // Compare first 10 samples
            println!("\n🔍 First 10 samples comparison:");
            println!("   Index | Input      | Output     | Diff");
            println!("   ------+------------+------------+----------");
            for i in 0..10.min(test_samples.len()).min(decoded_samples.len()) {
                let diff = (test_samples[i] - decoded_samples[i]).abs();
                println!("   {:5} | {:10.6} | {:10.6} | {:8.6}",
                         i, test_samples[i], decoded_samples[i], diff);
            }

            println!("\n🎧 Listen to output:");
            println!("   afplay {}", output_path);

        } else {
            println!("   ❌ Decode returned None");
        }
    } else {
        println!("   ❌ Encode returned None");
    }

    Ok(())
}
