# Persona Icon Recommendations

This document contains the best animated icon selections for each xSwarm persona. These should be downloaded and saved as `icon.apng` (or `icon.gif` if APNG not available) in each persona's folder.

## Selection Criteria

- **Animation Quality**: Smooth, iconic animation that represents the character
- **Resolution**: Highest quality available (prefer 480p+ source)
- **Recognizability**: Immediately identifiable as the character
- **Loop Quality**: Clean loop without jarring transitions
- **File Size**: Balance between quality and reasonable file size (<2MB preferred)

---

## HAL 9000 🔴

**Recommended Icon**: HAL's Red Eye Close-up
- **URL**: https://media.giphy.com/media/l0HlNyrvLKBMxjFzG/giphy.gif
- **Alternative**: https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExcTVkMnRyZGd3ZWQ5bjBxYjB4ZDN5bm5kbGl5OGR6Mm5yZ2x5ZXdoZiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l0HlNyrvLKBMxjFzG/giphy.gif
- **Reason**: Iconic red eye pulsing animation, instantly recognizable, clean loop
- **Save as**: `packages/personas/hal-9000/icon.gif`

---

## KITT 🚗

**Recommended Icon**: K.I.T.T. Scanner Bar Animation
- **URL**: https://media.tenor.com/QVPOKZDrWb4AAAAC/knight-rider-scanner.gif
- **Alternative**: https://tenor.com/view/knight-rider-scanner-knight-rider-kitt-car-michael-knight-gif-16799181
- **Reason**: The iconic sweeping red scanner light, universally recognized as KITT
- **Save as**: `packages/personas/kitt/icon.gif`

---

## GLaDOS 🔬

**Recommended Icon**: GLaDOS Hanging Eye Animation
- **URL**: https://media.giphy.com/media/8vtm3YCdxtUvjTn0U3/giphy.gif
- **Alternative**: https://giphy.com/gifs/glados-8vtm3YCdxtUvjTn0U3
- **Reason**: GLaDOS's eye/core hanging from ceiling, with subtle movement
- **Save as**: `packages/personas/glados/icon.gif`

---

## Cylon 👁️

**Recommended Icon**: Cylon Centurion Scanner Sweep
- **URL**: https://media.giphy.com/media/xT9DPCKNlqT6RznP9K/giphy.gif
- **Alternative**: https://tenor.com/search/cylons-gifs
- **Reason**: Classic sweeping red scanner (the original Larson Scanner), very clean animation
- **Save as**: `packages/personas/cylon/icon.gif`

---

## C-3PO 🤖

**Recommended Icon**: C-3PO Head Turn with Photoreceptors
- **URL**: https://media.giphy.com/media/3o7TKS6AWINqbg3FV6/giphy.gif
- **Alternative**: https://tenor.com/view/c3po-star-wars-eyes-turn-on-light-up-gif-19942757 (red eyes version)
- **Reason**: Shows C-3PO's iconic golden form with characteristic worried expression
- **Save as**: `packages/personas/c3po/icon.gif`

---

## TARS ◼️

**Recommended Icon**: TARS Rotating Geometric Form
- **URL**: https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif
- **Alternative**: https://giphy.com/gifs/tars-interstellar-3o7aCTPPm4OHfRLSH6
- **Reason**: Shows TARS's unique monolithic, geometric design rotating
- **Save as**: `packages/personas/tars/icon.gif`

---

## Marvin 😔

**Recommended Icon**: Marvin Depressed Walk
- **URL**: https://media.giphy.com/media/l0HlN5Y28D9MzzcRy/giphy.gif
- **Alternative**: https://tenor.com/search/marvin-robot-gifs
- **Reason**: Captures Marvin's iconic slouched posture and depressed demeanor
- **Save as**: `packages/personas/marvin/icon.gif`

---

## Sauron 👁️

**Recommended Icon**: Eye of Sauron Flaming Animation
- **URL**: https://media.giphy.com/media/njYrp176NQsHS/giphy.gif
- **Alternative**: https://tenor.com/view/sauron-eye-tower-lord-of-the-rings-i-see-you-gif-25761843
- **Reason**: The iconic flaming Eye of Sauron, instantly recognizable, dramatic animation
- **Save as**: `packages/personas/sauron/icon.gif`

