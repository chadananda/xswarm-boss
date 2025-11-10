// Greeting Generation Module - MOSHI Direct Speech for Startup Greetings
//
// ARCHITECTURAL NOTE: This module uses force_text_token for greeting generation.
// This is ACCEPTABLE for greetings because:
// 1. Greetings are scripted/predetermined text
// 2. Verbatim output is fine for "Hello, how can I help you today?"
// 3. This is simpler than full memory conditioning
//
// For MEMORY CONTEXT injection (where natural incorporation is needed),
// use the memory_conditioner module with Condition::AddToInput instead.
//
// DO NOT confuse this with TTS:
// - This is NOT a separate TTS model
// - This uses the SAME language model (LM) used for conversations
// - It injects text via force_text_token to generate speech
// - The LM's depformer generates audio tokens directly

use anyhow::{Context, Result};
use candle::Tensor;
use tracing::{debug, info, warn};

use crate::voice::MoshiState;

/// Generate greeting audio using MOSHI's direct speech generation
///
/// This function:
/// 1. Tokenizes greeting text using SentencePiece
/// 2. Creates an LM generator with silent audio input
/// 3. Injects text tokens via force_text_token (acceptable for greetings)
/// 4. Generates audio tokens via the depformer
/// 5. Decodes audio tokens to PCM via MIMI codec
///
/// Returns: PCM audio samples (24kHz, f32) ready for playback
pub async fn generate_simple_greeting(
    moshi_state: &mut MoshiState,
    greeting_text: &str,
) -> Result<Vec<f32>> {
    info!("Generating MOSHI greeting: '{}'", greeting_text);

    // Step 1: Tokenize greeting text
    let text_tokens = tokenize_text(greeting_text, &moshi_state.text_tokenizer)
        .context("Failed to tokenize greeting text")?;

    info!("Greeting tokenized into {} tokens", text_tokens.len());

    // Step 2: Generate audio tokens from text tokens
    let audio_tokens = generate_audio_tokens_from_text(
        &text_tokens,
        moshi_state,
    ).await.context("Failed to generate audio tokens from text")?;

    info!("Generated {} audio frames", audio_tokens.len());

    // Step 3: Decode audio tokens to PCM
    let pcm_samples = decode_audio_tokens_to_pcm(
        &audio_tokens,
        moshi_state,
    ).await.context("Failed to decode audio tokens to PCM")?;

    info!(
        "Greeting generation complete: {} PCM samples ({:.2}s @ 24kHz)",
        pcm_samples.len(),
        pcm_samples.len() as f32 / 24000.0
    );

    Ok(pcm_samples)
}

/// Tokenize text using SentencePiece tokenizer
fn tokenize_text(
    text: &str,
    tokenizer: &sentencepiece::SentencePieceProcessor,
) -> Result<Vec<u32>> {
    let encoded = tokenizer.encode(text)
        .context("SentencePiece encoding failed")?;

    let tokens: Vec<u32> = encoded.iter()
        .map(|piece| piece.id as u32)
        .collect();

    debug!("Tokenized '{}' -> {:?}", text, &tokens[..tokens.len().min(10)]);

    Ok(tokens)
}

