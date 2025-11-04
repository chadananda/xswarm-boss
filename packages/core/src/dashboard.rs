// Dashboard Module - Real-Time TUI Monitoring
//
// This module provides a terminal user interface (TUI) for monitoring
// xSwarm Boss activity in real-time:
// - SMS/Email/Voice call activity from server webhooks
// - Voice bridge and supervisor WebSocket status
// - Server health and user identity
// - Live event feed from supervisor

use anyhow::{Context, Result};
use crossterm::{
    event::{self, Event, KeyCode, KeyModifiers},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame, Terminal,
};
use std::env;
use std::io;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{RwLock, mpsc};
use tokio_tungstenite::{connect_async, tungstenite::Message as WsMessage};
use futures_util::{StreamExt, SinkExt};
use tracing::{info, warn, error};
use chrono::{DateTime, Local};

use crate::server_client::{ServerClient, ServerConfig, UserIdentity};
use crate::supervisor::SupervisorEvent;
use crate::audio_visualizer::{AudioVisualizer, VisualizerState, AudioLevel};

/// Maximum number of events to keep in activity feed
const MAX_ACTIVITY_EVENTS: usize = 50;

/// Global flag to track if terminal cleanup has been performed
static TERMINAL_CLEANED: AtomicBool = AtomicBool::new(false);

/// RAII guard for terminal cleanup
/// This ensures terminal is restored even on panic or early exit
struct TerminalGuard {
    cleaned: bool,
}

impl TerminalGuard {
    fn new() -> Result<Self> {
        // Check if we have a TTY before trying to enable raw mode
        use std::io::IsTerminal;

        if io::stdout().is_terminal() {
            // Setup terminal
            enable_raw_mode()?;
            let mut stdout = io::stdout();
            execute!(stdout, EnterAlternateScreen)?;
        } else {
            // No TTY available (output redirected) - skip terminal setup
            info!("No TTY detected, skipping terminal raw mode setup");
        }

        // Install panic hook to ensure cleanup on panic
        let default_panic = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |info| {
            // Clean up terminal before panic message
            let _ = TerminalGuard::cleanup_terminal();
            default_panic(info);
        }));

        Ok(Self { cleaned: false })
    }

    fn cleanup_terminal() -> Result<()> {
        // Only cleanup once
        if TERMINAL_CLEANED.swap(true, Ordering::SeqCst) {
            return Ok(());
        }

        // Check if we have a TTY before trying to cleanup
        use std::io::IsTerminal;

        if !io::stdout().is_terminal() {
            // No TTY, nothing to cleanup
            return Ok(());
        }

        // Restore terminal to normal mode
        // Use unwrap_or(()) pattern to ensure all steps execute
        disable_raw_mode().unwrap_or(());

        let mut stdout = io::stdout();
        execute!(
            stdout,
            LeaveAlternateScreen
        ).unwrap_or(());

        // Additional flush to ensure everything is written
        use std::io::Write;
        let _ = stdout.flush();

        Ok(())
    }
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        if !self.cleaned {
            let _ = Self::cleanup_terminal();
            self.cleaned = true;
        }
    }
}

/// Check if dev mode is active
/// Returns true if XSWARM_DEV_ADMIN_EMAIL and XSWARM_DEV_ADMIN_PASS are both present and valid
fn is_dev_mode() -> bool {
    let dev_email = env::var("XSWARM_DEV_ADMIN_EMAIL").ok();
    let dev_password = env::var("XSWARM_DEV_ADMIN_PASS").ok();

    // Both must be present
    if dev_email.is_none() || dev_password.is_none() {
        return false;
    }

    let dev_password = dev_password.unwrap();

    // Password must not be empty
    if dev_password.is_empty() {
        return false;
    }

    true
}

/// Activity event types for the feed
#[derive(Debug, Clone)]
pub enum ActivityEvent {
    SmsReceived { from: String, message: String, time: DateTime<Local> },
    SmsSent { to: String, message: String, time: DateTime<Local> },
    EmailReceived { from: String, subject: String, time: DateTime<Local> },
    EmailSent { to: String, subject: String, time: DateTime<Local> },
    VoiceCallIncoming { from: String, time: DateTime<Local> },
    VoiceCallOutgoing { to: String, time: DateTime<Local> },
    UserSpeech { duration_ms: u64, time: DateTime<Local> },
    UserTranscription { text: String, time: DateTime<Local> },
    SuggestionApplied { text: String, time: DateTime<Local> },
    SynthesisComplete { text: String, duration_ms: u64, time: DateTime<Local> },
    SystemEvent { message: String, time: DateTime<Local> },
    Error { message: String, time: DateTime<Local> },
}

/// Initialization error types
#[derive(Debug, Clone)]
pub enum InitializationError {
    MicrophonePermission { message: String },
    ServerConnection { message: String },
    Configuration { message: String },
    AudioDevice { message: String },
    Generic { message: String },
}

impl ActivityEvent {
    fn to_list_item(&self) -> ListItem {
        let (icon, text, style) = match self {
            ActivityEvent::SmsReceived { from, message, time } => (
                "📱",
                format!("{} SMS from {}: {}",
                    time.format("%H:%M:%S"),
                    from,
                    truncate_string(message, 40)
                ),
                Style::default().fg(Color::Cyan),
            ),
            ActivityEvent::SmsSent { to, message, time } => (
                "📤",
                format!("{} SMS to {}: {}",
                    time.format("%H:%M:%S"),
                    to,
                    truncate_string(message, 40)
                ),
                Style::default().fg(Color::Blue),
            ),
            ActivityEvent::EmailReceived { from, subject, time } => (
                "📧",
                format!("{} Email from {}: {}",
                    time.format("%H:%M:%S"),
                    from,
                    truncate_string(subject, 40)
                ),
                Style::default().fg(Color::Green),
            ),
            ActivityEvent::EmailSent { to, subject, time } => (
                "📨",
                format!("{} Email to {}: {}",
                    time.format("%H:%M:%S"),
                    to,
                    truncate_string(subject, 40)
                ),
                Style::default().fg(Color::LightGreen),
            ),
            ActivityEvent::VoiceCallIncoming { from, time } => (
                "📞",
                format!("{} Voice call from {}",
                    time.format("%H:%M:%S"),
                    from
                ),
                Style::default().fg(Color::Magenta),
            ),
            ActivityEvent::VoiceCallOutgoing { to, time } => (
                "📞",
                format!("{} Voice call to {}",
                    time.format("%H:%M:%S"),
                    to
                ),
                Style::default().fg(Color::LightMagenta),
            ),
            ActivityEvent::UserSpeech { duration_ms, time } => (
                "🎤",
                format!("{} User spoke for {}ms",
                    time.format("%H:%M:%S"),
                    duration_ms
                ),
                Style::default().fg(Color::Yellow),
            ),
            ActivityEvent::UserTranscription { text, time } => (
                "💬",
                format!("{} User said: {}",
                    time.format("%H:%M:%S"),
                    truncate_string(text, 50)
                ),
                Style::default().fg(Color::LightYellow),
            ),
            ActivityEvent::SuggestionApplied { text, time } => (
                "💡",
                format!("{} AI suggestion: {}",
                    time.format("%H:%M:%S"),
                    truncate_string(text, 40)
                ),
                Style::default().fg(Color::LightCyan),
            ),
            ActivityEvent::SynthesisComplete { text, duration_ms, time } => (
                "🔊",
                format!("{} AI spoke ({}ms): {}",
                    time.format("%H:%M:%S"),
                    duration_ms,
                    truncate_string(text, 40)
                ),
                Style::default().fg(Color::LightBlue),
            ),
            ActivityEvent::SystemEvent { message, time } => (
                "ℹ️",
                format!("{} {}",
                    time.format("%H:%M:%S"),
                    message
                ),
                Style::default().fg(Color::White),
            ),
            ActivityEvent::Error { message, time } => (
                "❌",
                format!("{} ERROR: {}",
                    time.format("%H:%M:%S"),
                    message
                ),
                Style::default().fg(Color::Red),
            ),
        };

        ListItem::new(Line::from(vec![
            Span::raw(icon),
            Span::raw(" "),
            Span::styled(text, style),
        ]))
    }
}

/// Statistics for the dashboard
#[derive(Debug, Clone, Default)]
pub struct DashboardStats {
    pub sms_received_today: u32,
    pub sms_sent_today: u32,
    pub emails_received_today: u32,
    pub emails_sent_today: u32,
    pub voice_calls_today: u32,
    pub voice_minutes_today: u32,
}

/// Dashboard state
pub struct DashboardState {
    /// Activity events feed
    activity_events: Vec<ActivityEvent>,
    /// Statistics
    stats: DashboardStats,
    /// User identity from server
    user_identity: Option<UserIdentity>,
    /// Server connection status
    server_connected: bool,
    /// Supervisor WebSocket connection status
    supervisor_connected: bool,
    /// Voice bridge status
    voice_bridge_online: bool,
    /// Last update timestamp
    last_update: Instant,
    /// Initialization errors that need user attention
    init_errors: Vec<InitializationError>,
    /// Show error recovery panel
    show_error_panel: bool,
    /// Development mode indicator
    dev_mode: bool,
    /// Voice system activation state (user initiated)
    voice_system_starting: bool,
    /// Audio visualizer for MOSHI output
    moshi_visualizer: AudioVisualizer,
    /// Audio visualizer for microphone input
    mic_visualizer: AudioVisualizer,
    /// Current MOSHI audio level
    current_moshi_level: f32,
    /// Current microphone audio level
    current_mic_level: f32,
}

impl DashboardState {
    fn new() -> Self {
        Self {
            activity_events: Vec::new(),
            stats: DashboardStats::default(),
            user_identity: None,
            server_connected: false,
            supervisor_connected: false,
            voice_bridge_online: false,
            last_update: Instant::now(),
            init_errors: Vec::new(),
            show_error_panel: false,
            dev_mode: is_dev_mode(),
            voice_system_starting: false,
            moshi_visualizer: AudioVisualizer::new(20, 4),
            mic_visualizer: AudioVisualizer::new(20, 4),
            current_moshi_level: 0.0,
            current_mic_level: 0.0,
        }
    }

    fn add_initialization_error(&mut self, error: InitializationError) {
        self.init_errors.push(error);
        self.show_error_panel = true;
        self.last_update = Instant::now();
    }

    fn clear_errors(&mut self) {
        self.init_errors.clear();
        self.show_error_panel = false;
        self.last_update = Instant::now();
    }

