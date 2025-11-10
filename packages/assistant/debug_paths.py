#!/usr/bin/env python3
"""Debug path resolution"""
from pathlib import Path

# Simulate what main.py does
main_file = Path(__file__).parent / "assistant" / "main.py"
print(f"main_file would be: {main_file}")

personas_dir_calculation = Path(main_file).parent.parent.parent / "personas"
print(f"personas_dir would be: {personas_dir_calculation}")
print(f"personas_dir exists: {personas_dir_calculation.exists()}")

if personas_dir_calculation.exists():
    print(f"\nContents of personas_dir:")
    for item in personas_dir_calculation.iterdir():
        print(f"  - {item.name}")
        if item.is_dir():
            theme_file = item / "theme.yaml"
            print(f"    theme.yaml exists: {theme_file.exists()}")
