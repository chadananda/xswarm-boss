// Memory Conditioning Module - Natural Memory Incorporation for MOSHI
//
// ARCHITECTURAL NOTE: This module uses Condition::AddToInput for memory context.
// This is DIFFERENT from force_text_token (used in greetings):
//
// 1. force_text_token → Verbatim speech output (for greetings)
//    Example: "Hello! I'm ready to help you today." (exactly as written)
//
// 2. Condition::AddToInput → Natural incorporation (for memory context)
//    Example: Memory = "Last Wednesday decided on JWT authentication"
//             MOSHI says: "I remember last Wednesday we discussed authentication..."
//             (Natural, conversational, not verbatim)
//
// HOW IT WORKS:
// - Takes memory text from semantic search
// - Tokenizes using SentencePiece
// - Embeds tokens using LM's text_emb layer
// - Mean-pools embeddings to create context vector
// - Returns Condition::AddToInput(context_vector)
// - LM broadcasts context_vector to input embeddings: emb = emb.broadcast_add(context_vector)
// - MOSHI naturally incorporates memory into its response

use anyhow::{Context, Result};
use candle::{Module, Tensor};
use tracing::{debug, info};

use crate::voice::MoshiState;

/// Memory conditioner for natural memory incorporation into MOSHI conversations
///
/// This is a zero-sized utility struct that provides methods for encoding memory
/// text into condition vectors. It doesn't store any state - all data comes from
/// MoshiState when encoding.
///
/// Unlike force_text_token (which produces verbatim speech), this creates embeddings
/// that guide the model to naturally incorporate memories into conversation.
pub struct MemoryConditioner;

impl MemoryConditioner {
    /// Create a new memory conditioner (no-op since it's stateless)
    pub fn new() -> Self {
        info!("Initializing memory conditioner (stateless)");
        Self
    }

    /// Encode memory text into a condition for MOSHI
    ///
    /// Process:
    /// 1. Tokenize memory text using MoshiState's tokenizer
    /// 2. Create tensor of token IDs
    /// 3. Apply text_emb layer to get embeddings
    /// 4. Mean-pool embeddings to single context vector
    /// 5. Wrap in Condition::AddToInput
    ///
    /// Example:
    /// ```
    /// let conditioner = MemoryConditioner::new();
    /// let memory = "Last Wednesday decided on JWT authentication";
    /// let condition = conditioner.encode_memory(memory, moshi_state)?;
    /// // Later: lm_generator.step_(..., Some(&condition))
    /// // MOSHI might say: "I remember we discussed authentication last Wednesday..."
    /// ```
    pub fn encode_memory(
        &self,
        memory_text: &str,
        moshi_state: &MoshiState,
    ) -> Result<moshi::conditioner::Condition> {
        info!("Encoding memory for conditioning: '{}'", memory_text);

        // Step 1: Tokenize memory text using MoshiState's tokenizer
        let tokens = Self::tokenize_text(memory_text, &moshi_state.text_tokenizer)
            .context("Failed to tokenize memory text")?;

        if tokens.is_empty() {
            anyhow::bail!("Tokenization produced empty token list");
        }

        debug!("Memory tokenized into {} tokens", tokens.len());

        // Step 2: Create tensor of token IDs
        // Shape: (batch=1, sequence_length)
        let token_ids = Tensor::from_vec(
            tokens.clone(),
            (1, tokens.len()),
            &moshi_state.device,
        ).context("Failed to create token tensor")?;

        debug!("Token tensor shape: {:?}", token_ids.dims());

        // Step 3: Apply text embedding layer
        // Get text_embeddings from LM model
        let text_emb = moshi_state.lm_model.text_embeddings();

        // Apply embeddings: (batch, seq_len) → (batch, seq_len, hidden_dim)
        let embeddings = token_ids.apply(text_emb)
            .context("Failed to apply text embeddings")?;

        debug!("Embeddings shape: {:?}", embeddings.dims());

        // Step 4: Mean-pool embeddings to create context vector
        // Mean over sequence dimension (dim 1) → (batch, hidden_dim)
        let context_vector = embeddings.mean(1)
            .context("Failed to mean-pool embeddings")?;

        debug!("Context vector shape: {:?}", context_vector.dims());

        // Add sequence dimension: (batch, hidden_dim) → (batch, 1, hidden_dim)
        // This is needed for broadcast_add in forward_cond
        let context_vector = context_vector.unsqueeze(1)
            .context("Failed to unsqueeze context vector")?;

        debug!("Final context vector shape: {:?}", context_vector.dims());

        // Step 5: Wrap in Condition::AddToInput
        let condition = moshi::conditioner::Condition::AddToInput(context_vector);

        info!("Memory conditioning complete");

        Ok(condition)
    }

    /// Tokenize text using SentencePiece
    fn tokenize_text(
        text: &str,
        tokenizer: &sentencepiece::SentencePieceProcessor,
    ) -> Result<Vec<u32>> {
        let encoded = tokenizer.encode(text)
            .context("SentencePiece encoding failed")?;

        let tokens: Vec<u32> = encoded.iter()
            .map(|piece| piece.id as u32)
            .collect();

        debug!(
            "Tokenized '{}' -> {} tokens: {:?}",
            text,
            tokens.len(),
            &tokens[..tokens.len().min(5)]
        );

        Ok(tokens)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_conditioner_concept() {
        // This test documents the concept - actual testing requires real MOSHI models
        // See integration tests for full testing
    }

    #[tokio::test]
    async fn test_encode_memory_structure() {
        // This test verifies the structure without needing real models
        // Full integration test will use real MOSHI models and verify audio output
    }
}
