# C-3PO Voice Training Sources

**Character:** C-3PO from *Star Wars* (1977-present)
**Voice Actor:** Anthony Daniels

## Direct Audio Sources

- https://movie-sounds.org/sci-fi-movie-samples/quotes-with-sound-clips-from-star-wars-episode-iv-a-new-hope/c-3po-c-3po-yes-sir
- https://www.youtube.com/watch?v=dRltkTJCHLU

## Key Phrases to Capture

- "Oh my!"
- "We're doomed!"
- "The odds of..."
- Anxious warnings
- Protocol explanations
- Worried observations

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Clear, slightly metallic British accent
- **Clips:** ~10 clips showing anxious, worried personality

## Collection Methods

### From YouTube/Audio Sites
```bash
yt-dlp -x --audio-format wav "https://www.youtube.com/watch?v=dRltkTJCHLU"
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Slight EQ for metallic tone if needed
5. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_worry.wav` - "Oh my!"
2. `02_doom.wav` - "We're doomed!"
3. `03_odds.wav` - Calculating odds
4. `04_warning.wav` - Anxious warnings
5. `05_protocol.wav` - Protocol explanations
6. `06_concern.wav` - Worried observations
7. `07_fluster.wav` - Flustered responses
8. `08_etiquette.wav` - Etiquette concerns

Save all clips to: `packages/themes/c3po/audio/samples/`
