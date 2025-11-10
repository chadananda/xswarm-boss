// Example: MOSHI Personality Configuration
//
// This example demonstrates how to configure MOSHI with different personalities
// for Jarvis-like voice conversations.
//
// Run with: cargo run --example moshi_personality_example

use xswarm::moshi_personality::{MoshiPersonality, PersonalityManager, ResponseConfig, InterruptHandling};
use xswarm::personas::{VerbosityLevel, ToneStyle};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing for logging
    tracing_subscriber::fmt::init();

    println!("=== MOSHI Personality Configuration Examples ===\n");

    // Example 1: Default Jarvis Personality
    println!("1. Default Jarvis Personality");
    println!("-------------------------------");
    let jarvis = MoshiPersonality::jarvis();
    println!("Name: {}", jarvis.assistant_role.name);
    println!("Role: {}", jarvis.assistant_role.primary_function);
    println!("Formality: {:.1}", jarvis.persona.personality_traits.formality);
    println!("Proactivity: {:.1}", jarvis.persona.response_style.proactivity);
    println!("Context: {}", jarvis.generate_context_prompt());
    println!("Greeting: {}\n", jarvis.generate_greeting());

    // Example 2: Friendly Assistant Personality
    println!("2. Friendly Assistant Personality");
    println!("----------------------------------");
    let friendly = MoshiPersonality::friendly();
    println!("Name: {}", friendly.assistant_role.name);
    println!("Role: {}", friendly.assistant_role.primary_function);
    println!("Enthusiasm: {:.1}", friendly.persona.personality_traits.enthusiasm);
    println!("Empathy: {:.1}", friendly.persona.response_style.empathy_level);
    println!("Context: {}", friendly.generate_context_prompt());
    println!("Greeting: {}\n", friendly.generate_greeting());

    // Example 3: Custom Executive Assistant
    println!("3. Custom Executive Assistant");
    println!("------------------------------");
    let mut executive = MoshiPersonality::jarvis();
    executive.persona.name = "Executive Assistant".to_string();
    executive.assistant_role.name = "Executive Assistant".to_string();
    executive.persona.personality_traits.conscientiousness = 0.95;
    executive.persona.personality_traits.formality = 0.85;
    executive.persona.response_style.proactivity = 0.95;
    executive.persona.response_style.verbosity = VerbosityLevel::Concise;
    executive.response_config.max_response_length = 50;
    println!("Name: {}", executive.assistant_role.name);
    println!("Conscientiousness: {:.2}", executive.persona.personality_traits.conscientiousness);
    println!("Max response length: {}", executive.response_config.max_response_length);
    println!("Context: {}", executive.generate_context_prompt());
    println!("Greeting: {}\n", executive.generate_greeting());

    // Example 4: Casual Tech Support
    println!("4. Casual Tech Support Assistant");
    println!("---------------------------------");
    let mut tech_support = MoshiPersonality::friendly();
    tech_support.persona.name = "Tech Support".to_string();
    tech_support.assistant_role.name = "Tech Support".to_string();
    tech_support.assistant_role.primary_function =
        "Technical support assistant for troubleshooting and guidance".to_string();
    tech_support.persona.expertise_areas = vec![
        "Technology".to_string(),
        "Troubleshooting".to_string(),
        "Software".to_string(),
    ];
    tech_support.persona.response_style.technical_depth = 0.8;
    tech_support.persona.response_style.tone = ToneStyle::Analytical;
    tech_support.persona.personality_traits.formality = 0.4; // Casual but competent
    println!("Name: {}", tech_support.assistant_role.name);
    println!("Technical depth: {:.1}", tech_support.persona.response_style.technical_depth);
    println!("Formality: {:.1}", tech_support.persona.personality_traits.formality);
    println!("Expertise: {}", tech_support.persona.expertise_areas.join(", "));
    println!("Context: {}\n", tech_support.generate_context_prompt());

    // Example 5: Personality Manager Usage
    println!("5. Using Personality Manager");
    println!("-----------------------------");
    let manager = PersonalityManager::new();
    println!("Default personality: {}", manager.get_personality().await.assistant_role.name);

    // Switch to friendly
    manager.set_personality(MoshiPersonality::friendly()).await;
    println!("Switched to: {}", manager.get_personality().await.assistant_role.name);

    // Generate context and greeting
    let context = manager.generate_context_prompt().await;
    let greeting = manager.generate_greeting().await;
    println!("Context: {}", context);
    println!("Greeting: {}\n", greeting);

    // Example 6: Response Configuration
    println!("6. Response Configuration Options");
    println!("---------------------------------");
    let mut quick_responder = MoshiPersonality::jarvis();
    quick_responder.response_config = ResponseConfig {
        max_response_length: 30,
        response_delay_ms: 150,
        use_filler_words: false,
        interrupt_handling: InterruptHandling::Immediate,
    };
    println!("Max response length: {}", quick_responder.response_config.max_response_length);
    println!("Response delay: {}ms", quick_responder.response_config.response_delay_ms);
    println!("Filler words: {}", quick_responder.response_config.use_filler_words);
    println!("Interrupt handling: {:?}\n", quick_responder.response_config.interrupt_handling);

    // Example 7: Personality Comparison
    println!("7. Personality Trait Comparison");
    println!("--------------------------------");
    let jarvis = MoshiPersonality::jarvis();
    let friendly = MoshiPersonality::friendly();

    println!("Trait Comparison (Jarvis vs Friendly):");
    println!("  Formality:        {:.1} vs {:.1}",
        jarvis.persona.personality_traits.formality,
        friendly.persona.personality_traits.formality
    );
    println!("  Enthusiasm:       {:.1} vs {:.1}",
        jarvis.persona.personality_traits.enthusiasm,
        friendly.persona.personality_traits.enthusiasm
    );
    println!("  Conscientiousness: {:.1} vs {:.1}",
        jarvis.persona.personality_traits.conscientiousness,
        friendly.persona.personality_traits.conscientiousness
    );
    println!("  Empathy:          {:.1} vs {:.1}",
        jarvis.persona.response_style.empathy_level,
        friendly.persona.response_style.empathy_level
    );
    println!("  Proactivity:      {:.1} vs {:.1}\n",
        jarvis.persona.response_style.proactivity,
        friendly.persona.response_style.proactivity
    );

    println!("=== Examples Complete ===");
    println!("\nNext Steps:");
    println!("1. Review MOSHI_PERSONALITY_GUIDE.md for detailed documentation");
    println!("2. Integrate personality into your VoiceBridge setup");
    println!("3. Call inject_personality_context() at conversation start");
    println!("4. Customize traits for your specific use case");

    Ok(())
}
