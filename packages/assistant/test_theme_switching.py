"""Test theme switching with VERY obvious colors"""

from assistant.dashboard.theme import generate_palette

# Test with extreme colors that should be super visible
test_colors = [
    ("#FF0000", "RED"),
    ("#00FF00", "GREEN"),
    ("#0000FF", "BLUE"),
    ("#FFFF00", "YELLOW"),
    ("#FF00FF", "MAGENTA"),
]

print("🎨 TESTING EXTREME COLOR PALETTES")
print("=" * 80)
print()

for color, name in test_colors:
    print(f"🎨 {name} (base: {color})")
    palette = generate_palette(color)
    print(f"   shade-1 (darkest):  {palette.shade_1}")
    print(f"   shade-2 (dark):     {palette.shade_2}")
    print(f"   shade-3 (medium):   {palette.shade_3}")
    print(f"   shade-4 (light):    {palette.shade_4}")
    print(f"   shade-5 (lightest): {palette.shade_5}")
    print()

print("=" * 80)
print("If you see these extreme colors in the TUI, theme switching works!")
print("If everything stays gray, we need to debug further.")
