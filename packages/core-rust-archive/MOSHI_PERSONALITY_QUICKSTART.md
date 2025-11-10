# MOSHI Personality Quick Start

## 30-Second Setup

```rust
use xswarm::voice::{VoiceBridge, VoiceConfig};

// 1. Create voice bridge (Jarvis personality auto-initialized)
let bridge = VoiceBridge::new(VoiceConfig::default()).await?;

// 2. Inject personality at conversation start
bridge.inject_personality_context().await?;

// 3. Generate greeting
let greeting = bridge.generate_personality_greeting().await;
println!("{}", greeting); // "Good day. How may I assist you?"
```

## Switch to Friendly Mode

```rust
use xswarm::moshi_personality::MoshiPersonality;

bridge.set_personality(MoshiPersonality::friendly()).await?;
bridge.inject_personality_context().await?;
```

## Create Custom Personality

```rust
use xswarm::moshi_personality::MoshiPersonality;
use xswarm::personas::VerbosityLevel;

let mut custom = MoshiPersonality::jarvis();
custom.persona.personality_traits.formality = 0.5; // More casual
custom.persona.response_style.verbosity = VerbosityLevel::Concise;
custom.response_config.max_response_length = 50;

bridge.set_personality(custom).await?;
bridge.inject_personality_context().await?;
```

## Personality Traits Cheat Sheet

| Trait | Jarvis | Friendly |
|-------|--------|----------|
| Formality | 0.7 (Professional) | 0.3 (Casual) |
| Enthusiasm | 0.6 (Engaged) | 0.8 (Energetic) |
| Conscientiousness | 0.9 (Disciplined) | 0.7 (Balanced) |
| Empathy | 0.7 (Supportive) | 0.9 (Very supportive) |
| Proactivity | 0.8 (Very proactive) | 0.7 (Proactive) |

## Common Customizations

**More Casual Jarvis:**
```rust
let mut casual_jarvis = MoshiPersonality::jarvis();
casual_jarvis.persona.personality_traits.formality = 0.4;
casual_jarvis.persona.personality_traits.enthusiasm = 0.8;
```

**Professional Friendly:**
```rust
let mut professional_friendly = MoshiPersonality::friendly();
professional_friendly.persona.personality_traits.formality = 0.6;
professional_friendly.persona.response_style.tone = ToneStyle::Professional;
```

**Concise Responder:**
```rust
custom.persona.response_style.verbosity = VerbosityLevel::Concise;
custom.response_config.max_response_length = 30;
```

**Quick Responder:**
```rust
custom.response_config.response_delay_ms = 150;
custom.response_config.use_filler_words = false;
```

## Files to Know

- **Guide:** `MOSHI_PERSONALITY_GUIDE.md` - Comprehensive documentation
- **Example:** `examples/moshi_personality_example.rs` - Run with `cargo run --example moshi_personality_example`
- **Source:** `src/moshi_personality.rs` - Implementation
- **Integration:** `src/voice.rs` - VoiceBridge methods

## Key Methods

```rust
// Get current personality
let personality = bridge.get_personality().await;

// Set new personality
bridge.set_personality(new_personality).await?;

// Inject context (IMPORTANT: call after setting personality!)
bridge.inject_personality_context().await?;

// Generate greeting
let greeting = bridge.generate_personality_greeting().await;
```

## Remember

1. **Always** call `inject_personality_context()` after changing personality
2. Use **Concise** or **Balanced** verbosity for voice
3. Set response delay to **200-400ms** for natural conversation
4. Keep formality at **0.5-0.7** for general use
5. Enable **filler words** for natural speech

## Help

Run the example to see all features:
```bash
cargo run --example moshi_personality_example
```

Read the full guide for detailed info:
```bash
cat MOSHI_PERSONALITY_GUIDE.md
```
