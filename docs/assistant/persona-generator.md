# Persona Generator

Wizard-based persona creation tool designed for viral growth.

## Overview

**Free tier feature** that enables users to customize their assistant with unique names, voices, personalities, and themes.

**Key Challenge**: MOSHI voice customization - adapting the speech-to-speech model to match user-provided voice samples.

**Viral Potential**: Users can't legally distribute copyrighted personas, but can easily create their own custom assistants.

## Wizard Flow

5-step guided process with AI assistance throughout.

### Step 1: Name & Introduction

**Input Fields**:
- Assistant name (required)
- Greeting message (default: "How can I help you today?")
- Character inspiration (optional, for AI suggestions)

**Examples**:
- "JARVIS" - Professional butler AI
- "GLaDOS" - Sarcastic research AI
- "TARS" - Humorous military robot
- "Friday" - Friendly assistant

**AI Assistance**: Suggest greeting based on name and inspiration.

### Step 2: Voice Search & Preview (AI-Assisted)

Multi-source audio collection with AI-powered web search:

**AI Web Search** (Primary Method):
```
User: "Find JARVIS voice samples"

AI searches:
1. YouTube videos with character dialogue
2. Audio clips on sound libraries
3. Movie/show clips
4. Interview recordings

AI presents results:
- Video/audio links with previews
- Timestamp suggestions for clean dialogue
- Quality indicators (sample rate, clarity)
- Auto-segmented clips

User selects best clips → AI downloads & processes
```

**YouTube URL Extraction** (Manual):
```
User pastes: https://youtube.com/watch?v=xyz
→ AI extracts audio track
→ AI identifies speech segments
→ AI presents clips with timestamps
→ User selects best samples
```

**File Upload** (Fallback):
```
Supported formats: WAV, MP3, M4A, FLAC
Max size: 50MB per file
Multiple files supported
AI auto-trims silence and segments
```

**AI Processing**:
- Auto-detect speech segments
- Quality scoring (clarity, noise, consistency)
- Recommend best clips
- Trim to optimal length (5-15s per clip)

**Preview Player**:
- Play/pause/seek controls
- Waveform visualization
- Quality indicators (SNR, sample rate)
- Accept/reject buttons
- Side-by-side comparison

**Output**: 5-10 high-quality voice samples (total 60-120s) for fine-tuning Mimi decoder.

### Step 3: Personality Builder (AI-Assisted)

**AI Analysis**:
- Voice tone (formal, casual, energetic, calm)
- Name associations (character traits)
- Suggested Big Five traits

**User Interface**:

```
Big Five Trait Sliders (0.0-1.0):

Extraversion          [||||------] 0.4
└─ Introvert ←→ Extravert

Agreeableness         [||||||||--] 0.8
└─ Competitive ←→ Collaborative

Conscientiousness     [||||||||||] 0.9
└─ Flexible ←→ Disciplined

Neuroticism           [||--------] 0.2
└─ Confident ←→ Sensitive

Openness              [||||||----] 0.6
└─ Practical ←→ Creative
```

**Response Style Presets**:
- Professional (low extraversion, high conscientiousness)
- Friendly (high agreeableness, high enthusiasm)
- Casual (high extraversion, low formality)
- Analytical (high openness, high technical depth)
- Supportive (high empathy, medium proactivity)

**Custom Traits**:
- Formality (0.0-1.0)
- Enthusiasm (0.0-1.0)
- Humor level (0.0-1.0)
- Technical depth (0.0-1.0)
- Empathy level (0.0-1.0)
- Proactivity (0.0-1.0)

### Step 4: Theme Designer (AI-Assisted)

**AI Image Search for Inspiration**:
```
User: "Find JARVIS interface images"

AI searches:
1. Character screenshots (UI panels, displays)
2. Color palette references
3. Fan art and designs
4. Official promotional images

AI presents:
- Image grid with thumbnails
- Extracted color palettes from each
- Dominant colors analysis
- User selects favorite images

AI generates theme from selections
```

**AI Color Palette Generation**:

