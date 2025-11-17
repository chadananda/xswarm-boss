#!/usr/bin/env python3
"""
Real TUI test using Textual Pilot to verify progress bar behavior.
This actually runs the TUI and inspects the ActivityFeed widget.
"""
import asyncio
from textual.pilot import Pilot
from assistant.dashboard.app import VoiceAssistantApp


async def test_progress_bar():
    """Test that progress updates don't create duplicates"""
    app = VoiceAssistantApp()

    async with app.run_test() as pilot:
        # Wait for app to initialize
        await pilot.pause(2)

        # Get the activity feed widget
        activity = app.query_one("#activity")

        print(f"\n=== Initial State ===")
        print(f"Messages count: {len(activity.messages)}")
        for i, msg in enumerate(activity.messages, 1):
            print(f"  {i}. [{msg['type']}] {msg['message'][:60]}...")

        # Wait for Moshi to start loading (this triggers the timer)
        print(f"\n=== Waiting 5 seconds for Moshi loading to start ===")
        await pilot.pause(5)

        print(f"\nMessages count: {len(activity.messages)}")
        for i, msg in enumerate(activity.messages, 1):
            print(f"  {i}. [{msg['type']}] {msg['message'][:60]}...")

        # Wait more to see if duplicates appear
        print(f"\n=== Waiting another 10 seconds ===")
        await pilot.pause(10)

        print(f"\nMessages count: {len(activity.messages)}")
        system_messages = [m for m in activity.messages if m['type'] == 'system' and 'Loading MOSHI' in m['message']]
        print(f"SYSTEM messages with 'Loading MOSHI': {len(system_messages)}")

        for i, msg in enumerate(activity.messages, 1):
            print(f"  {i}. [{msg['type']}] {msg['message'][:70]}...")

        # Verify
        print(f"\n=== VERDICT ===")
        if len(system_messages) <= 1:
            print(f"✓ SUCCESS: Only {len(system_messages)} progress message (no duplicates)")
            return True
        else:
            print(f"✗ FAILURE: Found {len(system_messages)} progress messages (expected 1)")
            for msg in system_messages:
                print(f"    - {msg['message']}")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_progress_bar())
    exit(0 if result else 1)
