"""
Test for MoshiClient Duplex Logic.
"""
import pytest
import asyncio
import queue
import numpy as np
from unittest.mock import MagicMock, patch
import sys

# Mock modules
sys.modules['rustymimi'] = MagicMock()
sys.modules['sentencepiece'] = MagicMock()

from assistant.voice import MoshiClient

@pytest.mark.asyncio
async def test_moshi_client_duplex_flow():
    """
    Test the MoshiClient async loops:
    1. Feed audio -> Encoded -> Client Queue
    2. Server Queue -> Decoded -> Output Callback
    """
    # Mocks
    c2s = queue.Queue()
    s2c = queue.Queue()
    
    with patch('assistant.voice.hf_hub_download', return_value="dummy_path"):
        with patch('rustymimi.StreamTokenizer') as MockTokenizer:
            mock_tok = MockTokenizer.return_value
            # Mock encoding: return dummy codes once, then None forever
            # We use a generator to avoid running out of items
            def encoded_generator():
                yield np.zeros((8, 1), dtype=np.int32)
                while True:
                    yield None
            mock_tok.get_encoded.side_effect = encoded_generator()
            
            # Mock decoding: return dummy audio once, then None forever
            def decoded_generator():
                yield np.zeros(1920, dtype=np.float32)
                while True:
                    yield None
            mock_tok.get_decoded.side_effect = decoded_generator()
            
            print("DEBUG: Test starting client...")
            
            client = MoshiClient(c2s, s2c)
            
            # Setup callbacks
            received_audio = []
            received_text = []
            
            def on_audio(audio):
                received_audio.append(audio)
                
            def on_text(text):
                received_text.append(text)
                
            client.on_output_audio = on_audio
            client.on_text_token = on_text
            
            # Start loops
            task = asyncio.create_task(client.run_async_loops())
            
            # 1. Test Sending (Mic -> Server)
            # Feed audio
            input_audio = np.zeros(1920, dtype=np.float32)
            client.feed_audio(input_audio)
            
            # Wait for processing
            await asyncio.sleep(0.1)
            
            # Check if data was put in c2s queue
            if task.done():
                # Task crashed?
                try:
                    await task
                except Exception as e:
                    pytest.fail(f"MoshiClient task failed: {e}")

            assert not c2s.empty(), "Client did not send encoded audio"
            try:
                data = c2s.get_nowait()
            except queue.Empty:
                pytest.fail("Queue empty despite check")
                
            assert isinstance(data, np.ndarray)
            assert data.shape == (8, 1)
            
            # 2. Test Receiving (Server -> Speaker)
            # Simulate server sending "ready" (should be consumed by wait_for_ready, but here we skip that)
            # Simulate server sending audio/text
            # Format: (msg_type, audio_tokens, text_piece)
            
            # Send text
            s2c.put(("text", None, "Hello"))
            await asyncio.sleep(0.1)
            assert "Hello" in received_text
            
            # Send audio
            dummy_tokens = np.zeros((1, 8), dtype=np.int32)
            s2c.put(("audio", dummy_tokens, None))
            await asyncio.sleep(0.1)
            assert len(received_audio) > 0
            assert received_audio[0].shape == (1920,)
            
            # Stop
            client.stop()
            await task
