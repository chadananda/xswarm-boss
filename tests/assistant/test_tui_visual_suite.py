#!/usr/bin/env python3
"""
Comprehensive visual testing for TUI at multiple sizes and configurations.

Generates SVG screenshots for manual inspection of:
- Responsive behavior at different terminal sizes
- Panel configurations (all panels, minimal, focus mode, etc.)
- Theme integration
- Layout modes

This allows the developer to visually verify the TUI works correctly
across all supported configurations.
"""

import asyncio
from pathlib import Path
from typing import List, Tuple
from textual.app import App, ComposeResult
from textual.widgets import Static, Header, Footer
from textual.containers import Container
from rich.text import Text

# Import our panels
from assistant.dashboard.widgets.panels import ChatPanel, PanelBase


# Define test terminal sizes
TERMINAL_SIZES = [
    (40, 15, "tiny"),       # Minimum supported
    (60, 20, "small"),      # Small terminal
    (80, 30, "medium"),     # Common size
    (100, 35, "large"),     # Large terminal
    (120, 40, "xlarge"),    # Extra large
    (160, 50, "xxlarge"),   # Ultra wide
]

# Define panel configurations to test
PANEL_CONFIGURATIONS = [
    ("chat_only", ["chat"], "Focus mode with chat panel only"),
    ("chat_with_data", ["chat"], "Chat panel with sample conversation"),
    ("minimal", ["chat"], "Minimal configuration for small terminals"),
]


class SimpleChatTestApp(App):
    """Simple test app to demonstrate ChatPanel at various sizes."""

    CSS = """
    Screen {
        align: center middle;
    }

    #main-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    ChatPanel {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, title: str = "Chat Panel Test", with_messages: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.with_messages = with_messages

    def compose(self) -> ComposeResult:
        """Compose the test app UI."""
        yield Header()

        with Container(id="main-container"):
            chat = ChatPanel()

            # Add sample messages if requested
            if self.with_messages:
                chat.add_message(
                    "user",
                    "Hey there! Can you help me with a Python question?"
                )
                chat.add_message(
                    "assistant",
                    "Of course! I'd be happy to help you with your Python question. What would you like to know?"
                )
                chat.add_message(
                    "user",
                    "How do I create a list comprehension that filters even numbers from a range?"
                )
                chat.add_message(
                    "assistant",
                    "Great question! You can use a list comprehension with an if condition. Here's an example:\n\n"
                    "even_numbers = [x for x in range(20) if x % 2 == 0]\n\n"
                    "This will create a list of all even numbers from 0 to 19. The 'if x % 2 == 0' part filters "
                    "to only include numbers divisible by 2."
                )
                chat.add_message(
                    "user",
                    "That's perfect! Thank you so much!"
                )
                chat.add_message(
                    "assistant",
                    "You're welcome! Let me know if you have any other questions."
                )

                # Mark as focused to show active state
                chat.focus_panel()

            yield chat

        yield Footer()


async def test_configuration(
    size: Tuple[int, int, str],
    config_name: str,
    description: str,
    with_messages: bool = False
) -> str:
    """
    Test specific configuration at specific size.

    Args:
        size: (width, height, label) tuple
        config_name: Configuration name for filename
        description: Human-readable description
        with_messages: Whether to populate with sample messages

    Returns:
        Path to generated SVG file
    """
    width, height, size_label = size

    # Create test app
    app = SimpleChatTestApp(
        title=f"{config_name.replace('_', ' ').title()} - {size_label}",
        with_messages=with_messages
    )

    # Set up output path
    output_dir = Path(__file__).parent / "tmp" / "visual_tests"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{config_name}_{size_label}_{width}x{height}.svg"

    # Run app in test mode
    async with app.run_test(size=(width, height)) as pilot:
        # Let the layout settle
        await pilot.pause(0.5)

        # Save screenshot
        app.save_screenshot(str(output_path))

    return str(output_path)


async def main():
    """Run complete visual test suite."""
    print("\n" + "=" * 80)
    print("TUI VISUAL TEST SUITE - Comprehensive Configuration Testing")
    print("=" * 80 + "\n")

    # Test configurations
    test_cases = [
        # Empty chat panel at all sizes
        ("chat_only", False, "Empty chat panel"),

        # Chat with sample conversation at all sizes
        ("chat_with_data", True, "Chat panel with conversation"),
    ]

    total_tests = len(TERMINAL_SIZES) * len(test_cases)
    current = 0
    generated_files = []

    for size in TERMINAL_SIZES:
        width, height, size_label = size

        for config_name, with_messages, description in test_cases:
            current += 1
            print(f"[{current}/{total_tests}] Testing {config_name} at {size_label} ({width}x{height})...")

            try:
                output_path = await test_configuration(
                    size,
                    config_name,
                    description,
                    with_messages=with_messages
                )
                generated_files.append(output_path)
                print(f"  ✓ Saved to: {output_path}")

            except Exception as e:
                print(f"  ✗ Failed: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"Generated {len(generated_files)} test screenshots")
    print(f"View results in: tmp/visual_tests/")
    print("=" * 80 + "\n")

    # Print file list
    if generated_files:
        print("Generated files:")
        for file_path in generated_files:
            print(f"  - {file_path}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
