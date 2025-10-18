# Contributing to xSwarm

Thank you for your interest in contributing to xSwarm! This guide will help you add new themes, fix bugs, or improve documentation.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Creating a New Theme](#creating-a-new-theme)
- [Training Voice Models](#training-voice-models)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Development Setup](#development-setup)

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the project's coding standards

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

---

## Ways to Contribute

### 1. Add a New Theme

Create a personality theme for an AI/robot character. See [Creating a New Theme](#creating-a-new-theme) below.

### 2. Improve Existing Themes

- Add more vocabulary entries
- Refine personality descriptions
- Improve voice training audio sources
- Create better visual assets

### 3. Bug Fixes & Features

- Fix bugs in Rust code
- Add new CLI commands
- Improve voice processing
- Enhance MeiliSearch integration

### 4. Documentation

- Improve README and guides
- Add examples and tutorials
- Create video demonstrations
- Translate documentation

---

## Creating a New Theme

Want to add your favorite AI/robot character? Here's how:

### Step 1: Choose Your Character

Pick an AI/robot character with:
- **Distinct personality** - Clear speech patterns and behaviors
- **Available audio** - Voice clips exist online for training
- **Memorable traits** - Unique phrases, tone, or quirks

**Examples:** WALL-E, EDI (Mass Effect), Cortana (Halo), Baymax (Big Hero 6), Robby the Robot, T-800, Data (Star Trek)

### Step 2: Create Theme Structure

```bash
# Create theme directory (use lowercase with hyphens)
mkdir -p packages/themes/wall-e/{audio/samples,assets}

# Create required files
touch packages/themes/wall-e/theme.yaml
touch packages/themes/wall-e/personality.md
touch packages/themes/wall-e/vocabulary.yaml
touch packages/themes/wall-e/README.md
touch packages/themes/wall-e/audio/SOURCES.md
```

### Step 3: Fill Out Configuration Files

See existing themes in `packages/themes/` for examples. Each theme needs:

- **theme.yaml** - Basic configuration (colors, voice settings, key phrases)
- **personality.md** - Detailed personality guide with DO/DON'T examples
- **vocabulary.yaml** - Speech patterns, greetings, technical terms
- **README.md** - Theme overview and character description
- **audio/SOURCES.md** - Direct URLs for voice training audio

Refer to `hal-9000`, `jarvis`, or `glados` themes as templates.

### Step 4: Gather Audio Sources

Create `audio/SOURCES.md` with direct URLs for voice clips:

```markdown
# CHARACTER Voice Training Sources

**Character:** Character Name from *Source Material* (Year)
**Voice Actor:** Actor Name

## Direct Audio Sources

- https://www.youtube.com/watch?v=EXAMPLE1
- https://www.youtube.com/watch?v=EXAMPLE2
- https://soundboards.com/character-sounds

## Key Phrases to Capture

- "Iconic quote 1"
- "Iconic quote 2"
- Technical explanations
- Emotional responses

## Target Format

- **Format:** WAV, 24kHz, 16-bit
- **Duration:** 3-10 minutes total
- **Quality:** Clear speech, minimal background noise
- **Clips:** ~10 clips showing different emotions/contexts
```

### Step 5: Create Visual Assets (Optional)

Add a character icon to `assets/icon.svg` (or icon.png):
- Square format (512x512 recommended)
- Transparent background
- Iconic representation of the character

### Step 6: Test Your Theme

```bash
# Build the project
cargo build

# Test theme loading
xswarm config set overlord.theme your-theme-name

# Verify theme configuration
xswarm config show
```

---

## Training Voice Models

Once your theme structure is complete, train the voice model using collected audio.

### Automated Training (Recommended)

```bash
# Install dependencies
pip install -r scripts/requirements.txt
brew install ffmpeg yt-dlp  # macOS
# or: sudo pacman -S ffmpeg yt-dlp  # Arch Linux

# Download and convert audio automatically
python scripts/train_voice.py --theme your-theme-name

# Limit to first 5 clips for testing
python scripts/train_voice.py --theme your-theme-name --limit 5
```

The script will:
1. Read URLs from `packages/themes/your-theme-name/audio/SOURCES.md`
2. Download from YouTube or direct links
3. Convert to WAV 24kHz mono
4. Save to `audio/samples/` directory

### Post-Processing

After automated download:

1. **Listen to each clip** - Ensure correct character and quality
2. **Rename descriptively**:
   - `01_source.wav` → `01_greeting.wav`
   - `02_source.wav` → `02_technical.wav`
   - etc.
3. **Edit in Audacity** (optional):
   - Remove long silences (Effect → Truncate Silence)
   - Normalize volume (Effect → Normalize, -3dB)
   - Remove background noise (Effect → Noise Reduction)
4. **Keep 8-10 best clips** - Total 3-10 minutes

### Manual Training (Alternative)

If you prefer manual control:

```bash
# Download from YouTube
yt-dlp -x --audio-format wav "VIDEO_URL"

# Convert to proper format
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 24000 output.wav

# Edit in Audacity, then export as WAV 24kHz
```

### Train MOSHI Model (Future Feature)

```bash
# Generate voice embedding
xswarm voice train --theme your-theme-name --samples packages/themes/your-theme-name/audio/samples/

# Test voice model
xswarm voice test --theme your-theme-name --text "Hello! Testing voice model."
```

---

## Submitting a Pull Request

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/xswarm-boss.git
cd xswarm-boss
```

### 2. Create a Branch

```bash
# Create feature branch
git checkout -b add-your-theme-name
```

### 3. Add Your Changes

```bash
# Add your new theme files
git add packages/themes/your-theme-name/

# Commit with descriptive message
git commit -m "Add YOUR_THEME theme from Source Material

- Complete theme configuration (theme.yaml, personality.md, vocabulary.yaml)
- Audio source URLs for voice training
- Character README and visual assets
- Brief personality description"
```

### 4. Push and Create PR

```bash
# Push to your fork
git push origin add-your-theme-name

# Go to GitHub and create a Pull Request
# Title: "Add YOUR_THEME theme"
# Description: Explain the theme, character source, and any special considerations
```

### PR Checklist

Before submitting, ensure:

- [ ] All required files exist (`theme.yaml`, `personality.md`, `vocabulary.yaml`, `README.md`, `audio/SOURCES.md`)
- [ ] Audio SOURCES.md has working URLs (tested at least 3)
- [ ] Theme colors are defined and visually distinct
- [ ] Personality description is detailed with DO/DON'T examples
- [ ] Vocabulary includes greetings, acknowledgments, questions, technical terms
- [ ] README explains character source and personality clearly
- [ ] `.gitkeep` file exists in `audio/samples/` directory
- [ ] NO audio files committed (only SOURCES.md with URLs)
- [ ] Theme name uses lowercase with hyphens (e.g., `wall-e`, not `WALLE` or `Wall-E`)
- [ ] Tested theme loads without errors

---

## Development Setup

### Prerequisites

- **Rust:** 1.75+ (install via [rustup](https://rustup.rs/))
- **Python:** 3.8+ (for training scripts)
- **ffmpeg:** Audio conversion
- **yt-dlp:** YouTube downloads

### Building from Source

```bash
# Clone repository
git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss

# Build project
cargo build

# Run tests
cargo test

# Install locally
cargo install --path packages/core
```

### Running Development Version

```bash
# Run without installing
cargo run -- config show

# Run with specific theme
cargo run -- config set overlord.theme hal-9000
```

### Project Structure

```
xswarm-boss/
├── packages/
│   ├── core/               # Main Rust application
│   ├── indexer/            # Semantic search (MeiliSearch)
│   ├── mcp-server/         # MCP protocol server
│   └── themes/             # Personality themes
│       ├── hal-9000/
│       ├── jarvis/
│       └── ...
├── scripts/
│   ├── train_voice.py      # Audio training automation
│   └── requirements.txt
└── planning/               # Architecture docs
```

See [planning/CODESTYLE.md](planning/CODESTYLE.md) for code style guidelines.

---

## Getting Help

- **Discussions:** [GitHub Discussions](https://github.com/chadananda/xswarm-boss/discussions)
- **Issues:** [GitHub Issues](https://github.com/chadananda/xswarm-boss/issues)
- **Discord:** Coming soon

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to xSwarm! Your themes help make AI assistants more engaging and fun to use. 🤖✨
