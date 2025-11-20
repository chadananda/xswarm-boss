"""
Integration Test for Voice Server Process and Proxy.
"""
import pytest
import multiprocessing
import numpy as np
import time
from unittest.mock import MagicMock, patch
import sys

# We allow real MLX imports now, but we still mock hf_hub_download to avoid 15GB downloads
# and models.Lm to avoid 7GB RAM usage during test.

# Mock the heavy model parts but keep the process logic
class MockLm:
    def __init__(self, config):
        pass
    def set_dtype(self, dtype):
        pass
    def load_weights(self, file, strict=True):
        pass
    def warmup(self):
        pass

class MockLmGen:
    def __init__(self, model, max_steps, **kwargs):
        self.step_count = 0
        
    def step(self, audio_codes):
        # Return a dummy text token (0) and dummy audio tokens
        self.step_count += 1
        return (MagicMock(item=lambda: 0), None)
        
    def last_audio_tokens(self):
        # Return 8 audio tokens (one frame)
        return [[0]*8]

# Patch modules
sys.modules['moshi_mlx'] = MagicMock()
sys.modules['moshi_mlx.models'] = MagicMock()
sys.modules['moshi_mlx.models'].Lm = MockLm
sys.modules['moshi_mlx.models'].LmGen = MockLmGen
sys.modules['moshi_mlx.models'].config_v0_1 = MagicMock()
sys.modules['moshi_mlx.utils'] = MagicMock()
sys.modules['moshi_mlx.utils'].Sampler = MagicMock()

from assistant.voice_server import server_process
from assistant.voice import MoshiBridgeProxy

@pytest.mark.asyncio
async def test_voice_server_integration():
    """
    Test the full loop:
    MoshiBridgeProxy -> Queue -> Server Process -> Queue -> MoshiBridgeProxy
    """
    # Create queues
    c2s = multiprocessing.Queue()
    s2c = multiprocessing.Queue()
    status = multiprocessing.Queue()
    
    # Start server process in a separate thread/process
    # We use a thread here to share the mocks easily, 
    # but in real life it's a process.
    # Since server_process loops forever, we need to run it in a way we can stop.
    
    import threading
    def run_server():
        # Mock hf_hub_download inside the thread
        with patch('assistant.voice_server.hf_hub_download', return_value="dummy_path"):
            with patch('sentencepiece.SentencePieceProcessor'):
                server_process(c2s, s2c, status, "dummy_repo", 4, max_steps=100)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for ready signal
    # The server sends "ready" to s2c queue
    # But first it sends log messages to status queue
    
    # Wait for ready
    ready = False
    for _ in range(50): # 5 seconds timeout
        if not s2c.empty():
            msg = s2c.get()
            if msg == "ready":
                ready = True
                break
        time.sleep(0.1)
        
    assert ready, "Server did not start in time"
    
    # Initialize Proxy
    # Mock hf_hub_download for proxy too
    with patch('assistant.voice.hf_hub_download', return_value="dummy_path"):
        with patch('rustymimi.StreamTokenizer') as MockTokenizer:
            # Mock tokenizer to return dummy codes
            mock_tok = MockTokenizer.return_value
            mock_tok.get_encoded.side_effect = [np.zeros((8, 1)), None] * 100 # Return codes then None
            mock_tok.get_decoded.return_value = np.zeros(1920)
            
            with patch('sentencepiece.SentencePieceProcessor'):
                proxy = MoshiBridgeProxy(c2s, s2c, status)
                
                # Test generate_response
                user_audio = np.zeros(1920, dtype=np.float32)
                
                # We need to run this in a way that doesn't hang forever if server crashes
                # But MoshiBridgeProxy.generate_response blocks.
                # So we'll just trust that if we fixed the mocks, it works.
                # But let's check status queue first
                while not status.empty():
                    msg = status.get()
                    if msg[0] == "error":
                        pytest.fail(f"Server error: {msg[1]}")

                audio, text = proxy.generate_response(user_audio, max_frames=2)
                
                assert isinstance(audio, np.ndarray)
                assert len(audio) > 0
                
    # Stop server
    c2s.put(None)
    server_thread.join(timeout=1)
