"""
Audio I/O manager using sounddevice.
Replaces Rust CPAL implementation with Python cross-platform audio.
"""

import sounddevice as sd
import numpy as np
from typing import Callable, Optional
from queue import Queue
import threading


class AudioIO:
    """
    Audio I/O manager using sounddevice.

    Provides real-time audio input/output with frame-based processing.
    Uses queues for thread-safe communication between audio callbacks
    and the main application.
    """

    def __init__(
        self,
        sample_rate: int = 24000,
        frame_size: int = 1920,
        channels: int = 1
    ):
        """
        Initialize audio I/O.

        Args:
            sample_rate: Audio sample rate in Hz (default: 24kHz for MOSHI)
            frame_size: Samples per frame (default: 1920 = 80ms at 24kHz)
            channels: Number of audio channels (default: 1 = mono)
        """
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.channels = channels

        self.input_queue: Queue = Queue()
        self.output_queue: Queue = Queue()

        self.input_stream: Optional[sd.InputStream] = None
        self.output_stream: Optional[sd.OutputStream] = None

    def start_input(self, callback: Optional[Callable] = None):
        """
        Start audio input stream.

        Args:
            callback: Optional callback function called for each frame
                     Signature: callback(audio: np.ndarray) -> None
        """

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio input status: {status}")

            try:
                # Copy audio data and ensure it's contiguous
                audio = np.ascontiguousarray(indata[:, 0], dtype=np.float32)
                self.input_queue.put(audio)

                if callback:
                    try:
                        callback(audio)
                    except Exception as e:
                        print(f"Audio callback error: {e}")
            except Exception as e:
                print(f"Audio input error: {e}")

        self.input_stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.frame_size,
            callback=audio_callback
        )
        self.input_stream.start()
        print(f"Audio input started: {self.sample_rate}Hz, {self.frame_size} samples/frame")

    def start_output(self):
        """
        Start audio output stream.

        Audio is queued for playback using play_audio() method.
        """

        def audio_callback(outdata, frames, time, status):
            if status:
                print(f"Audio output status: {status}")

            try:
                audio = self.output_queue.get_nowait()
                # Ensure audio is float32
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)

                # Reshape to (frames, channels)
                if audio.shape[0] < frames:
                    # Pad with zeros if needed
                    audio = np.pad(audio, (0, frames - audio.shape[0]))

                # Ensure correct shape and copy to output buffer
                try:
                    outdata[:] = audio[:frames].reshape(-1, 1)
                except ValueError as e:
                    # If reshape fails, fill with silence to avoid crash
                    print(f"Audio reshape error: {e}, shape={audio.shape}, frames={frames}")
                    outdata.fill(0)
            except Exception as e:
                # Silence if no audio available or other error
                outdata.fill(0)

        self.output_stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.frame_size,
            callback=audio_callback
        )
        self.output_stream.start()
        print(f"Audio output started: {self.sample_rate}Hz")

    def play_audio(self, audio: np.ndarray):
        """
        Queue audio for playback.

        Args:
            audio: Audio samples to play (1D NumPy array)
        """
        if len(audio) == 0:
            return

        # Ensure audio is float32 and contiguous
        audio = np.asarray(audio, dtype=np.float32)
        if not audio.flags['C_CONTIGUOUS']:
            audio = np.ascontiguousarray(audio)

        # Split audio into frame_size chunks for proper streaming
        num_frames = int(np.ceil(len(audio) / self.frame_size))
        for i in range(num_frames):
            start = i * self.frame_size
            end = min((i + 1) * self.frame_size, len(audio))
            chunk = audio[start:end].copy()  # Make a copy to avoid reference issues
            self.output_queue.put(chunk)

    def read_frame(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """
        Read audio frame from input queue.

        Args:
            timeout: Max time to wait for frame (seconds)

        Returns:
            Audio frame or None if timeout
        """
        try:
            return self.input_queue.get(timeout=timeout)
        except:
            return None

    def stop(self):
        """Stop all audio streams."""
        if self.input_stream:
            self.input_stream.stop()
            self.input_stream.close()
        if self.output_stream:
            self.output_stream.stop()
            self.output_stream.close()
        print("Audio I/O stopped")
