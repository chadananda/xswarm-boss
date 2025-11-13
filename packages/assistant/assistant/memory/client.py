"""
Memory client for Node.js server integration.
Uses httpx for async HTTP communication.
"""

import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os


class MemoryClient:
    """
    Async HTTP client for memory server.

    Connects to Node.js server at packages/server/ for:
    - Storing conversation history
    - Retrieving context for responses
    - Semantic memory search
    - User preferences
    """

    def __init__(
        self,
        server_url: str = "http://localhost:3000",
        api_token: Optional[str] = None,
        timeout: float = 10.0
    ):
        """
        Initialize memory client.

        Args:
            server_url: Base URL of memory server
            api_token: Optional API token for authentication
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.api_token = api_token or os.getenv("XSWARM_API_TOKEN")
        self.timeout = timeout

        # Create async client
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        self.client = httpx.AsyncClient(
            base_url=self.server_url,
            headers=headers,
            timeout=timeout
        )

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()

    # Conversation Memory

    async def store_message(
        self,
        user_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Store a conversation message.

        Args:
            user_id: User identifier
            message: Message content
            role: Message role (user, assistant, system)
            metadata: Optional metadata (persona, timestamp, etc.)

        Returns:
            Stored message data
        """
        payload = {
            "userId": user_id,
            "message": message,
            "role": role,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        try:
            response = await self.client.post("/memory/store", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f"Error storing message: {e}")
            return {}

    async def retrieve_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation context.

        Args:
            user_id: User identifier
            query: Optional semantic search query
            limit: Max messages to retrieve

        Returns:
            List of relevant messages
        """
        params = {
            "userId": user_id,
            "limit": limit
        }

        if query:
            params["query"] = query

        try:
            response = await self.client.get("/memory/retrieve", params=params)
            response.raise_for_status()
            return response.json().get("messages", [])
        except httpx.HTTPError as e:
            print(f"Error retrieving context: {e}")
            return []

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.

        Args:
            user_id: User identifier
            limit: Max messages to retrieve

        Returns:
            List of recent messages
        """
        try:
            response = await self.client.get(
                f"/memory/history/{user_id}",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json().get("history", [])
        except httpx.HTTPError as e:
            print(f"Error getting history: {e}")
            return []

    async def clear_history(self, user_id: str) -> bool:
        """
        Clear user's conversation history.

        Args:
            user_id: User identifier

        Returns:
            True if successful
        """
        try:
            response = await self.client.delete(f"/memory/history/{user_id}")
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"Error clearing history: {e}")
            return False

    # Semantic Search

    async def semantic_search(
        self,
        user_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across user's memory.

        Args:
            user_id: User identifier
            query: Search query
            limit: Max results

        Returns:
            List of relevant memory entries
        """
        payload = {
            "userId": user_id,
            "query": query,
            "limit": limit
        }

        try:
            response = await self.client.post("/memory/search", json=payload)
            response.raise_for_status()
            return response.json().get("results", [])
        except httpx.HTTPError as e:
            print(f"Error in semantic search: {e}")
            return []

    # User Preferences

    async def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences.

        Args:
            user_id: User identifier

        Returns:
            User preferences dict
        """
        try:
            response = await self.client.get(f"/users/{user_id}/preferences")
            response.raise_for_status()
            return response.json().get("preferences", {})
        except httpx.HTTPError as e:
            print(f"Error getting preferences: {e}")
            return {}

    async def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> bool:
        """
        Set user preference.

        Args:
            user_id: User identifier
            key: Preference key
            value: Preference value

        Returns:
            True if successful
        """
        payload = {
            "key": key,
            "value": value
        }

        try:
            response = await self.client.post(
                f"/users/{user_id}/preferences",
                json=payload
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            print(f"Error setting preference: {e}")
            return False

    # Health Check

    async def health_check(self) -> bool:
        """
        Check if memory server is reachable.

        Returns:
            True if server is healthy
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False


class LocalMemoryCache:
    """
    Local in-memory cache for offline operation.
    Falls back to this when server is unreachable.
    """

    def __init__(self, max_messages: int = 100):
        self.max_messages = max_messages
        self.conversations: Dict[str, List[Dict]] = {}

    def store_message(
        self,
        user_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict] = None
    ):
        """Store message locally"""
        if user_id not in self.conversations:
            self.conversations[user_id] = []

        entry = {
            "message": message,
            "role": role,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        self.conversations[user_id].append(entry)

        # Trim to max size
        if len(self.conversations[user_id]) > self.max_messages:
            self.conversations[user_id] = self.conversations[user_id][-self.max_messages:]

    def get_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get recent history"""
        history = self.conversations.get(user_id, [])
        return history[-limit:]

    def clear_history(self, user_id: str):
        """Clear history"""
        if user_id in self.conversations:
            del self.conversations[user_id]


class MemoryManager:
    """
    High-level memory manager with automatic fallback.
    Uses server when available, falls back to local cache.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:3000",
        api_token: Optional[str] = None,
        max_history: int = 100
    ):
        self.client = MemoryClient(server_url, api_token)
        self.local_cache = LocalMemoryCache()
        self._server_available = None
        self.max_history = max_history

    async def initialize(self):
        """Initialize and check server availability"""
        self._server_available = await self.client.health_check()
        if self._server_available:
            print("✅ Memory server connected")
        else:
            print("⚠️ Memory server unavailable - using local cache")

    async def store_message(
        self,
        user_id: str,
        message: str,
        role: str = "user",
        metadata: Optional[Dict] = None
    ):
        """Store message (with fallback)"""
        if self._server_available:
            try:
                await self.client.store_message(user_id, message, role, metadata)
                return
            except Exception as e:
                print(f"Server error, falling back to local: {e}")
                self._server_available = False

        # Fallback to local
        self.local_cache.store_message(user_id, message, role, metadata)

    async def get_context(
        self,
        user_id: str,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get conversation context (with fallback)"""
        if self._server_available:
            try:
                return await self.client.retrieve_context(user_id, query, limit)
            except Exception as e:
                print(f"Server error, falling back to local: {e}")
                self._server_available = False

        # Fallback to local
        return self.local_cache.get_history(user_id, limit)

    async def close(self):
        """Close connections"""
        await self.client.close()
