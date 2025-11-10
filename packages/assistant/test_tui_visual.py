#!/usr/bin/env python3
"""
Visual testing script for TUI at multiple terminal sizes.
Generates SVG screenshots that Claude can read and analyze.
"""

import asyncio
from pathlib import Path
from assistant.dashboard.app import VoiceAssistantApp
from assistant.config import Config


async def capture_at_size(width: int, height: int, output_path: Path, config, personas_dir):
    """Capture TUI screenshot at specific size"""
    print(f"Capturing TUI at {width}x{height}...")

    # Create app
    app = VoiceAssistantApp(config, personas_dir)

    # Run in test mode with specific size
    async with app.run_test(size=(width, height)) as pilot:
        # Wait a moment for rendering to stabilize
        await pilot.pause(0.5)

        # Save screenshot
        app.save_screenshot(str(output_path))
        print(f"  ✓ Saved to {output_path}")


async def main():
    """Generate screenshots at multiple sizes"""
    # Ensure tmp directory exists
    tmp_dir = Path(__file__).parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    print("\n" + "="*60)
    print("TUI VISUAL TESTING - Multiple Terminal Sizes")
    print("="*60 + "\n")

    # Load config and personas once
    try:
        print("Loading configuration...")
        config = Config.load_from_file()
        personas_dir = Path(__file__).parent.parent / "personas"
        print(f"  Config loaded: {config.device} device")
        print(f"  Personas dir: {personas_dir}")
        print(f"  Personas dir exists: {personas_dir.exists()}\n")
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test sizes: (width, height)
    sizes = [
        (40, 15, "small"),      # Currently shows "TERMINAL TOO SMALL"
        (60, 20, "medium"),     # Should be functional but compact
        (80, 30, "large"),      # Should be comfortable
        (120, 40, "xlarge"),    # Should be full-featured
    ]

    for width, height, label in sizes:
        output_path = tmp_dir / f"tui_{label}_{width}x{height}.svg"
        try:
            await capture_at_size(width, height, output_path, config, personas_dir)
        except Exception as e:
            print(f"  ✗ Error capturing {width}x{height}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("Screenshots saved to:")
    print(f"  {tmp_dir}/")
    print("\nClaude can now read these SVG files with:")
    print(f'  Read: {tmp_dir}/tui_*.svg')
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
