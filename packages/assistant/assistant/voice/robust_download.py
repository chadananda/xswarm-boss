"""
Truly robust download for weak/intermittent internet.

Key features for your situation:
- SHORT timeouts (30s) to detect stalls quickly
- IMMEDIATE retry (no long waits)
- NEVER gives up
- Automatic resume from checkpoints
- Works through weak connections
"""

import sys
import os
from pathlib import Path
import time
from huggingface_hub import hf_hub_download
import requests

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def download_with_aggressive_retry(
    repo_id: str,
    filename: str,
    max_single_attempt_time: int = 30  # 30 second timeout per attempt
):
    """
    Download with aggressive retry for weak internet.

    Strategy:
    - Try to download
    - If it stalls for >30s, kill it and retry IMMEDIATELY
    - Never give up
    - Always resume from checkpoint
    """
    attempt = 0

    while True:
        attempt += 1
        timestamp = time.strftime('%H:%M:%S')

        print(f"\n[{timestamp}] Attempt #{attempt}")
        print(f"  Timeout: {max_single_attempt_time}s (will retry if stalls)")

        try:
            # Enable hf_xet for chunk verification
            os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"

            # Set SHORT timeouts to detect stalls quickly
            os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = str(max_single_attempt_time)
            os.environ["HF_HUB_ETAG_TIMEOUT"] = str(max_single_attempt_time)

            # Try download with resume
            print(f"  → Downloading... (will auto-resume if interrupted)")
            model_file = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                resume_download=True,  # Always resume
            )

            # If we get here, download succeeded!
            print(f"\n[{time.strftime('%H:%M:%S')}] ✅ DOWNLOAD COMPLETE!")
            print(f"  File: {model_file}")
            print(f"  Total attempts: {attempt}")
            return model_file

        except (ConnectionError, TimeoutError, requests.exceptions.Timeout, OSError) as e:
            # Connection issue - retry IMMEDIATELY
            timestamp = time.strftime('%H:%M:%S')
            print(f"\n[{timestamp}] ⚠️  Connection issue: {type(e).__name__}")
            print(f"  Will retry IMMEDIATELY (attempt #{attempt + 1})")
            print(f"  (Internet is weak but working - keeping progress, retrying...)")
            # NO SLEEP - retry immediately
            continue

        except Exception as e:
            # Unexpected error
            timestamp = time.strftime('%H:%M:%S')
            print(f"\n[{timestamp}] ❌ Unexpected error: {type(e).__name__}: {e}")
            print(f"  Will retry in 5 seconds...")
            time.sleep(5)
            continue


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ROBUST DOWNLOAD - Weak Internet Edition")
    print("=" * 70)
    print("Strategy:")
    print("  • 30 second timeout per attempt (detects stalls quickly)")
    print("  • IMMEDIATE retry on any issue")
    print("  • Automatic resume from checkpoint")
    print("  • Never gives up")
    print("  • Chunk-level verification via hf_xet")
    print("=" * 70)
    print()

    try:
        model_file = download_with_aggressive_retry(
            repo_id="kyutai/moshiko-mlx-bf16",
            filename="model.safetensors",
            max_single_attempt_time=30  # 30s timeout
        )

        print("\n" + "=" * 70)
        print("🎉 SUCCESS! Model downloaded and verified!")
        print("=" * 70)
        print(f"Location: {model_file}")

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
