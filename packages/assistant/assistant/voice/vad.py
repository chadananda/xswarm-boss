"""
Voice Activity Detection (VAD) using energy-based detection.

This is a simple implementation that can be upgraded to use
Silero VAD or WebRTC VAD in the future for improved accuracy.
"""

import numpy as np
from typing import Optional


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
