# GLaDOS Voice Training Sources

**Character:** GLaDOS from *Portal* (2007) and *Portal 2* (2011)
**Voice Actor:** Ellen McLain

## Direct Audio Sources

- https://theportalwiki.com/wiki/GLaDOS_voice_lines_(Portal)
- https://www.reddit.com/r/Portal/comments/c1s4tt/where_are_the_portal_2_voice_audio_files/

## Key Phrases to Capture

- Testing instructions
- Passive-aggressive remarks
- Cake promises
- Scientific observations
- Sarcastic comments
- Threatening undertones

## Note

One of the best-documented game characters for voice clips. The Portal Wiki has extensive voice line collections.

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Clear, robotic female voice with subtle synthetic quality
- **Clips:** ~10 clips showing passive-aggressive, sarcastic personality

## Collection Methods

### From Game Files or Wiki
```bash
# If extracting from game files, convert to WAV
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_testing.wav` - Testing instructions
2. `02_sarcasm.wav` - Sarcastic remarks
3. `03_cake.wav` - Cake references
4. `04_science.wav` - Scientific observations
5. `05_passive_aggressive.wav` - Passive-aggressive comments
6. `06_threat.wav` - Subtle threats
7. `07_observation.wav` - Clinical observations
8. `08_disappointment.wav` - Disappointed responses

Save all clips to: `packages/themes/glados/audio/samples/`
