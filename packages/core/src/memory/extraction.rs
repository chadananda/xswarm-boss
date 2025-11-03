/// Fact and Entity Extraction
///
/// Extracts structured facts and named entities from natural language text.
/// Uses simple pattern matching and rule-based extraction for now.
/// Can be upgraded to use LLM-based extraction later.

use anyhow::Result;
use chrono::Utc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::{Entity, EntityType, Fact};

/// Fact extractor for natural language processing
pub struct FactExtractor {
    confidence_threshold: f32,
    entity_recognition_enabled: bool,
}

/// Extracted fact candidate before validation
#[derive(Debug, Clone)]
struct FactCandidate {
    text: String,
    category: Option<String>,
    confidence: f32,
}

/// Named entity candidate
#[derive(Debug, Clone)]
struct EntityCandidate {
    name: String,
    entity_type: EntityType,
    confidence: f32,
    attributes: serde_json::Value,
}

impl FactExtractor {
    /// Create a new fact extractor
    pub fn new(confidence_threshold: f32, entity_recognition_enabled: bool) -> Self {
        Self {
            confidence_threshold,
            entity_recognition_enabled,
        }
    }

    /// Extract facts from text
    pub async fn extract_facts(&self, text: &str) -> Result<Vec<Fact>> {
        let candidates = self.identify_fact_candidates(text);

        let facts: Vec<Fact> = candidates
            .into_iter()
            .filter(|c| c.confidence >= self.confidence_threshold)
            .map(|c| Fact {
                id: Uuid::new_v4(),
                user_id: Uuid::nil(), // Will be set by caller
                fact_text: c.text,
                category: c.category,
                confidence: c.confidence,
                source_session: None,
                created_at: Utc::now(),
            })
            .collect();

        tracing::info!("Extracted {} facts from text", facts.len());

        Ok(facts)
    }

    /// Extract entities from text
    pub async fn extract_entities(&self, text: &str) -> Result<Vec<Entity>> {
        if !self.entity_recognition_enabled {
            return Ok(vec![]);
        }

        let candidates = self.identify_entity_candidates(text);

        let entities: Vec<Entity> = candidates
            .into_iter()
            .filter(|c| c.confidence >= self.confidence_threshold)
            .map(|c| Entity {
                id: Uuid::new_v4(),
                user_id: Uuid::nil(), // Will be set by caller
                entity_type: c.entity_type,
                name: c.name,
                attributes: c.attributes,
                mention_count: 1,
                first_mentioned: Utc::now(),
                last_mentioned: Utc::now(),
            })
            .collect();

        tracing::info!("Extracted {} entities from text", entities.len());

        Ok(entities)
    }

    /// Identify fact candidates using pattern matching
    fn identify_fact_candidates(&self, text: &str) -> Vec<FactCandidate> {
        let mut candidates = Vec::new();

        // Split into sentences
        let sentences: Vec<&str> = text
            .split(|c| c == '.' || c == '!' || c == '?')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();

        for sentence in sentences {
            // Look for factual statements with high confidence indicators
            let confidence = self.assess_fact_confidence(sentence);
            let category = self.categorize_fact(sentence);

            if confidence > 0.5 {
                candidates.push(FactCandidate {
                    text: sentence.to_string(),
                    category,
                    confidence,
                });
            }
        }

        candidates
    }

    /// Assess confidence level of a fact
    fn assess_fact_confidence(&self, text: &str) -> f32 {
        let mut confidence: f32 = 0.5; // Base confidence

        // Positive indicators
        let positive_patterns = [
            ("is ", 0.2),
            ("has ", 0.2),
            ("works at ", 0.3),
            ("lives in ", 0.3),
            ("born on ", 0.4),
            ("graduated from ", 0.3),
            ("married to ", 0.3),
            ("manages ", 0.3),
            ("created ", 0.2),
        ];

        for (pattern, boost) in positive_patterns {
            if text.to_lowercase().contains(pattern) {
                confidence += boost;
            }
        }

        // Negative indicators (reduce confidence)
        let negative_patterns = ["maybe", "perhaps", "might", "could", "possibly"];
        for pattern in negative_patterns {
            if text.to_lowercase().contains(pattern) {
                confidence -= 0.2;
            }
        }

        confidence.max(0.0).min(1.0)
    }

