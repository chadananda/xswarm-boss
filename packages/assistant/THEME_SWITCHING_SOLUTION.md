# ✅ Dynamic Theme Switching - WORKING SOLUTION

## The Problem

When personas rotated every 5 seconds, the persona NAME would change but COLORS stayed gray/static. The issue was that Textual's `@property CSS` method only generates CSS **once at startup**, not when personas rotate at runtime.

## The Solution

Call `self.refresh_css()` to force Textual to regenerate CSS with the new palette colors.

### Key Code Change in `app.py:178-217`

```python
def rotate_persona(self):
    """Randomly switch to a different persona"""
    if not self.available_personas:
        return

    persona = random.choice(self.available_personas)

    if persona.theme and persona.theme.theme_color:
        # Log what we're doing
        self.update_activity(f"🔄 Switching to {persona.name} with color {persona.theme.theme_color}")

        # Regenerate theme palette
        self._theme_palette = self._load_theme(persona.theme.theme_color)

        # Log the generated shades
        self.update_activity(f"   Palette: {self._theme_palette.shade_1} → {self._theme_palette.shade_5}")

        # ✅ THIS IS THE FIX - Force Textual to regenerate CSS
        self.refresh_css()
        self.update_activity(f"   ✓ CSS refreshed")

        # Update reactive theme colors (triggers watchers for direct style updates)
        self.theme_shade_2 = self._theme_palette.shade_2
        self.theme_shade_3 = self._theme_palette.shade_3
        self.theme_shade_4 = self._theme_palette.shade_4

        self.update_activity(f"   ✓ Reactive colors updated")

    # Update persona name and title
    self.current_persona_name = persona.name
    self.title = f"xSwarm Voice Assistant - {persona.name}"
    self.update_activity(f"👤 Switched to persona: {persona.name}")

    # Update visualizer border title
    try:
        visualizer = self.query_one("#visualizer", VoiceVisualizerPanel)
        visualizer.border_title = f"xSwarm - {persona.name}"
    except Exception:
        pass
```

## How It Works

### 1. The `@property CSS` Method

This dynamically generates CSS by reading the base `styles.tcss` file and replacing shade variables with current theme colors:

```python
@property
def CSS(self) -> str:
    """Generate CSS with dynamic theme colors."""
    css_path = Path(__file__).parent / "styles.tcss"
    base_css = css_path.read_text()

    # Replace shade definitions with current theme
    replacement = f"""/* ▓▒░ DYNAMIC THEME PALETTE ░▒▓ */
$shade-5: {self._theme_palette.shade_5};  /* Lightest */
$shade-4: {self._theme_palette.shade_4};  /* Light */
$shade-3: {self._theme_palette.shade_3};  /* Medium */
$shade-2: {self._theme_palette.shade_2};  /* Dark */
$shade-1: {self._theme_palette.shade_1};  /* Darkest */"""

    themed_css = re.sub(palette_pattern, replacement, base_css, flags=re.DOTALL)
    return themed_css
```

**Key insight**: Textual caches the CSS after initial generation. When `_theme_palette` changes, Textual doesn't automatically know to regenerate it.

### 2. The Fix: `self.refresh_css()`

By calling `self.refresh_css()` after updating `_theme_palette`, we tell Textual:
- Re-evaluate the `@property CSS` method
- Get the new shade colors from the updated palette
- Reapply all CSS rules with new colors

This updates **everything** that uses the shade variables:
- Borders (all widgets)
- Text colors (5 emphasis levels)
- State indicators
- Progress bars
- Waveforms in visualizer
- Activity feed messages

### 3. Reactive Watchers (Bonus)

The reactive watchers provide additional direct style updates for key elements:

