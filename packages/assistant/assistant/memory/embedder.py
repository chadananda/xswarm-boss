"""
Embedder - Generate vector embeddings for semantic search.

Supports dual-mode architecture:
- Production mode: OpenAI embeddings API (text-embedding-3-small)
- Dev mode: Local sentence-transformers model (all-MiniLM-L6-v2)

Usage:
    # Production mode (requires OpenAI API key in config)
    embedder = Embedder(config, debug_mode=False)
    embedding = await embedder.embed("What was the user's favorite color?")

    # Dev mode (uses local model, no API key needed)
    embedder = Embedder(config, debug_mode=True)
    embedding = await embedder.embed("What was the user's favorite color?")

Architecture:
- Production: Uses OpenAI embeddings API via httpx
- Dev: Uses sentence-transformers with 'all-MiniLM-L6-v2' model
- Graceful fallback: Returns zero vector on failure (allows system to continue)

Dependencies:
- Production: openai (pip install openai)
- Dev: sentence-transformers (pip install sentence-transformers)
"""

import os
import asyncio
from typing import List, Optional, TYPE_CHECKING, Any
from dataclasses import dataclass

# Type checking imports (not runtime)
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
    import openai

# Try importing dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = Any  # Fallback type


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    # OpenAI settings (production mode)
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"  # 1536 dimensions, cheap, fast

    # Local model settings (dev mode)
    local_model: str = "all-MiniLM-L6-v2"  # 384 dimensions, fast, good quality

    # Common settings
    embedding_dimension: int = 384  # Default to local model dimensions
    max_tokens: int = 512  # Maximum text length


