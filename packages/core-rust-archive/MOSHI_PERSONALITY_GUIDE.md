# MOSHI Personality Configuration Guide

This guide explains how to configure MOSHI with different personalities for your Jarvis-like conversation system.

## Overview

The MOSHI personality system allows you to customize the assistant's behavior, communication style, and response patterns. Unlike traditional LLMs with system prompts, MOSHI uses conversation context injection and response conditioning to shape its personality.

## Architecture

### Components

1. **MoshiPersonality** - Core personality configuration combining:
   - PersonaConfig (traits, expertise, style)
   - AssistantRole (Jarvis-like behaviors)
   - ResponseConfig (real-time voice settings)

2. **PersonalityManager** - Manages personality state and provides:
   - Dynamic personality switching
   - Context prompt generation
   - Greeting generation

3. **VoiceBridge Integration** - Injects personality into conversations:
   - Context injection at conversation start
   - Response prefix generation
   - Personality-aware processing

## Quick Start

### Default Jarvis Personality

```rust
use xswarm::voice::VoiceBridge;
use xswarm::moshi_personality::MoshiPersonality;

// Create voice bridge with default Jarvis personality
let bridge = VoiceBridge::new(config).await?;

// Personality is automatically initialized
// Get the current personality
let personality = bridge.get_personality().await;
println!("Current assistant: {}", personality.assistant_role.name);

// Inject personality context at conversation start
bridge.inject_personality_context().await?;

// Generate a greeting
let greeting = bridge.generate_personality_greeting().await;
println!("{}", greeting); // "Good day. How may I assist you?"
```

### Custom Personality

```rust
use xswarm::moshi_personality::{MoshiPersonality, AssistantRole, ResponseConfig};
use xswarm::personas::{PersonalityTraits, ResponseStyle, VerbosityLevel, ToneStyle};

// Create a friendly casual assistant
let friendly_personality = MoshiPersonality::friendly();

// Set it on the voice bridge
bridge.set_personality(friendly_personality).await?;

// Re-inject context for new personality
bridge.inject_personality_context().await?;
```

## Personality Types

### 1. Jarvis (Professional Assistant)

```rust
let jarvis = MoshiPersonality::jarvis();
```

**Characteristics:**
- Professional but warm
- Highly proactive and anticipatory
- Clear, concise communication
- Technical expertise
- Formal but not stiff

**Use Cases:**
- Executive assistance
- Task management
- Calendar coordination
- Information retrieval

**Sample Interaction:**
```
User: "Schedule a meeting tomorrow."
Jarvis: "Certainly. What time would be most convenient, and who should I invite?"
```

### 2. Friendly Assistant

```rust
let friendly = MoshiPersonality::friendly();
```

**Characteristics:**
- Warm and approachable
- High empathy
- Casual communication
- Enthusiastic engagement
- Supportive tone

**Use Cases:**
- Personal assistance
- Casual conversations
- Emotional support
- General help

**Sample Interaction:**
```
User: "I need some help."
Assistant: "Hey there! I'd be happy to help. What can I do for you?"
```

## Customizing Personality

### Step-by-Step Customization

```rust
use xswarm::moshi_personality::MoshiPersonality;
use xswarm::personas::{PersonaConfig, PersonalityTraits, ResponseStyle};

// Start with a base personality
let mut custom = MoshiPersonality::jarvis();

// Adjust personality traits
custom.persona.personality_traits.formality = 0.5; // Less formal
custom.persona.personality_traits.enthusiasm = 0.8; // More enthusiastic
custom.persona.personality_traits.extraversion = 0.7; // More outgoing

// Adjust response style
custom.persona.response_style.verbosity = VerbosityLevel::Concise;
custom.persona.response_style.humor_level = 0.5; // Moderate humor
custom.persona.response_style.technical_depth = 0.6; // Moderately technical

// Customize assistant role
custom.assistant_role.name = "MOSHI".to_string();
custom.assistant_role.guidelines = vec![
    "Be helpful and friendly".to_string(),
    "Keep responses brief but complete".to_string(),
    "Use casual language".to_string(),
];

// Adjust response configuration
custom.response_config.max_response_length = 50; // Shorter responses
custom.response_config.response_delay_ms = 200; // Faster responses

// Apply the custom personality
bridge.set_personality(custom).await?;
bridge.inject_personality_context().await?;
```

## Personality Traits Reference

### Core Traits (0.0 - 1.0)

