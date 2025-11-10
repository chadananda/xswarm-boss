# Multi-Panel TUI Architecture - Hyprland-Style Tiling

## Vision
A comprehensive, voice-controllable TUI with multiple panels (chat, documents, projects, calendar, todo, notifications) arranged in a configurable tiling layout, with subtle background animations and an animated persona avatar.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Header (Persona, Status, Wake Word Indicator)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │   Chat Window    │  │ Documents Panel  │  │ Todo List    │ │
│  │                  │  │                  │  │              │ │
│  │  [Messages]      │  │  [File Browser]  │  │  [ ] Task 1  │ │
│  │  [Input Box]     │  │  [Preview]       │  │  [x] Task 2  │ │
│  │                  │  │                  │  │  [ ] Task 3  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │ Projects Panel   │  │   Calendar       │  │Notifications │ │
│  │                  │  │                  │  │              │ │
│  │  [Project List]  │  │  [Month View]    │  │  [Alerts]    │ │
│  │  [Task Kanban]   │  │  [Reminders]     │  │  [Updates]   │ │
│  │                  │  │                  │  │              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
│                                                                 │
│  Background Layer: Animated Persona Avatar (opacity: 0.2)      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ Footer (System Stats, Controls)                                │
└─────────────────────────────────────────────────────────────────┘
```

## Layer System (Z-Index)

```
z-index: 100  - Modal dialogs, wizards
z-index: 50   - Floating windows, popups
z-index: 10   - Main panels (chat, docs, todo, etc.)
z-index: 5    - Header, Footer
z-index: 0    - Background animated avatar
z-index: -1   - Subtle background effects (particles, matrix rain)
```

## Panel Types

### 1. Chat Window (Primary)
**Purpose:** Voice conversation and text chat with AI assistant

**Features:**
- Message history (scrollable)
- User messages (right-aligned)
- AI responses (left-aligned)
- Text input box
- Voice indicator (pulsing when listening)
- Quick commands bar

**State:**
- Current conversation ID
- Message history (last 100)
- Typing indicator

### 2. Documents Panel
**Purpose:** Browse, search, and preview documents

**Features:**
- File browser (tree view)
- Search bar (full-text + semantic)
- Document preview (text, markdown, code)
- Recent files list
- Starred documents
- Tags/categories

**State:**
- Current directory
- Selected file
- Search query
- Preview content

### 3. Projects Panel
**Purpose:** Project management with Kanban board

**Features:**
- Project list
- Kanban board (Backlog, In Progress, Done)
- Task cards (drag & drop)
- Filter by tags, assignee, priority
- Project statistics

**State:**
- Active project
- Task list
- Board layout
- Filters

### 4. Calendar/Reminders Panel
**Purpose:** Schedule management and reminders

**Features:**
- Month/week/day views
- Event list
- Reminder notifications
- Quick event creation
- Time-sensitive highlighting

**State:**
- Current view mode
- Selected date
- Event list
- Active reminders

### 5. Todo List Panel
**Purpose:** Quick task management

**Features:**
- Task list with checkboxes
- Priority indicators
- Due dates
- Tags/categories
- Quick add via voice

**State:**
- Task list
- Filters
- Sort order

### 6. Notifications Panel
**Purpose:** System notifications and alerts

**Features:**
- Notification feed
- Badge count
- Priority levels (info, warning, error)
- Dismiss/snooze actions
- Notification history

**State:**
- Notification list
- Unread count
- Filter settings

## Tiling Layout System (Hyprland-Inspired)

### Layout Modes

**1. Grid Layout (Default)**
```
┌─────┬─────┬─────┐
│  A  │  B  │  C  │
├─────┼─────┼─────┤
│  D  │  E  │  F  │
└─────┴─────┴─────┘
```

**2. Master-Stack Layout**
```
┌───────────┬─────┐
│           │  B  │
│     A     ├─────┤
│  (Master) │  C  │
│           ├─────┤
│           │  D  │
└───────────┴─────┘
```

**3. Horizontal Split**
```
┌─────────────────┐
│        A        │
├─────────────────┤
│        B        │
├─────────────────┤
│        C        │
└─────────────────┘
```

**4. Vertical Split**
```
┌─────┬─────┬─────┐
│     │     │     │
│  A  │  B  │  C  │
│     │     │     │
└─────┴─────┴─────┘
```

**5. Focus Mode (Full Screen)**
```
┌─────────────────┐
│                 │
│                 │
│        A        │
│                 │
│                 │
└─────────────────┘
```

### Layout Configuration

```yaml
# ~/.config/xswarm/layout.yaml

layout_mode: "grid"  # grid, master-stack, hsplit, vsplit, focus

