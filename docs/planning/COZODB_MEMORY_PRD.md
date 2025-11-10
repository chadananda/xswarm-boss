# Product Requirements Document (PRD): CozoDB Integration for AI Personal Assistant in Rust

## Status: PLANNED (Post-Audio Fix Implementation)

**Priority**: High - Will replace current libsql memory implementation after MOSHI audio issues are resolved.

## Objective

Integrate CozoDB as the core long-term memory store for an offline, personalized AI assistant in Rust. The solution should provide robust, durable storage and retrieval of conversational logs, summaries, and entity relationships, enabling "subconscious" memory injection into context-limited Moshi LLM runs.[9]

***

## System Architecture Overview

- **Main Interface:** Moshi (conversational LLM, limited context window)
- **Memory Store:** CozoDB (embedded, no external server required)
- **Retrieval Agent:** Local LLM, background Rust thread for memory search/summarization

### Workflow

1. Conversation Logging: Every Moshi exchange is recorded (with metadata) as nodes and edges in CozoDB.
2. Memory Summarization: At session end or on-demand, a background Rust thread triggers a local LLM to summarize recent exchanges or extract key events/entities.
3. Memory Injection: When new input is received, the LLM agent queries CozoDB (vector, FTS, graph search) for relevant facts/summaries to inject into the next Moshi context window.

***

## Detailed Feature Requirements

### 1. Schema Design

- Relations:
    - message{id, sender, content, timestamp, embedding<F32;N>}
    - summary{id, content, timestamp, embedding<F32;N>}
    - entity{id, type, label, embedding<F32;N>}
    - relation{id, subject_id, predicate, object_id, weight}

- Indices:
    - HNSW vector indices for semantic similarity search (on content embeddings).
    - Full-text search (FTS) indices on content fields for keyword/text queries.
    - Graph edges (relations) for contextual linking and entity tracking.

- Example Usage:
    - Save each message after preprocessing (e.g., generating vector embedding).
    - After session/periodic summary, append new summary node/edge.
    - Track core entities and update their links as context changes.[9]

### 2. Memory Retrieval API

- Expose Rust functions for searching CozoDB via:
    - Vector Search: Most semantically similar memories/facts.
    - FTS: Direct keyword search, ranking by relevance score.
    - Graph Traversal: Follow related entities/events, context expansion.
    - Hybrid queries for best recall.[9]

- Queries should support:
    - Recency/relevancy ranking.
    - Filtering by session/user/task.
    - Batch/streamed result output for low-latency context injection.

### 3. Subconscious Memory Pipeline

- Background thread (Rust): Periodically or on user/query demand, run LLM agent to:
    - Summarize past session, extract core events/entities.
    - Search CozoDB for matching/relevant prior memories.
    - Select top-N items for Moshi injection.
    - Prepare/format injection buffer for Moshi (context string, JSON, etc.).

### 4. LLM Summarization Integration

- Use locally run LLM (via HuggingFace, llama.cpp, etc.) to:
    - Summarize batch conversations.
    - Extract high-level facts, events, or observations.
    - Store results as summary nodes/edges in CozoDB.
    - Optionally, compute embeddings for new summary chunks.

### 5. Rust Integration

- Add cozodb crate as project dependency; configure CozoDB as embedded, local storage.
- Schema migration routines for initial/upgrade deployment.
- Direct API calls for inserts/searches (vector, FTS, Datalog graph queries).
- Concurrency-safe writes using CozoDB's transactional features.
- Cross-platform bytecode serialization for LLM memory retrieval.

### 6. Performance and Reliability

- Memory flushing and compaction for long-running systems.
- Efficient disk/memory usage on desktop/edge environments.[9]
- Robust error and exception handling for durable personal memory.

***

## How CozoDB Works in This Design

- Stores conversational logs, summaries, and knowledge graphs (all as relations with rich metadata).
- Enables both FTS and vector search for quick memory retrieval (injecting relevant content into Moshi's context).
- Graph traversal enables "subconscious" reasoning steps (the LLM agent can explore related concepts/events via Datalog).
- Full transactional support and concurrency benefits for multiple threads/agents.
- Embedding and proximity-based graph algorithms empower agentic reasoning (beyond simple retrieval).[9]

***

## Example Rust API Integration

```rust
use cozodb::{Database, Relation, VectorIndex, FTSIndex};

// Open database
let db = Database::open("memory.db")?;

// Insert a new message, with embedding
db.relation("message").put(&message_fields)?;

// Insert or update entity relations
db.relation("entity").put(&entity_fields)?;
db.relation("relation").put(&relation_fields)?;

// Search messages by vector similarity
db.vector_search("message:mem_idx", input_embedding, k_top)?;

// Perform full-text search
db.fts_search("message:fts_idx", "query terms")?;

// Traverse memory graph for related context
db.datalog_query(
    "?[label] := *relation{subject_id: $entity_id, predicate, object_id: oid}, \
     *entity{id: oid, label} :limit 5",
    params
)?;
```

***

## Advantages Over Current libsql Implementation

1. **Graph-Based Reasoning**: Entity relationships and context traversal via Datalog
2. **Vector + FTS + Graph**: Hybrid search capabilities in one system
3. **Embedded**: No external server, easier deployment
4. **HNSW Indices**: Faster semantic similarity search
5. **Transactional**: Better concurrency support for background agents
6. **Agentic Memory**: LLM can explore related concepts, not just keyword/vector match

***

## Implementation Plan

### Phase 1: Schema Design & Migration
- Design CozoDB relations (message, summary, entity, relation)
- Create migration from current libsql memory.db
- Set up HNSW vector indices
- Configure FTS indices

### Phase 2: Core Memory API
- Implement Rust wrapper for CozoDB operations
- Create memory storage functions (insert message, entity, relation)
- Build retrieval functions (vector search, FTS, graph traversal)
- Add embedding generation pipeline

### Phase 3: Subconscious Memory Pipeline
- Background thread for memory summarization
- LLM agent for fact extraction
- Context injection logic for Moshi
- Recency/relevancy ranking

### Phase 4: Testing & Optimization
- Performance benchmarks
- Memory usage optimization
- Concurrency testing
- Migration validation

***

## Dependencies

```toml
[dependencies]
cozo = "0.7"  # Latest CozoDB Rust crate
```

***

## Migration from libsql

Current memory system uses libsql with tables:
- conversations
- memories
- semantic_memory

Migration strategy:
1. Export existing data from libsql
2. Transform to CozoDB relations
3. Generate embeddings for existing content
4. Populate entity/relation graphs
5. Create vector/FTS indices
6. Validate data integrity

***

## References

- CozoDB documentation: vector search, FTS, and graph modeling features.[9]
- Embedded operational model for Rust, no external server required.[9]
- Datalog queries for memory/event/entity reasoning.[9]
- arXiv paper: https://arxiv.org/abs/2505.23735

***

## Timeline

**Start**: After MOSHI audio issues are resolved
**Duration**: 2-3 weeks estimated
**Priority**: High - Core feature for personalized AI assistant

---

**Last Updated**: 2025-11-05
**Status**: Awaiting audio fix completion
**Author**: Product Requirements
