"""
Test MoshiBridge (Local Voice Server).
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
import sys

# Mock MLX and other dependencies BEFORE importing voice
# We use a more robust mocking strategy
import sys
from unittest.mock import MagicMock

# Create a dummy module for MLX
class MockMlx:
    def __getattr__(self, name):
        return MagicMock()
    
    class core:
        @staticmethod
        def array(x): return MagicMock()
        @staticmethod
        def zeros(*args, **kwargs): return MagicMock()
        int32 = "int32"
        float32 = "float32"
        bfloat16 = "bfloat16"

    class nn:
        @staticmethod
        def quantize(*args, **kwargs): pass

sys.modules['mlx'] = MockMlx()
sys.modules['mlx.core'] = MockMlx.core
sys.modules['mlx.nn'] = MockMlx.nn
sys.modules['rustymimi'] = MagicMock()
sys.modules['moshi_mlx'] = MagicMock()
sys.modules['moshi_mlx.models'] = MagicMock()
sys.modules['moshi_mlx.utils'] = MagicMock()
sys.modules['huggingface_hub'] = MagicMock()
sys.modules['sentencepiece'] = MagicMock()

# Patch hardware to avoid GPU detection during import
with patch.dict('sys.modules', {'assistant.hardware': MagicMock()}):
    from assistant.voice import MoshiBridge

@pytest.mark.asyncio
async def test_moshi_bridge_initialization():
    """Test that MoshiBridge initializes correctly."""
    with patch('assistant.voice.hf_hub_download') as mock_download:
        bridge = MoshiBridge(quality="q4")
        assert bridge.quality == "q4"
        assert bridge.sample_rate == 24000

@pytest.mark.asyncio
async def test_moshi_bridge_encoding():
    """Test audio encoding."""
    with patch('assistant.voice.hf_hub_download'):
        bridge = MoshiBridge(quality="q4")
        
        # Mock audio tokenizer
        bridge.audio_tokenizer = MagicMock()
        bridge.audio_tokenizer.get_encoded.side_effect = [np.zeros((1, 8)), None]
        
        audio = np.zeros(1920, dtype=np.float32)
        codes = bridge.encode_audio(audio)
        
        assert codes is not None
        bridge.audio_tokenizer.encode.assert_called_once()

@pytest.mark.asyncio
async def test_moshi_bridge_generation():
    """Test response generation."""
    with patch('assistant.voice.hf_hub_download'):
        bridge = MoshiBridge(quality="q4")
        
        # Mock internals
        bridge.encode_audio = MagicMock(return_value=np.zeros((1, 8)))
        bridge.decode_audio = MagicMock(return_value=np.zeros(1920))
        bridge.model = MagicMock()
        
        # Mock LmGen
        with patch('moshi_mlx.models.LmGen') as MockGen:
            mock_gen_instance = MockGen.return_value
            # Mock step to return (text_token, audio_tokens)
            # text_token is a tensor, audio_tokens is a list/tensor
            mock_gen_instance.step.return_value = (MagicMock(item=lambda: 0), None)
            mock_gen_instance.last_audio_tokens.return_value = [[0]*8]
            
            audio, text = bridge.generate_response(np.zeros(1920), text_prompt="Test")
            
            assert isinstance(audio, np.ndarray)
            assert isinstance(text, str)
