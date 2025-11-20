#!/usr/bin/env python3
"""
Test script that mirrors official local.py architecture.

This tests the server/client split before integrating with Textual.
"""

import asyncio
import queue
import time
import sys

import numpy as np
import sounddevice as sd

from assistant.voice_server import start_server_process_process
from assistant.voice import MoshiClient

SAMPLE_RATE = 24000
FRAME_SIZE = 1920


def main():
    print("Starting Moshi test (mirrors local.py architecture)...")
    print("=" * 60)

    # Start server process FIRST (before any async/threading)
    print("Starting Moshi server process...")
    quality = "q4"  # Use q4 for faster loading
    process, client_to_server, server_to_client, status_queue = start_server_process(quality="q4")

    # Monitor status messages
    print("Waiting for server to initialize...")
    while True:
        try:
            msg_type, msg = status_queue.get(timeout=0.1)
            print(f"[SERVER] {msg_type}: {msg}")
            if msg_type == "error":
                print("Server failed to start!")
                process.terminate()
                sys.exit(1)
        except queue.Empty:
            pass

        # Check if server is ready
        try:
            ready = server_to_client.get_nowait()
            if ready == "ready":
                print("Server is ready!")
                break
        except queue.Empty:
            pass

        if not process.is_alive():
            print("Server process died!")
            sys.exit(1)

    # Create client
    print("Creating client...")
    client = MoshiClient(client_to_server, server_to_client)

    # Warmup
    print("Running warmup...")
    client.warmup()
    print("Warmup complete!")

    # Set up callbacks
    text_buffer = []

    def on_text(text):
        text_buffer.append(text)
        print(text, end="", flush=True)

    client.on_text_token = on_text

    # Set up audio I/O
    input_queue = queue.Queue()
    output_queue = client.output_queue

    def on_input(in_data, frames, time_info, status):
        in_data = in_data[:, 0].astype(np.float32)
        client.feed_audio(in_data)

    cnt_output = 0

    def on_output(out_data, frames, time_info, status):
        nonlocal cnt_output
        cnt_output += 1
        try:
            pcm_data = output_queue.get(block=False)
            out_data[:, 0] = pcm_data
        except queue.Empty:
            if cnt_output > 3:
                pass  # Lag indicator
            out_data.fill(0)

    # Create streams
    in_stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=FRAME_SIZE,
        callback=on_input
    )

    out_stream = sd.OutputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        blocksize=FRAME_SIZE,
        callback=on_output
    )

    print("\n" + "=" * 60)
    print("MOSHI READY - Speak into your microphone!")
    print("Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    # Run async loops
    async def run():
        with in_stream, out_stream:
            await client.run_async_loops()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n\nStopping...")
        client.shutdown()
        process.terminate()
        process.join(timeout=2)
        print("Done!")


if __name__ == "__main__":
    main()
