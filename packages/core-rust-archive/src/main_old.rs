mod ai;
mod audio;
mod calendar_view;
mod claude_code;
mod client;
mod config;
mod dashboard;
mod docs;
mod permissions;
mod platform;
mod scheduler;
mod server_client;
mod supervisor;
mod tts;
mod voice;

use anyhow::Result;
use chrono::Datelike;
use clap::{Parser, Subcommand};
use std::sync::Arc;
use tracing::{info, warn, Level};
use tracing_subscriber;

use crate::ai::{AiClient, Message, Role, VoiceClient};
use crate::config::Config;

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

// ============================================================================
// CALENDAR COMMAND HANDLERS
// ============================================================================

async fn handle_calendar_command(action: CalendarAction) -> Result<()> {
    use calendar_view::{CalendarViewConfig, OutputFormat};

    let format = match action {
        CalendarAction::Day { ref format, .. } |
        CalendarAction::Week { ref format, .. } |
        CalendarAction::Month { ref format, .. } => {
            match format.to_lowercase().as_str() {
                "json" => OutputFormat::Json,
                "plain" => OutputFormat::Plain,
                _ => OutputFormat::Terminal,
            }
        }
    };

    let config = CalendarViewConfig {
        format,
        ..Default::default()
    };

    // For now, use mock data. In production, this would fetch from server
    let appointments = vec![]; // TODO: Fetch from server

    match action {
        CalendarAction::Day { date, .. } => {
            let parsed_date = calendar_view::parse_date_string(&date)?;
            let output = calendar_view::render_day_view(parsed_date, &appointments, &config)?;
            println!("{}", output);
        }
        CalendarAction::Week { date, .. } => {
            let parsed_date = calendar_view::parse_date_string(&date)?;
            let output = calendar_view::render_week_view(parsed_date, &appointments, &config)?;
            println!("{}", output);
        }
        CalendarAction::Month { year, month, .. } => {
            let output = calendar_view::render_month_view(year, month, &appointments, &config)?;
            println!("{}", output);
        }
    }

    println!("\n⚠️  Note: Calendar data requires server connection.");
    println!("   Showing empty calendar. Use API to sync appointments.");

    Ok(())
}

