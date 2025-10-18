# DALEK Voice Training Sources

**Character:** Daleks from *Doctor Who* (1963-present)
**Voice Actor:** Various (Nicholas Briggs in modern era)

## Direct Audio Sources

- https://www.youtube.com/watch?v=8vgGqZz9CJs
- https://www.youtube.com/watch?v=9bDGH3dKo90

## Key Phrases to Capture

- "EXTERMINATE!"
- "OBEY! OBEY!"
- "YOU WILL BE EXTERMINATED"
- "DALEKS CONQUER AND DESTROY"
- Tactical commands
- Status reports

## DIY Voice Effect

Dalek voice effect is achievable with ring modulation + EQ. The mechanical, staccato delivery is key to the character.

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Harsh, mechanical, robotic
- **Clips:** ~10 clips showing aggressive, commanding tone

## Collection Methods

### From YouTube
```bash
yt-dlp -x --audio-format wav "https://www.youtube.com/watch?v=9bDGH3dKo90"
```

### Apply Dalek Effect in Audacity
1. Import audio
2. Effect → Distortion (add harshness)
3. Effect → Change Pitch (slightly robotic)
4. Effect → Ring Modulator (classic Dalek sound)
5. Effect → Normalize (-3dB)
6. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_exterminate.wav` - "EXTERMINATE!"
2. `02_obey.wav` - "OBEY! OBEY!"
3. `03_threat.wav` - Extermination threats
4. `04_command.wav` - Tactical commands
5. `05_conquest.wav` - Conquest declarations
6. `06_status.wav` - Status reports
7. `07_destroy.wav` - Destruction orders
8. `08_alert.wav` - Alert warnings

Save all clips to: `packages/themes/dalek/audio/samples/`
