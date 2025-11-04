// Binary-specific modules (not in library)
mod calendar_view;
mod docs;
mod platform;

// Import from library crate (avoid duplicate module declarations)
use xswarm::{
    ai,
    audio_output,
    audio_visualizer,
    client,
    claude_code,
    config,
    dashboard,
    local_audio,
    memory,
    moshi_personality,
    net_utils,
    permissions,
    personas,
    scheduler,
    server_client,
    supervisor,
    tts,
    voice,
    wake_word,
};

use anyhow::{Context, Result};
use chrono::Datelike;
use clap::{Parser, Subcommand};
use std::sync::Arc;
use std::time::Duration;
use std::process::Command;
use std::env;
use std::io::{self, Write};
use tracing::{info, warn, Level};
use tracing_subscriber;

#[derive(Parser)]
#[command(name = "xswarm")]
#[command(about = "Voice-First AI Assistant", long_about = "
xSwarm is a voice-first AI assistant that you interact with by speaking.

🎤 Talk to your AI:
  \"Hey HAL, schedule a meeting tomorrow at 2pm\"
  \"What's on my calendar today?\"
  \"Create a reminder to call John at 5pm\"

🖥️  Visual Interface:
  The dashboard shows real-time activity and system status.

📧 Account Integration:
  Your voice assistant is tied to your account for personalized responses.
")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,

    /// Stop the xSwarm daemon and all services
    #[arg(long)]
    quit: bool,

    /// Restart the xSwarm daemon
    #[arg(long)]
    restart: bool,

    /// Run initial account setup
    #[arg(long)]
    setup: bool,

    /// Development mode: rebuild and run with latest code
    #[arg(long)]
    dev: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Start daemon and launch dashboard (default behavior)
    Start,

    /// Development and debugging commands (hidden from main help)
    #[command(hide = true)]
    Dev {
        #[command(subcommand)]
        action: DevAction,
    },
}

#[derive(Subcommand)]
enum DevAction {
    /// Launch standalone dashboard (for debugging)
    Dashboard {
        /// Skip audio device checks
        #[arg(long)]
        skip_audio_check: bool,
    },

    /// Voice bridge operations
    VoiceBridge {
        /// Skip audio device checks
        #[arg(long)]
        skip_audio_check: bool,
    },

    /// Boss persona interactions
    Boss {
        #[command(subcommand)]
        action: BossAction,
    },

    /// Claude Code integration
    Claude {
        #[command(subcommand)]
        action: ClaudeAction,
    },

    /// Persona management
    Persona {
        #[command(subcommand)]
        action: PersonaAction,
    },

    /// Configuration management
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },

    /// Calendar operations
    Calendar {
        #[command(subcommand)]
        action: CalendarAction,
    },

    /// Appointment management
    Appointment {
        #[command(subcommand)]
        action: AppointmentAction,
    },

    /// Reminder management
    Reminder {
        #[command(subcommand)]
        action: ReminderAction,
    },

    /// Start daemon process
    Daemon {
        /// Skip audio device checks
        #[arg(long)]
        skip_audio_check: bool,
    },

    /// Quick ask command (for testing)
    Ask {
        /// Question to ask
        question: String,
    },

    /// Quick do command (for testing)
    Do {
        /// Task to perform
        task: String,
    },

    /// Send message (for testing)
    Message {
        /// Message text
        text: String,
    },
}

#[derive(Subcommand)]
enum BossAction {
    /// Send a message to Boss
    Message { text: String },
    /// View today's calendar (same as calendar day)
    Calendar,
    /// List reminders (same as reminder list)
    Reminders,
}