async fn handle_appointment_command(action: AppointmentAction) -> Result<()> {
    // Create scheduler (default to UTC timezone)
    let scheduler = scheduler::Scheduler::new(
        "user1".to_string(), // TODO: Get from config/identity
        "UTC".to_string(),
    );

    match action {
        AppointmentAction::Create { title, start, end, description, location, reminder } => {
            println!("📅 Creating appointment: {}", title);

            // Parse start and end times
            let start_time = parse_time_input(&start, &scheduler)?;
            let end_time = parse_time_input(&end, &scheduler)?;

            // Validate times
            if end_time <= start_time {
                anyhow::bail!("End time must be after start time");
            }

            // Create appointment using scheduler
            let request = scheduler::ScheduleRequest {
                raw_text: format!("Create appointment: {}", title),
                action: scheduler::ScheduleAction::Create,
                title: Some(title.clone()),
                when: Some(scheduler::ScheduleTime::Absolute(start_time)),
                duration: Some(end_time - start_time),
                location: location.clone(),
                participants: vec![],
                recurrence: None,
            };

            match scheduler.create_appointment(request) {
                Ok(mut appointment) => {
                    // Add description and reminder after creation
                    if let Some(desc) = description {
                        appointment.description = Some(desc);
                    }

                    if let Some(rem) = reminder {
                        appointment.reminder_minutes = Some(rem);
                    }

                    println!("\n✅ Appointment created:");
                    println!("   ID: {}", appointment.id);
                    println!("   Title: {}", appointment.title);
                    println!("   Start: {}", appointment.start_time.format("%Y-%m-%d %H:%M %Z"));
                    println!("   End: {}", appointment.end_time.format("%Y-%m-%d %H:%M %Z"));

                    if let Some(desc) = &appointment.description {
                        println!("   Description: {}", desc);
                    }

                    if let Some(loc) = &appointment.location {
                        println!("   Location: {}", loc);
                    }

                    if let Some(rem) = &appointment.reminder_minutes {
                        println!("   Reminder: {} minutes before", rem);
                    }

                    println!("\n⚠️  Note: Appointment created locally. Save to database via API.");
                }
                Err(e) => {
                    anyhow::bail!("Failed to create appointment: {}", e);
                }
            }
        }
        AppointmentAction::List { from, to, user, format: _ } => {
            println!("📋 Listing appointments");

            if let Some(from_date) = from {
                println!("   From: {}", from_date);
            }
            if let Some(to_date) = to {
                println!("   To: {}", to_date);
            }
            if let Some(user_id) = user {
                println!("   User: {}", user_id);
            }

            println!("\n⚠️  Note: Listing requires server connection.");
            println!("   Use: curl http://localhost:8787/api/appointments?user_id=xxx");
        }
        AppointmentAction::Update { id, title, start, end, description, location } => {
            println!("📝 Updating appointment: {}", id);

            // Build update request
            let has_updates = title.is_some() || start.is_some() || end.is_some()
                || description.is_some() || location.is_some();

            if !has_updates {
                anyhow::bail!("No updates specified. Use --title, --start, --end, --description, or --location");
            }

            if let Some(t) = title {
                println!("   New title: {}", t);
            }
            if let Some(s) = start {
                println!("   New start: {}", s);
            }
            if let Some(e) = end {
                println!("   New end: {}", e);
            }

            println!("\n⚠️  Note: Update requires server connection.");
            println!("   Use: curl -X PUT http://localhost:8787/api/appointments/{}", id);
        }
        AppointmentAction::Delete { id, yes } => {
            if !yes {
                println!("⚠️  Are you sure you want to delete appointment {}? Use -y to confirm.", id);
                return Ok(());
            }

            println!("🗑️  Deleting appointment: {}", id);
            println!("\n⚠️  Note: Delete requires server connection.");
            println!("   Use: curl -X DELETE http://localhost:8787/api/appointments/{}", id);
        }
        AppointmentAction::Show { id } => {
            println!("🔍 Showing appointment: {}", id);
            println!("\n⚠️  Note: Fetch requires server connection.");
            println!("   Use: curl http://localhost:8787/api/appointments/{}", id);
        }
    }

    Ok(())
}

async fn handle_reminder_command(action: ReminderAction) -> Result<()> {
    let scheduler = scheduler::Scheduler::new(
        "user1".to_string(), // TODO: Get from config/identity
        "UTC".to_string(),
    );

    match action {
        ReminderAction::Create { title, time, priority, description } => {
            println!("⏰ Creating reminder: {}", title);

            let due_time = parse_time_input(&time, &scheduler)?;

            let reminder_priority = match priority {
                1 => scheduler::ReminderPriority::High,
                5 => scheduler::ReminderPriority::Low,
                _ => scheduler::ReminderPriority::Normal,
            };

            match scheduler.create_reminder(title.clone(), due_time, reminder_priority) {
                Ok(mut reminder) => {
                    if let Some(desc) = description {
                        reminder.description = Some(desc);
                    }

                    println!("\n✅ Reminder created:");
                    println!("   ID: {}", reminder.id);
                    println!("   Title: {}", reminder.title);
                    println!("   Due: {}", reminder.due_time.format("%Y-%m-%d %H:%M %Z"));
                    println!("   Priority: {:?}", reminder.priority);

                    if let Some(desc) = &reminder.description {
                        println!("   Description: {}", desc);
                    }

                    println!("\n⚠️  Note: Reminder created locally. Save to database via API.");
                }
                Err(e) => {
                    anyhow::bail!("Failed to create reminder: {}", e);
                }
            }
        }
        ReminderAction::List { due, user, completed, format: _ } => {
            println!("📋 Listing reminders");

            if let Some(due_date) = due {
                println!("   Due: {}", due_date);
            }
            if let Some(user_id) = user {
                println!("   User: {}", user_id);
            }
            if completed {
                println!("   Including completed reminders");
            }

            println!("\n⚠️  Note: Listing requires server connection.");
            println!("   Use: curl http://localhost:8787/api/reminders?user_id=xxx");
        }
        ReminderAction::ForAppointment { appointment_id, minutes_before } => {
            println!("⏰ Creating reminder for appointment: {}", appointment_id);
            println!("   {} minutes before appointment", minutes_before);

            println!("\n⚠️  Note: Creating appointment reminder requires server connection.");
            println!("   Use: curl -X POST http://localhost:8787/api/appointments/{}/reminder", appointment_id);
        }
        ReminderAction::Complete { id } => {
            println!("✅ Marking reminder as complete: {}", id);

            println!("\n⚠️  Note: Update requires server connection.");
            println!("   Use: curl -X PUT http://localhost:8787/api/reminders/{}/complete", id);
        }
        ReminderAction::Delete { id, yes } => {
            if !yes {
                println!("⚠️  Are you sure you want to delete reminder {}? Use -y to confirm.", id);
                return Ok(());
            }

            println!("🗑️  Deleting reminder: {}", id);
            println!("\n⚠️  Note: Delete requires server connection.");
            println!("   Use: curl -X DELETE http://localhost:8787/api/reminders/{}", id);
        }
    }

    Ok(())
}

