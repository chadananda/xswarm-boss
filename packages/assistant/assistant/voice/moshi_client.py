# Copyright (c) Kyutai, all rights reserved.
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
#
# Adapted from official moshi_mlx local.py for use with Textual TUI.

"""
Moshi Client - Handles audio I/O and codec operations.

This mirrors the official local.py client that handles:
- Audio input/output via sounddevice
- Encoding audio to codes via rustymimi
- Decoding audio tokens back to PCM
"""

import asyncio
import queue
import time
from pathlib import Path
from typing import Optional, Callable

import numpy as np
import huggingface_hub
import rustymimi

SAMPLE_RATE = 24000
FRAME_SIZE = 1920  # 80ms at 24kHz


def hf_hub_download(repo, path: str) -> str:
    """Download file from HuggingFace hub."""
    return huggingface_hub.hf_hub_download(repo, path)


class MoshiClient:
    """
    Client that handles audio codec and communicates with server process.

    This mirrors the client from local.py but is designed for integration
    with Textual rather than standalone operation.
    """

    def __init__(
        self,
        client_to_server,  # multiprocessing.Queue
        server_to_client,  # multiprocessing.Queue
        hf_repo: str = "kyutai/moshiko-mlx-bf16",
        mimi_file: Optional[str] = None,
    ):
        """
        Initialize Moshi client.

        Args:
            client_to_server: Queue to send encoded audio to server
            server_to_client: Queue to receive audio tokens from server
            hf_repo: HuggingFace repo for mimi weights
            mimi_file: Optional path to mimi weights (downloads if None)
        """
        self.client_to_server = client_to_server
        self.server_to_client = server_to_client

        # Download mimi weights if needed
        if mimi_file is None:
            mimi_file = hf_hub_download(hf_repo, "tokenizer-e351c8d8-checkpoint125.safetensors")

        # Initialize audio tokenizer
        self.audio_tokenizer = rustymimi.StreamTokenizer(mimi_file)

        # Queues for internal async processing
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        # Callbacks for audio data
        self.on_output_audio: Optional[Callable[[np.ndarray], None]] = None
        self.on_text_token: Optional[Callable[[str], None]] = None

        # State
        self._running = False

    def warmup(self):
        """
        Full pipeline warmup matching official MOSHI CLI.

        Runs 4 iterations of encode→decode to ensure all Metal kernels
        are compiled and cached before real-time processing begins.
        """
        for i in range(4):
            # Encode silent frame
            pcm_data = np.zeros(FRAME_SIZE, dtype=np.float32)
            self.audio_tokenizer.encode(pcm_data)

            # Wait for encode
            while True:
                time.sleep(0.01)
                data = self.audio_tokenizer.get_encoded()
                if data is not None:
                    break

            # Send to server
            self.client_to_server.put_nowait(data)

            if i == 0:
                continue

            # Get from server and decode
            result = self.server_to_client.get()
            if result[0] == "audio":
                _, audio_tokens, _ = result
                self.audio_tokenizer.decode(audio_tokens)

                # Wait for decode
                while True:
                    time.sleep(0.01)
                    data = self.audio_tokenizer.get_decoded()
                    if data is not None:
                        break

    def feed_audio(self, audio: np.ndarray):
        """
        Feed audio input for processing.

        Args:
            audio: PCM audio data (1920 samples at 24kHz)
        """
        self.input_queue.put_nowait(audio.astype(np.float32))

    def get_output_audio(self) -> Optional[np.ndarray]:
        """
        Get decoded output audio if available.

        Returns:
            PCM audio data or None if not available
        """
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    async def run_async_loops(self):
        """
        Run the async processing loops.

        This mirrors the asyncio.gather() in local.py's client.
        """
        self._running = True

        async def send_loop():
            """Take PCM from input_queue → encode."""
            while self._running:
                await asyncio.sleep(0.001)
                try:
                    pcm_data = self.input_queue.get(block=False)
                    self.audio_tokenizer.encode(pcm_data)
                except queue.Empty:
                    continue

        async def send_loop2():
            """Get encoded data → send to server."""
            while self._running:
                data = self.audio_tokenizer.get_encoded()
                if data is None:
                    await asyncio.sleep(0.001)
                    continue
                self.client_to_server.put_nowait(data)

        async def recv_loop2():
            """Get audio tokens from server → decode."""
            while self._running:
                try:
                    result = self.server_to_client.get(block=False)
                except queue.Empty:
                    await asyncio.sleep(0.001)
                    continue

                msg_type, audio_tokens, text_piece = result

                # Handle text
                if text_piece and self.on_text_token:
                    self.on_text_token(text_piece)

                # Decode audio
                if audio_tokens is not None:
                    self.audio_tokenizer.decode(audio_tokens)

        async def recv_loop():
            """Get decoded PCM → output_queue."""
            while self._running:
                data = self.audio_tokenizer.get_decoded()
                if data is None:
                    await asyncio.sleep(0.001)
                    continue

                self.output_queue.put_nowait(data)

                if self.on_output_audio:
                    self.on_output_audio(data)

        await asyncio.gather(send_loop(), send_loop2(), recv_loop(), recv_loop2())

    def stop(self):
        """Stop the async loops."""
        self._running = False

    def shutdown(self):
        """Shutdown and cleanup."""
        self.stop()
        # Send shutdown signal to server
        self.client_to_server.put(None)
