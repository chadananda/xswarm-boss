#!/usr/bin/env python3
"""
Programmatically test the TUI without displaying output to terminal.
Uses Textual's run_test() context manager to run TUI headlessly.
"""
import asyncio
import sys
from pathlib import Path

# Ensure we can import the app
sys.path.insert(0, str(Path(__file__).parent))

async def test_progress_bar_in_real_tui():
    """
    Test the actual TUI's progress bar behavior during Moshi loading.
    This runs the TUI in headless mode and inspects the ActivityFeed.
    """
    print("=" * 70)
    print("Testing Progress Bar in Real TUI (Headless Mode)")
    print("=" * 70)

    # Import here to avoid early initialization
    from assistant.dashboard.app import VoiceAssistantApp
    from assistant.dashboard.widgets.activity_feed import ActivityFeed

    print("\n[1/4] Initializing TUI in headless mode...")
    app = VoiceAssistantApp()

    try:
        async with app.run_test() as pilot:
            print("[2/4] TUI initialized. Waiting for widgets to mount...")
            await pilot.pause(2)

            # Get the activity feed widget
            try:
                activity = app.query_one("#activity", ActivityFeed)
                print(f"[3/4] Activity feed found. Waiting for Moshi to start loading...")
            except Exception as e:
                print(f"❌ FAILED: Could not find activity feed widget: {e}")
                return False

            # Wait for Moshi loading to begin and progress
            # The timer fires every 0.1s, so 15 seconds = 150 ticks
            # Moshi loading takes ~30 seconds typically
            print("[4/4] Monitoring activity feed for 20 seconds...")

            snapshots = []
            for i in range(20):  # Check every second for 20 seconds
                await pilot.pause(1)

                # Capture current state
                messages = list(activity.messages)
                progress_messages = [
                    m for m in messages
                    if m['type'] == 'system' and 'Loading MOSHI' in m['message']
                ]

                snapshot = {
                    'time': i,
                    'total_messages': len(messages),
                    'progress_count': len(progress_messages),
                    'progress_messages': [m['message'][:60] for m in progress_messages]
                }
                snapshots.append(snapshot)

                if i % 5 == 0:  # Print every 5 seconds
                    print(f"  t={i}s: {len(messages)} total messages, "
                          f"{len(progress_messages)} progress messages")

            # Analyze results
            print("\n" + "=" * 70)
            print("ANALYSIS")
            print("=" * 70)

            max_progress_count = max(s['progress_count'] for s in snapshots)
            final_snapshot = snapshots[-1]

            print(f"\nMaximum progress messages seen: {max_progress_count}")
            print(f"Final state: {final_snapshot['total_messages']} total messages")

            if max_progress_count > 1:
                print(f"\n❌ FAILURE: Found {max_progress_count} progress messages")
                print("\nDuplicate messages detected at:")
                for snap in snapshots:
                    if snap['progress_count'] > 1:
                        print(f"  t={snap['time']}s: {snap['progress_count']} messages:")
                        for msg in snap['progress_messages']:
                            print(f"    - {msg}...")
                return False
            elif max_progress_count == 1:
                print("\n✅ SUCCESS: Only ONE progress message (no duplicates)")

                # Find a snapshot with the progress message
                for snap in snapshots:
                    if snap['progress_count'] == 1:
                        print(f"  Example at t={snap['time']}s: {snap['progress_messages'][0]}...")
                        break
                return True
            else:
                print("\n⚠️  WARNING: No progress messages found")
                print("   This might mean Moshi didn't start loading yet")
                return False

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(test_progress_bar_in_real_tui())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
