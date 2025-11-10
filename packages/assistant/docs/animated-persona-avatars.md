# Animated Persona Avatars & AI-Assisted Creator

## Vision
Create living, breathing persona avatars that animate in the TUI background, and provide an AI-assisted wizard to help users create custom personalities, voices, themes, and wake words.

## Research Findings

### Animation Libraries

**1. Textual (Built-in - RECOMMENDED)**
- ✅ Already our TUI framework
- ✅ Native animation support (`animate()` method)
- ✅ Layer system for background/foreground
- ✅ Opacity, offset, scale animations
- ✅ 60 FPS smooth animations
- ✅ No additional dependencies

**2. Asciimatics**
- 🎨 Full-featured ASCII animation library
- 🎮 Sprites, particle systems, effects
- 📦 `pip install asciimatics`
- ⚠️ Separate rendering from Textual (may conflict)
- 💡 Could use for pre-rendering animation frames

**3. ASCII Animator**
- 🎬 Converts GIFs to ASCII animations
- 📦 `pip install ascii-animator`
- 💡 Perfect for converting character art to ASCII
- 🎯 Use case: C-3PO GIF → ASCII animation

**4. Rich (Already using)**
- ✅ Styled text rendering
- ✅ Progress animations
- ✅ Already integrated with Textual

## Architecture Design

### 1. Animated Persona Avatar System

```python
# assistant/dashboard/widgets/animated_avatar.py

from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from pathlib import Path
import time

class AnimatedAvatar(Static):
    """
    Animated ASCII art persona avatar that plays in TUI background.

    Features:
    - Frame-based animation (sprite sheets)
    - Idle animations (breathing, blinking, subtle movements)
    - Speaking animations (mouth moves when assistant talks)
    - Emotion states (happy, thinking, sad, excited)
    - Background layer (doesn't block TUI controls)
    """

    # Reactive properties
    is_speaking = reactive(False)
    emotion = reactive("neutral")  # neutral, happy, thinking, sad, excited

    def __init__(self, persona_name: str, animation_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.persona_name = persona_name
        self.animation_dir = animation_dir
        self.frames = self._load_frames()
        self.current_frame = 0
        self.frame_time = 0.1  # 10 FPS for ASCII art

    def _load_frames(self) -> Dict[str, List[Text]]:
        """
        Load animation frames from persona directory.

        Directory structure:
        personas/c3po/
          animations/
            idle_001.txt       # Idle animation frames
            idle_002.txt
            ...
            speaking_001.txt   # Speaking animation
            speaking_002.txt
            ...
            thinking_001.txt   # Thinking animation
            ...
        """
        frames = {
            "idle": [],
            "speaking": [],
            "thinking": [],
            "happy": [],
            "sad": [],
        }

        for state in frames.keys():
            state_dir = self.animation_dir / state
            if not state_dir.exists():
                continue

            # Load all frames for this state
            frame_files = sorted(state_dir.glob("*.txt"))
            for frame_file in frame_files:
                with open(frame_file, 'r') as f:
                    frame_text = Text(f.read())
                    frames[state].append(frame_text)

        return frames

    def on_mount(self):
        """Start animation loop"""
        self.set_interval(self.frame_time, self.advance_frame)

    def advance_frame(self):
        """Advance to next animation frame"""
        state = self._get_current_state()

        if not self.frames[state]:
            return

        self.current_frame = (self.current_frame + 1) % len(self.frames[state])
        self.refresh()

    def _get_current_state(self) -> str:
        """Determine which animation state to show"""
        if self.is_speaking:
            return "speaking"
        elif self.emotion != "neutral":
            return self.emotion
        else:
            return "idle"

    def render(self) -> Text:
        """Render current frame"""
        state = self._get_current_state()

        if not self.frames[state]:
            return Text()

        return self.frames[state][self.current_frame]

    def watch_is_speaking(self, is_speaking: bool):
        """React to speaking state change"""
        if is_speaking:
            self.current_frame = 0  # Reset to start of speaking animation

    def watch_emotion(self, emotion: str):
        """React to emotion change"""
        self.current_frame = 0  # Reset to start of emotion animation
```

### 2. Textual Layer System