class Embedder:
    """
    Generate vector embeddings for semantic search.

    Dual-mode architecture:
    - Production mode: OpenAI embeddings API
    - Dev mode: Local sentence-transformers model

    Attributes:
        debug_mode (bool): If True, uses local model. If False, uses OpenAI API.
        config (EmbeddingConfig): Embedding configuration.
        _local_model: Local model instance (lazy loaded).
        _openai_client: OpenAI client (lazy loaded).
    """

    def __init__(self, config: EmbeddingConfig, debug_mode: bool = False):
        """
        Initialize embedder.

        Args:
            config: Embedding configuration with API keys and model settings.
            debug_mode: If True, uses local model. If False, uses OpenAI API.

        Raises:
            ValueError: If production mode requested but no OpenAI API key provided.
            ImportError: If required dependencies not installed.
        """
        self.debug_mode = debug_mode
        self.config = config
        self._local_model: Optional[Any] = None
        self._openai_client: Optional[Any] = None

        # Validate configuration based on mode
        if not self.debug_mode:
            # Production mode - requires OpenAI
            if not OPENAI_AVAILABLE:
                raise ImportError(
                    "openai package required for production mode. "
                    "Install with: pip install openai"
                )
            if not self.config.openai_api_key:
                raise ValueError(
                    "OpenAI API key required for production mode embeddings. "
                    "Set OPENAI_API_KEY in config or use debug_mode=True for local embeddings."
                )
            # Update dimension for OpenAI model
            if self.config.openai_model == "text-embedding-3-small":
                self.config.embedding_dimension = 1536
            elif self.config.openai_model == "text-embedding-3-large":
                self.config.embedding_dimension = 3072
        else:
            # Dev mode - requires sentence-transformers
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers package required for dev mode. "
                    "Install with: pip install sentence-transformers"
                )
            # Update dimension for local model
            if self.config.local_model == "all-MiniLM-L6-v2":
                self.config.embedding_dimension = 384

    def _get_local_model(self) -> Any:
        """
        Lazy load local sentence-transformers model.

        Returns:
            SentenceTransformer: Loaded model instance.
        """
        if self._local_model is None:
            self._local_model = SentenceTransformer(self.config.local_model)
        return self._local_model

    def _get_openai_client(self) -> Any:
        """
        Lazy load OpenAI client.

        Returns:
            openai.AsyncOpenAI: OpenAI client instance.
        """
        if self._openai_client is None:
            self._openai_client = openai.AsyncOpenAI(
                api_key=self.config.openai_api_key
            )
        return self._openai_client

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed (will be truncated to max_tokens).

        Returns:
            List[float]: Embedding vector (dimension depends on model).
                         Returns zero vector on failure (allows graceful degradation).

        Examples:
            >>> embedder = Embedder(config, debug_mode=True)
            >>> embedding = await embedder.embed("Hello world")
            >>> len(embedding)
            384

            >>> embedder = Embedder(config, debug_mode=False)
            >>> embedding = await embedder.embed("Hello world")
            >>> len(embedding)
            1536
        """
        # Truncate text if too long
        if len(text) > self.config.max_tokens * 4:  # Rough estimate: 4 chars per token
            text = text[:self.config.max_tokens * 4]

        if self.debug_mode:
            return await self._embed_local(text)
        else:
            return await self._embed_openai(text)

    async def _embed_local(self, text: str) -> List[float]:
        """
        Generate embedding using local sentence-transformers model.

        Args:
            text: Text to embed.

        Returns:
            List[float]: Embedding vector (384 dimensions for all-MiniLM-L6-v2).
                         Returns zero vector on failure.
        """
        try:
            model = self._get_local_model()

            # Run in thread pool to avoid blocking async event loop
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                model.encode,
                text
            )

            # Convert numpy array to list
            embedding_list = embedding.tolist()

            return embedding_list

        except Exception:
            # Return zero vector (graceful degradation)
            return [0.0] * self.config.embedding_dimension

    async def _embed_openai(self, text: str) -> List[float]:
        """
        Generate embedding using OpenAI embeddings API.

        Args:
            text: Text to embed.

        Returns:
            List[float]: Embedding vector (1536 dimensions for text-embedding-3-small).
                         Returns zero vector on failure.
        """
        try:
            client = self._get_openai_client()

            # Call OpenAI embeddings API
            response = await client.embeddings.create(
                model=self.config.openai_model,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            return embedding

        except Exception:
            # Return zero vector (graceful degradation)
            return [0.0] * self.config.embedding_dimension

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed.

        Returns:
            List[List[float]]: List of embedding vectors.

        Examples:
            >>> embedder = Embedder(config, debug_mode=True)
            >>> embeddings = await embedder.embed_batch(["Hello", "World"])
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            384
        """
        if self.debug_mode:
            return await self._embed_batch_local(texts)
        else:
            return await self._embed_batch_openai(texts)

    async def _embed_batch_local(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch using local model.

        Args:
            texts: List of texts to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        try:
            model = self._get_local_model()

            # Run in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                model.encode,
                texts
            )

            # Convert numpy arrays to lists
            embeddings_list = [emb.tolist() for emb in embeddings]

            return embeddings_list

        except Exception:
            # Return zero vectors for all texts
            return [[0.0] * self.config.embedding_dimension for _ in texts]

    async def _embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch using OpenAI API.

        Args:
            texts: List of texts to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        try:
            client = self._get_openai_client()

            # Call OpenAI embeddings API with batch
            response = await client.embeddings.create(
                model=self.config.openai_model,
                input=texts,
                encoding_format="float"
            )

            # Extract embeddings (preserve order)
            embeddings = [item.embedding for item in response.data]

            return embeddings

        except Exception:
            # Return zero vectors for all texts
            return [[0.0] * self.config.embedding_dimension for _ in texts]

    def get_dimension(self) -> int:
        """
        Get embedding dimension for current configuration.

        Returns:
            int: Embedding dimension (384 for local, 1536 for OpenAI small).

        Examples:
            >>> embedder = Embedder(config, debug_mode=True)
            >>> embedder.get_dimension()
            384
        """
        return self.config.embedding_dimension

    def is_available(self) -> bool:
        """
        Check if embedder is available (dependencies installed).

        Returns:
            bool: True if embedder can generate embeddings.
        """
        if self.debug_mode:
            return SENTENCE_TRANSFORMERS_AVAILABLE
        else:
            return OPENAI_AVAILABLE and self.config.openai_api_key is not None


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_embedder_from_env(debug_mode: bool = False) -> Embedder:
    """
    Create embedder from environment variables.

    Environment variables:
        OPENAI_API_KEY: OpenAI API key (production mode)
        OPENAI_EMBEDDING_MODEL: OpenAI model name (optional)
        LOCAL_EMBEDDING_MODEL: Local model name (optional)

    Args:
        debug_mode: If True, uses local model. If False, uses OpenAI API.

    Returns:
        Embedder: Configured embedder instance.

    Examples:
        >>> # Production mode
        >>> os.environ["OPENAI_API_KEY"] = "sk-..."
        >>> embedder = create_embedder_from_env(debug_mode=False)

        >>> # Dev mode
        >>> embedder = create_embedder_from_env(debug_mode=True)
    """
    config = EmbeddingConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        local_model=os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )

    return Embedder(config, debug_mode=debug_mode)


