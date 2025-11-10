# TUI Testing Guide

## Overview

This guide explains how to test the Textual TUI application **without corrupting your terminal**. All testing runs in **headless mode**, making it safe for AI assistants and developers to verify visual output.

## Problem We Solved

**Before:** Running TUI apps takes over the terminal, making it impossible to:
- See test output during development
- Let AI assistants verify visual changes
- Run automated visual regression tests

**After:** Headless testing with snapshot automation:
- ✅ No terminal corruption
- ✅ AI can generate and review SVG screenshots
- ✅ Automated visual regression testing
- ✅ Fast feedback loop (seconds)

## Testing Architecture

### 1. Snapshot Testing (Automated)

**Purpose:** Catch unintended visual regressions automatically

**How it works:**
1. Tests capture SVG screenshots of TUI components
2. Compare against baseline snapshots
3. Generate HTML diff reports if changed
4. Update baselines when changes are intentional

**Tools:**
- `pytest` - Test framework
- `pytest-textual-snapshot` - Snapshot testing plugin
- `textual` - Built-in headless mode (`run_test()`)

### 2. On-Demand SVG Generation (AI Collaboration)

**Purpose:** Let AI generate and review screenshots without running full test suite

**How it works:**
1. Run helper script: `python scripts/generate_test_svgs.py`
2. SVGs generated in `tmp/ai_review/`
3. AI reads/analyzes SVG files
4. Human reviews visually in browser

## Quick Start

### Install Dependencies

```bash
# From packages/assistant directory
pip install -e ".[dev]"
```

This installs:
- `pytest>=7.4.0`
- `pytest-asyncio>=0.23.0`
- `pytest-cov>=4.1.0`
- `pytest-textual-snapshot>=1.0.0` ⭐ (new!)

### Run Snapshot Tests

```bash
# Run all snapshot tests
pytest tests/test_*_snapshots.py -v

# Run specific component
pytest tests/test_chat_panel_snapshots.py -v
pytest tests/test_voice_visualizer_snapshots.py -v

# Generate/update baselines (after intentional visual changes)
pytest tests/test_*_snapshots.py --snapshot-update
```

### Generate SVGs for AI Review

```bash
# Generate all components
python scripts/generate_test_svgs.py

# Generate specific component
python scripts/generate_test_svgs.py --component chat
python scripts/generate_test_svgs.py --component voice

# Custom terminal size
python scripts/generate_test_svgs.py --size 120x40

# See all options
python scripts/generate_test_svgs.py --help
```

Output: `tmp/ai_review/*.svg` (open in browser to view)

## Snapshot Testing Workflow

### Typical Development Flow

```
1. Make changes to TUI component
   └─ Edit: assistant/dashboard/widgets/panels/chat_panel.py

2. Run snapshot tests
   └─ pytest tests/test_chat_panel_snapshots.py
   └─ ❌ FAILED: Snapshots don't match

3. Review diff (if unintended change)
   └─ Look at HTML diff report
   └─ Fix the bug
   └─ Re-run tests

4. Update baselines (if intentional change)
   └─ pytest tests/test_chat_panel_snapshots.py --snapshot-update
   └─ ✅ PASSED: New baselines saved
```

### Understanding Test Output

**When tests pass:**
```
===== 12 passed in 99.07s (0:01:39) =====
```

**When visual changes detected:**
```
========================== FAILURES ==========================
_________ TestChatPanelSnapshots.test_chat_panel_conversation _________

AssertionError: Snapshot does not match stored snapshot.
Generated HTML report: __snapshots__/report.html
```

**Open the HTML report** to see side-by-side visual diff!

## Writing New Snapshot Tests

### Example: Test a New Panel

