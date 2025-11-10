"""
Wake word detection using Vosk.
Offline, lightweight, deterministic speech recognition.
"""

import json
import queue
import threading
from typing import Optional, Callable
from pathlib import Path
import numpy as np

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    raise ImportError("Vosk not installed. Install: pip install vosk")


class WakeWordDetector:
    """
    Offline wake word detection using Vosk.

    Vosk advantages:
    - Fully offline (no API calls)
    - Lightweight (~50MB model)
    - Deterministic (no false positives from AI hallucinations)
    - Low latency (<100ms)
    - No GPU required
    """

    def __init__(
        self,
        model_path: Path,
        wake_word: str = "jarvis",
        sample_rate: int = 16000,
        sensitivity: float = 0.8
    ):
        """
        Initialize wake word detector.

        Args:
            model_path: Path to Vosk model (e.g., vosk-model-small-en-us-0.15)
            wake_word: Word/phrase to detect (lowercase)
            sample_rate: Audio sample rate (Vosk uses 16kHz)
            sensitivity: Detection sensitivity 0.0-1.0 (higher = more sensitive)
        """
        self.wake_word = wake_word.lower().strip()
        self.sample_rate = sample_rate
        self.sensitivity = sensitivity

        # Load Vosk model
        if not model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found: {model_path}\n"
                f"Download: https://alphacephei.com/vosk/models"
            )

        print(f"Loading Vosk model from {model_path}...")
        self.model = Model(str(model_path))
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        self.recognizer.SetWords(True)  # Get word-level confidence
        print(f"Vosk model loaded. Listening for: '{self.wake_word}'")

        # Detection state
        self.is_active = False
        self.detection_callback: Optional[Callable] = None
        self._audio_queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    def start(self, callback: Optional[Callable] = None):
        """
        Start wake word detection in background thread.

        Args:
            callback: Function to call when wake word detected
        """
        if self.is_active:
            return

        self.is_active = True
        self.detection_callback = callback

        # Start detection thread
        self._thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._thread.start()

        print(f"Wake word detection started: '{self.wake_word}'")

    def stop(self):
        """Stop wake word detection"""
        self.is_active = False
        if self._thread:
            self._thread.join(timeout=1.0)
        print("Wake word detection stopped")

    def process_audio(self, audio: np.ndarray):
        """
        Process audio frame for wake word detection.

        Args:
            audio: Audio samples at 16kHz (int16 or float32)
        """
        if not self.is_active:
            return

        # Convert to int16 if needed
        if audio.dtype == np.float32 or audio.dtype == np.float64:
            audio = (audio * 32767).astype(np.int16)

        # Queue for processing
        self._audio_queue.put(audio.tobytes())

    def _detection_loop(self):
        """Background thread for wake word detection"""
        while self.is_active:
            try:
                # Get audio from queue (blocking with timeout)
                audio_data = self._audio_queue.get(timeout=0.1)

                # Process with Vosk
                if self.recognizer.AcceptWaveform(audio_data):
                    # Final result (end of utterance)
                    result = json.loads(self.recognizer.Result())
                    self._check_wake_word(result)
                else:
                    # Partial result (still speaking)
                    result = json.loads(self.recognizer.PartialResult())
                    self._check_wake_word(result, partial=True)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Wake word detection error: {e}")

    def _check_wake_word(self, result: dict, partial: bool = False):
        """
        Check if wake word was detected in result.

        Args:
            result: Vosk recognition result
            partial: Whether this is a partial result
        """
        # Get text from result
        text = result.get("partial", "") if partial else result.get("text", "")
        text = text.lower().strip()

        if not text:
            return

        # Check for wake word
        if self._is_wake_word_present(text):
            # Get confidence if available
            confidence = self._get_confidence(result)

            # Check sensitivity threshold
            if confidence >= self.sensitivity:
                print(f"Wake word detected: '{text}' (confidence: {confidence:.2f})")

                # Call callback
                if self.detection_callback:
                    try:
                        self.detection_callback()
                    except Exception as e:
                        print(f"Wake word callback error: {e}")

    def _is_wake_word_present(self, text: str) -> bool:
        """Check if wake word is in recognized text"""
        # Exact match
        if text == self.wake_word:
            return True

        # Wake word as part of phrase
        words = text.split()
        if self.wake_word in words:
            return True

        # Multi-word wake word
        if " " in self.wake_word and self.wake_word in text:
            return True

        return False

    def _get_confidence(self, result: dict) -> float:
        """
        Get confidence score from Vosk result.

        Vosk provides word-level confidence scores.
        We use the average confidence of wake word.
        """
        # Try to get word-level results
        if "result" in result:
            words = result["result"]
            if isinstance(words, list):
                # Find wake word in results
                wake_word_parts = self.wake_word.split()
                confidences = []

                for word_info in words:
                    if isinstance(word_info, dict):
                        word = word_info.get("word", "").lower()
                        conf = word_info.get("conf", 1.0)

                        if word in wake_word_parts:
                            confidences.append(conf)

                if confidences:
                    return sum(confidences) / len(confidences)

        # Default high confidence if no word-level data
        return 1.0

    def set_wake_word(self, wake_word: str):
        """
        Change wake word at runtime.
        Useful for switching personas.

        Args:
            wake_word: New wake word to detect
        """
        old_word = self.wake_word
        self.wake_word = wake_word.lower().strip()
        print(f"Wake word changed: '{old_word}' -> '{self.wake_word}'")

    def reset(self):
        """Reset recognizer state"""
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.recognizer.SetWords(True)


class WakeWordDetectorWithVAD:
    """
    Wake word detector with integrated Voice Activity Detection.
    Only processes audio when speech is detected (more efficient).
    """

    def __init__(
        self,
        model_path: Path,
        wake_word: str = "jarvis",
        sample_rate: int = 16000,
        sensitivity: float = 0.8,
        vad_threshold: float = 0.02
    ):
        from ..voice.vad import VoiceActivityDetector

        self.detector = WakeWordDetector(
            model_path=model_path,
            wake_word=wake_word,
            sample_rate=sample_rate,
            sensitivity=sensitivity
        )

        self.vad = VoiceActivityDetector(threshold=vad_threshold)
        self._speech_buffer = []

    def start(self, callback: Optional[Callable] = None):
        """Start detection"""
        self.detector.start(callback)

    def stop(self):
        """Stop detection"""
        self.detector.stop()

    def process_audio(self, audio: np.ndarray):
        """
        Process audio with VAD filtering.
        Only sends audio to detector when speech is detected.
        """
        # Check for speech
        is_speech = self.vad.process_frame(audio)

        if is_speech:
            # Add to buffer
            self._speech_buffer.append(audio)

            # Process with detector
            self.detector.process_audio(audio)
        else:
            # End of speech - flush buffer
            if self._speech_buffer:
                self._speech_buffer = []
                self.detector.reset()

    def set_wake_word(self, wake_word: str):
        """Change wake word"""
        self.detector.set_wake_word(wake_word)
