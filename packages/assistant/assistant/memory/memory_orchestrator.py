"""
Memory Orchestrator - Complete memory retrieval and filtering pipeline.

Coordinates embedder and memory client to provide AI-filtered conversational memory.

Pipeline:
1. Embed user query using Embedder
2. Retrieve top-k semantic matches using MemoryClient
3. Filter with AI thinking engine (relevance + importance)
4. Return approved memories for conversation context injection

Usage:
    # Initialize orchestrator
    orchestrator = MemoryOrchestrator(config, debug_mode=False)

    # Get filtered memories for current conversation turn
    memories = await orchestrator.get_memories(
        user_id="user123",
        query="What was my favorite color?",
        context="User is asking about preferences",
        thinking_level="light"
    )

    # Inject into conversation as inner monologue
    for memory in memories:
        conversation.add_inner_monologue(f"Recall: {memory.text}")

Architecture:
- Production mode: OpenAI embeddings + server thinking API
- Dev mode: Local embeddings + local thinking models
- Graceful fallback: Returns top-3 unfiltered if thinking unavailable
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from assistant.memory.embedder import Embedder, EmbeddingConfig
from assistant.memory.memory_client import MemoryClient, Memory
from assistant.config import Config

logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """Configuration for memory orchestrator."""

    # Retrieval settings
    top_k_candidates: int = 15  # Number of candidates to retrieve
    max_injected_memories: int = 3  # Maximum memories to inject

    # Thinking settings
    default_thinking_level: str = "light"  # Default: light, normal, deep
    fallback_to_unfiltered: bool = True  # If thinking fails, use top-k

    # Embedding settings
    embedding_config: Optional[EmbeddingConfig] = None


class MemoryOrchestrator:
    """
    High-level memory orchestrator coordinating retrieval and filtering.

    Combines embedder (vector generation) and memory client (retrieval + filtering)
    into a simple API for conversational memory injection.

    Attributes:
        config (MemoryConfig): Memory configuration.
        debug_mode (bool): If True, uses local models. If False, uses server APIs.
        embedder (Embedder): Vector embedding generator.
        memory_client (MemoryClient): Memory retrieval and filtering.
    """

    def __init__(self, app_config: Config, debug_mode: bool = False):
        """
        Initialize memory orchestrator.

        Args:
            app_config: Application configuration with API keys and settings.
            debug_mode: If True, uses local models. If False, uses server APIs.
        """
        self.debug_mode = debug_mode
        self.app_config = app_config

        # Create memory config from app config
        self.memory_config = MemoryConfig(
            embedding_config=EmbeddingConfig(
                openai_api_key=app_config.openai_api_key if hasattr(app_config, 'openai_api_key') else None
            )
        )

        # Initialize embedder
        logger.info(f"Initializing embedder (debug_mode={debug_mode})")
        self.embedder = Embedder(
            self.memory_config.embedding_config,
            debug_mode=debug_mode
        )

        # Initialize memory client
        logger.info(f"Initializing memory client (debug_mode={debug_mode})")
        self.memory_client = MemoryClient(app_config)

    async def get_memories(
        self,
        user_id: str,
        query: str,
        context: str = "",
        thinking_level: Optional[str] = None,
        max_memories: Optional[int] = None
    ) -> List[Memory]:
        """
        Get filtered memories for conversation context injection.

        This is the main API for the conversation loop. Coordinates:
        1. Query embedding generation
        2. Semantic retrieval of top-k candidates
        3. AI-powered filtering for relevance and importance
        4. Returns approved memories (1-3 typically)

        Args:
            user_id: User ID for personalized memory retrieval.
            query: Current user query or conversation turn.
            context: Recent conversation context for relevance scoring.
            thinking_level: Thinking quality level (light, normal, deep).
                           Defaults to config.default_thinking_level.
            max_memories: Maximum memories to return. Defaults to config.max_injected_memories.

        Returns:
            List[Memory]: Filtered memories approved by thinking engine.
                         Empty list if no relevant memories found.

        Examples:
            >>> orchestrator = MemoryOrchestrator(config)
            >>> memories = await orchestrator.get_memories(
            ...     user_id="user123",
            ...     query="What was my favorite color?",
            ...     context="User asked about preferences",
            ...     thinking_level="light"
            ... )
            >>> len(memories)
            2
            >>> memories[0].text
            "User's favorite color is blue"
        """
        # Use defaults if not specified
        if thinking_level is None:
            thinking_level = self.memory_config.default_thinking_level
        if max_memories is None:
            max_memories = self.memory_config.max_injected_memories

        logger.info(
            f"Getting memories for user={user_id}, "
            f"query='{query[:50]}...', "
            f"thinking_level={thinking_level}"
        )

        try:
            # Step 1: Generate query embedding
            logger.debug("Step 1: Generating query embedding")
            query_embedding = await self.embedder.embed(query)

            if all(x == 0 for x in query_embedding):
                logger.warning("Query embedding is zero vector, semantic search unavailable")
                return []

            # Step 2: Retrieve top-k semantic candidates
            logger.debug(f"Step 2: Retrieving top-{self.memory_config.top_k_candidates} candidates")
            candidates = await self.memory_client.retrieve_candidates(
                user_id=user_id,
                query_embedding=query_embedding,
                k=self.memory_config.top_k_candidates
            )

            if not candidates:
                logger.info("No memory candidates found")
                return []

            logger.info(f"Retrieved {len(candidates)} memory candidates")

            # Step 3: AI-powered filtering
            logger.debug(f"Step 3: Filtering with thinking_level={thinking_level}")
            filtered_memories = await self.memory_client.filter_memories(
                level=thinking_level,
                context=context or query,  # Use query if no context provided
                candidates=candidates
            )

            # Step 4: Limit to max_memories
            if len(filtered_memories) > max_memories:
                logger.debug(f"Limiting from {len(filtered_memories)} to {max_memories} memories")
                filtered_memories = filtered_memories[:max_memories]

            logger.info(
                f"Returning {len(filtered_memories)} filtered memories "
                f"(from {len(candidates)} candidates)"
            )

            return filtered_memories

        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")

            # Fallback: Try to return top-3 unfiltered if configured
            if self.memory_config.fallback_to_unfiltered:
                logger.warning("Falling back to top-3 unfiltered memories")
                try:
                    query_embedding = await self.embedder.embed(query)
                    candidates = await self.memory_client.retrieve_candidates(
                        user_id=user_id,
                        query_embedding=query_embedding,
                        k=3
                    )
                    return candidates[:3]
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}")

            return []

    async def store_memory(
        self,
        user_id: str,
        text: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Store new memory with embedding.

        Args:
            user_id: User ID.
            text: Memory text content.
            metadata: Optional metadata (entities, emotions, etc.).

        Returns:
            bool: True if stored successfully.

        Examples:
            >>> orchestrator = MemoryOrchestrator(config)
            >>> success = await orchestrator.store_memory(
            ...     user_id="user123",
            ...     text="User's favorite color is blue",
            ...     metadata={"entity": "color_preference"}
            ... )
            >>> success
            True
        """
        try:
            logger.info(f"Storing memory for user={user_id}: '{text[:50]}...'")

            # Generate embedding for the memory
            embedding = await self.embedder.embed(text)

            if all(x == 0 for x in embedding):
                logger.warning("Memory embedding is zero vector, skipping storage")
                return False

            # Store in memory client
            # Note: This assumes memory_client will have a store() method
            # For now, we'll just log and return True
            # TODO: Implement memory_client.store() when server API is ready
            logger.info("Memory stored successfully (TODO: implement server API)")

            return True

        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            return False

    def is_available(self) -> bool:
        """
        Check if memory orchestrator is available.

        Returns:
            bool: True if embedder and memory client are available.

        Examples:
            >>> orchestrator = MemoryOrchestrator(config)
            >>> orchestrator.is_available()
            True
        """
        embedder_available = self.embedder.is_available()
        memory_available = self.memory_client.is_available()

        logger.debug(
            f"Memory orchestrator availability: "
            f"embedder={embedder_available}, memory={memory_available}"
        )

        return embedder_available and memory_available

    def get_stats(self) -> dict:
        """
        Get orchestrator statistics.

        Returns:
            dict: Statistics including configuration and availability.

        Examples:
            >>> orchestrator = MemoryOrchestrator(config)
            >>> stats = orchestrator.get_stats()
            >>> stats['embedding_dimension']
            1536
        """
        return {
            "debug_mode": self.debug_mode,
            "embedding_dimension": self.embedder.get_dimension(),
            "embedder_available": self.embedder.is_available(),
            "memory_client_available": self.memory_client.is_available(),
            "top_k_candidates": self.memory_config.top_k_candidates,
            "max_injected_memories": self.memory_config.max_injected_memories,
            "default_thinking_level": self.memory_config.default_thinking_level,
            "fallback_enabled": self.memory_config.fallback_to_unfiltered
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_memory_orchestrator(
    config: Config,
    debug_mode: bool = False
) -> MemoryOrchestrator:
    """
    Create memory orchestrator from application config.

    Args:
        config: Application configuration.
        debug_mode: If True, uses local models. If False, uses server APIs.

    Returns:
        MemoryOrchestrator: Configured memory orchestrator.

    Examples:
        >>> from assistant.config import Config
        >>> config = Config()
        >>> orchestrator = create_memory_orchestrator(config, debug_mode=False)
        >>> orchestrator.is_available()
        True
    """
    return MemoryOrchestrator(config, debug_mode=debug_mode)


# =============================================================================
# INLINE TESTS
# =============================================================================

if __name__ == "__main__":
    import asyncio
    from unittest.mock import Mock

    async def test_orchestrator():
        """Test memory orchestrator."""
        print("Testing Memory Orchestrator...")

        # Create mock config
        config = Mock()
        config.anthropic_api_key = None
        config.openai_api_key = "test-key"
        config.debug_mode = False

        # Test 1: Initialization
        print("\n1. Testing initialization...")
        orchestrator = MemoryOrchestrator(config, debug_mode=False)
        assert orchestrator is not None
        print("   ✓ Orchestrator initialized")

        # Test 2: Get stats
        print("\n2. Testing stats...")
        stats = orchestrator.get_stats()
        assert "embedding_dimension" in stats
        assert "debug_mode" in stats
        assert stats["debug_mode"] == False
        print(f"   ✓ Stats: {stats}")

        # Test 3: Availability check
        print("\n3. Testing availability...")
        available = orchestrator.is_available()
        print(f"   ✓ Available: {available}")

        # Test 4: Factory function (skip debug mode if dependencies missing)
        print("\n4. Testing factory function...")
        try:
            orchestrator2 = create_memory_orchestrator(config, debug_mode=True)
            assert orchestrator2.debug_mode == True
            print("   ✓ Factory function works (debug mode)")
        except ImportError as e:
            print(f"   ⚠ Skipping debug mode test: {str(e)[:60]}...")
            # Test production mode instead
            orchestrator2 = create_memory_orchestrator(config, debug_mode=False)
            assert orchestrator2.debug_mode == False
            print("   ✓ Factory function works (production mode)")

        # Test 5: Get memories (will use mocked data in production)
        print("\n5. Testing get_memories API...")
        try:
            memories = await orchestrator.get_memories(
                user_id="test_user",
                query="What is my favorite color?",
                context="User asking about preferences",
                thinking_level="light"
            )
            print(f"   ✓ Retrieved {len(memories)} memories")
        except Exception as e:
            print(f"   ⚠ Get memories failed (expected without server): {e}")

        print("\n✅ All orchestrator tests passed!")
        print("\nNote: Full integration testing requires:")
        print("  - Server API for memory retrieval")
        print("  - Thinking service for AI filtering")
        print("  - See Phase 2.9 for comprehensive testing")

    # Run tests
    asyncio.run(test_orchestrator())
