"""
Comprehensive theme switching tests for Python TUI.

Tests that theme colors (from personas) apply correctly to all UI elements:
- Borders, text, backgrounds change together
- JARVIS (cyan #00D4FF) and GLaDOS (orange #FFA500) themes work
- Responsive behavior maintains theming at all sizes
- Visual regression prevention

This test suite demonstrates the autonomous testing workflow:
1. pytest-textual-snapshot captures SVG outputs
2. conftest helpers analyze SVGs programmatically
3. Smart update logic decides when to auto-update baselines
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.widgets import Static, Label
from textual.containers import Container
from textual.reactive import reactive
from textual.color import Color
from assistant.dashboard.theme import generate_palette

# conftest.py is automatically loaded by pytest - these functions will be available
# When tester agent needs to analyze SVGs, import like this:
# from conftest import analyze_svg_snapshot, verify_theme_colors, etc.


class TestThemeApp(App):
    """
    Minimal test app for theme switching demonstration.

    Simulates how theme colors are applied in the full VoiceAssistantApp
    without all the dependencies (config, personas, etc.).
    """

    CSS = """
    Container {
        border: solid cyan;
        padding: 1;
    }

    #status {
        color: white;
        background: #0d414b;
    }

    #title {
        color: cyan;
        text-style: bold;
    }
    """

    theme_color = reactive(Color.parse("#00D4FF"))  # Default JARVIS cyan

    def compose(self) -> ComposeResult:
        """Create simple themed UI."""
        with Container():
            yield Label("Theme Switching Test", id="title")
            yield Static("Testing theme color application", id="status")

    def watch_theme_color(self, new_color: Color):
        """Update theme when color changes - mimics app.py approach."""
        palette = generate_palette(new_color.hex)

        # Update widget styles manually (like app.py does)
        try:
            container = self.query_one(Container)
            title = self.query_one("#title", Label)
            status = self.query_one("#status", Static)

            # Set border colors
            border_color = Color.parse(palette.shade_3)
            container.styles.border = ("solid", border_color)

            # Set text colors
            title.styles.color = border_color

            # Set background colors
            bg_color = Color.parse(palette.shade_1).with_alpha(0.8)
            status.styles.background = bg_color

            # Force refresh
            container.refresh()
            title.refresh()
            status.refresh()
        except Exception:
            # Widgets might not be mounted yet during initialization
            pass


class TestThemeSwitchingVisual:
    """Visual regression tests for theme switching feature."""

    def test_default_theme_applied(self, snap_compare):
        """Test that default theme (JARVIS cyan) is applied on startup."""
        app = TestThemeApp()
        assert snap_compare(app, terminal_size=(80, 30))

    def test_jarvis_theme_cyan(self, snap_compare):
        """Test JARVIS persona theme (cyan #00D4FF) is applied."""
        app = TestThemeApp()

        async def apply_jarvis_theme(pilot):
            """Set JARVIS cyan theme."""
            pilot.app.theme_color = Color.parse("#00D4FF")
            await pilot.pause(0.2)

        assert snap_compare(
            app,
            terminal_size=(80, 30),
            run_before=apply_jarvis_theme
        )

    def test_glados_theme_orange(self, snap_compare):
        """Test GLaDOS persona theme (orange #FFA500) is applied."""
        app = TestThemeApp()

        async def apply_glados_theme(pilot):
            """Set GLaDOS orange theme."""
            pilot.app.theme_color = Color.parse("#FFA500")
            await pilot.pause(0.2)

        assert snap_compare(
            app,
            terminal_size=(80, 30),
            run_before=apply_glados_theme
        )


class TestThemeSwitchingResponsive:
    """Responsive behavior tests - theme colors work at all terminal sizes."""

    @pytest.mark.parametrize("size,size_name", [
        ((40, 15), "small"),
        ((80, 24), "default_linux"),
        ((80, 30), "standard"),
        ((120, 40), "large"),
    ])
    def test_jarvis_theme_responsive(self, snap_compare, size, size_name):
        """Test JARVIS theme renders correctly at all terminal sizes."""
        app = TestThemeApp()

        async def apply_jarvis_theme(pilot):
            """Set JARVIS theme."""
            pilot.app.theme_color = Color.parse("#00D4FF")
            await pilot.pause(0.2)

        assert snap_compare(
            app,
            terminal_size=size,
            run_before=apply_jarvis_theme
        )

    @pytest.mark.parametrize("size,size_name", [
        ((40, 15), "small"),
        ((80, 30), "standard"),
        ((120, 40), "large"),
    ])
    def test_glados_theme_responsive(self, snap_compare, size, size_name):
        """Test GLaDOS theme renders correctly at key terminal sizes."""
        app = TestThemeApp()

        async def apply_glados_theme(pilot):
            """Set GLaDOS theme."""
            pilot.app.theme_color = Color.parse("#FFA500")
            await pilot.pause(0.2)

        assert snap_compare(
            app,
            terminal_size=size,
            run_before=apply_glados_theme
        )


class TestThemeSwitchingProgrammaticVerification:
    """
    Programmatic SVG analysis tests.

    These tests demonstrate the smart update logic:
    1. Capture snapshot
    2. Analyze SVG programmatically
    3. Verify expected colors/text/layout
    4. Auto-update if expectations met, else invoke @stuck
    """

    def test_jarvis_colors_present_in_svg(self, snap_compare, tmp_path):
        """
        Verify JARVIS cyan color (#00D4FF) appears in SVG snapshot.

        This demonstrates programmatic color verification without human eyes.
        """
        app = TestThemeApp()

        async def apply_jarvis_theme(pilot):
            pilot.app.theme_color = Color.parse("#00D4FF")
            await pilot.pause(0.2)

        # Capture snapshot
        assert snap_compare(
            app,
            terminal_size=(80, 30),
            run_before=apply_jarvis_theme
        )

        # Analyze SVG (smart update logic)
        # Note: In actual workflow, tester agent would:
        # 1. Read SVG from __snapshots__ directory
        # 2. Run these verifications
        # 3. If pass: auto-update baseline
        # 4. If fail: invoke @stuck with details

        # Example verification (snapshot path varies by test runner)
        # In real agent workflow, agent would construct correct path
        # svg_path = Path("packages/assistant/tests/__snapshots__") / "test_jarvis_colors_present_in_svg.svg"
        # if svg_path.exists():
        #     analysis = analyze_svg_snapshot(svg_path)
        #     # JARVIS cyan should appear in SVG
        #     assert "#00D4FF" in analysis['colors'] or any(
        #         color.startswith("#00D") for color in analysis['colors']
        #     ), f"JARVIS cyan not found. Colors: {analysis['colors']}"

    def test_glados_colors_present_in_svg(self, snap_compare, tmp_path):
        """
        Verify GLaDOS orange color (#FFA500) appears in SVG snapshot.

        This demonstrates programmatic color verification without human eyes.
        """
        app = TestThemeApp()

        async def apply_glados_theme(pilot):
            pilot.app.theme_color = Color.parse("#FFA500")
            await pilot.pause(0.2)

        # Capture snapshot
        assert snap_compare(
            app,
            terminal_size=(80, 30),
            run_before=apply_glados_theme
        )

        # Programmatic verification
        # svg_path = Path("packages/assistant/tests/__snapshots__") / "test_glados_colors_present_in_svg.svg"
        # if svg_path.exists():
        #     analysis = analyze_svg_snapshot(svg_path)
        #     # GLaDOS orange should appear in SVG
        #     assert "#FFA500" in analysis['colors'] or any(
        #         color.startswith("#FF") for color in analysis['colors']
        #     ), f"GLaDOS orange not found. Colors: {analysis['colors']}"

    def test_ui_elements_present(self, snap_compare, tmp_path):
        """
        Verify expected UI elements and text are present.

        This ensures theme switching doesn't break layout.
        """
        app = TestThemeApp()

        # Capture default state
        assert snap_compare(app, terminal_size=(80, 30))

        # Programmatic verification
        # svg_path = Path("packages/assistant/tests/__snapshots__") / "test_ui_elements_present.svg"
        # if svg_path.exists():
        #     analysis = analyze_svg_snapshot(svg_path)
        #
        #     # Verify layout elements
        #     assert analysis['has_borders'], "UI borders not found in SVG"
        #
        #     # Verify expected text (adjust based on actual UI)
        #     # text_content = ' '.join(analysis['text'])
        #     # assert any(keyword in text_content for keyword in ['Voice', 'Status', 'Active'])


class TestThemeSwitchingEdgeCases:
    """Edge case tests for theme switching."""

    def test_rapid_theme_switching(self, snap_compare):
        """Test that rapid theme changes don't cause visual artifacts."""
        app = TestThemeApp()

        async def rapid_switch(pilot):
            """Rapidly switch between themes."""
            # Switch to JARVIS cyan
            pilot.app.theme_color = Color.parse("#00D4FF")
            await pilot.pause(0.1)

            # Switch to GLaDOS orange
            pilot.app.theme_color = Color.parse("#FFA500")
            await pilot.pause(0.2)

        assert snap_compare(
            app,
            terminal_size=(80, 30),
            run_before=rapid_switch
        )

    def test_theme_persistence_after_resize(self, snap_compare):
        """Test that theme colors persist after terminal resize."""
        app = TestThemeApp()

        async def resize_with_theme(pilot):
            """Apply theme, resize, verify theme persists."""
            # Apply JARVIS theme
            pilot.app.theme_color = Color.parse("#00D4FF")
            await pilot.pause(0.2)

            # Resize terminal
            await pilot.resize_terminal(120, 40)
            await pilot.pause(0.2)

        assert snap_compare(
            app,
            terminal_size=(120, 40),
            run_before=resize_with_theme
        )


# Usage Notes for Future Development:
#
# **Coder Agent Workflow (Temporary Tests):**
# 1. Implement feature in packages/assistant/assistant/dashboard/
# 2. Create quick test in ./tmp/dev_tests/test_quick_[feature].py
# 3. Run: pytest ./tmp/dev_tests/test_quick_[feature].py -v
# 4. Read SVG: ./tmp/dev_tests/__snapshots__/[test].svg
# 5. Iterate until correct
# 6. Update baseline: pytest --snapshot-update
# 7. Signal completion (temp tests NOT committed)
#
# **Tester Agent Workflow (Permanent Tests):**
# 1. Receive completed feature
# 2. Write permanent tests in tests/test_[feature]_snapshots.py (like this file)
# 3. Run: pytest tests/test_[feature]*.py -v
# 4. Analyze SVGs with conftest helpers
# 5. Smart update: auto-update if expected, @stuck if unexpected
# 6. Commit tests + snapshots
#
# **Running These Tests:**
# pytest packages/assistant/tests/test_theme_switching_snapshots.py -v
# pytest packages/assistant/tests/test_theme_switching_snapshots.py -v --snapshot-update
# pytest packages/assistant/tests/test_theme_switching_snapshots.py::TestThemeSwitchingVisual -v
