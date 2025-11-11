"""
Demo script showing the flexible theming system.

Change ONE base color and the entire interface adapts!
"""

from assistant.dashboard.theme import (
    generate_palette,
    get_theme_preset,
    THEME_PRESETS,
    generate_css_variables
)


def demo_theme_presets():
    """Show all available theme presets."""
    print("=" * 80)
    print("🎨 AVAILABLE THEME PRESETS")
    print("=" * 80)
    print()

    for theme_name, base_color in THEME_PRESETS.items():
        print(f"📦 Theme: {theme_name.upper()}")
        print(f"   Base color: {base_color}")
        palette = get_theme_preset(theme_name)
        print(f"   Generated palette:")
        print(f"     shade-1 (darkest):  {palette.shade_1}")
        print(f"     shade-2 (dark):     {palette.shade_2}")
        print(f"     shade-3 (medium):   {palette.shade_3}")
        print(f"     shade-4 (light):    {palette.shade_4}")
        print(f"     shade-5 (lightest): {palette.shade_5}")
        print()


def demo_custom_theme():
    """Show how to create custom themes from any color."""
    print("=" * 80)
    print("🎨 CUSTOM THEME EXAMPLES")
    print("=" * 80)
    print()

    custom_colors = [
        ("#ff6b6b", "Warm Red"),
        ("#4ecdc4", "Turquoise"),
        ("#ffe66d", "Golden Yellow"),
        ("#a8dadc", "Powder Blue"),
        ("#f1faee", "Off White"),
    ]

    for color, name in custom_colors:
        print(f"🎨 {name} (base: {color})")
        palette = generate_palette(color)
        print(f"   shade-1: {palette.shade_1}")
        print(f"   shade-2: {palette.shade_2}")
        print(f"   shade-3: {palette.shade_3}")
        print(f"   shade-4: {palette.shade_4}")
        print(f"   shade-5: {palette.shade_5}")
        print()


def demo_how_to_use():
    """Show how to use themes in practice."""
    print("=" * 80)
    print("📚 HOW TO USE THEMES")
    print("=" * 80)
    print()

    print("1️⃣  Using a preset theme:")
    print("   Edit your config.yaml:")
    print("   ```yaml")
    print("   theme_base_color: cyan  # Use any preset name")
    print("   ```")
    print()

    print("2️⃣  Using a custom color:")
    print("   Edit your config.yaml:")
    print("   ```yaml")
    print("   theme_base_color: '#ff6b6b'  # Use any hex color")
    print("   ```")
    print()

    print("3️⃣  Available presets:")
    print("   " + ", ".join(THEME_PRESETS.keys()))
    print()

    print("4️⃣  That's it! The entire interface adapts automatically!")
    print()


def demo_css_generation():
    """Show how CSS variables are generated."""
    print("=" * 80)
    print("🎨 CSS VARIABLE GENERATION")
    print("=" * 80)
    print()

    print("When you set a theme, these CSS variables are automatically generated:")
    print()

    palette = get_theme_preset("purple")
    css = generate_css_variables(palette)
    print(css)

    print("All UI components reference these variables, so changing the theme")
    print("updates everything instantly!")
    print()


if __name__ == "__main__":
    demo_theme_presets()
    print("\n" * 2)
    demo_custom_theme()
    print("\n" * 2)
    demo_how_to_use()
    print("\n" * 2)
    demo_css_generation()

    print("=" * 80)
    print("✨ SUMMARY")
    print("=" * 80)
    print()
    print("The theming system is now SUPER flexible:")
    print()
    print("✅ One base color controls the entire interface")
    print("✅ 8 predefined theme presets available")
    print("✅ Use ANY hex color for custom themes")
    print("✅ All 5 shades auto-generated with perfect contrast")
    print("✅ Change theme in config.yaml - no code changes needed")
    print()
    print("🎨 Happy theming!")
    print()