/// Parse time input (supports ISO 8601, natural language, relative times)
fn parse_time_input(input: &str, scheduler: &scheduler::Scheduler) -> Result<chrono::DateTime<chrono::Utc>> {
    use chrono::{DateTime, Duration, Utc};

    // Try ISO 8601 first
    if let Ok(dt) = DateTime::parse_from_rfc3339(input) {
        return Ok(dt.with_timezone(&Utc));
    }

    // Try common date formats
    if let Ok(dt) = chrono::NaiveDateTime::parse_from_str(input, "%Y-%m-%d %H:%M") {
        return Ok(Utc::now().date_naive().and_time(dt.time()).and_utc());
    }

    // Try natural language via scheduler
    match scheduler.parse_natural_language(&format!("meeting {}", input)) {
        Ok(request) => {
            if let Some(scheduler::ScheduleTime::Absolute(dt)) = request.when {
                Ok(dt)
            } else if let Some(scheduler::ScheduleTime::Relative(rel)) = request.when {
                let now = Utc::now();
                let duration = match rel.unit {
                    scheduler::TimeUnit::Minutes => Duration::minutes(rel.amount),
                    scheduler::TimeUnit::Hours => Duration::hours(rel.amount),
                    scheduler::TimeUnit::Days => Duration::days(rel.amount),
                    scheduler::TimeUnit::Weeks => Duration::weeks(rel.amount),
                    scheduler::TimeUnit::Months => Duration::days(rel.amount * 30),
                };
                Ok(now + duration)
            } else {
                anyhow::bail!("Could not parse time: {}", input)
            }
        }
        Err(_) => {
            anyhow::bail!(
                "Could not parse time: {}. Use ISO 8601 (2024-01-15T14:30:00Z) or natural language (tomorrow at 2pm)",
                input
            )
        }
    }
}

// ============================================================================
// BOSS AI CLIENT COMMAND HANDLERS
// ============================================================================

