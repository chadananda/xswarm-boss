mod config;
mod docs;

use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing::{info, Level};
use tracing_subscriber;

use crate::config::Config;

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
            println!("🤔 Ask: {}", query);
            println!("Coming soon: Natural language queries with AI");
        }
        Commands::Do { command } => {
            info!("Executing command: {}", command);
            println!("⚡ Do: {}", command);
            println!("Coming soon: AI-powered command execution");
        }
    }

    Ok(())
}
