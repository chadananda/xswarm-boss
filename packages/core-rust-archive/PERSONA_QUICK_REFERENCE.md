# Persona System - Quick Reference

## API Endpoints Summary

| Method | Endpoint | Description | Tier |
|--------|----------|-------------|------|
| `POST` | `/api/personas` | Create new persona | Free (limit 3) |
| `GET` | `/api/personas` | List all personas | All |
| `GET` | `/api/personas/active` | Get active persona | All |
| `GET` | `/api/personas/:id` | Get specific persona | All |
| `PUT` | `/api/personas/:id` | Update persona | All |
| `DELETE` | `/api/personas/:id` | Delete persona | All |
| `POST` | `/api/personas/:id/activate` | Activate persona | All |
| `POST` | `/api/personas/:id/learn` | Add conversation example | All |
| `POST` | `/api/personas/:id/train-voice` | Train voice model | Personal+ |
| `GET` | `/api/personas/:id/training-status` | Get training status | Personal+ |

## Personality Trait Ranges

All values: `0.0` (low) to `1.0` (high)

```javascript
{
  extraversion: 0.5,       // Introvert → Extravert
  agreeableness: 0.5,      // Competitive → Collaborative
  conscientiousness: 0.5,  // Flexible → Disciplined
  neuroticism: 0.5,        // Confident → Sensitive
  openness: 0.5,           // Practical → Creative
  formality: 0.5,          // Casual → Formal
  enthusiasm: 0.5          // Reserved → Enthusiastic
}
```

## Response Style Options

### Verbosity
- `Concise` - Brief, to-the-point
- `Balanced` - Normal conversation
- `Detailed` - Comprehensive
- `Elaborate` - Extensive detail

### Tone
- `Professional` - Business-like
- `Friendly` - Warm, approachable
- `Casual` - Relaxed, informal
- `Authoritative` - Confident, directive
- `Supportive` - Encouraging, empathetic
- `Analytical` - Logical, fact-based

### Style Values (0.0 - 1.0)
```javascript
{
  humor_level: 0.5,
  technical_depth: 0.5,
  empathy_level: 0.5,
  proactivity: 0.5
}
```

## Common Use Cases

### 1. Create Professional Assistant

```javascript
POST /api/personas

{
  "name": "Alex",
  "description": "Professional business assistant",
  "personality_traits": {
    "formality": 0.9,
    "conscientiousness": 0.9,
    "enthusiasm": 0.4
  },
  "response_style": {
    "verbosity": "Balanced",
    "tone": "Professional",
    "humor_level": 0.2,
    "technical_depth": 0.6,
    "empathy_level": 0.5,
    "proactivity": 0.7
  },
  "expertise_areas": ["business", "scheduling", "email"]
}
```

### 2. Create Friendly Companion

```javascript
POST /api/personas

{
  "name": "Buddy",
  "description": "Friendly conversational AI",
  "personality_traits": {
    "extraversion": 0.9,
    "agreeableness": 0.9,
    "enthusiasm": 0.8,
    "formality": 0.3
  },
  "response_style": {
    "verbosity": "Detailed",
    "tone": "Friendly",
    "humor_level": 0.7,
    "empathy_level": 0.9
  }
}
```

### 3. Create Technical Expert

```javascript
POST /api/personas

{
  "name": "DevBot",
  "description": "Expert software development assistant",
  "personality_traits": {
    "openness": 0.8,
    "conscientiousness": 0.8,
    "formality": 0.6
  },
  "response_style": {
    "verbosity": "Elaborate",
    "tone": "Analytical",
    "technical_depth": 1.0,
    "humor_level": 0.3
  },
  "expertise_areas": [
    "programming",
    "architecture",
    "debugging",
    "devops"
  ]
}
```

### 4. Activate Persona

```javascript
POST /api/personas/{personaId}/activate
```

Deactivates all other personas automatically.

### 5. Add Learning Example

```javascript
POST /api/personas/{personaId}/learn

{
  "user_message": "Schedule a meeting tomorrow at 2pm",
  "persona_response": "I've scheduled your meeting for tomorrow at 2:00 PM. Would you like me to send calendar invites?",
  "context": "scheduling",
  "quality_score": 0.95
}
```

### 6. Train Voice (Personal Tier)

```javascript
POST /api/personas/{personaId}/train-voice

{
  "audio_samples": [
    "base64_encoded_audio_1",
    "base64_encoded_audio_2",
    // ... minimum 5 samples
  ],
  "sample_texts": [
    "Hello, how can I help you today?",
    "Your meeting is scheduled for 2pm"
  ]
}
```

## Rust Usage

### Setup Client

```rust
use xswarm::personas::PersonaClient;
use uuid::Uuid;

let client = PersonaClient::new(
    "https://api.xswarm.ai".to_string(),
    user_id,
    "auth_token".to_string(),
);
```

### Create Persona

```rust
use xswarm::personas::{
    CreatePersonaRequest,
    PersonalityTraits,
    ResponseStyle,
    VerbosityLevel,
    ToneStyle,
};

let request = CreatePersonaRequest {
    name: "Jarvis".to_string(),
    description: Some("AI butler".to_string()),
    personality_traits: Some(PersonalityTraits {
        formality: 0.9,
        ..Default::default()
    }),
    response_style: Some(ResponseStyle {
        verbosity: VerbosityLevel::Balanced,
        tone: ToneStyle::Professional,
        ..Default::default()
    }),
    expertise_areas: Some(vec!["technology".to_string()]),
};

let persona = client.create_persona(request).await?;
```

### Build Prompt

```rust
use xswarm::personas::build_persona_prompt;

let prompt = build_persona_prompt(&persona, "What's the weather?");
// Use prompt with AI model...
```

### Apply Style

```rust
use xswarm::personas::apply_persona_style;

let response = generate_response(&prompt).await?;
let styled = apply_persona_style(&persona, response);
```

## Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| `TIER_LIMIT_EXCEEDED` | Free tier limit (3 personas) | Upgrade to Personal |
| `NOT_FOUND` | Persona doesn't exist | Check persona ID |
| `FORBIDDEN` | Access denied | Verify ownership |
| `TIER_REQUIRED` | Personal tier needed | Upgrade for feature |
| `INSUFFICIENT_SAMPLES` | Need more audio samples | Provide 5+ samples |

## Response Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `202` | Accepted (async operation) |
| `400` | Bad request |
| `401` | Unauthorized |
| `402` | Payment required (tier limit) |
| `403` | Forbidden |
| `404` | Not found |
| `500` | Server error |

## Database Queries

### Count User Personas

```sql
SELECT COUNT(*) FROM personas WHERE user_id = ?
```

### Get Active Persona

```sql
SELECT * FROM personas WHERE user_id = ? AND is_active = TRUE
```

### Check Tier Limit

```sql
SELECT
  u.subscription_tier,
  COUNT(p.id) as persona_count
FROM users u
LEFT JOIN personas p ON u.id = p.user_id
WHERE u.id = ?
GROUP BY u.subscription_tier
```

## Testing

```bash
# Run test suite
cd packages/server
node test-personas-api.js

# Expected output:
✅ create
✅ list
✅ get
✅ update
✅ activate
✅ addExample
✅ tierLimits
✅ delete

8/8 tests passed
```

## Migration

Apply schema:

```bash
cd packages/server
sqlite3 production.db < migrations/personas.sql
```

Or with Turso:

```bash
turso db shell xswarm-db < migrations/personas.sql
```
