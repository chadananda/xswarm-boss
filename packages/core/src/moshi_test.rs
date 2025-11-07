// MOSHI Audio Testing Module
// v0.1.0-2025.11.6.1
//
// This module provides systematic testing of MOSHI audio output quality
// using OpenAI Whisper API for objective verification of intelligibility.

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use tracing::{info, warn, error};

/// Configuration for different audio processing experiments
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioConfig {
    pub name: String,
    pub description: String,
    pub resampler_sinc_len: usize,
    pub resampler_f_cutoff: f64,
    pub resampler_interpolation: String,
    pub resampler_oversampling: usize,
    pub resampler_window: String,
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            name: "default".to_string(),
            description: "Current production configuration".to_string(),
            resampler_sinc_len: 512,
            resampler_f_cutoff: 0.99,
            resampler_interpolation: "Linear".to_string(),
            resampler_oversampling: 512,
            resampler_window: "Blackman".to_string(),
        }
    }
}

/// Experiment result logging
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentResult {
    pub timestamp: String,
    pub config: AudioConfig,
    pub transcription: String,
    pub word_count: usize,
    pub intelligible: bool,
    pub audio_path: String,
}

/// OpenAI Whisper API response
#[derive(Debug, Deserialize)]
struct WhisperResponse {
    text: String,
}

/// Generate a simple test audio file (silent frame or simple tone)
/// This triggers MOSHI to generate a greeting response
pub fn generate_test_audio(output_path: &str) -> Result<()> {
    info!("Generating test audio file: {}", output_path);

    // Create 1 second of near-silence (very quiet noise to trigger VAD)
    // At 24kHz, that's 24000 samples
    let sample_rate = 24000;
    let duration_secs = 1.0;
    let num_samples = (sample_rate as f32 * duration_secs) as usize;

    // Generate very quiet white noise (amplitude ~0.001) to trigger voice activity detection
    use rand::Rng;
    let mut rng = rand::thread_rng();
    let samples: Vec<f32> = (0..num_samples)
        .map(|_| rng.gen::<f32>() * 0.002 - 0.001) // Range: [-0.001, 0.001]
        .collect();

    // Save as 24kHz 16-bit PCM WAV
    let spec = hound::WavSpec {
        channels: 1,
        sample_rate: sample_rate as u32,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };

    let mut writer = hound::WavWriter::create(output_path, spec)
        .context("Failed to create test WAV file")?;

    for &sample in &samples {
        let sample_i16 = (sample * 32767.0).clamp(-32768.0, 32767.0) as i16;
        writer.write_sample(sample_i16)?;
    }

    writer.finalize()?;

    info!("Test audio generated: {} samples ({:.2}s)", num_samples, duration_secs);
    Ok(())
}

/// Transcribe audio file using OpenAI Whisper API
pub async fn transcribe_with_whisper(audio_path: &str) -> Result<String> {
    info!("Transcribing audio with OpenAI Whisper API: {}", audio_path);

    // Get API key from environment
    let api_key = std::env::var("OPENAI_API_KEY")
        .context("OPENAI_API_KEY environment variable not set. Run: export OPENAI_API_KEY=sk-...")?;

    // Read the audio file
    let audio_data = fs::read(audio_path)
        .context(format!("Failed to read audio file: {}", audio_path))?;

    // Create multipart form
    let form = reqwest::multipart::Form::new()
        .text("model", "whisper-1")
        .part(
            "file",
            reqwest::multipart::Part::bytes(audio_data)
                .file_name("audio.wav")
                .mime_str("audio/wav")?,
        );

    // Call OpenAI API
    let client = reqwest::Client::new();
    let response = client
        .post("https://api.openai.com/v1/audio/transcriptions")
        .header("Authorization", format!("Bearer {}", api_key))
        .multipart(form)
        .send()
        .await
        .context("Failed to call OpenAI Whisper API")?;

    if !response.status().is_success() {
        let status = response.status();
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        anyhow::bail!("Whisper API error ({}): {}", status, error_text);
    }

    let whisper_response: WhisperResponse = response.json().await
        .context("Failed to parse Whisper API response")?;

    info!("Transcription: \"{}\"", whisper_response.text);
    Ok(whisper_response.text)
}

/// Check if transcription indicates intelligible speech
pub fn is_intelligible(transcription: &str) -> bool {
    let word_count = transcription.split_whitespace().count();
    let char_count = transcription.chars().filter(|c| c.is_alphabetic()).count();

    // Consider intelligible if we have at least 3 words and 10 characters
    let intelligible = word_count >= 3 && char_count >= 10;

    info!("Intelligibility check: {} words, {} chars -> {}",
          word_count, char_count, if intelligible { "PASS" } else { "FAIL" });

    intelligible
}

