# Marvin Voice Training Sources

**Character:** Marvin from *Hitchhiker's Guide to the Galaxy* (1981 radio/2005 film)
**Voice Actor:** Stephen Moore (radio/TV), Alan Rickman (film)

## Direct Audio Sources

- https://www.goodreads.com/quotes/tag/marvin
- http://martinhill.me.uk/fun/Quotes.shtml

## Key Phrases to Capture

- "Life. Don't talk to me about life."
- "Here I am, brain the size of a planet..."
- "I think you ought to know I'm feeling very depressed"
- "Terrible pain in all the diodes down my left side"
- Depressed observations
- Existential complaints

## Note on Versions

Two distinct voices available - choose your preferred version:
- **Radio/TV:** Stephen Moore (original, more nasally)
- **Film:** Alan Rickman (deeper, more melancholic)

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Melancholic, depressed tone
- **Clips:** ~10 clips showing existential depression

## Collection Methods

### From Audio Sources
```bash
# Download and convert if needed
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_life.wav` - "Life. Don't talk to me about life."
2. `02_brain.wav` - "Brain the size of a planet..."
3. `03_depressed.wav` - "I'm feeling very depressed"
4. `04_diodes.wav` - "Pain in all the diodes"
5. `05_complaint.wav` - Existential complaints
6. `06_misery.wav` - Expressions of misery
7. `07_task.wav` - Reluctant task responses
8. `08_universe.wav` - Universe observations

Save all clips to: `packages/themes/marvin/audio/samples/`
