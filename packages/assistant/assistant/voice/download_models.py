"""
Pre-download and cache Moshi MLX models.

This script downloads the required models from HuggingFace and caches them locally
so the first run of xswarm is fast. It also checks for updates periodically.
"""

import sys
from pathlib import Path
from huggingface_hub import hf_hub_download, HfApi
from datetime import datetime, timedelta
import json


# Model configuration
DEFAULT_REPO = "kyutai/moshiko-mlx-q8"
QUANTIZATION = 8  # 8-bit quantization

# Files to download
MODEL_FILES = [
    "model.q8.safetensors",
    "tokenizer-e351c8d8-checkpoint125.safetensors",
    "tokenizer_spm_32k_3.model",
]

# Update check cache
CACHE_DIR = Path.home() / ".cache" / "xswarm"
UPDATE_CHECK_FILE = CACHE_DIR / "last_model_check.json"
CHECK_INTERVAL_DAYS = 7  # Check for updates weekly


def should_check_for_updates() -> bool:
    """Check if we should look for model updates."""
    if not UPDATE_CHECK_FILE.exists():
        return True

    try:
        with open(UPDATE_CHECK_FILE) as f:
            data = json.load(f)
            last_check = datetime.fromisoformat(data["last_check"])
            return datetime.now() - last_check > timedelta(days=CHECK_INTERVAL_DAYS)
    except (json.JSONDecodeError, KeyError, ValueError):
        return True


def mark_update_check():
    """Record that we checked for updates."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(UPDATE_CHECK_FILE, "w") as f:
        json.dump({"last_check": datetime.now().isoformat()}, f)


def download_models(repo_id: str = DEFAULT_REPO, force: bool = False, quiet: bool = False):
    """
    Download and cache Moshi MLX models.

    Args:
        repo_id: HuggingFace repo ID
        force: Force re-download even if cached
        quiet: Suppress output
    """
    if not quiet:
        print(f"Downloading Moshi MLX models from {repo_id}...")
        print("This is a one-time download. Future runs will use cached models.\n")

    # Check for updates if needed
    check_updates = force or should_check_for_updates()

    for filename in MODEL_FILES:
        try:
            if not quiet:
                status = "Checking" if check_updates else "Using cached"
                print(f"{status} {filename}...")

            # Download (or verify cached version)
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                force_download=force,
                resume_download=True,
            )

            if not quiet:
                print(f"  ✓ {filename}")
        except Exception as e:
            print(f"  ✗ Failed to download {filename}: {e}", file=sys.stderr)
            return False

    # Mark that we checked for updates
    if check_updates:
        mark_update_check()

    if not quiet:
        print("\n✓ All models cached successfully!")
        print(f"Models will be checked for updates every {CHECK_INTERVAL_DAYS} days.")

    return True


def main():
    """CLI entry point for model download."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and cache Moshi MLX models for xSwarm voice assistant"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if models are cached"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output"
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"HuggingFace repo ID (default: {DEFAULT_REPO})"
    )

    args = parser.parse_args()

    success = download_models(
        repo_id=args.repo,
        force=args.force,
        quiet=args.quiet
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