panels:
  chat:
    enabled: true
    position: [0, 0]      # Grid position (row, col)
    size: [2, 1]          # Span (rows, cols)
    min_width: 40
    min_height: 10

  documents:
    enabled: true
    position: [0, 1]
    size: [1, 1]

  todo:
    enabled: true
    position: [0, 2]
    size: [1, 1]

  projects:
    enabled: true
    position: [1, 0]
    size: [1, 1]

  calendar:
    enabled: true
    position: [1, 1]
    size: [1, 1]

  notifications:
    enabled: true
    position: [1, 2]
    size: [1, 1]

# Responsive breakpoints
breakpoints:
  xlarge: 120  # >= 120 cols: Show all 6 panels
  large: 80    # >= 80 cols: Show 4 panels (hide notifications, projects)
  medium: 60   # >= 60 cols: Show 2 panels (chat + todo)
  small: 40    # >= 40 cols: Show 1 panel (chat only)

# Animation settings
animations:
  enabled: true
  avatar_opacity: 0.2
  background_effects: "subtle"  # none, subtle, full
  transition_speed: 0.3  # seconds
```

## Voice Commands for Configuration

### Panel Management
- **"Show chat"** - Focus chat panel
- **"Hide documents"** - Hide documents panel
- **"Toggle notifications"** - Show/hide notifications
- **"Full screen chat"** - Focus mode on chat
- **"Exit focus mode"** - Return to tiled layout

### Layout Commands
- **"Switch to grid layout"** - Grid mode
- **"Switch to master stack"** - Master-stack mode
- **"Arrange panels horizontally"** - Horizontal split
- **"Arrange panels vertically"** - Vertical split

### Panel Actions
- **"Move chat to left"** - Reposition panel
- **"Resize todo smaller"** - Adjust panel size
- **"Swap chat and documents"** - Exchange positions

### Quick Access
- **"Open todo"** - Quick open todo panel
- **"Show calendar"** - Jump to calendar
- **"Check notifications"** - View notifications

## Visual Testing Suite

### Test Script Architecture

```python
# test_tui_visual_suite.py

"""
Comprehensive visual testing for TUI at multiple sizes and configurations.
Generates SVG screenshots for manual inspection.
"""

import asyncio
from pathlib import Path
from assistant.dashboard.app import VoiceAssistantApp
from assistant.config import Config

TERMINAL_SIZES = [
    (40, 15, "tiny"),       # Minimum supported
    (60, 20, "small"),      # Small terminal
    (80, 30, "medium"),     # Common size
    (100, 35, "large"),     # Large terminal
    (120, 40, "xlarge"),    # Extra large
    (160, 50, "xxlarge"),   # Ultra wide
]

PANEL_CONFIGURATIONS = [
    ("all_panels", ["chat", "documents", "todo", "projects", "calendar", "notifications"]),
    ("productivity", ["chat", "todo", "calendar"]),
    ("coding", ["chat", "documents", "projects"]),
    ("minimal", ["chat", "todo"]),
    ("focus_chat", ["chat"]),
]

async def test_configuration(size, config_name, enabled_panels):
    """Test specific configuration at specific size"""
    width, height, size_label = size
    config = Config.load_from_file()
    personas_dir = Path(__file__).parent.parent / "personas"

    # Configure which panels are enabled
    config.layout = {
        "enabled_panels": enabled_panels,
        "layout_mode": "grid" if len(enabled_panels) > 2 else "vsplit",
    }

    app = VoiceAssistantApp(config, personas_dir)

    async with app.run_test(size=(width, height)) as pilot:
        await pilot.pause(0.5)  # Let layout settle

        output_path = Path(__file__).parent / "tmp" / "visual_tests" / \
                     f"{config_name}_{size_label}_{width}x{height}.svg"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        app.save_screenshot(str(output_path))
        print(f"✓ {config_name} at {width}x{height} → {output_path}")

async def main():
    """Run complete visual test suite"""
    print("\n" + "="*80)
    print("TUI VISUAL TEST SUITE - Comprehensive Configuration Testing")
    print("="*80 + "\n")

    total_tests = len(TERMINAL_SIZES) * len(PANEL_CONFIGURATIONS)
    current = 0

    for size in TERMINAL_SIZES:
        for config_name, enabled_panels in PANEL_CONFIGURATIONS:
            current += 1
            print(f"[{current}/{total_tests}] Testing {config_name} at {size[2]}...")

            try:
                await test_configuration(size, config_name, enabled_panels)
            except Exception as e:
                print(f"  ✗ Failed: {e}")

    print("\n" + "="*80)
    print(f"Generated {total_tests} test screenshots")
    print("View results in: tmp/visual_tests/")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
