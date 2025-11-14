"""
Audio format conversion for Twilio Media Streams.

Converts between:
- Twilio format: mulaw 8kHz (base64 encoded)
- Moshi format: PCM 24kHz float32 (numpy array)
"""

import base64
import audioop
import numpy as np
from scipy import signal


def mulaw_to_pcm24k(mulaw_8k_base64: str) -> np.ndarray:
    """
    Convert Twilio mulaw audio to Moshi PCM format.

    Pipeline:
    1. base64 decode → mulaw 8kHz bytes
    2. mulaw decode → PCM 8kHz int16
    3. resample → PCM 24kHz int16
    4. normalize → PCM 24kHz float32 [-1.0, 1.0]

    Args:
        mulaw_8k_base64: Base64-encoded mulaw audio (Twilio format)

    Returns:
        PCM 24kHz float32 numpy array (Moshi format)
    """
    # Step 1: Decode base64 to mulaw bytes
    mulaw_bytes = base64.b64decode(mulaw_8k_base64)

    # Step 2: Decode mulaw to PCM 8kHz int16
    # audioop.ulaw2lin converts mulaw to linear PCM
    # width=2 means 16-bit (int16)
    pcm_8k_bytes = audioop.ulaw2lin(mulaw_bytes, 2)

    # Convert bytes to numpy array
    pcm_8k_int16 = np.frombuffer(pcm_8k_bytes, dtype=np.int16)

    # Step 3: Resample from 8kHz to 24kHz (3x upsampling)
    # scipy.signal.resample uses FFT for high-quality resampling
    num_samples_24k = len(pcm_8k_int16) * 3
    pcm_24k_int16 = signal.resample(pcm_8k_int16, num_samples_24k).astype(np.int16)

    # Step 4: Normalize to float32 [-1.0, 1.0]
    pcm_24k_float32 = pcm_24k_int16.astype(np.float32) / 32768.0

    return pcm_24k_float32


def pcm24k_to_mulaw(pcm_24k_float32: np.ndarray) -> str:
    """
    Convert Moshi PCM audio to Twilio mulaw format.

    Pipeline:
    1. denormalize → PCM 24kHz int16
    2. resample → PCM 8kHz int16
    3. mulaw encode → mulaw 8kHz bytes
    4. base64 encode → mulaw 8kHz base64

    Args:
        pcm_24k_float32: PCM 24kHz float32 numpy array (Moshi format)

    Returns:
        Base64-encoded mulaw audio (Twilio format)
    """
    # Step 1: Denormalize from float32 [-1.0, 1.0] to int16
    pcm_24k_int16 = (pcm_24k_float32 * 32767.0).astype(np.int16)

    # Step 2: Resample from 24kHz to 8kHz (3x downsampling)
    num_samples_8k = len(pcm_24k_int16) // 3
    pcm_8k_int16 = signal.resample(pcm_24k_int16, num_samples_8k).astype(np.int16)

    # Step 3: Encode PCM to mulaw
    # audioop.lin2ulaw converts linear PCM to mulaw
    # width=2 means 16-bit input
    pcm_8k_bytes = pcm_8k_int16.tobytes()
    mulaw_bytes = audioop.lin2ulaw(pcm_8k_bytes, 2)

    # Step 4: Encode to base64
    mulaw_base64 = base64.b64encode(mulaw_bytes).decode('utf-8')

    return mulaw_base64


def get_audio_stats(audio: np.ndarray) -> dict:
    """
    Get audio statistics for debugging.

    Args:
        audio: Audio numpy array

    Returns:
        Dict with min, max, mean, rms values
    """
    return {
        "min": float(np.min(audio)),
        "max": float(np.max(audio)),
        "mean": float(np.mean(audio)),
        "rms": float(np.sqrt(np.mean(audio ** 2))),
        "samples": len(audio),
    }