```python
"""
Snapshot tests for MyNewPanel.
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.dashboard.widgets.panels.my_new_panel import MyNewPanel
from textual.app import App, ComposeResult


class MyPanelApp(App):
    """Test app for MyNewPanel."""

    def compose(self) -> ComposeResult:
        panel = MyNewPanel()
        # Set up panel state for testing
        panel.set_data("test data")
        yield panel


class TestMyNewPanelSnapshots:
    """Visual snapshot tests for MyNewPanel."""

    def test_panel_empty(self, snap_compare):
        """Test empty panel state."""
        assert snap_compare(MyPanelApp(), terminal_size=(80, 30))

    def test_panel_with_data(self, snap_compare):
        """Test panel with data."""
        async def run_before(pilot):
            # Set up state before screenshot
            panel = pilot.app.query_one(MyNewPanel)
            panel.set_data("Sample data")
            await pilot.pause(0.2)

        assert snap_compare(
            MyPanelApp(),
            terminal_size=(80, 30),
            run_before=run_before
        )

    @pytest.mark.parametrize("size,size_name", [
        ((40, 15), "small"),
        ((80, 30), "standard"),
        ((120, 40), "large"),
    ])
    def test_panel_responsive(self, snap_compare, size, size_name):
        """Test panel at multiple terminal sizes."""
        assert snap_compare(MyPanelApp(), terminal_size=size)
```

### Best Practices

1. **Test at multiple sizes**: small (40x15), standard (80x30), large (120x40)
2. **Test different states**: empty, with data, error states
3. **Use `run_before` for setup**: Set state before screenshot
4. **Use `pilot.pause()`**: Let animations stabilize
5. **Keep tests fast**: Avoid unnecessary delays

## AI Collaboration Workflow

### Scenario: AI Needs to Verify TUI Changes

**Step 1: Developer requests verification**
```
Developer: "Can you verify the chat panel looks correct after my changes?"
```

**Step 2: AI generates screenshot**
```python
# AI runs this (headless, no terminal corruption):
!python scripts/generate_test_svgs.py --component chat
```

**Step 3: AI reads/analyzes SVG**
```python
# AI can read SVG as XML or view it visually
from pathlib import Path
svg_content = Path("tmp/ai_review/chat_panel_conversation_80x30.svg").read_text()

# AI verifies:
# - Layout structure
# - Text content
# - Colors and styling
# - Element positioning
```

**Step 4: AI provides feedback**
```
AI: "The chat panel looks correct! I can see:
     ✓ User messages right-aligned in cyan
     ✓ Assistant messages left-aligned in green
     ✓ Proper word wrapping at narrow widths
     ✓ Scrolling works with many messages

     The conversation layout matches the design."
```

### No Terminal Corruption!

All testing runs with `app.run_test()` which:
- Runs in headless mode (no terminal control codes)
- Generates SVG output
- Exits cleanly
- Safe for automated testing

## Project Structure

```
packages/assistant/
├── tests/
│   ├── __snapshots__/              # Generated baseline snapshots
│   │   ├── test_chat_panel_snapshots/
│   │   │   ├── test_chat_panel_empty.svg
│   │   │   ├── test_chat_panel_conversation.svg
│   │   │   └── ...
│   │   └── test_voice_visualizer_snapshots/
│   │       ├── test_visualizer_style_concentric_circles.svg
│   │       └── ...
│   ├── test_chat_panel_snapshots.py    # Chat panel snapshot tests
│   └── test_voice_visualizer_snapshots.py  # Voice viz snapshot tests
│
├── scripts/
│   └── generate_test_svgs.py       # AI helper script
│
├── tmp/                            # Temporary files (gitignored)
│   ├── ai_review/                  # On-demand SVG screenshots
│   │   ├── chat_panel_*.svg
│   │   └── voice_viz_*.svg
│   └── test-results/               # Old manual test outputs
│
└── docs/
    └── testing-guide.md            # This file
```

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Test TUI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          cd packages/assistant
          pip install -e ".[dev]"

      - name: Run snapshot tests
        run: |
          cd packages/assistant
          pytest tests/test_*_snapshots.py -v

      - name: Upload diff reports on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: snapshot-diffs
          path: packages/assistant/tests/__snapshots__/report.html
```

## Troubleshooting

### "Snapshot does not match"

**Cause:** Visual output changed (intentional or bug)

**Solution:**
1. Review HTML diff report: `tests/__snapshots__/report.html`
2. If intentional: `pytest --snapshot-update`
3. If bug: Fix code and re-run tests

### "No nodes match 'MyPanel'"

**Cause:** Panel not composed or selector wrong

**Solution:**
```python
# Ensure panel is yielded in compose()
def compose(self) -> ComposeResult:
    yield MyPanel()  # ← Must yield