```

### Visual Test Matrix

| Size    | All Panels | Productivity | Coding | Minimal | Focus |
|---------|-----------|--------------|---------|---------|-------|
| 40x15   | ✓         | ✓            | ✓       | ✓       | ✓     |
| 60x20   | ✓         | ✓            | ✓       | ✓       | ✓     |
| 80x30   | ✓         | ✓            | ✓       | ✓       | ✓     |
| 100x35  | ✓         | ✓            | ✓       | ✓       | ✓     |
| 120x40  | ✓         | ✓            | ✓       | ✓       | ✓     |
| 160x50  | ✓         | ✓            | ✓       | ✓       | ✓     |

**Total: 30 test screenshots** to validate responsive behavior

## Implementation Priority

### Phase 1: Foundation (This Session)
1. ✅ Design multi-panel architecture
2. ✅ Create visual test suite
3. ⏳ Create panel base class
4. ⏳ Implement AnimatedAvatar widget
5. ⏳ Build Chat panel (primary)

### Phase 2: Core Panels (Next Session)
1. Documents panel
2. Todo panel
3. Projects panel (basic)
4. Layout manager

### Phase 3: Additional Panels (Sprint 2)
1. Calendar/Reminders panel
2. Notifications panel
3. Voice command integration
4. Configuration UI

### Phase 4: Polish (Sprint 2)
1. Subtle background animations
2. Panel transitions
3. Drag & drop panel reordering
4. Theme integration with panels

## Panel Base Class

```python
# assistant/dashboard/widgets/panel_base.py

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from abc import ABC, abstractmethod

class PanelBase(Static, ABC):
    """
    Base class for all TUI panels.

    Provides:
    - Common styling
    - State management
    - Visibility control
    - Voice command registration
    - Animation support
    """

    # Reactive properties
    is_focused = reactive(False)
    is_minimized = reactive(False)
    notification_count = reactive(0)

    def __init__(self, panel_id: str, title: str, **kwargs):
        super().__init__(**kwargs)
        self.panel_id = panel_id
        self.panel_title = title

    @abstractmethod
    def render_content(self) -> Text:
        """Render panel-specific content"""
        pass

    def render(self) -> Text:
        """Render panel with border and title"""
        result = Text()

        # Border top with title
        border_style = "bold cyan" if self.is_focused else "dim cyan"
        result.append("╔═══", style=border_style)
        result.append(f" {self.panel_title} ", style=f"bold {'yellow' if self.is_focused else 'white'}")

        # Notification badge
        if self.notification_count > 0:
            result.append(f" ({self.notification_count}) ", style="bold red")

        result.append("═" * (self.size.width - len(self.panel_title) - 10), style=border_style)
        result.append("╗\n", style=border_style)

        # Content
        if not self.is_minimized:
            content = self.render_content()
            for line in content.split("\n"):
                result.append("║ ", style=border_style)
                result.append(line)
                result.append(" ║\n", style=border_style)

        # Border bottom
        result.append("╚" + "═" * (self.size.width - 2) + "╝", style=border_style)

        return result

    def focus_panel(self):
        """Focus this panel"""
        self.is_focused = True
        self.refresh()

    def blur_panel(self):
        """Unfocus this panel"""
        self.is_focused = False
        self.refresh()

    def toggle_minimize(self):
        """Minimize/maximize panel"""
        self.is_minimized = not self.is_minimized
        self.refresh()

    def handle_voice_command(self, command: str, args: dict) -> bool:
        """
        Handle voice command directed to this panel.

        Returns:
            True if command was handled, False otherwise
        """
        return False
```

## Subtle Background Animations

### Particle System
```python
# assistant/dashboard/effects/particles.py

class ParticleEffect(Static):
    """
    Subtle particle animation in background.

    Features:
    - Floating dots/stars
    - Very low opacity (0.05-0.1)
    - Slow movement
    - Doesn't distract from content
    """

    def __init__(self, particle_count: int = 20, **kwargs):
        super().__init__(**kwargs)
        self.particles = self._init_particles(particle_count)

    def _init_particles(self, count):
        """Initialize particle positions"""
        import random
        return [
            {
                "x": random.randint(0, 100),
                "y": random.randint(0, 100),
                "dx": random.uniform(-0.5, 0.5),
                "dy": random.uniform(-0.5, 0.5),
                "char": random.choice(["·", "∙", "•", "*"]),
            }
            for _ in range(count)
        ]

    def on_mount(self):
        """Start animation"""
        self.set_interval(0.1, self.update_particles)

    def update_particles(self):
        """Move particles"""
        for p in self.particles:
            p["x"] += p["dx"]
            p["y"] += p["dy"]

            # Wrap around screen
            if p["x"] < 0: p["x"] = 100
            if p["x"] > 100: p["x"] = 0
            if p["y"] < 0: p["y"] = 100
            if p["y"] > 100: p["y"] = 0

        self.refresh()
```

## Next Steps

1. Implement panel base class
2. Create Chat panel
3. Build visual test suite
4. Add AnimatedAvatar widget
5. Test at multiple sizes

This creates the foundation for the most comprehensive, configurable TUI ever built! 🚀
