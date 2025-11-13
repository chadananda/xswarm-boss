"""
Memory Client with dev/prod modes and thinking service integration.
Handles memory retrieval and AI-powered filtering with fallback support.
"""
# Standard library imports
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
# Third-party imports
import httpx
# Local imports
from ..config import Config
from .model_config import ModelConfig, load_thinking_config

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """A single memory record."""
    id: str
    user_id: str
    text: str
    created_at: datetime
    relevance_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure created_at is datetime object."""
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)


class MemoryClient:
    """
    Memory client with dev/prod modes and thinking service integration.

    Dev mode: Uses local Ollama/Anthropic/OpenAI from .env
    Production mode: Uses server API for both memory and thinking
    Fallback: Always returns top-3 candidates if anything fails
    """

    def __init__(self, config: Config):
        """
        Initialize memory client.

        Args:
            config: Application configuration
        """
        self.config = config
        self.debug_mode = config.is_debug_mode
        self.client: Optional[httpx.AsyncClient] = None
        self.thinking_models: Optional[Dict[str, ModelConfig]] = None
        # Dev mode: Load thinking models from .env
        if self.debug_mode:
            try:
                self.thinking_models = load_thinking_config(debug_mode=True)
                if self.thinking_models:
                    logger.info("Loaded thinking models from .env:")
                    for level, model in self.thinking_models.items():
                        logger.info(f"  {level}: {model}")
            except Exception as e:
                logger.warning(f"Failed to load thinking config: {e}")
                self.thinking_models = None

    async def initialize(self):
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"MemoryClient initialized (debug_mode={self.debug_mode})")

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

    async def retrieve_candidates(
        self,
        user_id: str,
        query_embedding: List[float],
        k: int = 15
    ) -> List[Memory]:
        """
        Retrieve top-k semantically similar memories.

        Dev mode: Local SQLite (TODO - stub for now)
        Production mode: Server API

        Args:
            user_id: User identifier
            query_embedding: Query vector for semantic search
            k: Number of candidates to retrieve

        Returns:
            List of Memory objects
        """
        if self.debug_mode:
            # Dev mode: Local SQLite (TODO - will implement in later task)
            logger.debug("Dev mode: Local SQLite not yet implemented")
            return []
        else:
            # Production mode: Server API
            try:
                response = await self.client.post(
                    f"{self.config.server_url}/api/memory/retrieve",
                    json={
                        "user_id": user_id,
                        "query_embedding": query_embedding,
                        "limit": k
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    memories = [Memory(**m) for m in data.get("memories", [])]
                    logger.debug(f"Retrieved {len(memories)} candidates from server")
                    return memories
                else:
                    logger.warning(f"Server retrieve failed: {response.status_code}")
                    return []
            except Exception as e:
                logger.warning(f"Memory retrieval error: {e}")
                return []

    async def filter_memories(
        self,
        level: str,
        context: str,
        candidates: List[Memory]
    ) -> List[Memory]:
        """
        Filter candidate memories using AI thinking.

        Dev mode: Uses .env configured model (Ollama/Anthropic/OpenAI)
        Production mode: Server decides model based on cost
        Fallback: Returns top-3 without filtering

        Args:
            level: Thinking level ("light", "normal", "deep")
            context: Current conversation context
            candidates: Candidate memories to filter

        Returns:
            List of approved Memory objects (up to 3)
        """
        # Validate level
        valid_levels = {"light", "normal", "deep"}
        if level not in valid_levels:
            logger.warning(f"Invalid thinking level: {level}, using 'normal'")
            level = "normal"
        # Edge case: No candidates
        if not candidates:
            return []
        # Edge case: 3 or fewer candidates, return all
        if len(candidates) <= 3:
            return candidates
        # Dev mode: Use local models
        if self.debug_mode and self.thinking_models:
            try:
                model_config = self.thinking_models[level]
                logger.info(f"Filtering {len(candidates)} memories with {model_config}")
                # Route to provider-specific implementation
                if model_config.provider == "OLLAMA":
                    return await self._filter_ollama(
                        model_config.model,
                        context,
                        candidates
                    )
                elif model_config.provider == "ANTHROPIC":
                    return await self._filter_anthropic(
                        model_config.model,
                        context,
                        candidates
                    )
                elif model_config.provider == "OPENAI":
                    return await self._filter_openai(
                        model_config.model,
                        context,
                        candidates
                    )
                else:
                    logger.warning(f"Unknown provider: {model_config.provider}")
                    return candidates[:3]
            except Exception as e:
                logger.warning(f"Dev mode filtering failed: {e}")
                return candidates[:3]
        # Production mode: Server thinking API
        elif not self.debug_mode:
            return await self._filter_production(level, context, candidates)
        # Fallback: Return top-3
        else:
            logger.warning("No thinking service available, returning top-3")
            return candidates[:3]

    async def _filter_ollama(
        self,
        model: str,
        context: str,
        candidates: List[Memory]
    ) -> List[Memory]:
        """
        Filter using local Ollama instance.

        Args:
            model: Ollama model identifier
            context: Conversation context
            candidates: Candidate memories

        Returns:
            Filtered memories (up to 3)
        """
        try:
            prompt = self._build_filter_prompt(context, candidates)
            response = await self.client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30.0
            )
            if response.status_code == 200:
                data = response.json()
                # Parse JSON response
                decisions = json.loads(data["response"])
                # Filter based on AI decisions
                approved = [
                    candidates[i] for i, dec in enumerate(decisions)
                    if isinstance(dec, dict) and dec.get("relevant") and dec.get("important")
                ]
                result = approved[:3]  # Limit to 3
                logger.info(f"Ollama filtered {len(candidates)} → {len(result)} memories")
                return result
            else:
                logger.warning(f"Ollama API error: {response.status_code}")
                return candidates[:3]
        except json.JSONDecodeError as e:
            logger.warning(f"Ollama response parsing failed: {e}")
            return candidates[:3]
        except Exception as e:
            logger.warning(f"Ollama filtering failed: {e}")
            return candidates[:3]

    async def _filter_anthropic(
        self,
        model: str,
        context: str,
        candidates: List[Memory]
    ) -> List[Memory]:
        """
        Filter using Anthropic Claude API.

        Args:
            model: Anthropic model identifier
            context: Conversation context
            candidates: Candidate memories

        Returns:
            Filtered memories (up to 3)
        """
        try:
            from anthropic import AsyncAnthropic
            import os
            # Get API key
            api_key = self.config.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("Anthropic API key not found")
                return candidates[:3]
            # Create client
            client = AsyncAnthropic(api_key=api_key)
            prompt = self._build_filter_prompt(context, candidates)
            # Call API
            response = await client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            # Parse response
            decisions = json.loads(response.content[0].text)
            # Filter based on AI decisions
            approved = [
                candidates[i] for i, dec in enumerate(decisions)
                if isinstance(dec, dict) and dec.get("relevant") and dec.get("important")
            ]
            result = approved[:3]
            logger.info(f"Anthropic filtered {len(candidates)} → {len(result)} memories")
            return result
        except ImportError:
            logger.warning("anthropic package not installed")
            return candidates[:3]
        except json.JSONDecodeError as e:
            logger.warning(f"Anthropic response parsing failed: {e}")
            return candidates[:3]
        except Exception as e:
            logger.warning(f"Anthropic filtering failed: {e}")
            return candidates[:3]

    async def _filter_openai(
        self,
        model: str,
        context: str,
        candidates: List[Memory]
    ) -> List[Memory]:
        """
        Filter using OpenAI API.

        Args:
            model: OpenAI model identifier
            context: Conversation context
            candidates: Candidate memories

        Returns:
            Filtered memories (up to 3)
        """
        try:
            from openai import AsyncOpenAI
            import os
            # Get API key
            api_key = self.config.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OpenAI API key not found")
                return candidates[:3]
            # Create client
            client = AsyncOpenAI(api_key=api_key)
            prompt = self._build_filter_prompt(context, candidates)
            # Call API
            response = await client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                max_tokens=500,
                temperature=0.0
            )
            # Parse response
            decisions = json.loads(response.choices[0].message.content)
            # Filter based on AI decisions
            approved = [
                candidates[i] for i, dec in enumerate(decisions)
                if isinstance(dec, dict) and dec.get("relevant") and dec.get("important")
            ]
            result = approved[:3]
            logger.info(f"OpenAI filtered {len(candidates)} → {len(result)} memories")
            return result
        except ImportError:
            logger.warning("openai package not installed")
            return candidates[:3]
        except json.JSONDecodeError as e:
            logger.warning(f"OpenAI response parsing failed: {e}")
            return candidates[:3]
        except Exception as e:
            logger.warning(f"OpenAI filtering failed: {e}")
            return candidates[:3]

    async def _filter_production(
        self,
        level: str,
        context: str,
        candidates: List[Memory]
    ) -> List[Memory]:
        """
        Production mode: Server thinking API.

        Args:
            level: Thinking level
            context: Conversation context
            candidates: Candidate memories

        Returns:
            Filtered memories (up to 3)
        """
        try:
            # Convert Memory objects to dicts
            candidates_data = [
                {
                    "id": c.id,
                    "user_id": c.user_id,
                    "text": c.text,
                    "created_at": c.created_at.isoformat(),
                    "relevance_score": c.relevance_score,
                    "metadata": c.metadata
                }
                for c in candidates
            ]
            # Call server thinking API
            response = await self.client.post(
                f"{self.config.server_url}/api/thinking/filter",
                json={
                    "level": level,
                    "context": context,
                    "candidates": candidates_data
                },
                headers={"Authorization": f"Bearer {self.config.api_token}"},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                approved = [Memory(**m) for m in data.get("approved", [])]
                logger.info(f"Server filtered {len(candidates)} → {len(approved)} memories")
                return approved[:3]
            else:
                logger.warning(f"Server thinking failed: {response.status_code}")
                return candidates[:3]
        except Exception as e:
            logger.warning(f"Server thinking error: {e}")
            return candidates[:3]

    def is_available(self) -> bool:
        """
        Check if memory client is available.

        Returns:
            bool: True if memory client can retrieve and filter memories.
                 In dev mode, returns True if thinking models configured.
                 In production mode, returns True (always available via server).
        """
        if self.debug_mode:
            # Dev mode: Check if thinking models are configured
            return self.thinking_models is not None and len(self.thinking_models) > 0
        else:
            # Production mode: Always available (server-based)
            return True

    def _build_filter_prompt(
        self,
        context: str,
        candidates: List[Memory]
    ) -> str:
        """
        Build prompt for AI thinking engine.

        Asks AI to evaluate each candidate for:
        - Relevance: Does it relate to current conversation?
        - Importance: Is it significant enough to mention?

        Args:
            context: Current conversation context
            candidates: Candidate memories to evaluate

        Returns:
            Formatted prompt string
        """
        prompt = f"""Given this conversation context:
{context}

For each of these {len(candidates)} candidate memories, evaluate:
1. Is this memory relevant to the current conversation? (yes/no)
2. Is this memory important enough to inject into limited context? (yes/no)

Memories:
"""
        # Add numbered memories
        for i, mem in enumerate(candidates):
            prompt += f"\n{i+1}. {mem.text}"
        # Request JSON response
        prompt += """

Respond with JSON array (one object per memory):
[{"relevant": true/false, "important": true/false}, ...]"""
        return prompt
