// Whisper transcription tool for MOSHI audio debugging
// Usage: cargo run --example transcribe_moshi_audio [path/to/audio.wav]
//
// This tool transcribes MOSHI audio output to verify if it contains intelligible speech.
// Use with MOSHI_DEBUG_WAV=1 to capture audio to ./tmp/moshi-debug-audio.wav

use anyhow::Result;
use candle::{Device, Tensor};
use candle_transformers::models::whisper::{self as m, audio, Config};
use hound;
use std::env;
use std::path::PathBuf;

fn main() -> Result<()> {
    // Get WAV file path from args or use default
    let wav_path = env::args()
        .nth(1)
        .unwrap_or_else(|| "./tmp/moshi-debug-audio.wav".to_string());

    println!("🎙️  MOSHI Audio Transcription Test");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("📁 Input: {}", wav_path);
    println!();

    // Read WAV file
    println!("📖 Reading WAV file...");
    let mut reader = hound::WavReader::open(&wav_path)?;
    let spec = reader.spec();

    println!("   Channels: {}", spec.channels);
    println!("   Sample rate: {} Hz", spec.sample_rate);
    println!("   Bits per sample: {}", spec.bits_per_sample);
    println!("   Sample format: {:?}", spec.sample_format);

    // Read all samples
    let samples: Vec<f32> = reader
        .samples::<f32>()
        .map(|s| s.unwrap())
        .collect();

    let duration_secs = samples.len() as f32 / spec.sample_rate as f32;
    println!("   Duration: {:.2}s ({} samples)", duration_secs, samples.len());
    println!();

    // Resample to 16kHz (Whisper requirement) if needed
    let samples_16khz = if spec.sample_rate != 16000 {
        println!("🔄 Resampling {} Hz → 16000 Hz...", spec.sample_rate);
        resample_to_16khz(&samples, spec.sample_rate)?
    } else {
        samples
    };

    println!("   Resampled: {} samples", samples_16khz.len());
    println!();

    // Convert to mono if stereo
    let mono_samples = if spec.channels == 2 {
        println!("🔄 Converting stereo → mono...");
        stereo_to_mono(&samples_16khz)
    } else {
        samples_16khz
    };

    // Initialize Whisper model
    println!("🤖 Loading Whisper tiny model...");
    let device = Device::cuda_if_available(0)?;

    // Download model from HuggingFace
    let api = hf_hub::api::sync::Api::new()?;
    let repo = api.model("openai/whisper-tiny".to_string());
    let model_path = repo.get("model.safetensors")?;
    let config_path = repo.get("config.json")?;

    // Load config
    let config_str = std::fs::read_to_string(config_path)?;
    let config: Config = serde_json::from_str(&config_str)?;

    // Load model
    let vb = candle_nn::VarBuilder::from_pth(model_path, candle::DType::F32, &device)?;
    let model = m::model::Whisper::load(&vb, config)?;

    println!("   Model loaded on {:?}", device);
    println!();

    // Prepare audio for Whisper
    println!("🎵 Processing audio...");
    let mel_bytes = audio::pcm_to_mel(&config, &mono_samples, &[]);
    let mel_bytes = mel_bytes.unwrap();
    let mel = Tensor::from_vec(
        mel_bytes,
        (1, config.num_mel_bins, mel_bytes.len() / config.num_mel_bins),
        &device,
    )?;

    // Transcribe
    println!("✍️  Transcribing...");
    let mut dc = m::audio::DecodingConfig::default();
    dc.language = Some("en".to_string());
    dc.task = Some(m::audio::Task::Transcribe);

    let result = model.decode(&mel, &dc)?;

    println!();
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("📝 TRANSCRIPTION RESULT:");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("{}", result.text);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!();

    // Analysis
    let word_count = result.text.split_whitespace().count();
    println!("📊 Analysis:");
    println!("   Words detected: {}", word_count);
    println!("   Text length: {} characters", result.text.len());

    if word_count > 0 {
        println!();
        println!("✅ SUCCESS: Audio contains recognizable speech!");
        println!("   MOSHI audio pipeline is working correctly.");
    } else {
        println!();
        println!("❌ FAILURE: No recognizable words detected.");
        println!("   MOSHI audio is garbled or silent.");
        println!("   Try next audio pipeline configuration.");
    }

    Ok(())
}

/// Resample audio from source sample rate to 16kHz
fn resample_to_16khz(samples: &[f32], source_rate: u32) -> Result<Vec<f32>> {
    use rubato::{SincFixedIn, Resampler};

    let params = rubato::SincInterpolationParameters {
        sinc_len: 256,
        f_cutoff: 0.95,
        interpolation: rubato::SincInterpolationType::Linear,
        oversampling_factor: 256,
        window: rubato::WindowFunction::BlackmanHarris2,
    };

    let mut resampler = SincFixedIn::<f32>::new(
        16000.0 / source_rate as f64,
        2.0,
        params,
        1024,
        1,
    )?;

    let mut output = Vec::new();
    let chunk_size = resampler.input_frames_next();

    for chunk in samples.chunks(chunk_size) {
        let mut input = vec![chunk.to_vec()];

        // Pad last chunk if needed
        if chunk.len() < chunk_size {
            input[0].resize(chunk_size, 0.0);
        }

        let out = resampler.process(&input, None)?;
        output.extend_from_slice(&out[0]);
    }

    Ok(output)
}

/// Convert stereo to mono by averaging channels
fn stereo_to_mono(stereo: &[f32]) -> Vec<f32> {
    stereo
        .chunks(2)
        .map(|chunk| {
            if chunk.len() == 2 {
                (chunk[0] + chunk[1]) / 2.0
            } else {
                chunk[0]
            }
        })
        .collect()
}
