"""
Persona configuration models.
Personas are loaded from external YAML files, not hardcoded.
"""

from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from pathlib import Path


class PersonalityTraits(BaseModel):
    """Big Five personality traits + custom dimensions"""

    # Big Five (0.0 - 1.0)
    openness: float = Field(0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(0.5, ge=0.0, le=1.0)
    extraversion: float = Field(0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(0.5, ge=0.0, le=1.0)

    # Custom dimensions (0.0 - 1.0)
    formality: float = Field(0.5, ge=0.0, le=1.0)
    enthusiasm: float = Field(0.5, ge=0.0, le=1.0)
    humor: float = Field(0.5, ge=0.0, le=1.0)
    verbosity: float = Field(0.5, ge=0.0, le=1.0)

    def to_prompt_text(self) -> str:
        """Convert traits to natural language for system prompt"""
        descriptions = []

        if self.openness > 0.7:
            descriptions.append("curious and open to new ideas")
        elif self.openness < 0.3:
            descriptions.append("practical and traditional")

        if self.extraversion > 0.7:
            descriptions.append("outgoing and energetic")
        elif self.extraversion < 0.3:
            descriptions.append("reserved and thoughtful")

        if self.formality > 0.7:
            descriptions.append("professional and formal")
        elif self.formality < 0.3:
            descriptions.append("casual and friendly")

        if self.enthusiasm > 0.7:
            descriptions.append("enthusiastic and passionate")
        elif self.enthusiasm < 0.3:
            descriptions.append("calm and measured")

        return ", ".join(descriptions)


class VoiceSettings(BaseModel):
    """Voice-specific settings for MOSHI"""

    pitch: float = Field(1.0, ge=0.5, le=2.0, description="Pitch multiplier")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speaking speed")
    tone: str = Field("neutral", description="Tone descriptor (neutral, warm, professional, etc.)")
    quality: float = Field(0.8, ge=0.0, le=1.0, description="Generation quality (0-1)")


class ThemeColors(BaseModel):
    """Color scheme for persona theme"""
    primary: str = Field("#00D4FF", description="Primary accent color (hex)")
    secondary: str = Field("#FFB300", description="Secondary accent color")
    accent: str = Field("#00FF88", description="Success/accent color")
    background: str = Field("#0A0E14", description="Background color")
    text: str = Field("#C5C8C6", description="Text color")
    dim: str = Field("#5C6773", description="Dim/secondary text")
    error: str = Field("#FF3333", description="Error color")
    warning: str = Field("#FFAA00", description="Warning color")


class AsciiArtConfig(BaseModel):
    """ASCII art configuration"""
    file: Optional[str] = Field(None, description="ASCII art filename in persona dir")
    position: str = Field("header", description="Where to display: header, sidebar, visualizer")
    show_when_speaking: bool = Field(True, description="Show art when persona speaks")


class ThemeStyle(BaseModel):
    """Visual style preferences"""
    border_style: str = Field("heavy", description="Border style: none, light, heavy, double, rounded, dashed")
    glow_effect: bool = Field(True, description="Enable glowing text effects")
    animation_speed: float = Field(1.0, ge=0.1, le=3.0, description="Animation speed multiplier")
    matrix_rain: bool = Field(False, description="Enable matrix-style background")
    pulse_color: bool = Field(True, description="Pulse colors when active")


class ThemeConfig(BaseModel):
    """Complete theme configuration for persona"""
    theme_color: Optional[str] = Field(None, description="Base color for TUI theme (hex or preset name)")
    colors: ThemeColors = Field(default_factory=ThemeColors, description="Color scheme")
    ascii_art: Optional[AsciiArtConfig] = Field(None, description="ASCII art config")
    style: ThemeStyle = Field(default_factory=ThemeStyle, description="Visual style")
    textual: Optional[Dict[str, str]] = Field(None, description="Textual theme overrides")


class PersonaConfig(BaseModel):
    """Complete persona configuration loaded from YAML"""

    # Identity
    name: str = Field(..., description="Persona display name")
    description: str = Field("", description="Brief description of persona")
    version: str = Field("1.0.0", description="Persona version")
    purpose: Optional[str] = Field(None, description="Persona's stated purpose/mission (e.g., 'I am designed to...')")
    agenda: Optional[str] = Field(None, description="Specific tasks/goals the persona focuses on")

    # Personality
    traits: PersonalityTraits = Field(default_factory=PersonalityTraits)

    # Voice
    voice: VoiceSettings = Field(default_factory=VoiceSettings)

    # Theme (NEW)
    theme: ThemeConfig = Field(default_factory=ThemeConfig, description="Visual theme configuration")

    # System prompt
    system_prompt: str = Field("", description="Base system prompt")
    personality_guide: str = Field("", description="Detailed personality guide")

    # Vocabulary customization
    vocabulary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom vocabulary (preferred_phrases, avoid_phrases, etc.)"
    )

    # Wake word (optional override)
    wake_word: Optional[str] = Field(
        default=None,
        description="Custom wake word (overrides default)"
    )

    def get_personality_description(self) -> str:
        """Generate natural language description from personality traits."""
        if not self.traits:
            return "I am a balanced, helpful assistant"
        
        descriptions = []
        
        # Formality
        if self.traits.formality > 0.7:
            descriptions.append("I maintain high professionalism")
        elif self.traits.formality < 0.3:
            descriptions.append("I keep things casual and relaxed")
        
        # Agreeableness
        if self.traits.agreeableness > 0.7:
            descriptions.append("I'm warm and approachable")
        
        # Conscientiousness
        if self.traits.conscientiousness > 0.8:
            descriptions.append("I'm highly organized")
        
        # Enthusiasm
        if self.traits.enthusiasm > 0.7:
            descriptions.append("I bring energy and excitement")
        elif self.traits.enthusiasm < 0.3:
            descriptions.append("I keep calm and measured")
        
        # Neuroticism (invert for calmness)
        if self.traits.neuroticism < 0.3:
            descriptions.append("I stay calm under pressure")
        
        return ", ".join(descriptions) + "."

    def build_system_prompt(self, include_personality: bool = True) -> str:
        """Build complete system prompt with template replacement."""
        # Start with base system prompt
        prompt = self.system_prompt or ""
        
        # Replace template variables
        prompt = prompt.replace("{NAME}", self.name)
        prompt = prompt.replace("{PURPOSE}", self.purpose or self.description)
        prompt = prompt.replace("{AGENDA}", self.agenda or "various tasks")
        prompt = prompt.replace("{PERSONALITY_SUMMARY}", self.get_personality_description())
        
        parts = [prompt] if prompt else []

        # Add personality traits (if not already in template)
        if include_personality and self.traits and "{PERSONALITY_SUMMARY}" not in self.system_prompt:
            trait_desc = self.traits.to_prompt_text()
            if trait_desc:
                parts.append(f"My personality is: {trait_desc}.")

        # Detailed personality guide
        if include_personality and self.personality_guide:
            parts.append(self.personality_guide)

        # Vocabulary preferences
        if self.vocabulary:
            if "preferred_phrases" in self.vocabulary:
                phrases = ", ".join(self.vocabulary["preferred_phrases"])
                parts.append(f"My preferred phrases are: {phrases}.")

            if "avoid_phrases" in self.vocabulary:
                avoid = ", ".join(self.vocabulary["avoid_phrases"])
                parts.append(f"I avoid phrases like: {avoid}.")

        return "\n\n".join(parts)