| Trait | Low (0.0-0.3) | Medium (0.4-0.6) | High (0.7-1.0) |
|-------|---------------|------------------|----------------|
| **Extraversion** | Reserved, quiet | Balanced social energy | Outgoing, talkative |
| **Agreeableness** | Competitive, direct | Collaborative | Highly cooperative |
| **Conscientiousness** | Flexible, spontaneous | Balanced | Disciplined, organized |
| **Neuroticism** | Confident, calm | Balanced | Sensitive, cautious |
| **Openness** | Practical, traditional | Balanced | Creative, innovative |
| **Formality** | Casual, informal | Professional | Very formal, proper |
| **Enthusiasm** | Reserved, measured | Engaged | Highly energetic |

### Response Style Parameters

| Parameter | Low | Medium | High |
|-----------|-----|--------|------|
| **Humor** | Serious | Light humor | Playful |
| **Technical Depth** | Simple explanations | Balanced | Highly technical |
| **Empathy** | Factual | Understanding | Deeply supportive |
| **Proactivity** | Reactive only | Balanced | Highly anticipatory |

## Verbosity Levels

```rust
use xswarm::personas::VerbosityLevel;

// Concise - Brief, to-the-point
custom.persona.response_style.verbosity = VerbosityLevel::Concise;
// Example: "Meeting scheduled for 2pm tomorrow."

// Balanced - Normal conversation (recommended for voice)
custom.persona.response_style.verbosity = VerbosityLevel::Balanced;
// Example: "I've scheduled your meeting for 2pm tomorrow. Would you like me to send calendar invites?"

// Detailed - Comprehensive explanations
custom.persona.response_style.verbosity = VerbosityLevel::Detailed;
// Example: "I've scheduled your meeting for 2pm tomorrow in Conference Room A. I've sent calendar invites to all three participants with the meeting agenda you provided. The room is equipped with video conferencing if needed."

// Elaborate - Extensive, thorough (use sparingly for voice)
custom.persona.response_style.verbosity = VerbosityLevel::Elaborate;
```

## Tone Styles

```rust
use xswarm::personas::ToneStyle;

// Professional - Business-like, formal
custom.persona.response_style.tone = ToneStyle::Professional;

// Friendly - Warm, approachable
custom.persona.response_style.tone = ToneStyle::Friendly;

// Casual - Relaxed, informal
custom.persona.response_style.tone = ToneStyle::Casual;

// Authoritative - Confident, directive
custom.persona.response_style.tone = ToneStyle::Authoritative;

// Supportive - Encouraging, empathetic
custom.persona.response_style.tone = ToneStyle::Supportive;

// Analytical - Logical, fact-based
custom.persona.response_style.tone = ToneStyle::Analytical;
```

## Response Configuration

### Real-Time Voice Settings

```rust
use xswarm::moshi_personality::{ResponseConfig, InterruptHandling};

custom.response_config = ResponseConfig {
    // Maximum response length (in tokens)
    // Recommended: 50-100 for voice conversations
    max_response_length: 75,

    // Delay before responding (ms)
    // Creates natural conversation flow
    response_delay_ms: 300,

    // Enable filler words ("um", "let me see", etc.)
    // Makes conversation more natural
    use_filler_words: true,

    // How to handle interruptions
    interrupt_handling: InterruptHandling::Graceful,
};
```

### Interrupt Handling Modes

```rust
use xswarm::moshi_personality::InterruptHandling;

// Stop immediately when user speaks
custom.response_config.interrupt_handling = InterruptHandling::Immediate;

// Finish current sentence then stop (recommended)
custom.response_config.interrupt_handling = InterruptHandling::Graceful;

// Continue speaking (override interruptions)
custom.response_config.interrupt_handling = InterruptHandling::Continue;
```

## Integration Examples

### Voice Bridge Initialization

```rust
use std::sync::Arc;
use xswarm::voice::{VoiceBridge, VoiceConfig};
use xswarm::moshi_personality::MoshiPersonality;

// Create voice bridge
let config = VoiceConfig::default();
let bridge = Arc::new(VoiceBridge::new(config).await?);

// Set Jarvis personality
let jarvis = MoshiPersonality::jarvis();
bridge.set_personality(jarvis).await?;

// Inject personality context at conversation start
bridge.inject_personality_context().await?;

// Generate greeting
let greeting = bridge.generate_personality_greeting().await;
println!("{}", greeting);
```

### Dynamic Personality Switching

```rust
// Start with professional Jarvis
bridge.set_personality(MoshiPersonality::jarvis()).await?;
bridge.inject_personality_context().await?;

// Later, switch to friendly mode
bridge.set_personality(MoshiPersonality::friendly()).await?;
bridge.inject_personality_context().await?;

// Or create custom personality on-the-fly
let mut custom = MoshiPersonality::jarvis();
custom.persona.personality_traits.formality = 0.4; // More casual
custom.response_config.use_filler_words = false; // More direct
bridge.set_personality(custom).await?;
bridge.inject_personality_context().await?;
```

