/// Example: Integrating Persona System with Voice Bridge
///
/// This example demonstrates how to use the persona system
/// to create personality-aware voice responses in real-time.

use anyhow::Result;
use uuid::Uuid;
use xswarm::personas::{
    PersonaClient, CreatePersonaRequest, PersonalityTraits,
    ResponseStyle, VerbosityLevel, ToneStyle,
    build_persona_prompt, apply_persona_style,
};

#[tokio::main]
async fn main() -> Result<()> {
    // Configuration
    let api_base_url = std::env::var("XSWARM_API_URL")
        .unwrap_or_else(|_| "http://localhost:8787".to_string());
    let user_id = Uuid::parse_str(&std::env::var("USER_ID")?)?;
    let auth_token = std::env::var("AUTH_TOKEN")?;

    println!("🎭 Persona Voice Integration Example\n");

    // 1. Create PersonaClient
    let client = PersonaClient::new(api_base_url, user_id, auth_token);

    // 2. Create a professional assistant persona
    println!("Creating Jarvis persona...");
    let request = CreatePersonaRequest {
        name: "Jarvis".to_string(),
        description: Some("A sophisticated AI butler with British refinement".to_string()),
        personality_traits: Some(PersonalityTraits {
            extraversion: 0.6,
            agreeableness: 0.8,
            conscientiousness: 0.9,
            neuroticism: 0.2,
            openness: 0.7,
            formality: 0.9,
            enthusiasm: 0.5,
        }),
        response_style: Some(ResponseStyle {
            verbosity: VerbosityLevel::Balanced,
            tone: ToneStyle::Professional,
            humor_level: 0.3,
            technical_depth: 0.7,
            empathy_level: 0.6,
            proactivity: 0.8,
        }),
        expertise_areas: Some(vec![
            "technology".to_string(),
            "scheduling".to_string(),
            "productivity".to_string(),
        ]),
    };

    let jarvis = client.create_persona(request).await?;
    println!("✅ Created: {}", jarvis.name);
    println!("   Formality: {:.1}", jarvis.personality_traits.formality);
    println!("   Tone: {:?}\n", jarvis.response_style.tone);

    // 3. Activate the persona
    println!("Activating Jarvis...");
    let active_jarvis = client.activate_persona(jarvis.id).await?;
    println!("✅ Active: {}\n", active_jarvis.name);

    // 4. Simulate voice interaction
    println!("=== Voice Interaction Simulation ===\n");

    let user_message = "What's on my calendar today?";
    println!("User: {}", user_message);

    // 5. Build persona-aware prompt
    let prompt = build_persona_prompt(&active_jarvis, user_message);
    println!("\n📝 Generated Prompt:");
    println!("{}\n", prompt);

    // 6. Simulate AI response (in production, this would come from MOSHI or Claude)
    let ai_response = simulate_ai_response(&prompt);
    println!("🤖 Raw AI Response:");
    println!("{}\n", ai_response);

    // 7. Apply persona style to response
    let styled_response = apply_persona_style(&active_jarvis, ai_response);
    println!("🎭 Styled Response (Jarvis):");
    println!("{}\n", styled_response);

    // 8. Learn from the interaction
    println!("📚 Learning from interaction...");
    client.add_example(
        active_jarvis.id,
        xswarm::personas::types::AddExampleRequest {
            user_message: user_message.to_string(),
            persona_response: styled_response.clone(),
            context: Some("calendar_query".to_string()),
            quality_score: Some(0.95),
        },
    ).await?;
    println!("✅ Conversation example stored\n");

    // 9. Create a different persona for comparison
    println!("Creating Buddy persona (friendly companion)...");
    let buddy_request = CreatePersonaRequest {
        name: "Buddy".to_string(),
        description: Some("A friendly, enthusiastic AI companion".to_string()),
        personality_traits: Some(PersonalityTraits {
            extraversion: 0.9,
            agreeableness: 0.9,
            conscientiousness: 0.6,
            neuroticism: 0.3,
            openness: 0.8,
            formality: 0.3,
            enthusiasm: 0.9,
        }),
        response_style: Some(ResponseStyle {
            verbosity: VerbosityLevel::Detailed,
            tone: ToneStyle::Friendly,
            humor_level: 0.7,
            technical_depth: 0.4,
            empathy_level: 0.9,
            proactivity: 0.7,
        }),
        expertise_areas: None,
    };

    let buddy = client.create_persona(buddy_request).await?;
    println!("✅ Created: {}", buddy.name);

    // 10. Activate Buddy and show different response
    client.activate_persona(buddy.id).await?;
    println!("✅ Activated: {}\n", buddy.name);

    println!("=== Same Question, Different Persona ===\n");
    println!("User: {}", user_message);

    let buddy_prompt = build_persona_prompt(&buddy, user_message);
    let buddy_ai_response = simulate_ai_response(&buddy_prompt);
    let buddy_styled = apply_persona_style(&buddy, buddy_ai_response);

    println!("\n🎭 Styled Response (Buddy):");
    println!("{}\n", buddy_styled);

    // 11. List all personas
    println!("=== All Personas ===\n");
    let all_personas = client.list_personas().await?;
    for persona in &all_personas.personas {
        let status = if persona.is_active { "ACTIVE" } else { "inactive" };
        println!("• {} [{}]", persona.name, status);
        println!("  Formality: {:.1}, Enthusiasm: {:.1}",
            persona.personality_traits.formality,
            persona.personality_traits.enthusiasm);
    }

    println!("\n📊 Total: {} personas", all_personas.personas.len());
    println!("   Limit: {}",
        if all_personas.meta.limit == -1 { "unlimited".to_string() }
        else { all_personas.meta.limit.to_string() });
    println!("   Can create more: {}\n", all_personas.meta.can_create_more);

    // 12. Voice training example (Personal tier feature)
    if all_personas.meta.tier != "free" {
        println!("=== Voice Training ===\n");
        println!("Training custom voice model for Jarvis...");

        // In production, these would be actual audio samples
        let mock_audio_samples = vec![
            "base64_encoded_audio_sample_1".to_string(),
            "base64_encoded_audio_sample_2".to_string(),
            "base64_encoded_audio_sample_3".to_string(),
            "base64_encoded_audio_sample_4".to_string(),
            "base64_encoded_audio_sample_5".to_string(),
        ];

        let training_session = client.train_voice(
            jarvis.id,
            xswarm::personas::types::TrainVoiceRequest {
                audio_samples: mock_audio_samples,
                sample_texts: Some(vec![
                    "Good morning, sir.".to_string(),
                    "Your meeting is at 2pm.".to_string(),
                ]),
            },
        ).await?;

        println!("✅ Training started");
        println!("   Session ID: {}", training_session.id);
        println!("   Status: {}", training_session.status);
        println!("   Progress: {}%\n", training_session.progress_percent);
    } else {
        println!("ℹ️  Voice training requires Personal tier\n");
    }

    println!("🎉 Example complete!");

    Ok(())
}

