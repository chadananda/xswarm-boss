# Memory System Quick Reference

## Quick Start

### 1. Basic Conversation Memory

```rust
use xswarm::memory::ConversationMemory;

// Create memory
let memory = ConversationMemory::new();

// Add messages
memory.add_user_message("Hello".to_string()).await?;
memory.add_assistant_response("Hi there!".to_string()).await?;

// Get recent context
let context = memory.get_context_for_prompt(5).await;
```

### 2. VoiceBridge Integration

```rust
use xswarm::voice::{VoiceBridge, VoiceConfig};

// Memory is automatically created with VoiceBridge
let bridge = VoiceBridge::new(VoiceConfig::default()).await?;

// Initialize conversation with personality
bridge.inject_personality_context().await?;

// User transcriptions are automatically stored
// (happens in MOSHI processing)

// Inject context periodically
bridge.inject_conversation_context(5).await?;

// Access memory directly
let memory = bridge.get_conversation_memory().await;
let recent = memory.get_recent_messages(10).await;
```

## Common Operations

### Add Messages

```rust
// User message
let msg_id = memory.add_user_message("What's the weather?".to_string()).await?;

// Assistant response
let msg_id = memory.add_assistant_response("It's sunny".to_string()).await?;
```

### Retrieve Context

```rust
// Get last N messages
let messages = memory.get_recent_messages(5).await;

// Get formatted context for MOSHI
let context = memory.get_context_for_prompt(5).await;
// Returns:
// "Conversation history:
//  User: What's the weather?
//  Assistant: It's sunny
//  ..."
```

### Session Management

```rust
// Get current session info
let session = memory.get_current_session().await;
println!("Session: {}", session.session_id);
println!("Messages: {}", session.messages.len());

// Start new session (archives current)
let new_session_id = memory.start_new_session().await;

// Clear all memory
memory.clear().await;
```

### Statistics

```rust
// Message count
let count = memory.get_message_count().await;

// Summary
let summary = memory.get_summary().await;
// Returns: "Session: abc-123 | Duration: 5m | Messages: 12 (User: 6, Assistant: 6)"
```

## Configuration

### Custom Buffer Sizes

```rust
// Default: 50 recent messages, 10 past sessions
let memory = ConversationMemory::new();

// Custom: 100 recent messages, 20 past sessions
let memory = ConversationMemory::with_config(100, 20);
```

## Integration Patterns

### Pattern 1: Start of Conversation

```rust
let bridge = VoiceBridge::new(config).await?;

// Initialize personality
bridge.inject_personality_context().await?;

// Optionally inject previous session context
bridge.inject_conversation_context(3).await?;
```

### Pattern 2: During Conversation

```rust
// Every N messages, refresh context
let count = bridge.get_conversation_memory()
    .await
    .get_message_count()
    .await;

if count % 10 == 0 {
    bridge.inject_conversation_context(5).await?;
}
```

### Pattern 3: Long Conversations

```rust
// Start new session after 50 messages
let count = bridge.get_conversation_memory()
    .await
    .get_message_count()
    .await;

if count >= 50 {
    let new_session = bridge.start_new_conversation_session().await;
    println!("Started new session: {}", new_session);
}
```

## Message Structure

```rust
pub struct ConversationMessage {
    pub id: String,              // UUID
    pub timestamp: DateTime<Utc>, // When message was created
    pub speaker: Speaker,         // User | Assistant
    pub content: String,          // Message text
    pub importance: f32,          // 0.0-1.0 (for future prioritization)
}
```

## Session Structure

```rust
pub struct ConversationSession {
    pub session_id: String,                      // UUID
    pub start_time: DateTime<Utc>,              // Session start
    pub end_time: Option<DateTime<Utc>>,        // Session end (if archived)
    pub messages: Vec<ConversationMessage>,     // All messages
    pub summary: Option<String>,                // Optional summary
}
```

## Error Handling

```rust
// All methods return Result<T, anyhow::Error>
match memory.add_user_message("Hello".to_string()).await {
    Ok(msg_id) => println!("Message stored: {}", msg_id),
    Err(e) => eprintln!("Failed to store message: {}", e),
}
```

## Performance Tips

1. **Buffer Size**: Keep `max_recent_messages` under 100 for best performance
2. **Context Injection**: Don't inject context on every message (every 5-10 is fine)
3. **Session Management**: Archive sessions after 50-100 messages
4. **Memory Cleanup**: Call `clear()` when starting completely new conversations

## Testing

```bash
# Run all memory tests
cargo test memory

# Run specific tests
cargo test memory::conversation
cargo test memory::storage
```

## Troubleshooting

### Messages Not Being Stored

- Check that `add_user_message()` is being called
- Verify no errors in logs
- Check message count: `memory.get_message_count().await`

### Context Not Appearing in MOSHI

- Ensure `inject_conversation_context()` is called
- Check suggestion queue has items
- Verify personality context is set first

### Memory Growing Too Large

- Reduce `max_recent_messages` in config
- Start new sessions more frequently
- Clear memory when appropriate

## Advanced Usage

### Custom Message Importance

```rust
// Manually create high-importance message
let message = ConversationMessage {
    id: uuid::Uuid::new_v4().to_string(),
    timestamp: chrono::Utc::now(),
    speaker: Speaker::User,
    content: "This is important!".to_string(),
    importance: 1.0, // Maximum importance
};
```

### Selective Context Retrieval

```rust
// Get only recent messages
let recent = memory.get_recent_messages(5).await;

// Filter by speaker
let user_messages: Vec<_> = recent
    .iter()
    .filter(|m| m.speaker == Speaker::User)
    .collect();
```

### Session Archiving

```rust
// Archive current session manually
let current = memory.get_current_session().await;
let session_copy = current.clone();

// Store session_copy to database, file, etc.
save_to_database(session_copy).await?;

// Start fresh
memory.start_new_session().await;
```

## Complete Example

```rust
use xswarm::voice::{VoiceBridge, VoiceConfig};
use xswarm::memory::Speaker;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Create voice bridge (includes memory)
    let bridge = VoiceBridge::new(VoiceConfig::default()).await?;

    // Initialize conversation
    bridge.inject_personality_context().await?;

    // Simulate conversation
    bridge.add_user_message("What's the time?".to_string()).await?;
    bridge.add_assistant_response("It's 3:30 PM".to_string()).await?;

    // Get context
    let context = bridge.get_conversation_context(5).await;
    println!("Context:\n{}", context);

    // Inject context for continuity
    bridge.inject_conversation_context(3).await?;

    // Access memory directly
    let memory = bridge.get_conversation_memory().await;
    let summary = memory.get_summary().await;
    println!("Summary: {}", summary);

    // Start new session when needed
    if memory.get_message_count().await > 50 {
        let new_session = bridge.start_new_conversation_session().await;
        println!("Started new session: {}", new_session);
    }

    Ok(())
}
```

## Related Documentation

- Full implementation details: `MEMORY_INTEGRATION_COMPLETE.md`
- Memory system architecture: `src/memory/mod.rs`
- Conversation tracking: `src/memory/conversation.rs`
- VoiceBridge integration: `src/voice.rs`