    fn add_event(&mut self, event: ActivityEvent) {
        // Update statistics based on event type
        match &event {
            ActivityEvent::SmsReceived { .. } => self.stats.sms_received_today += 1,
            ActivityEvent::SmsSent { .. } => self.stats.sms_sent_today += 1,
            ActivityEvent::EmailReceived { .. } => self.stats.emails_received_today += 1,
            ActivityEvent::EmailSent { .. } => self.stats.emails_sent_today += 1,
            ActivityEvent::VoiceCallIncoming { .. } | ActivityEvent::VoiceCallOutgoing { .. } => {
                self.stats.voice_calls_today += 1;
            }
            _ => {}
        }

        // Update audio visualizers based on event type
        match &event {
            ActivityEvent::UserSpeech { .. } | ActivityEvent::UserTranscription { .. } => {
                self.mic_visualizer.set_state(VisualizerState::Speaking);
            }
            ActivityEvent::SynthesisComplete { .. } => {
                self.moshi_visualizer.set_state(VisualizerState::AiSpeaking);
            }
            ActivityEvent::SystemEvent { message, .. } if message.contains("Processing") => {
                self.moshi_visualizer.set_state(VisualizerState::Processing);
            }
            _ => {
                // For other events, set to listening if voice bridge is online
                if self.voice_bridge_online {
                    if self.moshi_visualizer.state == VisualizerState::Idle {
                        self.moshi_visualizer.set_state(VisualizerState::Listening);
                    }
                    if self.mic_visualizer.state == VisualizerState::Idle {
                        self.mic_visualizer.set_state(VisualizerState::Listening);
                    }
                }
            }
        }

        // Add to feed
        self.activity_events.insert(0, event);

        // Trim to max size
        if self.activity_events.len() > MAX_ACTIVITY_EVENTS {
            self.activity_events.truncate(MAX_ACTIVITY_EVENTS);
        }

        self.last_update = Instant::now();
    }

    /// Update microphone audio level from real audio data
    fn update_mic_audio_level(&mut self, audio_level: f32) {
        self.current_mic_level = audio_level;

        // Update visualizer audio level
        let level = AudioLevel::from_rms(audio_level);
        self.mic_visualizer.set_audio_level(level);

        // Update visualizer state based on audio activity
        if audio_level > 0.01 {
            // Voice detected
            if self.mic_visualizer.state == VisualizerState::Listening {
                self.mic_visualizer.set_state(VisualizerState::Speaking);
            }
        } else {
            // Silence - return to listening if not in other states
            if self.mic_visualizer.state == VisualizerState::Speaking {
                self.mic_visualizer.set_state(VisualizerState::Listening);
            }
        }
    }

    /// Update MOSHI audio level from real audio data
    fn update_moshi_audio_level(&mut self, audio_level: f32) {
        self.current_moshi_level = audio_level;

        // Update visualizer audio level
        let level = AudioLevel::from_rms(audio_level);
        self.moshi_visualizer.set_audio_level(level);

        // Update visualizer state based on audio activity
        if audio_level > 0.01 {
            // AI speaking
            if self.moshi_visualizer.state == VisualizerState::Listening {
                self.moshi_visualizer.set_state(VisualizerState::AiSpeaking);
            }
        } else {
            // Silence - return to listening if not in other states
            if self.moshi_visualizer.state == VisualizerState::AiSpeaking {
                self.moshi_visualizer.set_state(VisualizerState::Listening);
            }
        }
    }

    /// Export current dashboard state as formatted text
    fn export_to_text(&self) -> String {
        let mut output = String::new();

        // Header
        output.push_str("=".repeat(80).as_str());
        output.push('\n');
        output.push_str("xSwarm Boss Dashboard Export\n");
        output.push_str(format!("Generated: {}\n", Local::now().format("%Y-%m-%d %H:%M:%S")).as_str());
        output.push_str("=".repeat(80).as_str());
        output.push_str("\n\n");

        // User Identity
        if let Some(identity) = &self.user_identity {
            output.push_str("USER IDENTITY\n");
            output.push_str("-".repeat(80).as_str());
            output.push('\n');
            output.push_str(format!("Username: {}\n", identity.username).as_str());
            output.push_str(format!("Email: {}\n", identity.email).as_str());
            output.push_str(format!("Subscription Tier: {}\n", identity.subscription_tier).as_str());
            output.push_str(format!("Persona: {}\n", identity.persona).as_str());
            if let Some(minutes) = identity.voice_minutes_remaining {
                output.push_str(format!("Voice Minutes Remaining: {}\n", minutes).as_str());
            }
            if let Some(sms) = identity.sms_messages_remaining {
                output.push_str(format!("SMS Messages Remaining: {}\n", sms).as_str());
            }
            output.push_str("\n\n");
        }

        // Connection Status
        output.push_str("CONNECTION STATUS\n");
        output.push_str("-".repeat(80).as_str());
        output.push('\n');
        output.push_str(format!("Server: {}\n", if self.server_connected { "Online" } else { "Offline" }).as_str());
        output.push_str(format!("Supervisor: {}\n", if self.supervisor_connected { "Online" } else { "Offline" }).as_str());
        output.push_str(format!("Voice Bridge: {}\n", if self.voice_bridge_online { "Online" } else { "Offline" }).as_str());
        if self.dev_mode {
            output.push_str("Development Mode: ACTIVE (External services bypassed)\n");
        }
        output.push_str("\n\n");

        // Statistics
        output.push_str("STATISTICS (Today)\n");
        output.push_str("-".repeat(80).as_str());
        output.push('\n');
        output.push_str(format!("SMS Received: {}\n", self.stats.sms_received_today).as_str());
        output.push_str(format!("SMS Sent: {}\n", self.stats.sms_sent_today).as_str());
        output.push_str(format!("Emails Received: {}\n", self.stats.emails_received_today).as_str());
        output.push_str(format!("Emails Sent: {}\n", self.stats.emails_sent_today).as_str());
        output.push_str(format!("Voice Calls: {}\n", self.stats.voice_calls_today).as_str());
        output.push_str(format!("Voice Minutes: {}\n", self.stats.voice_minutes_today).as_str());
        output.push_str("\n\n");

        // Initialization Errors
        if !self.init_errors.is_empty() {
            output.push_str("INITIALIZATION ERRORS\n");
            output.push_str("-".repeat(80).as_str());
            output.push('\n');
            for (i, error) in self.init_errors.iter().enumerate() {
                let (error_type, message) = match error {
                    InitializationError::MicrophonePermission { message } => ("Microphone Permission", message),
                    InitializationError::ServerConnection { message } => ("Server Connection", message),
                    InitializationError::Configuration { message } => ("Configuration", message),
                    InitializationError::AudioDevice { message } => ("Audio Device", message),
                    InitializationError::Generic { message } => ("Generic Error", message),
                };
                output.push_str(format!("{}. [{}] {}\n", i + 1, error_type, message).as_str());
            }
            output.push_str("\n\n");
        }

        // Activity Feed
        output.push_str("ACTIVITY FEED (Recent Events)\n");
        output.push_str("-".repeat(80).as_str());
        output.push('\n');

        if self.activity_events.is_empty() {
            output.push_str("No recent activity.\n");
        } else {
            for event in &self.activity_events {
                let event_text = match event {
                    ActivityEvent::SmsReceived { from, message, time } => {
                        format!("[{}] SMS RECEIVED from {}: {}", time.format("%H:%M:%S"), from, message)
                    }
                    ActivityEvent::SmsSent { to, message, time } => {
                        format!("[{}] SMS SENT to {}: {}", time.format("%H:%M:%S"), to, message)
                    }
                    ActivityEvent::EmailReceived { from, subject, time } => {
                        format!("[{}] EMAIL RECEIVED from {}: {}", time.format("%H:%M:%S"), from, subject)
                    }
                    ActivityEvent::EmailSent { to, subject, time } => {
                        format!("[{}] EMAIL SENT to {}: {}", time.format("%H:%M:%S"), to, subject)
                    }
                    ActivityEvent::VoiceCallIncoming { from, time } => {
                        format!("[{}] VOICE CALL INCOMING from {}", time.format("%H:%M:%S"), from)
                    }
                    ActivityEvent::VoiceCallOutgoing { to, time } => {
                        format!("[{}] VOICE CALL OUTGOING to {}", time.format("%H:%M:%S"), to)
                    }
                    ActivityEvent::UserSpeech { duration_ms, time } => {
                        format!("[{}] USER SPEECH: {}ms", time.format("%H:%M:%S"), duration_ms)
                    }
                    ActivityEvent::UserTranscription { text, time } => {
                        format!("[{}] USER SAID: {}", time.format("%H:%M:%S"), text)
                    }
                    ActivityEvent::SuggestionApplied { text, time } => {
                        format!("[{}] AI SUGGESTION: {}", time.format("%H:%M:%S"), text)
                    }
                    ActivityEvent::SynthesisComplete { text, duration_ms, time } => {
                        format!("[{}] AI SPOKE ({}ms): {}", time.format("%H:%M:%S"), duration_ms, text)
                    }
                    ActivityEvent::SystemEvent { message, time } => {
                        format!("[{}] SYSTEM: {}", time.format("%H:%M:%S"), message)
                    }
                    ActivityEvent::Error { message, time } => {
                        format!("[{}] ERROR: {}", time.format("%H:%M:%S"), message)
                    }
                };
                output.push_str(format!("{}\n", event_text).as_str());
            }
        }

        output.push_str("\n");
        output.push_str("=".repeat(80).as_str());
        output.push('\n');
        output.push_str("End of Dashboard Export\n");
        output.push_str("=".repeat(80).as_str());
        output.push('\n');

        output
    }
}

/// Dashboard configuration
#[derive(Debug, Clone)]
pub struct DashboardConfig {
    /// Server configuration for API calls
    pub server_config: ServerConfig,
    /// Supervisor WebSocket URL
    pub supervisor_url: String,
    /// Supervisor authentication token
    pub supervisor_token: String,
    /// Refresh interval for server health checks (seconds)
    pub refresh_interval_secs: u64,
}

impl Default for DashboardConfig {
    fn default() -> Self {
        let supervisor_token = std::env::var("SUPERVISOR_TOKEN")
            .unwrap_or_else(|_| "dev-token-12345".to_string());

        Self {
            server_config: ServerConfig::default(),
            supervisor_url: "ws://127.0.0.1:9999".to_string(),
            supervisor_token,
            refresh_interval_secs: 5,
        }
    }
}

