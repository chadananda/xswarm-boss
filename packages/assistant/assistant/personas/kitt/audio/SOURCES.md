# KITT Voice Training Sources

**Character:** KITT from *Knight Rider* (1982-1986)
**Voice Actor:** William Daniels

## Direct Audio Sources

- https://www.101soundboards.com/ → Search "KITT Knight Rider voice soundboard"
- https://www.myinstants.com/ → Search "KITT voice quotes"

## Key Phrases to Capture

- "Good morning, Michael"
- "As you wish, Michael"
- "Really, Michael..."
- "My scanners indicate..."
- Technical reports
- Mission updates
- Mild protests

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Professional, slightly synthesized voice
- **Clips:** ~10 clips showing professional, protective personality

## Collection Methods

### From Soundboards
```bash
# Download clips from soundboards, convert if needed
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Slight EQ for car speaker quality if desired
5. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_greeting.wav` - "Good morning, Michael"
2. `02_acknowledgment.wav` - "As you wish, Michael"
3. `03_protest.wav` - "Really, Michael..."
4. `04_scanners.wav` - "My scanners indicate..."
5. `05_technical.wav` - Technical reports
6. `06_mission.wav` - Mission updates
7. `07_concern.wav` - Protective concerns
8. `08_analysis.wav` - Analytical observations

Save all clips to: `packages/themes/kitt/audio/samples/`
