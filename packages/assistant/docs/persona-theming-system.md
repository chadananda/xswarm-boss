# Persona Theming System Design

## Overview
Enable users to customize the xswarm TUI appearance through persona-specific themes. Each persona has its own color scheme, ASCII art, and visual styling, allowing users to "rice" their xswarm installation.

## User Requirements
1. Color scheme adapts to system colors when on Omarchy platform
2. Cool theming options as part of each persona
3. ASCII art image of each persona in the TUI (speaking visual)
4. Users can heavily customize ("rice") their xswarm TUI
5. Leverage Textual's theming capabilities (don't roll our own)

## Architecture

### 1. Theme Configuration Structure

Each persona has a `theme.yaml` file with the following structure:

```yaml
# Basic persona info
name: "JARVIS"
description: "Professional AI assistant inspired by Iron Man's JARVIS"
version: "1.0.0"

# Personality traits (existing)
traits:
  openness: 0.8
  conscientiousness: 0.9
  # ... etc

# Voice settings (existing)
voice:
  pitch: 1.0
  speed: 1.0
  tone: "professional"

# NEW: Theme configuration
theme:
  # Color scheme
  colors:
    primary: "#00D4FF"        # Neon cyan (JARVIS blue)
    secondary: "#FFB300"      # Gold accent
    accent: "#00FF88"         # Success green
    background: "#0A0E14"     # Dark background
    text: "#C5C8C6"           # Light text
    dim: "#5C6773"            # Dim text
    error: "#FF3333"          # Error red
    warning: "#FFAA00"        # Warning orange

  # ASCII art
  ascii_art:
    file: "jarvis.txt"        # Filename in persona directory
    position: "header"        # Where to show: header, sidebar, visualizer
    show_when_speaking: true  # Show when persona is speaking

  # Visual style
  style:
    border_style: "heavy"     # none, light, heavy, double, rounded, dashed
    glow_effect: true         # Glowing text effect
    animation_speed: 1.0      # Speed multiplier for animations
    matrix_rain: false        # Matrix-style background
    pulse_color: true         # Pulse colors when active

  # Textual theme overrides (leverage framework)
  textual:
    accent: "$primary"
    success: "$accent"
    error: "$error"
    warning: "$warning"
```

### 2. Extended PersonaConfig Model

Add `ThemeConfig` class to `assistant/personas/config.py`:

```python
class ThemeColors(BaseModel):
    """Color scheme for persona theme"""
    primary: str = Field("#00D4FF", description="Primary accent color")
    secondary: str = Field("#FFB300", description="Secondary accent")
    accent: str = Field("#00FF88", description="Success/accent color")
    background: str = Field("#0A0E14", description="Background color")
    text: str = Field("#C5C8C6", description="Text color")
    dim: str = Field("#5C6773", description="Dim/secondary text")
    error: str = Field("#FF3333", description="Error color")
    warning: str = Field("#FFAA00", description="Warning color")

class AsciiArtConfig(BaseModel):
    """ASCII art configuration"""
    file: Optional[str] = None
    position: str = Field("header", description="header, sidebar, visualizer")
    show_when_speaking: bool = True

class ThemeStyle(BaseModel):
    """Visual style preferences"""
    border_style: str = Field("heavy", description="Border style")
    glow_effect: bool = True
    animation_speed: float = Field(1.0, ge=0.1, le=3.0)
    matrix_rain: bool = False
    pulse_color: bool = True

class ThemeConfig(BaseModel):
    """Complete theme configuration"""
    colors: ThemeColors = Field(default_factory=ThemeColors)
    ascii_art: Optional[AsciiArtConfig] = None
    style: ThemeStyle = Field(default_factory=ThemeStyle)
    textual: Optional[Dict[str, str]] = None  # Textual theme overrides

class PersonaConfig(BaseModel):
    # ... existing fields ...
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
```

### 3. System Color Detection (Omarchy Platform)

Add platform detection to automatically adapt colors:

