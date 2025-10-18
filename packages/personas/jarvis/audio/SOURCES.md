# JARVIS Voice Training Sources

**Character:** JARVIS from *Iron Man* / *Avengers* (2008-2015)
**Voice Actor:** Paul Bettany

## Direct Audio Sources

- https://fish.audio/m/612b878b113047d9a770c069c8b4fdfe/
- https://www.fineshare.com/ai-voice/jarvis.html

## Key Phrases to Capture

- "Good morning, sir"
- "As you wish, sir"
- "Shall I prepare the Mark..."
- Technical status reports
- Polite observations
- Emergency alerts

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Clear, professional British accent
- **Clips:** ~10 clips showing polite, technical communication

## Collection Methods

### From Audio Sources
```bash
# Download from sources above, then convert if needed
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Remove background noise (Effect → Noise Reduction)
5. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_greeting.wav` - "Good morning, sir"
2. `02_acknowledgment.wav` - "As you wish, sir"
3. `03_technical.wav` - Technical status reports
4. `04_preparation.wav` - System preparation notices
5. `05_observation.wav` - Polite observations
6. `06_alert.wav` - Emergency alerts
7. `07_analysis.wav` - Analytical reports
8. `08_recommendation.wav` - Professional recommendations

Save all clips to: `packages/themes/jarvis/audio/samples/`
