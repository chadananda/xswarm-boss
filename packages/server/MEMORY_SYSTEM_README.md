# Semantic Memory System

Comprehensive 3-tier memory architecture with vector embeddings for contextual AI conversations.

## Architecture Overview

The memory system provides three layers of memory:

1. **Session Memory** - Current conversation context (short-term)
2. **Episodic Memory** - Recent interactions with tier-based retention
3. **Semantic Memory** - Long-term facts and knowledge (permanent)

## Features

- ✅ Vector embeddings for semantic search (OpenAI text-embedding-ada-002)
- ✅ Cosine similarity-based retrieval
- ✅ Automatic fact extraction
- ✅ Named entity recognition
- ✅ Entity relationship tracking
- ✅ Tier-based retention policies
- ✅ GDPR-compliant data deletion
- ✅ SQLite-compatible (JSON-serialized vectors)

## Tier-Based Retention

| Tier           | Retention Period | Semantic Memory |
|----------------|------------------|-----------------|
| Free           | 30 days          | No              |
| Personal       | 365 days         | Yes             |
| Professional   | 730 days         | Yes             |
| Enterprise     | Unlimited        | Yes             |

## Database Schema

### Tables

- **memory_sessions** - Conversation sessions with embeddings
- **memory_facts** - Extracted facts with confidence scores
- **memory_entities** - Named entities (people, places, companies, etc.)
- **entity_relationships** - Connections between entities
- **memory_metadata** - Per-user configuration and statistics

### Indexes

Optimized for:
- Fast user lookups
- Temporal queries (recent first)
- Confidence-based filtering
- Entity mention tracking

## API Endpoints

### Store Conversation

```http
POST /api/memory/store
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "I work at Google and love programming.",
  "embedding": [0.123, 0.456, ...], // 1536-dimensional vector
  "metadata": {
    "topics": ["work", "programming"]
  }
}
```

### Retrieve Context

```http
POST /api/memory/retrieve
Authorization: Bearer <token>
Content-Type: application/json

{
  "embedding": [0.123, 0.456, ...],
  "limit": 10,
  "minSimilarity": 0.7
}
```

**Response:**
```json
{
  "memories": [
    {
      "id": "uuid",
      "content": "...",
      "relevanceScore": 0.95,
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ],
  "entities": [...],
  "facts": [...]
}
```

### Store Fact

```http
POST /api/memory/facts
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "User works at Google",
  "embedding": [0.123, ...],
  "confidence": 0.9,
  "category": "employment",
  "sourceSession": "session-uuid"
}
```

### Get Entities

```http
GET /api/memory/entities?type=company&minMentions=1
Authorization: Bearer <token>
```

**Response:**
```json
{
  "entities": [
    {
      "id": "uuid",
      "type": "company",
      "name": "Google",
      "attributes": {
        "industry": "technology"
      },
      "mentionCount": 5
    }
  ]
}
```

### Memory Statistics

```http
GET /api/memory/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
  "totalSessions": 42,
  "totalFacts": 18,
  "totalEntities": 12,
  "retentionDays": 365,
  "lastCleanup": "2024-01-01T00:00:00Z"
}
```

### Delete Session (GDPR)

```http
DELETE /api/memory/session/:sessionId
Authorization: Bearer <token>
```

### Delete All Memories (GDPR)

```http
DELETE /api/memory/all
Authorization: Bearer <token>
Content-Type: application/json

{
  "confirm": "DELETE_ALL_MEMORIES"
}
```

## Rust Integration

### Memory Module

Located in `packages/core/src/memory/`:

- `mod.rs` - Main module with MemorySystem
- `storage.rs` - Database operations
- `embeddings.rs` - OpenAI embeddings integration
- `extraction.rs` - Fact and entity extraction
- `retrieval.rs` - Context-aware memory search

### Usage Example

```rust
use xswarm::memory::{MemorySystem, MemoryConfig};

let config = MemoryConfig {
    embedding_model: "text-embedding-ada-002".to_string(),
    fact_confidence_threshold: 0.8,
    entity_recognition_enabled: true,
    retention_days: Some(365), // Personal tier
    openai_api_key: Some(api_key),
};

let memory = MemorySystem::new(config).await?;

// Store conversation
let session_id = memory.store_conversation(user_id, "I work at Google").await?;

// Retrieve context
let context = memory.retrieve_context(user_id, query, 10).await?;

// Extract facts
let facts = memory.extract_facts(user_id, session_id).await?;

// Get entities
let entities = memory.get_entities(user_id).await?;
```

## Node.js Integration

### Memory API Class