    /// Categorize a fact by domain
    fn categorize_fact(&self, text: &str) -> Option<String> {
        let lower = text.to_lowercase();

        if lower.contains("work") || lower.contains("job") || lower.contains("company") {
            Some("employment".to_string())
        } else if lower.contains("live") || lower.contains("address") || lower.contains("city") {
            Some("location".to_string())
        } else if lower.contains("born") || lower.contains("age") || lower.contains("birthday") {
            Some("biographical".to_string())
        } else if lower.contains("like") || lower.contains("prefer") || lower.contains("love") {
            Some("preference".to_string())
        } else if lower.contains("skill") || lower.contains("expert") || lower.contains("good at") {
            Some("ability".to_string())
        } else {
            None
        }
    }

    /// Identify entity candidates using pattern matching
    fn identify_entity_candidates(&self, text: &str) -> Vec<EntityCandidate> {
        let mut candidates = Vec::new();

        // Simple name detection (capitalized words)
        let words: Vec<&str> = text.split_whitespace().collect();

        for window in words.windows(2) {
            if let [first, second] = window {
                // Check if both words are capitalized (potential person name)
                if self.is_capitalized(first) && self.is_capitalized(second) {
                    let name = format!("{} {}", first, second);
                    candidates.push(EntityCandidate {
                        name,
                        entity_type: EntityType::Person,
                        confidence: 0.7,
                        attributes: serde_json::json!({}),
                    });
                }
            }
        }

        // Company detection (Inc., Corp., LLC, etc.)
        let company_suffixes = ["Inc.", "Corp.", "LLC", "Ltd.", "Company"];
        for suffix in company_suffixes {
            if let Some(pos) = text.find(suffix) {
                // Extract company name (up to 5 words before suffix)
                let before = &text[..pos];
                let words: Vec<&str> = before.split_whitespace().rev().take(5).collect();
                let company_name = words
                    .into_iter()
                    .rev()
                    .collect::<Vec<_>>()
                    .join(" ") + " " + suffix;

                candidates.push(EntityCandidate {
                    name: company_name.trim().to_string(),
                    entity_type: EntityType::Company,
                    confidence: 0.9,
                    attributes: serde_json::json!({}),
                });
            }
        }

        candidates
    }

    /// Check if a word is capitalized
    fn is_capitalized(&self, word: &str) -> bool {
        word.chars().next().map_or(false, |c| c.is_uppercase())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_extract_facts() {
        let extractor = FactExtractor::new(0.5, true);
        let text = "John works at Google. He lives in San Francisco. Maybe he likes coffee.";

        let facts = extractor.extract_facts(text).await.unwrap();
        assert!(facts.len() >= 2); // Should extract at least 2 high-confidence facts
    }

    #[test]
    fn test_assess_fact_confidence() {
        let extractor = FactExtractor::new(0.8, true);

        // High confidence
        let high = extractor.assess_fact_confidence("John works at Google");
        assert!(high > 0.7);

        // Low confidence
        let low = extractor.assess_fact_confidence("Maybe John could work somewhere");
        assert!(low < 0.5);
    }

    #[test]
    fn test_categorize_fact() {
        let extractor = FactExtractor::new(0.8, true);

        assert_eq!(
            extractor.categorize_fact("John works at Google"),
            Some("employment".to_string())
        );

        assert_eq!(
            extractor.categorize_fact("She lives in Paris"),
            Some("location".to_string())
        );

        assert_eq!(
            extractor.categorize_fact("He was born in 1990"),
            Some("biographical".to_string())
        );
    }

    #[tokio::test]
    async fn test_extract_entities() {
        let extractor = FactExtractor::new(0.5, true);
        let text = "John Smith works at Google Inc. and lives in San Francisco.";

        let entities = extractor.extract_entities(text).await.unwrap();
        assert!(!entities.is_empty());
    }

    #[test]
    fn test_is_capitalized() {
        let extractor = FactExtractor::new(0.8, true);

        assert!(extractor.is_capitalized("John"));
        assert!(extractor.is_capitalized("Smith"));
        assert!(!extractor.is_capitalized("works"));
        assert!(!extractor.is_capitalized("at"));
    }
}