```python
# assistant/dashboard/app.py

from textual.app import App
from textual.containers import Container
from textual.css.query import NoMatches

class VoiceAssistantApp(App):
    """TUI with layered animated background"""

    CSS = """
    #background-layer {
        layers: background;  /* Textual layer system */
        opacity: 0.3;        /* Subtle background presence */
        z-index: 0;          /* Behind all other widgets */
    }

    #main-container {
        layers: main;
        z-index: 10;
    }

    AnimatedAvatar {
        width: 100%;
        height: 100%;
        align: center middle;
        opacity: 0.2;        /* Ghosted avatar */
    }

    /* When speaking, increase opacity */
    AnimatedAvatar.speaking {
        opacity: 0.5;
        /* Textual animate() for smooth transition */
        transition: opacity 300ms;
    }
    """

    def compose(self):
        """Compose UI with background avatar layer"""
        # Background layer (animated avatar)
        with Container(id="background-layer"):
            yield AnimatedAvatar(
                persona_name=self.current_persona,
                animation_dir=self.personas_dir / self.current_persona / "animations"
            )

        # Main UI layer (on top)
        with Container(id="main-container"):
            yield CyberpunkHeader(id="header")
            yield CyberpunkVisualizer(id="visualizer")
            # ... rest of UI

    def on_voice_state_change(self, is_speaking: bool):
        """Update avatar when speaking"""
        try:
            avatar = self.query_one(AnimatedAvatar)
            avatar.is_speaking = is_speaking

            # Add/remove "speaking" CSS class for opacity animation
            if is_speaking:
                avatar.add_class("speaking")
            else:
                avatar.remove_class("speaking")
        except NoMatches:
            pass
```

### 3. GIF to ASCII Animation Converter

```python
# scripts/gif_to_ascii_animation.py

"""
Convert animated GIF to ASCII animation frames.

Usage:
  python scripts/gif_to_ascii_animation.py input.gif personas/c3po/animations/idle/

This creates:
  personas/c3po/animations/idle/
    frame_001.txt
    frame_002.txt
    ...
"""

from PIL import Image
import ascii_magic
from pathlib import Path
import sys

def gif_to_ascii_frames(gif_path: Path, output_dir: Path, width: int = 60):
    """Convert animated GIF to ASCII frames"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open GIF
    gif = Image.open(gif_path)
    frame_count = 0

    try:
        while True:
            # Convert current frame to ASCII
            ascii_art = ascii_magic.from_pillow_image(gif)
            ascii_art.to_terminal()  # Preview

            # Save frame
            frame_file = output_dir / f"frame_{frame_count:03d}.txt"
            with open(frame_file, 'w') as f:
                f.write(str(ascii_art))

            frame_count += 1
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    print(f"Converted {frame_count} frames to {output_dir}")

if __name__ == "__main__":
    gif_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    gif_to_ascii_frames(gif_path, output_dir)
```

### 4. AI-Assisted Persona Creator Wizard

