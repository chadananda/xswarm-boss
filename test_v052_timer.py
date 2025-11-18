#!/usr/bin/env python3
"""
Test v0.3.52: Timer-based event checking to fix async/threading deadlock.
"""
import subprocess
import time
import sys
import signal
from pathlib import Path

print("=" * 70)
print("Testing v0.3.52: Timer-Based Event Checking")
print("=" * 70)

# Clean old logs
for log_file in ["/tmp/xswarm_debug.log", "/tmp/moshi_text.log"]:
    try:
        Path(log_file).unlink()
    except:
        pass

print("\n[1/4] Launching TUI...")

# Launch the app
proc = subprocess.Popen(
    ["xswarm"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print(f"[2/4] TUI launched (PID: {proc.pid}). Waiting 30 seconds for full cycle...")

# Wait 30 seconds for full cycle
for i in range(30):
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
print("\n[3/4] Stopping TUI...")
proc.send_signal(signal.SIGINT)

try:
    exit_code = proc.wait(timeout=5)
except subprocess.TimeoutExpired:
    print("⚠️  Force kill...")
    proc.kill()
    proc.wait()

# Analyze debug log
print("\n[4/4] Analyzing debug log...")
print("=" * 70)

debug_log = Path("/tmp/xswarm_debug.log")
if not debug_log.exists():
    print("❌ No debug log found!")
    sys.exit(1)

log_content = debug_log.read_text()
lines = log_content.split("\n")

# Count timer ticks
timer_setup = [l for l in lines if "setting up timer-based polling" in l]
timer_started = [l for l in lines if "timer started, returning" in l]
timer_ticks = [l for l in lines if "Timer tick #" in l]
loading_detected = [l for l in lines if "loading_complete detected!" in l or "Loading complete!" in l]
audio_io_created = [l for l in lines if "AudioIO created" in l]
processing_ready_set = [l for l in lines if "processing_ready signal set" in l]
loop_iterations = [l for l in lines if "Loop iteration #" in l and "start" in l]
audio_generated = [l for l in lines if "Generated audio chunk" in l]

print(f"\nTimer setup: {len(timer_setup)}")
print(f"Timer started: {len(timer_started)}")
print(f"Timer ticks logged: {len(timer_ticks)}")
print(f"Loading detected: {len(loading_detected)}")
print(f"AudioIO created: {len(audio_io_created)}")
print(f"processing_ready set: {len(processing_ready_set)}")
print(f"Loop iterations: {len(loop_iterations)}")
print(f"Audio chunks generated: {len(audio_generated)}")

# Show last 30 lines of debug log
print("\n" + "=" * 70)
print("LAST 30 LINES OF DEBUG LOG:")
print("=" * 70)
for line in lines[-30:]:
    if line.strip():
        print(line)

# Check if timer mechanism works
if len(timer_setup) > 0 and len(timer_started) > 0:
    print("\n" + "=" * 70)
    print("✅ TIMER MECHANISM INITIALIZED!")
    print(f"   - Timer setup detected")
    print(f"   - Timer started successfully")

    if len(timer_ticks) > 0:
        print(f"✅ TIMER IS TICKING! ({len(timer_ticks)} ticks logged)")

        if len(loading_detected) > 0:
            print("✅ Loading completion detected by timer")

            if len(processing_ready_set) > 0:
                print("✅ processing_ready signal was set")

                if len(loop_iterations) > 0:
                    print(f"✅ Processing loop started ({len(loop_iterations)} iterations)")

                    if len(audio_generated) > 0:
                        print(f"✅ Audio generation working ({len(audio_generated)} chunks)")
                        print("\n🎉 SUCCESS: Full audio pipeline is working!")
                    else:
                        print("\n⚠️  Loop running but NO audio generated")
                else:
                    print("\n⚠️  processing_ready set but loop NEVER started")
            else:
                print("\n⚠️  processing_ready signal was NEVER set")
        else:
            print("\n⚠️  Timer ticking but loading completion NEVER detected")
            print("   (This might mean models are still loading - try waiting longer)")
    else:
        print("\n❌ Timer initialized but NO ticks logged!")
        print("   This suggests the timer callback is not being called")
    print("=" * 70)
else:
    print("\n" + "=" * 70)
    print("❌ TIMER MECHANISM FAILED TO INITIALIZE")
    if len(timer_setup) == 0:
        print("   - Timer setup code NEVER ran")
    if len(timer_started) == 0:
        print("   - Timer NEVER started")
    print("=" * 70)

print("\n✅ Test complete. Check findings above.")
sys.exit(0)
