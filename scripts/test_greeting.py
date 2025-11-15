#!/usr/bin/env python3
"""Test Moshi greeting generation to debug crash."""

import sys
import asyncio
sys.path.insert(0, 'packages/assistant')

from assistant.voice.moshi_mlx import MoshiBridge
from assistant.phone.twilio_voice_bridge import TwilioVoiceBridge
from assistant.services.persona_manager import PersonaManager
from assistant.services.memory import MemoryService

async def test_greeting():
    """Test greeting generation."""
    print("=" * 60)
    print("Testing Moshi Greeting Generation")
    print("=" * 60)
    print()

    # Initialize components
    print("1. Loading Moshi...")
    moshi = MoshiBridge(quality='q4')
    print("   ✓ Moshi loaded")
    print()

    print("2. Creating TwilioVoiceBridge...")
    try:
        # Initialize memory and persona manager
        memory_service = MemoryService()
        persona_manager = PersonaManager()

        bridge = TwilioVoiceBridge(
            moshi=moshi,
            persona_manager=persona_manager,
            memory_service=memory_service,
            call_sid="TEST_CALL_SID",
            from_number="+19167656913",
            to_number="+18447472899"
        )
        print("   ✓ Bridge created")
        print()

        print("3. Initializing bridge...")
        await bridge.initialize()
        print("   ✓ Bridge initialized")
        print()

        print("4. Generating greeting...")
        greeting_audio = await bridge.generate_and_send_greeting()
        print(f"   ✓ Greeting generated: {len(greeting_audio) if greeting_audio else 0} bytes")
        print()

        print("=" * 60)
        print("✅ SUCCESS - Greeting generation works!")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        print("=" * 60)
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_greeting())
