# Voice Training Audio Sources

This guide explains how to collect and prepare audio samples for training MOSHI voice models. Audio files should be saved locally in each theme's `audio/samples/` directory but are **excluded from git** to avoid copyright issues.

## Finding Character-Specific Sources

Each theme has its own `audio/SOURCES.md` file with direct download links:

- `hal-9000/audio/SOURCES.md` - HAL 9000 voice sources
- `sauron/audio/SOURCES.md` - Sauron voice sources
- `jarvis/audio/SOURCES.md` - JARVIS voice sources
- `dalek/audio/SOURCES.md` - DALEK voice sources
- `c3po/audio/SOURCES.md` - C-3PO voice sources
- `glados/audio/SOURCES.md` - GLaDOS voice sources
- `tars/audio/SOURCES.md` - TARS voice sources
- `marvin/audio/SOURCES.md` - Marvin voice sources
- `kitt/audio/SOURCES.md` - KITT voice sources
- `cylon/audio/SOURCES.md` - Cylon voice sources

Each character's SOURCES.md contains:
- Direct URLs for downloading audio
- Key phrases to capture
- Character-specific collection tips
- Suggested clip organization

---

## General Guidelines

### Audio Quality Requirements

- **Format:** WAV (preferred), FLAC, or high-quality MP3
- **Sample Rate:** 24kHz or 48kHz
- **Duration:** 3-10 minutes total per character
- **Quality:** Clear speech, minimal background noise
- **Variety:** Different emotions, contexts, speaking speeds

### File Naming Convention

```
[theme]/audio/samples/
├── 01_greeting.wav
├── 02_explanation.wav
├── 03_concern.wav
├── 04_success.wav
├── 05_technical.wav
├── 06_command.wav
├── 07_question.wav
├── 08_sarcasm.wav (if applicable)
└── ...
```

### Legal Considerations

⚠️ **Important:** Audio samples from movies/TV/games are copyrighted. Options:

1. **Fair Use:** Educational/development purposes (keep local only)
2. **Public Domain:** Use clips from public domain sources
3. **Licensed:** Purchase/license official audio
4. **Synthesized:** Use existing TTS to bootstrap, then refine
5. **Original Performance:** Record your own voice acting

**This is why audio files are .gitignored** - users collect locally, never commit to git.

---

## Collection Methods

### Method 1: YouTube Download

```bash
# Download audio from YouTube
yt-dlp -x --audio-format wav "https://youtube.com/watch?v=VIDEO_ID"

# Rename to convention
mv "Video Title.wav" 01_greeting.wav
```

**Install yt-dlp:**
```bash
# macOS
brew install yt-dlp

# Arch Linux
sudo pacman -S yt-dlp

# Or via pip
pip install yt-dlp
```

### Method 2: Audio Extraction from Video

```bash
# Extract audio from video file
ffmpeg -i input_video.mp4 -vn -acodec pcm_s16le -ar 24000 output.wav

# Convert any audio format to WAV
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav
```

### Method 3: Screen Recording Audio

1. Play video/game with character dialogue
2. Use QuickTime (macOS) or OBS (Linux/macOS) to record system audio
3. Extract and clean audio in Audacity
4. Export as WAV 24kHz

---

## Audio Preparation

### Clean Up in Audacity (Free)

1. **Import audio:** File → Import → Audio
2. **Remove silence:** Select silence → Effect → Truncate Silence
3. **Normalize volume:** Effect → Normalize (-3dB)
4. **Remove noise:** Select silence → Effect → Noise Reduction
5. **Export:** File → Export → WAV (24kHz, 16-bit)

**Install Audacity:**
```bash
# macOS
brew install --cask audacity

# Arch Linux
sudo pacman -S audacity
```

### Optimal Training Set

For each character, collect ~10 clips demonstrating:

