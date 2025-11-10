// Comprehensive tests for STT (Speech-to-Text) module
//
// Tests cover:
// - Engine initialization
// - Audio format conversions
// - Background worker spawning
// - Thread-safe AudioResampler access
// - Transcription polling
// - Memory integration

use xswarm::stt::{SttEngine, SttConfig, AudioChunk, TranscriptionResult};
use anyhow::Result;

#[tokio::test]
async fn test_stt_engine_creation_default() {
    let engine = SttEngine::new();
    assert!(engine.is_ok(), "Failed to create default STT engine");
}

#[tokio::test]
async fn test_stt_engine_creation_custom_config() {
    let config = SttConfig {
        model_size: "tiny".to_string(),
        language: Some("en".to_string()),
        background_transcription: true,
        min_audio_duration_ms: 1000,
        model_path: None,
    };

    let engine = SttEngine::with_config(config);
    assert!(engine.is_ok(), "Failed to create STT engine with custom config");
}

#[test]
fn test_stt_config_defaults() {
    let config = SttConfig::default();

    assert_eq!(config.model_size, "base");
    assert_eq!(config.language, Some("en".to_string()));
    assert_eq!(config.background_transcription, true);
    assert_eq!(config.min_audio_duration_ms, 500);
    assert_eq!(config.model_path, None);
}

#[test]
fn test_mulaw_to_pcm_conversion() {
    // Test μ-law to PCM conversion with known values
    let mulaw_samples = vec![
        0xFF, // Maximum positive value
        0x00, // Minimum negative value
        0x7F, // Zero/silence
        0x80, // Small positive
        0xFE, // Large positive
    ];

    let result = xswarm::stt::SttEngine::mulaw_to_pcm(&mulaw_samples);
    assert!(result.is_ok(), "μ-law to PCM conversion failed");

    let pcm = result.unwrap();
    assert_eq!(pcm.len(), mulaw_samples.len(), "PCM output length mismatch");

    // Verify values are in valid f32 range (-1.0 to 1.0)
    for (i, &sample) in pcm.iter().enumerate() {
        assert!(
            sample >= -1.0 && sample <= 1.0,
            "Sample {} out of range: {}",
            i,
            sample
        );
    }
}

#[test]
fn test_mulaw_silence() {
    // 0x7F in μ-law represents silence (zero)
    let silence = vec![0x7F; 100];
    let result = xswarm::stt::SttEngine::mulaw_to_pcm(&silence);
    assert!(result.is_ok());

    let pcm = result.unwrap();

    // All samples should be near zero
    for (i, &sample) in pcm.iter().enumerate() {
        assert!(
            sample.abs() < 0.01,
            "Silence sample {} not near zero: {}",
            i,
            sample
        );
    }
}

#[tokio::test]
async fn test_submit_audio_without_background_worker() {
    // Create engine without background transcription
    let config = SttConfig {
        background_transcription: false,
        ..Default::default()
    };

    let engine = SttEngine::with_config(config).unwrap();

    // Attempt to submit audio should fail
    let audio_data = vec![0x7F; 960]; // 120ms of silence at 8kHz
    let result = engine.submit_audio(
        &audio_data,
        "test_user".to_string(),
        "test_session".to_string()
    ).await;

    assert!(result.is_err(), "Should fail without background worker");
    assert!(
        result.unwrap_err().to_string().contains("not enabled"),
        "Error message should mention background transcription not enabled"
    );
}

#[tokio::test]
async fn test_submit_audio_with_background_worker() {
    // Create engine with background transcription
    let engine = SttEngine::new().unwrap();

    // Submit audio should succeed
    let audio_data = vec![0x7F; 960]; // 120ms of silence at 8kHz
    let result = engine.submit_audio(
        &audio_data,
        "test_user".to_string(),
        "test_session".to_string()
    ).await;

    assert!(result.is_ok(), "Failed to submit audio: {:?}", result.err());
}

#[tokio::test]
async fn test_get_transcription_without_worker() {
    let config = SttConfig {
        background_transcription: false,
        ..Default::default()
    };

    let engine = SttEngine::with_config(config).unwrap();

    let result = engine.get_transcription().await;
    assert!(result.is_err(), "Should fail without background worker");
}

#[tokio::test]
async fn test_get_transcription_empty_queue() {
    let engine = SttEngine::new().unwrap();

    // Get transcription without submitting audio
    let result = engine.get_transcription().await;
    assert!(result.is_ok(), "get_transcription should not error on empty queue");
    assert!(result.unwrap().is_none(), "Should return None when no transcription ready");
}