### Accessing Personality Manager

```rust
// Get personality manager for advanced control
let manager = bridge.get_personality_manager().await;

// Generate context manually
let context = manager.generate_context_prompt().await;
println!("Personality context: {}", context);

// Generate greeting manually
let greeting = manager.generate_greeting().await;
println!("Greeting: {}", greeting);
```

## Best Practices

### For Voice Conversations

1. **Keep responses concise** - Use `VerbosityLevel::Concise` or `Balanced`
2. **Natural delays** - Set `response_delay_ms` to 200-400ms
3. **Graceful interrupts** - Use `InterruptHandling::Graceful`
4. **Moderate formality** - 0.5-0.7 works well for most contexts
5. **Enable filler words** - Makes conversation more natural

### For Different Use Cases

**Task Management:**
```rust
let mut task_assistant = MoshiPersonality::jarvis();
task_assistant.persona.expertise_areas = vec![
    "Task management".to_string(),
    "Productivity".to_string(),
    "Project planning".to_string(),
];
task_assistant.persona.response_style.proactivity = 0.9; // Very proactive
task_assistant.persona.response_style.verbosity = VerbosityLevel::Concise;
```

**Emotional Support:**
```rust
let mut support_assistant = MoshiPersonality::friendly();
support_assistant.persona.response_style.empathy_level = 0.9;
support_assistant.persona.response_style.tone = ToneStyle::Supportive;
support_assistant.persona.personality_traits.agreeableness = 0.9;
```

**Technical Support:**
```rust
let mut tech_assistant = MoshiPersonality::jarvis();
tech_assistant.persona.expertise_areas = vec!["Technology".to_string(), "Troubleshooting".to_string()];
tech_assistant.persona.response_style.technical_depth = 0.8;
tech_assistant.persona.response_style.tone = ToneStyle::Analytical;
```

## Environment Configuration

Add to `.env` or configuration file:

```env
# Default personality type (jarvis, friendly, or custom)
MOSHI_PERSONALITY=jarvis

# Personality customization
MOSHI_FORMALITY=0.7
MOSHI_ENTHUSIASM=0.6
MOSHI_VERBOSITY=balanced
MOSHI_RESPONSE_DELAY_MS=300
```

## Troubleshooting

### Personality Not Taking Effect

**Problem:** Changes to personality don't seem to affect responses.

**Solution:** Always call `inject_personality_context()` after changing personality:
```rust
bridge.set_personality(new_personality).await?;
bridge.inject_personality_context().await?; // Don't forget this!
```

### Responses Too Long

**Problem:** Voice responses are too lengthy.

**Solution:** Adjust verbosity and max response length:
```rust
custom.persona.response_style.verbosity = VerbosityLevel::Concise;
custom.response_config.max_response_length = 50;
```

### Personality Feels Inconsistent

**Problem:** Assistant doesn't consistently maintain personality.

**Solution:**
1. Ensure context is injected at conversation start
2. Check trait values are within expected ranges (0.0-1.0)
3. Verify personality manager is properly initialized

## Advanced Topics

### Creating Personality Presets

```rust
pub fn create_executive_assistant() -> MoshiPersonality {
    let mut exec = MoshiPersonality::jarvis();
    exec.persona.name = "Executive Assistant".to_string();
    exec.persona.personality_traits.conscientiousness = 0.95;
    exec.persona.personality_traits.formality = 0.8;
    exec.persona.response_style.proactivity = 0.9;
    exec.persona.response_style.verbosity = VerbosityLevel::Concise;
    exec
}

pub fn create_personal_companion() -> MoshiPersonality {
    let mut companion = MoshiPersonality::friendly();
    companion.persona.response_style.empathy_level = 0.95;
    companion.persona.personality_traits.enthusiasm = 0.8;
    companion.persona.response_style.tone = ToneStyle::Supportive;
    companion
}
```

### Personality Persistence

```rust
use serde_json;

// Save personality to file
let personality = bridge.get_personality().await;
let json = serde_json::to_string_pretty(&personality)?;
std::fs::write("my_personality.json", json)?;

// Load personality from file
let json = std::fs::read_to_string("my_personality.json")?;
let personality: MoshiPersonality = serde_json::from_str(&json)?;
bridge.set_personality(personality).await?;
```

## Next Steps

- Explore `packages/core/src/moshi_personality.rs` for implementation details
- Check `packages/core/src/personas/mod.rs` for persona system
- Review `packages/core/src/voice.rs` for MOSHI integration
- Create custom personality presets for your use cases

## Support

For questions or issues:
- Check the source code documentation
- Review example implementations
- Consult the xSwarm documentation
