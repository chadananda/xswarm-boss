"""
Tests for AIClient - unified AI wrapper for Claude/OpenAI.

Tests include:
- Client initialization with different API keys
- Provider selection (OpenAI with available SDK)
- Chat method
- Error handling (missing keys, API failures)
- Message formatting
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.voice.conversation import AIClient


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_config_openai():
    """Mock Config with OpenAI API key"""
    config = Mock()
    config.anthropic_api_key = None
    config.openai_api_key = "test-openai-key-456"
    return config


@pytest.fixture
def mock_config_none():
    """Mock Config with no API keys"""
    config = Mock()
    config.anthropic_api_key = None
    config.openai_api_key = None
    return config


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestAIClientInitialization:
    """Tests for AIClient initialization."""
    
    def test_init_with_openai_key(self, mock_config_openai):
        """Test initialization with OpenAI API key."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            mock_client = Mock()
            MockOpenAI.return_value = mock_client
            
            client = AIClient(mock_config_openai)
            
            assert client.provider == "openai"
            assert client.client is not None
            MockOpenAI.assert_called_once_with(api_key="test-openai-key-456")
    
    def test_init_fails_no_keys(self, mock_config_none):
        """Test initialization fails when no API keys provided."""
        with pytest.raises(ValueError, match="No AI API key found"):
            AIClient(mock_config_none)


# =============================================================================
# CHAT METHOD TESTS - OPENAI
# =============================================================================

class TestAIClientChatOpenAI:
    """Tests for chat method with OpenAI provider."""
    
    @pytest.mark.asyncio
    async def test_chat_openai_basic(self, mock_config_openai):
        """Test basic chat with OpenAI."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            # Mock OpenAI client
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Hello from GPT!"))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockOpenAI.return_value = mock_client
            
            # Create AI client
            client = AIClient(mock_config_openai)
            
            # Test chat
            messages = [
                {"role": "user", "content": "Hello"}
            ]
            response = await client.chat(messages)
            
            # Verify response
            assert response == "Hello from GPT!"
            
            # Verify API called correctly
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["max_tokens"] == 1024
            assert call_kwargs["messages"] == messages
    
    @pytest.mark.asyncio
    async def test_chat_openai_with_system_prompt(self, mock_config_openai):
        """Test OpenAI keeps system message in conversation."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            # Mock OpenAI client
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="I am GLaDOS."))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockOpenAI.return_value = mock_client
            
            # Create AI client
            client = AIClient(mock_config_openai)
            
            # Test chat with system message
            messages = [
                {"role": "system", "content": "You are GLaDOS."},
                {"role": "user", "content": "Who are you?"}
            ]
            response = await client.chat(messages)
            
            # Verify system message kept in messages
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert len(call_kwargs["messages"]) == 2
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][1]["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_chat_openai_custom_max_tokens(self, mock_config_openai):
        """Test custom max_tokens parameter with OpenAI."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Response"))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockOpenAI.return_value = mock_client
            
            client = AIClient(mock_config_openai)
            
            messages = [{"role": "user", "content": "Test"}]
            await client.chat(messages, max_tokens=4096)
            
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["max_tokens"] == 4096


# =============================================================================
# IS_AVAILABLE TESTS
# =============================================================================

class TestAIClientIsAvailable:
    """Tests for is_available method."""
    
    def test_is_available_with_client(self, mock_config_openai):
        """Test is_available returns True when client initialized."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            MockOpenAI.return_value = Mock()
            
            client = AIClient(mock_config_openai)
            
            assert client.is_available() is True
    
    def test_is_available_no_client(self):
        """Test is_available returns False when no client."""
        config = Mock()
        config.anthropic_api_key = None
        config.openai_api_key = None
        
        try:
            client = AIClient(config)
            assert client.is_available() is False
        except ValueError:
            # Expected - no API key
            pass


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestAIClientErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_chat_uninitialized_client(self):
        """Test chat fails gracefully when client not initialized."""
        config = Mock()
        config.anthropic_api_key = None
        config.openai_api_key = None
        
        # Should raise during init
        with pytest.raises(ValueError):
            AIClient(config)
    
    @pytest.mark.asyncio
    async def test_chat_api_error_openai(self, mock_config_openai):
        """Test chat handles OpenAI API errors."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            MockOpenAI.return_value = mock_client
            
            client = AIClient(mock_config_openai)
            
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(Exception, match="API Error"):
                await client.chat(messages)


# =============================================================================
# MESSAGE FORMATTING TESTS
# =============================================================================

class TestMessageFormatting:
    """Tests for message formatting with OpenAI provider."""
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation_openai(self, mock_config_openai):
        """Test multi-turn conversation with OpenAI."""
        with patch('openai.AsyncOpenAI') as MockOpenAI:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Sure!"))]
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockOpenAI.return_value = mock_client
            
            client = AIClient(mock_config_openai)
            
            messages = [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
                {"role": "user", "content": "Help me"}
            ]
            await client.chat(messages)
            
            # Verify all messages included
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert len(call_kwargs["messages"]) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