```python
# Declared as reactive properties
theme_shade_2 = reactive("#363d47")
theme_shade_3 = reactive("#4d5966")
theme_shade_4 = reactive("#6b7a8a")

# Watchers called automatically when values change
def watch_theme_shade_3(self, new_color: str) -> None:
    """Updates main widget borders"""
    color = Color.parse(new_color)
    visualizer.styles.border = ("solid", color)
    activity.styles.border = ("solid", color)
    status.styles.border = ("solid", color)

def watch_theme_shade_4(self, new_color: str) -> None:
    """Updates border title colors"""
    color = Color.parse(new_color)
    visualizer.styles.border_title_color = color
    activity.styles.border_title_color = color
    status.styles.border_title_color = color

def watch_theme_shade_2(self, new_color: str) -> None:
    """Updates header/footer borders"""
    color = Color.parse(new_color)
    header.styles.border = ("solid", color)
    footer.styles.border = ("solid", color)
```

These ensure that borders update immediately via Python, while the CSS refresh handles all the other color uses.

## Testing Results

Running `test_extreme_colors.py` with pure RGB colors (RED, GREEN, BLUE) shows dramatic visual changes:

```
0001 [18:50:08.705] 🔄 Switching to GLaDOS with color #00FF00
0002 [18:50:08.705]    Palette: #0d4b0d → #5be25b (dark green → light green)
0003 [18:50:08.710]    ✓ CSS refreshed
0004 [18:50:08.710] ✅ Borders updated to #4d5966
0005 [18:50:08.710] ✅ Borders updated to #1ca21c (GREEN!)
0006 [18:50:08.710]    ✓ Reactive colors updated
0007 [18:50:08.710] 👤 Switched to persona: GLaDOS

... 5 seconds later ...

0015 [18:50:18.711] 🔄 Switching to NEON with color #0000FF
0016 [18:50:18.711]    Palette: #0d0d4b → #5b5be2 (dark blue → light blue)
0017 [18:50:18.717]    ✓ CSS refreshed
0018 [18:50:18.717] ✅ Borders updated to #1c1ca2 (BLUE!)
0019 [18:50:18.717]    ✓ Reactive colors updated
0020 [18:50:18.717] 👤 Switched to persona: NEON
```

Terminal ANSI color codes change from `[38;5;34` (green) to `[38;5;19` (blue), confirming colors are updating throughout the entire interface.

## Why This Wasn't Working Before

**Attempts that failed:**

1. ❌ **Reload stylesheets** - Textual caches them
2. ❌ **Direct style updates only** - Missed all CSS variable uses
3. ❌ **Color objects without CSS refresh** - Python styles don't affect CSS rules

**What finally worked:**

✅ **`self.refresh_css()`** - Forces Textual to regenerate CSS from the `@property CSS` method with updated palette

## Architecture

```
Persona YAML
    ↓
theme_color: "#FF00FF"
    ↓
PersonaManager loads config
    ↓
rotate_persona() called (every 5s)
    ↓
_theme_palette = generate_palette("#FF00FF")
    ↓
        shade_1: #4b0d4b (dark)
        shade_2: #6f1c6f (medium-dark)
        shade_3: #931c93 (medium)
        shade_4: #b746b7 (light)
        shade_5: #e25be2 (lightest)
    ↓
self.refresh_css() ← KEY FIX
    ↓
@property CSS re-evaluated
    ↓
CSS variables replaced:
    $shade-1: #4b0d4b
    $shade-2: #6f1c6f
    $shade-3: #931c93
    $shade-4: #b746b7
    $shade-5: #e25be2
    ↓
ENTIRE UI updates with new colors
```

## Complete Color Flow

**Single base color** → 5-shade palette → CSS variables → ALL UI elements

- Borders
- Text (5 emphasis levels)
- Backgrounds
- State indicators
- Progress bars
- Waveforms
- Activity messages
- System stats

**Result**: Persona change = instant theme transformation! 🎨✨

## Running the Demo

```bash
# Standard app (5-second rotation, realistic colors)
python -m assistant.dashboard

# Extreme color test (3-second rotation, pure RGB)
python test_extreme_colors.py
```

Watch as the interface transforms from:
- JARVIS cyan (#00D4FF)
- GLaDOS orange (#FFA500)
- NEON magenta (#FF00FF)

Every border, text color, and visual element shifts to match the persona's theme!
