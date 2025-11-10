#!/usr/bin/env python3
"""
Generate SVG screenshots of the FULL app layout (not just individual panels).

This shows how all components look together: header, left panel (visualizer + status),
right panel (activity feed), and footer.

Usage:
    python scripts/generate_full_app_svgs.py
    python scripts/generate_full_app_svgs.py --size 120x40
"""

import asyncio
import argparse
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.app import VoiceAssistantApp
from assistant.config import Config


async def generate_full_app_screenshot(output_dir: Path, terminal_size: tuple):
    """Generate screenshot of the complete app."""
    print(f"\n🖥️  Generating FULL APP screenshots ({terminal_size[0]}x{terminal_size[1]})...")

    # Create config
    config = Config()
    config.default_persona = "JARVIS"

    # Create app with all components
    personas_dir = Path(__file__).parent.parent / "personas"
    app = VoiceAssistantApp(config, personas_dir)

    async with app.run_test(size=terminal_size) as pilot:
        # Let app initialize
        await pilot.pause(1.0)

        # Take screenshot
        output_path = output_dir / f"full_app_{terminal_size[0]}x{terminal_size[1]}.svg"
        app.save_screenshot(str(output_path))
        print(f"  ✓ {output_path.name}")


async def main():
    parser = argparse.ArgumentParser(
        description="Generate SVG screenshots of FULL APP (all components together)",
    )
    parser.add_argument(
        "--size",
        default="80x30",
        help="Terminal size as WxH (default: 80x30)",
    )
    parser.add_argument(
        "--output",
        default="tmp/ai_review",
        help="Output directory (default: tmp/ai_review)",
    )

    args = parser.parse_args()

    # Parse terminal size
    try:
        width, height = map(int, args.size.split("x"))
        terminal_size = (width, height)
    except ValueError:
        print(f"❌ Invalid size format: {args.size}. Use WxH format (e.g., 80x30)")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n🎨 Generating FULL APP TUI screenshot in headless mode...")
    print(f"📁 Output directory: {output_dir.absolute()}")

    # Generate screenshot
    await generate_full_app_screenshot(output_dir, terminal_size)

    print(f"\n✅ Done! Generated screenshot in {output_dir}/")
    print(f"💡 Open in browser to see the complete app layout.")
    print(f"\nTo generate different sizes:")
    print(f"  python scripts/generate_full_app_svgs.py --size 120x40")
    print(f"  python scripts/generate_full_app_svgs.py --size 200x60")


if __name__ == "__main__":
    asyncio.run(main())
