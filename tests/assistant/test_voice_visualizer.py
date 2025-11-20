#!/usr/bin/env python3
"""
Comprehensive visual testing for VoiceVisualizerPanel.

Tests all 6 visualization styles at various terminal sizes to showcase
different circular animation options for assistant speaking.

Generates SVG screenshots for comparison and selection of preferred style.
"""

import asyncio
from pathlib import Path
from typing import Tuple
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

from assistant.dashboard.widgets.panels import (
    VoiceVisualizerPanel,
    VisualizationStyle,
)


# Define test terminal sizes
TERMINAL_SIZES = [
    (60, 20, "small"),      # Small terminal
    (80, 30, "medium"),     # Common size
    (100, 35, "large"),     # Large terminal
    (120, 40, "xlarge"),    # Extra large
]

# All visualization styles to test
VISUALIZATION_STYLES = [
    (VisualizationStyle.CONCENTRIC_CIRCLES, "concentric_circles"),
    (VisualizationStyle.RIPPLE_WAVES, "ripple_waves"),
    (VisualizationStyle.CIRCULAR_BARS, "circular_bars"),
    (VisualizationStyle.PULSING_DOTS, "pulsing_dots"),
    (VisualizationStyle.SPINNING_INDICATOR, "spinning_indicator"),
    (VisualizationStyle.SOUND_WAVE_CIRCLE, "sound_wave_circle"),
]


class VoiceVisualizerTestApp(App):
    """Test app for VoiceVisualizerPanel with specific style."""

    CSS = """
    VoiceVisualizerPanel { width: 100%; height: 100%; }
    """

    def __init__(self, style: VisualizationStyle, **kwargs):
        super().__init__(**kwargs)
        self.style = style

    def compose(self) -> ComposeResult:
        yield Header()
        panel = VoiceVisualizerPanel(visualization_style=self.style)
        panel.focus_panel()
        panel.simulation_mode = True
        # Start animation
        panel.start_animation()
        yield panel
        yield Footer()


async def test_style_at_size(
    style: VisualizationStyle,
    style_name: str,
    size: Tuple[int, int, str],
    frame: int = 10
) -> str:
    """
    Test a visualization style at a specific size.

    Args:
        style: Visualization style
        style_name: Style name for filename
        size: (width, height, label) tuple
        frame: Which animation frame to capture (affects visualization)

    Returns:
        Path to generated SVG file
    """
    width, height, size_label = size

    # Create test app
    app = VoiceVisualizerTestApp(style=style)

    # Set up output path
    output_dir = Path(__file__).parent / "tmp" / "voice_viz_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{style_name}_{size_label}_{width}x{height}_f{frame}.svg"

    # Run app in test mode
    async with app.run_test(size=(width, height)) as pilot:
        # Let animation run to desired frame
        # Each pause is ~0.05s, so we pause multiple times to reach frame
        for _ in range(frame):
            await pilot.pause(0.05)

        # Save screenshot
        app.save_screenshot(str(output_path))

    return str(output_path)


async def test_style_animation_sequence(
    style: VisualizationStyle,
    style_name: str,
    size: Tuple[int, int, str],
    num_frames: int = 3
) -> list:
    """
    Test a visualization style across multiple animation frames.

    Args:
        style: Visualization style
        style_name: Style name for filename
        size: (width, height, label) tuple
        num_frames: Number of frames to capture

    Returns:
        List of paths to generated SVG files
    """
    paths = []

    for frame_idx in range(num_frames):
        # Capture frames at different points in animation cycle
        frame = frame_idx * 10

        path = await test_style_at_size(style, style_name, size, frame)
        paths.append(path)

    return paths


