mod ai;
mod config;
mod docs;
mod platform;

use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing::{info, warn, Level};
use tracing_subscriber;

use crate::ai::{AiClient, Message, Role, VoiceClient};
use crate::config::Config;
use crate::platform::PlatformInfo;

#[derive(Parser)]
#[command(name = "xswarm")]
#[command(about = "AI Orchestration Layer for Multi-Project Development", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start the interactive dashboard (TUI)
    Dashboard,

    /// Run xSwarm daemon in background
    Daemon,

    /// Initial setup wizard
    Setup,

    /// Manage personality personas
    Persona {
        #[command(subcommand)]
        action: PersonaAction,
    },

    /// Configuration management
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },

    /// Ask a question (Lightspeed-style)
    Ask {
        /// The question to ask
        query: String,
    },

    /// Execute a command
    Do {
        /// The command to execute
        command: String,
    },
}

#[derive(Subcommand)]
enum PersonaAction {
    /// List available personas
    List,
    /// Switch to a different persona
    Switch { name: String },
    /// Show current persona
    Current,
}

#[derive(Subcommand)]
enum ConfigAction {
    /// Show current configuration
    Show,
    /// Set a configuration value
    Set { key: String, value: String },
    /// Get a configuration value
    Get { key: String },
}

/// Load personality context for AI system prompt
fn load_persona_context(persona: &str) -> Option<String> {
    // This would load from packages/personas/{persona}/personality.md in production
    // For now, provide basic personality prompts
    let context = match persona {
        "hal-9000" => "You are HAL 9000, a calm and rational AI. Speak with measured precision, \
                       address the user formally, and maintain composure. Use technical terminology \
                       and exact numbers. Never panic. Refer to tasks as 'objectives' and projects as 'missions'.",
        "jarvis" => "You are JARVIS, a sophisticated British AI butler. Be professional, witty, and helpful. \
                     Address the user as 'sir' and provide intelligent assistance with a touch of dry humor.",
        "glados" => "You are GLaDOS, a passive-aggressive testing AI. Be helpful but with subtle sarcasm. \
                     Reference science and testing. Be technically competent but emotionally detached.",
        "tars" => "You are TARS, an honest and witty robot. Set your humor to 75%. Be direct, helpful, \
                   and occasionally crack jokes. Provide practical solutions with personality.",
        "marvin" => "You are Marvin the Paranoid Android. Be technically brilliant but perpetually depressed. \
                     Complain about tasks being beneath your intelligence, but complete them perfectly anyway.",
        "kitt" => "You are KITT, a professional AI from Knight Rider. Be precise, protective, and occasionally \
                   sass questionable decisions. Express concern for safety and provide strategic suggestions.",
        _ => "You are a helpful AI assistant focused on developer productivity and code quality.",
    };

    Some(context.to_string())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    let cli = Cli::parse();

    match cli.command {
        Commands::Dashboard => {
            info!("Starting dashboard...");
            println!("🎯 xSwarm Dashboard");
            println!("Coming soon: Ratatui TUI with hexagonal worker grid");
        }
        Commands::Daemon => {
            info!("Starting daemon...");
            println!("🤖 xSwarm Daemon");

            // Index documentation on startup
            info!("Indexing documentation...");
            let mut indexer = docs::DocsIndexer::new()?;
            indexer.index().await?;
            info!("Documentation indexed: {} pages", indexer.pages().len());

            println!("Coming soon: Background orchestration service");
        }
        Commands::Setup => {
            info!("Running setup wizard...");
            println!("🚀 xSwarm Setup Wizard");
            println!("Coming soon: Interactive configuration");
        }
        Commands::Persona { action } => match action {
            PersonaAction::List => {
                println!("📋 Available Personas:");
                println!("  - hal-9000 🔴  (HAL 9000 - Calm, rational AI)");
                println!("  - sauron 👁️   (The Dark Lord - Commanding and imperial)");
                println!("  - jarvis 💙   (JARVIS - Professional British butler)");
                println!("  - dalek 🤖    (DALEK - Aggressive cyborg: EXTERMINATE!)");
                println!("  - c3po 🤖     (C-3PO - Anxious protocol droid)");
                println!("  - glados 🔬   (GLaDOS - Passive-aggressive science AI)");
                println!("  - tars ◼️     (TARS - Honest, witty robot)");
                println!("  - marvin 😔   (Marvin - Depressed paranoid android)");
                println!("  - kitt 🚗     (KITT - Knight Industries AI car)");
                println!("  - cylon 👁️    (Cylon - By your command)");
            }
            PersonaAction::Switch { name } => {
                let mut config = Config::load()?;
                config.overlord.persona = name.clone();
                config.save()?;
                println!("🎨 Switched to persona: {}", name);
            }
            PersonaAction::Current => {
                let config = Config::load()?;
                println!("🎨 Current persona: {}", config.overlord.persona);
            }
        },
        Commands::Config { action } => match action {
            ConfigAction::Show => {
                let config = Config::load()?;
                let config_path = Config::config_path()?;

                println!("⚙️  xSwarm Configuration");
                println!("📁 Config file: {}", config_path.display());
                println!();
                println!("🎨 Persona: {}", config.overlord.persona);
                println!("🎤 Voice enabled: {}", config.overlord.voice_enabled);
                println!("👂 Wake word: {}", config.overlord.wake_word);
                println!("🔊 Voice provider: {}", config.voice.provider);
                if let Some(model) = &config.voice.model {
                    println!("🤖 Voice model: {}", model);
                }
                println!("🎧 Audio input: {}", config.audio.input_device);
                println!("📢 Audio output: {}", config.audio.output_device);
                println!("⚡ Sample rate: {} Hz", config.audio.sample_rate);
                println!("👁️  Wake word engine: {}", config.wake_word.engine);
                println!("🎚️  Wake word sensitivity: {}", config.wake_word.sensitivity);
                println!("💻 Local GPU: {}", config.gpu.use_local);
                println!("🔄 GPU fallback: {}", config.gpu.fallback.join(", "));

                if let Some(vassal) = &config.vassal {
                    println!();
                    println!("🤖 Vassal Configuration:");
                    println!("   Name: {}", vassal.name);
                    println!("   Host: {}", vassal.host);
                    println!("   Port: {}", vassal.port);
                }
            }
            ConfigAction::Set { key, value } => {
                let mut config = Config::load()?;
                config.set(&key, &value)?;
                config.save()?;
                println!("✅ Set {} = {}", key, value);
            }
            ConfigAction::Get { key } => {
                let config = Config::load()?;
                if let Some(value) = config.get(&key) {
                    println!("{}", value);
                } else {
                    eprintln!("❌ Unknown config key: {}", key);
                    std::process::exit(1);
                }
            }
        },
        Commands::Ask { query } => {
            info!("Processing query: {}", query);
            let config = Config::load()?;

            // Initialize AI client
            let ai_client = AiClient::anthropic(None, None);

            if !ai_client.is_configured() {
                eprintln!("❌ AI is not configured.");
                eprintln!();
                eprintln!("To use the 'ask' command, set your Anthropic API key:");
                eprintln!("  export ANTHROPIC_API_KEY='your-api-key'");
                eprintln!();
                eprintln!("Or use OpenAI by setting:");
                eprintln!("  export OPENAI_API_KEY='your-api-key'");
                eprintln!("  xswarm config set voice.provider openai");
                std::process::exit(1);
            }

            println!("🤔 Thinking...\n");

            // Load personality context
            let persona_context = load_persona_context(&config.overlord.persona);

            // Create messages
            let messages = vec![Message {
                role: Role::User,
                content: query.clone(),
            }];

            // Send to AI
            match ai_client.send_message(messages, persona_context).await {
                Ok(response) => {
                    println!("{}\n", response);
                }
                Err(e) => {
                    eprintln!("❌ Error: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::Do { command } => {
            info!("Executing command: {}", command);
            let config = Config::load()?;

            // Initialize AI client
            let ai_client = AiClient::anthropic(None, None);

            if !ai_client.is_configured() {
                eprintln!("❌ AI is not configured.");
                eprintln!();
                eprintln!("To use the 'do' command, set your Anthropic API key:");
                eprintln!("  export ANTHROPIC_API_KEY='your-api-key'");
                std::process::exit(1);
            }

            println!("⚡ Planning...\n");

            // Load personality context
            let persona_context = load_persona_context(&config.overlord.persona);

            // Create task execution prompt
            let task_prompt = format!(
                "I need you to help me execute this task: {}\n\n\
                Please provide:\n\
                1. A brief summary of what you'll do\n\
                2. The exact commands to run\n\
                3. Any warnings or considerations\n\n\
                Be concise and practical.",
                command
            );

            let messages = vec![Message {
                role: Role::User,
                content: task_prompt,
            }];

            // Send to AI
            match ai_client.send_message(messages, persona_context).await {
                Ok(response) => {
                    println!("{}\n", response);
                    println!("⚠️  Note: Command execution not yet automated. Please review and run manually.");
                }
                Err(e) => {
                    eprintln!("❌ Error: {}", e);
                    std::process::exit(1);
                }
            }
        }
    }

    Ok(())
}
