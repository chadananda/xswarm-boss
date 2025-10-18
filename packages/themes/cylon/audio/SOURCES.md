# Cylon Voice Training Sources

**Character:** Cylon Centurions from *Battlestar Galactica* (1978)
**Voice Actor:** Various

## Direct Audio Sources

- https://www.101soundboards.com/ → Search "Classic Cylon Quotes"
- YouTube → Search "Cylon voice sound effect compilation"

## Key Phrases to Capture

- "By your command"
- "Affirmative"
- "Negative"
- Command acknowledgments
- Status reports

## Note

Very mechanical, monotone voice - easier to synthesize with voice effects. The emotionless, obedient delivery is key to the character.

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Mechanical, monotone, robotic
- **Clips:** ~10 clips showing absolute obedience and emotionless responses

## Collection Methods

### From Soundboards/YouTube
```bash
# Download clips, convert if needed
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Apply Robotic Effect in Audacity
1. Import audio
2. Effect → Vocoder (for robotic quality)
3. Effect → Change Pitch (slightly lower, mechanical)
4. Effect → Normalize (-3dB)
5. Remove all emotion/inflection
6. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_by_your_command.wav` - "By your command"
2. `02_affirmative.wav` - "Affirmative"
3. `03_negative.wav` - "Negative"
4. `04_acknowledgment.wav` - Command acknowledgments
5. `05_status.wav` - Status reports
6. `06_orders.wav` - Following orders
7. `07_report.wav` - Mission reports
8. `08_obey.wav` - Obedience responses

Save all clips to: `packages/themes/cylon/audio/samples/`