/// Main dashboard instance
pub struct Dashboard {
    config: DashboardConfig,
    state: Arc<RwLock<DashboardState>>,
    server_client: Arc<ServerClient>,
    /// Voice bridge handle (started on demand)
    voice_bridge_handle: Arc<RwLock<Option<tokio::task::JoinHandle<()>>>>,
    /// Supervisor handle (started on demand)
    supervisor_handle: Arc<RwLock<Option<tokio::task::JoinHandle<()>>>>,
    /// Audio frame receiver for real-time audio visualization
    #[allow(dead_code)]
    audio_rx: Arc<RwLock<Option<mpsc::UnboundedReceiver<super::local_audio::AudioFrame>>>>,
    /// MOSHI audio amplitude receiver for AI output visualization
    moshi_amplitude_rx: Arc<RwLock<Option<mpsc::UnboundedReceiver<f32>>>>,
    /// Shared audio broadcast channel for visualizer and MOSHI
    shared_audio_broadcast: Arc<RwLock<Option<tokio::sync::broadcast::Sender<super::local_audio::AudioFrame>>>>,
    /// Shared playback channel for MOSHI audio output
    shared_playback_tx: Arc<RwLock<Option<mpsc::UnboundedSender<Vec<f32>>>>>,
}

impl Dashboard {
    /// Create a new dashboard
    pub fn new(config: DashboardConfig) -> Result<Self> {
        let server_client = Arc::new(ServerClient::new(config.server_config.clone())?);

        Ok(Self {
            config,
            state: Arc::new(RwLock::new(DashboardState::new())),
            server_client,
            voice_bridge_handle: Arc::new(RwLock::new(None)),
            supervisor_handle: Arc::new(RwLock::new(None)),
            audio_rx: Arc::new(RwLock::new(None)),
            moshi_amplitude_rx: Arc::new(RwLock::new(None)),
        shared_audio_broadcast: Arc::new(RwLock::new(None)),
        shared_playback_tx: Arc::new(RwLock::new(None)),
        })
    }

    /// Create a new dashboard with initialization errors
    pub fn new_with_errors(config: DashboardConfig, errors: Vec<InitializationError>) -> Result<Self> {
        let server_client = Arc::new(ServerClient::new(config.server_config.clone())?);
        let mut state = DashboardState::new();

        // Add all initialization errors
        for error in errors {
            state.add_initialization_error(error);
        }

        Ok(Self {
            config,
            state: Arc::new(RwLock::new(state)),
            server_client,
            voice_bridge_handle: Arc::new(RwLock::new(None)),
            supervisor_handle: Arc::new(RwLock::new(None)),
            audio_rx: Arc::new(RwLock::new(None)),
            moshi_amplitude_rx: Arc::new(RwLock::new(None)),
        shared_audio_broadcast: Arc::new(RwLock::new(None)),
        shared_playback_tx: Arc::new(RwLock::new(None)),
        })
    }

    /// Add an initialization error to be displayed in the dashboard
    pub async fn add_initialization_error(&self, error: InitializationError) {
        let mut state = self.state.write().await;
        state.add_initialization_error(error);
    }

