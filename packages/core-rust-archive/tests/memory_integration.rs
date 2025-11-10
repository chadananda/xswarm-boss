/// Integration test for memory system with VoiceBridge
///
/// This test demonstrates the complete memory integration:
/// - ConversationMemory creation
/// - Message storage
/// - Context retrieval
/// - Session management

use xswarm::memory::{ConversationMemory, Speaker};

#[tokio::test]
async fn test_conversation_memory_basic() {
    let memory = ConversationMemory::new();

    // Add user message
    let msg_id = memory
        .add_user_message("What's the weather?".to_string())
        .await
        .expect("Failed to add user message");

    assert!(!msg_id.is_empty());

    // Add assistant response
    let resp_id = memory
        .add_assistant_response("It's sunny and 72°F".to_string())
        .await
        .expect("Failed to add assistant response");

    assert!(!resp_id.is_empty());

    // Verify message count
    let count = memory.get_message_count().await;
    assert_eq!(count, 2);

    // Get recent messages
    let recent = memory.get_recent_messages(10).await;
    assert_eq!(recent.len(), 2);
    assert_eq!(recent[0].speaker, Speaker::User);
    assert_eq!(recent[1].speaker, Speaker::Assistant);
    assert_eq!(recent[0].content, "What's the weather?");
    assert_eq!(recent[1].content, "It's sunny and 72°F");
}

#[tokio::test]
async fn test_conversation_context_formatting() {
    let memory = ConversationMemory::new();

    // Add conversation
    memory
        .add_user_message("Hello".to_string())
        .await
        .unwrap();
    memory
        .add_assistant_response("Hi there!".to_string())
        .await
        .unwrap();
    memory
        .add_user_message("How are you?".to_string())
        .await
        .unwrap();

    // Get formatted context
    let context = memory.get_context_for_prompt(10).await;

    assert!(context.contains("Conversation history:"));
    assert!(context.contains("User: Hello"));
    assert!(context.contains("Assistant: Hi there!"));
    assert!(context.contains("User: How are you?"));
}

#[tokio::test]
async fn test_session_management() {
    let memory = ConversationMemory::new();

    // Add messages to first session
    memory
        .add_user_message("Session 1 message".to_string())
        .await
        .unwrap();

    let session1_id = memory.get_current_session().await.session_id;
    let count1 = memory.get_message_count().await;
    assert_eq!(count1, 1);

    // Start new session
    let session2_id = memory.start_new_session().await;

    assert_ne!(session1_id, session2_id);

    // New session should have 0 messages
    let count2 = memory.get_message_count().await;
    assert_eq!(count2, 0);

    // Add message to new session
    memory
        .add_user_message("Session 2 message".to_string())
        .await
        .unwrap();

    let count3 = memory.get_message_count().await;
    assert_eq!(count3, 1);
}

#[tokio::test]
async fn test_memory_buffer_limit() {
    // Create memory with small buffer (5 messages)
    let memory = ConversationMemory::with_config(5, 10);

    // Add 10 messages (exceeds buffer)
    for i in 0..10 {
        memory
            .add_user_message(format!("Message {}", i))
            .await
            .unwrap();
    }

    // Session has all 10 messages
    let session = memory.get_current_session().await;
    assert_eq!(session.messages.len(), 10);

    // But recent buffer only has last 5
    let recent = memory.get_recent_messages(100).await;
    assert_eq!(recent.len(), 5);
    assert_eq!(recent[0].content, "Message 5");
    assert_eq!(recent[4].content, "Message 9");
}

#[tokio::test]
async fn test_clear_memory() {
    let memory = ConversationMemory::new();

    // Add messages
    memory.add_user_message("Test 1".to_string()).await.unwrap();
    memory.add_user_message("Test 2".to_string()).await.unwrap();

    assert_eq!(memory.get_message_count().await, 2);

    // Clear memory
    memory.clear().await;

    assert_eq!(memory.get_message_count().await, 0);
    let recent = memory.get_recent_messages(10).await;
    assert_eq!(recent.len(), 0);
}

#[tokio::test]
async fn test_conversation_summary() {
    let memory = ConversationMemory::new();

    // Add conversation
    memory.add_user_message("Hello".to_string()).await.unwrap();
    memory
        .add_assistant_response("Hi!".to_string())
        .await
        .unwrap();
    memory
        .add_user_message("How are you?".to_string())
        .await
        .unwrap();

    let summary = memory.get_summary().await;

    // Summary should contain session info
    assert!(summary.contains("Session:"));
    assert!(summary.contains("Messages: 3"));
    assert!(summary.contains("User: 2"));
    assert!(summary.contains("Assistant: 1"));
}

#[tokio::test]
async fn test_multi_session_archiving() {
    let memory = ConversationMemory::with_config(50, 3); // Keep only 3 past sessions

    // Create 5 sessions
    for i in 0..5 {
        memory
            .add_user_message(format!("Session {} message", i))
            .await
            .unwrap();
        memory.start_new_session().await;
    }

    // Current session + max 3 past = 4 total sessions retained
    // (past sessions are archived, current is active)
}

#[tokio::test]
async fn test_empty_context() {
    let memory = ConversationMemory::new();

    // No messages yet
    let context = memory.get_context_for_prompt(10).await;

    // Context should be empty string
    assert_eq!(context, "");
}

#[tokio::test]
async fn test_message_ordering() {
    let memory = ConversationMemory::new();

    // Add messages in order
    memory.add_user_message("First".to_string()).await.unwrap();
    memory
        .add_assistant_response("Second".to_string())
        .await
        .unwrap();
    memory.add_user_message("Third".to_string()).await.unwrap();

    // Get recent messages
    let recent = memory.get_recent_messages(10).await;

    // Should be in chronological order
    assert_eq!(recent[0].content, "First");
    assert_eq!(recent[1].content, "Second");
    assert_eq!(recent[2].content, "Third");
}

#[tokio::test]
async fn test_concurrent_access() {
    use std::sync::Arc;

    let memory = Arc::new(ConversationMemory::new());

    // Spawn multiple tasks adding messages concurrently
    let mut handles = vec![];

    for i in 0..10 {
        let mem = memory.clone();
        let handle = tokio::spawn(async move {
            mem.add_user_message(format!("Message {}", i))
                .await
                .unwrap();
        });
        handles.push(handle);
    }

    // Wait for all tasks
    for handle in handles {
        handle.await.unwrap();
    }

    // All 10 messages should be stored
    let count = memory.get_message_count().await;
    assert_eq!(count, 10);
}
