#!/usr/bin/env python3
"""
Generate SVG screenshots for AI review without running full test suite.

This script generates SVG screenshots of TUI components in headless mode
(no terminal corruption). Perfect for AI to review visual output during development.

Usage:
    python scripts/generate_test_svgs.py                    # Generate all
    python scripts/generate_test_svgs.py --component voice  # Only voice visualizer
    python scripts/generate_test_svgs.py --component chat   # Only chat panel
    python scripts/generate_test_svgs.py --size 120x40      # Custom terminal size
    python scripts/generate_test_svgs.py --list             # List available components

Output: tmp/ai_review/*.svg
"""

import asyncio
import argparse
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.widgets.panels.voice_visualizer_panel import (
    VoiceVisualizerPanel,
    VisualizationStyle,
    MicrophoneWaveformStyle,
)
from assistant.dashboard.widgets.panels.chat_panel import ChatPanel
from textual.app import App, ComposeResult


class VoiceVisualizerApp(App):
    """App for voice visualizer screenshot."""

    def __init__(self, style: VisualizationStyle):
        super().__init__()
        self.style = style

    def compose(self) -> ComposeResult:
        panel = VoiceVisualizerPanel(
            visualization_style=self.style,
            microphone_waveform_style=MicrophoneWaveformStyle.SCROLLING_FILL,
        )
        panel.simulation_mode = True
        panel.amplitude = 0.6
        yield panel


class ChatPanelApp(App):
    """App for chat panel screenshot."""

    def __init__(self, messages=None):
        super().__init__()
        self.messages = messages or []

    def compose(self) -> ComposeResult:
        chat = ChatPanel()
        for role, content in self.messages:
            chat.add_message(role, content)
        yield chat


async def generate_voice_visualizer_screenshots(output_dir: Path, terminal_size: tuple):
    """Generate screenshots for voice visualizer in all styles."""
    print(f"\n📊 Generating Voice Visualizer screenshots ({terminal_size[0]}x{terminal_size[1]})...")

    styles = [
        (VisualizationStyle.CONCENTRIC_CIRCLES, "concentric_circles"),
        (VisualizationStyle.RIPPLE_WAVES, "ripple_waves"),
        (VisualizationStyle.CIRCULAR_BARS, "circular_bars"),
        (VisualizationStyle.PULSING_DOTS, "pulsing_dots"),
        (VisualizationStyle.SPINNING_INDICATOR, "spinning_indicator"),
        (VisualizationStyle.SOUND_WAVE_CIRCLE, "sound_wave_circle"),
    ]

    for style, name in styles:
        app = VoiceVisualizerApp(style)
        async with app.run_test(size=terminal_size) as pilot:
            await pilot.pause(0.5)  # Let animation stabilize
            output_path = output_dir / f"voice_viz_{name}_{terminal_size[0]}x{terminal_size[1]}.svg"
            app.save_screenshot(str(output_path))
            print(f"  ✓ {output_path.name}")


async def generate_chat_panel_screenshots(output_dir: Path, terminal_size: tuple):
    """Generate screenshots for chat panel in various states."""
    print(f"\n💬 Generating Chat Panel screenshots ({terminal_size[0]}x{terminal_size[1]})...")

    scenarios = [
        ("empty", []),
        (
            "conversation",
            [
                ("user", "What's the weather like?"),
                (
                    "assistant",
                    "I don't have access to real-time weather data, but I can help you find weather information.",
                ),
                ("user", "That's okay, thanks!"),
                ("assistant", "You're welcome! Is there anything else I can help with?"),
            ],
        ),
        (
            "long_message",
            [
                ("user", "Can you explain what quantum computing is and how it differs from classical computing in a detailed way?"),
                (
                    "assistant",
                    "Quantum computing is a type of computation that harnesses quantum mechanical phenomena like superposition and entanglement. Unlike classical computers that use bits (0 or 1), quantum computers use qubits that can exist in multiple states simultaneously.",
                ),
            ],
        ),
    ]

    for name, messages in scenarios:
        app = ChatPanelApp(messages)
        async with app.run_test(size=terminal_size) as pilot:
            await pilot.pause(0.2)
            output_path = output_dir / f"chat_panel_{name}_{terminal_size[0]}x{terminal_size[1]}.svg"
            app.save_screenshot(str(output_path))
            print(f"  ✓ {output_path.name}")


async def main():
    parser = argparse.ArgumentParser(
        description="Generate SVG screenshots for AI review (headless mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_test_svgs.py
  python scripts/generate_test_svgs.py --component voice
  python scripts/generate_test_svgs.py --component chat --size 120x40
  python scripts/generate_test_svgs.py --list
        """,
    )
    parser.add_argument(
        "--component",
        choices=["voice", "chat", "all"],
        default="all",
        help="Which component to generate (default: all)",
    )
    parser.add_argument(
        "--size",
        default="80x30",
        help="Terminal size as WxH (default: 80x30)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available components",
    )
    parser.add_argument(
        "--output",
        default="tmp/ai_review",
        help="Output directory (default: tmp/ai_review)",
    )

    args = parser.parse_args()

    if args.list:
        print("\n📋 Available Components:")
        print("  - voice: Voice Visualizer Panel (6 visualization styles)")
        print("  - chat: Chat Panel (3 conversation scenarios)")
        print("  - all: Generate screenshots for all components")
        return

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
    print(f"\n🎨 Generating TUI screenshots in headless mode...")
    print(f"📁 Output directory: {output_dir.absolute()}")

    # Generate screenshots
    if args.component in ["voice", "all"]:
        await generate_voice_visualizer_screenshots(output_dir, terminal_size)

    if args.component in ["chat", "all"]:
        await generate_chat_panel_screenshots(output_dir, terminal_size)

    print(f"\n✅ Done! Generated screenshots in {output_dir}/")
    print(f"💡 These SVGs can be opened in a browser or analyzed programmatically.")


if __name__ == "__main__":
    asyncio.run(main())
