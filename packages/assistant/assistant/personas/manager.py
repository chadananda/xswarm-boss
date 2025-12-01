"""
Persona manager - loads and manages external personas.
"""

from pathlib import Path
from typing import Dict, Optional, List
import yaml
from .config import PersonaConfig


class PersonaManager:
    """
    Manages loading and switching between personas.
    Personas are loaded from external YAML files.
    """

    def __init__(self, personas_dir: Path):
        """
        Initialize persona manager.

        Args:
            personas_dir: Directory containing persona folders
                          (e.g., /path/to/packages/personas/)
        """
        self.personas_dir = Path(personas_dir)
        self.personas: Dict[str, PersonaConfig] = {}
        self.current_persona: Optional[PersonaConfig] = None

        # Discover and load all personas
        self.discover_personas()

    def discover_personas(self) -> List[str]:
        """
        Discover all available personas in personas directory.

        Each persona should be in a subdirectory with a theme.yaml file:
            personas/
                persona-name/
                    theme.yaml         # Main config
                    personality.md     # Optional detailed guide
                    vocabulary.yaml    # Optional vocabulary

        Returns:
            List of discovered persona names
        """
        if not self.personas_dir.exists():
            return []

        discovered = []

        for persona_dir in self.personas_dir.iterdir():
            if not persona_dir.is_dir():
                continue

            theme_file = persona_dir / "theme.yaml"
            if not theme_file.exists():
                continue

            try:
                persona = self.load_persona_from_dir(persona_dir)
                self.personas[persona.name] = persona
                discovered.append(persona.name)
            except Exception:
                pass  # Skip failed persona loads

        return discovered

    def load_persona_from_dir(self, persona_dir: Path) -> PersonaConfig:
        """
        Load persona from directory.

        Expected structure:
            persona-dir/
                theme.yaml          # Main config (REQUIRED)
                personality.md      # Detailed guide (optional)
                vocabulary.yaml     # Vocabulary (optional)
        """
        theme_file = persona_dir / "theme.yaml"
        personality_file = persona_dir / "personality.md"
        vocab_file = persona_dir / "vocabulary.yaml"

        # Load main theme config
        with open(theme_file, 'r') as f:
            theme_data = yaml.safe_load(f)

        # Load personality guide if exists
        if personality_file.exists():
            with open(personality_file, 'r') as f:
                theme_data['personality_guide'] = f.read()

        # Load vocabulary if exists
        if vocab_file.exists():
            with open(vocab_file, 'r') as f:
                vocab_data = yaml.safe_load(f)
                theme_data['vocabulary'] = vocab_data

        # Create PersonaConfig
        persona = PersonaConfig(**theme_data)

        return persona

    def get_persona(self, name: str) -> Optional[PersonaConfig]:
        """
        Get persona by name (case-insensitive).
        
        Args:
            name: Persona name (e.g. "Jarvis", "jarvis", "JARVIS")
            
        Returns:
            PersonaConfig or None
        """
        # Try exact match first
        if name in self.personas:
            return self.personas[name]
            
        # Try case-insensitive match
        name_lower = name.lower()
        for p_name, p_config in self.personas.items():
            if p_name.lower() == name_lower:
                return p_config

        return None

    def get_current_persona(self) -> Optional[PersonaConfig]:
        """Get the currently active persona"""
        return self.current_persona

    def set_current_persona(self, name: str) -> bool:
        """
        Set current active persona.

        Returns:
            True if persona found and set, False otherwise
        """
        persona = self.get_persona(name)
        if persona:
            self.current_persona = persona
            return True
        else:
            return False

    def list_personas(self) -> List[str]:
        """List all available persona names"""
        return list(self.personas.keys())

    def reload_persona(self, name: str) -> bool:
        """
        Reload a persona from disk (for hot-reloading).

        Returns:
            True if reload successful
        """
        persona_dir = self.personas_dir / name
        if not persona_dir.exists():
            return False

        try:
            persona = self.load_persona_from_dir(persona_dir)
            self.personas[persona.name] = persona

            # Update current if it's the active one
            if self.current_persona and self.current_persona.name == name:
                self.current_persona = persona

            return True
        except Exception:
            return False
