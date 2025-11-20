#!/usr/bin/env python3
"""
Test persona loading and management.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant.personas import PersonaManager


def main():
    print("=== Persona System Test ===\n")

    # Find personas directory
    project_root = Path(__file__).parent.parent.parent.parent
    personas_dir = project_root / "packages" / "personas"

    print(f"Personas directory: {personas_dir}")
    print(f"Exists: {personas_dir.exists()}\n")

    # Initialize manager
    manager = PersonaManager(personas_dir)

    # List personas
    personas = manager.list_personas()
    print(f"Discovered {len(personas)} persona(s):")
    for name in personas:
        persona = manager.get_persona(name)
        print(f"  - {name} (v{persona.version}): {persona.description}")

    if not personas:
        print("\nNo personas found. Create one in packages/personas/")
        print("Example: packages/personas/jarvis/theme.yaml")
        return 1

    # Test loading first persona
    print(f"\n--- Testing Persona: {personas[0]} ---\n")
    manager.set_current_persona(personas[0])
    persona = manager.current_persona

    # Display persona details
    print(f"Name: {persona.name}")
    print(f"Description: {persona.description}")
    print(f"Version: {persona.version}")
    print(f"Wake word: {persona.wake_word or '(default)'}")

    print(f"\nTraits:")
    print(f"  Formality: {persona.traits.formality:.2f}")
    print(f"  Enthusiasm: {persona.traits.enthusiasm:.2f}")
    print(f"  Extraversion: {persona.traits.extraversion:.2f}")

    print(f"\nVoice Settings:")
    print(f"  Pitch: {persona.voice.pitch}x")
    print(f"  Speed: {persona.voice.speed}x")
    print(f"  Tone: {persona.voice.tone}")

    # Build system prompt
    print(f"\n--- System Prompt (first 500 chars) ---\n")
    prompt = persona.build_system_prompt()
    print(prompt[:500])
    if len(prompt) > 500:
        print(f"... ({len(prompt)} chars total)")

    print("\n=== All tests passed! ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