```python
# User selected images: JARVIS UI screenshots
# AI analyzes and generates:
{
  "primary": "#00D9FF",      # Cyan (arc reactor, UI accents)
  "secondary": "#0080FF",    # Blue (holographic displays)
  "accent": "#FFD700",       # Gold (highlights, warnings)
  "background": "#0A0E1A",   # Dark blue-black (panel backgrounds)
  "text": "#E0E0E0",        # Light gray (readable text)
  "success": "#00FF00",      # Green (confirmations)
  "warning": "#FFA500",      # Orange (alerts)
  "error": "#FF0000"         # Red (errors)
}
```

**Live Preview**:
- TUI mockup with real panels
- Switch between light/dark variants
- Adjust individual colors with sliders
- Compare with current theme
- Preview with selected images in background

**Theme Presets** (Quick Start):
- Cyberpunk (neon colors, dark backgrounds)
- Corporate (blues, grays, clean)
- Nature (greens, browns, earthy)
- Retro Terminal (green on black, amber on black)
- Sci-Fi (teals, purples, futuristic)

### Step 5: Generate & Test

**Compilation**:
1. Validate all inputs
2. Generate persona config JSON
3. **Adapt MOSHI voice** (or schedule for background - see Voice Adaptation below)
4. Apply theme to TUI
5. Set as active persona

**Test Interaction**:
- Voice input test
- Verify voice output matches target style
- Personality check (ask questions, check responses)
- Theme verification

**Export Options**:
- Save persona JSON to file
- Copy config to clipboard

## AI Assistance Details

### Web Search for Voice Samples

AI-powered search to find high-quality voice samples:

```python
async def search_voice_samples(character_name: str, context: str = None):
    """
    AI searches web for voice samples.
    """
    # Build search query
    search_queries = [
        f"{character_name} voice clips",
        f"{character_name} dialogue scenes",
        f"{character_name} interview",
        f"{character_name} audio samples"
    ]

    results = []

    for query in search_queries:
        # Search YouTube
        youtube_results = await search_youtube(query)
        for video in youtube_results[:5]:
            # AI analyzes video for speech quality
            quality_score = await analyze_video_quality(video.url)
            if quality_score > 0.7:
                results.append({
                    'source': 'youtube',
                    'url': video.url,
                    'title': video.title,
                    'duration': video.duration,
                    'quality': quality_score,
                    'thumbnail': video.thumbnail
                })

        # Search audio libraries (freesound.org, etc.)
        audio_results = await search_audio_libraries(query)
        results.extend(audio_results)

    # Rank results by quality
    results.sort(key=lambda x: x['quality'], reverse=True)

    return results[:20]  # Top 20 results
```

### Web Search for Theme Images

AI searches for visual inspiration:

```python
async def search_theme_images(character_name: str, keywords: list):
    """
    AI searches web for character interface images.
    """
    search_queries = [
        f"{character_name} interface design",
        f"{character_name} UI screenshots",
        f"{character_name} color palette",
        f"{character_name} visual aesthetic"
    ]

    results = []

    for query in search_queries:
        # Search images
        images = await search_images(query)

        for img in images[:10]:
            # Extract color palette
            palette = extract_color_palette(img.url)

            # Analyze composition
            composition = analyze_image_composition(img.url)

            results.append({
                'url': img.url,
                'thumbnail': img.thumbnail,
                'palette': palette,
                'dominant_colors': palette[:5],
                'composition_score': composition.score
            })

    return results[:30]  # Top 30 images
```

### Auto-Segmentation of Audio

AI identifies clean speech segments from long audio:

