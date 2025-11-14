"""
Tests for Twilio audio format conversion (mulaw ↔ PCM 24kHz).

Tests verify:
- Roundtrip conversion preserves audio quality
- Sample rate conversion (8kHz ↔ 24kHz)
- Format conversion (mulaw ↔ PCM)
- Edge cases (silence, loud audio, clipping)
"""

import pytest
import numpy as np
import base64
import audioop

from assistant.phone.audio_converter import (
    mulaw_to_pcm24k,
    pcm24k_to_mulaw,
    get_audio_stats,
)


class TestAudioConverter:
    """Test suite for audio format conversion."""

    def test_mulaw_to_pcm_basic(self):
        """Test basic mulaw to PCM conversion."""
        # Create simple mulaw audio (silence)
        mulaw_bytes = b'\xff' * 160  # 20ms of mulaw silence at 8kHz
        mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

        # Convert to PCM 24kHz
        pcm = mulaw_to_pcm24k(mulaw_base64)

        # Verify output
        assert isinstance(pcm, np.ndarray)
        assert pcm.dtype == np.float32
        assert len(pcm) == 160 * 3  # 3x upsampling (8kHz → 24kHz)
        assert np.all(np.abs(pcm) <= 1.0)  # Normalized to [-1.0, 1.0]

    def test_pcm_to_mulaw_basic(self):
        """Test basic PCM to mulaw conversion."""
        # Create simple PCM audio (silence)
        pcm = np.zeros(480, dtype=np.float32)  # 20ms at 24kHz

        # Convert to mulaw
        mulaw_base64 = pcm24k_to_mulaw(pcm)

        # Verify output
        assert isinstance(mulaw_base64, str)
        mulaw_bytes = base64.b64decode(mulaw_base64)
        assert len(mulaw_bytes) == 480 // 3  # 3x downsampling (24kHz → 8kHz)

    def test_roundtrip_silence(self):
        """Test roundtrip conversion preserves silence."""
        # Original mulaw silence
        mulaw_bytes = b'\xff' * 160
        original_mulaw = base64.b64encode(mulaw_bytes).decode('utf-8')

        # Roundtrip: mulaw → PCM → mulaw
        pcm = mulaw_to_pcm24k(original_mulaw)
        result_mulaw = pcm24k_to_mulaw(pcm)

        # Verify silence is preserved (allow small error due to resampling)
        pcm_original = mulaw_to_pcm24k(original_mulaw)
        pcm_result = mulaw_to_pcm24k(result_mulaw)

        rms_original = np.sqrt(np.mean(pcm_original ** 2))
        rms_result = np.sqrt(np.mean(pcm_result ** 2))

        assert rms_original < 0.05  # Original is silence
        assert rms_result < 0.05    # Result is still silence

    def test_roundtrip_sine_wave(self):
        """Test roundtrip conversion with sine wave."""
        # Generate 440Hz sine wave at 24kHz (20ms)
        sample_rate = 24000
        duration = 0.02  # 20ms
        frequency = 440  # A4 note
        samples = int(sample_rate * duration)

        t = np.linspace(0, duration, samples, endpoint=False)
        sine_wave = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.5

        # Roundtrip: PCM → mulaw → PCM
        mulaw = pcm24k_to_mulaw(sine_wave)
        result = mulaw_to_pcm24k(mulaw)

        # Verify audio quality (correlation should be high)
        # Note: mulaw compression introduces some distortion
        correlation = np.corrcoef(sine_wave, result)[0, 1]
        assert correlation > 0.85  # Allow some distortion from mulaw compression

    def test_sample_rate_conversion(self):
        """Test sample rate conversion accuracy."""
        # Create audio at 8kHz
        mulaw_bytes = b'\xff' * 800  # 100ms at 8kHz
        mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

        # Convert to 24kHz
        pcm_24k = mulaw_to_pcm24k(mulaw_base64)

        # Verify 3x upsampling
        assert len(pcm_24k) == 800 * 3  # 2400 samples

        # Convert back to 8kHz
        mulaw_result = pcm24k_to_mulaw(pcm_24k)
        mulaw_bytes_result = base64.b64decode(mulaw_result)

        # Verify 3x downsampling
        assert len(mulaw_bytes_result) == 800

    def test_normalization_range(self):
        """Test PCM values are properly normalized to [-1.0, 1.0]."""
        # Create loud mulaw audio (max amplitude)
        mulaw_bytes = b'\x00' * 160  # Max positive amplitude
        mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

        # Convert to PCM
        pcm = mulaw_to_pcm24k(mulaw_base64)

        # Verify normalization
        assert np.all(pcm >= -1.0)
        assert np.all(pcm <= 1.0)
        assert np.max(np.abs(pcm)) > 0.5  # Should be loud

    def test_edge_case_empty_audio(self):
        """Test handling of empty audio."""
        # Empty mulaw audio
        mulaw_base64 = base64.b64encode(b'').decode('utf-8')

        # Convert should handle gracefully
        pcm = mulaw_to_pcm24k(mulaw_base64)
        assert len(pcm) == 0

    def test_edge_case_single_sample(self):
        """Test handling of single sample."""
        # Single mulaw sample
        mulaw_bytes = b'\xff'
        mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

        # Convert to PCM (should upsample to 3 samples)
        pcm = mulaw_to_pcm24k(mulaw_base64)
        assert len(pcm) == 3  # 3x upsampling

    def test_edge_case_clipping(self):
        """Test handling of audio at max amplitude."""
        # Create max amplitude PCM
        pcm = np.ones(480, dtype=np.float32)  # Max positive

        # Convert to mulaw and back
        mulaw = pcm24k_to_mulaw(pcm)
        result = mulaw_to_pcm24k(mulaw)

        # Verify no clipping (values stay within [-1.0, 1.0])
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)

    def test_get_audio_stats(self):
        """Test audio statistics helper."""
        # Create test audio
        audio = np.array([0.5, -0.5, 0.3, -0.3], dtype=np.float32)

        # Get stats
        stats = get_audio_stats(audio)

        # Verify stats
        assert stats['min'] == -0.5
        assert stats['max'] == 0.5
        assert stats['mean'] == 0.0
        assert stats['samples'] == 4
        assert 'rms' in stats
        assert stats['rms'] > 0

    def test_conversion_preserves_energy(self):
        """Test roundtrip conversion preserves audio energy."""
        # Create test signal with known energy
        pcm_original = np.random.randn(2400).astype(np.float32) * 0.3

        # Roundtrip
        mulaw = pcm24k_to_mulaw(pcm_original)
        pcm_result = mulaw_to_pcm24k(mulaw)

        # Calculate energy (RMS)
        energy_original = np.sqrt(np.mean(pcm_original ** 2))
        energy_result = np.sqrt(np.mean(pcm_result ** 2))

        # Energy should be similar (mulaw compression is lossy, allow 50% reduction)
        ratio = energy_result / energy_original
        assert 0.4 < ratio < 1.2

    def test_multiple_roundtrips(self):
        """Test multiple roundtrips degrade gracefully."""
        # Original signal
        pcm = np.random.randn(2400).astype(np.float32) * 0.3

        # Multiple roundtrips
        for i in range(5):
            mulaw = pcm24k_to_mulaw(pcm)
            pcm = mulaw_to_pcm24k(mulaw)

            # Verify still normalized
            assert np.all(np.abs(pcm) <= 1.0)

            # Verify still has energy
            rms = np.sqrt(np.mean(pcm ** 2))
            assert rms > 0.01  # Should still have signal

    def test_base64_encoding_decoding(self):
        """Test base64 encoding/decoding is consistent."""
        # Create mulaw bytes
        mulaw_bytes = bytes(range(256))
        mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

        # Verify encoding
        assert isinstance(mulaw_base64, str)
        assert len(mulaw_base64) > 0

        # Verify decoding
        decoded = base64.b64decode(mulaw_base64)
        assert decoded == mulaw_bytes

    @pytest.mark.parametrize("duration_ms", [20, 40, 60, 80, 100])
    def test_various_durations(self, duration_ms):
        """Test conversion with various audio durations."""
        # Create audio of specific duration at 24kHz
        samples = int(24000 * duration_ms / 1000)
        pcm = np.random.randn(samples).astype(np.float32) * 0.3

        # Roundtrip
        mulaw = pcm24k_to_mulaw(pcm)
        result = mulaw_to_pcm24k(mulaw)

        # Verify length is approximately preserved (within 1% due to resampling)
        length_ratio = len(result) / len(pcm)
        assert 0.99 < length_ratio < 1.01

    @pytest.mark.parametrize("amplitude", [0.1, 0.3, 0.5, 0.7, 0.9])
    def test_various_amplitudes(self, amplitude):
        """Test conversion with various audio amplitudes."""
        # Create audio with specific amplitude
        pcm = np.random.randn(2400).astype(np.float32) * amplitude

        # Roundtrip
        mulaw = pcm24k_to_mulaw(pcm)
        result = mulaw_to_pcm24k(mulaw)

        # Verify amplitude is approximately preserved
        original_rms = np.sqrt(np.mean(pcm ** 2))
        result_rms = np.sqrt(np.mean(result ** 2))

        ratio = result_rms / original_rms
        # Mulaw compression is lossy, especially at higher amplitudes
        # Allow 30-70% retention (lower amplitudes retain better)
        assert 0.3 < ratio < 1.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