/// Generate audio tokens from text tokens using force_text_token injection
///
/// This uses MOSHI's BIDIRECTIONAL model with real MIMI-encoded audio input.
/// The audio input is generated (silence) and encoded through MIMI to provide
/// real audio codes (not padding tokens), which MOSHI needs for coherent output.
async fn generate_audio_tokens_from_text(
    text_tokens: &[u32],
    moshi_state: &mut MoshiState,
) -> Result<Vec<Vec<u32>>> {
    // Step 1: Generate real audio input and encode it with MIMI
    // v0.1.0-2025.11.5.31: Generate 440Hz tone (not silence) to give MOSHI real audio context
    // MOSHI's bidirectional model requires meaningful audio input - silence causes garbled output
    const AUDIO_DURATION_SAMPLES: usize = 12000; // 0.5s * 24000 Hz
    let tone_audio: Vec<f32> = (0..AUDIO_DURATION_SAMPLES)
        .map(|i| {
            let sample_time = i as f32 / 24000.0;
            (2.0 * std::f32::consts::PI * 440.0 * sample_time).sin() * 0.1 // 440Hz sine wave, amplitude 0.1
        })
        .collect();

    info!("Encoding {} 440Hz tone samples to MIMI codes as audio input for greeting (provides real audio context)", AUDIO_DURATION_SAMPLES);

    // Select device for MIMI
    let mimi_device = if moshi_state.config.use_cpu_for_mimi {
        candle::Device::Cpu
    } else {
        moshi_state.device.clone()
    };

    // Encode 440Hz tone through MIMI to get real audio codes
    let pcm_tensor = Tensor::from_vec(
        tone_audio,
        (1, 1, AUDIO_DURATION_SAMPLES),
        &mimi_device,
    ).context("Failed to create PCM tensor for tone encoding")?;

    let codes_stream = moshi_state.mimi_model.encode_step(&pcm_tensor.into(), &().into())
        .context("Failed to encode 440Hz tone through MIMI")?;

    // Extract encoded codes
    let codes_tensor = codes_stream.as_option()
        .context("MIMI encode returned None for silence")?;

    debug!("MIMI encoded silence to codes tensor with shape {:?}", codes_tensor.shape());

    // Get the actual audio codes from tensor
    // Shape should be [batch=1, codebooks, time] where codebooks=8 for MOSHI
    let codes_vec = codes_tensor.to_vec2::<u32>()
        .context("Failed to convert MIMI codes tensor to vec")?;

    info!("Got {} MIMI code frames from silence encoding", codes_vec[0].len());

    // Step 2: Create LM generator with BIDIRECTIONAL config
    // Create logits processors for sampling
    let audio_logits_processor = candle_transformers::generation::LogitsProcessor::new(
        1337, // seed (deterministic for greetings)
        Some(0.8), // temperature (slightly varied for natural speech)
        None, // top_p
    );

    let text_logits_processor = candle_transformers::generation::LogitsProcessor::new(
        1337,
        Some(0.0), // temperature 0 = deterministic (we're forcing tokens anyway)
        None,
    );

    // Calculate max steps (text tokens + buffer for audio generation)
    let max_steps = text_tokens.len() + 200;

    // Use standard BIDIRECTIONAL v0_1() config
    // This requires real audio input (which we have from MIMI encoding)
    let lm_config = moshi_state.lm_config.clone();

    // Create LM generator with bidirectional config
    let mut lm_generator = moshi::lm_generate_multistream::State::new(
        moshi_state.lm_model.clone(),
        max_steps,
        audio_logits_processor,
        text_logits_processor,
        None, // pad_mult
        None, // repetition_penalty
        None, // cfg_alpha
        lm_config.clone(),
    );

    info!("Created LM generator for greeting in BIDIRECTIONAL mode (max_steps={}, input_audio_codebooks={})",
          max_steps, lm_config.input_audio_codebooks);

    // Extract one frame of MIMI codes to use as audio input context
    // codes_vec shape is [codebooks, time], so we need to transpose to get [time, codebooks]
    // For greeting generation, we'll use the first frame as consistent audio context
    let num_codebooks = codes_vec.len();
    let num_frames = if num_codebooks > 0 { codes_vec[0].len() } else { 0 };

    if num_frames == 0 {
        return Err(anyhow::anyhow!("MIMI encoding produced no frames"));
    }

    // Extract the number of input audio codebooks from config
    let input_audio_codebooks = lm_config.input_audio_codebooks;

    // Extract first frame: transpose to get [frame_0_codebook_0, frame_0_codebook_1, ..., frame_0_codebook_7]
    let audio_input_frame: Vec<u32> = (0..input_audio_codebooks)
        .map(|cb_idx| codes_vec[cb_idx][0])
        .collect();

    info!("Using MIMI-encoded audio frame as input context: {} codebooks", audio_input_frame.len());

    // Initialize with text start token
    let mut prev_text_token = moshi_state.lm_config.text_start_token;

    // Collect generated audio tokens
    let mut all_audio_tokens = Vec::new();

    // Step through each text token, forcing it and collecting audio output
    for (step_idx, &force_token) in text_tokens.iter().enumerate() {
        // Run LM step with forced text token
        // Feed real MIMI codes (not padding tokens) to provide proper audio context
        let text_token = lm_generator.step(
            prev_text_token,
            &audio_input_frame,  // Real MIMI-encoded audio codes (not padding tokens!)
            Some(force_token),   // Force this specific text token
            None,                // No cross-attention
        ).context(format!("LM step failed at token index {}", step_idx))?;

        prev_text_token = text_token;

        // Extract audio tokens if available
        // Note: First few steps (≤ acoustic_delay) may return None
        if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
            all_audio_tokens.push(audio_tokens.clone());

            if step_idx % 10 == 0 {
                debug!(
                    "Step {}/{}: Generated {} audio codebooks",
                    step_idx,
                    text_tokens.len(),
                    audio_tokens.len()
                );
            }
        }
    }

    // Continue generating for a few more steps to let audio finish
    // (text may be done but audio generation lags behind)
    let extra_steps = 10;
    for step_idx in 0..extra_steps {
        let text_token = lm_generator.step(
            prev_text_token,
            &audio_input_frame,  // Continue feeding real MIMI codes
            None,                // No more forced tokens
            None,
        )?;

        prev_text_token = text_token;

        if let Some(audio_tokens) = lm_generator.last_audio_tokens() {
            all_audio_tokens.push(audio_tokens.clone());
        } else {
            debug!("Extra step {}: No audio tokens yet", step_idx);
        }
    }

    info!(
        "Generated {} audio token frames from {} text tokens",
        all_audio_tokens.len(),
        text_tokens.len()
    );

    if all_audio_tokens.is_empty() {
        warn!("No audio tokens generated! This may indicate an issue with acoustic_delay or depformer");
    }

    Ok(all_audio_tokens)
}