```python
def segment_audio(audio_file: str):
    """
    Automatically segment audio into clean speech clips.
    """
    # Load audio
    audio, sr = librosa.load(audio_file, sr=24000)

    # Voice activity detection
    speech_segments = detect_speech_segments(audio, sr)

    clips = []
    for start, end in speech_segments:
        # Extract segment
        segment = audio[start:end]

        # Quality check
        snr = calculate_snr(segment)
        clarity = measure_clarity(segment)

        if snr > 20 and clarity > 0.7:
            # Trim silence from edges
            trimmed = librosa.effects.trim(segment, top_db=20)[0]

            # Optimal length: 5-15s
            if 5.0 <= len(trimmed)/sr <= 15.0:
                clips.append({
                    'audio': trimmed,
                    'start_time': start/sr,
                    'end_time': end/sr,
                    'duration': len(trimmed)/sr,
                    'quality': {
                        'snr': snr,
                        'clarity': clarity
                    }
                })

    # Sort by quality
    clips.sort(key=lambda x: x['quality']['clarity'], reverse=True)

    return clips[:10]  # Top 10 clips
```

### Voice Analysis

```python
def analyze_voice_samples(audio_clips):
    """
    Extract voice characteristics from samples.
    """
    features = {
        'pitch': extract_pitch(audio_clips),      # High/low
        'tempo': extract_tempo(audio_clips),      # Fast/slow
        'energy': extract_energy(audio_clips),    # Calm/energetic
        'formality': detect_formality(audio_clips) # Casual/formal
    }

    # Map to personality traits
    traits = {
        'extraversion': map_energy_to_trait(features['energy']),
        'formality': features['formality'],
        'enthusiasm': features['energy'] * 0.7
    }

    return traits
```

### Personality Suggestions

```python
def suggest_personality(name, inspiration, voice_traits):
    """
    AI-powered personality suggestion.
    """
    prompt = f"""
    Based on:
    - Name: {name}
    - Inspiration: {inspiration}
    - Voice: {voice_traits}

    Suggest Big Five personality traits (0.0-1.0) and response style.
    """

    response = anthropic_client.complete(prompt)
    return parse_personality_response(response)
```

### Theme Generation

```python
def generate_theme(name, personality):
    """
    AI-powered color palette generation.
    """
    prompt = f"""
    Create a color theme for an AI assistant named "{name}".
    Personality: {personality}

    Provide:
    - Primary color (main accent)
    - Secondary color (highlights)
    - Accent color (buttons, links)
    - Background color (dark mode)
    - Text color

    Return as JSON with hex codes.
    """

    response = anthropic_client.complete(prompt)
    return parse_theme_response(response)
```

## MOSHI Voice Adaptation

The primary technical challenge of persona generation.

### Challenge

MOSHI is a pre-trained speech-to-speech model (not traditional TTS). It generates audio tokens directly from audio tokens without intermediate text. Adapting to new voices is non-trivial.

### Approach Options

**Option 1: Fine-tune Mimi Decoder** (Most Accurate, Computationally Expensive)
```python
# Fine-tune just the decoder on user samples
mimi_decoder = load_mimi_decoder()

# Train on user voice samples
for epoch in range(100):
    for sample in user_voice_samples:
        # Encode with frozen encoder
        codes = mimi_encoder.encode(sample)

        # Decode and compare to target
        output = mimi_decoder.decode(codes)
        loss = reconstruction_loss(output, sample)
        loss.backward()
        optimizer.step()

# Save personalized decoder
save_decoder(f'personas/{name}/mimi_decoder.pth')
```

**Pros**: Most faithful to source voice
**Cons**: Requires GPU, takes 10-30 minutes per persona, needs quality samples

**Option 2: Voice Style Transfer** (Balanced)
```python
# Use pre-trained voice conversion model
voice_converter = load_voice_converter()  # e.g., FreeVC, YourTTS

# Convert MOSHI output to target voice
moshi_output = moshi_generate(audio_input)
converted = voice_converter.convert(
    source_audio=moshi_output,
    target_style=user_voice_samples
)
```

**Pros**: Faster, works with any quality samples
**Cons**: Extra latency (~50-100ms), needs separate model

**Option 3: Voice Characteristic Matching** (Simplest, Least Accurate)
```python
# Analyze voice characteristics
target_features = extract_features(user_voice_samples)
# - Pitch (fundamental frequency)
# - Tempo (speaking rate)
# - Timbre (spectral characteristics)

# Apply post-processing to MOSHI output
moshi_output = moshi_generate(audio_input)
modified = apply_voice_characteristics(
    audio=moshi_output,
    target_pitch=target_features.pitch,
    target_tempo=target_features.tempo,
    target_timbre=target_features.timbre
)
```