# =============================================================================
# INLINE TESTS
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_embedder():
        """Test embedder in both modes."""
        print("Testing Embedder...")

        # Test 1: Dev mode (local model) - only if available
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            print("\n1. Testing dev mode (local model)...")
            config = EmbeddingConfig()
            embedder = Embedder(config, debug_mode=True)

            assert embedder.is_available(), "Dev mode should be available"
            assert embedder.get_dimension() == 384, "Local model should have 384 dimensions"

            embedding = await embedder.embed("Hello world")
            assert len(embedding) == 384, f"Expected 384 dimensions, got {len(embedding)}"
            assert any(x != 0 for x in embedding), "Embedding should not be all zeros"
            print(f"   ✓ Generated embedding: {len(embedding)} dimensions")

            # Test 2: Batch embedding (dev mode)
            print("\n2. Testing batch embedding (dev mode)...")
            embeddings = await embedder.embed_batch(["Hello", "World", "Test"])
            assert len(embeddings) == 3, "Should generate 3 embeddings"
            assert all(len(emb) == 384 for emb in embeddings), "All embeddings should be 384 dimensions"
            print(f"   ✓ Generated {len(embeddings)} embeddings in batch")
        else:
            print("\n1. Skipping dev mode tests (sentence-transformers not available)")
            print("   Install with: pip install sentence-transformers")

        # Test 3: Production mode (if API key available)
        if os.getenv("OPENAI_API_KEY") and OPENAI_AVAILABLE:
            print("\n3. Testing production mode (OpenAI API)...")
            config_prod = EmbeddingConfig(openai_api_key=os.getenv("OPENAI_API_KEY"))
            embedder_prod = Embedder(config_prod, debug_mode=False)

            assert embedder_prod.is_available(), "Production mode should be available"
            assert embedder_prod.get_dimension() == 1536, "OpenAI model should have 1536 dimensions"

            embedding_prod = await embedder_prod.embed("Hello world")
            assert len(embedding_prod) == 1536, f"Expected 1536 dimensions, got {len(embedding_prod)}"
            print(f"   ✓ Generated OpenAI embedding: {len(embedding_prod)} dimensions")

            # Test 4: Error handling (invalid API key)
            print("\n4. Testing error handling...")
            config_bad = EmbeddingConfig(openai_api_key="invalid-key")
            embedder_bad = Embedder(config_bad, debug_mode=False)

            embedding_bad = await embedder_bad.embed("This should fail gracefully")
            assert len(embedding_bad) == 1536, "Should return zero vector on failure"
            assert all(x == 0 for x in embedding_bad), "Failed embedding should be zero vector"
            print("   ✓ Graceful fallback to zero vector on API error")
        else:
            print("\n3. Skipping production mode tests (no OPENAI_API_KEY or openai package)")

        print("\n✅ All available embedder tests passed!")
        print("\nNote: This module supports dual-mode architecture:")
        print("  - Dev mode: Local sentence-transformers (requires manual install)")
        print("  - Production mode: OpenAI embeddings API (requires API key)")

    # Run tests
    asyncio.run(test_embedder())