/// Send a message to Boss AI via the simple message router
async fn send_boss_message(text: &str) -> Result<()> {
    use crate::client::{BossClient, BossClientConfig};

    println!("📤 Sending message to Boss AI...\n");

    // Build client config
    let server_url = std::env::var("BOSS_SERVER_URL")
        .unwrap_or_else(|_| "http://localhost:8787".to_string());

    // Use phone from environment or config, or default to "admin"
    let from = std::env::var("ADMIN_PHONE")
        .or_else(|_| std::env::var("XSWARM_ADMIN_PHONE"))
        .unwrap_or_else(|_| "admin".to_string());

    let client_config = BossClientConfig {
        server_url: server_url.clone(),
        api_path: "/api/message".to_string(),
        channel: "cli".to_string(),
        from,
    };

    // Create client
    let client = BossClient::new(client_config)?;

    // Check if server is reachable
    if !client.health_check().await? {
        eprintln!("❌ Boss AI server is not reachable at {}", server_url);
        eprintln!("\nMake sure the server is running:");
        eprintln!("  cd packages/server");
        eprintln!("  npm run dev");
        eprintln!("\nOr set BOSS_SERVER_URL environment variable to the correct URL.");
        std::process::exit(1);
    }

    // Send message
    match client.send_message(text).await {
        Ok(response) => {
            println!("💬 Boss AI:\n{}\n", response);
        }
        Err(e) => {
            eprintln!("❌ Error: {}", e);
            std::process::exit(1);
        }
    }

    Ok(())
}

