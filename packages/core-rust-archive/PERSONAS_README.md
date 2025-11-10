# Persona System Documentation

## Overview

The xSwarm Persona System allows users to create multiple AI personalities with distinct characteristics, voice models, and conversation styles. Each persona has customizable personality traits, response styles, and areas of expertise.

## Architecture

### Components

1. **Database Layer** (`packages/server/migrations/personas.sql`)
   - SQLite/Turso database schema
   - Personas, training sessions, and voice samples tables
   - Tier-based access control
   - Automatic triggers and views

2. **API Layer** (`packages/server/src`)
   - RESTful API endpoints (`routes/personas.js`)
   - Business logic (`lib/personas.js`)
   - Tier limit enforcement
   - Authentication and authorization

3. **Core Library** (`packages/core/src/personas`)
   - Rust types and utilities
   - HTTP client for API communication
   - Prompt generation
   - Style application

## Tier Limits

| Tier         | Personas | Voice Training |
|--------------|----------|----------------|
| Free         | 3        | ❌             |
| Personal     | Unlimited| ✅             |
| Professional | Unlimited| ✅             |
| Enterprise   | Unlimited| ✅             |

## Database Schema

### `personas` Table

```sql
CREATE TABLE personas (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    personality_traits TEXT, -- JSON
    response_style TEXT,     -- JSON
    expertise_areas TEXT,    -- JSON array
    voice_model_config TEXT, -- JSON
    conversation_examples TEXT, -- JSON array
    is_active BOOLEAN DEFAULT FALSE,
    created_at TEXT,
    updated_at TEXT
);
```

### Personality Traits

All traits are normalized 0.0 - 1.0:

- **extraversion**: Introvert (0.0) → Extravert (1.0)
- **agreeableness**: Competitive (0.0) → Collaborative (1.0)
- **conscientiousness**: Flexible (0.0) → Disciplined (1.0)
- **neuroticism**: Confident (0.0) → Sensitive (1.0)
- **openness**: Practical (0.0) → Creative (1.0)
- **formality**: Casual (0.0) → Formal (1.0)
- **enthusiasm**: Reserved (0.0) → Enthusiastic (1.0)

### Response Style

- **verbosity**: `Concise | Balanced | Detailed | Elaborate`
- **tone**: `Professional | Friendly | Casual | Authoritative | Supportive | Analytical`
- **humor_level**: 0.0 - 1.0
- **technical_depth**: 0.0 (simple) - 1.0 (technical)
- **empathy_level**: 0.0 - 1.0
- **proactivity**: 0.0 (reactive) - 1.0 (proactive)

## API Endpoints

### Create Persona

```http
POST /api/personas
Authorization: Bearer {token}
X-User-Id: {user_id}

{
  "name": "Jarvis",
  "description": "A sophisticated AI butler",
  "personality_traits": {
    "extraversion": 0.6,
    "formality": 0.9,
    "enthusiasm": 0.5
  },
  "response_style": {
    "verbosity": "Balanced",
    "tone": "Professional",
    "humor_level": 0.3
  },
  "expertise_areas": ["technology", "scheduling"]
}
```

**Response:**
```json
{
  "success": true,
  "persona": {
    "id": "uuid",
    "name": "Jarvis",
    "is_active": false,
    ...
  }
}
```

**Tier Limit Error (402):**
```json
{
  "error": "Free tier limited to 3 personas...",
  "code": "TIER_LIMIT_EXCEEDED",
  "upgrade_cta": {
    "tier": "personal",
    "feature": "unlimited_personas",
    "benefit": "Create unlimited AI personalities"
  }
}
```

### List Personas

```http
GET /api/personas
Authorization: Bearer {token}
X-User-Id: {user_id}
```

**Response:**
```json
{
  "success": true,
  "personas": [...],
  "meta": {
    "total": 2,
    "limit": 3,
    "can_create_more": true,
    "tier": "free"
  }
}
```

### Get Active Persona

```http
GET /api/personas/active
Authorization: Bearer {token}
X-User-Id: {user_id}
```

### Get Specific Persona

```http
GET /api/personas/{personaId}
Authorization: Bearer {token}
X-User-Id: {user_id}
```

### Update Persona

```http
PUT /api/personas/{personaId}
Authorization: Bearer {token}
X-User-Id: {user_id}

{
  "description": "Updated description",
  "expertise_areas": ["new", "areas"]
}
```

### Delete Persona

```http
DELETE /api/personas/{personaId}
Authorization: Bearer {token}
X-User-Id: {user_id}
```

### Activate Persona

```http
POST /api/personas/{personaId}/activate
Authorization: Bearer {token}
X-User-Id: {user_id}
```

Automatically deactivates other personas for the user.

### Add Conversation Example

```http
POST /api/personas/{personaId}/learn
Authorization: Bearer {token}
X-User-Id: {user_id}

{
  "user_message": "What's on my schedule?",
  "persona_response": "You have a meeting at 2pm...",
  "context": "scheduling_query",
  "quality_score": 0.9
}
```

Stores up to 100 recent conversation examples for learning.

### Train Voice Model

```http
POST /api/personas/{personaId}/train-voice
Authorization: Bearer {token}
X-User-Id: {user_id}

{
  "audio_samples": ["base64...", "base64..."],
  "sample_texts": ["Hello world", "How are you?"]
}
```

