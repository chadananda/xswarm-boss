#!/usr/bin/env python3
"""
Test v0.3.46 debug logging to understand why processing loop stops.
"""
import subprocess
import time
import sys
import signal
from pathlib import Path

print("=" * 70)
print("Testing v0.3.46: Debug Logging for Processing Loop")
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

print(f"[2/4] TUI launched (PID: {proc.pid}). Waiting 30 seconds for Moshi to load and process audio...")

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

# Count iterations
iteration_lines = [l for l in lines if "Loop iteration #" in l and "start" in l]
step_frame_calls = [l for l in lines if "About to call moshi_bridge.step_frame()" in l]
step_frame_returns = [l for l in lines if "step_frame() returned successfully" in l]
audio_generated = [l for l in lines if "Generated audio chunk" in l]
loop_exit = [l for l in lines if "Processing loop EXITED" in l]

print(f"\nIterations started: {len(iteration_lines)}")
print(f"step_frame() calls: {len(step_frame_calls)}")
print(f"step_frame() returns: {len(step_frame_returns)}")
print(f"Audio chunks generated: {len(audio_generated)}")
print(f"Loop exit messages: {len(loop_exit)}")

# Show last 20 lines of debug log
print("\n" + "=" * 70)
print("LAST 20 LINES OF DEBUG LOG:")
print("=" * 70)
for line in lines[-20:]:
    if line.strip():
        print(line)

# Check for crashes
if len(step_frame_calls) > len(step_frame_returns):
    print("\n" + "=" * 70)
    print("⚠️  CRASH DETECTED: step_frame() called but didn't return!")
    print(f"   Calls: {len(step_frame_calls)}, Returns: {len(step_frame_returns)}")
    print("   This indicates an MLX crash or segfault.")
    print("=" * 70)

if loop_exit:
    print("\n" + "=" * 70)
    print("✅ Loop exited gracefully (logged exit)")
    for line in loop_exit:
        print(f"   {line}")
    print("=" * 70)
elif iteration_lines:
    print("\n" + "=" * 70)
    print("⚠️  Loop stopped WITHOUT logging exit")
    print(f"   Last iteration: #{len(iteration_lines)}")
    print("   This suggests a silent crash or thread death.")
    print("=" * 70)

print("\n✅ Test complete. Check findings above.")
sys.exit(0)
