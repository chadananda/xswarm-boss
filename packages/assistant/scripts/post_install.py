"""
Post-installation script to download Moshi models.

This runs automatically after pip install to cache models.
"""

import sys


def main():
    """Run post-install tasks."""
    print("\n" + "="*60)
    print("xSwarm Voice Assistant - Post-Install Setup")
    print("="*60 + "\n")

    # Try to import and run model download
    try:
        from assistant.voice.download_models import download_models

        print("Downloading Moshi MLX models...")
        print("This ensures fast startup on first run.\n")

        success = download_models(quiet=False)

        if success:
            print("\n" + "="*60)
            print("✓ Installation complete! Run 'xswarm --debug' to start.")
            print("="*60 + "\n")
        else:
            print("\n⚠️  Model download failed. You can retry with:")
            print("    xswarm-download-models")
            print("\nxSwarm will still work but may download on first run.\n")

    except ImportError:
        print("⚠️  Could not import model downloader.")
        print("Models will be downloaded on first run instead.\n")
    except Exception as e:
        print(f"⚠️  Unexpected error during model download: {e}")
        print("Models will be downloaded on first run instead.\n")


if __name__ == "__main__":
    main()
