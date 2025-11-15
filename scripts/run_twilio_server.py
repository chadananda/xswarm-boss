#!/usr/bin/env python3
"""
Run Twilio Media Streams WebSocket server for Moshi phone calls.

Usage:
    python scripts/run_twilio_server.py [--port 5000] [--host 0.0.0.0]
"""

import asyncio
import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/assistant"))

from assistant.phone import MediaStreamsServer, TwilioVoiceBridge
from assistant.personas.manager import PersonaManager
from assistant.memory import MemoryManager
from assistant.config import Config
from assistant.voice.moshi_mlx import MoshiBridge

# Global Moshi instance (loaded once at startup, reused for all calls)
MOSHI = None


async def create_bridge(call_sid: str, from_number: str, to_number: str) -> TwilioVoiceBridge:
    """
    Factory function to create TwilioVoiceBridge for each call.

    Args:
        call_sid: Twilio call SID
        from_number: Caller's phone number
        to_number: Recipient's phone number

    Returns:
        Initialized TwilioVoiceBridge instance
    """
    # Load config
    config = Config()

    # Load personas
    personas_dir = Path(__file__).parent.parent / "packages/personas"
    persona_manager = PersonaManager(personas_dir=personas_dir)

    # Initialize memory
    memory_manager = MemoryManager()

    # Create bridge with pre-loaded Moshi instance
    bridge = TwilioVoiceBridge(
        call_sid=call_sid,
        from_number=from_number,
        to_number=to_number,
        persona_manager=persona_manager,
        memory_manager=memory_manager,
        config=config,
        moshi=MOSHI,  # Use pre-loaded global Moshi instance
        on_state_change=lambda state: print(f"[Call {call_sid[-8:]}] State: {state}"),
    )

    return bridge


async def main():
    """Run the Media Streams server."""
    global MOSHI

    import argparse
    import time

    parser = argparse.ArgumentParser(description="Twilio Media Streams server for Moshi")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--quality", default="q8", choices=["q4", "q8", "bf16"], help="Moshi quality (default: q8)")
    args = parser.parse_args()

    print("=" * 60)
    print("🎙️  Twilio Media Streams Server - Moshi Voice Calls")
    print("=" * 60)
    print()

    # Pre-load Moshi BEFORE starting server
    print(f"🚀 Loading Moshi ({args.quality})...")
    start = time.time()
    MOSHI = MoshiBridge(quality=args.quality)
    elapsed = time.time() - start
    print(f"✅ Moshi loaded in {elapsed:.1f}s")
    print()

    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"WebSocket URL: ws://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print()
    print("⚠️  Make sure to expose this server via ngrok or deploy to cloud")
    print("   Twilio requires wss:// (secure WebSocket)")
    print()
    print("   Example with ngrok:")
    print(f"   $ ngrok http {args.port}")
    print("   Then update Twilio webhook to: wss://YOUR-NGROK-URL")
    print()
    print("=" * 60)
    print()

    # Create server
    server = MediaStreamsServer(
        host=args.host,
        port=args.port,
        bridge_factory=create_bridge,
    )

    # Start server
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n\n❌ Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
