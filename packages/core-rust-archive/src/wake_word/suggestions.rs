// Proactive Suggestion System
//
// This module provides intelligent proactive suggestions based on user activity,
// time of day, and configured preferences.

use anyhow::Result;
use chrono::{DateTime, Utc, Duration, Timelike};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{interval, Duration as TokioDuration};
use tracing::{debug, info};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuggestionContext {
    pub user_id: String,
    pub last_interaction: DateTime<Utc>,
    pub activity_level: ActivityLevel,
    pub preferred_suggestion_times: Vec<u8>, // Hours of day (0-23)
    pub suggestion_types: Vec<SuggestionType>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum ActivityLevel {
    Idle,
    Light,
    Active,
    Busy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SuggestionType {
    CalendarReminder,
    TaskCheck,
    EmailSummary,
    WeatherUpdate,
    NewsDigest,
    HealthCheck,
}

impl Default for SuggestionContext {
    fn default() -> Self {
        Self {
            user_id: "default".to_string(),
            last_interaction: Utc::now(),
            activity_level: ActivityLevel::Idle,
            // Suggest during typical work breaks: 10am, 2pm, 5pm
            preferred_suggestion_times: vec![10, 14, 17],
            suggestion_types: vec![
                SuggestionType::CalendarReminder,
                SuggestionType::TaskCheck,
                SuggestionType::EmailSummary,
            ],
        }
    }
}

/// Proactive suggestion engine
pub struct SuggestionEngine {
    contexts: Arc<RwLock<HashMap<String, SuggestionContext>>>,
    suggestion_sender: tokio::sync::mpsc::Sender<String>,
    interval_minutes: u32,
    is_running: Arc<RwLock<bool>>,
}

impl SuggestionEngine {
    /// Create a new suggestion engine
    pub fn new(
        suggestion_sender: tokio::sync::mpsc::Sender<String>,
        interval_minutes: u32,
    ) -> Self {
        let mut contexts = HashMap::new();
        contexts.insert("default".to_string(), SuggestionContext::default());

        Self {
            contexts: Arc::new(RwLock::new(contexts)),
            suggestion_sender,
            interval_minutes,
            is_running: Arc::new(RwLock::new(false)),
        }
    }

    /// Start the suggestion loop
    pub async fn start_suggestion_loop(&self) -> Result<()> {
        if *self.is_running.read().await {
            debug!("Suggestion loop already running");
            return Ok(());
        }

        *self.is_running.write().await = true;

        let contexts = self.contexts.clone();
        let sender = self.suggestion_sender.clone();
        let interval_minutes = self.interval_minutes;
        let is_running = self.is_running.clone();

        tokio::spawn(async move {
            let mut timer = interval(TokioDuration::from_secs(interval_minutes as u64 * 60));

            info!("Suggestion loop started (interval: {} minutes)", interval_minutes);

            loop {
                timer.tick().await;

                if !*is_running.read().await {
                    info!("Suggestion loop stopped");
                    break;
                }

                let contexts_guard = contexts.read().await;
                for (user_id, context) in contexts_guard.iter() {
                    if Self::should_suggest(context).await {
                        let suggestion = Self::generate_suggestion(context).await;
                        debug!("Generated suggestion for {}: {}", user_id, suggestion);

                        if let Err(e) = sender.try_send(suggestion) {
                            debug!("Failed to send suggestion: {}", e);
                        }
                    }
                }
            }
        });

        Ok(())
    }

    /// Stop the suggestion loop
    pub async fn stop(&self) {
        *self.is_running.write().await = false;
    }

    /// Check if a suggestion should be made for this context
    async fn should_suggest(context: &SuggestionContext) -> bool {
        let now = Utc::now();
        let time_since_interaction = now - context.last_interaction;

        // Don't suggest if user was active recently (within 15 minutes)
        if time_since_interaction < Duration::minutes(15) {
            return false;
        }

        // Don't suggest if user is busy
        if context.activity_level == ActivityLevel::Busy {
            return false;
        }

        // Check if current hour is in preferred times
        let current_hour = now.hour() as u8;
        if !context.preferred_suggestion_times.is_empty()
            && !context.preferred_suggestion_times.contains(&current_hour)
        {
            return false;
        }

        // Only suggest during reasonable hours (8am - 10pm)
        if current_hour < 8 || current_hour >= 22 {
            return false;
        }

        // Consider activity level
        matches!(
            context.activity_level,
            ActivityLevel::Idle | ActivityLevel::Light
        )
    }

    /// Generate a contextual suggestion
    async fn generate_suggestion(context: &SuggestionContext) -> String {
        use rand::seq::SliceRandom;

        let now = Utc::now();
        let hour = now.hour();

        // Time-based suggestions
        let time_suggestions = if hour < 12 {
            vec![
                "Good morning! Want me to review your calendar for today?",
                "Morning! Should I check for any urgent emails?",
                "Hey! Ready to plan your day? I can help prioritize your tasks.",
            ]
        } else if hour < 18 {
            vec![
                "Need a quick productivity check? I can review your progress.",
                "Want me to summarize what's left on your task list?",
                "How about a brief update on your pending items?",
            ]
        } else {
            vec![
                "Winding down? Want a summary of what you accomplished today?",
                "Evening check-in: should I review tomorrow's calendar?",
                "End of day - need help planning for tomorrow?",
            ]
        };

        // Activity-based suggestions
        let activity_suggestions = match context.activity_level {
            ActivityLevel::Idle => vec![
                "You've been idle for a bit. Need help getting started on something?",
                "Ready to tackle a task? I can suggest what to work on next.",
            ],
            ActivityLevel::Light => vec![
                "Taking a break? Want a quick update on your priorities?",
                "Got a moment? I can give you a status update.",
            ],
            _ => vec![],
        };

        // Combine all suggestions
        let mut all_suggestions = time_suggestions;
        all_suggestions.extend(activity_suggestions);

        all_suggestions
            .choose(&mut rand::thread_rng())
            .unwrap_or(&"Need anything?")
            .to_string()
    }

    /// Update user activity level
    pub async fn update_user_activity(&self, user_id: &str, activity: ActivityLevel) {
        let mut contexts = self.contexts.write().await;

        contexts
            .entry(user_id.to_string())
            .and_modify(|context| {
                context.last_interaction = Utc::now();
                context.activity_level = activity;
            })
            .or_insert_with(|| {
                let mut context = SuggestionContext::default();
                context.user_id = user_id.to_string();
                context.activity_level = activity;
                context
            });

        debug!("Updated activity for {}: {:?}", user_id, activity);
    }

    /// Add or update suggestion context for a user
    pub async fn set_user_context(&self, context: SuggestionContext) {
        let mut contexts = self.contexts.write().await;
        contexts.insert(context.user_id.clone(), context);
    }

    /// Get current context for a user
    pub async fn get_user_context(&self, user_id: &str) -> Option<SuggestionContext> {
        let contexts = self.contexts.read().await;
        contexts.get(user_id).cloned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_suggestion_engine_creation() {
        let (tx, _rx) = tokio::sync::mpsc::channel(10);
        let engine = SuggestionEngine::new(tx, 30);

        assert!(!*engine.is_running.read().await);
    }

    #[tokio::test]
    async fn test_activity_update() {
        let (tx, _rx) = tokio::sync::mpsc::channel(10);
        let engine = SuggestionEngine::new(tx, 30);

        engine
            .update_user_activity("test_user", ActivityLevel::Active)
            .await;

        let context = engine.get_user_context("test_user").await;
        assert!(context.is_some());
        assert_eq!(context.unwrap().activity_level, ActivityLevel::Active);
    }

    #[tokio::test]
    async fn test_should_not_suggest_when_busy() {
        let mut context = SuggestionContext::default();
        context.activity_level = ActivityLevel::Busy;

        assert!(!SuggestionEngine::should_suggest(&context).await);
    }

    #[tokio::test]
    async fn test_should_not_suggest_recently_active() {
        let mut context = SuggestionContext::default();
        context.last_interaction = Utc::now(); // Just now

        assert!(!SuggestionEngine::should_suggest(&context).await);
    }
}