```python
# assistant/dashboard/platform.py

import platform
import subprocess
from typing import Optional, Dict

class PlatformTheme:
    """Detect system theme colors (Omarchy, macOS, GTK, etc.)"""

    @staticmethod
    def detect_platform() -> str:
        """Detect current platform"""
        system = platform.system()
        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            # Check for Omarchy-specific env or files
            if PlatformTheme._is_omarchy():
                return "omarchy"
            return "linux"
        return "unknown"

    @staticmethod
    def _is_omarchy() -> bool:
        """Check if running on Omarchy"""
        # Check for Omarchy-specific environment variables or files
        import os
        return os.path.exists("/etc/omarchy") or "OMARCHY" in os.environ

    @staticmethod
    def get_system_colors() -> Optional[Dict[str, str]]:
        """Get system accent colors if available"""
        platform_name = PlatformTheme.detect_platform()

        if platform_name == "omarchy":
            return PlatformTheme._get_omarchy_colors()
        elif platform_name == "macos":
            return PlatformTheme._get_macos_colors()
        elif platform_name == "linux":
            return PlatformTheme._get_gtk_colors()

        return None

    @staticmethod
    def _get_omarchy_colors() -> Dict[str, str]:
        """Extract colors from Omarchy system theme"""
        # TODO: Implement Omarchy color detection
        # This would read from Omarchy's theme config
        return {
            "primary": "#00D4FF",
            "secondary": "#FFB300",
            "accent": "#00FF88"
        }

    @staticmethod
    def _get_macos_colors() -> Dict[str, str]:
        """Get macOS accent color"""
        try:
            # Read macOS accent color preference
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleAccentColor"],
                capture_output=True, text=True
            )
            # Map macOS accent to hex colors
            accent_map = {
                "0": "#FF3B30",  # Red
                "1": "#FF9500",  # Orange
                # ... etc
            }
            accent_id = result.stdout.strip()
            return {"primary": accent_map.get(accent_id, "#00D4FF")}
        except:
            return {}

    @staticmethod
    def _get_gtk_colors() -> Dict[str, str]:
        """Get GTK theme colors"""
        # Read from ~/.config/gtk-3.0/gtk.css or dconf
        return {}
```

### 4. Theme Application in TUI

Integrate themes into widgets:

```python
# assistant/dashboard/app.py

class VoiceAssistantApp(App):
    def __init__(self, config: Config, personas_dir: Path):
        super().__init__()
        self.config = config
        self.personas_dir = personas_dir
        self.persona_manager = PersonaManager(personas_dir)

        # Load current persona theme
        self.current_theme: Optional[ThemeConfig] = None
        self.load_persona_theme()

    def load_persona_theme(self):
        """Load theme for current persona"""
        persona_name = self.config.default_persona or "JARVIS"
        persona = self.persona_manager.get_persona(persona_name)

        if persona and persona.theme:
            self.current_theme = persona.theme

            # Apply system colors if on Omarchy
            if PlatformTheme.detect_platform() == "omarchy":
                system_colors = PlatformTheme.get_system_colors()
                if system_colors:
                    self._merge_system_colors(system_colors)

            # Apply theme to app
            self._apply_theme()

    def _merge_system_colors(self, system_colors: Dict[str, str]):
        """Merge system colors into persona theme"""
        if self.current_theme:
            for key, value in system_colors.items():
                if hasattr(self.current_theme.colors, key):
                    setattr(self.current_theme.colors, key, value)

    def _apply_theme(self):
        """Apply theme colors to widgets"""
        if not self.current_theme:
            return

        # Get all widgets and update their color schemes
        header = self.query_one("#header", CyberpunkHeader)
        header.set_theme(self.current_theme)

        visualizer = self.query_one("#visualizer", CyberpunkVisualizer)
        visualizer.set_theme(self.current_theme)

        # ... etc for all widgets
```

### 5. ASCII Art Integration

Show ASCII art when persona speaks:

