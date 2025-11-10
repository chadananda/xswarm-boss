#!/usr/bin/env python3
"""
Download Vosk model for wake word detection.

Vosk models: https://alphacephei.com/vosk/models
We use vosk-model-small-en-us-0.15 (~40MB) for balance of size/accuracy.
"""

import urllib.request
import zipfile
from pathlib import Path
import sys


def download_vosk_model(
    model_name: str = "vosk-model-small-en-us-0.15",
    cache_dir: Path = None
):
    """
    Download and extract Vosk model.

    Args:
        model_name: Name of Vosk model to download
        cache_dir: Directory to store model (default: ~/.cache/vosk/)
    """
    if cache_dir is None:
        cache_dir = Path.home() / ".cache" / "vosk"

    cache_dir.mkdir(parents=True, exist_ok=True)
    model_dir = cache_dir / model_name

    # Check if already downloaded
    if model_dir.exists() and (model_dir / "am").exists():
        print(f"✅ Vosk model already downloaded: {model_dir}")
        return model_dir

    # Model URLs
    base_url = "https://alphacephei.com/vosk/models"
    model_url = f"{base_url}/{model_name}.zip"
    zip_path = cache_dir / f"{model_name}.zip"

    try:
        # Download
        print(f"Downloading Vosk model: {model_name}")
        print(f"URL: {model_url}")
        print("This may take a few minutes...")

        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")

        urllib.request.urlretrieve(model_url, zip_path, reporthook=progress)
        print("\n✅ Download complete")

        # Extract
        print(f"Extracting to {cache_dir}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(cache_dir)

        # Clean up zip
        zip_path.unlink()

        print(f"✅ Vosk model installed: {model_dir}")
        return model_dir

    except Exception as e:
        print(f"❌ Error downloading Vosk model: {e}")
        print(f"\nManual download:")
        print(f"  1. Download: {model_url}")
        print(f"  2. Extract to: {cache_dir}")
        sys.exit(1)


def main():
    """Download Vosk model"""
    print("=== Vosk Model Download ===\n")

    # Download small English model (good for wake words)
    model_dir = download_vosk_model()

    print(f"\n✅ Setup complete!")
    print(f"Model location: {model_dir}")
    print(f"\nUsage:")
    print(f'  from assistant.wake_word import WakeWordDetector')
    print(f'  detector = WakeWordDetector(')
    print(f'      model_path=Path("{model_dir}"),')
    print(f'      wake_word="jarvis"')
    print(f'  )')


if __name__ == "__main__":
    main()
