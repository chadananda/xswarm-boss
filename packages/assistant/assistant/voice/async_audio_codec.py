"""
Async Audio Codec - Runs rustymimi in separate thread for non-blocking encode/decode.

This replicates the official MOSHI CLI architecture where the audio codec
runs asynchronously, allowing encode/decode operations to overlap with
ML inference on the GPU.

Key Architecture:
- Codec thread: Handles rustymimi encode/decode operations
- Main thread: Runs MLX inference on Metal GPU
- Communication: Thread-safe queues for non-blocking I/O
- Result: Parallel execution instead of serial
"""

import queue
import threading
import time
import numpy as np
from typing import Optional
import rustymimi


def _codec_worker_loop(
    codec: rustymimi.StreamTokenizer,
    encode_requests: queue.Queue,
    decode_requests: queue.Queue,
    encoded_results: queue.Queue,
    decoded_results: queue.Queue,
    shutdown_event: threading.Event
):
    """
    Codec worker that runs in separate thread.

    Handles encode/decode requests asynchronously without blocking
    the main thread that runs MLX inference.

    Args:
        codec: Initialized rustymimi StreamTokenizer
        encode_requests: Queue for incoming encode requests
        decode_requests: Queue for incoming decode requests
        encoded_results: Queue for encoded audio codes
        decoded_results: Queue for decoded audio samples
        shutdown_event: Event to signal worker shutdown
    """
    # Track pending operations
    encode_pending = False
    decode_pending = False

    while not shutdown_event.is_set():
        # Check for encode requests
        try:
            audio = encode_requests.get_nowait()
            codec.encode(audio)
            encode_pending = True
        except queue.Empty:
            pass

        # Poll for encode completion
        if encode_pending:
            codes = codec.get_encoded()
            if codes is not None:
                encoded_results.put(codes)
                encode_pending = False

        # Check for decode requests
        try:
            codes = decode_requests.get_nowait()
            codec.decode(codes)
            decode_pending = True
        except queue.Empty:
            pass

        # Poll for decode completion
        if decode_pending:
            audio = codec.get_decoded()
            if audio is not None:
                decoded_results.put(audio)
                decode_pending = False

        # Small sleep to avoid busy-waiting (but still responsive)
        time.sleep(0.0001)  # 100 microseconds


class AsyncAudioCodec:
    """
    Async wrapper for rustymimi codec that runs in separate thread.

    Provides non-blocking encode/decode operations that can overlap
    with MLX inference, replicating the official MOSHI CLI architecture.

    Example:
        codec = AsyncAudioCodec(mimi_file)

        # Non-blocking encode (returns immediately, processes in background)
        codec.encode_async(audio_frame)

        # While encoding happens, we can run inference on GPU
        # Then decode the result (also non-blocking)
        codec.decode_async(audio_codes)
    """

    def __init__(self, mimi_file: str):
        """
        Initialize async codec with separate worker thread.

        Args:
            mimi_file: Path to Mimi model weights
        """
        self.mimi_file = mimi_file

        # Initialize codec in main thread (must be done before starting worker)
        self._codec = rustymimi.StreamTokenizer(mimi_file)

        # Create communication queues (thread-safe)
        self.encode_requests = queue.Queue()
        self.decode_requests = queue.Queue()
        self.encoded_results = queue.Queue()
        self.decoded_results = queue.Queue()
        self.shutdown_event = threading.Event()

        # Start worker thread
        self.worker = threading.Thread(
            target=_codec_worker_loop,
            args=(
                self._codec,
                self.encode_requests,
                self.decode_requests,
                self.encoded_results,
                self.decoded_results,
                self.shutdown_event
            ),
            daemon=True  # Auto-cleanup on main thread exit
        )
        self.worker.start()

        # Warmup: encode a silent frame to initialize codec
        self._warmup()

    def _warmup(self):
        """
        Full pipeline warmup matching official MOSHI CLI.

        Runs 4 iterations of encode→decode to ensure all Metal kernels
        are compiled and cached before real-time processing begins.
        """
        for i in range(4):
            # Encode silent frame
            silence = np.zeros(1920, dtype=np.float32)
            self.encode_requests.put(silence)

            # Wait for encode result
            while True:
                try:
                    codes = self.encoded_results.get(timeout=0.01)
                    break
                except queue.Empty:
                    continue

            # Skip first decode like official CLI
            if i == 0:
                continue

            # Decode to warmup decode path too
            # Use the encoded codes (shape is (time, codebooks) -> transpose to (codebooks, time))
            # rustymimi expects (8, time_steps) format
            self.decode_requests.put(codes.T if codes.ndim == 2 else codes)

            # Wait for decode result
            while True:
                try:
                    self.decoded_results.get(timeout=0.01)
                    break
                except queue.Empty:
                    continue

    # =========================================================================
    # Non-blocking async methods for pipelined operation
    # =========================================================================

    def encode_async(self, audio: np.ndarray):
        """
        Submit encode request without waiting for result.

        Use try_get_encoded() to poll for the result later.
        This enables pipelining where inference can run while encode happens.

        Args:
            audio: Audio samples (1920 samples at 24kHz for 80ms frame)
        """
        self.encode_requests.put(audio.astype(np.float32))

    def try_get_encoded(self) -> Optional[np.ndarray]:
        """
        Poll for encoded result (non-blocking).

        Returns:
            Encoded audio codes if ready, None if still processing
        """
        try:
            return self.encoded_results.get_nowait()
        except queue.Empty:
            return None

    def decode_async(self, codes: np.ndarray):
        """
        Submit decode request without waiting for result.

        Use try_get_decoded() to poll for the result later.
        This enables pipelining where next encode can start while decode happens.

        Args:
            codes: Audio codes from model
        """
        self.decode_requests.put(codes)

    def try_get_decoded(self) -> Optional[np.ndarray]:
        """
        Poll for decoded result (non-blocking).

        Returns:
            Decoded audio samples if ready, None if still processing
        """
        try:
            return self.decoded_results.get_nowait()
        except queue.Empty:
            return None

    def encode(self, audio: np.ndarray) -> np.ndarray:
        """
        Encode audio to codes (synchronous but non-blocking via worker process).

        This sends the encode request to the worker process and waits for result.
        The actual encoding happens in parallel in the separate process.

        Args:
            audio: Audio samples (1920 samples at 24kHz for 80ms frame)

        Returns:
            Encoded audio codes
        """
        # Send request to worker (non-blocking)
        self.encode_requests.put(audio.astype(np.float32))

        # Wait for result (blocking, but worker does actual work in parallel)
        return self.encoded_results.get()

    def decode(self, codes: np.ndarray) -> np.ndarray:
        """
        Decode codes to audio (synchronous but non-blocking via worker process).

        This sends the decode request to the worker process and waits for result.
        The actual decoding happens in parallel in the separate process.

        Args:
            codes: Audio codes from model

        Returns:
            Decoded audio samples
        """
        # Send request to worker (non-blocking)
        self.decode_requests.put(codes)

        # Wait for result (blocking, but worker does actual work in parallel)
        return self.decoded_results.get()

    def shutdown(self):
        """Shutdown codec worker process."""
        self.shutdown_event.set()
        self.worker.join(timeout=2.0)
        if self.worker.is_alive():
            self.worker.terminate()
            self.worker.join()

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            self.shutdown()
        except:
            pass
