#!/usr/bin/env python3
"""
Test memory client integration.
"""

import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.memory import MemoryManager


async def main():
    print("=== Memory Client Test ===\n")

    # Initialize memory manager
    print("Initializing memory manager...")
    manager = MemoryManager(
        server_url="http://localhost:3000"
    )

    await manager.initialize()

    # Test user ID
    user_id = "test-user-123"

    # Store some messages
    print(f"\nStoring messages for user: {user_id}")

    await manager.store_message(
        user_id=user_id,
        message="Hello, can you help me with my project?",
        role="user"
    )

    await manager.store_message(
        user_id=user_id,
        message="Of course! I'd be happy to help. What project are you working on?",
        role="assistant",
        metadata={"persona": "JARVIS"}
    )

    await manager.store_message(
        user_id=user_id,
        message="I'm building a voice assistant with MOSHI",
        role="user"
    )

    print("✅ Messages stored")

    # Retrieve context
    print(f"\nRetrieving conversation context...")
    context = await manager.get_context(user_id, limit=10)

    print(f"Found {len(context)} messages:")
    for msg in context:
        role = msg.get("role", "unknown")
        text = msg.get("message", "")
        timestamp = msg.get("timestamp", "")
        print(f"  [{role}] {text[:60]}... ({timestamp})")

    # Cleanup
    await manager.close()

    print("\n=== Test complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
