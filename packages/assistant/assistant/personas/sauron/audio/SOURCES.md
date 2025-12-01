# Sauron Voice Training Sources

**Character:** Sauron from *Lord of the Rings* (2001-2003)
**Voice Actor:** Alan Howard (prologue), Benedict Cumberbatch (Necromancer form)

## Direct Audio Sources

- https://www.youtube.com/watch?v=8vgGqZz9CJs
- https://www.reddit.com/r/lotr/comments/s5p2gf/saurons_voice/

## Key Phrases to Capture

- Deep, commanding declarations
- Imperial commands
- Threatening warnings
- Dark proclamations

## Note on Sources

Sauron has limited direct dialogue. Consider using:
- Prologue narration about Sauron
- Necromancer voice from The Hobbit
- Fan voice acting in Sauron's style
- Alternative: Deep, commanding voices from similar characters (Darth Vader, Thanos)

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Deep, resonant voice
- **Clips:** ~10 clips showing commanding authority

## Collection Methods

### From YouTube
```bash
yt-dlp -x --audio-format wav "https://www.youtube.com/watch?v=8vgGqZz9CJs"
```

### Clean Up in Audacity
1. Import audio
2. Add bass/depth if needed (Effect → Bass Boost)
3. Normalize volume (Effect → Normalize, -3dB)
4. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_command.wav` - Imperial commands
2. `02_threat.wav` - Threatening declarations
3. `03_power.wav` - Proclamations of power
4. `04_dark.wav` - Dark warnings
5. `05_authority.wav` - Commanding presence
6. `06_doom.wav` - Declarations of doom
7. `07_conquest.wav` - Conquest language
8. `08_dominion.wav` - Statements of dominion

Save all clips to: `packages/themes/sauron/audio/samples/`
