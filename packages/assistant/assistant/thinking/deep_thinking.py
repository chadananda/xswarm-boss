"""
Deep Thinking Engine for Voice Assistant

Provides a two-tier AI architecture:
- Tier 1: Moshi (fast, conversational, voice interface)
- Tier 2: Deep Thinking LLM (slow, reasoning, tool-calling)

The deep thinking engine handles:
- Complex reasoning and planning
- Tool calling (search, memory, file system)
- Research and information gathering
- Memory search and recollection

Results are injected into Moshi as "inner monologue" or "memory injection"
to make Moshi appear smarter than it is.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ThinkingMode(Enum):
    """Deep thinking operation modes"""
    LOCAL = "local"  # Ollama (70B/13B/7B)
    CLOUD = "cloud"  # Anthropic Claude API


@dataclass
class ThinkingRequest:
    """
    Request for deep thinking operation.

    This is sent when Moshi needs help with:
    - Complex reasoning ("What's the best approach to...")
    - Memory search ("What did we discuss about...")
    - Research ("Find information about...")
    - Tool execution ("Search files for...")
    """
    prompt: str  # The thinking prompt
    context: str  # Recent conversation context
    tools_available: List[str]  # Available tools: ["memory_search", "file_search", "web_search"]
    max_tokens: int = 1000  # Max response length


@dataclass
class ThinkingResponse:
    """
    Response from deep thinking operation.

    Contains the result that will be injected into Moshi.
    """
    inner_monologue: str  # The thinking result (injected into Moshi)
    tool_calls: List[Dict[str, Any]]  # Tools that were called
    reasoning_trace: str  # Explanation of reasoning (for debugging)
    tokens_used: int  # Tokens consumed
    mode: ThinkingMode  # Local or cloud


class DeepThinkingEngine(ABC):
    """
    Abstract base class for deep thinking engines.

    Implementations:
    - AnthropicThinking: Uses Claude API (cloud)
    - OllamaThinking: Uses local Ollama (70B/13B/7B)
    """

    @abstractmethod
    def think(self, request: ThinkingRequest) -> ThinkingResponse:
        """
        Perform deep thinking operation.

        Args:
            request: Thinking request with prompt and context

        Returns:
            ThinkingResponse with inner monologue and tool results
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this thinking engine is available.

        Returns:
            True if engine is ready to use
        """
        pass


class AnthropicThinking(DeepThinkingEngine):
    """
    Deep thinking using Anthropic Claude API.

    Requires ANTHROPIC_API_KEY in config (debug mode).
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5"):
        """
        Initialize Anthropic thinking engine.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-sonnet-4-5)
        """
        self.api_key = api_key
        self.model = model
        self.client = None  # Lazy init

    def think(self, request: ThinkingRequest) -> ThinkingResponse:
        """
        Think using Anthropic Claude API.

        TODO: Implement actual Anthropic API call
        """
        # Placeholder implementation
        return ThinkingResponse(
            inner_monologue=f"[Anthropic thinking not yet implemented]",
            tool_calls=[],
            reasoning_trace="Not implemented",
            tokens_used=0,
            mode=ThinkingMode.CLOUD
        )

    def is_available(self) -> bool:
        """Check if Anthropic API is available."""
        return self.api_key is not None and len(self.api_key) > 0


class OllamaThinking(DeepThinkingEngine):
    """
    Deep thinking using local Ollama.

    Requires Ollama installed with a large model (70B/13B/7B).
    """

    def __init__(self, model: str = "llama3.1:70b", host: str = "http://localhost:11434"):
        """
        Initialize Ollama thinking engine.

        Args:
            model: Ollama model to use (llama3.1:70b/13b/7b)
            host: Ollama server host
        """
        self.model = model
        self.host = host
        self.client = None  # Lazy init

    def think(self, request: ThinkingRequest) -> ThinkingResponse:
        """
        Think using local Ollama.

        TODO: Implement actual Ollama API call
        """
        # Placeholder implementation
        return ThinkingResponse(
            inner_monologue=f"[Ollama thinking not yet implemented]",
            tool_calls=[],
            reasoning_trace="Not implemented",
            tokens_used=0,
            mode=ThinkingMode.LOCAL
        )

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False


def create_thinking_engine(
    mode: str,
    anthropic_api_key: Optional[str] = None,
    ollama_model: str = "llama3.1:70b",
    ollama_host: str = "http://localhost:11434"
) -> DeepThinkingEngine:
    """
    Factory function to create appropriate thinking engine.

    Args:
        mode: "cloud" or "local"
        anthropic_api_key: API key for Anthropic (required if mode="cloud")
        ollama_model: Ollama model name (used if mode="local")
        ollama_host: Ollama server host (used if mode="local")

    Returns:
        DeepThinkingEngine instance

    Raises:
        ValueError: If invalid mode or missing required parameters
    """
    if mode == "cloud":
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY required for cloud thinking")
        return AnthropicThinking(api_key=anthropic_api_key)

    elif mode == "local":
        engine = OllamaThinking(model=ollama_model, host=ollama_host)
        if not engine.is_available():
            raise RuntimeError(
                f"Ollama not available at {ollama_host}. "
                "Install Ollama and run: ollama pull llama3.1:70b"
            )
        return engine

    else:
        raise ValueError(f"Invalid thinking mode: {mode}. Must be 'cloud' or 'local'")


# Example usage
if __name__ == "__main__":
    # Test thinking engine creation
    print("Testing Deep Thinking Engine...")

    # Try cloud thinking (requires API key)
    try:
        engine = create_thinking_engine(mode="cloud", anthropic_api_key="test-key")
        print(f"✓ Cloud thinking engine created: {engine.__class__.__name__}")
        print(f"  Available: {engine.is_available()}")
    except Exception as e:
        print(f"✗ Cloud thinking failed: {e}")

    # Try local thinking (requires Ollama)
    try:
        engine = create_thinking_engine(mode="local")
        print(f"✓ Local thinking engine created: {engine.__class__.__name__}")
        print(f"  Available: {engine.is_available()}")
    except Exception as e:
        print(f"✗ Local thinking failed: {e}")