**Requires:** Personal tier or higher
**Minimum:** 5 audio samples

**Response (202 Accepted):**
```json
{
  "success": true,
  "session": {
    "id": "uuid",
    "status": "pending",
    "progress_percent": 0
  },
  "message": "Voice training started"
}
```

### Get Training Status

```http
GET /api/personas/{personaId}/training-status
Authorization: Bearer {token}
X-User-Id: {user_id}
```

**Response:**
```json
{
  "success": true,
  "sessions": [
    {
      "id": "uuid",
      "training_type": "voice_model",
      "status": "completed",
      "progress_percent": 100,
      "completed_at": "2025-10-30T..."
    }
  ]
}
```

## Rust Integration

### Using PersonaClient

```rust
use xswarm::personas::{PersonaClient, CreatePersonaRequest};
use uuid::Uuid;

let client = PersonaClient::new(
    "https://api.xswarm.ai".to_string(),
    user_id,
    auth_token,
);

// Create persona
let request = CreatePersonaRequest {
    name: "Jarvis".to_string(),
    description: Some("AI butler".to_string()),
    personality_traits: None, // Uses defaults
    response_style: None,
    expertise_areas: Some(vec!["technology".to_string()]),
};

let persona = client.create_persona(request).await?;

// Get active persona
let active = client.get_active_persona().await?;

// Activate persona
let activated = client.activate_persona(persona_id).await?;
```

### Building Persona-Aware Prompts

```rust
use xswarm::personas::{build_persona_prompt, apply_persona_style};

// Generate prompt with persona context
let prompt = build_persona_prompt(&persona, "What's the weather?");

// Send to AI model...
let mut response = generate_ai_response(&prompt).await?;

// Apply persona-specific style
response = apply_persona_style(&persona, response);
```

## Voice Integration

The persona system integrates with the MOSHI voice bridge for real-time conversations:

1. **Active Persona Detection**: Voice bridge retrieves user's active persona
2. **Prompt Generation**: Uses `build_persona_prompt()` with persona traits
3. **Response Processing**: Applies `apply_persona_style()` to output
4. **Learning**: Stores high-quality interactions as conversation examples

## Testing

Run the comprehensive test suite:

```bash
cd packages/server
node test-personas-api.js
```

Tests cover:
- ✅ Create persona
- ✅ List personas
- ✅ Get persona by ID
- ✅ Update persona
- ✅ Activate persona
- ✅ Add conversation example
- ✅ Tier limit enforcement
- ✅ Delete persona

## Future Enhancements

### Phase 1 (Implemented)
- ✅ Database schema
- ✅ RESTful API
- ✅ Rust types and client
- ✅ Tier-based limits
- ✅ Conversation learning

### Phase 2 (Planned)
- [ ] Voice training implementation (Personal tier)
- [ ] Real-time persona switching in voice calls
- [ ] Personality-aware response generation
- [ ] Voice clone model training
- [ ] Advanced conversation analytics

### Phase 3 (Future)
- [ ] Persona marketplace
- [ ] Shared/team personas
- [ ] A/B testing for persona effectiveness
- [ ] Multi-language personas
- [ ] Emotion detection and adaptation

## Best Practices

### Creating Effective Personas

1. **Name**: Choose memorable, personality-reflecting names
2. **Personality Traits**: Adjust for desired interaction style
3. **Expertise Areas**: List specific domains for better context
4. **Response Style**: Match tone to use case (support vs. assistant)

### Example Personas

**Professional Assistant**
```json
{
  "name": "Alex",
  "personality_traits": {
    "formality": 0.8,
    "conscientiousness": 0.9,
    "enthusiasm": 0.5
  },
  "response_style": {
    "verbosity": "Balanced",
    "tone": "Professional",
    "technical_depth": 0.7
  }
}
```

**Friendly Companion**
```json
{
  "name": "Buddy",
  "personality_traits": {
    "extraversion": 0.9,
    "agreeableness": 0.9,
    "enthusiasm": 0.8
  },
  "response_style": {
    "verbosity": "Detailed",
    "tone": "Friendly",
    "humor_level": 0.7
  }
}
```

**Technical Expert**
```json
{
  "name": "TechBot",
  "personality_traits": {
    "openness": 0.8,
    "conscientiousness": 0.7
  },
  "response_style": {
    "verbosity": "Elaborate",
    "tone": "Analytical",
    "technical_depth": 1.0
  },
  "expertise_areas": ["programming", "architecture", "devops"]
}
```

## Troubleshooting

### "Tier limit exceeded"
**Problem:** Free tier users can only create 3 personas
**Solution:** Upgrade to Personal tier for unlimited personas

### "Persona not found"
**Problem:** Invalid persona ID or deleted persona
**Solution:** Use `GET /api/personas` to list valid personas

### "Voice training requires Personal tier"
**Problem:** Trying to train voice model on Free tier
**Solution:** Upgrade to Personal tier or higher

### "Access denied"
**Problem:** Trying to access another user's persona
**Solution:** Ensure proper authentication and user ID

## Support

For questions or issues:
- API Documentation: `/api/docs`
- GitHub Issues: [xswarm-boss/issues](https://github.com/xswarm/xswarm-boss/issues)
- Email: support@xswarm.ai
