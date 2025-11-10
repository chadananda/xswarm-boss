#!/usr/bin/env python3
"""Debug persona loading"""
from pathlib import Path
import sys

sys.path.insert(0, '.')

from assistant.personas.manager import PersonaManager

# Test personas loading
personas_dir = Path(__file__).parent.parent / "personas"
print(f"Personas dir: {personas_dir}")
print(f"Exists: {personas_dir.exists()}")

if personas_dir.exists():
    print(f"\nContents:")
    for item in sorted(personas_dir.iterdir()):
        if item.is_dir():
            theme = item / "theme.yaml"
            print(f"  {item.name}: theme.yaml exists = {theme.exists()}")

print("\nInitializing PersonaManager...")
manager = PersonaManager(personas_dir)

print(f"\nDiscovered personas: {manager.list_personas()}")
print(f"Total count: {len(manager.list_personas())}")

if len(manager.list_personas()) > 0:
    print("\nPersona details:")
    for name in manager.list_personas():
        persona = manager.get_persona(name)
        print(f"  - {name}: version={persona.version}")

    # Test get_current_persona
    print("\nTesting get_current_persona():")
    manager.set_current_persona('Cylon')
    current = manager.get_current_persona()
    if current:
        print(f"✅ get_current_persona() works: {current.name}")
    else:
        print("❌ get_current_persona() returned None")