/// Handle Boss AI subcommands
async fn handle_boss_command(action: BossAction) -> Result<()> {
    match action {
        BossAction::Message { text } => {
            send_boss_message(&text).await?;
        }
        BossAction::Calendar => {
            send_boss_message("show my calendar today").await?;
        }
        BossAction::Reminders => {
            send_boss_message("list my reminders").await?;
        }
    }
    Ok(())
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

    // Handle subcommands
    match cli.command {
        Some(Commands::Start) | None => {
            info!("Starting xSwarm daemon and dashboard...");
            println!("🎤 xSwarm Voice-First AI Assistant");
            println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
            println!();
            println!("Welcome! Talk to your AI assistant:");
            println!("  \"Hey HAL, what's on my calendar today?\"");
            println!("  \"Schedule a meeting tomorrow at 2pm\"");
            println!("  \"Create a reminder to call John at 5pm\"");
            println!();
            println!("🖥️  Opening dashboard for visual monitoring...");

            // TODO: Check if daemon is already running and connect to it
            // TODO: If not running, start the daemon
            // TODO: Launch the dashboard interface

            // For now, launch the dashboard
            // Check/request microphone permission on macOS
            #[cfg(target_os = "macos")]
            {
                if let Err(e) = permissions::ensure_microphone_permission(false) {
                    eprintln!("❌ Dashboard requires microphone permission due to terminal device scanning: {}", e);
                    eprintln!();
                    eprintln!("This is needed because the terminal library scans audio devices (including Bluetooth).");
                    eprintln!("Please grant microphone permission in System Settings > Privacy & Security > Microphone");
                    std::process::exit(1);
                }
            }

            // Create dashboard configuration
            let dashboard_config = dashboard::DashboardConfig::default();

            // Create and run dashboard
            let dashboard = dashboard::Dashboard::new(dashboard_config)?;

            // Try to run the dashboard, catching device permission errors gracefully
            match dashboard.run().await {
                Ok(_) => {}
                Err(e) => {
                    let error_msg = e.to_string();
                    // Check for the specific "Device not configured" error (macOS permission issue)
                    if error_msg.contains("os error 6") || error_msg.contains("Device not configured") {
                        eprintln!("\n❌ Dashboard Failed to Start - Permission Error");
                        eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                        eprintln!();
                        eprintln!("The dashboard requires microphone permission to run because");
                        eprintln!("the terminal UI library scans Bluetooth devices.");
                        eprintln!();
                        eprintln!("🔧 To fix this:");
                        eprintln!();
                        eprintln!("  1. Open System Settings (or System Preferences)");
                        eprintln!("  2. Go to: Privacy & Security → Microphone");
                        eprintln!("  3. Find and enable your terminal application:");
                        eprintln!("     • Terminal.app");
                        eprintln!("     • iTerm2");
                        eprintln!("     • VS Code");
                        eprintln!("     • Or whatever app you're running this from");
                        eprintln!("  4. Restart xswarm");
                        eprintln!();
                        eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                        std::process::exit(1);
                    } else {
                        // For other errors, just propagate them
                        return Err(e);
                    }
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

            // Check/request microphone permission on macOS
            // This is required because crossterm's enable_raw_mode() scans Bluetooth audio devices
            #[cfg(target_os = "macos")]
            {
                if let Err(e) = permissions::ensure_microphone_permission(false) {
                    eprintln!("❌ Dashboard requires microphone permission due to terminal device scanning: {}", e);
                    eprintln!();
                    eprintln!("This is needed because the terminal library scans audio devices (including Bluetooth).");
                    eprintln!("Please grant microphone permission in System Settings > Privacy & Security > Microphone");
                    std::process::exit(1);
                }
            }

            // Create dashboard configuration
            let dashboard_config = dashboard::DashboardConfig::default();

            // Create and run dashboard
            let dashboard = dashboard::Dashboard::new(dashboard_config)?;

            // Try to run the dashboard, catching device permission errors gracefully
            match dashboard.run().await {
                Ok(_) => {}
                Err(e) => {
                    let error_msg = e.to_string();

                    // Check for the specific "Device not configured" error (macOS permission issue)
                    if error_msg.contains("os error 6") || error_msg.contains("Device not configured") {
                        eprintln!("\n❌ Dashboard Failed to Start - Permission Error");
                        eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                        eprintln!();
                        eprintln!("The dashboard requires microphone permission to run because");
                        eprintln!("the terminal UI library scans Bluetooth devices.");
                        eprintln!();
                        eprintln!("🔧 To fix this:");
                        eprintln!();
                        eprintln!("  1. Open System Settings (or System Preferences)");
                        eprintln!("  2. Go to: Privacy & Security → Microphone");
                        eprintln!("  3. Find and enable your terminal application:");
                        eprintln!("     • Terminal.app");
                        eprintln!("     • iTerm2");
                        eprintln!("     • Visual Studio Code");
                        eprintln!("     • Or whichever app you're running this from");
                        eprintln!("  4. Restart this application");
                        eprintln!();
                        eprintln!("💡 Note: If you're running from VS Code, you need to:");
                        eprintln!("     • Quit VS Code completely");
                        eprintln!("     • Enable 'Visual Studio Code' in Microphone settings");
                        eprintln!("     • Restart VS Code");
                        eprintln!();
                        eprintln!("Technical details: {}", error_msg);
                        eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n");
                        std::process::exit(1);
                    } else {
                        // For other errors, just propagate them
                        return Err(e);
                    }
                }
            }
        }

        DevAction::VoiceBridge { skip_audio_check } => {
            info!("Starting MOSHI voice bridge...");

            // Check/request microphone permission on macOS unless skipped
            #[cfg(target_os = "macos")]
            {
                if !skip_audio_check {
                    if let Err(e) = permissions::ensure_microphone_permission(false) {
                        eprintln!("❌ Failed to ensure microphone permission: {}", e);
                        std::process::exit(1);
                    }
                }
            }

            // Create voice bridge configuration
            let voice_config = voice::VoiceConfig::default();
            let supervisor_config = supervisor::SupervisorConfig::default();

            // Start voice bridge
            let voice_bridge = voice::VoiceBridge::new(voice_config.clone()).await?;
            let voice_handle = tokio::spawn(async move {
                if let Err(e) = voice_bridge.run().await {
                    eprintln!("❌ Voice bridge error: {}", e);
                }
            });

            // Start supervisor
            let supervisor = supervisor::Supervisor::new(supervisor_config.clone())?;
            let supervisor_handle = tokio::spawn(async move {
                if let Err(e) = supervisor.run().await {
                    eprintln!("❌ Supervisor error: {}", e);
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

            // Index documentation on startup
            info!("Indexing documentation...");
            let mut indexer = docs::DocsIndexer::new()?;
            indexer.index().await?;
            info!("Documentation indexed: {} pages", indexer.pages().len());

            println!("Coming soon: Background orchestration service");
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
        Commands::VoiceBridge { host, port, supervisor_port, enable_claude_code, claude_code_url } => {
            info!("Starting MOSHI voice bridge...");

            // Check/request microphone permission on macOS
            #[cfg(target_os = "macos")]
            {
                if let Err(e) = permissions::ensure_microphone_permission(false) {
                    eprintln!("❌ Failed to ensure microphone permission: {}", e);
                    std::process::exit(1);
                }
            }

            // Create voice bridge configuration
            let mut voice_config = voice::VoiceConfig::default();
            voice_config.host = host;
            voice_config.port = port;

            // Create supervisor configuration
            let mut supervisor_config = supervisor::SupervisorConfig::default();
            supervisor_config.host = voice_config.host.clone();
            supervisor_config.port = supervisor_port;

            // Save values for printing later (before moving the configs)
            let voice_host = voice_config.host.clone();
            let voice_port = voice_config.port;
            let supervisor_host = supervisor_config.host.clone();
            let supervisor_port_val = supervisor_config.port;

            info!(
                voice_host = %voice_host,
                voice_port = voice_port,
                supervisor_port = supervisor_port_val,
                claude_code_enabled = enable_claude_code,
                "Initializing voice bridge and supervisor"
            );

            // Initialize voice bridge
            let voice_bridge = Arc::new(
                voice::VoiceBridge::new(voice_config)
                    .await
                    .expect("Failed to initialize voice bridge")
            );

            // Get shared MOSHI state for supervisor
            let moshi_state = voice_bridge.get_moshi_state();

            // Create server client for user identity
            let server_config = crate::config::ServerConfig::default();
            let server_client = match crate::server_client::ServerClient::new(server_config) {
                Ok(client) => {
                    info!("Server client initialized for user identity");
                    Some(Arc::new(client))
                }
                Err(e) => {
                    warn!(error = ?e, "Failed to initialize server client - running without user identity");
                    None
                }
            };

            // Create supervisor server with optional Claude Code integration
            let supervisor_server = if let Some(ref client) = server_client {
                let mut server = supervisor::SupervisorServer::with_server_client(
                    supervisor_config,
                    moshi_state,
                    client.clone()
                );

                // Enable Claude Code if requested
                if enable_claude_code {
                    info!(
                        url = %claude_code_url,
                        "Enabling Claude Code integration for Admin message routing"
                    );

                    let claude_config = crate::claude_code::ClaudeCodeConfig {
                        websocket_url: claude_code_url.clone(),
                        auth_token: std::env::var("CLAUDE_CODE_AUTH_TOKEN").ok(),
                        max_sessions: 10,
                        idle_timeout_seconds: 300,
                        track_costs: true,
                    };

                    server = server.with_claude_code(claude_config);

                    println!("🤖 Claude Code integration enabled");
                    println!("   Admin messages will be routed to Claude Code at: {}", claude_code_url);
                }

                Arc::new(server)
            } else {
                Arc::new(supervisor::SupervisorServer::new(supervisor_config, moshi_state))
            };

            info!("Voice bridge and supervisor initialized successfully");

            // Start both servers concurrently
            let voice_handle = {
                let bridge = voice_bridge.clone();
                tokio::spawn(async move {
                    info!("Starting voice bridge server...");
                    if let Err(e) = bridge.start_server().await {
                        eprintln!("❌ Voice bridge error: {}", e);
                        std::process::exit(1);
                    }
                })
            };

            let supervisor_handle = {
                let server = supervisor_server.clone();
                tokio::spawn(async move {
                    info!("Starting supervisor server...");
                    if let Err(e) = server.start().await {
                        eprintln!("❌ Supervisor error: {}", e);
                        std::process::exit(1);
                    }
                })
            };

            println!("🎤 MOSHI Voice Bridge is running!");
            println!();
            println!("📞 Voice WebSocket: ws://{}:{}", voice_host, voice_port);
            println!("🔧 Supervisor WebSocket: ws://{}:{}", supervisor_host, supervisor_port_val);
            println!();
            println!("Press Ctrl+C to stop");

            // Wait for both servers (they run forever until interrupted)
            tokio::try_join!(voice_handle, supervisor_handle)?;
        }
        Commands::Claude { action } => {
            info!("Claude Code integration command");

            // Import claude_code module types
            use xswarm::claude_code::{ClaudeCodeConnector, ClaudeCodeConfig};

            // Initialize Claude Code connector
            let config = ClaudeCodeConfig::default();
            let connector = Arc::new(ClaudeCodeConnector::new(config));

            match action {
                ClaudeAction::Connect { session_id } => {
                    println!("🔌 Connecting to Claude Code session: {}", session_id);

                    match connector.connect_session(&session_id).await {
                        Ok(_) => {
                            println!("✅ Connected to session {}", session_id);
                            println!("Session is ready for communication");
                        }
                        Err(e) => {
                            eprintln!("❌ Failed to connect: {}", e);
                            std::process::exit(1);
                        }
                    }
                }
                ClaudeAction::Status { session_id } => {
                    println!("📊 Claude Code Session Status\n");

                    if let Some(sid) = session_id {
                        // Show specific session
                        if let Some(session) = connector.get_session(&sid).await {
                            println!("Session ID: {}", session.id);
                            println!("User ID: {}", session.user_id);
                            println!("Project: {}", session.project_path);
                            println!("Status: {:?}", session.status);
                            println!("Messages: {}", session.message_count);
                            println!("Cost: ${:.4}", session.cost_usd);
                            println!("Duration: {}s", session.duration_seconds());
                            println!("Started: {}", session.started_at);
                            if let Some(ended) = session.ended_at {
                                println!("Ended: {}", ended);
                            }
                        } else {
                            eprintln!("❌ Session not found: {}", sid);
                            std::process::exit(1);
                        }
                    } else {
                        // Show all active sessions
                        let sessions = connector.get_active_sessions().await;
                        if sessions.is_empty() {
                            println!("No active sessions");
                        } else {
                            println!("Active sessions: {}\n", sessions.len());
                            for session in sessions {
                                println!("  {} - {} ({:?})",
                                    session.id,
                                    session.user_id,
                                    session.status
                                );
                                println!("    Messages: {}, Cost: ${:.4}",
                                    session.message_count,
                                    session.cost_usd
                                );
                                println!();
                            }
                        }
                    }
                }
                ClaudeAction::Cost { user_id } => {
                    println!("💰 Claude Code Cost Tracking\n");

                    if let Some(uid) = user_id {
                        // Show cost for specific user
                        let total_cost = connector.get_user_total_cost(&uid).await;
                        let sessions = connector.get_user_sessions(&uid).await;

                        println!("User: {}", uid);
                        println!("Total sessions: {}", sessions.len());
                        println!("Total cost: ${:.4}\n", total_cost);

                        if !sessions.is_empty() {
                            println!("Session breakdown:");
                            for session in sessions {
                                println!("  {} - ${:.4} ({} messages)",
                                    session.id,
                                    session.cost_usd,
                                    session.message_count
                                );
                            }
                        }
                    } else {
                        // Show total costs across all users
                        let sessions = connector.get_active_sessions().await;
                        let total_cost: f64 = sessions.iter().map(|s| s.cost_usd).sum();

                        println!("Total active sessions: {}", sessions.len());
                        println!("Total cost: ${:.4}", total_cost);
                    }
                }
            }
        }
        Commands::Calendar { action } => {
            handle_calendar_command(action).await?;
        }
        Commands::Appointment { action } => {
            handle_appointment_command(action).await?;
        }
        Commands::Reminder { action } => {
            handle_reminder_command(action).await?;
        }
        Commands::Message { text } => {
            send_boss_message(&text).await?;
        }
        Commands::Boss { action } => {
            handle_boss_command(action).await?;
        }
    }

    Ok(())
}
