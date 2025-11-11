"""
Dynamic color theme system for the TUI.

Generates a 5-shade grayscale palette from a single base color,
making the entire interface easily themeable.
"""

from typing import Tuple
from dataclasses import dataclass
import colorsys


@dataclass
class ColorPalette:
    """5-shade color palette generated from a base color."""
    shade_1: str  # Darkest
    shade_2: str  # Dark
    shade_3: str  # Medium
    shade_4: str  # Light
    shade_5: str  # Lightest


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def adjust_brightness(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """
    Adjust brightness of an RGB color by a factor.

    Args:
        rgb: RGB color tuple (0-255)
        factor: Brightness multiplier (< 1 = darker, > 1 = brighter)

    Returns:
        Adjusted RGB tuple
    """
    # Convert to HSL for better brightness control
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Adjust lightness
    l = max(0.0, min(1.0, l * factor))

    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return tuple(int(x * 255) for x in (r, g, b))


def desaturate(rgb: Tuple[int, int, int], amount: float = 0.5) -> Tuple[int, int, int]:
    """
    Desaturate a color towards grayscale.

    Args:
        rgb: RGB color tuple (0-255)
        amount: Desaturation amount (0.0 = original, 1.0 = full grayscale)

    Returns:
        Desaturated RGB tuple
    """
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    # Reduce saturation
    s = s * (1.0 - amount)

    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return tuple(int(x * 255) for x in (r, g, b))


def generate_palette(base_color: str) -> ColorPalette:
    """
    Generate a 5-shade palette from a base color.

    The palette is designed to work well for UI elements with:
    - shade-1 (darkest): Background elements, subtle text
    - shade-2 (dark): Secondary text, dimmed elements
    - shade-3 (medium): Labels, separators, medium emphasis
    - shade-4 (light): Primary text, normal emphasis
    - shade-5 (lightest): Highlights, active states, maximum emphasis

    Args:
        base_color: Hex color string (e.g., "#8899aa" or "8899aa")

    Returns:
        ColorPalette with 5 shades from darkest to lightest
    """
    # Parse base color
    rgb = hex_to_rgb(base_color)

    # Desaturate the base color for a more subtle palette
    rgb = desaturate(rgb, amount=0.3)

    # Generate 5 shades by adjusting brightness
    # Base color becomes shade-4 (light)
    shade_1 = rgb_to_hex(adjust_brightness(rgb, 0.35))  # Very dark
    shade_2 = rgb_to_hex(adjust_brightness(rgb, 0.55))  # Dark
    shade_3 = rgb_to_hex(adjust_brightness(rgb, 0.75))  # Medium
    shade_4 = rgb_to_hex(rgb)                            # Light (base)
    shade_5 = rgb_to_hex(adjust_brightness(rgb, 1.25))  # Lightest

    return ColorPalette(
        shade_1=shade_1,
        shade_2=shade_2,
        shade_3=shade_3,
        shade_4=shade_4,
        shade_5=shade_5
    )


def generate_css_variables(palette: ColorPalette) -> str:
    """
    Generate CSS variable declarations from a palette.

    Args:
        palette: ColorPalette instance

    Returns:
        CSS string with variable declarations
    """
    return f"""/* ▓▒░ DYNAMIC SHADE PALETTE ░▒▓ */
$shade-5: {palette.shade_5};  /* Lightest */
$shade-4: {palette.shade_4};  /* Light */
$shade-3: {palette.shade_3};  /* Medium */
$shade-2: {palette.shade_2};  /* Dark */
$shade-1: {palette.shade_1};  /* Darkest */
"""


# Predefined theme presets
THEME_PRESETS = {
    "blue-gray": "#8899aa",      # Current default - cool blue-gray
    "slate": "#6b7b8c",           # Neutral slate gray
    "cyan": "#5eb3b3",            # Subtle cyan tint
    "purple": "#9b8cbb",          # Muted purple
    "green": "#88aa88",           # Subtle green
    "amber": "#aa9977",           # Warm amber
    "rose": "#aa8899",            # Soft rose
    "steel": "#778899",           # Cool steel blue
}


def get_theme_preset(name: str) -> ColorPalette:
    """
    Get a predefined theme palette by name.

    Args:
        name: Theme preset name (e.g., "blue-gray", "slate", "cyan")

    Returns:
        ColorPalette for the theme

    Raises:
        KeyError: If theme name not found
    """
    if name not in THEME_PRESETS:
        raise KeyError(f"Theme '{name}' not found. Available: {list(THEME_PRESETS.keys())}")

    return generate_palette(THEME_PRESETS[name])


if __name__ == "__main__":
    # Demo: Generate palettes for all presets
    print("🎨 Theme Palette Generator\n")

    for theme_name, base_color in THEME_PRESETS.items():
        print(f"Theme: {theme_name.upper()} (base: {base_color})")
        palette = generate_palette(base_color)
        print(f"  shade-1 (darkest):  {palette.shade_1}")
        print(f"  shade-2 (dark):     {palette.shade_2}")
        print(f"  shade-3 (medium):   {palette.shade_3}")
        print(f"  shade-4 (light):    {palette.shade_4}")
        print(f"  shade-5 (lightest): {palette.shade_5}")
        print()
