import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import queue
import threading
import time
import numpy as np

# Add package path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../packages/assistant')))

# Mock dependencies BEFORE importing voice_server
sys.modules["moshi_mlx"] = MagicMock()
sys.modules["moshi_mlx.models"] = MagicMock()
sys.modules["moshi_mlx.utils"] = MagicMock()
sys.modules["rustymimi"] = MagicMock()
sys.modules["mlx"] = MagicMock()
sys.modules["mlx.core"] = MagicMock()
sys.modules["mlx.nn"] = MagicMock()
sys.modules["sentencepiece"] = MagicMock()
sys.modules["huggingface_hub"] = MagicMock()
sys.modules["assistant.ai_client"] = MagicMock()

# Mock mlx.core.zeros to return a mock object that supports indexing
mock_mx_array = MagicMock()
sys.modules["mlx.core"].zeros.return_value = mock_mx_array
sys.modules["mlx.core"].array.side_effect = lambda x: x # Pass through

import assistant.voice_server as vs
from assistant.subconscious import SubconsciousBridge

class TestVoiceServerLogic(unittest.TestCase):
    def setUp(self):
        self.c2s = queue.Queue()
        self.s2c = queue.Queue()
        self.mock_gen = MagicMock()
        self.mock_gen.step_idx = 0
        self.mock_gen.max_steps = 100
        self.mock_gen.gen_sequence = MagicMock()
        
        self.mock_text_tokenizer = MagicMock()
        self.mock_text_tokenizer.encode.return_value = [1, 2, 3] # Dummy tokens
        
        # Configure the mocks
        # Ensure we are modifying the same mock object that voice_server imported
        import assistant.voice_server as vs_module
        vs_module.models.LmGen.return_value = self.mock_gen
        vs_module.sentencepiece.SentencePieceProcessor.return_value = self.mock_text_tokenizer
        
        # Verify mock setup
        print(f"DEBUG: LmGen() returns {vs_module.models.LmGen()}")
        print(f"DEBUG: step_idx = {vs_module.models.LmGen().step_idx}")
        print(f"DEBUG: SPProcessor() returns {vs_module.sentencepiece.SentencePieceProcessor()}")
        
        # Patch internal functions
        self.patches = [
            # patch('assistant.voice_server.load_model'), # Does not exist
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_injection_logic(self):
        """Test that 'inject' message triggers token forcing and stepping."""
        print("\nTesting Injection Logic...")
        
        # Setup input: Inject message then Stop
        self.c2s.put(("inject", "Hello World"))
        self.c2s.put("stop")
        
        # Run server
        # We mock mx.load and mx.random.uniform to avoid MLX calls
        self.status_q = queue.Queue()
        with patch('assistant.voice_server.mx.load', return_value={}), \
             patch('assistant.voice_server.mx.random.uniform', return_value=0.0):
            
            vs.server_process(
                self.c2s, self.s2c, 
                status_queue=self.status_q,
                hf_repo="dummy", 
                quantized=4
            )
            
        # Check for errors in status queue
        while not self.status_q.empty():
            msg = self.status_q.get()
            print(f"DEBUG: Status message: {msg}")
            
        # Verification
        self.mock_text_tokenizer.encode.assert_called_with("Hello World")
        self.assertEqual(self.mock_gen.step.call_count, 3)
        print("✅ Injection logic verified: Tokenizer called, Step called 3 times.")

class TestSubconsciousBridge(unittest.TestCase):
    def test_bridge_trigger(self):
        """Test that SubconsciousBridge triggers injection on transcript update."""
        print("\nTesting SubconsciousBridge...")
        
        mock_ai = MagicMock()
        c2s = queue.Queue()
        
        bridge = SubconsciousBridge(mock_ai, c2s)
        
        # Mock AI response
        mock_ai.generate_response.return_value = "This is a subconscious thought."
        
        # We need to control time to trigger the check
        # The loop checks: time.time() - self.last_query_time > 5.0
        
        # We will manually call the check method instead of running the thread
        # to avoid race conditions and waiting
        
        bridge.transcript_buffer = "User: Hello\nMoshi: Hi there\n" * 10 # Fill buffer > 50 chars
        bridge.last_query_time = 0 # Force time check to pass
        
        # Mock time.time to be large enough
        with patch('time.time', return_value=1000.0):
            bridge._monitor_loop = MagicMock(wraps=bridge._monitor_loop) # Spy on it? No, just call internal method
            
            # We can just call _query_brain directly to test logic, 
            # OR we can run the loop for one iteration.
            # Let's call _query_brain directly as it's the core logic
            bridge._query_brain()
            
        # Check if injection message was put in queue
        try:
            msg = c2s.get_nowait()
            self.assertEqual(msg[0], "inject")
            self.assertIn("This is a subconscious thought", msg[1])
            print("✅ SubconsciousBridge verified: Injection message sent.")
        except queue.Empty:
            self.fail("Queue is empty, injection not triggered")

if __name__ == '__main__':
    unittest.main()