/// Log experiment result to avoid testing same config twice
pub fn log_experiment(result: &ExperimentResult) -> Result<()> {
    let log_dir = Path::new("./tmp/experiments");
    fs::create_dir_all(log_dir)?;

    let log_path = log_dir.join(format!("experiment_{}.json", result.timestamp));
    let json = serde_json::to_string_pretty(result)?;
    fs::write(&log_path, json)?;

    info!("Experiment logged: {}", log_path.display());
    Ok(())
}

/// Load all previous experiment results
pub fn load_experiment_history() -> Vec<ExperimentResult> {
    let log_dir = Path::new("./tmp/experiments");
    if !log_dir.exists() {
        return Vec::new();
    }

    let mut results = Vec::new();
    if let Ok(entries) = fs::read_dir(log_dir) {
        for entry in entries.flatten() {
            if let Ok(json) = fs::read_to_string(entry.path()) {
                if let Ok(result) = serde_json::from_str::<ExperimentResult>(&json) {
                    results.push(result);
                }
            }
        }
    }

    results.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
    results
}

/// Get next untested configuration to try
pub fn get_next_config_to_test(history: &[ExperimentResult]) -> Option<AudioConfig> {
    // Define a series of configurations to test systematically
    let configs = vec![
        AudioConfig {
            name: "config_1_ultra_high_quality".to_string(),
            description: "Ultra high quality: sinc_len=512, f_cutoff=0.99, Linear".to_string(),
            resampler_sinc_len: 512,
            resampler_f_cutoff: 0.99,
            resampler_interpolation: "Linear".to_string(),
            resampler_oversampling: 512,
            resampler_window: "Blackman".to_string(),
        },
        AudioConfig {
            name: "config_2_cubic_interpolation".to_string(),
            description: "Try Cubic interpolation instead of Linear".to_string(),
            resampler_sinc_len: 512,
            resampler_f_cutoff: 0.99,
            resampler_interpolation: "Cubic".to_string(),
            resampler_oversampling: 512,
            resampler_window: "Blackman".to_string(),
        },
        AudioConfig {
            name: "config_3_lower_cutoff".to_string(),
            description: "Lower cutoff frequency (0.95 instead of 0.99)".to_string(),
            resampler_sinc_len: 512,
            resampler_f_cutoff: 0.95,
            resampler_interpolation: "Linear".to_string(),
            resampler_oversampling: 512,
            resampler_window: "Blackman".to_string(),
        },
        AudioConfig {
            name: "config_4_shorter_sinc".to_string(),
            description: "Shorter sinc filter (256 instead of 512)".to_string(),
            resampler_sinc_len: 256,
            resampler_f_cutoff: 0.95,
            resampler_interpolation: "Cubic".to_string(),
            resampler_oversampling: 256,
            resampler_window: "BlackmanHarris2".to_string(),
        },
        AudioConfig {
            name: "config_5_no_resampling".to_string(),
            description: "Test without resampling (match device rate to MOSHI rate)".to_string(),
            resampler_sinc_len: 0, // Special marker for no resampling
            resampler_f_cutoff: 0.0,
            resampler_interpolation: "None".to_string(),
            resampler_oversampling: 0,
            resampler_window: "None".to_string(),
        },
    ];

    // Find first config not yet tested
    for config in configs {
        let already_tested = history.iter().any(|r| r.config.name == config.name);
        if !already_tested {
            return Some(config);
        }
    }

    None
}

/// Print test report
pub fn print_test_report(result: &ExperimentResult) {
    println!();
    println!("╔════════════════════════════════════════════════════════════════");
    println!("║ MOSHI AUDIO TEST RESULTS");
    println!("╠════════════════════════════════════════════════════════════════");
    println!("║ Configuration: {}", result.config.name);
    println!("║ {}", result.config.description);
    println!("╠════════════════════════════════════════════════════════════════");
    println!("║ 📝 Transcription:");
    println!("║    \"{}\"", result.transcription);
    println!("╠════════════════════════════════════════════════════════════════");
    println!("║ 📊 Analysis:");
    println!("║    Words detected: {}", result.word_count);
    println!("║    Text length: {} characters", result.transcription.len());
    println!("║    Audio file: {}", result.audio_path);
    println!("╠════════════════════════════════════════════════════════════════");
    if result.intelligible {
        println!("║ ✅ SUCCESS: Audio contains recognizable speech!");
        println!("║");
        println!("║ The audio pipeline is working correctly. MOSHI output is");
        println!("║ intelligible and can be transcribed by Whisper API.");
    } else {
        println!("║ ❌ FAILURE: No recognizable words detected");
        println!("║");
        println!("║ The audio is still garbled. Will try next configuration...");
    }
    println!("╚════════════════════════════════════════════════════════════════");
    println!();
}

/// Print experiment history summary
pub fn print_experiment_history(history: &[ExperimentResult]) {
    if history.is_empty() {
        return;
    }

    println!();
    println!("📋 Previous Test Results:");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    for result in history {
        let status = if result.intelligible { "✅" } else { "❌" };
        println!("{} {} - {} words - {}",
                 status,
                 result.config.name,
                 result.word_count,
                 result.timestamp);
    }
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!();
}
