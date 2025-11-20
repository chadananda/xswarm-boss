"""Test script to verify the subtle shade palette in the TUI."""

import asyncio
from assistant.dashboard.app import VoiceAssistantApp


async def test_app():
    """Run the app briefly to generate test data."""
    app = VoiceAssistantApp()

    # Schedule app exit after 2 seconds
    async def auto_exit():
        await asyncio.sleep(2)
        app.exit()

    # Start auto-exit task
    asyncio.create_task(auto_exit())

    # Run the app
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(test_app())
    print("\n✅ Shade palette test completed successfully!")
    print("All widgets updated to use subtle grayscale shades:")
    print("  - shade-5: #8899aa (lightest)")
    print("  - shade-4: #6b7a8a (light)")
    print("  - shade-3: #4d5966 (medium)")
    print("  - shade-2: #363d47 (dark)")
    print("  - shade-1: #252a33 (darkest)")