async def main():
    """Run complete voice visualizer test suite."""
    print("\n" + "=" * 80)
    print("VOICE VISUALIZER PANEL TEST SUITE")
    print("Testing ALL 6 visualization styles at multiple sizes")
    print("=" * 80 + "\n")

    total_tests = len(VISUALIZATION_STYLES) * len(TERMINAL_SIZES)
    current = 0
    generated_files = []

    # Test each visualization style
    for style, style_name in VISUALIZATION_STYLES:
        print(f"\n🎨 Testing {style_name.upper().replace('_', ' ')}")
        print("-" * 80)

        for size in TERMINAL_SIZES:
            current += 1
            width, height, size_label = size

            print(f"  [{current:2d}/{total_tests}] {size_label:8s} ({width:3d}x{height:2d})...", end=" ")

            try:
                # Capture multiple frames to show animation
                output_paths = await test_style_animation_sequence(
                    style, style_name, size, num_frames=3
                )
                generated_files.extend(output_paths)
                print(f"✓ ({len(output_paths)} frames)")

            except Exception as e:
                print(f"✗ FAILED: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"✅ Generated {len(generated_files)} test screenshots")
    print(f"   ({len(VISUALIZATION_STYLES)} styles × {len(TERMINAL_SIZES)} sizes × 3 frames)")
    print(f"📁 View results in: tmp/voice_viz_tests/")
    print("=" * 80 + "\n")

    # Print summary by style
    print("Summary by visualization style:")
    for style, style_name in VISUALIZATION_STYLES:
        style_files = [f for f in generated_files if f"/{style_name}_" in f]
        expected_count = len(TERMINAL_SIZES) * 3  # 3 frames per size
        status = "✅" if len(style_files) == expected_count else "❌"
        display_name = style_name.replace("_", " ").title()
        print(f"  {status} {display_name:25s}: {len(style_files):2d}/{expected_count} screenshots")

    print("\n" + "=" * 80)
    print("📊 COMPARISON GUIDE")
    print("=" * 80)
    print()
    print("Style 1: Concentric Circles")
    print("  - Expanding rings from center")
    print("  - Uses density characters (░▒▓█)")
    print("  - Good for: Pulsing beat effect")
    print()
    print("Style 2: Ripple Waves")
    print("  - Ripple effect with wave characters")
    print("  - Uses wave chars (◠◡◝◞)")
    print("  - Good for: Water ripple / echo effect")
    print()
    print("Style 3: Circular Bars")
    print("  - Vertical bars in circular arrangement")
    print("  - Like audio equalizer bent into circle")
    print("  - Good for: Classic audio visualizer feel")
    print()
    print("Style 4: Pulsing Dots")
    print("  - Multiple rings of pulsing dots")
    print("  - Uses dot chars (·•●⬤)")
    print("  - Good for: Discrete, minimal aesthetic")
    print()
    print("Style 5: Spinning Indicator")
    print("  - Rotating spiral effect")
    print("  - Uses spinner chars (◜◝◞◟)")
    print("  - Good for: Processing/thinking indicator")
    print()
    print("Style 6: Sound Wave Circle")
    print("  - Wave pattern around circle perimeter")
    print("  - Amplitude modulates circle radius")
    print("  - Good for: Organic sound wave feel")
    print()
    print("=" * 80 + "\n")


async def demo_single_style(style: VisualizationStyle, style_name: str):
    """
    Demo a single style with live animation.

    Args:
        style: Visualization style to demo
        style_name: Style name for display
    """
    print(f"\n🎬 Live Demo: {style_name.replace('_', ' ').title()}")
    print("=" * 80)
    print("Press Ctrl+C to stop...\n")

    app = VoiceVisualizerTestApp(style=style)

    try:
        await app.run_async()
    except KeyboardInterrupt:
        print("\n\nDemo stopped.")


if __name__ == "__main__":
    import sys

    # Check if user wants to demo a specific style
    if len(sys.argv) > 1:
        style_arg = sys.argv[1].lower()

        # Find matching style
        for style, style_name in VISUALIZATION_STYLES:
            if style_name.lower() == style_arg or style_name.replace("_", "") == style_arg:
                asyncio.run(demo_single_style(style, style_name))
                sys.exit(0)

        print(f"❌ Unknown style: {style_arg}")
        print("\nAvailable styles:")
        for _, style_name in VISUALIZATION_STYLES:
            print(f"  - {style_name}")
        sys.exit(1)

    # Run full test suite
    asyncio.run(main())
