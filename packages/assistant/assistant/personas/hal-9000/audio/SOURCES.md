# HAL 9000 Voice Training Sources

**Character:** HAL 9000 from *2001: A Space Odyssey* (1968)
**Voice Actor:** Douglas Rain

## Direct Audio Sources

- https://www.wavsource.com/movies/2001.htm
- https://hal9000computer.wordpress.com/2017/11/22/all-hal-9000-phrases-from-the-movie/
- https://movie-sounds.org/hal-9000
- https://www.youtube.com/watch?v=9wrjl-H4Hs8
- https://www.youtube.com/shorts/5lsExRvJTAI

## Key Phrases to Capture

- "Good morning, Dave"
- "I'm sorry, Dave. I'm afraid I can't do that"
- "This mission is too important for me to allow you to jeopardize it"
- "I am putting myself to the fullest possible use"
- Calm technical explanations
- Emergency responses

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Clear speech, minimal background noise
- **Clips:** ~10 clips showing different emotions/contexts

## Collection Methods

### From YouTube
```bash
yt-dlp -x --audio-format wav "https://www.youtube.com/watch?v=9wrjl-H4Hs8"
mv *.wav 01_greeting.wav
```

### From MP3/Other Formats
```bash
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Clean Up in Audacity
1. Import audio
2. Remove silence (Effect → Truncate Silence)
3. Normalize volume (Effect → Normalize, -3dB)
4. Remove noise (Effect → Noise Reduction)
5. Export as WAV (24kHz, 16-bit)

## Suggested Clips

1. `01_greeting.wav` - "Good morning, Dave"
2. `02_technical.wav` - Systems status reports
3. `03_concern.wav` - "I'm sorry, Dave..."
4. `04_explanation.wav` - Technical explanations
5. `05_mission.wav` - Mission priorities
6. `06_emergency.wav` - Emergency responses
7. `07_calm.wav` - Calm reassurances
8. `08_analysis.wav` - Analytical observations

Save all clips to: `packages/themes/hal-9000/audio/samples/`