- ✅ Neutral/greeting tone
- ✅ Explaining/teaching tone
- ✅ Expressing concern/warning
- ✅ Confirming/acknowledging
- ✅ Questioning
- ✅ Technical/analytical speech
- ✅ Success/satisfaction
- ✅ Unique emotional range (humor, sarcasm, depression, etc.)

**Total duration:** 3-10 minutes per character

---

## Automated Collection (Recommended)

We provide a training script that automatically downloads and converts audio from each theme's SOURCES.md file:

### Setup

```bash
# Install Python dependencies
pip install -r scripts/requirements.txt

# Install system dependencies
# macOS:
brew install ffmpeg yt-dlp

# Arch Linux:
sudo pacman -S ffmpeg yt-dlp
```

### Usage

```bash
# Train a specific theme (downloads all URLs from its SOURCES.md)
python scripts/train_voice.py --theme hal-9000

# Limit to first 5 clips (for testing)
python scripts/train_voice.py --theme jarvis --limit 5

# Train all themes at once
python scripts/train_voice.py --all

# Re-download existing files
python scripts/train_voice.py --theme glados --force
```

The script will:
1. Parse URLs from the theme's `audio/SOURCES.md`
2. Download from YouTube (yt-dlp) or direct audio links
3. Convert everything to WAV 24kHz mono
4. Save as `01_source.wav`, `02_source.wav`, etc. in `audio/samples/`
5. Skip soundboard URLs (requires manual download)

### Post-Processing

After automated download:
1. **Listen to clips** - Ensure quality and correct character
2. **Rename descriptively** - `01_greeting.wav`, `02_technical.wav`, etc.
3. **Edit in Audacity** - Remove silence, normalize volume, trim to best parts
4. **Keep 8-10 best clips** - Total 3-10 minutes

---

## Training MOSHI with Audio

Once you've collected and cleaned samples in a theme's `audio/samples/` directory:

```bash
# Generate voice embedding (future feature)
xswarm voice train --theme hal-9000 \
  --samples packages/themes/hal-9000/audio/samples/

# Verify voice model
xswarm voice test --theme hal-9000 \
  --text "Good morning, Dave. All systems are functioning normally."
```

The trained voice embeddings will be saved in each theme's configuration and used by MOSHI for real-time voice cloning during conversations.

---

## Quick Start Example

Let's collect HAL 9000 audio:

```bash
# 1. Navigate to HAL theme
cd packages/themes/hal-9000/audio

# 2. Read the character-specific sources
cat SOURCES.md

# 3. Download a clip from YouTube
yt-dlp -x --audio-format wav "https://www.youtube.com/watch?v=9wrjl-H4Hs8"

# 4. Convert to proper format
ffmpeg -i "*.wav" -acodec pcm_s16le -ar 24000 samples/01_greeting.wav

# 5. Repeat for 8-10 clips showing different emotions

# 6. Train the voice model
xswarm voice train --theme hal-9000 --samples samples/
```

---

## Tips

### Finding High-Quality Sources

- **YouTube:** Search "[character name] voice lines compilation"
- **Soundboards:** myinstants.com, 101soundboards.com
- **Wiki Pages:** Many characters have dedicated wikis with audio
- **Game Files:** Extract directly from game installations (if you own the game)
- **Streaming:** Use screen recording to capture Netflix/Disney+/etc.

### Common Issues

**Problem:** Audio has background music
**Solution:** Use Audacity's vocal isolation or find dialogue-only clips

**Problem:** Multiple characters talking
**Solution:** Trim to only target character, or find solo dialogue

**Problem:** Low quality audio
**Solution:** Prioritize newer HD sources, avoid YouTube re-uploads

**Problem:** Wrong format
**Solution:** Always convert to WAV 24kHz: `ffmpeg -i input -ar 24000 output.wav`

---

## Contributing New Themes

When creating a new theme, include an `audio/SOURCES.md` file with:

1. Character name and source material
2. Voice actor name
3. Direct URLs for audio sources
4. Key phrases specific to that character
5. Any special voice effect notes
6. Suggested clip organization

See existing themes for examples.
