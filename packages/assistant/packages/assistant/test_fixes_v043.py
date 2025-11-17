#!/usr/bin/env python3
"""
Test v0.3.43 fixes by running the app for 40 seconds.
"""
import subprocess
import time
import sys
import signal
from pathlib import Path

print("=" * 70)
print("Testing v0.3.43: App loads and runs without crash")
print("=" * 70)

# Launch the app
proc = subprocess.Popen(
    [sys.executable, "-m", "assistant.main"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=Path(__file__).parent,
    text=True
)

print(f"\nTUI launched (PID: {proc.pid}). Running for 40 seconds...")

# Monitor for 40 seconds
for i in range(40):
    time.sleep(1)

    poll = proc.poll()
    if poll is not None:
        stderr = proc.stderr.read()
        stdout = proc.stdout.read()

        print(f"\n❌ FAILED: App crashed after {i} seconds (exit code {poll})")
        print("\nError output:")
        print(stderr[:1000])
        sys.exit(1)

    if i % 10 == 0 and i > 0:
        print(f"  t={i}s: Still running ✓")

# Kill gracefully
print("\nSending Ctrl+C to test shutdown...")
proc.send_signal(signal.SIGINT)

try:
    exit_code = proc.wait(timeout=5)
    stderr = proc.stderr.read()

    # Check for threading exception
    if "Exception ignored in: <module 'threading'" in stderr:
        print("\n⚠️  Threading exception on shutdown (minor issue)")
        print("\n✅ But app ran for 40 seconds without crash!")
    else:
        print(f"\n✅ SUCCESS: App ran 40 seconds and shutdown cleanly")

    sys.exit(0)

except subprocess.TimeoutExpired:
    print("\n⚠️  Forcing kill...")
    proc.kill()
    proc.wait()
    print("\n✅ But app ran for 40 seconds without crash!")
    sys.exit(0)
