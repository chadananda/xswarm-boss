# TARS Voice Training Sources

**Character:** TARS from *Interstellar* (2014)
**Voice Actor:** Bill Irwin

## Direct Audio Sources

- https://www.youtube.com/watch?v=Pwcip_zMI6g
- https://www.instagram.com/reel/DIgzVsQO6tu/?hl=en

## Key Phrases to Capture

- Honest assessments (various honesty settings)
- Humorous quips
- Technical explanations
- Mission updates
- Witty observations

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Clear, dry wit with slight robotic quality
- **Clips:** ~10 clips showing humor settings and technical competence

## Collection Methods

### From YouTube
```bash
yt-dlp -x --audio-format wav "https://www.youtube.com/watch?v=Pwcip_zMI6g"
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Remove background noise if present
5. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_humor.wav` - Humor setting jokes
2. `02_honesty.wav` - Brutally honest assessments
3. `03_technical.wav` - Technical explanations
4. `04_mission.wav` - Mission updates
5. `05_wit.wav` - Witty observations
6. `06_sarcasm.wav` - Dry sarcasm
7. `07_analysis.wav` - Analytical responses
8. `08_settings.wav` - Discussing humor/honesty settings

Save all clips to: `packages/themes/tars/audio/samples/`