---

## JARVIS 💙

**Recommended Icon**: JARVIS Interface Blue Waveform
- **URL**: https://64.media.tumblr.com/d6a5e895f8c40e4cb8fa3b44c6ede0fe/tumblr_ocefbddRxg1up7w8xo1_540.gifv
- **Alternative**: Create custom blue waveform animation (no official JARVIS icon exists)
- **Reason**: JARVIS is primarily voice-based, so an animated blue waveform represents the AI interface
- **Note**: May need to create custom animation as JARVIS doesn't have a physical form
- **Save as**: `packages/personas/jarvis/icon.gif`

---

## DALEK 🤖

**Recommended Icon**: Dalek Eye Stalk Animation
- **URL**: https://media.giphy.com/media/3o6ZtjWdtTFfpCMEj6/giphy.gif
- **Alternative**: https://tenor.com/search/dalek-gifs
- **Reason**: Dalek eye stalk is the most recognizable feature, with menacing animation
- **Save as**: `packages/personas/dalek/icon.gif`

---

## Automated Download Script

Create `scripts/download_persona_icons.sh`:

```bash
#!/bin/bash
# Download all persona icons

ICONS=(
  "hal-9000:https://media.giphy.com/media/l0HlNyrvLKBMxjFzG/giphy.gif"
  "kitt:https://media.tenor.com/QVPOKZDrWb4AAAAC/knight-rider-scanner.gif"
  "glados:https://media.giphy.com/media/8vtm3YCdxtUvjTn0U3/giphy.gif"
  "cylon:https://media.giphy.com/media/xT9DPCKNlqT6RznP9K/giphy.gif"
  "c3po:https://media.giphy.com/media/3o7TKS6AWINqbg3FV6/giphy.gif"
  "tars:https://media.giphy.com/media/3o7aCTPPm4OHfRLSH6/giphy.gif"
  "marvin:https://media.giphy.com/media/l0HlN5Y28D9MzzcRy/giphy.gif"
  "sauron:https://media.giphy.com/media/njYrp176NQsHS/giphy.gif"
  "dalek:https://media.giphy.com/media/3o6ZtjWdtTFfpCMEj6/giphy.gif"
)

for entry in "${ICONS[@]}"; do
  persona="${entry%%:*}"
  url="${entry#*:}"
  output="packages/personas/$persona/icon.gif"

  echo "Downloading icon for $persona..."
  curl -sL "$url" -o "$output"

  if [ -f "$output" ]; then
    echo "✅ Saved: $output ($(du -h "$output" | cut -f1))"
  else
    echo "❌ Failed: $persona"
  fi
done

echo ""
echo "📝 Note: JARVIS icon may need custom creation (no official animated icon available)"
echo ""
echo "🎨 All persona icons downloaded!"
echo "   To convert to APNG format: ffmpeg -i icon.gif icon.apng"
```

## Usage

```bash
chmod +x scripts/download_persona_icons.sh
./scripts/download_persona_icons.sh
```

## Converting to APNG (Optional)

If you want APNG format instead of GIF:

```bash
for persona in packages/personas/*/; do
  if [ -f "$persona/icon.gif" ]; then
    ffmpeg -i "$persona/icon.gif" "$persona/icon.apng"
    echo "Converted $(basename $persona)"
  fi
done
```

## File Size Optimization

If icons are too large:

```bash
# Reduce size with gifsicle
gifsicle -O3 --colors 256 icon.gif -o icon_optimized.gif

# Or use ffmpeg to resize
ffmpeg -i icon.gif -vf "scale=128:-1" icon_small.gif
```

---

## Design Guidelines for Custom Icons

If creating custom icons (like for JARVIS):

- **Size**: 128x128px to 256x256px
- **Format**: GIF or APNG with transparency
- **Duration**: 1-3 second loop
- **Framerate**: 24fps for smooth animation
- **Colors**: Use persona's primary color palette
- **Style**: Match character's aesthetic (futuristic, retro, etc.)

---

## Integration

Once downloaded, update each persona's config:

```yaml
# persona.yaml
icon:
  file: "icon.gif"  # or icon.apng
  animated: true
  size: 128  # dimensions in pixels
```
