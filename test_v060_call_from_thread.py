#!/usr/bin/env python3
"""
Test v0.3.60: call_from_thread() approach to fix async/threading deadlock.
Background thread now notifies app directly instead of polling.
"""
import subprocess
import time
import sys
import signal
from pathlib import Path

print("=" * 70)
print("Testing v0.3.60: call_from_thread() Background Thread Notification")
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

# Count events
setup_complete = [l for l in lines if "setup complete, returning" in l]
message_posted = [l for l in lines if "post LoadingComplete message" in l or "LoadingComplete message posted" in l]
handler_invoked = [l for l in lines if "on_loading_complete() handling LoadingComplete message" in l]
moshi_assigned = [l for l in lines if "Moshi bridge assigned successfully" in l]
lm_assigned = [l for l in lines if "LM generator assigned" in l]
audio_io_created = [l for l in lines if "AudioIO created" in l]
processing_ready_set = [l for l in lines if "processing_ready signal set" in l]
loop_iterations = [l for l in lines if "Loop iteration #" in l and "start" in l]
audio_generated = [l for l in lines if "Generated audio chunk" in l]

print(f"\nInitialization setup complete: {len(setup_complete)}")
print(f"LoadingComplete message posted: {len(message_posted)}")
print(f"Handler invoked: {len(handler_invoked)}")
print(f"Moshi bridge assigned: {len(moshi_assigned)}")
print(f"LM generator assigned: {len(lm_assigned)}")
print(f"AudioIO created: {len(audio_io_created)}")
print(f"processing_ready set: {len(processing_ready_set)}")
print(f"Loop iterations: {len(loop_iterations)}")
print(f"Audio chunks generated: {len(audio_generated)}")

# Show last 40 lines of debug log
print("\n" + "=" * 70)
print("LAST 40 LINES OF DEBUG LOG:")
print("=" * 70)
for line in lines[-40:]:
    if line.strip():
        print(line)

# Check if message mechanism works
if len(setup_complete) > 0:
    print("\n" + "=" * 70)
    print("✅ INITIALIZATION SETUP COMPLETED")

    if len(message_posted) > 0:
        print("✅ LoadingComplete message WAS POSTED from background thread")

        if len(handler_invoked) > 0:
            print("✅ Message handler WAS INVOKED in main thread")

            if len(moshi_assigned) > 0 and len(lm_assigned) > 0:
                print("✅ Models assigned successfully")

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
                print("\n⚠️  Models were NOT assigned")
        else:
            print("\n⚠️  Message handler was NEVER invoked")
            print("   (This means post_message() didn't deliver the message)")
    else:
        print("\n⚠️  LoadingComplete message was NEVER posted")
        print("   (This means models never finished loading)")
    print("=" * 70)
else:
    print("\n" + "=" * 70)
    print("❌ INITIALIZATION NEVER COMPLETED")
    print("=" * 70)

print("\n✅ Test complete. Check findings above.")
sys.exit(0)