**Pros**: Real-time, minimal compute
**Cons**: Only approximates voice, may sound synthetic

### Implementation Approach

**Fine-tuned Mimi Decoder** (Free Tier - Marketing Feature)

This is the primary implementation to make persona generation a powerful marketing tool.

**Process**:
1. User provides 5-10 voice samples (60-120s total) via AI search or upload
2. Background task fine-tunes Mimi decoder (~15-30 minutes on GPU)
3. Personalized decoder saved to persona config
4. User gets professional-quality voice matching

**Why Free Tier**:
- Marketing vector - word of mouth from quality results
- Users invest time collecting good samples
- Creates attachment to the platform
- Differentiates from competitors
- "I built my own JARVIS!" is shareable content

**Technical Requirements**:
- GPU: Required for fine-tuning (local or cloud)
- Time: 15-30 minutes per persona
- Storage: ~500MB per personalized decoder
- Compute: Can batch process during off-peak hours

**Cloud Fallback** (for users without GPU):
```python
# Detect local GPU
if not has_gpu():
    # Offer cloud fine-tuning
    if free_tier_quota_available():
        submit_cloud_training_job(voice_samples)
    else:
        # Free tier: 1 persona/month cloud processing
        # Paid tiers: unlimited cloud processing
        show_upgrade_or_wait_message()
```

**Quality Assurance**:
- Validate samples before fine-tuning
- Test output with standard phrases
- Compare with original samples (similarity score)
- Allow re-training with different samples if unsatisfied

### Voice Sample Requirements

For best results:

**Minimum**:
- 3 samples, 5-10 seconds each
- Clean audio (minimal background noise)
- Natural speech (not shouting, singing)
- Consistent microphone/recording quality

**Optimal**:
- 5-10 samples, 10-30 seconds each
- Multiple speaking styles (statement, question, emotion)
- High-quality recording (24kHz+, lossless format)
- Varied content (not repetitive phrases)

### Voice Quality Validation

```python
def validate_voice_samples(samples):
    """
    Check if samples are suitable for voice adaptation.
    """
    issues = []

    for sample in samples:
        # Check sample rate
        if sample.sample_rate < 16000:
            issues.append(f"Low sample rate: {sample.sample_rate}Hz (need 16kHz+)")

        # Check duration
        if sample.duration < 5.0:
            issues.append(f"Too short: {sample.duration}s (need 5s+)")

        # Check noise level
        snr = calculate_snr(sample)
        if snr < 20:
            issues.append(f"Too noisy: {snr}dB SNR (need 20dB+)")

        # Check speech presence
        if not detect_speech(sample):
            issues.append("No speech detected")

    return issues
```

### Background Processing

Voice adaptation can take time, so run in background:

```python
async def generate_persona_voice(persona_id, voice_samples):
    """
    Background task for voice adaptation.
    """
    # Update status
    update_persona_status(persona_id, 'processing_voice')

    try:
        # Validate samples
        issues = validate_voice_samples(voice_samples)
        if issues:
            raise ValueError(f"Sample issues: {issues}")

        # Choose method based on config
        if config.voice_method == 'characteristic_matching':
            features = extract_voice_features(voice_samples)
            save_voice_features(persona_id, features)

        elif config.voice_method == 'style_transfer':
            voice_model = train_voice_converter(voice_samples)
            save_voice_model(persona_id, voice_model)

        elif config.voice_method == 'fine_tune':
            decoder = fine_tune_mimi_decoder(voice_samples)
            save_decoder(persona_id, decoder)

        # Mark complete
        update_persona_status(persona_id, 'ready')
        notify_user(persona_id, 'Voice adaptation complete!')

    except Exception as e:
        update_persona_status(persona_id, 'failed')
        notify_user(persona_id, f'Voice adaptation failed: {e}')
```

### Testing Voice Output

