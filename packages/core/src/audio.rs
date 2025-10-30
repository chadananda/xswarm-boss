// Audio Conversion Utilities
//
// This module provides audio format conversion utilities for
// integrating Twilio Media Streams (μ-law 8kHz) with MOSHI (PCM 24kHz).
//
// Key conversions:
// - μ-law ↔ PCM 16-bit
// - Sample rate conversion (8kHz ↔ 24kHz)
// - PCM i16 ↔ f32 normalization

use anyhow::Result;
use rubato::{
    Resampler, SincFixedIn, SincInterpolationParameters, SincInterpolationType, WindowFunction,
};

/// Convert μ-law encoded audio to PCM 16-bit samples
///
/// μ-law (also known as u-law) is a logarithmic compression algorithm used by
/// Twilio Media Streams. This implementation follows ITU-T G.711 standard.
///
/// # Arguments
/// * `mulaw_bytes` - μ-law encoded audio samples (8-bit each)
///
/// # Returns
/// PCM 16-bit samples
///
/// # Reference
/// https://en.wikipedia.org/wiki/Μ-law_algorithm
pub fn mulaw_to_pcm(mulaw_bytes: &[u8]) -> Vec<i16> {
    const MULAW_BIAS: i16 = 0x84;
    const MULAW_MAX: i16 = 0x1FFF;

    mulaw_bytes
        .iter()
        .map(|&mulaw| {
            // Complement to get original code
            let mulaw = !mulaw;

            // Extract mantissa and exponent
            let sign = (mulaw & 0x80) != 0;
            let exponent = ((mulaw & 0x70) >> 4) as i16;
            let mantissa = (mulaw & 0x0F) as i16;

            // Calculate PCM value
            let mut pcm = mantissa * 2 + 33;
            pcm = pcm << (exponent + 2);
            pcm -= MULAW_BIAS;

            // Clamp to valid range
            if pcm > MULAW_MAX {
                pcm = MULAW_MAX;
            }

            // Apply sign
            if sign {
                -pcm
            } else {
                pcm
            }
        })
        .collect()
}

/// Convert PCM 16-bit samples to μ-law encoded audio
///
/// This is the inverse of mulaw_to_pcm, encoding PCM audio using
/// the μ-law logarithmic compression algorithm.
///
/// # Arguments
/// * `pcm_samples` - PCM 16-bit samples
///
/// # Returns
/// μ-law encoded audio (8-bit per sample)
pub fn pcm_to_mulaw(pcm_samples: &[i16]) -> Vec<u8> {
    const MULAW_BIAS: i16 = 0x84;
    const MULAW_CLIP: i16 = 32635;

    pcm_samples
        .iter()
        .map(|&pcm| {
            // Get sign and absolute value
            let sign = if pcm < 0 { 0x80 } else { 0x00 };
            let mut pcm = pcm.abs();

            // Clip to valid range
            if pcm > MULAW_CLIP {
                pcm = MULAW_CLIP;
            }

            // Add bias
            pcm += MULAW_BIAS;

            // Find exponent
            let mut exponent = 7;
            for i in (0..8).rev() {
                if (pcm & (1 << (i + 5))) != 0 {
                    exponent = i;
                    break;
                }
            }

            // Extract mantissa
            let mantissa = if exponent == 0 {
                (pcm >> 4) & 0x0F
            } else {
                (pcm >> (exponent + 3)) & 0x0F
            };

            // Combine sign, exponent, and mantissa
            let mulaw = sign | ((exponent as u8) << 4) | (mantissa as u8);

            // Return complement
            !mulaw
        })
        .collect()
}

/// Convert PCM i16 samples to normalized f32 samples (-1.0 to 1.0)
///
/// # Arguments
/// * `pcm_samples` - PCM 16-bit samples
///
/// # Returns
/// Normalized f32 samples in range [-1.0, 1.0]
pub fn pcm_to_f32(pcm_samples: &[i16]) -> Vec<f32> {
    pcm_samples
        .iter()
        .map(|&sample| sample as f32 / 32768.0)
        .collect()
}

/// Convert normalized f32 samples to PCM i16 samples
///
/// # Arguments
/// * `f32_samples` - Normalized f32 samples (should be in range [-1.0, 1.0])
///
/// # Returns
/// PCM 16-bit samples
pub fn f32_to_pcm(f32_samples: &[f32]) -> Vec<i16> {
    f32_samples
        .iter()
        .map(|&sample| {
            let scaled = sample * 32768.0;
            scaled.clamp(-32768.0, 32767.0) as i16
        })
        .collect()
}

/// Audio resampler for converting between sample rates
///
/// Uses high-quality sinc interpolation for sample rate conversion.
/// This is a stateful resampler that can be reused across multiple chunks.
pub struct AudioResampler {
    resampler: SincFixedIn<f32>,
    from_rate: u32,
    to_rate: u32,
}

