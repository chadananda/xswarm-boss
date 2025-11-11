# 🎨 Flexible Theming System

The TUI now has a **super flexible theming system** - change ONE base color and the entire interface adapts automatically!

## Quick Start

### Option 1: Use a Preset Theme

Edit your `config.yaml`:

```yaml
theme_base_color: cyan  # Use any preset name
```

Available presets:
- `blue-gray` (default) - Cool blue-gray
- `slate` - Neutral slate gray
- `cyan` - Subtle cyan tint
- `purple` - Muted purple
- `green` - Subtle green
- `amber` - Warm amber
- `rose` - Soft rose
- `steel` - Cool steel blue

### Option 2: Use Any Custom Color

Edit your `config.yaml`:

```yaml
theme_base_color: '#ff6b6b'  # Use ANY hex color
```

The system will automatically generate a 5-shade palette with perfect contrast!

## How It Works

1. **You pick ONE base color** (hex or preset name)
2. **System generates 5 shades** with optimal brightness levels:
   - `shade-5` - Lightest (highlights, active states)
   - `shade-4` - Light (primary text, normal emphasis)
   - `shade-3` - Medium (labels, separators)
   - `shade-2` - Dark (secondary text, dimmed elements)
   - `shade-1` - Darkest (backgrounds, subtle text)
3. **All UI components adapt** - borders, text, visualizers, everything!

## Theme Examples

### Blue-Gray (Default)
```yaml
theme_base_color: blue-gray  # or '#8899aa'
```
Cool, professional blue-gray tones.

### Cyan
```yaml
theme_base_color: cyan  # or '#5eb3b3'
```
Fresh cyan with subtle blue-green tints.

### Purple
```yaml
theme_base_color: purple  # or '#9b8cbb'
```
Elegant muted purple shades.

### Custom Red
```yaml
theme_base_color: '#ff6b6b'
```
Warm red tones - fully custom!

## Testing Themes

Run the theme demo to see all available options:

```bash
python demo_themes.py
```

This shows:
- All 8 preset themes with their generated palettes
- Custom color examples
- How to use themes in your config
- CSS variable generation

## Technical Details

### Color Generation

The theme system uses smart color generation:
1. **Desaturation** - Reduces saturation by 30% for subtlety
2. **Brightness Scaling** - Generates 5 levels from dark to light
3. **Contrast Optimization** - Ensures readable text on all backgrounds

### CSS Variables

The generated CSS variables:

```css
$shade-5: #c8c2d4;  /* Lightest */
$shade-4: #9d93b3;  /* Light */
$shade-3: #72648f;  /* Medium */
$shade-2: #534a69;  /* Dark */
$shade-1: #352f42;  /* Darkest */
```

All UI components reference these variables, so changing the theme updates everything instantly!

### Components Themed

Everything adapts to your theme:
- ✅ Borders and dividers
- ✅ Text colors (all emphasis levels)
- ✅ Activity feed messages
- ✅ Status indicators
- ✅ Progress bars
- ✅ System stats
- ✅ Voice visualizer (circular + waveforms)
- ✅ All 5 waveform styles (scrolling, bars, wave chars, line, dots)

## Benefits

✅ **One color controls everything** - No more tweaking individual components
✅ **8 beautiful presets** - Instant professional themes
✅ **Unlimited custom themes** - Use ANY color you want
✅ **Perfect contrast** - Auto-generated shades always look good
✅ **Zero code changes** - Just update config.yaml
✅ **Consistent design** - All components use the same palette

## Examples in Config

### Using a Preset
```yaml
# config.yaml
device: auto
theme_base_color: purple  # Just add this line!
wake_word: jarvis
# ... rest of config
```

### Using Custom Color
```yaml
# config.yaml
device: auto
theme_base_color: '#4ecdc4'  # Beautiful turquoise!
wake_word: jarvis
# ... rest of config
```

## Advanced: Creating Custom Presets

Want to add your own named preset? Edit `assistant/dashboard/theme.py`:

```python
THEME_PRESETS = {
    "my-theme": "#abcdef",  # Add your custom preset
    # ... existing presets
}
```

Then use it:
```yaml
theme_base_color: my-theme
```

---

**🎨 Happy theming! Change one color, transform the entire interface.**
