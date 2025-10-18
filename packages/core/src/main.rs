mod docs;

use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing::{info, Level};
use tracing_subscriber;

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

    /// Manage personality themes
    Theme {
        #[command(subcommand)]
        action: ThemeAction,
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
enum ThemeAction {
    /// List available themes
    List,
    /// Switch to a different theme
    Switch { name: String },
    /// Show current theme
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
        Commands::Theme { action } => match action {
            ThemeAction::List => {
                println!("📋 Available Themes:");
                println!("  - hal-9000 🔴  (HAL 9000 - Calm, rational AI)");
                println!("  - sauron 👁️   (The Dark Lord - Commanding and imperial)");
                println!("  - jarvis 💙   (JARVIS - Professional British butler)");
                println!("  - dalek 🤖    (DALEK - Aggressive cyborg: EXTERMINATE!)");
                println!("  - c3po 🤖     (C-3PO - Anxious protocol droid)");
                println!("  - glados 🔬   (GLaDOS - Passive-aggressive science AI)");
                println!("  - tars ◼️     (TARS - Honest, witty robot)");
            }
            ThemeAction::Switch { name } => {
                println!("🎨 Switching to theme: {}", name);
            }
            ThemeAction::Current => {
                println!("🎨 Current theme: hal-9000");
            }
        },
        Commands::Config { action } => match action {
            ConfigAction::Show => {
                println!("⚙️  xSwarm Configuration");
                println!("Coming soon: Configuration display");
            }
            ConfigAction::Set { key, value } => {
                println!("✏️  Setting {} = {}", key, value);
            }
            ConfigAction::Get { key } => {
                println!("🔍 Getting value for: {}", key);
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