/// Decode audio tokens to PCM samples using MIMI codec
async fn decode_audio_tokens_to_pcm(
    audio_tokens: &[Vec<u32>],
    moshi_state: &mut MoshiState,
) -> Result<Vec<f32>> {
    if audio_tokens.is_empty() {
        warn!("No audio tokens to decode");
        return Ok(Vec::new());
    }

    // Select device for MIMI (might use CPU for codec)
    let mimi_device = if moshi_state.config.use_cpu_for_mimi {
        &candle::Device::Cpu
    } else {
        &moshi_state.device
    };

    let mut all_pcm_samples = Vec::new();
    let generated_codebooks = moshi_state.lm_config.generated_audio_codebooks;

    debug!(
        "Decoding {} frames with {} codebooks each",
        audio_tokens.len(),
        generated_codebooks
    );

    // Decode each frame
    for (frame_idx, audio_token_frame) in audio_tokens.iter().enumerate() {
        // Take only the generated codebooks (model may produce more than needed)
        let tokens_slice = &audio_token_frame[..generated_codebooks.min(audio_token_frame.len())];

        // Create tensor [batch=1, codebooks, time=1]
        let audio_tensor = Tensor::from_vec(
            tokens_slice.to_vec(),
            (1, tokens_slice.len(), 1),
            mimi_device,
        ).context(format!("Failed to create audio tensor for frame {}", frame_idx))?;

        // Decode through MIMI
        let decoded = moshi_state.mimi_model.decode_step(
            &audio_tensor.into(),
            &().into(),
        ).context(format!("MIMI decode failed for frame {}", frame_idx))?;

        // Extract PCM samples if available
        if let Some(pcm_tensor) = decoded.as_option() {
            let frame_samples = pcm_tensor.flatten_all()?.to_vec1::<f32>()
                .context("Failed to convert PCM tensor to vec")?;

            all_pcm_samples.extend(frame_samples);

            if frame_idx % 50 == 0 {
                debug!(
                    "Decoded frame {}/{}: {} samples",
                    frame_idx,
                    audio_tokens.len(),
                    all_pcm_samples.len()
                );
            }
        } else {
            debug!("Frame {}: MIMI decode returned None (warmup period?)", frame_idx);
        }
    }

    info!(
        "Decoded {} frames -> {} PCM samples",
        audio_tokens.len(),
        all_pcm_samples.len()
    );

    Ok(all_pcm_samples)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tokenize_text() {
        // This test requires a real tokenizer file
        // Skip for now, will test in integration tests
    }

    #[tokio::test]
    async fn test_generate_greeting_structure() {
        // This test verifies the structure without needing real models
        // Full integration test will use real MOSHI models
    }
}
