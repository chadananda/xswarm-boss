"""
Voice Activity Detection (VAD) using hybrid approach.

Combines:
1. Fast amplitude threshold (energy-based) for initial filtering
2. Silero VAD ML model for accurate voice confirmation

This hybrid approach reduces false positives while maintaining low latency.
"""

import numpy as np
from typing import Optional
import torch


class VoiceActivityDetector:
    """
    Simple energy-based VAD.

    Detects speech segments based on audio energy (RMS).
    Uses hysteresis with minimum speech/silence durations to
    avoid false triggers from brief noise.
    """

    def __init__(
        self,
        threshold: float = 0.02,
        min_speech_duration: int = 5,  # frames
        min_silence_duration: int = 10  # frames
    ):
        """
        Initialize VAD.

        Args:
            threshold: Energy threshold for voice detection (0.0 - 1.0)
            min_speech_duration: Min consecutive frames to trigger speech
            min_silence_duration: Min consecutive frames to end speech
        """
        self.threshold = threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration

        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0

    def process_frame(self, audio: np.ndarray) -> bool:
        """
        Process audio frame and return True if speech detected.

        Args:
            audio: Audio frame (1920 samples at 24kHz)

        Returns:
            True if currently in speech segment
        """
        # Calculate energy (RMS)
        energy = np.sqrt(np.mean(audio ** 2))

        is_voice = energy > self.threshold

        if is_voice:
            self.speech_frames += 1
            self.silence_frames = 0

            # Start speech if enough frames
            if self.speech_frames >= self.min_speech_duration:
                self.is_speaking = True
        else:
            self.silence_frames += 1

            # End speech if enough silence
            if self.silence_frames >= self.min_silence_duration:
                self.is_speaking = False
                self.speech_frames = 0

        return self.is_speaking

    def reset(self):
        """Reset VAD state."""
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0

    def get_energy(self, audio: np.ndarray) -> float:
        """
        Calculate audio energy for external use.

        Args:
            audio: Audio samples

        Returns:
            RMS energy value
        """
        return float(np.sqrt(np.mean(audio ** 2)))


class HybridVAD:
    """
    Hybrid VAD combining amplitude threshold + Silero ML model.

    Two-stage detection:
    1. Fast amplitude check (rejects obvious silence)
    2. Silero VAD (confirms actual speech)

    This reduces false positives while maintaining low latency.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        amplitude_threshold: float = 0.015,
        silero_threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500,
    ):
        """
        Initialize hybrid VAD.

        Args:
            sample_rate: Audio sample rate (16kHz for Silero)
            amplitude_threshold: Energy threshold for pre-filtering
            silero_threshold: Silero confidence threshold (0.0-1.0)
            min_speech_duration_ms: Min speech duration to trigger
            min_silence_duration_ms: Min silence to end speech
        """
        self.sample_rate = sample_rate
        self.amplitude_threshold = amplitude_threshold
        self.silero_threshold = silero_threshold

        # Convert durations to frame counts (assuming 30ms frames = 480 samples @ 16kHz)
        frame_ms = 30
        self.min_speech_frames = max(1, min_speech_duration_ms // frame_ms)
        self.min_silence_frames = max(1, min_silence_duration_ms // frame_ms)

        # State tracking
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0

        # Load Silero VAD model (lazy loading)
        self._silero_model = None
        self._silero_utils = None

    def _load_silero(self):
        """Lazy load Silero VAD model."""
        if self._silero_model is not None:
            return

        try:
            # Load Silero VAD from torch hub
            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False  # Use PyTorch model (faster on Apple Silicon with MPS)
            )
            self._silero_model = model
            self._silero_utils = utils

            # Move to appropriate device
            if torch.backends.mps.is_available():
                self._silero_model = self._silero_model.to('mps')
            elif torch.cuda.is_available():
                self._silero_model = self._silero_model.to('cuda')

            self._silero_model.eval()
        except Exception as e:
            print(f"Warning: Failed to load Silero VAD: {e}")
            print("Falling back to amplitude-only VAD")
            self._silero_model = "disabled"  # Mark as disabled

    def _check_amplitude(self, audio: np.ndarray) -> bool:
        """
        Fast amplitude check (pre-filter).

        Args:
            audio: Audio samples

        Returns:
            True if amplitude exceeds threshold
        """
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > self.amplitude_threshold

    def _check_silero(self, audio: np.ndarray) -> float:
        """
        Check Silero VAD confidence.

        Args:
            audio: Audio samples (must be 16kHz, 512+ samples)

        Returns:
            Silero confidence score (0.0-1.0)
        """
        self._load_silero()

        if self._silero_model == "disabled":
            # Fallback: use amplitude as confidence
            return 1.0 if self._check_amplitude(audio) else 0.0

        try:
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float()

            # Move to same device as model
            if hasattr(self._silero_model, 'device'):
                audio_tensor = audio_tensor.to(self._silero_model.device)

            # Get confidence from Silero
            with torch.no_grad():
                confidence = self._silero_model(audio_tensor, self.sample_rate).item()

            return confidence
        except Exception as e:
            print(f"Warning: Silero VAD failed: {e}")
            # Fallback to amplitude
            return 1.0 if self._check_amplitude(audio) else 0.0

    def process_frame(self, audio: np.ndarray) -> bool:
        """
        Process audio frame through hybrid VAD.

        Args:
            audio: Audio frame (16kHz, 512-4096 samples)

        Returns:
            True if speech detected
        """
        # Stage 1: Fast amplitude check
        if not self._check_amplitude(audio):
            # Obvious silence - skip Silero
            self.silence_frames += 1
            self.speech_frames = 0

            if self.silence_frames >= self.min_silence_frames:
                self.is_speaking = False

            return self.is_speaking

        # Stage 2: Silero confirmation (only for non-silent audio)
        confidence = self._check_silero(audio)
        is_voice = confidence >= self.silero_threshold

        if is_voice:
            self.speech_frames += 1
            self.silence_frames = 0

            # Start speech if enough frames
            if self.speech_frames >= self.min_speech_frames:
                self.is_speaking = True
        else:
            self.silence_frames += 1

            # End speech if enough silence
            if self.silence_frames >= self.min_silence_frames:
                self.is_speaking = False
                self.speech_frames = 0

        return self.is_speaking

    def reset(self):
        """Reset VAD state."""
        self.is_speaking = False
        self.speech_frames = 0
        self.silence_frames = 0

        # Reset Silero state if loaded
        if self._silero_model and self._silero_model != "disabled":
            try:
                self._silero_model.reset_states()
            except:
                pass  # Some Silero versions don't have reset_states

    def get_stats(self) -> dict:
        """
        Get VAD statistics.

        Returns:
            Dict with current state info
        """
        return {
            "is_speaking": self.is_speaking,
            "speech_frames": self.speech_frames,
            "silence_frames": self.silence_frames,
            "silero_loaded": self._silero_model is not None and self._silero_model != "disabled",
        }