impl AudioResampler {
    /// Create a new audio resampler
    ///
    /// # Arguments
    /// * `from_rate` - Source sample rate (e.g., 8000 Hz)
    /// * `to_rate` - Target sample rate (e.g., 24000 Hz)
    /// * `chunk_size` - Size of input chunks in samples
    ///
    /// # Returns
    /// A new AudioResampler instance
    pub fn new(from_rate: u32, to_rate: u32, chunk_size: usize) -> Result<Self> {
        // Configure high-quality sinc interpolation
        let params = SincInterpolationParameters {
            sinc_len: 256,
            f_cutoff: 0.95,
            interpolation: SincInterpolationType::Cubic,  // Upgraded from Linear for better quality
            oversampling_factor: 256,
            window: WindowFunction::BlackmanHarris2,
        };

        let resampler = SincFixedIn::<f32>::new(
            to_rate as f64 / from_rate as f64,
            2.0,                      // max_resample_ratio_relative
            params,
            chunk_size,
            1,                        // channels (mono)
        )?;

        Ok(Self {
            resampler,
            from_rate,
            to_rate,
        })
    }

    /// Resample audio from source rate to target rate
    ///
    /// # Arguments
    /// * `samples` - Input samples at source sample rate
    ///
    /// # Returns
    /// Resampled audio at target sample rate
    pub fn resample(&mut self, samples: &[f32]) -> Result<Vec<f32>> {
        // Convert to rubato's expected format (Vec<Vec<f32>> for channels)
        let input = vec![samples.to_vec()];

        // Process resampling
        let output = self.resampler.process(&input, None)?;

        // Extract mono channel
        Ok(output[0].clone())
    }

    /// Get the input chunk size for this resampler
    pub fn chunk_size(&self) -> usize {
        self.resampler.input_frames_next()
    }

    /// Get the expected output size for a given input size
    pub fn output_size(&self, input_size: usize) -> usize {
        ((input_size as f64) * (self.to_rate as f64 / self.from_rate as f64)).ceil() as usize
    }
}

/// Complete audio conversion pipeline: Twilio μ-law 8kHz → MOSHI PCM f32 24kHz
///
/// # Arguments
/// * `mulaw_8khz` - μ-law encoded audio at 8kHz
/// * `resampler` - Audio resampler configured for 8kHz → 24kHz
///
/// # Returns
/// Normalized f32 PCM samples at 24kHz
pub fn twilio_to_moshi(mulaw_8khz: &[u8], resampler: &mut AudioResampler) -> Result<Vec<f32>> {
    // 1. μ-law → PCM i16 (still 8kHz)
    let pcm_8khz = mulaw_to_pcm(mulaw_8khz);

    // 2. PCM i16 → f32 normalized (still 8kHz)
    let f32_8khz = pcm_to_f32(&pcm_8khz);

    // 3. Resample 8kHz → 24kHz
    let f32_24khz = resampler.resample(&f32_8khz)?;

    Ok(f32_24khz)
}

/// Complete audio conversion pipeline: MOSHI PCM f32 24kHz → Twilio μ-law 8kHz
///
/// # Arguments
/// * `f32_24khz` - Normalized f32 PCM samples at 24kHz
/// * `resampler` - Audio resampler configured for 24kHz → 8kHz
///
/// # Returns
/// μ-law encoded audio at 8kHz
pub fn moshi_to_twilio(f32_24khz: &[f32], resampler: &mut AudioResampler) -> Result<Vec<u8>> {
    // 1. Resample 24kHz → 8kHz
    let f32_8khz = resampler.resample(f32_24khz)?;

    // 2. f32 normalized → PCM i16 (still 8kHz)
    let pcm_8khz = f32_to_pcm(&f32_8khz);

    // 3. PCM i16 → μ-law (still 8kHz)
    let mulaw_8khz = pcm_to_mulaw(&pcm_8khz);

    Ok(mulaw_8khz)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mulaw_roundtrip() {
        // Test μ-law encoding/decoding roundtrip
        let original = vec![0, 100, -100, 1000, -1000, 10000, -10000];
        let mulaw = pcm_to_mulaw(&original);
        let decoded = mulaw_to_pcm(&mulaw);

        // μ-law is lossy, so we check approximate equality
        for (orig, dec) in original.iter().zip(decoded.iter()) {
            let diff = (orig - dec).abs();
            assert!(diff < 100, "μ-law roundtrip error too large: {} -> {}", orig, dec);
        }
    }

    #[test]
    fn test_f32_conversion() {
        let pcm = vec![0, 16384, -16384, 32767, -32768];
        let f32_samples = pcm_to_f32(&pcm);
        let pcm_back = f32_to_pcm(&f32_samples);

        assert_eq!(pcm, pcm_back);
    }

    #[test]
    fn test_resampler() -> Result<()> {
        // Create resampler 8kHz → 24kHz
        let chunk_size = 160; // 20ms at 8kHz
        let mut resampler = AudioResampler::new(8000, 24000, chunk_size)?;

        // Generate test signal (1 second of 440 Hz sine wave at 8kHz)
        let samples: Vec<f32> = (0..8000)
            .map(|i| (2.0 * std::f32::consts::PI * 440.0 * i as f32 / 8000.0).sin() * 0.5)
            .collect();

        // Resample in chunks
        let mut output = Vec::new();
        for chunk in samples.chunks(chunk_size) {
            let resampled = resampler.resample(chunk)?;
            output.extend(resampled);
        }

        // Output should be roughly 3x the input size (24kHz / 8kHz = 3)
        assert!((output.len() as f32 / samples.len() as f32 - 3.0).abs() < 0.1);

        Ok(())
    }
}
