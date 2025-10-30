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
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{
    backend::CrosstermBackend,
    layout::{Alignment, Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span, Text},
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame, Terminal,
};
use std::io;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;
use tokio_tungstenite::{connect_async, tungstenite::Message as WsMessage};
use futures_util::{StreamExt, SinkExt};
use tracing::{info, warn, error, debug};
use chrono::{DateTime, Local};
use serde::{Deserialize, Serialize};

use crate::server_client::{ServerClient, ServerConfig, UserIdentity};
use crate::supervisor::SupervisorEvent;

/// Maximum number of events to keep in activity feed
const MAX_ACTIVITY_EVENTS: usize = 50;

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
        }
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

        // Add to feed
        self.activity_events.insert(0, event);

        // Trim to max size
        if self.activity_events.len() > MAX_ACTIVITY_EVENTS {
            self.activity_events.truncate(MAX_ACTIVITY_EVENTS);
        }

        self.last_update = Instant::now();
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
}

impl Dashboard {
    /// Create a new dashboard
    pub fn new(config: DashboardConfig) -> Result<Self> {
        let server_client = Arc::new(ServerClient::new(config.server_config.clone())?);

        Ok(Self {
            config,
            state: Arc::new(RwLock::new(DashboardState::new())),
            server_client,
        })
    }

    /// Run the dashboard TUI
    pub async fn run(&self) -> Result<()> {
        // Setup terminal
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
        let backend = CrosstermBackend::new(stdout);
        let mut terminal = Terminal::new(backend)?;

        // Spawn background tasks
        let ws_handle = self.spawn_supervisor_listener();
        let health_handle = self.spawn_health_checker();

        // Add initial system event
        {
            let mut state = self.state.write().await;
            state.add_event(ActivityEvent::SystemEvent {
                message: "Dashboard started".to_string(),
                time: Local::now(),
            });
        }

        // Run UI loop
        let result = self.run_ui_loop(&mut terminal).await;

        // Cleanup
        ws_handle.abort();
        health_handle.abort();

        disable_raw_mode()?;
        execute!(
            terminal.backend_mut(),
            LeaveAlternateScreen,
            DisableMouseCapture
        )?;
        terminal.show_cursor()?;

        result
    }

    /// UI rendering loop
    async fn run_ui_loop<B: ratatui::backend::Backend>(
        &self,
        terminal: &mut Terminal<B>,
    ) -> Result<()> {
        let tick_rate = Duration::from_millis(250);
        let mut last_tick = Instant::now();

        loop {
            // Render UI
            let state = self.state.read().await;
            terminal.draw(|f| self.render_ui(f, &state))?;
            drop(state);

            // Handle input with timeout
            let timeout = tick_rate
                .checked_sub(last_tick.elapsed())
                .unwrap_or_else(|| Duration::from_secs(0));

            if event::poll(timeout)? {
                if let Event::Key(key) = event::read()? {
                    match key.code {
                        KeyCode::Char('q') | KeyCode::Char('Q') | KeyCode::Esc => {
                            return Ok(());
                        }
                        KeyCode::Char('r') | KeyCode::Char('R') => {
                            // Force refresh
                            self.refresh_server_data().await;
                        }
                        KeyCode::Char('c') | KeyCode::Char('C') => {
                            // Clear activity feed
                            let mut state = self.state.write().await;
                            state.activity_events.clear();
                            state.add_event(ActivityEvent::SystemEvent {
                                message: "Activity feed cleared".to_string(),
                                time: Local::now(),
                            });
                        }
                        _ => {}
                    }
                }
            }

            if last_tick.elapsed() >= tick_rate {
                last_tick = Instant::now();
            }
        }
    }