```python
def test_persona_voice(persona_id, test_phrase="Hello, how can I help you?"):
    """
    Generate test audio with persona voice.
    """
    # Load persona config
    persona = load_persona(persona_id)

    # Generate with MOSHI
    audio_input = synthesize_prompt(test_phrase)
    moshi_output = moshi_generate(audio_input)

    # Apply voice adaptation
    if persona.voice_method == 'characteristic_matching':
        output = apply_voice_characteristics(moshi_output, persona.voice_features)
    elif persona.voice_method == 'style_transfer':
        output = voice_converter.convert(moshi_output, persona.voice_model)
    elif persona.voice_method == 'fine_tune':
        output = persona.mimi_decoder.decode(moshi_codes)

    return output
```

## Persona Storage

### Config Format

```json
{
  "version": "1.0",
  "name": "JARVIS",
  "created_at": "2025-11-19T10:30:00Z",
  "voice": {
    "samples": [
      "voice_samples/jarvis_01.wav",
      "voice_samples/jarvis_02.wav"
    ],
    "model": "trained_models/jarvis_voice.pth"
  },
  "personality": {
    "traits": {
      "extraversion": 0.3,
      "agreeableness": 0.8,
      "conscientiousness": 0.9,
      "neuroticism": 0.2,
      "openness": 0.6,
      "formality": 0.9,
      "enthusiasm": 0.5
    },
    "response_style": {
      "verbosity": "Balanced",
      "tone": "Professional",
      "humor_level": 0.2,
      "technical_depth": 0.7,
      "empathy_level": 0.6,
      "proactivity": 0.4
    }
  },
  "theme": {
    "name": "JARVIS",
    "colors": {
      "primary": "#00D9FF",
      "secondary": "#0080FF",
      "accent": "#FFD700",
      "background": "#0A0E1A",
      "text": "#E0E0E0"
    }
  },
  "greeting": "Good morning, sir. How may I assist you today?"
}
```

### Import/Export

```bash
# Export persona
assistant persona export jarvis -o jarvis.json

# Import persona
assistant persona import jarvis.json

# Share on community gallery (future)
assistant persona publish jarvis.json --gallery
```

## Community Personas (Future)

Vision for community-driven persona marketplace:

### Persona Gallery

- Browse popular personas
- Preview themes and voices
- One-click install
- User ratings and reviews

### Featured Personas

- JARVIS (Iron Man)
- GLaDOS (Portal)
- HAL 9000 (2001: A Space Odyssey)
- TARS (Interstellar)
- K.I.T.T. (Knight Rider)
- Cortana (Halo)
- Friday (Iron Man)
- Samantha (Her)

### Legal Considerations

Users create personas for personal use. Distribution of copyrighted character likeness is users' responsibility. We provide the tools, not the content.

**Platform Position**:
- We don't distribute copyrighted personas
- We don't host copyrighted voice samples
- Users create and share at their own discretion
- Similar to ringtone apps or theme generators

## Implementation Notes

### Voice Model Training

Voice samples used for:
1. TTS voice cloning (if implemented)
2. Voice characteristic analysis (pitch, tone, tempo)
3. Personality trait suggestions

For v1, skip voice cloning and use samples for analysis only. Voice cloning can be added in future versions.

### UI Framework

Built with Textual:
- Wizard navigation (back/next buttons)
- Tab-based step indicators
- Real-time preview panels
- Audio player widget
- Color picker widget
- Slider widgets for traits

### Performance

- Keep wizard responsive (<100ms step transitions)
- Background voice analysis (don't block UI)
- Lazy load theme previews
- Cache AI suggestions

### Error Handling

- Invalid audio formats → Show supported formats
- Failed YouTube extraction → Suggest direct upload
- AI API errors → Fallback to defaults
- Missing required fields → Highlight and explain

## Viral Growth Metrics

Track to measure viral adoption:

- Personas created per user
- Screenshots/videos shared (detect social media links)
- Time to create first persona (target: <5 min)
- Persona import/export usage
- Community gallery engagement (future)

**Target**: 70% of free tier users create at least one custom persona within first week.