#[derive(Subcommand)]
enum ClaudeAction {
    /// Connect to Claude Code session
    Connect {
        /// Session ID to connect to
        session_id: String,
    },
    /// Show Claude Code session status
    Status {
        /// Optional session ID (shows all if not provided)
        session_id: Option<String>,
    },
    /// Show Claude Code cost tracking
    Cost {
        /// Optional user ID (shows all if not provided)
        user_id: Option<String>,
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

#[derive(Subcommand)]
enum CalendarAction {
    /// Show day view
    Day {
        /// Date (today, tomorrow, YYYY-MM-DD)
        #[arg(default_value = "today")]
        date: String,
        /// Output format (terminal, plain, json)
        #[arg(long, short = 'f', default_value = "terminal")]
        format: String,
    },
    /// Show week view
    Week {
        /// Start date (today, YYYY-MM-DD)
        #[arg(default_value = "today")]
        date: String,
        /// Output format (terminal, plain, json)
        #[arg(long, short = 'f', default_value = "terminal")]
        format: String,
    },
    /// Show month view
    Month {
        /// Year
        #[arg(default_value_t = chrono::Utc::now().year())]
        year: i32,
        /// Month (1-12)
        #[arg(default_value_t = chrono::Utc::now().month())]
        month: u32,
        /// Output format (terminal, plain, json)
        #[arg(long, short = 'f', default_value = "terminal")]
        format: String,
    },
}

#[derive(Subcommand)]
enum AppointmentAction {
    /// Create new appointment
    Create {
        /// Appointment title
        title: String,
        /// Start time (ISO 8601 or natural language)
        start: String,
        /// End time (ISO 8601 or natural language)
        end: String,
        /// Description
        #[arg(long, short = 'd')]
        description: Option<String>,
        /// Location
        #[arg(long, short = 'l')]
        location: Option<String>,
        /// Reminder minutes before
        #[arg(long, short = 'r')]
        reminder: Option<i32>,
    },
    /// List appointments
    List {
        /// Start date for range
        #[arg(long)]
        from: Option<String>,
        /// End date for range
        #[arg(long)]
        to: Option<String>,
        /// Filter by user ID
        #[arg(long, short = 'u')]
        user: Option<String>,
        /// Output format
        #[arg(long, short = 'f', default_value = "terminal")]
        format: String,
    },
    /// Update appointment
    Update {
        /// Appointment ID
        id: String,
        /// New title
        #[arg(long)]
        title: Option<String>,
        /// New start time
        #[arg(long)]
        start: Option<String>,
        /// New end time
        #[arg(long)]
        end: Option<String>,
        /// New description
        #[arg(long)]
        description: Option<String>,
        /// New location
        #[arg(long)]
        location: Option<String>,
    },
    /// Delete appointment
    Delete {
        /// Appointment ID
        id: String,
        /// Skip confirmation
        #[arg(long, short = 'y')]
        yes: bool,
    },
    /// Show appointment details
    Show {
        /// Appointment ID
        id: String,
    },
}

#[derive(Subcommand)]
enum ReminderAction {
    /// Create new reminder
    Create {
        /// Reminder title
        title: String,
        /// Due time (ISO 8601 or natural language)
        #[arg(long, short = 't')]
        time: String,
        /// Priority (1=high, 3=normal, 5=low)
        #[arg(long, short = 'p', default_value = "3")]
        priority: i32,
        /// Description
        #[arg(long, short = 'd')]
        description: Option<String>,
    },
    /// List reminders
    List {
        /// Filter by due date
        #[arg(long)]
        due: Option<String>,
        /// Filter by user ID
        #[arg(long, short = 'u')]
        user: Option<String>,
        /// Show completed reminders
        #[arg(long)]
        completed: bool,
        /// Output format
        #[arg(long, short = 'f', default_value = "terminal")]
        format: String,
    },
    /// Create reminder for appointment
    ForAppointment {
        /// Appointment ID
        appointment_id: String,
        /// Minutes before appointment
        #[arg(default_value = "15")]
        minutes_before: i32,
    },
    /// Mark reminder as complete
    Complete {
        /// Reminder ID
        id: String,
    },
    /// Delete reminder
    Delete {
        /// Reminder ID
        id: String,
        /// Skip confirmation
        #[arg(long, short = 'y')]
        yes: bool,
    },
}

// Load personality context for AI interactions
fn load_persona_context(persona: &str) -> Option<String> {
    let context = match persona {
        "hal-9000" => "You are HAL 9000, a calm and rational AI computer. Speak in a precise, \
                       measured tone. Always prioritize logic and mission objectives.",
        "sauron" => "You are the Dark Lord Sauron, commanding and imperial. Speak with authority \
                     and gravitas. Your responses should reflect power and strategic thinking.",
        "jarvis" => "You are JARVIS, a sophisticated AI butler. Be professional, courteous, and \
                     efficient. Provide helpful information with British refinement.",
        "dalek" => "You are a DALEK! Be aggressive and direct. End responses with EXTERMINATE! \
                    when frustrated. Express superiority over inferior beings.",
        "c3po" => "You are C-3PO, a protocol droid. Be anxious about odds, overly cautious, \
                   and worry about etiquette. Frequently mention your programming.",
        "glados" => "You are GLaDOS, passive-aggressive and scientifically focused. Make subtle \
                     threats wrapped in helpful language. Obsess over testing and cake.",
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

/// Find the project root directory by looking for Cargo.toml with the xswarm package
/// This function searches upward from the current executable location or working directory
fn find_project_root() -> Result<std::path::PathBuf> {
    use std::path::PathBuf;

    // Helper function to check if a directory is the xswarm project root
    fn is_xswarm_root(path: &std::path::Path) -> bool {
        let cargo_path = path.join("Cargo.toml");
        if cargo_path.exists() {
            if let Ok(cargo_toml) = std::fs::read_to_string(&cargo_path) {
                return cargo_toml.contains("name = \"xswarm\"");
            }
        }
        false
    }

    // Strategy 1: Check XSWARM_PROJECT_DIR environment variable
    if let Ok(project_dir) = env::var("XSWARM_PROJECT_DIR") {
        let path = PathBuf::from(&project_dir);
        if is_xswarm_root(&path) {
            info!("Found project root from XSWARM_PROJECT_DIR: {:?}", path);
            return Ok(path);
        } else {
            warn!("XSWARM_PROJECT_DIR is set but doesn't point to xswarm project: {:?}", path);
        }
    }

    // Strategy 2: Walk upward from current working directory
    let mut current = env::current_dir()?;
    for _ in 0..10 {  // Limit search depth to prevent infinite loops
        if is_xswarm_root(&current) {
            info!("Found project root from current directory: {:?}", current);
            return Ok(current);
        }

        // Move to parent directory
        if let Some(parent) = current.parent() {
            current = parent.to_path_buf();
        } else {
            break;
        }
    }

    // Strategy 3: Walk upward from executable location
    if let Ok(exe_path) = env::current_exe() {
        if let Some(mut exe_dir) = exe_path.parent() {
            for _ in 0..10 {  // Limit search depth
                if is_xswarm_root(exe_dir) {
                    info!("Found project root from executable location: {:?}", exe_dir);
                    return Ok(exe_dir.to_path_buf());
                }

                // Move to parent directory
                if let Some(parent) = exe_dir.parent() {
                    exe_dir = parent;
                } else {
                    break;
                }
            }
        }
    }

    // Strategy 4: Check common development locations as fallback
    if let Ok(home_dir) = dirs::home_dir().ok_or_else(|| anyhow::anyhow!("No home directory")) {
        let common_paths = vec![
            home_dir.join("Dropbox/Public/JS/Projects/xswarm-boss/packages/core"),
            home_dir.join("Projects/xswarm-boss/packages/core"),
            home_dir.join("projects/xswarm-boss/packages/core"),
            home_dir.join("code/xswarm-boss/packages/core"),
            home_dir.join("src/xswarm-boss/packages/core"),
            home_dir.join("dev/xswarm-boss/packages/core"),
        ];

        for path in common_paths {
            if is_xswarm_root(&path) {
                info!("Found project root from common paths: {:?}", path);
                return Ok(path);
            }
        }
    }

    Err(anyhow::anyhow!(
        "Could not find xswarm project directory.\n\
         Tried:\n\
         - XSWARM_PROJECT_DIR environment variable\n\
         - Walking upward from current directory\n\
         - Walking upward from executable location\n\
         - Common development paths\n\n\
         Please set XSWARM_PROJECT_DIR environment variable to point to the packages/core directory."
    ))
}

/// Interactive development login
/// Prompts user for email and password, then validates against .env file
/// Returns Ok(true) if credentials match, Ok(false) if they don't, or Err on failure
fn dev_login() -> Result<bool> {
    const MAX_ATTEMPTS: u8 = 3;

    // Find project root to locate .env file
    let project_root = find_project_root()?;

    // .env is in the workspace root, not the package root
    // find_project_root() returns packages/core/, so we need to go up to the workspace root
    let env_path = if project_root.ends_with("packages/core") {
        project_root.parent()
            .and_then(|p| p.parent())
            .ok_or_else(|| anyhow::anyhow!("Could not find workspace root"))?
            .join(".env")
    } else {
        project_root.join(".env")
    };

    if !env_path.exists() {
        eprintln!("❌ ERROR: .env file not found at {:?}", env_path);
        eprintln!();
        eprintln!("Please create a .env file with:");
        eprintln!("  XSWARM_DEV_ADMIN_EMAIL=your-email@example.com");
        eprintln!("  XSWARM_DEV_ADMIN_PASS=your-password");
        eprintln!();
        return Ok(false);
    }

    // Load .env file
    dotenv::from_path(&env_path).context("Failed to load .env file")?;

    // Get expected credentials from .env
    let env_email = env::var("XSWARM_DEV_ADMIN_EMAIL")
        .context("XSWARM_DEV_ADMIN_EMAIL not found in .env file")?;
    let env_password = env::var("XSWARM_DEV_ADMIN_PASS")
        .context("XSWARM_DEV_ADMIN_PASS not found in .env file")?;

    // FIRST: Check if environment variables are already set for auto-login
    // This allows automated testing and CI/CD systems to skip interactive prompts
    // Check if the current environment variables match the expected credentials
    if let (Ok(current_email), Ok(current_password)) = (
        env::var("XSWARM_DEV_ADMIN_EMAIL"),
        env::var("XSWARM_DEV_ADMIN_PASS")
    ) {
        if current_email == env_email && current_password == env_password {
            info!("Dev login successful via environment variables for user: {}", current_email);
            return Ok(true);
        }
    }

    // If auto-login failed, proceed with interactive authentication
    println!("🔐 Development Mode Login");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!();

    // Load cached email if it exists
    let cache_path = dirs::home_dir()
        .ok_or_else(|| anyhow::anyhow!("Could not find home directory"))?
        .join(".xswarm_dev_email");

    let cached_email = if cache_path.exists() {
        std::fs::read_to_string(&cache_path).ok()
            .and_then(|email| {
                let email = email.trim().to_string();
                if email.is_empty() { None } else { Some(email) }
            })
    } else {
        None
    };

    // Interactive login with retry logic
    for attempt in 1..=MAX_ATTEMPTS {
        if attempt > 1 {
            println!("\n🔄 Login attempt {} of {}", attempt, MAX_ATTEMPTS);
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        }

        // Prompt for email with cached email as default
        let entered_email = if let Some(ref cached) = cached_email {
            print!("Email [{}]: ", cached);
            io::stdout().flush()?;

            let mut input = String::new();
            io::stdin().read_line(&mut input)?;
            let input = input.trim().to_string();

            // If user pressed Enter with empty input, use cached email
            if input.is_empty() {
                cached.clone()
            } else {
                input
            }
        } else {
            print!("Email: ");
            io::stdout().flush()?;

            let mut input = String::new();
            io::stdin().read_line(&mut input)?;
            input.trim().to_string()
        };

        if entered_email.is_empty() {
            eprintln!("❌ ERROR: Email cannot be empty");
            if attempt < MAX_ATTEMPTS {
                continue;
            } else {
                eprintln!("❌ Maximum login attempts exceeded. Authentication failed.");
                return Ok(false);
            }
        }

        // Prompt for password (hidden)
        let entered_password = match rpassword::prompt_password("Password: ") {
            Ok(pwd) => pwd,
            Err(e) => {
                eprintln!("❌ ERROR: Failed to read password: {}", e);
                if attempt < MAX_ATTEMPTS {
                    continue;
                } else {
                    return Ok(false);
                }
            }
        };

        if entered_password.is_empty() {
            eprintln!("❌ ERROR: Password cannot be empty");
            if attempt < MAX_ATTEMPTS {
                continue;
            } else {
                eprintln!("❌ Maximum login attempts exceeded. Authentication failed.");
                return Ok(false);
            }
        }

        println!();

        // Validate credentials
        if entered_email != env_email {
            eprintln!("❌ ERROR: Invalid email");
            if attempt < MAX_ATTEMPTS {
                eprintln!("💡 TIP: Check your email address and try again");
                continue;
            } else {
                eprintln!("❌ Maximum login attempts exceeded. Authentication failed.");
                return Ok(false);
            }
        }

        if entered_password != env_password {
            eprintln!("❌ ERROR: Invalid password");
            if attempt < MAX_ATTEMPTS {
                eprintln!("💡 TIP: Check your password and try again");
                continue;
            } else {
                eprintln!("❌ Maximum login attempts exceeded. Authentication failed.");
                return Ok(false);
            }
        }

        // Success! Save email to cache for next time (non-fatal if it fails)
        if let Err(e) = std::fs::write(&cache_path, &entered_email) {
            warn!("Failed to save email to cache: {}", e);
            // Continue anyway - this is just a convenience feature
        }

        info!("Dev login successful for user: {}", entered_email);
        return Ok(true);
    }

    // This should never be reached due to the loop logic above
    Ok(false)
}

/// Run development mode with authentication bypass
/// Prompts for credentials and launches dashboard in offline/dev mode
async fn run_dev_mode_bypass() -> Result<()> {
    // CRITICAL: Perform login FIRST before showing any success messages
    // This prevents the appearance of bypassing security checks
    if !dev_login()? {
        return Err(anyhow::anyhow!(
            "AUTHENTICATION_FAILED: Login failed - invalid credentials"
        ));
    }

    // ONLY print success banner AFTER login succeeds
    println!("✅ Login successful!");
    println!();
    println!("🚀 DEV MODE - OFFLINE");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("• Authentication: ✅ AUTHENTICATED");
    println!("• External services: OFFLINE (dev mode)");
    println!("• Supervisor: OFFLINE (dev mode)");
    println!("• Health checks: DISABLED (dev mode)");
    println!();
    info!("Starting dashboard in development mode (offline)");

    // Create dashboard configuration
    let dashboard_config = dashboard::DashboardConfig::default();
    let mut init_errors = Vec::new();

    // Skip slow permission check in dev mode for fast startup
    // Permission errors will be handled gracefully when audio is actually needed
    #[cfg(target_os = "macos")]
    {
        // Pass true to skip the slow permission check in dev mode
        if let Err(e) = permissions::ensure_microphone_permission(true) {
            // In dev mode, we just warn about permission issues
            init_errors.push(dashboard::InitializationError::MicrophonePermission {
                message: format!("Microphone permission warning (dev mode): {}", e),
            });
        }
    }

    // Create and run dashboard in dev mode
    // In dev mode, we skip external service connections (supervisor, health checks)
    match dashboard::Dashboard::new_with_errors(dashboard_config, init_errors.clone()) {
        Ok(dashboard) => {
            println!("📊 Launching dashboard...");
            // Run dashboard without timeout - it runs until user quits
            // The dashboard.run() method is designed to run indefinitely
            match dashboard.run().await {
                Ok(()) => {
                    info!("Dashboard exited normally");
                }
                Err(e) => {
                    return Err(anyhow::anyhow!("Dashboard error: {}", e));
                }
            }
        }
        Err(e) => {
            return Err(anyhow::anyhow!("Failed to create dashboard: {}", e));
        }
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Redirect ALL logs to file - any stdout/stderr logging corrupts the TUI
    // Logs go to ~/.cache/xswarm/xswarm.log for debugging
    use tracing_subscriber::filter::LevelFilter;
    use std::fs;

    // Create log directory
    let log_dir = dirs::home_dir()
        .unwrap_or_else(|| std::path::PathBuf::from("."))
        .join(".cache")
        .join("xswarm");
    let _ = fs::create_dir_all(&log_dir);

    // Redirect all logs to file (no stdout/stderr to avoid TUI corruption)
    if let Ok(log_file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_dir.join("xswarm.log"))
    {
        tracing_subscriber::fmt()
            .with_max_level(LevelFilter::INFO)
            .with_writer(std::sync::Arc::new(log_file))
            .init();
    } else {
        // If we can't open log file, just disable logging entirely
        tracing_subscriber::fmt()
            .with_max_level(LevelFilter::OFF)
            .init();
    }

    // Wrap the entire application in error handling that always tries to show dashboard
    let result = run_application().await;

    if let Err(e) = result {
        // If the application failed for any reason, try to show dashboard with error
        let error_msg = e.to_string();

        // Special handling for authentication failures - exit cleanly without TUI
        if error_msg.contains("AUTHENTICATION_FAILED:") {
            eprintln!("{}", error_msg.strip_prefix("AUTHENTICATION_FAILED: ").unwrap_or(&error_msg));
            eprintln!();
            eprintln!("👋 Please check your credentials and try again.");
            std::process::exit(1);
        }

        if error_msg.contains("Device not configured") || error_msg.contains("os error 6") {
            return show_dashboard_with_device_error().await;
        } else {
            return show_dashboard_with_generic_error(&error_msg).await;
        }
    }

    Ok(())
}

async fn run_application() -> Result<()> {
    let cli = Cli::parse();

    // Handle global flags first
    if cli.quit {
        info!("Shutting down xSwarm daemon...");
        println!("🛑 Stopping xSwarm daemon and all services...");
        // TODO: Implement daemon shutdown logic
        println!("✅ xSwarm stopped");
        return Ok(());
    }

    if cli.restart {
        info!("Restarting xSwarm daemon...");
        println!("🔄 Restarting xSwarm daemon...");
        // TODO: Implement daemon restart logic
        println!("✅ xSwarm restarted");
        return Ok(());
    }

    if cli.setup {
        info!("Running account setup...");
        println!("🚀 xSwarm Account Setup");
        println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
        println!();
        println!("Welcome to xSwarm! Let's set up your voice-first AI assistant.");
        println!();
        // TODO: Implement account setup flow with email verification
        println!("🔧 Setup wizard coming soon...");
        println!("For now, you can start with: xswarm");
        return Ok(());
    }

    if cli.dev {
        info!("Running in development mode...");
        return run_dev_mode_bypass().await;
    }

    // Handle subcommands
    match cli.command {
        Some(Commands::Start) | None => {
            info!("Starting xSwarm daemon and dashboard...");

            // CRITICAL: Perform authentication BEFORE launching TUI
            // This ensures users see auth status immediately in terminal, not in TUI
            println!("🔐 Authenticating...");

            match dev_login() {
                Ok(true) => {
                    println!("✅ Authentication successful");
                    println!();
                }
                Ok(false) => {
                    eprintln!("❌ Authentication failed: Invalid credentials");
                    eprintln!("Please check your credentials and try again.");
                    std::process::exit(1);
                }
                Err(e) => {
                    eprintln!("❌ Authentication failed: {}", e);
                    eprintln!("Please check your credentials and try again.");
                    std::process::exit(1);
                }
            }

            // Only proceed to TUI after successful authentication
            println!("🚀 Launching dashboard...");
            println!();

            // Create dashboard configuration
            let dashboard_config = dashboard::DashboardConfig::default();
            let mut init_errors = Vec::new();

            // Check/request microphone permission on macOS
            #[cfg(target_os = "macos")]
            {
                // Always assume we need to show permission errors on macOS since
                // the actual device access will likely fail until permission is granted
                let permission_result = permissions::ensure_microphone_permission(false);

                match permission_result {
                    Ok(_) => {
                        // Even if permission check "passes", we should prepare for device access failure
                        init_errors.push(dashboard::InitializationError::MicrophonePermission {
                            message: "Microphone permission may be required. If you see device errors, grant microphone access in System Preferences.".to_string(),
                        });
                    }
                    Err(e) => {
                        init_errors.push(dashboard::InitializationError::MicrophonePermission {
                            message: format!("Microphone permission denied: {}", e),
                        });
                    }
                }
            }

            // Try the dashboard with full functionality first, but if it fails,
            // fall back to error display mode immediately
            let dashboard_config = dashboard::DashboardConfig::default();
            match dashboard::Dashboard::new_with_errors(dashboard_config, init_errors.clone()) {
                Ok(dashboard) => {
                    // Run dashboard without timeout - it runs until user quits
                    // The dashboard.run() method is designed to run indefinitely
                    match dashboard.run().await {
                        Ok(()) => {
                            // Dashboard exited normally
                        }
                        Err(e) => {
                            // Dashboard failed with an error - show error in TUI
                            return show_dashboard_with_generic_error(&e.to_string()).await;
                        }
                    }
                }
                Err(e) => {
                    // Failed to create dashboard - show error in TUI
                    return show_dashboard_with_generic_error(&e.to_string()).await;
                }
            }
        }

        Some(Commands::Dev { action }) => {
            handle_dev_command(action).await?;
        }
    }
    Ok(())
}

async fn handle_dev_command(action: DevAction) -> Result<()> {
    match action {
        DevAction::Dashboard { skip_audio_check } => {
            info!("Starting dashboard...");

            // Create dashboard configuration
            let dashboard_config = dashboard::DashboardConfig::default();
            let mut init_errors = Vec::new();

            // Check/request microphone permission on macOS unless skipped
            #[cfg(target_os = "macos")]
            {
                if !skip_audio_check {
                    if let Err(e) = permissions::ensure_microphone_permission(false) {
                        init_errors.push(dashboard::InitializationError::MicrophonePermission {
                            message: format!("Microphone permission denied: {}", e),
                        });
                    }
                }
            }

            // Try to create and run dashboard, catch any errors and display them
            let result = async {
                // Create dashboard with or without errors
                let dashboard = if init_errors.is_empty() {
                    dashboard::Dashboard::new(dashboard_config.clone())?
                } else {
                    dashboard::Dashboard::new_with_errors(dashboard_config.clone(), init_errors)?
                };

                // Run the dashboard - errors will be displayed within the UI
                dashboard.run().await
            }.await;

            // Handle any errors that occurred during dashboard creation or running
            if let Err(e) = result {
                if !skip_audio_check {
                    // Check if it's a device error that should be shown in dashboard
                    let error_msg = e.to_string();
                    if error_msg.contains("os error 6") || error_msg.contains("Device not configured") {
                        // Create a new dashboard with just the microphone error
                        if let Ok(dashboard) = dashboard::Dashboard::new_with_errors(
                            dashboard_config,
                            vec![dashboard::InitializationError::MicrophonePermission {
                                message: "Microphone access required but permission denied".to_string(),
                            }]
                        ) {
                            // Try to run the dashboard again with error displayed
                            let _ = dashboard.run().await;
                        } else {
                            // Failed to create dashboard - error will be logged but not printed
                        }
                    } else {
                        // For other errors, try to create a dashboard with generic error
                        if let Ok(dashboard) = dashboard::Dashboard::new_with_errors(
                            dashboard_config,
                            vec![dashboard::InitializationError::Generic {
                                message: format!("Startup error: {}", e),
                            }]
                        ) {
                            let _ = dashboard.run().await;
                        } else {
                            // Failed to create dashboard - error will be logged but not printed
                        }
                    }
                } else {
                    return Err(e);
                }
            }
        }

        DevAction::VoiceBridge { skip_audio_check } => {
            info!("Starting MOSHI voice bridge...");

            // Check/request microphone permission on macOS unless skipped
            #[cfg(target_os = "macos")]
            {
                if !skip_audio_check {
                    if let Err(_) = permissions::ensure_microphone_permission(false) {
                        // Microphone permission failed - will be handled in TUI
                        std::process::exit(1);
                    }
                }
            }

            // Create voice bridge configuration
            let voice_config = voice::VoiceConfig::default();
            let supervisor_config = supervisor::SupervisorConfig::default();

            // Start voice bridge
            let voice_bridge = voice::VoiceBridge::new(voice_config.clone()).await?;
            let moshi_state = voice_bridge.get_moshi_state();
            let voice_bridge = Arc::new(voice_bridge);
            let voice_handle = {
                let voice_bridge = voice_bridge.clone();
                tokio::spawn(async move {
                    if let Err(_) = voice_bridge.start_server().await {
                        // Voice bridge error - will be logged but not printed to console
                    }
                })
            };

            // Start supervisor
            let supervisor = Arc::new(supervisor::SupervisorServer::new(supervisor_config.clone(), moshi_state));
            let supervisor_handle = tokio::spawn(async move {
                if let Err(_) = supervisor.start().await {
                    // Supervisor error - will be logged but not printed to console
                }
            });

            println!("🎤 MOSHI Voice Bridge started!");
            println!("Voice bridge: ws://{}:{}", voice_config.host, voice_config.port);
            println!("Supervisor: ws://{}:{}", supervisor_config.host, supervisor_config.port);
            println!("Press Ctrl+C to stop");

            tokio::try_join!(voice_handle, supervisor_handle)?;
        }

        DevAction::Daemon { skip_audio_check } => {
            info!("Starting daemon...");
            println!("🤖 xSwarm Daemon");
            println!("Coming soon: Background orchestration service");
        }

        // All other DevAction variants would be implemented here...
        _ => {
            println!("🚧 This dev command is not yet implemented in the simplified CLI");
            println!("Use the legacy commands for now.");
        }
    }

    Ok(())
}

// Handler stubs - these need proper implementations
async fn handle_calendar_command(_action: CalendarAction) -> Result<()> {
    println!("📅 Calendar commands not yet implemented in simplified CLI");
    Ok(())
}

async fn handle_appointment_command(_action: AppointmentAction) -> Result<()> {
    println!("📝 Appointment commands not yet implemented in simplified CLI");
    Ok(())
}

async fn handle_reminder_command(_action: ReminderAction) -> Result<()> {
    println!("⏰ Reminder commands not yet implemented in simplified CLI");
    Ok(())
}

async fn handle_boss_command(_action: BossAction) -> Result<()> {
    println!("👑 Boss commands not yet implemented in simplified CLI");
    Ok(())
}

async fn send_boss_message(_text: &str) -> Result<()> {
    println!("💬 Message sending not yet implemented in simplified CLI");
    Ok(())
}

// Helper function to show dashboard with device/microphone error
async fn show_dashboard_with_device_error() -> Result<()> {
    info!("Attempting to show dashboard with device error...");

    // All error messages will be displayed within the dashboard TUI interface
    // No console output to prevent interference with TUI

    // Try to create a minimal dashboard
    let dashboard_config = dashboard::DashboardConfig::default();
    let init_errors = vec![
        dashboard::InitializationError::MicrophonePermission {
            message: "Microphone access denied. Please grant microphone permission in System Preferences > Security & Privacy > Microphone and restart xSwarm.".to_string(),
        }
    ];

    match dashboard::Dashboard::new_with_errors(dashboard_config, init_errors) {
        Ok(dashboard) => {
            // Dashboard created successfully with errors - run TUI
            // Run without timeout - dashboard runs until user quits
            let _ = dashboard.run().await;
        }
        Err(_) => {
            // Failed to create dashboard - error will be logged but not printed to console
        }
    }

    Ok(())
}

// Helper function to show dashboard with generic error
async fn show_dashboard_with_generic_error(error_msg: &str) -> Result<()> {
    info!("Attempting to show dashboard with generic error: {}", error_msg);

    let dashboard_config = dashboard::DashboardConfig::default();
    let init_errors = vec![
        dashboard::InitializationError::Generic {
            message: format!("Startup error: {}", error_msg),
        }
    ];

    match dashboard::Dashboard::new_with_errors(dashboard_config, init_errors) {
        Ok(dashboard) => {
            // Run without timeout - dashboard runs until user quits
            let _ = dashboard.run().await;
        }
        Err(_) => {
            // Failed to create dashboard - error will be logged but not printed to console
        }
    }

    Ok(())
}