    /// Run the dashboard TUI
    pub async fn run(&self) -> Result<()> {
        // Setup terminal with RAII guard for automatic cleanup
        let _terminal_guard = TerminalGuard::new()?;

        // Running flag for main event loop (controlled by keyboard events)
        let running = Arc::new(AtomicBool::new(true));

        let backend = CrosstermBackend::new(io::stdout());
        let mut terminal = Terminal::new(backend)?;

        // Check if we're in dev mode
        let dev_mode = {
            let state = self.state.read().await;
            state.dev_mode
        };

        // Spawn background tasks - skip if in dev mode
        let ws_handle = if !dev_mode {
            Some(self.spawn_supervisor_listener())
        } else {
            None
        };

        let health_handle = if !dev_mode {
            Some(self.spawn_health_checker())
        } else {
            None
        };


        // Create SHARED audio system for BOTH visualizer and MOSHI
        // This prevents duplicate microphone access conflicts
        info!("DASHBOARD: Creating shared audio system for visualizer and MOSHI conversation");

        let (audio_broadcast_tx, _) = tokio::sync::broadcast::channel::<crate::local_audio::AudioFrame>(1000);
        let audio_broadcast_tx_clone = audio_broadcast_tx.clone();
        info!("DASHBOARD: Created broadcast channel");

        // Store for later access by MOSHI
        {
            let mut shared_broadcast = self.shared_audio_broadcast.write().await;
            *shared_broadcast = Some(audio_broadcast_tx.clone());
        }
        info!("DASHBOARD: Stored broadcast channel for MOSHI access");
        
        // Spawn SINGLE audio system in blocking task (CPAL streams are not Send)
        let state_for_audio = self.state.clone();
        let shared_playback_tx_arc = self.shared_playback_tx.clone();
        
        info!("DASHBOARD: About to spawn audio system blocking task");
        let shared_audio_handle = tokio::task::spawn_blocking(move || {
            info!("DASHBOARD: Shared audio system task starting...");

            // Create the ONE and ONLY audio system
            info!("DASHBOARD: Creating LocalAudioSystem...");
            let (mut audio_system, mut audio_rx, playback_tx) = match crate::local_audio::LocalAudioSystem::new() {
                Ok(system) => {
                    info!("DASHBOARD: LocalAudioSystem created successfully");
                    system
                },
                Err(e) => {
                    error!("DASHBOARD: Failed to create shared audio system: {}", e);
                    return;
                }
            };
            
            // Store playback_tx for MOSHI to use
            tokio::runtime::Handle::current().block_on(async {
                let mut shared_tx = shared_playback_tx_arc.write().await;
                *shared_tx = Some(playback_tx);
            });
            
            // Start BOTH microphone input and speaker output
            if let Err(e) = audio_system.start() {
                error!("Failed to start shared audio system I/O: {}", e);
                let rt = tokio::runtime::Handle::current();
                rt.spawn(async move {
                    let mut state = state_for_audio.write().await;
                    state.add_initialization_error(InitializationError::AudioDevice {
                        message: format!("Failed to start audio I/O: {}", e),
                    });
                });
                return;
            }
            
            info!("✓ Shared audio system started (microphone + speakers)");

            // Forward ALL microphone audio to broadcast channel
            // This allows MULTIPLE consumers (visualizer + MOSHI) to receive same audio
            let mut frame_count = 0u64;
            info!("AUDIO_BROADCAST: Starting to forward microphone frames to broadcast channel");

            while let Some(audio_frame) = audio_rx.blocking_recv() {
                frame_count += 1;

                // Broadcast to all subscribers (no per-frame logging - floods TUI)
                match audio_broadcast_tx_clone.send(audio_frame) {
                    Ok(_) => {
                        // Success - continue
                    }
                    Err(e) => {
                        error!("AUDIO_BROADCAST: Broadcast failed after {} frames: {} - no receivers, stopping", frame_count, e);
                        break;
                    }
                }
            }

            info!("AUDIO_BROADCAST: Shared audio system stopped after {} frames", frame_count);
            let _ = audio_system.stop();
        });

        // Subscribe visualizer to shared audio broadcast
        info!("Starting audio visualizer (subscribed to shared audio)");
        let mut visualizer_audio_rx = audio_broadcast_tx.subscribe();
        let state_for_visualizer = self.state.clone();

        let audio_visualizer_handle = tokio::spawn(async move {
            info!("Audio visualizer subscriber started");

            while let Ok(audio_frame) = visualizer_audio_rx.recv().await {
                // Calculate RMS audio level for visualizer
                let rms = crate::audio_visualizer::AudioLevel::calculate_rms(&audio_frame.samples);

                // Update dashboard state with microphone audio level
                let mut state = state_for_visualizer.write().await;
                state.update_mic_audio_level(rms);
            }

            info!("Audio visualizer subscriber stopped");
        });

        let audio_handle = Some(shared_audio_handle);

        // CRITICAL FIX: Subscribe MOSHI to broadcast channel EARLY (before async spawn)
        // This prevents missing audio frames due to late subscription
        info!("MOSHI SETUP: Pre-subscribing to audio broadcast BEFORE async initialization...");
        let moshi_broadcast_rx = audio_broadcast_tx.subscribe();
        info!("MOSHI SETUP: Pre-subscribed successfully - will receive all microphone frames");

        // Auto-start MOSHI voice system after TUI is ready
        // This happens in background to avoid blocking the UI
        info!("Auto-starting MOSHI voice system in background...");
        {
            let mut state = self.state.write().await;
            state.add_event(ActivityEvent::SystemEvent {
                message: "🎤 Starting MOSHI voice system...".to_string(),
                time: Local::now(),
            });
        }

        // Spawn voice system startup in background task
        // We need to clone the Arc fields we'll use in the async block
        let state_clone = self.state.clone();
        let voice_bridge_handle = self.voice_bridge_handle.clone();
        let supervisor_handle = self.supervisor_handle.clone();
        let moshi_amplitude_rx = self.moshi_amplitude_rx.clone();
        let shared_audio_broadcast = self.shared_audio_broadcast.clone();
        let shared_playback_tx = self.shared_playback_tx.clone();

        tokio::spawn(async move {
            // Move the pre-subscribed receiver into the async block
            let mut moshi_broadcast_rx = moshi_broadcast_rx;
            // Check if voice system is already running
            {
                let voice_handle = voice_bridge_handle.read().await;
                if voice_handle.is_some() {
                    info!("Voice system already running - skipping auto-start");
                    return;
                }
            }

            // Mark as starting
            {
                let mut state = state_clone.write().await;
                state.voice_system_starting = true;
            }

            // STEP 1: Check/request microphone permission on macOS
            #[cfg(target_os = "macos")]
            {
                use crate::permissions;
                {
                    let mut state = state_clone.write().await;
                    state.add_event(ActivityEvent::SystemEvent {
                        message: "🎤 Requesting microphone permission...".to_string(),
                        time: Local::now(),
                    });
                }

                info!("Checking microphone permissions on macOS");
                if let Err(e) = permissions::ensure_microphone_permission(true) {
                    error!("Microphone permission check failed: {}", e);
                    let mut state = state_clone.write().await;
                    state.voice_system_starting = false;
                    state.add_initialization_error(InitializationError::MicrophonePermission {
                        message: format!("Microphone permission denied: {}", e),
                    });
                    state.add_event(ActivityEvent::Error {
                        message: "❌ Microphone permission denied - voice system startup failed".to_string(),
                        time: Local::now(),
                    });
                    return;
                }

                {
                    let mut state = state_clone.write().await;
                    state.add_event(ActivityEvent::SystemEvent {
                        message: "✓ Microphone permission granted".to_string(),
                        time: Local::now(),
                    });
                }
            }

            // STEP 2: Initialize MOSHI models
            {
                let mut state = state_clone.write().await;
                state.add_event(ActivityEvent::SystemEvent {
                    message: "🤖 Initializing MOSHI AI models...".to_string(),
                    time: Local::now(),
                });
            }

            // Create voice bridge configuration
            info!("Creating voice bridge configuration");
            let voice_config = crate::voice::VoiceConfig::default();
            let supervisor_config = crate::supervisor::SupervisorConfig::default();

            // STEP 3: Create voice bridge (this loads the models)
            info!("Creating VoiceBridge instance");
            match crate::voice::VoiceBridge::new(voice_config.clone()).await {
                Ok(voice_bridge) => {
                    info!("VoiceBridge created successfully");
                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "✓ MOSHI models loaded".to_string(),
                            time: Local::now(),
                        });
                    }

                    let moshi_state = voice_bridge.get_moshi_state();

                    // STEP 4: Connect audio visualizer
                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "🔗 Connecting audio visualizer...".to_string(),
                            time: Local::now(),
                        });
                    }

                    // Connect amplitude channel for visualizer
                    let amplitude_rx = voice_bridge.connect_amplitude_channel().await;
                    {
                        let mut moshi_rx = moshi_amplitude_rx.write().await;
                        *moshi_rx = Some(amplitude_rx);
                    }

                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "✓ Audio visualizer connected".to_string(),
                            time: Local::now(),
                        });
                    }

                    let voice_bridge = Arc::new(voice_bridge);

                    // STEP 5: Start voice bridge server
                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: format!("🔗 Starting voice bridge on ws://{}:{}...", voice_config.host, voice_config.port),
                            time: Local::now(),
                        });
                    }

                    // Spawn voice bridge task
                    let voice_bridge_clone = voice_bridge.clone();
                    let state_clone_inner = state_clone.clone();
                    let voice_handle = tokio::spawn(async move {
                        match voice_bridge_clone.start_server().await {
                            Ok(_) => {
                                info!("Voice bridge stopped normally");
                            }
                            Err(e) => {
                                error!("Voice bridge error: {}", e);
                                let mut state = state_clone_inner.write().await;
                                state.voice_bridge_online = false;
                                state.add_event(ActivityEvent::Error {
                                    message: format!("Voice bridge error: {}", e),
                                    time: Local::now(),
                                });
                            }
                        }
                    });

                    // Store voice bridge handle
                    {
                        let mut handle = voice_bridge_handle.write().await;
                        *handle = Some(voice_handle);
                    }

                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "✓ Voice bridge online".to_string(),
                            time: Local::now(),
                        });
                    }

                    // STEP 6: Start local voice conversation (microphone → MOSHI → speakers)
                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "🎤 Starting local voice conversation...".to_string(),
                            time: Local::now(),
                        });
                    }

                    // Use SHARED audio system for voice conversation
                    // No need for spawn_blocking - audio system already running!
                    let voice_bridge_for_conversation = voice_bridge.clone();
                    let state_for_conversation = state_clone.clone();
                    let shared_broadcast = shared_audio_broadcast.clone();
                    let shared_playback = shared_playback_tx.clone();

                    tokio::spawn(async move {
                        info!("Subscribing MOSHI to shared audio system");

                        // Get shared audio broadcast
                        let audio_broadcast = {
                            let broadcast_guard = shared_broadcast.read().await;
                            match broadcast_guard.as_ref() {
                                Some(tx) => tx.clone(),
                                None => {
                                    error!("Shared audio broadcast not available for MOSHI");
                                    let mut state = state_for_conversation.write().await;
                                    state.add_event(ActivityEvent::Error {
                                        message: "Shared audio system not initialized".to_string(),
                                        time: Local::now(),
                                    });
                                    return;
                                }
                            }
                        };

                        // Get shared playback channel
                        let playback_tx = {
                            let playback_guard = shared_playback.read().await;
                            match playback_guard.as_ref() {
                                Some(tx) => tx.clone(),
                                None => {
                                    error!("Shared playback channel not available for MOSHI");
                                    let mut state = state_for_conversation.write().await;
                                    state.add_event(ActivityEvent::Error {
                                        message: "Shared audio playback not initialized".to_string(),
                                        time: Local::now(),
                                    });
                                    return;
                                }
                            }
                        };

                        // Use the pre-subscribed broadcast receiver (created early to avoid missing frames)
                        info!("MOSHI SETUP: Using pre-subscribed audio broadcast receiver");

                        // Convert broadcast receiver to unbounded channel for compatibility with start_local_conversation
                        let (moshi_tx, moshi_rx) = mpsc::unbounded_channel();
                        info!("MOSHI SETUP: Created unbounded channel for MOSHI conversation");

                        // Spawn forwarding task and store handle
                        let forwarding_handle = tokio::spawn(async move {
                            info!("========================================");
                            info!("AUDIO_BRIDGE: Forwarding task SPAWNED and STARTING");
                            info!("AUDIO_BRIDGE: This task forwards broadcast frames to MOSHI");
                            info!("========================================");

                            let mut frame_count = 0u64;
                            let mut lag_count = 0u64;

                            loop {
                                match moshi_broadcast_rx.recv().await {
                                    Ok(frame) => {
                                        frame_count += 1;
                                        // Forward to MOSHI channel (no per-frame logging - floods TUI)

                                        if let Err(_e) = moshi_tx.send(frame) {
                                            error!("AUDIO_BRIDGE: MOSHI receiver dropped after {} frames - conversation ended", frame_count);
                                            break;
                                        }
                                    }
                                    Err(tokio::sync::broadcast::error::RecvError::Lagged(skipped)) => {
                                        lag_count += 1;
                                        warn!(
                                            "AUDIO_BRIDGE: [Lag #{}] Broadcast lagged, skipped {} frames - continuing",
                                            lag_count,
                                            skipped
                                        );
                                        // Continue receiving - don't exit on lag
                                    }
                                    Err(tokio::sync::broadcast::error::RecvError::Closed) => {
                                        error!("AUDIO_BRIDGE: Broadcast channel closed - exiting forwarding task");
                                        break;
                                    }
                                }
                            }

                            error!("AUDIO_BRIDGE: Forwarding task stopped - frames={}, lags={}", frame_count, lag_count);
                        });

                        info!("MOSHI SETUP: Forwarding task spawned successfully");

                        info!("MOSHI subscribed to shared audio (microphone + speakers)");

                        // Start voice conversation loop (connects shared microphone → MOSHI → shared speakers)
                        match voice_bridge_for_conversation.start_local_conversation(moshi_rx, playback_tx).await {
                                Ok(handle) => {
                                    info!("Local voice conversation loop started successfully");

                                    // Store the handle for proper cleanup on exit
                                    {
                                        let mut voice_handle = voice_bridge_handle.write().await;
                                        *voice_handle = Some(handle);
                                    }

                                    let mut state = state_for_conversation.write().await;
                                    state.add_event(ActivityEvent::SystemEvent {
                                        message: "✓ Local voice conversation ready - speak into microphone!".to_string(),
                                        time: Local::now(),
                                    });

                                    // Voice conversation now runs in background - no need to block
                                    info!("Voice conversation running in background, UI remains responsive");
                                }
                                Err(e) => {
                                    error!("Failed to start local conversation loop: {}", e);
                                    let mut state = state_for_conversation.write().await;
                                    state.add_event(ActivityEvent::Error {
                                        message: format!("Failed to start conversation: {}", e),
                                        time: Local::now(),
                                    });
                                }
                            }
                        });

                    // STEP 8: Start supervisor
                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: format!("🔗 Starting supervisor on ws://{}:{}...", supervisor_config.host, supervisor_config.port),
                            time: Local::now(),
                        });
                    }

                    let supervisor = Arc::new(crate::supervisor::SupervisorServer::new(supervisor_config.clone(), moshi_state));
                    let state_clone_inner = state_clone.clone();
                    let supervisor_task = tokio::spawn(async move {
                        match supervisor.start().await {
                            Ok(_) => {
                                info!("Supervisor stopped normally");
                            }
                            Err(e) => {
                                error!("Supervisor error: {}", e);
                                let mut state = state_clone_inner.write().await;
                                state.supervisor_connected = false;
                                state.add_event(ActivityEvent::Error {
                                    message: format!("Supervisor error: {}", e),
                                    time: Local::now(),
                                });
                            }
                        }
                    });

                    // Store supervisor handle
                    {
                        let mut handle = supervisor_handle.write().await;
                        *handle = Some(supervisor_task);
                    }

                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "✓ Supervisor online".to_string(),
                            time: Local::now(),
                        });
                    }

                    // Update state
                    {
                        let mut state = state_clone.write().await;
                        state.voice_system_starting = false;
                        state.voice_bridge_online = true;
                        state.supervisor_connected = true;
                    }

                    info!("Voice system auto-started successfully");

                    // STEP 9: Play greeting to indicate MOSHI is ready
                    {
                        let mut state = state_clone.write().await;
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "🔊 Playing greeting tones...".to_string(),
                            time: Local::now(),
                        });
                    }

                    // Spawn in blocking task since audio uses non-Send CPAL streams
                    let state_for_greeting = state_clone.clone();
                    tokio::task::spawn_blocking(move || {
                        // Create a new tokio runtime for this blocking task
                        let rt = tokio::runtime::Runtime::new().unwrap();
                        rt.block_on(async {
                            if let Err(e) = crate::voice::generate_greeting_tone().await {
                                warn!("Failed to play greeting tone: {}", e);
                                let mut state = state_for_greeting.write().await;
                                state.add_event(ActivityEvent::Error {
                                    message: format!("Failed to play greeting: {}", e),
                                    time: Local::now(),
                                });
                            } else {
                                let mut state = state_for_greeting.write().await;
                                state.add_event(ActivityEvent::SystemEvent {
                                    message: "✅ MOSHI voice system ready!".to_string(),
                                    time: Local::now(),
                                });
                            }
                        })
                    });
                }
                Err(e) => {
                    error!("Failed to auto-start voice system: {}", e);
                    let mut state = state_clone.write().await;
                    state.voice_system_starting = false;
                    state.add_initialization_error(InitializationError::AudioDevice {
                        message: format!("Failed to initialize voice system: {}", e),
                    });
                    state.add_event(ActivityEvent::Error {
                        message: format!("❌ Voice system startup failed: {}", e),
                        time: Local::now(),
                    });
                }
            }
        });

        // Add initial system event
        {
            let mut state = self.state.write().await;
            let message = if dev_mode {
                "Dashboard started in DEVELOPMENT MODE - external services disabled".to_string()
            } else {
                "Dashboard started".to_string()
            };
            state.add_event(ActivityEvent::SystemEvent {
                message,
                time: Local::now(),
            });
        }

        // Run UI loop - catch any errors and try to display them in the UI
        let running_clone = running.clone();
        let result = match self.run_ui_loop(&mut terminal, running_clone).await {
            Ok(()) => Ok(()),
            Err(e) => {
                // If UI loop fails, try to handle device errors gracefully
                let error_msg = e.to_string();
                if error_msg.contains("os error 6") || error_msg.contains("Device not configured") {
                    // Add microphone error to state and try to continue showing UI
                    {
                        let mut state = self.state.write().await;
                        state.add_initialization_error(InitializationError::MicrophonePermission {
                            message: "Audio device access failed during operation".to_string(),
                        });
                        state.add_event(ActivityEvent::SystemEvent {
                            message: "Audio permission error handled".to_string(),
                            time: Local::now(),
                        });
                    }

                    // Try to run UI loop again with error displayed
                    self.run_ui_loop(&mut terminal, running.clone()).await
                } else {
                    // For other errors, add generic error and try again
                    {
                        let mut state = self.state.write().await;
                        state.add_initialization_error(InitializationError::Generic {
                            message: format!("Runtime error: {}", e),
                        });
                    }

                    self.run_ui_loop(&mut terminal, running.clone()).await
                }
            }
        };

        // Cleanup background tasks - only abort handles if they were spawned
        if let Some(handle) = ws_handle {
            handle.abort();
        }
        if let Some(handle) = health_handle {
            handle.abort();
        }
        if let Some(handle) = audio_handle {
            handle.abort();
            info!("Audio visualizer listener aborted");
        }

        // Cleanup voice system handles
        {
            let mut voice_handle = self.voice_bridge_handle.write().await;
            if let Some(handle) = voice_handle.take() {
                handle.abort();
                info!("Voice bridge task aborted");
            }
        }
        {
            let mut supervisor_handle = self.supervisor_handle.write().await;
            if let Some(handle) = supervisor_handle.take() {
                handle.abort();
                info!("Supervisor task aborted");
            }
        }

        // Show cursor before exit
        let _ = terminal.show_cursor();

        // Terminal cleanup happens automatically via TerminalGuard's Drop trait

        result
    }

    /// UI rendering loop
    async fn run_ui_loop<B: ratatui::backend::Backend>(
        &self,
        terminal: &mut Terminal<B>,
        running: Arc<AtomicBool>,
    ) -> Result<()> {
        let tick_rate = Duration::from_millis(250);
        let mut last_tick = Instant::now();

        loop {
            // Check if we should exit (signal handler triggered)
            if !running.load(Ordering::SeqCst) {
                break;
            }

            // Render UI
            let mut state = self.state.write().await;
            terminal.draw(|f| self.render_ui(f, &mut state))?;
            drop(state);

            // Handle input with timeout
            let timeout = tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| Duration::from_secs(0));

            // Check if we have a TTY before trying to poll for keyboard events
            use std::io::IsTerminal;

            if io::stdout().is_terminal() {
                // Only try to read keyboard input if we have a TTY
                if event::poll(timeout)? {
                    if let Event::Key(key) = event::read()? {
                        // Handle Ctrl+C first - this is critical for proper terminal cleanup
                        if key.code == KeyCode::Char('c') && key.modifiers.contains(KeyModifiers::CONTROL) {
                            running.store(false, Ordering::SeqCst);
                            break;
                        }

                        match key.code {
                            KeyCode::Char('q') | KeyCode::Char('Q') | KeyCode::Esc => {
                                break;
                            }
                            KeyCode::Char('r') | KeyCode::Char('R') => {
                                // Force refresh
                                self.refresh_server_data().await;
                            }
                            KeyCode::Char('c') | KeyCode::Char('C') => {
                                // Clear activity feed (only if not Ctrl+C)
                                if !key.modifiers.contains(KeyModifiers::CONTROL) {
                                    let mut state = self.state.write().await;
                                    state.activity_events.clear();
                                    state.add_event(ActivityEvent::SystemEvent {
                                        message: "Activity feed cleared".to_string(),
                                        time: Local::now(),
                                    });
                                }
                            }
                            KeyCode::Char('e') | KeyCode::Char('E') => {
                                // Toggle error panel visibility
                                let mut state = self.state.write().await;
                                state.show_error_panel = !state.show_error_panel;
                            }
                            KeyCode::Char('x') | KeyCode::Char('X') => {
                                // Clear errors
                                let mut state = self.state.write().await;
                                state.clear_errors();
                            }
                            KeyCode::Char('v') | KeyCode::Char('V') => {
                                // Start voice conversation system
                                let mut state = self.state.write().await;

                                // Check if voice system is already running
                                let voice_handle = self.voice_bridge_handle.read().await;
                                if voice_handle.is_some() {
                                    state.add_event(ActivityEvent::SystemEvent {
                                        message: "Voice system already running".to_string(),
                                        time: Local::now(),
                                    });
                                    drop(voice_handle);
                                } else {
                                    drop(voice_handle);
                                    state.add_event(ActivityEvent::SystemEvent {
                                        message: "Activating voice conversation...".to_string(),
                                        time: Local::now(),
                                    });
                                    drop(state);

                                    // Start voice system in background
                                    if let Err(e) = self.start_voice_system().await {
                                        let mut state = self.state.write().await;
                                        state.add_event(ActivityEvent::Error {
                                            message: format!("Failed to start voice system: {}", e),
                                            time: Local::now(),
                                        });
                                    }
                                }
                            }
                            _ => {}
                        }
                    }
                }
            } else {
                // No TTY - skip keyboard input handling, just sleep for the timeout
                tokio::time::sleep(timeout).await;
            }

            if last_tick.elapsed() >= tick_rate {
                last_tick = Instant::now();
            }
        }

        Ok(())
    }

    /// Render the UI
    fn render_ui(&self, frame: &mut Frame, state: &mut DashboardState) {
        let size = frame.size();

        // Check if we need to show error panel
        let show_errors = !state.init_errors.is_empty() && state.show_error_panel;

        // Create main layout with optional error panel
        let chunks = if show_errors {
            Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3),   // Header
                    Constraint::Length(8),   // Error panel
                    Constraint::Min(5),      // Content (smaller)
                    Constraint::Length(3),   // Footer
                ])
                .split(size)
        } else {
            Layout::default()
                .direction(Direction::Vertical)
                .constraints([
                    Constraint::Length(3),  // Header
                    Constraint::Min(10),    // Content
                    Constraint::Length(3),  // Footer
                ])
                .split(size)
        };

        // Render header
        self.render_header(frame, chunks[0], state);

        // Render error panel if needed
        let content_index = if show_errors {
            self.render_error_panel(frame, chunks[1], state);
            2
        } else {
            1
        };

        // Split content area
        let content_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(65),  // Activity feed
                Constraint::Percentage(35),  // Stats & Status
            ])
            .split(chunks[content_index]);

        // Render activity feed
        self.render_activity_feed(frame, content_chunks[0], state);

        // Split right side for MOSHI visualizer, mic bar, stats, and status
        let right_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(4),       // MOSHI output visualizer (fixed height)
                Constraint::Length(1),       // Single-line microphone level bar
                Constraint::Percentage(50),  // Statistics
                Constraint::Percentage(50),  // Status
            ])
            .split(content_chunks[1]);

        // Render MOSHI visualizer, mic bar, statistics, and status
        self.render_moshi_visualizer(frame, right_chunks[0], state);
        self.render_mic_level_bar(frame, right_chunks[1], state);
        self.render_statistics(frame, right_chunks[2], state);
        self.render_status(frame, right_chunks[3], state);

        // Render footer
        let footer_index = if show_errors { 3 } else { 2 };
        self.render_footer(frame, chunks[footer_index], show_errors, !state.init_errors.is_empty());
    }

    /// Render header with user info and connection status
    fn render_header(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        let username = state.user_identity.as_ref()
            .map(|u| u.username.clone())
            .unwrap_or_else(|| "Not connected".to_string());

        // Server status shows BYPASSED in dev mode, Online/Offline otherwise
        let server_status = if state.dev_mode {
            "BYPASSED"
        } else if state.server_connected {
            "Online"
        } else {
            "Offline"
        };

        let server_color = if state.dev_mode {
            Color::Yellow  // Match dev mode styling
        } else if state.server_connected {
            Color::Green
        } else {
            Color::Red
        };

        // Build title based on dev mode
        let title = if state.dev_mode {
            "xSwarm Boss Dashboard - DEV MODE (OFFLINE)"
        } else {
            "xSwarm Boss Dashboard"
        };

        let title_color = if state.dev_mode {
            Color::Yellow
        } else {
            Color::Cyan
        };

        // Get version from Cargo.toml
        let version = env!("CARGO_PKG_VERSION");

        let header_text = vec![
            Line::from(vec![
                Span::styled(title, Style::default().fg(title_color).add_modifier(Modifier::BOLD)),
                Span::raw(" | User: "),
                Span::styled(username, Style::default().fg(Color::Yellow)),
                Span::raw(" | Server: "),
                Span::styled(server_status, Style::default().fg(server_color)),
                Span::raw(" | v"),
                Span::styled(version, Style::default().fg(Color::LightMagenta)),
            ]),
        ];

        let header = Paragraph::new(header_text)
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Left);

        frame.render_widget(header, area);
    }

    /// Render activity feed
    fn render_activity_feed(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        let items: Vec<ListItem> = state.activity_events
            .iter()
            .map(|event| event.to_list_item())
            .collect();

        let list = List::new(items)
            .block(Block::default()
                .title("Recent Activity")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Cyan)))
            .highlight_style(Style::default().add_modifier(Modifier::BOLD));

        frame.render_widget(list, area);
    }

    /// Render MOSHI output visualizer
    fn render_moshi_visualizer(&self, frame: &mut Frame, area: Rect, state: &mut DashboardState) {
        // Get current animation frame for MOSHI output
        let frame_lines = state.moshi_visualizer.get_frame();

        // Determine border color based on visualizer state
        let border_color = match state.moshi_visualizer.state {
            VisualizerState::Idle => Color::Gray,
            VisualizerState::Listening => Color::Cyan,
            VisualizerState::Speaking => Color::Yellow,
            VisualizerState::Processing => Color::Magenta,
            VisualizerState::AiSpeaking => Color::Green,
        };

        // Create title based on state
        let title = match state.moshi_visualizer.state {
            VisualizerState::Idle => "MOSHI Output [Idle]",
            VisualizerState::Listening => "MOSHI Output [Ready]",
            VisualizerState::Speaking => "MOSHI Output [Active]",
            VisualizerState::Processing => "MOSHI Output [Processing]",
            VisualizerState::AiSpeaking => "MOSHI Output [Speaking]",
        };

        // Convert frame lines to ratatui Lines
        let lines: Vec<Line> = frame_lines
            .iter()
            .map(|line| Line::from(Span::styled(line.clone(), Style::default().fg(border_color))))
            .collect();

        let visualizer = Paragraph::new(lines)
            .block(Block::default()
                .title(title)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)))
            .alignment(Alignment::Center);

        frame.render_widget(visualizer, area);
    }

    /// Render single-line microphone level bar
    /// Shows real-time microphone input level as a horizontal bar
    fn render_mic_level_bar(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        // Generate bar using Unicode block characters
        let max_bar_width = 30; // Maximum bar width in characters
        let level = (state.current_mic_level * max_bar_width as f32) as usize;
        let bar_width = level.min(max_bar_width);

        // Unicode block characters: full, 7/8, 3/4, 5/8, 1/2, 3/8, 1/4, 1/8
        let blocks = ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏'];

        let mut bar = String::new();
        bar.push_str("Mic: ");

        // Full blocks
        for _ in 0..bar_width {
            bar.push(blocks[0]);
        }

        // Add partial block if there's a fractional part
        let fractional = (state.current_mic_level * max_bar_width as f32) - bar_width as f32;
        if fractional > 0.0 && bar_width < max_bar_width {
            let block_index = ((1.0 - fractional) * 7.0) as usize;
            bar.push(blocks[block_index.min(7)]);
        }

        // Color based on amplitude level
        let color = if state.current_mic_level > 0.1 {
            Color::Green  // Active speech
        } else if state.current_mic_level > 0.01 {
            Color::Yellow  // Quiet speech/noise
        } else {
            Color::Gray  // Silence
        };

        let paragraph = Paragraph::new(bar)
            .style(Style::default().fg(color));

        frame.render_widget(paragraph, area);
    }

    /// Render microphone input visualizer
    fn render_mic_visualizer(&self, frame: &mut Frame, area: Rect, state: &mut DashboardState) {
        // Get microphone input visualization frame
        let frame_lines = state.mic_visualizer.get_mic_input_frames();

        // Determine border color based on visualizer state (different colors for input)
        let border_color = match state.mic_visualizer.state {
            VisualizerState::Idle => Color::DarkGray,
            VisualizerState::Listening => Color::Blue,
            VisualizerState::Speaking => Color::LightYellow,
            VisualizerState::Processing => Color::LightMagenta,
            VisualizerState::AiSpeaking => Color::LightGreen,
        };

        // Create title based on state
        let title = match state.mic_visualizer.state {
            VisualizerState::Idle => "Microphone Input [Idle]",
            VisualizerState::Listening => "Microphone Input [Listening]",
            VisualizerState::Speaking => "Microphone Input [Speaking]",
            VisualizerState::Processing => "Microphone Input [Processing]",
            VisualizerState::AiSpeaking => "Microphone Input [Active]",
        };

        // Convert frame lines to ratatui Lines
        let lines: Vec<Line> = frame_lines
            .iter()
            .map(|line| Line::from(Span::styled(line.clone(), Style::default().fg(border_color))))
            .collect();

        let visualizer = Paragraph::new(lines)
            .block(Block::default()
                .title(title)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)))
            .alignment(Alignment::Center);

        frame.render_widget(visualizer, area);
    }

    /// Render statistics
    fn render_statistics(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        let stats_text = vec![
            Line::from(vec![
                Span::styled("Today:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::raw("  SMS received: "),
                Span::styled(state.stats.sms_received_today.to_string(), Style::default().fg(Color::Cyan)),
            ]),
            Line::from(vec![
                Span::raw("  SMS sent: "),
                Span::styled(state.stats.sms_sent_today.to_string(), Style::default().fg(Color::Blue)),
            ]),
            Line::from(vec![
                Span::raw("  Emails received: "),
                Span::styled(state.stats.emails_received_today.to_string(), Style::default().fg(Color::Green)),
            ]),
            Line::from(vec![
                Span::raw("  Emails sent: "),
                Span::styled(state.stats.emails_sent_today.to_string(), Style::default().fg(Color::LightGreen)),
            ]),
            Line::from(vec![
                Span::raw("  Voice calls: "),
                Span::styled(state.stats.voice_calls_today.to_string(), Style::default().fg(Color::Magenta)),
            ]),
        ];

        // Add usage limits if available
        let mut full_text = stats_text;
        if let Some(identity) = &state.user_identity {
            full_text.push(Line::from(""));
            full_text.push(Line::from(vec![
                Span::styled("Limits:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]));
            full_text.push(Line::from(""));

            if let Some(minutes) = identity.voice_minutes_remaining {
                full_text.push(Line::from(vec![
                    Span::raw("  Voice mins left: "),
                    Span::styled(minutes.to_string(), Style::default().fg(Color::LightBlue)),
                ]));
            }

            if let Some(sms) = identity.sms_messages_remaining {
                full_text.push(Line::from(vec![
                    Span::raw("  SMS left: "),
                    Span::styled(sms.to_string(), Style::default().fg(Color::LightCyan)),
                ]));
            }
        }

        let stats = Paragraph::new(full_text)
            .block(Block::default()
                .title("Statistics")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Green)))
            .alignment(Alignment::Left);

        frame.render_widget(stats, area);
    }

    /// Render system status
    fn render_status(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        let supervisor_status = if state.supervisor_connected { "Online" } else { "Offline" };
        let supervisor_color = if state.supervisor_connected { Color::Green } else { Color::Red };

        let (voice_status, voice_color) = if state.voice_system_starting {
            ("Starting...", Color::Yellow)
        } else if state.voice_bridge_online {
            ("Online", Color::Green)
        } else {
            ("Offline", Color::Gray)
        };

        let mut status_text = vec![];

        // Add dev mode indicator at top if in dev mode
        if state.dev_mode {
            status_text.extend(vec![
                Line::from(vec![
                    Span::styled("🔧 DEVELOPMENT MODE", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(""),
                Line::from(vec![
                    Span::styled("  External services:", Style::default().fg(Color::Yellow)),
                    Span::raw(" "),
                    Span::styled("BYPASSED", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(vec![
                    Span::styled("  Authentication:", Style::default().fg(Color::Yellow)),
                    Span::raw(" "),
                    Span::styled("MOCK ADMIN", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(vec![
                    Span::styled("  Supervisor:", Style::default().fg(Color::Yellow)),
                    Span::raw(" "),
                    Span::styled("OFFLINE", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                ]),
                Line::from(""),
                Line::from(vec![
                    Span::styled("─".repeat(30), Style::default().fg(Color::Gray)),
                ]),
                Line::from(""),
            ]);
        }

        // Add regular status info
        status_text.extend(vec![
            Line::from(vec![
                Span::styled("Voice Bridge:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::raw("  Status: "),
                Span::styled(voice_status, Style::default().fg(voice_color)),
            ]),
            Line::from(vec![
                Span::raw("  Port: "),
                Span::styled("9998", Style::default().fg(Color::Cyan)),
            ]),
            Line::from(""),
            Line::from(vec![
                Span::styled("Supervisor:", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(vec![
                Span::raw("  Status: "),
                Span::styled(supervisor_status, Style::default().fg(supervisor_color)),
            ]),
            Line::from(vec![
                Span::raw("  Port: "),
                Span::styled("9999", Style::default().fg(Color::Cyan)),
            ]),
        ]);

        let title = if state.dev_mode {
            "System Status (DEV MODE)"
        } else {
            "System Status"
        };

        let border_color = if state.dev_mode {
            Color::Yellow
        } else {
            Color::Magenta
        };

        let status = Paragraph::new(status_text)
            .block(Block::default()
                .title(title)
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color)))
            .alignment(Alignment::Left);

        frame.render_widget(status, area);
    }

    /// Render footer with help text
    fn render_footer(&self, frame: &mut Frame, area: Rect, _show_errors: bool, has_errors: bool) {
        let mut footer_text = vec![
            Span::styled("[Q]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("uit | "),
            Span::styled("[R]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("efresh | "),
            Span::styled("[C]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("lear Activity | "),
            Span::styled("[V]", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
            Span::raw("oice | "),
        ];

        if has_errors {
            footer_text.extend([
                Span::styled("[E]", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                Span::raw("rrors | "),
                Span::styled("[X]", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
                Span::raw(" Clear Errors | "),
            ]);
        }

        footer_text.extend([
            Span::styled("[H]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
            Span::raw("elp"),
        ]);

        let footer = Paragraph::new(vec![Line::from(footer_text)])
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Center);

        frame.render_widget(footer, area);
    }

    /// Render error panel with initialization errors and recovery instructions
    fn render_error_panel(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        let mut error_lines = vec![
            Line::from(vec![
                Span::styled("⚠️  Initialization Errors", Style::default().fg(Color::Red).add_modifier(Modifier::BOLD)),
            ]),
            Line::from(""),
        ];

        for error in &state.init_errors {
            let (icon, message, instructions) = match error {
                InitializationError::MicrophonePermission { message } => (
                    "🎤",
                    message.clone(),
                    "Grant microphone access in System Settings > Privacy & Security > Microphone"
                ),
                InitializationError::ServerConnection { message } => (
                    "🌐",
                    message.clone(),
                    "Check server configuration and network connectivity"
                ),
                InitializationError::Configuration { message } => (
                    "⚙️",
                    message.clone(),
                    "Review configuration files and environment variables"
                ),
                InitializationError::AudioDevice { message } => (
                    "🔊",
                    message.clone(),
                    "Check audio device connections and drivers"
                ),
                InitializationError::Generic { message } => (
                    "❌",
                    message.clone(),
                    "See documentation for troubleshooting steps"
                ),
            };

            error_lines.push(Line::from(vec![
                Span::raw(icon),
                Span::raw(" "),
                Span::styled(message, Style::default().fg(Color::Red)),
            ]));
            error_lines.push(Line::from(vec![
                Span::raw("  "),
                Span::styled("→ ", Style::default().fg(Color::Yellow)),
                Span::raw(instructions),
            ]));
            error_lines.push(Line::from(""));
        }

        error_lines.push(Line::from(vec![
            Span::styled("Press [E] to hide errors | [X] to clear errors", Style::default().fg(Color::Gray)),
        ]));

        let error_panel = Paragraph::new(error_lines)
            .block(Block::default()
                .title("System Errors")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Red)))
            .alignment(Alignment::Left)
            .wrap(Wrap { trim: true });

        frame.render_widget(error_panel, area);
    }

    /// Spawn WebSocket listener for supervisor events
    fn spawn_supervisor_listener(&self) -> tokio::task::JoinHandle<()> {
        let state = self.state.clone();
        let supervisor_url = self.config.supervisor_url.clone();
        let supervisor_token = self.config.supervisor_token.clone();

        tokio::spawn(async move {
            loop {
                info!("Connecting to supervisor at {}", supervisor_url);

                // Add connection timeout to prevent hanging
                let connection_result = tokio::time::timeout(
                    Duration::from_secs(5),
                    connect_async(&supervisor_url)
                ).await;

                match connection_result {
                    Ok(Ok((mut ws_stream, _))) => {
                        info!("Connected to supervisor WebSocket");

                        // Update connection status
                        {
                            let mut s = state.write().await;
                            s.supervisor_connected = true;
                            s.add_event(ActivityEvent::SystemEvent {
                                message: "Connected to supervisor".to_string(),
                                time: Local::now(),
                            });
                        }

                        // Send authentication
                        let auth_msg = serde_json::json!({
                            "type": "auth",
                            "token": supervisor_token
                        });

                        if let Err(e) = ws_stream.send(WsMessage::Text(auth_msg.to_string())).await {
                            error!("Failed to send auth to supervisor: {}", e);
                            continue;
                        }

                        // Listen for events
                        while let Some(msg) = ws_stream.next().await {
                            match msg {
                                Ok(WsMessage::Text(text)) => {
                                    if let Ok(event) = serde_json::from_str::<SupervisorEvent>(&text) {
                                        let activity_event = convert_supervisor_event(event);
                                        if let Some(evt) = activity_event {
                                            let mut s = state.write().await;
                                            s.add_event(evt);
                                        }
                                    }
                                }
                                Ok(WsMessage::Close(_)) => {
                                    info!("Supervisor connection closed");
                                    break;
                                }
                                Err(e) => {
                                    error!("Supervisor WebSocket error: {}", e);
                                    break;
                                }
                                _ => {}
                            }
                        }

                        // Update connection status
                        {
                            let mut s = state.write().await;
                            s.supervisor_connected = false;
                            s.add_event(ActivityEvent::SystemEvent {
                                message: "Disconnected from supervisor".to_string(),
                                time: Local::now(),
                            });
                        }
                    }
                    Ok(Err(e)) => {
                        error!("Failed to connect to supervisor: {}", e);
                        let mut s = state.write().await;
                        s.supervisor_connected = false;
                    }
                    Err(_) => {
                        warn!("Supervisor connection timeout after 5 seconds");
                        let mut s = state.write().await;
                        s.supervisor_connected = false;
                    }
                }

                // Wait before reconnecting
                tokio::time::sleep(Duration::from_secs(5)).await;
            }
        })
    }

    /// Spawn health checker for server and voice bridge
    fn spawn_health_checker(&self) -> tokio::task::JoinHandle<()> {
        let state = self.state.clone();
        let server_client = self.server_client.clone();
        let refresh_interval = Duration::from_secs(self.config.refresh_interval_secs);

        tokio::spawn(async move {
            loop {
                // Check server health with timeout
                let health_result = tokio::time::timeout(
                    Duration::from_secs(3),
                    server_client.health_check()
                ).await;

                match health_result {
                    Ok(Ok(healthy)) => {
                        let mut s = state.write().await;
                        s.server_connected = healthy;
                    }
                    Ok(Err(e)) => {
                        error!("Server health check failed: {}", e);
                        let mut s = state.write().await;
                        s.server_connected = false;
                    }
                    Err(_) => {
                        warn!("Server health check timeout after 3 seconds");
                        let mut s = state.write().await;
                        s.server_connected = false;
                    }
                }

                // Fetch user identity if connected with timeout
                if state.read().await.server_connected {
                    let identity_result = tokio::time::timeout(
                        Duration::from_secs(3),
                        server_client.get_identity()
                    ).await;

                    match identity_result {
                        Ok(Ok(identity)) => {
                            let mut s = state.write().await;
                            s.user_identity = Some(identity);
                        }
                        Ok(Err(_)) | Err(_) => {
                            // Identity fetch failed or timed out - not critical
                        }
                    }
                } else {
                    // Not connected - clear identity
                    let mut s = state.write().await;
                    s.user_identity = None;
                }

                tokio::time::sleep(refresh_interval).await;
            }
        })
    }

    /// Refresh server data manually
    async fn refresh_server_data(&self) {
        // This is now handled automatically by the health checker
    }

    /// Start refresh timer - legacy function, now handled by spawn_health_checker
    async fn start_refresh_timer(&self) {
        // No longer needed - health checker handles this
    }

    /// Start MOSHI amplitude listener for AI output visualization
    /// This receives amplitude data from MOSHI's audio output and updates the visualizer
    fn spawn_moshi_amplitude_listener(&self) -> Result<tokio::task::JoinHandle<()>> {
        info!("Starting MOSHI amplitude listener for AI output visualization");

        let state_clone = self.state.clone();
        let moshi_rx_arc = self.moshi_amplitude_rx.clone();

        let handle = tokio::spawn(async move {
            // Wait for receiver to be set
            let mut rx_opt = moshi_rx_arc.write().await;
            let Some(mut rx) = rx_opt.take() else {
                warn!("MOSHI amplitude receiver not initialized");
                return;
            };
            drop(rx_opt);

            info!("MOSHI amplitude listener started - receiving AI audio amplitudes");

            // Process amplitude values
            while let Some(rms) = rx.recv().await {
                // Update visualizer with AI audio amplitude
                let mut state = state_clone.write().await;
                state.update_moshi_audio_level(rms);
            }

            info!("MOSHI amplitude listener stopped");
        });

        Ok(handle)
    }

    /// Start local audio capture for visualizer
    /// This starts the microphone and feeds real-time audio levels to the visualizer
    fn spawn_audio_visualizer_listener(&self) -> Result<tokio::task::JoinHandle<()>> {
        info!("Starting audio visualizer listener");

        // Create local audio system
        // Note: LocalAudioSystem cannot be Send, so we need to keep it on the main thread
        // We'll use a different approach: spawn a blocking task that runs the audio system
        let state_clone = self.state.clone();

        let handle = tokio::task::spawn_blocking(move || {
            // Create audio system (this must run on a thread that can block)
            let (mut audio_system, mut audio_rx, _playback_tx) = match super::local_audio::LocalAudioSystem::new() {
                Ok(system) => system,
                Err(e) => {
                    error!("Failed to create local audio system: {}", e);
                    return;
                }
            };

            // Start audio input
            if let Err(e) = audio_system.start_input() {
                error!("Failed to start audio input: {}", e);
                return;
            }

            info!("Audio visualizer listener started successfully");

            // Process audio frames in blocking context
            // Since we're in spawn_blocking, we can use blocking operations
            while let Some(audio_frame) = audio_rx.blocking_recv() {
                // Calculate RMS audio level
                let rms = AudioLevel::calculate_rms(&audio_frame.samples);

                // Update dashboard state with microphone audio level
                // We need to spawn a tokio task to update the async state
                let state = state_clone.clone();
                tokio::spawn(async move {
                    let mut s = state.write().await;
                    s.update_mic_audio_level(rms);
                });
            }

            info!("Audio visualizer listener stopped");

            // Stop audio system
            let _ = audio_system.stop_input();
        });

        Ok(handle)
    }

    /// Start the voice system on demand (activated by user pressing V)
    async fn start_voice_system(&self) -> Result<()> {
        use crate::voice;
        use crate::supervisor;

        info!("🎤 [DEBUG] start_voice_system() called");

        // Check if voice system is already running
        {
            let voice_handle = self.voice_bridge_handle.read().await;
            if voice_handle.is_some() {
                info!("🎤 [DEBUG] Voice system already running - aborting");
                let mut state = self.state.write().await;
                state.add_event(ActivityEvent::SystemEvent {
                    message: "Voice system already running".to_string(),
                    time: Local::now(),
                });
                return Ok(());
            }
        }

        info!("🎤 [DEBUG] Voice system not running - proceeding with start");

        // Mark as starting
        {
            let mut state = self.state.write().await;
            state.voice_system_starting = true;
            state.add_event(ActivityEvent::SystemEvent {
                message: "Starting voice system...".to_string(),
                time: Local::now(),
            });
        }

        info!("🎤 [DEBUG] Marked voice_system_starting = true");

        // Check/request microphone permission on macOS
        #[cfg(target_os = "macos")]
        {
            use crate::permissions;
            info!("🎤 [DEBUG] Checking microphone permissions on macOS");
            if let Err(e) = permissions::ensure_microphone_permission(true) {
                error!("🎤 [DEBUG] Microphone permission check failed: {}", e);
                let mut state = self.state.write().await;
                state.voice_system_starting = false;
                state.add_initialization_error(InitializationError::MicrophonePermission {
                    message: format!("Microphone permission denied: {}", e),
                });
                state.add_event(ActivityEvent::Error {
                    message: "Voice system startup failed: microphone permission denied".to_string(),
                    time: Local::now(),
                });
                return Err(anyhow::anyhow!("Microphone permission denied"));
            }
            info!("🎤 [DEBUG] Microphone permissions OK");
        }

        // Create voice bridge configuration
        info!("🎤 [DEBUG] Creating voice bridge configuration");
        let voice_config = voice::VoiceConfig::default();
        let supervisor_config = supervisor::SupervisorConfig::default();
        info!("🎤 [DEBUG] Configurations created");

        // Start voice bridge
        info!("🎤 [DEBUG] Creating VoiceBridge instance");
        match voice::VoiceBridge::new(voice_config.clone()).await {
            Ok(voice_bridge) => {
                info!("🎤 [DEBUG] VoiceBridge created successfully");
                let moshi_state = voice_bridge.get_moshi_state();

                // Connect amplitude channel for visualizer
                let amplitude_rx = voice_bridge.connect_amplitude_channel().await;
                {
                    let mut moshi_rx = self.moshi_amplitude_rx.write().await;
                    *moshi_rx = Some(amplitude_rx);
                }

                // Spawn MOSHI amplitude listener for AI output visualization
                match self.spawn_moshi_amplitude_listener() {
                    Ok(handle) => {
                        info!("MOSHI amplitude listener spawned successfully");
                        // Store handle to abort on shutdown
                        // For now we'll let it be cleaned up automatically
                        drop(handle);
                    }
                    Err(e) => {
                        warn!("Failed to start MOSHI amplitude listener: {}", e);
                    }
                }

                let voice_bridge = Arc::new(voice_bridge);

                // Spawn voice bridge task
                let voice_bridge_clone = voice_bridge.clone();
                let state_clone = self.state.clone();
                let voice_handle = tokio::spawn(async move {
                    match voice_bridge_clone.start_server().await {
                        Ok(_) => {
                            info!("Voice bridge stopped normally");
                        }
                        Err(e) => {
                            error!("Voice bridge error: {}", e);
                            let mut state = state_clone.write().await;
                            state.voice_bridge_online = false;
                            state.add_event(ActivityEvent::Error {
                                message: format!("Voice bridge error: {}", e),
                                time: Local::now(),
                            });
                        }
                    }
                });

                // Store voice bridge handle
                {
                    let mut handle = self.voice_bridge_handle.write().await;
                    *handle = Some(voice_handle);
                }

                // STEP 6: Start local voice conversation (microphone → MOSHI → speakers)
                {
                    let mut state = self.state.write().await;
                    state.add_event(ActivityEvent::SystemEvent {
                        message: "🎤 Starting local voice conversation...".to_string(),
                        time: Local::now(),
                    });
                }

                // Use SHARED audio system for voice conversation
                // No need for spawn_blocking - audio system already running!
                let voice_bridge_for_conversation = voice_bridge.clone();
                let state_for_conversation = self.state.clone();
                let shared_broadcast = self.shared_audio_broadcast.clone();
                let shared_playback = self.shared_playback_tx.clone();
                let voice_handle_for_conversation = self.voice_bridge_handle.clone();

                tokio::spawn(async move {
                    info!("Subscribing MOSHI to shared audio system (manual start)");

                    // Get shared audio broadcast
                    let audio_broadcast = {
                        let broadcast_guard = shared_broadcast.read().await;
                        match broadcast_guard.as_ref() {
                            Some(tx) => tx.clone(),
                            None => {
                                error!("Shared audio broadcast not available for MOSHI");
                                let mut state = state_for_conversation.write().await;
                                state.add_event(ActivityEvent::Error {
                                    message: "Shared audio system not initialized".to_string(),
                                    time: Local::now(),
                                });
                                return;
                            }
                        }
                    };

                    // Get shared playback channel
                    let playback_tx = {
                        let playback_guard = shared_playback.read().await;
                        match playback_guard.as_ref() {
                            Some(tx) => tx.clone(),
                            None => {
                                error!("Shared playback channel not available for MOSHI");
                                let mut state = state_for_conversation.write().await;
                                state.add_event(ActivityEvent::Error {
                                    message: "Shared audio playback not initialized".to_string(),
                                    time: Local::now(),
                                });
                                return;
                            }
                        }
                    };

                    // Subscribe to audio broadcast for MOSHI
                    info!("MOSHI SETUP (Manual): Subscribing to audio broadcast...");
                    let mut moshi_broadcast_rx = audio_broadcast.subscribe();
                    info!("MOSHI SETUP (Manual): Successfully subscribed to audio broadcast");

                    // Convert broadcast receiver to unbounded channel for compatibility with start_local_conversation
                    let (moshi_tx, moshi_rx) = mpsc::unbounded_channel();
                    info!("MOSHI SETUP (Manual): Created unbounded channel for MOSHI conversation");

                    // Spawn forwarding task and store handle
                    let forwarding_handle = tokio::spawn(async move {
                        info!("========================================");
                        info!("AUDIO_BRIDGE (Manual): Forwarding task SPAWNED and STARTING");
                        info!("AUDIO_BRIDGE (Manual): This task forwards broadcast frames to MOSHI");
                        info!("========================================");

                        let mut frame_count = 0u64;
                        let mut lag_count = 0u64;

                        loop {
                            match moshi_broadcast_rx.recv().await {
                                Ok(frame) => {
                                    frame_count += 1;
                                    // Forward to MOSHI channel (no per-frame logging - floods TUI)

                                    if let Err(_e) = moshi_tx.send(frame) {
                                        error!("AUDIO_BRIDGE (Manual): MOSHI receiver dropped after {} frames - conversation ended", frame_count);
                                        break;
                                    }
                                }
                                Err(tokio::sync::broadcast::error::RecvError::Lagged(skipped)) => {
                                    lag_count += 1;
                                    warn!(
                                        "AUDIO_BRIDGE (Manual): [Lag #{}] Broadcast lagged, skipped {} frames - continuing",
                                        lag_count,
                                        skipped
                                    );
                                    // Continue receiving - don't exit on lag
                                }
                                Err(tokio::sync::broadcast::error::RecvError::Closed) => {
                                    error!("AUDIO_BRIDGE (Manual): Broadcast channel closed - exiting forwarding task");
                                    break;
                                }
                            }
                        }

                        error!("AUDIO_BRIDGE (Manual): Forwarding task stopped - frames={}, lags={}", frame_count, lag_count);
                    });

                    info!("MOSHI SETUP (Manual): Forwarding task spawned successfully");

                    info!("MOSHI subscribed to shared audio (microphone + speakers, manual start)");

                    // Start voice conversation loop (connects shared microphone → MOSHI → shared speakers)
                    match voice_bridge_for_conversation.start_local_conversation(moshi_rx, playback_tx).await {
                            Ok(handle) => {
                                info!("Local voice conversation loop started successfully");

                                // Store the handle for proper cleanup on exit
                                {
                                    let mut voice_handle = voice_handle_for_conversation.write().await;
                                    *voice_handle = Some(handle);
                                }

                                let mut state = state_for_conversation.write().await;
                                state.add_event(ActivityEvent::SystemEvent {
                                    message: "✓ Local voice conversation ready - speak into microphone!".to_string(),
                                    time: Local::now(),
                                });

                                // Voice conversation now runs in background - no need to block
                                info!("Voice conversation running in background, UI remains responsive");
                            }
                            Err(e) => {
                                error!("Failed to start local conversation loop: {}", e);
                                let mut state = state_for_conversation.write().await;
                                state.add_event(ActivityEvent::Error {
                                    message: format!("Failed to start conversation: {}", e),
                                    time: Local::now(),
                                });
                            }
                        }
                    });

                // Clone moshi_state before moving it into supervisor
                let moshi_state_for_greeting = moshi_state.clone();

                // Start supervisor
                let supervisor = Arc::new(supervisor::SupervisorServer::new(supervisor_config.clone(), moshi_state));
                let state_clone = self.state.clone();
                let supervisor_handle = tokio::spawn(async move {
                    match supervisor.start().await {
                        Ok(_) => {
                            info!("Supervisor stopped normally");
                        }
                        Err(e) => {
                            error!("Supervisor error: {}", e);
                            let mut state = state_clone.write().await;
                            state.supervisor_connected = false;
                            state.add_event(ActivityEvent::Error {
                                message: format!("Supervisor error: {}", e),
                                time: Local::now(),
                            });
                        }
                    }
                });

                // Store supervisor handle
                {
                    let mut handle = self.supervisor_handle.write().await;
                    *handle = Some(supervisor_handle);
                }

                // Update state
                {
                    let mut state = self.state.write().await;
                    state.voice_system_starting = false;
                    state.voice_bridge_online = true;
                    state.supervisor_connected = true;
                    state.add_event(ActivityEvent::SystemEvent {
                        message: format!(
                            "Voice system started - Bridge: ws://{}:{}, Supervisor: ws://{}:{}",
                            voice_config.host, voice_config.port,
                            supervisor_config.host, supervisor_config.port
                        ),
                        time: Local::now(),
                    });
                }

                info!("Voice system started successfully");

                // Generate and play MOSHI greeting
                info!("🎤 Generating MOSHI voice greeting...");
                tokio::spawn(async move {
                    if let Err(e) = voice::generate_moshi_voice_greeting(moshi_state_for_greeting).await {
                        error!("Failed to generate MOSHI voice greeting: {}", e);
                    }
                });

                Ok(())
            }
            Err(e) => {
                let mut state = self.state.write().await;
                state.voice_system_starting = false;
                state.add_initialization_error(InitializationError::AudioDevice {
                    message: format!("Failed to initialize voice system: {}", e),
                });
                state.add_event(ActivityEvent::Error {
                    message: format!("Voice system startup failed: {}", e),
                    time: Local::now(),
                });
                Err(e)
            }
        }
    }
}

// Helper function to truncate strings for display
fn truncate_string(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else {
        format!("{}...", &s[..max_len.saturating_sub(3)])
    }
}

// Convert supervisor event to activity event
fn convert_supervisor_event(event: SupervisorEvent) -> Option<ActivityEvent> {
    match event {
        SupervisorEvent::UserSpeech { duration_ms, .. } => {
            Some(ActivityEvent::UserSpeech {
                duration_ms,
                time: Local::now(),
            })
        }
        SupervisorEvent::UserTranscription { text, .. } => {
            Some(ActivityEvent::UserTranscription {
                text,
                time: Local::now(),
            })
        }
        SupervisorEvent::SuggestionApplied { text, .. } => {
            Some(ActivityEvent::SuggestionApplied {
                text,
                time: Local::now(),
            })
        }
        SupervisorEvent::SynthesisComplete { text, duration_ms, .. } => {
            Some(ActivityEvent::SynthesisComplete {
                text,
                duration_ms,
                time: Local::now(),
            })
        }
        SupervisorEvent::SynthesisStarted { text, .. } => {
            Some(ActivityEvent::SystemEvent {
                message: format!("Started synthesis: {}", truncate_string(&text, 40)),
                time: Local::now(),
            })
        }
        SupervisorEvent::SynthesisFailed { text, error, .. } => {
            Some(ActivityEvent::Error {
                message: format!("Synthesis failed for '{}': {}", truncate_string(&text, 20), error),
                time: Local::now(),
            })
        }
        SupervisorEvent::AuthResult { success, message } => {
            Some(ActivityEvent::SystemEvent {
                message: format!("Auth {}: {}", if success { "success" } else { "failed" }, message),
                time: Local::now(),
            })
        }
        SupervisorEvent::SuggestionRejected { reason } => {
            Some(ActivityEvent::Error {
                message: format!("Suggestion rejected: {}", reason),
                time: Local::now(),
            })
        }
        _ => None,
    }
}