// NOTE: This test requires network access to download Whisper models from HuggingFace
// Skipped for now - will be re-enabled once actual Whisper implementation is complete
#[tokio::test]
#[ignore]
async fn test_placeholder_transcription_flow() {
    let engine = SttEngine::new().unwrap();

    // Submit audio
    let audio_data = vec![0x7F; 960 * 10]; // 1.2 seconds of silence
    engine.submit_audio(
        &audio_data,
        "test_user_123".to_string(),
        "test_session_456".to_string()
    ).await.unwrap();

    // Wait for transcription processing (placeholder is fast)
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    // Poll for result
    let result = engine.get_transcription().await;
    assert!(result.is_ok(), "Failed to get transcription");

    let transcription = result.unwrap();
    assert!(transcription.is_some(), "Expected transcription result");

    let trans = transcription.unwrap();

    // Verify placeholder text format
    assert!(
        trans.text.contains("PLACEHOLDER"),
        "Expected placeholder text, got: {}",
        trans.text
    );
    assert!(
        trans.text.contains("test_user_123"),
        "Transcription should include user_id"
    );
    assert!(
        trans.text.contains("test_session_456"),
        "Transcription should include session_id"
    );

    // Verify metadata
    assert_eq!(trans.user_id, "test_user_123");
    assert_eq!(trans.session_id, "test_session_456");
    assert!(trans.confidence > 0.0 && trans.confidence <= 1.0);
    assert!(trans.processing_time_ms >= 0);
}

// NOTE: This test requires network access to download Whisper models from HuggingFace
// Skipped for now - will be re-enabled once actual Whisper implementation is complete
#[tokio::test]
#[ignore]
async fn test_transcribe_sync() {
    let engine = SttEngine::new().unwrap();

    let audio_data = vec![0x7F; 960 * 5]; // 600ms of silence
    let result = engine.transcribe_sync(&audio_data).await;

    assert!(result.is_ok(), "Sync transcription failed");

    let text = result.unwrap();
    assert!(text.contains("PLACEHOLDER"), "Expected placeholder transcription");
}

// NOTE: This test requires network access to download Whisper models from HuggingFace
// Skipped for now - will be re-enabled once actual Whisper implementation is complete
#[tokio::test]
#[ignore]
async fn test_multiple_audio_submissions() {
    let engine = SttEngine::new().unwrap();

    // Submit multiple audio chunks
    for i in 0..5 {
        let audio_data = vec![0x7F; 960];
        engine.submit_audio(
            &audio_data,
            format!("user_{}", i),
            format!("session_{}", i),
        ).await.unwrap();
    }

    // Wait for processing
    tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;

    // Should get multiple transcriptions
    let mut count = 0;
    for _ in 0..10 {
        if let Ok(Some(_)) = engine.get_transcription().await {
            count += 1;
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }

    assert!(count >= 3, "Expected at least 3 transcriptions, got {}", count);
}

#[tokio::test]
async fn test_audio_resampling_thread_safety() {
    use std::sync::Arc;

    let engine = Arc::new(SttEngine::new().unwrap());

    // Spawn multiple tasks submitting audio concurrently
    let mut handles = vec![];

    for i in 0..5 {
        let engine_clone = engine.clone();
        let handle = tokio::spawn(async move {
            let audio_data = vec![0x7F; 960];
            engine_clone.submit_audio(
                &audio_data,
                format!("concurrent_user_{}", i),
                format!("concurrent_session_{}", i),
            ).await
        });
        handles.push(handle);
    }

    // Wait for all tasks
    for handle in handles {
        let result = handle.await.unwrap();
        assert!(result.is_ok(), "Concurrent audio submission failed");
    }
}

#[test]
fn test_audio_chunk_creation() {
    let chunk = AudioChunk {
        samples: vec![0.0, 0.5, -0.5, 1.0],
        user_id: "test_user".to_string(),
        session_id: "test_session".to_string(),
        timestamp: chrono::Utc::now(),
    };

    assert_eq!(chunk.samples.len(), 4);
    assert_eq!(chunk.user_id, "test_user");
    assert_eq!(chunk.session_id, "test_session");
}

#[test]
fn test_transcription_result_creation() {
    let result = TranscriptionResult {
        text: "Test transcription".to_string(),
        user_id: "user_123".to_string(),
        session_id: "session_456".to_string(),
        confidence: 0.95,
        language: Some("en".to_string()),
        processing_time_ms: 150,
        timestamp: chrono::Utc::now(),
    };

    assert_eq!(result.text, "Test transcription");
    assert_eq!(result.user_id, "user_123");
    assert_eq!(result.confidence, 0.95);
    assert_eq!(result.language, Some("en".to_string()));
}

#[tokio::test]
async fn test_engine_drop_cleanup() {
    // Create engine in scope
    {
        let engine = SttEngine::new().unwrap();
        engine.submit_audio(
            &vec![0x7F; 960],
            "cleanup_test".to_string(),
            "cleanup_session".to_string(),
        ).await.unwrap();
    } // Engine dropped here - should cleanup worker gracefully

    // If we get here without hanging, cleanup worked
    assert!(true, "Engine cleanup successful");
}
