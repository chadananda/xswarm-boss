// Wake Word Detector Tests
//
// Tests for the wake word detection system to ensure it compiles and works correctly
// after fixing the Send/Sync threading issues.

#[cfg(test)]
mod tests {
    // These tests verify the wake word module structure without actually
    // running audio detection (which requires hardware)

    #[tokio::test]
    async fn test_wake_word_config_creation() {
        // Import from the library
        use xswarm::wake_word::WakeWordConfig;

        let config = WakeWordConfig::default();

        assert_eq!(config.enabled, false, "Wake word should be disabled by default");
        assert_eq!(config.sensitivity, 0.5);
        assert_eq!(config.threshold, 0.5);
        assert!(!config.keywords.is_empty(), "Should have default keywords");
    }

    #[tokio::test]
    async fn test_wake_word_system_creation() {
        use xswarm::wake_word::{WakeWordConfig, WakeWordSystem};

        let config = WakeWordConfig::default();
        let system = WakeWordSystem::new(config).await;

        assert!(system.is_ok(), "WakeWordSystem should be created successfully");
    }

    #[tokio::test]
    async fn test_wake_word_system_disabled_start() {
        use xswarm::wake_word::{WakeWordConfig, WakeWordSystem};

        let config = WakeWordConfig {
            enabled: false,
            ..Default::default()
        };

        let system = WakeWordSystem::new(config).await.unwrap();
        let result = system.start_listening().await;

        assert!(result.is_ok(), "Should handle disabled wake word gracefully");
    }

    #[tokio::test]
    async fn test_wake_word_config_validation() {
        use xswarm::wake_word::config::WakeWordUserConfig;

        let config = WakeWordUserConfig::default();
        let validation = config.validate();

        assert!(validation.is_ok(), "Default config should be valid");
    }

    #[tokio::test]
    async fn test_wake_word_config_invalid_sensitivity() {
        use xswarm::wake_word::config::WakeWordUserConfig;

        let mut config = WakeWordUserConfig::default();
        config.wake_words.sensitivity = 2.0; // Invalid: > 1.0

        let validation = config.validate();
        assert!(validation.is_err(), "Invalid sensitivity should fail validation");
    }

    #[tokio::test]
    async fn test_wake_word_config_invalid_threshold() {
        use xswarm::wake_word::config::WakeWordUserConfig;

        let mut config = WakeWordUserConfig::default();
        config.wake_words.threshold = -0.5; // Invalid: < 0.0

        let validation = config.validate();
        assert!(validation.is_err(), "Invalid threshold should fail validation");
    }

    #[tokio::test]
    async fn test_wake_word_config_serialization() {
        use xswarm::wake_word::config::WakeWordUserConfig;

        let config = WakeWordUserConfig::default();
        let toml = toml::to_string_pretty(&config).unwrap();

        assert!(!toml.is_empty(), "Config should serialize to TOML");
        assert!(toml.contains("enabled"), "TOML should contain enabled field");
    }

    #[tokio::test]
    async fn test_suggestion_engine_creation() {
        use xswarm::wake_word::suggestions::SuggestionEngine;

        let (tx, _rx) = tokio::sync::mpsc::channel(10);
        let engine = SuggestionEngine::new(tx, 30);

        // Engine should be created successfully (no panic)
        drop(engine);
    }
}
