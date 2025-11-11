# 🎭 Persona-Based Theme Rotation

The TUI now automatically rotates through different AI personas every 30 seconds, each bringing their unique theme color!

## 🎨 How It Works

### 1. Each Persona Has a Theme Color

In each persona's `theme.yaml`:
```yaml
theme:
  # TUI Base Color - generates 5-shade palette automatically
  theme_color: "#00D4FF"  # JARVIS cyan
```

### 2. Automatic 30-Second Rotation

- App discovers all personas on startup
- Every 30 seconds, randomly picks a new persona
- Extracts the `theme_color` from persona config
- Regenerates the 5-shade palette
- Refreshes the entire UI with new colors

### 3. UI Updates

When switching personas:
- ✅ **Title**: Updates to `xSwarm Voice Assistant - [Persona Name]`
- ✅ **Theme Colors**: All 5 shades regenerated from persona's color
- ✅ **Visualizer Border**: Shows `Voice - [Persona Name]`
- ✅ **Activity Feed**: Logs `🎨 Switched to persona: [Name]`
- ✅ **All UI Components**: Borders, text, waveforms all adapt

## 🎭 Available Personas

### JARVIS (Professional Assistant)
- **Theme Color**: `#00D4FF` - Signature cyan/blue
- **Vibe**: Cool, professional, Iron Man aesthetic
- **Colors**: Blue-gray tones throughout interface

### GLaDOS (Aperture Science)
- **Theme Color**: `#FFA500` - Aperture orange
- **Vibe**: Warm, institutional, portal vibes
- **Colors**: Orange-amber tones throughout interface

### NEON (Cyberpunk Hacker)
- **Theme Color**: `#FF00FF` - Neon magenta
- **Vibe**: Edgy, high-energy, matrix aesthetic
- **Colors**: Purple-magenta tones throughout interface

## 🎥 Demo

Watch the interface transform every 30 seconds:

```
0:00 - JARVIS (cyan/blue)
       Cool professional tones

0:30 - GLaDOS (orange)
       Warm aperture science colors

1:00 - NEON (magenta)
       Cyberpunk purple aesthetic

1:30 - [Random rotation continues...]
```

## 🛠️ Adding New Personas

Want to add your own persona with custom colors?

### 1. Create Persona Directory
```bash
mkdir personas/my-persona
```

### 2. Create `theme.yaml`
```yaml
name: "My Persona"
description: "My custom AI persona"

theme:
  theme_color: "#YOUR_COLOR_HERE"  # Use any hex color!

# ... rest of persona config
```

### 3. Run the App
Your new persona will automatically be discovered and included in the rotation!

## 🎨 Theme Color Examples

Try these colors for different vibes:

- **Cyan Tech**: `#00ffff` - Matrix-style cyan
- **Warm Red**: `#ff6b6b` - Energetic warm red
- **Mint Green**: `#88aa88` - Calm nature tones
- **Deep Purple**: `#9b8cbb` - Elegant purple
- **Golden Amber**: `#aa9977` - Warm earth tones
- **Steel Blue**: `#778899` - Industrial cool

## 💡 Key Features

1. **Zero Configuration**: Just add personas, rotation happens automatically
2. **Dynamic Theming**: 5-shade palette regenerated for each persona
3. **Seamless Transitions**: CSS refresh happens instantly
4. **Activity Logging**: See every persona switch in the feed
5. **Name Display**: Always know which persona is active

## 🎭 Persona Rotation Flow

```
App Starts
    ↓
Load All Personas (JARVIS, GLaDOS, NEON)
    ↓
Set 30-second Timer
    ↓
[First Rotation - Immediate]
Pick Random Persona → Update Theme → Refresh UI
    ↓
[30 seconds pass...]
    ↓
[Rotation Event]
Pick Different Random Persona → Update Theme → Refresh UI
    ↓
[30 seconds pass...]
    ↓
[Repeat Forever...]
```

## 🎨 Visual Impact

Each persona completely transforms the interface:

**All UI Elements Themed:**
- Borders (visualizer, activity, status)
- Text (all 5 emphasis levels)
- Progress bars
- System stats
- Voice waveforms (all 5 styles)
- Activity feed messages
- State indicators

**Result:** A living, breathing interface that changes personality every 30 seconds!

## 🚀 Try It Out

Just run the app and watch it transform:

```bash
python -m assistant.dashboard.app
```

Every 30 seconds, the interface will:
1. Pick a random persona (JARVIS, GLaDOS, or NEON)
2. Extract their theme color
3. Generate new shade palette
4. Refresh the entire UI
5. Show the persona name in title and activity feed

**It's like having multiple AIs taking turns controlling the interface!** 🎭✨

---

**Want to customize?** Check out `THEMING.md` for full theming documentation!
