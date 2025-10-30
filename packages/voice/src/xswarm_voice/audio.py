"""
Audio format conversion for xSwarm Voice Bridge

Handles conversion between:
- Twilio: 8kHz PCM int16 (from μ-law)
- MOSHI: 24kHz PCM float32

See planning/TWILIO_AUDIO_ARCHITECTURE.md for details.
"""

import numpy as np
from scipy import signal
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Audio format constants
TWILIO_SAMPLE_RATE = 8000  # Hz
MOSHI_SAMPLE_RATE = 24000  # Hz
RESAMPLE_RATIO = MOSHI_SAMPLE_RATE / TWILIO_SAMPLE_RATE  # 3.0


def twilio_to_moshi(audio_8khz: np.ndarray) -> np.ndarray:
    """
    Convert Twilio audio to MOSHI format.

    Pipeline:
    1. Convert int16 → float32 (normalize to [-1, 1])
    2. Resample 8kHz → 24kHz (3x upsampling)

    Args:
        audio_8khz: 8kHz PCM int16 from Twilio (after μ-law decode)

    Returns:
        24kHz PCM float32 for MOSHI

    Example:
        >>> audio_8k = np.array([0, 16384, 32767, -16384, -32768], dtype=np.int16)
        >>> audio_24k = twilio_to_moshi(audio_8k)
        >>> audio_24k.shape[0] == audio_8k.shape[0] * 3
        True
        >>> audio_24k.dtype == np.float32
        True
        >>> -1.0 <= audio_24k.max() <= 1.0
        True
    """
    if audio_8khz.dtype != np.int16:
        logger.warning(f"Expected int16, got {audio_8khz.dtype}. Converting...")
        audio_8khz = audio_8khz.astype(np.int16)

    if len(audio_8khz) == 0:
        logger.warning("Empty audio input")
        return np.array([], dtype=np.float32)

    # 1. Convert int16 → float32, normalize to [-1, 1]
    audio_float = audio_8khz.astype(np.float32) / 32768.0

    # 2. Resample 8kHz → 24kHz (3x upsampling)
    num_samples_24k = int(len(audio_float) * RESAMPLE_RATIO)
    audio_24khz = signal.resample(audio_float, num_samples_24k)

    # Ensure float32 (scipy.signal.resample returns float64)
    audio_24khz = audio_24khz.astype(np.float32)

    logger.debug(
        f"Upsampled: {len(audio_8khz)} samples @ 8kHz → "
        f"{len(audio_24khz)} samples @ 24kHz"
    )

    return audio_24khz


def moshi_to_twilio(audio_24khz: np.ndarray) -> np.ndarray:
    """
    Convert MOSHI audio to Twilio format.

    Pipeline:
    1. Resample 24kHz → 8kHz (3x downsampling)
    2. Clip to valid range [-1, 1]
    3. Convert float32 → int16

    Args:
        audio_24khz: 24kHz PCM float32 from MOSHI

    Returns:
        8kHz PCM int16 for Twilio (ready for μ-law encode)

    Example:
        >>> audio_24k = np.array([0.0, 0.5, 1.0, -0.5, -1.0], dtype=np.float32)
        >>> audio_8k = moshi_to_twilio(audio_24k)
        >>> audio_8k.dtype == np.int16
        True
        >>> len(audio_8k) < len(audio_24k)  # Downsampled
        True
    """
    if audio_24khz.dtype not in (np.float32, np.float64):
        logger.warning(f"Expected float32/64, got {audio_24khz.dtype}. Converting...")
        audio_24khz = audio_24khz.astype(np.float32)

    if len(audio_24khz) == 0:
        logger.warning("Empty audio input")
        return np.array([], dtype=np.int16)

    # 1. Resample 24kHz → 8kHz (3x downsampling)
    num_samples_8k = int(len(audio_24khz) / RESAMPLE_RATIO)
    audio_8khz = signal.resample(audio_24khz, num_samples_8k)

    # 2. Clip to valid range (prevent overflow)
    audio_8khz = np.clip(audio_8khz, -1.0, 1.0)

    # 3. Convert float32 → int16
    audio_int16 = (audio_8khz * 32767).astype(np.int16)

    logger.debug(
        f"Downsampled: {len(audio_24khz)} samples @ 24kHz → "
        f"{len(audio_int16)} samples @ 8kHz"
    )

    return audio_int16


def validate_audio_format(
    audio: np.ndarray,
    expected_dtype: type,
    expected_rate: int,
    name: str = "audio"
) -> None:
    """
    Validate audio array format.

    Args:
        audio: Audio array to validate
        expected_dtype: Expected numpy dtype
        expected_rate: Expected sample rate (for logging)
        name: Name for error messages

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(audio, np.ndarray):
        raise ValueError(f"{name} must be numpy array, got {type(audio)}")

    if audio.ndim != 1:
        raise ValueError(
            f"{name} must be 1D (mono), got shape {audio.shape}"
        )

    if audio.dtype != expected_dtype:
        raise ValueError(
            f"{name} must be {expected_dtype}, got {audio.dtype}"
        )

    logger.debug(
        f"Validated {name}: {len(audio)} samples, "
        f"{expected_rate}Hz, {expected_dtype}"
    )


def estimate_duration(num_samples: int, sample_rate: int) -> float:
    """
    Estimate audio duration in seconds.

    Args:
        num_samples: Number of audio samples
        sample_rate: Sample rate in Hz

    Returns:
        Duration in seconds

    Example:
        >>> estimate_duration(24000, 24000)
        1.0
        >>> estimate_duration(8000, 8000)
        1.0
    """
    return num_samples / sample_rate


# Convenience functions for common operations

def convert_for_moshi(audio: np.ndarray, source_rate: int) -> np.ndarray:
    """
    Convert any audio format to MOSHI format (24kHz float32).

    Args:
        audio: Input audio (int16 or float32)
        source_rate: Source sample rate (8000 or 24000)

    Returns:
        24kHz PCM float32 for MOSHI
    """
    if source_rate == MOSHI_SAMPLE_RATE:
        # Already 24kHz, just convert type if needed
        if audio.dtype == np.int16:
            return audio.astype(np.float32) / 32768.0
        return audio.astype(np.float32)

    elif source_rate == TWILIO_SAMPLE_RATE:
        # 8kHz → 24kHz conversion
        return twilio_to_moshi(audio)

    else:
        raise ValueError(
            f"Unsupported source rate: {source_rate}Hz. "
            f"Expected {TWILIO_SAMPLE_RATE}Hz or {MOSHI_SAMPLE_RATE}Hz"
        )


def convert_for_twilio(audio: np.ndarray, source_rate: int) -> np.ndarray:
    """
    Convert any audio format to Twilio format (8kHz int16).

    Args:
        audio: Input audio (int16 or float32)
        source_rate: Source sample rate (8000 or 24000)

    Returns:
        8kHz PCM int16 for Twilio
    """
    if source_rate == TWILIO_SAMPLE_RATE:
        # Already 8kHz, just convert type if needed
        if audio.dtype in (np.float32, np.float64):
            return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        return audio.astype(np.int16)

    elif source_rate == MOSHI_SAMPLE_RATE:
        # 24kHz → 8kHz conversion
        return moshi_to_twilio(audio)

    else:
        raise ValueError(
            f"Unsupported source rate: {source_rate}Hz. "
            f"Expected {TWILIO_SAMPLE_RATE}Hz or {MOSHI_SAMPLE_RATE}Hz"
        )