# Query the exact class
panel = pilot.app.query_one(MyPanel)  # ← Use class, not string
```

### SVG file empty or corrupted

**Cause:** Animation not stabilized before screenshot

**Solution:**
```python
async def run_before(pilot):
    await pilot.pause(0.5)  # ← Increase pause time
```

### Tests too slow

**Cause:** Too many tests or long pause times

**Solution:**
- Run specific test file: `pytest tests/test_chat_panel_snapshots.py`
- Reduce pause times if animation is stable
- Use parallel testing: `pytest -n auto` (requires pytest-xdist)

## Performance

### Benchmark (M1 MacBook Pro)

| Test Suite | Tests | Time | Snapshots |
|------------|-------|------|-----------|
| Chat Panel | 12 | 99s (1:39) | 12 SVGs |
| Voice Visualizer (all styles) | 6 | 4.4s | 6 SVGs |
| Voice Visualizer (single test) | 1 | 0.95s | 1 SVG |
| On-demand SVG generation | - | 2-3s | 9 SVGs |

### Optimization Tips

1. **Run specific tests** during development
2. **Use `--snapshot-update` only when needed** (slower)
3. **Keep pause times minimal** (0.2-0.5s usually enough)
4. **Run full suite in CI/CD** only

## FAQ

### Q: Do snapshots need to be committed to git?

**A:** Yes! Snapshots in `tests/__snapshots__/` should be committed. They serve as the visual "baseline" for regression testing.

```bash
git add tests/__snapshots__/
git commit -m "test: update chat panel snapshots after styling changes"
```

### Q: Should `tmp/` be committed?

**A:** No. Add to `.gitignore`:
```gitignore
tmp/
.pytest_cache/
__pycache__/
```

### Q: How do I test animations?

**A:** Use `pilot.pause()` to advance to specific animation frames:

```python
async def run_before(pilot):
    # Advance animation by 0.5 seconds
    await pilot.pause(0.5)
    # Now take screenshot at this frame
```

### Q: Can I test keyboard interactions?

**A:** Yes! Use Pilot's `press()` method:

```python
async def run_before(pilot):
    # Press Tab to focus next element
    await pilot.press("tab")
    # Press Enter
    await pilot.press("enter")
```

### Q: How does AI analyze SVGs?

**A:** AI can:
1. **Read SVG as XML** - Parse structure programmatically
2. **View visually** - See the rendered SVG (if tool supports it)
3. **Check attributes** - Verify colors, positions, text content
4. **Compare layouts** - Ensure responsive behavior

## Responsive Testing

For comprehensive responsive testing across 10 terminal sizes (30x10 to 200x60), see:

📖 **[docs/responsive-testing.md](responsive-testing.md)**

**Quick Start:**
```bash
# Run all responsive tests (~70 snapshots, ~3 min)
pytest tests/test_responsive_comprehensive.py -v

# Test specific component
pytest tests/test_responsive_comprehensive.py::TestChatPanelResponsive -v

# Generate SVGs at different sizes
python scripts/generate_test_svgs.py --size 30x10   # Tiny
python scripts/generate_test_svgs.py --size 200x60  # 4K
```

**Coverage:**
- ✅ 10 terminal sizes from tiny (30x10) to 4K (200x60)
- ✅ Voice visualizer at all sizes
- ✅ Chat panel at all sizes
- ✅ Extreme edge cases (ultra-wide, very tall)
- ✅ ~70 responsive snapshots total

## Next Steps

1. ✅ **Run existing tests**: `pytest tests/test_*_snapshots.py -v`
2. ✅ **Run responsive tests**: `pytest tests/test_responsive_comprehensive.py -v`
3. ✅ **Generate SVGs for review**: `python scripts/generate_test_svgs.py`
4. ✅ **Write tests for new components**: Follow examples above
5. ✅ **Add to CI/CD**: Catch regressions automatically

## Resources

- [Textual Testing Docs](https://textual.textualize.io/guide/testing/)
- [pytest-textual-snapshot](https://github.com/Textualize/pytest-textual-snapshot)
- [Textual Pilot API](https://textual.textualize.io/guide/testing/#pilot)
- **[Responsive Testing Guide](responsive-testing.md)** - Comprehensive responsive testing

---

**Happy Testing!** 🎉 No more terminal corruption! 🚀
