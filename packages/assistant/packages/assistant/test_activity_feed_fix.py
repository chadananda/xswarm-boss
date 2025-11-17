#!/usr/bin/env python3
"""
Test ActivityFeed widget directly without running full TUI.
This simulates what happens during Moshi loading.
"""
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from assistant.dashboard.widgets.activity_feed import ActivityFeed


def test_progress_updates():
    """
    Simulate the exact scenario from app.py:
    1. Create initial progress message and capture ID
    2. Add some other messages (like "Loaded 10 personas")
    3. Update progress message by ID multiple times
    4. Verify only ONE progress message exists
    """
    print("=" * 60)
    print("Testing ActivityFeed progress update behavior")
    print("=" * 60)

    feed = ActivityFeed(max_messages=100)

    # Step 1: Add initial progress message (simulating line 677 in app.py)
    print("\n[Step 1] Adding initial progress message...")
    progress_message_id = feed.add_message("Initializing voice models...", "system")
    print(f"  ✓ Created message ID: {progress_message_id}")
    print_messages(feed)

    # Step 2: Add some other messages (simulating persona loading, etc.)
    print("\n[Step 2] Adding other system messages...")
    feed.add_message("Loaded 10 personas", "info")
    feed.add_message("Memory initialized", "info")
    feed.add_message("GPU: Apple Silicon (MPS)", "info")
    print_messages(feed)

    # Step 3: Update progress message by ID (simulating timer callback)
    print("\n[Step 3] Updating progress message by ID (like timer does)...")

    # Simulate 10 progress updates (like the timer firing)
    for i in range(10):
        pct = 5 + (i * 10)  # 5%, 15%, 25%, ..., 95%
        bar_width = 20
        filled = int(bar_width * pct / 100)
        empty = bar_width - filled
        bar = "█" * filled + "░" * empty
        progress_msg = f"[{bar}] {pct}% - Loading MOSHI (q8) - {i}s"

        feed.update_message_by_id(progress_message_id, progress_msg, "system")
        time.sleep(0.05)  # Simulate time passing

    print_messages(feed)

    # Step 4: Verify results
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    system_messages = [m for m in feed.messages if m['type'] == 'system' and 'Loading MOSHI' in m['message']]

    print(f"\nTotal messages: {len(feed.messages)}")
    print(f"SYSTEM messages containing 'Loading MOSHI': {len(system_messages)}")

    if len(system_messages) == 1:
        print("\n✅ SUCCESS: Only ONE progress message (no duplicates)")
        print(f"   Message: {system_messages[0]['message'][:70]}...")
        return True
    else:
        print(f"\n❌ FAILURE: Found {len(system_messages)} progress messages (expected 1)")
        for idx, msg in enumerate(system_messages, 1):
            print(f"   {idx}. {msg['message']}")
        return False


def print_messages(feed):
    """Print current state of feed"""
    print(f"  Current messages ({len(feed.messages)} total):")
    for msg in feed.messages:
        msg_preview = msg['message'][:60] + "..." if len(msg['message']) > 60 else msg['message']
        print(f"    [{msg['id']:03d}] [{msg['type']:7s}] {msg_preview}")


if __name__ == "__main__":
    success = test_progress_updates()
    sys.exit(0 if success else 1)
