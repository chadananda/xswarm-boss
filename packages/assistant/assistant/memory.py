"""
Memory Manager for conversation history and context.

Provides:
- Message storage and retrieval
- Conversation history management
- Integration with server memory API (when available)
- Fallback to in-memory storage
"""

import httpx
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class MemoryManager:
    """
    Manages conversation memory with fallback support.

    Tries to use server API first, falls back to in-memory storage.
    """

    def __init__(self, server_url: str = "http://localhost:3000", max_history: int = 100):
        """
        Initialize memory manager.

        Args:
            server_url: URL of memory server API
            max_history: Maximum messages to keep in memory
        """
        self.server_url = server_url
        self.max_history = max_history
        self.client: Optional[httpx.AsyncClient] = None
        self.server_available = False

        # In-memory fallback storage
        self._memory_store: Dict[str, List[Dict[str, Any]]] = {}

    async def initialize(self):
        """Initialize HTTP client and check server availability."""
        self.client = httpx.AsyncClient(timeout=5.0)

        # Check if server is available
        try:
            response = await self.client.get(f"{self.server_url}/health")
            self.server_available = response.status_code == 200
            if self.server_available:
                print("✅ Memory server connected")
        except Exception:
            print("⚠️  Memory server unavailable, using in-memory storage")
            self.server_available = False

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()

    async def store_message(
        self,
        user_id: str,
        message: str,
        role: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a conversation message.

        Args:
            user_id: User identifier
            message: Message text
            role: "user" or "assistant"
            metadata: Optional metadata (persona, tools used, etc.)

        Returns:
            Message ID
        """
        timestamp = datetime.now().isoformat()
        message_id = f"{user_id}-{timestamp}"

        message_data = {
            "id": message_id,
            "user_id": user_id,
            "message": message,
            "role": role,
            "timestamp": timestamp,
            "metadata": metadata or {}
        }

        if self.server_available:
            try:
                response = await self.client.post(
                    f"{self.server_url}/api/memory/messages",
                    json=message_data
                )
                if response.status_code == 200:
                    return message_id
            except Exception as e:
                print(f"⚠️  Server storage failed: {e}, using in-memory")

        # Fallback: in-memory storage
        if user_id not in self._memory_store:
            self._memory_store[user_id] = []

        self._memory_store[user_id].append(message_data)

        # Keep only recent messages
        if len(self._memory_store[user_id]) > self.max_history:
            self._memory_store[user_id] = self._memory_store[user_id][-self.max_history:]

        return message_id

    async def get_context(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent conversation context.

        Args:
            user_id: User identifier
            limit: Maximum messages to retrieve

        Returns:
            List of message dictionaries
        """
        if self.server_available:
            try:
                response = await self.client.get(
                    f"{self.server_url}/api/memory/messages/{user_id}",
                    params={"limit": limit}
                )
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                print(f"⚠️  Server retrieval failed: {e}, using in-memory")

        # Fallback: in-memory retrieval
        messages = self._memory_store.get(user_id, [])
        return messages[-limit:] if messages else []

    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 20
    ) -> str:
        """
        Get conversation history formatted for LLM context.

        Args:
            user_id: User identifier
            limit: Maximum messages to include

        Returns:
            Formatted conversation history string
        """
        messages = await self.get_context(user_id, limit)

        if not messages:
            return ""

        history_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("message", "")
            metadata = msg.get("metadata", {})

            if role == "assistant" and metadata.get("persona"):
                persona = metadata["persona"]
                history_lines.append(f"{persona}: {text}")
            elif role == "user":
                history_lines.append(f"User: {text}")
            else:
                history_lines.append(f"{role}: {text}")

        return "\n".join(history_lines)

    async def clear_history(self, user_id: str):
        """Clear conversation history for a user."""
        if self.server_available:
            try:
                await self.client.delete(
                    f"{self.server_url}/api/memory/messages/{user_id}"
                )
            except Exception:
                pass

        # Clear in-memory storage
        if user_id in self._memory_store:
            del self._memory_store[user_id]
