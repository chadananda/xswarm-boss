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
        wake_word: str | list[str] = "jarvis",
        sample_rate: int = 16000,
        sensitivity: float = 0.8
    ):
        """
        Initialize wake word detector.

        Args:
            model_path: Path to Vosk model (e.g., vosk-model-small-en-us-0.15)
            wake_word: Word/phrase to detect, or list of multiple wake words
            sample_rate: Audio sample rate (Vosk uses 16kHz)
            sensitivity: Detection sensitivity 0.0-1.0 (higher = more sensitive)
        """
        # Support both single string and list of wake words
        if isinstance(wake_word, str):
            self.wake_words = [wake_word.lower().strip()]
        else:
            self.wake_words = [w.lower().strip() for w in wake_word]

        # Keep backward compatibility with .wake_word attribute
        self.wake_word = self.wake_words[0] if self.wake_words else "jarvis"

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

        # Show all wake words
        if len(self.wake_words) == 1:
            print(f"Vosk model loaded. Listening for: '{self.wake_words[0]}'")
        else:
            wake_words_str = "', '".join(self.wake_words)
            print(f"Vosk model loaded. Listening for: '{wake_words_str}'")

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

        if len(self.wake_words) == 1:
            print(f"Wake word detection started: '{self.wake_words[0]}'")
        else:
            wake_words_str = "', '".join(self.wake_words)
            print(f"Wake word detection started for: '{wake_words_str}'")

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

        # Check for wake word and identify which one
        detected_word = self._get_detected_wake_word(text)
        if detected_word:
            # Get confidence if available
            confidence = self._get_confidence(result)

            # Check sensitivity threshold
            if confidence >= self.sensitivity:
                print(f"Wake word detected: '{detected_word}' in '{text}' (confidence: {confidence:.2f})")

                # Call callback with detected wake word
                if self.detection_callback:
                    try:
                        self.detection_callback(detected_word)
                    except Exception as e:
                        print(f"Wake word callback error: {e}")

    def _get_detected_wake_word(self, text: str) -> Optional[str]:
        """
        Get the specific wake word that was detected in text.

        Returns the wake word that was found, or None if no wake word detected.
        """
        # Check each wake word
        for wake_word in self.wake_words:
            # Exact match
            if text == wake_word:
                return wake_word

            # Wake word as part of phrase
            words = text.split()
            if wake_word in words:
                return wake_word

            # Multi-word wake word
            if " " in wake_word and wake_word in text:
                return wake_word

        return None

    def _is_wake_word_present(self, text: str) -> bool:
        """Check if any wake word is in recognized text"""
        return self._get_detected_wake_word(text) is not None

    def _get_confidence(self, result: dict) -> float:
        """
        Get confidence score from Vosk result.

        Vosk provides word-level confidence scores.
        We use the average confidence of detected wake word.
        """
        # Try to get word-level results
        if "result" in result:
            words = result["result"]
            if isinstance(words, list):
                # Check all wake words and find the best match
                all_confidences = []

                for wake_word in self.wake_words:
                    wake_word_parts = wake_word.split()
                    confidences = []

                    for word_info in words:
                        if isinstance(word_info, dict):
                            word = word_info.get("word", "").lower()
                            conf = word_info.get("conf", 1.0)

                            if word in wake_word_parts:
                                confidences.append(conf)

                    if confidences:
                        avg_conf = sum(confidences) / len(confidences)
                        all_confidences.append(avg_conf)

                if all_confidences:
                    # Return best confidence score
                    return max(all_confidences)

        # Default high confidence if no word-level data
        return 1.0

    def set_wake_word(self, wake_word: str | list[str]):
        """
        Change wake word(s) at runtime.
        Useful for switching personas.

        Args:
            wake_word: New wake word(s) to detect (string or list)
        """
        old_words = self.wake_words.copy()

        # Update wake words list
        if isinstance(wake_word, str):
            self.wake_words = [wake_word.lower().strip()]
        else:
            self.wake_words = [w.lower().strip() for w in wake_word]

        # Update backward compatibility attribute
        self.wake_word = self.wake_words[0] if self.wake_words else "jarvis"

        # Log change
        if len(old_words) == 1 and len(self.wake_words) == 1:
            print(f"Wake word changed: '{old_words[0]}' -> '{self.wake_words[0]}'")
        else:
            old_str = "', '".join(old_words)
            new_str = "', '".join(self.wake_words)
            print(f"Wake words changed: ['{old_str}'] -> ['{new_str}']")

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
        wake_word: str | list[str] = "jarvis",
        sample_rate: int = 16000,
        sensitivity: float = 0.8,
        vad_threshold: float = 0.02
    ):
        from .audio import VoiceActivityDetector

        self.detector = WakeWordDetector(
            model_path=model_path,
            wake_word=wake_word,  # Pass through - supports both str and list
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

    def set_wake_word(self, wake_word: str | list[str]):
        """Change wake word(s)"""
        self.detector.set_wake_word(wake_word)