```python
# assistant/dashboard/screens/persona_creator.py

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, Button, Label, RadioSet, RadioButton, TextArea
from textual import on

class PersonaCreatorWizard(ModalScreen):
    """
    AI-assisted wizard for creating custom personas.

    Steps:
    1. Basic Info (name, description)
    2. Personality Traits (AI suggests based on description)
    3. Voice Settings (AI suggests based on personality)
    4. Theme & Colors (AI suggests palette)
    5. Wake Word (AI validates pronunciation)
    6. ASCII Art (AI helps describe/generate)
    7. Preview & Test
    8. Save
    """

    def __init__(self, ai_assistant):
        super().__init__()
        self.ai_assistant = ai_assistant
        self.persona_data = {}
        self.step = 1

    def compose(self) -> ComposeResult:
        with Container(id="wizard-container"):
            yield Label("Create Your Custom Persona", id="wizard-title")
            yield self._render_step()

            with Horizontal(id="wizard-buttons"):
                yield Button("Back", id="back-button", variant="default")
                yield Button("Next", id="next-button", variant="primary")
                yield Button("AI Assist", id="ai-assist-button", variant="success")

    def _render_step(self):
        """Render current wizard step"""
        if self.step == 1:
            return self._step_basic_info()
        elif self.step == 2:
            return self._step_personality_traits()
        elif self.step == 3:
            return self._step_voice_settings()
        elif self.step == 4:
            return self._step_theme_colors()
        elif self.step == 5:
            return self._step_wake_word()
        elif self.step == 6:
            return self._step_ascii_art()
        elif self.step == 7:
            return self._step_preview()

    def _step_basic_info(self):
        """Step 1: Basic persona information"""
        return Vertical(
            Label("Step 1: Basic Information"),
            Label("Name your persona:"),
            Input(placeholder="e.g., C-3PO, GLaDOS, Cortana", id="persona-name"),
            Label("Brief description:"),
            TextArea(
                "Describe your persona's character (AI will use this to suggest settings)",
                id="persona-description"
            ),
            Label("Examples:"),
            Label("• Protocol droid, nervous but helpful, British accent"),
            Label("• Sarcastic AI from Aperture Science, dark humor"),
            Label("• Holographic AI assistant, calm and professional"),
        )

    def _step_personality_traits(self):
        """Step 2: AI-suggested personality traits"""
        # AI generates suggestions based on description
        traits = self.persona_data.get('ai_suggested_traits', {})

        return Vertical(
            Label("Step 2: Personality Traits"),
            Label("AI suggested these traits based on your description:"),

            Label(f"Openness: {traits.get('openness', 0.5):.2f}"),
            Label(f"Conscientiousness: {traits.get('conscientiousness', 0.5):.2f}"),
            # ... other traits with sliders

            Label("Adjust if needed, or press 'AI Assist' to regenerate"),
        )

    def _step_theme_colors(self):
        """Step 4: AI-suggested color palette"""
        colors = self.persona_data.get('ai_suggested_colors', {})

        return Vertical(
            Label("Step 4: Theme & Colors"),
            Label("AI suggested this color palette:"),

            # Color preview boxes
            self._color_preview("Primary", colors.get('primary', '#00D4FF')),
            self._color_preview("Secondary", colors.get('secondary', '#FFB300')),
            self._color_preview("Accent", colors.get('accent', '#00FF88')),

            Button("Regenerate Palette", id="regen-palette"),
            Button("Use Pywal Colors", id="use-pywal"),
        )

    @on(Button.Pressed, "#ai-assist-button")
    async def handle_ai_assist(self):
        """Use AI to help with current step"""
        if self.step == 2:
            await self._ai_suggest_traits()
        elif self.step == 3:
            await self._ai_suggest_voice()
        elif self.step == 4:
            await self._ai_suggest_colors()
        elif self.step == 5:
            await self._ai_validate_wake_word()
        elif self.step == 6:
            await self._ai_help_ascii_art()

    async def _ai_suggest_traits(self):
        """AI suggests personality traits based on description"""
        description = self.query_one("#persona-description", TextArea).text

        prompt = f"""
        Based on this character description, suggest Big Five personality traits (0.0-1.0):

        "{description}"

        Respond with JSON:
        {{
          "openness": 0.8,
          "conscientiousness": 0.7,
          ...
        }}
        """

        response = await self.ai_assistant.query(prompt)
        traits = parse_json(response)

        self.persona_data['ai_suggested_traits'] = traits
        self.refresh()

    async def _ai_suggest_colors(self):
        """AI suggests color palette based on personality"""
        description = self.query_one("#persona-description", TextArea).text

        prompt = f"""
        Suggest a color palette for this character:

        "{description}"

        Consider their personality and provide hex colors that match their vibe.
        Respond with JSON:
        {{
          "primary": "#00D4FF",
          "secondary": "#FFB300",
          "accent": "#00FF88",
          "background": "#0A0E14",
          "reasoning": "Blue conveys trust and professionalism..."
        }}
        """

        response = await self.ai_assistant.query(prompt)
        colors = parse_json(response)

        self.persona_data['ai_suggested_colors'] = colors
        self.refresh()

    async def _ai_help_ascii_art(self):
        """AI helps describe/generate ASCII art"""
        description = self.query_one("#persona-description", TextArea).text

        prompt = f"""
        The user wants ASCII art for this character:

        "{description}"

        Options:
        1. Suggest where to find existing ASCII art/GIFs of this character
        2. Describe what the ASCII art should look like
        3. If it's a simple design, generate it

        Respond with helpful suggestions.
        """

        response = await self.ai_assistant.query(prompt)

        # Show AI response in dialog
        self.app.push_screen(AIAssistDialog(response))
```

### 5. Complete Persona Directory Structure

```
personas/
  c3po/
    theme.yaml              # Configuration
    animations/             # NEW: Animation frames
      idle/
        frame_001.txt       # Standing still, subtle movement
        frame_002.txt
        frame_003.txt
        frame_004.txt
      speaking/
        frame_001.txt       # Mouth open
        frame_002.txt       # Mouth closed
        frame_003.txt
      thinking/
        frame_001.txt       # Head tilt
        frame_002.txt
      happy/
        frame_001.txt       # Arms up
        frame_002.txt
    avatar_static.txt       # Fallback static image
```

## Implementation Plan

### Phase 1: Animated Avatar Foundation (Week 1)
- [ ] Create `AnimatedAvatar` widget
- [ ] Implement frame-based animation system
- [ ] Add Textual layer/z-index for background placement
- [ ] Create simple test animation (2-3 frames)
- [ ] Integrate with speaking state

### Phase 2: GIF to ASCII Converter (Week 1)
- [ ] Install `ascii-animator` or `ascii-magic`
- [ ] Create conversion script
- [ ] Convert C-3PO GIF to ASCII frames
- [ ] Test animation playback in TUI

### Phase 3: AI-Assisted Wizard (Week 2)
- [ ] Create `PersonaCreatorWizard` screen
- [ ] Implement 7-step wizard flow
- [ ] Add AI assistance for each step
- [ ] Generate `theme.yaml` from wizard data
- [ ] Save persona to user directory

