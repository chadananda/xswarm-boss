import multiprocessing
import queue
import time
import numpy as np
import sys
import os
from pathlib import Path

# Add package root to path
sys.path.append(str(Path(__file__).parent.parent / "packages/assistant"))

# MOCK DEPENDENCIES for logic testing
from unittest.mock import MagicMock
import types

# Mock mlx
mock_mlx = MagicMock()
mock_mlx.array = np.array # Use numpy for array operations in logic
sys.modules["mlx"] = mock_mlx
sys.modules["mlx.core"] = mock_mlx
sys.modules["mlx.nn"] = mock_mlx

# Mock moshi_mlx
mock_moshi = MagicMock()
sys.modules["moshi_mlx"] = mock_moshi
sys.modules["moshi_mlx.models"] = mock_moshi.models
sys.modules["moshi_mlx.utils"] = mock_moshi.utils

# Mock huggingface_hub
mock_hf = MagicMock()
mock_hf.hf_hub_download.return_value = "/tmp/dummy_model.safetensors"
sys.modules["huggingface_hub"] = mock_hf

# Mock sentencepiece
mock_sp = MagicMock()
mock_tokenizer = MagicMock()
mock_tokenizer.decode.return_value = " hello"
mock_sp.SentencePieceProcessor.return_value = mock_tokenizer
sys.modules["sentencepiece"] = mock_sp

# Configure mocks
mock_gen = MagicMock()
mock_moshi.models.LmGen.return_value = mock_gen
# step returns a tensor with item() method
mock_token = MagicMock()
mock_token.item.return_value = 100 # Return a valid token ID
mock_gen.step.return_value = [mock_token] 
mock_gen.last_audio_tokens.return_value = np.zeros((8, 1), dtype=np.uint32) # Return silence
mock_gen.max_steps = 50000

try:
    from assistant.voice_server import server_process
except ImportError as e:
    print(f"❌ Could not import server_process: {e}")
    sys.exit(1)

def test_duplex_server():
    print("🚀 Starting E2E Duplex Voice Test...")

    # Setup queues
    client_to_server = queue.Queue()
    server_to_client = queue.Queue()
    status_queue = queue.Queue()

    # Start server process (using Thread for testing with Mocks)
    import threading
    process = threading.Thread(
        target=server_process,
        args=(client_to_server, server_to_client, status_queue, "kyutai/moshiko-mlx-bf16", 4, 1000)
    )
    process.daemon = True # Ensure it dies if main thread dies
    process.start()
    print(f"✅ Server thread started")

    try:
        # Wait for ready signal
        print("⏳ Waiting for server ready...")
        try:
            msg = server_to_client.get(timeout=30)
            if msg == "ready":
                print("✅ Server is ready!")
            else:
                print(f"❌ Unexpected initial message: {msg}")
                return
        except queue.Empty:
            print("❌ Timeout waiting for server ready")
            return

        # 1. Test Duplex Audio
        print("\n🧪 Testing Duplex Audio Stream...")
        # Send 1 second of silence (simulated audio codes)
        # Moshi expects (1, 8) codes. 
        # We'll send 50 frames (approx 1s at 24kHz/1920 frame size? No, frame rate is 12.5Hz -> 80ms per frame)
        # 1s = 12.5 frames. Let's send 20 frames.
        
        silence_frame = np.zeros((1, 8), dtype=np.int32) + 1685 # Silence code
        
        start_time = time.time()
        received_audio_packets = 0
        received_text_packets = 0
        
        for i in range(20):
            client_to_server.put(silence_frame)
            time.sleep(0.05) # Send at approx 20Hz
            
            # Check for output (non-blocking)
            try:
                while True:
                    msg = server_to_client.get_nowait()
                    if isinstance(msg, tuple):
                        type_, data, text = msg
                        if type_ == "audio":
                            received_audio_packets += 1
                        elif type_ == "text":
                            received_text_packets += 1
                            print(f"🤖 Moshi: {text}")
            except queue.Empty:
                pass
                
        print(f"📊 Sent 20 frames, Received {received_audio_packets} audio packets")
        
        if received_audio_packets > 0:
            print("✅ Duplex audio verified!")
        else:
            print("❌ No audio received back!")

        # 2. Test Context Injection
        print("\n🧪 Testing Context Injection...")
        injection_text = "... just remembered: The user loves sci-fi."
        print(f"💉 Injecting: '{injection_text}'")
        
        # Send injection message
        # Note: We need to implement this in voice_server.py first!
        # Current implementation might not handle it yet.
        client_to_server.put(("inject", injection_text))
        
        # Continue sending audio to keep loop alive
        for i in range(50):
            client_to_server.put(silence_frame)
            time.sleep(0.05)
            
            try:
                while True:
                    msg = server_to_client.get_nowait()
                    if isinstance(msg, tuple):
                        type_, data, text = msg
                        if type_ == "text":
                            print(f"🤖 Moshi: {text}")
                            
            except queue.Empty:
                pass

        # Verify injection by checking mock calls
        print("\n🔍 Verifying injection calls...")
        calls = mock_gen.step.call_args_list
        # Check for calls with >1 argument (audio, text)
        injection_calls = [call for call in calls if len(call.args) > 1]
        
        if injection_calls:
            print(f"✅ Injection verified: gen.step called {len(injection_calls)} times with text tokens")
        else:
            print("❌ Injection failed: gen.step never called with text tokens")
            # Print last few calls for debugging
            if calls:
                print(f"Last call args: {calls[-1].args}")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted")
    finally:
        print("\n🛑 Stopping server...")
        client_to_server.put("stop")
        process.join(timeout=5)
        print("✅ Done")

if __name__ == "__main__":
    test_duplex_server()