/// Simulate AI response (in production, use MOSHI or Claude API)
fn simulate_ai_response(prompt: &str) -> String {
    // This is a mock - in production, call your AI model here
    if prompt.contains("formality: 0.9") {
        // Jarvis-style response
        "Good morning, sir. Today you have three appointments on your calendar. \
         Your first meeting is at 9:00 AM with the development team, followed by \
         a lunch meeting at 12:30 PM. Your final appointment is at 3:00 PM with \
         the board of directors. Shall I provide more details about any of these?".to_string()
    } else {
        // Buddy-style response
        "Hey! Great question! So, let me check your calendar for you... Okay, you've \
         got a pretty busy day ahead! You have a team meeting at 9 AM - that should \
         be fun! Then lunch at 12:30, and wrapping up with the board meeting at 3 PM. \
         Want me to tell you more about any of these? I'm here to help!".to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_persona_traits_defaults() {
        let traits = PersonalityTraits::default();
        assert_eq!(traits.formality, 0.5);
        assert_eq!(traits.enthusiasm, 0.5);
    }

    #[test]
    fn test_simulate_ai_response() {
        let formal_prompt = "formality: 0.9";
        let response = simulate_ai_response(formal_prompt);
        assert!(response.contains("sir"));
        assert!(response.contains("Shall I"));
    }
}