```python
# assistant/dashboard/widgets/persona_avatar.py

from textual.widgets import Static
from rich.text import Text
from pathlib import Path

class PersonaAvatar(Static):
    """Display ASCII art of current persona"""

    def __init__(self, persona_dir: Path, theme: ThemeConfig, **kwargs):
        super().__init__(**kwargs)
        self.persona_dir = persona_dir
        self.theme = theme
        self.ascii_art: Optional[str] = None
        self.is_speaking = False

        # Load ASCII art
        if theme.ascii_art and theme.ascii_art.file:
            self._load_ascii_art()

    def _load_ascii_art(self):
        """Load ASCII art from file"""
        art_file = self.persona_dir / self.theme.ascii_art.file
        if art_file.exists():
            with open(art_file, 'r') as f:
                self.ascii_art = f.read()

    def set_speaking(self, speaking: bool):
        """Update speaking state"""
        self.is_speaking = speaking
        self.refresh()

    def render(self) -> Text:
        """Render ASCII art with color"""
        if not self.ascii_art:
            return Text()

        # Only show if configured to show when speaking
        if self.theme.ascii_art.show_when_speaking and not self.is_speaking:
            return Text()

        result = Text()

        # Color ASCII art with primary color
        for line in self.ascii_art.split('\n'):
            result.append(line + '\n', style=f"bold {self.theme.colors.primary}")

        return result
```

### 6. Example Persona Directories

Create structure:

```
personas/
  jarvis/
    theme.yaml
    personality.md
    vocabulary.yaml
    jarvis.txt          # ASCII art

  glados/
    theme.yaml
    personality.md
    glados.txt

  cyberpunk-ai/
    theme.yaml
    personality.md
    cyberpunk.txt
```

## Implementation Plan

### Phase 1: Core Theme System (Current)
1. ✅ Extend PersonaConfig with ThemeConfig
2. ✅ Create example persona directories
3. ✅ Integrate theme loading into PersonaManager
4. ✅ Apply themes to existing widgets

### Phase 2: System Color Integration
1. Implement PlatformTheme detection
2. Add Omarchy color detection
3. Add macOS accent color detection
4. Merge system colors with persona themes

### Phase 3: ASCII Art & Visual Effects
1. Create PersonaAvatar widget
2. Generate ASCII art for default personas
3. Add ASCII art to header/sidebar
4. Implement speaking indicator with art

### Phase 4: Theme Customization UI
1. Add theme editor to settings screen
2. Allow color picker for all theme colors
3. ASCII art preview and upload
4. Save custom themes to ~/.config/xswarm/custom-themes/

## Example Themes

### JARVIS (Professional AI)
```yaml
theme:
  colors:
    primary: "#00D4FF"    # Iconic JARVIS blue
    secondary: "#FFB300"  # Gold UI accents
    accent: "#00FF88"     # Success green
```

### GLaDOS (Aperture Science)
```yaml
theme:
  colors:
    primary: "#FFA500"    # Aperture orange
    secondary: "#0066FF"  # Portal blue
    accent: "#FF3333"     # Danger red
```

### Cyberpunk AI (Hacker Style)
```yaml
theme:
  colors:
    primary: "#00FF00"    # Matrix green
    secondary: "#FF00FF"  # Neon magenta
    accent: "#00FFFF"     # Cyan glow
  style:
    matrix_rain: true     # Enable matrix effect
    glow_effect: true     # Glowing text
```

### Minimalist (Clean & Simple)
```yaml
theme:
  colors:
    primary: "#FFFFFF"
    secondary: "#666666"
    accent: "#0088FF"
  style:
    border_style: "light"
    glow_effect: false
    animation_speed: 0.5
```

## Benefits

1. **User Personalization**: Users can create unique, personalized assistants
2. **Platform Integration**: Automatic adaptation to system themes (Omarchy, macOS)
3. **Brand Identity**: Each persona has distinct visual identity
4. **Accessibility**: Users can customize for visibility/readability
5. **Community**: Shareable persona themes (like VS Code themes)
6. **Framework-Native**: Leverages Textual's built-in theming capabilities

## Technical Considerations

- **Color Validation**: Ensure hex colors are valid
- **ASCII Art Size**: Validate art fits in available space
- **Performance**: Cache rendered ASCII art
- **Accessibility**: Ensure sufficient color contrast
- **Fallbacks**: Graceful degradation if theme files missing
- **Hot Reload**: Support theme reloading without restart
