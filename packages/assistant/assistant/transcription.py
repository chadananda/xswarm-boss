"""
User voice transcription using Vosk.
Handles continuous speech recognition for the user's voice input.
"""

import json
import queue
import threading
import logging
from typing import Optional, Callable
from pathlib import Path
import numpy as np

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    raise ImportError("Vosk not installed. Install: pip install vosk")

logger = logging.getLogger(__name__)

class UserTranscriber:
    """
    Continuous speech-to-text for user input using Vosk.
    """

    def __init__(
        self,
        model_path: Path,
        sample_rate: int = 16000,
        on_text: Optional[Callable[[str, bool], None]] = None
    ):
        """
        Initialize user transcriber.

        Args:
            model_path: Path to Vosk model
            sample_rate: Audio sample rate
            on_text: Callback for recognized text (text, is_final)
        """
        self.sample_rate = sample_rate
        self.on_text = on_text
        
        if not model_path.exists():
            raise FileNotFoundError(f"Vosk model not found: {model_path}")

        logger.info(f"Loading Vosk model for transcription from {model_path}...")
        self.model = Model(str(model_path))
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        self.recognizer.SetWords(True)
        
        self.is_active = False
        self._audio_queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start transcription thread"""
        if self.is_active:
            return

        self.is_active = True
        self._thread = threading.Thread(target=self._transcription_loop, daemon=True)
        self._thread.start()
        logger.info("User transcription started")

    def stop(self):
        """Stop transcription"""
        self.is_active = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("User transcription stopped")

    def process_audio(self, audio: np.ndarray):
        """
        Process audio frame.
        
        Args:
            audio: Audio samples at 16kHz (int16 or float32)
        """
        if not self.is_active:
            return

        # Convert to int16 if needed
        if audio.dtype == np.float32 or audio.dtype == np.float64:
            audio = (audio * 32767).astype(np.int16)

        self._audio_queue.put(audio.tobytes())

    def _transcription_loop(self):
        """Background thread for transcription"""
        while self.is_active:
            try:
                audio_data = self._audio_queue.get(timeout=0.1)

                if self.recognizer.AcceptWaveform(audio_data):
                    # Final result
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip()
                    if text and self.on_text:
                        self.on_text(text, True)
                else:
                    # Partial result
                    # We usually don't want to show partials in chat to avoid flickering
                    # But we could if we wanted to support streaming text
                    pass

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Transcription error: {e}")