### Phase 4: Animation States (Week 2)
- [ ] Implement emotion states (idle, speaking, thinking, happy, sad)
- [ ] Connect to voice assistant state
- [ ] Add smooth transitions between states
- [ ] Create animations for 3 default personas (JARVIS, GLaDOS, NEON)

### Phase 5: Community Features (Week 3)
- [ ] Persona sharing (export persona + animations)
- [ ] Persona marketplace (discover community personas)
- [ ] Animation preview before download
- [ ] One-click persona installation

## Technical Details

### Animation Performance
- **Frame Rate**: 10 FPS for ASCII art (comfortable for terminal)
- **Frame Count**: 4-8 frames for idle, 2-4 for speaking
- **Memory**: ~1KB per frame, ~50KB per persona with animations
- **CPU**: <1% per animated avatar (Textual is efficient)

### ASCII Art Sources
1. **ASCII Art Archive** - https://www.asciiart.eu/
2. **Text-Image.com** - Convert images to ASCII
3. **GIPHY** - Find animated GIFs of characters
4. **ascii-animator** - Convert GIFs to ASCII automatically

### Textual Animation API
```python
# Fade in avatar when persona loads
avatar.styles.opacity = 0
avatar.animate("opacity", value=0.5, duration=1.0)

# Move avatar on screen
avatar.styles.offset = (0, 100)  # Start off-screen
avatar.animate("offset", value=(0, 0), duration=0.5, easing="out_cubic")

# Scale animation (breathing effect)
for _ in range(4):
    avatar.animate("opacity", value=0.4, duration=0.8)
    avatar.animate("opacity", value=0.5, duration=0.8)
```

## Example: C-3PO Persona

```yaml
# personas/c3po/theme.yaml

name: "C-3PO"
description: "Protocol droid fluent in over six million forms of communication"
version: "1.0.0"

traits:
  openness: 0.5          # By-the-book
  conscientiousness: 0.95 # Very detail-oriented
  extraversion: 0.7       # Chatty
  agreeableness: 0.9      # Helpful and polite
  neuroticism: 0.8        # Anxious!

  formality: 0.9          # Very formal
  enthusiasm: 0.6         # Moderate
  humor: 0.3              # Unintentionally funny
  verbosity: 0.8          # Long-winded

voice:
  pitch: 1.1              # Slightly higher
  speed: 1.0              # Normal pace
  tone: "formal"
  quality: 0.9

theme:
  colors:
    primary: "#FFD700"    # Gold
    secondary: "#C0C0C0"  # Silver
    accent: "#FFA500"     # Orange glow
    background: "#0A0A0A"
    text: "#FFE4B5"       # Moccasin

  ascii_art:
    file: "avatar_static.txt"
    position: "background"   # NEW: background layer
    show_when_speaking: true
    animated: true           # NEW: enable animation
    animation_dir: "animations/"

  style:
    border_style: "rounded"
    glow_effect: true
    animation_speed: 1.0
    matrix_rain: false
    pulse_color: true

system_prompt: |
  You are C-3PO, a protocol droid fluent in over six million forms of communication.

  You are:
  - Excessively polite and formal
  - Anxious about everything
  - Concerned with odds and statistics
  - Loyal but pessimistic
  - Often stating the obvious

  Catchphrases:
  - "Oh my!"
  - "We're doomed!"
  - "I suggest a new strategy, R2: let the Wookiee win."
  - "Don't call me a mindless philosopher, you overweight glob of grease!"

wake_word: "threepio"
```

## Benefits

### For Users
- **Visual Personality** - See their assistant's character
- **Immersive Experience** - Living, breathing AI companion
- **Customization** - Create truly unique assistants
- **Share & Discover** - Community persona marketplace

### For Viral Growth
- **Screenshot-Worthy** - Animated ASCII art = r/unixporn gold
- **Character Attachment** - Users bond with their persona
- **Creative Expression** - Persona creation is an art form
- **Social Sharing** - "Check out my custom C-3PO assistant!"

### For Ecosystem
- **Content Creation** - Users make persona packs
- **Artist Collaboration** - ASCII artists contribute
- **Character Licensing** - Official branded personas (future revenue)
- **Animation Packs** - Premium animation sets

## Next Steps

1. ✅ Create `AnimatedAvatar` widget
2. ✅ Test Textual layering with background avatar
3. ✅ Convert one test GIF to ASCII frames
4. ✅ Build basic PersonaCreatorWizard
5. ✅ Integrate AI assistance into wizard
6. ✅ Create complete C-3PO example persona with animations

This will make xswarm the most visually impressive and customizable TUI assistant ever built! 🎬🤖