    /// Render the UI
    fn render_ui(&self, frame: &mut Frame, state: &DashboardState) {
        let size = frame.size();

        // Create main layout
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Length(3),  // Header
                Constraint::Min(10),    // Content
                Constraint::Length(3),  // Footer
            ])
            .split(size);

        // Render header
        self.render_header(frame, chunks[0], state);

        // Split content area
        let content_chunks = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([
                Constraint::Percentage(65),  // Activity feed
                Constraint::Percentage(35),  // Stats & Status
            ])
            .split(chunks[1]);

        // Render activity feed
        self.render_activity_feed(frame, content_chunks[0], state);

        // Split right side for stats and status
        let right_chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Percentage(50),  // Statistics
                Constraint::Percentage(50),  // Status
            ])
            .split(content_chunks[1]);

        // Render statistics and status
        self.render_statistics(frame, right_chunks[0], state);
        self.render_status(frame, right_chunks[1], state);

        // Render footer
        self.render_footer(frame, chunks[2]);
    }

    /// Render header with user info and connection status
    fn render_header(&self, frame: &mut Frame, area: Rect, state: &DashboardState) {
        let username = state.user_identity.as_ref()
            .map(|u| u.username.clone())
            .unwrap_or_else(|| "Not connected".to_string());

        let server_status = if state.server_connected { "Online" } else { "Offline" };
        let server_color = if state.server_connected { Color::Green } else { Color::Red };

        let header_text = vec![
            Line::from(vec![
                Span::styled("xSwarm Boss Dashboard", Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD)),
                Span::raw(" | User: "),
                Span::styled(username, Style::default().fg(Color::Yellow)),
                Span::raw(" | Server: "),
                Span::styled(server_status, Style::default().fg(server_color)),
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

        let voice_status = if state.voice_bridge_online { "Online" } else { "Offline" };
        let voice_color = if state.voice_bridge_online { Color::Green } else { Color::Gray };

        let status_text = vec![
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
        ];

        let status = Paragraph::new(status_text)
            .block(Block::default()
                .title("System Status")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Magenta)))
            .alignment(Alignment::Left);

        frame.render_widget(status, area);
    }

    /// Render footer with help text
    fn render_footer(&self, frame: &mut Frame, area: Rect) {
        let footer_text = vec![
            Line::from(vec![
                Span::styled("[Q]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("uit | "),
                Span::styled("[R]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("efresh | "),
                Span::styled("[C]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("lear Activity | "),
                Span::styled("[H]", Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD)),
                Span::raw("elp"),
            ]),
        ];

        let footer = Paragraph::new(footer_text)
            .block(Block::default().borders(Borders::ALL))
            .alignment(Alignment::Center);

        frame.render_widget(footer, area);
    }

    /// Spawn WebSocket listener for supervisor events
    fn spawn_supervisor_listener(&self) -> tokio::task::JoinHandle<()> {
        let state = self.state.clone();
        let supervisor_url = self.config.supervisor_url.clone();
        let supervisor_token = self.config.supervisor_token.clone();

        tokio::spawn(async move {
            loop {
                info!("Connecting to supervisor at {}", supervisor_url);

                match connect_async(&supervisor_url).await {
                    Ok((mut ws_stream, _)) => {
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
                    Err(e) => {
                        error!("Failed to connect to supervisor: {}", e);

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
                // Check server health
                match server_client.health_check().await {
                    Ok(healthy) => {
                        let mut s = state.write().await;
                        s.server_connected = healthy;
                    }
                    Err(e) => {
                        error!("Server health check failed: {}", e);
                        let mut s = state.write().await;
                        s.server_connected = false;
                    }
                }

                // Fetch user identity if connected
                if state.read().await.server_connected {
                    match server_client.get_identity().await {
                        Ok(identity) => {
                            let mut s = state.write().await;
                            s.user_identity = Some(identity);
                        }
                        Err(e) => {
                            error!("Failed to fetch user identity: {}", e);
                        }
                    }
                }

                // TODO: Check voice bridge health (could ping ws://127.0.0.1:9998)

                tokio::time::sleep(refresh_interval).await;
            }
        })
    }

    /// Force refresh server data
    async fn refresh_server_data(&self) {
        info!("Forcing server data refresh");

        // Invalidate cache and force refetch
        self.server_client.invalidate_cache().await;

        match self.server_client.get_identity().await {
            Ok(identity) => {
                let mut state = self.state.write().await;
                state.user_identity = Some(identity);
                state.add_event(ActivityEvent::SystemEvent {
                    message: "Server data refreshed".to_string(),
                    time: Local::now(),
                });
            }
            Err(e) => {
                error!("Failed to refresh server data: {}", e);
                let mut state = self.state.write().await;
                state.add_event(ActivityEvent::Error {
                    message: format!("Refresh failed: {}", e),
                    time: Local::now(),
                });
            }
        }
    }
}

/// Convert supervisor event to activity event
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
        SupervisorEvent::Error { message } => {
            Some(ActivityEvent::Error {
                message,
                time: Local::now(),
            })
        }
        _ => None,
    }
}

/// Truncate string to max length
fn truncate_string(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else {
        format!("{}...", &s[..max_len.saturating_sub(3)])
    }
}