```javascript
import { createMemoryAPI } from './src/lib/memory.js';

const memoryAPI = createMemoryAPI(dbUrl, authToken);

// Store conversation
const sessionId = await memoryAPI.storeConversation(
  userId,
  "I work at Google",
  embedding,
  { topics: ['work'] }
);

// Retrieve context
const context = await memoryAPI.retrieveContext(userId, queryEmbedding, {
  limit: 10,
  minSimilarity: 0.7
});

// Store fact
const factId = await memoryAPI.storeFact(userId, "User works at Google", embedding, {
  confidence: 0.9,
  category: 'employment'
});

// Get entities
const entities = await memoryAPI.getEntities(userId);

// Cleanup old memories
const result = await memoryAPI.cleanupOldMemories(userId, 30);
```

## Vector Embeddings

### Generation

Uses OpenAI's `text-embedding-ada-002` model:
- 1536 dimensions
- Normalized vectors
- Cosine similarity for search

### Storage

Vectors are stored as JSON arrays in SQLite:
```json
"[0.123, 0.456, 0.789, ...]"
```

### Similarity Search

Cosine similarity formula:
```
similarity = (A · B) / (||A|| * ||B||)
```

Where:
- `A · B` = dot product
- `||A||`, `||B||` = vector magnitudes

## Fact Extraction

### Pattern-Based Extraction

Identifies factual statements using:
- Positive indicators: "is", "works at", "lives in", "born on"
- Negative indicators: "maybe", "perhaps", "might"
- Confidence scoring: 0.0 to 1.0

### Categories

- **employment** - Work, job, company
- **location** - Address, city, residence
- **biographical** - Age, birthday, background
- **preference** - Likes, dislikes, favorites
- **ability** - Skills, expertise, talents

## Entity Recognition

### Entity Types

- **person** - Names, individuals
- **place** - Locations, cities, venues
- **project** - Projects, repositories
- **company** - Organizations, businesses
- **concept** - Abstract ideas, topics

### Detection Methods

- Capitalized word pairs (person names)
- Company suffixes (Inc., Corp., LLC)
- Contextual patterns

## Migration

### Apply Schema

```bash
cd packages/server
node ../../scripts/migrate-db.js
```

This applies `migrations/memory.sql` to create all tables, indexes, triggers, and views.

### Test Implementation

```bash
cd packages/server
node test-memory-api.js
```

## Performance Considerations

### Indexing Strategy

- User-based partitioning via indexes
- Temporal indexes for recent queries
- Confidence indexes for fact filtering

### Caching

- Embedding cache (1000 entries)
- LRU eviction policy
- In-memory for performance

### Optimization Tips

1. **Batch embeddings** - Generate multiple at once
2. **Limit results** - Use pagination
3. **Filter by confidence** - Skip low-quality facts
4. **Cleanup regularly** - Run retention policy

## GDPR Compliance

### Right to Access

```http
GET /api/memory/stats
GET /api/memory/entities
```

### Right to Deletion

```http
DELETE /api/memory/session/:id
DELETE /api/memory/all
```

### Data Portability

Export via API endpoints with full session data.

### Retention Policies

Automatic cleanup based on tier:
- Free: 30 days
- Personal: 365 days
- Professional: 730 days
- Enterprise: Unlimited

## Future Enhancements

### Planned Features

- [ ] Native vector database (pgvector migration)
- [ ] LLM-based fact extraction
- [ ] Relationship inference
- [ ] Memory consolidation
- [ ] Importance scoring
- [ ] Cross-user privacy-preserving search
- [ ] Memory summarization
- [ ] Temporal knowledge graphs

### Performance Improvements

- [ ] Approximate nearest neighbor search (ANNOY/FAISS)
- [ ] Distributed embeddings
- [ ] Async fact extraction
- [ ] Incremental entity updates

## Troubleshooting

### Common Issues

**Embedding API errors**
```javascript
// Check API key
process.env.OPENAI_API_KEY
```

**Low similarity scores**
```javascript
// Adjust threshold
{ minSimilarity: 0.5 } // Lower = more results
```

**Memory not persisting**
```bash
# Check database connection
echo $TURSO_DATABASE_URL
```

**Retention policy not working**
```http
POST /api/memory/cleanup
```

## Testing

### Unit Tests

```bash
cargo test --package xswarm
```

### Integration Tests

```bash
cd packages/server
node test-memory-api.js
```

### Manual Testing

```bash
curl -X POST http://localhost:8787/api/memory/store \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test memory", "embedding": [...]}'
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## Support

- Documentation: `/docs/memory-system`
- Issues: GitHub Issues
- Email: support@xswarm.ai
