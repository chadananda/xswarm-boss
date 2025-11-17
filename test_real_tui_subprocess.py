#!/usr/bin/env python3
"""
Test real TUI by launching it as a subprocess and monitoring debug logs.
This avoids terminal corruption and import issues.
"""
import subprocess
import time
import sys
from pathlib import Path

def test_progress_bar_via_subprocess():
    """
    Launch the TUI as a subprocess, monitor debug log for progress messages.
    """
    print("=" * 70)
    print("Testing Progress Bar via Subprocess")
    print("=" * 70)

    debug_log = Path("/tmp/xswarm_debug.log")

    # Clean up old log
    if debug_log.exists():
        debug_log.unlink()

    print("\n[1/4] Launching TUI in subprocess...")

    # Launch the app
    proc = subprocess.Popen(
        [sys.executable, "-m", "assistant.main", "--debug"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent / "packages" / "assistant"
    )

    print(f"[2/4] TUI launched (PID: {proc.pid}). Monitoring for 30 seconds...")

    # Monitor for 30 seconds (enough time for Moshi to load)
    progress_snapshots = []

    for i in range(30):
        time.sleep(1)

        # Read debug log if it exists
        if debug_log.exists():
            try:
                log_content = debug_log.read_text()

                # Count progress messages
                progress_lines = [
                    line for line in log_content.split("\n")
                    if "Loading MOSHI" in line and "%" in line
                ]

                # Extract unique progress messages
                unique_progress = list(set(progress_lines))

                snapshot = {
                    "time": i,
                    "progress_count": len(unique_progress),
                    "progress_messages": unique_progress[:5]  # First 5
                }

                progress_snapshots.append(snapshot)

                if i % 5 == 0:
                    print(f"  t={i}s: {len(unique_progress)} unique progress messages")

            except Exception as e:
                pass  # Log might be being written

    # Kill the process
    print("\n[3/4] Stopping TUI...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Analyze results
    print("\n[4/4] Analyzing results...")
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    if not progress_snapshots:
        print("\n⚠️  WARNING: No snapshots captured (debug log not found)")
        return False

    max_progress = max(s["progress_count"] for s in progress_snapshots)
    final_snapshot = progress_snapshots[-1]

    print(f"\nMaximum unique progress messages seen: {max_progress}")

    if max_progress > 1:
        print(f"\n❌ FAILURE: Found {max_progress} different progress messages")
        print("\nThis indicates duplicate progress bars were created.")
        print("\nExamples:")
        for msg in final_snapshot["progress_messages"][:3]:
            print(f"  - {msg}")
        return False
    elif max_progress == 1:
        print("\n✅ SUCCESS: Only ONE progress message (no duplicates)")
        if final_snapshot["progress_messages"]:
            print(f"\n  Message: {final_snapshot['progress_messages'][0][:70]}...")
        return True
    else:
        print("\n⚠️  WARNING: No progress messages found")
        print("   Moshi might not have started loading yet")
        return False


if __name__ == "__main__":
    try:
        result = test_progress_bar_via_subprocess()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
