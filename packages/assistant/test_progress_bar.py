#!/usr/bin/env python3
"""
Test script to verify progress bar behavior without running full TUI.
This simulates the timer callback logic to check for duplicate messages.
"""
import sys
import time
from assistant.dashboard.widgets.activity_feed import ActivityFeed


class MockApp:
    """Mock Textual app for testing"""
    def __init__(self):
        self.activity_feed = ActivityFeed()

    def query_one(self, selector, widget_type):
        return self.activity_feed


def test_progress_updates():
    """Test that progress updates modify existing message, not create duplicates"""
    print("Testing progress bar update logic...")

    app = MockApp()
    activity = app.activity_feed

    # Simulate the initialize_moshi flow
    print("\n1. Add 'Initializing voice models...' message")
    activity.add_message("Initializing voice models...", "info")
    print(f"   Messages count: {len(activity.messages)}")
    print(f"   Last message: {activity.messages[-1]['message']}")

    # Simulate timer callbacks (what should happen)
    progress_message_added = False
    moshi_quality = "q8"

    print("\n2. First timer tick (should UPDATE existing message, not add)")
    progress_counter = 0
    elapsed_seconds = progress_counter // 10
    pct = 35  # Simulate progress
    bar = "███████░░░░░░░░░░░░░"
    progress_msg = f"[{bar}] {pct}% - Loading MOSHI ({moshi_quality}) - {elapsed_seconds}s"

    if not progress_message_added:
        # WRONG: This adds a NEW message
        # activity.add_message(progress_msg, "system")
        # progress_message_added = True

        # RIGHT: Should update the last message
        activity.update_last_message(progress_msg, "system")
        progress_message_added = True

    print(f"   Messages count: {len(activity.messages)}")
    print(f"   Last message: {activity.messages[-1]['message']}")

    print("\n3. Second timer tick (should UPDATE same message)")
    progress_counter = 50
    elapsed_seconds = progress_counter // 10
    pct = 85
    bar = "█████████████████░░░"
    progress_msg = f"[{bar}] {pct}% - Loading MOSHI ({moshi_quality}) - {elapsed_seconds}s"

    activity.update_last_message(progress_msg, "system")

    print(f"   Messages count: {len(activity.messages)}")
    print(f"   Last message: {activity.messages[-1]['message']}")

    # Verify results
    print("\n" + "="*60)
    if len(activity.messages) == 1:
        print("✓ SUCCESS: Only ONE message (no duplicates)")
        print(f"  Final message: {activity.messages[-1]['message']}")
        print(f"  Message type: {activity.messages[-1]['type']}")
        return True
    else:
        print(f"✗ FAILURE: Found {len(activity.messages)} messages (expected 1)")
        for i, msg in enumerate(activity.messages, 1):
            print(f"  {i}. [{msg['type']}] {msg['message']}")
        return False


def test_current_implementation():
    """Test what the NEW FIXED code does"""
    print("\n\n" + "="*60)
    print("Testing NEW FIXED implementation (always update_last_message)")
    print("="*60)

    app = MockApp()
    activity = app.activity_feed

    # Initial message
    activity.add_message("Initializing voice models...", "info")
    print(f"After init message: {len(activity.messages)} messages")

    # Simulate NEW FIXED timer callback logic
    moshi_quality = "q8"

    # First tick
    print("\nFirst timer tick:")
    progress_counter = 0
    elapsed_seconds = progress_counter // 10
    pct = 35
    bar = "███████░░░░░░░░░░░░░"
    progress_msg = f"[{bar}] {pct}% - Loading MOSHI ({moshi_quality}) - {elapsed_seconds}s"

    # NEW: ALWAYS call update_last_message()
    activity.update_last_message(progress_msg, "system")

    print(f"  Messages count: {len(activity.messages)}")
    for i, msg in enumerate(activity.messages, 1):
        print(f"    {i}. [{msg['type']}] {msg['message'][:50]}...")

    # Second tick
    print("\nSecond timer tick:")
    progress_counter = 50
    elapsed_seconds = progress_counter // 10
    pct = 85
    bar = "█████████████████░░░"
    progress_msg = f"[{bar}] {pct}% - Loading MOSHI ({moshi_quality}) - {elapsed_seconds}s"

    activity.update_last_message(progress_msg, "system")

    print(f"  Messages count: {len(activity.messages)}")
    for i, msg in enumerate(activity.messages, 1):
        print(f"    {i}. [{msg['type']}] {msg['message'][:50]}...")

    print("\n" + "="*60)
    if len(activity.messages) == 1:
        print("✓ SUCCESS: Fixed implementation keeps only 1 message")
        print("  Reason: Always calls update_last_message(), never add_message()")
        return True
    else:
        print(f"✗ FAILURE: {len(activity.messages)} messages (expected 1)")
        return False


if __name__ == "__main__":
    # Test correct behavior
    correct = test_progress_updates()

    # Test current buggy behavior
    current_buggy = test_current_implementation()

    print("\n\n" + "="*60)
    print("CONCLUSION")
    print("="*60)
    print("The fix should ALWAYS call update_last_message(), never add_message()")
    print("This will replace 'Initializing voice models...' with the progress bar")
    sys.exit(0 if correct else 1)
