// Supervisor Module - Claude Code ↔ MOSHI Integration
//
// This module provides a WebSocket API for Claude Code to:
// 1. Monitor MOSHI voice conversations
// 2. Inject suggestions into MOSHI's text conditioning layer
// 3. Receive user speech events for context
//
// This serves as both a development interface and the production blueprint
// for RAG/tool integration.

use anyhow::{Context, Result};
use std::sync::Arc;
use tokio::sync::{RwLock, Mutex};
use tokio::net::TcpStream;
use tokio_tungstenite::{accept_async, tungstenite::Message as WsMessage};
use futures_util::{StreamExt, SinkExt};
use tracing::{info, warn, error, debug};
use serde::{Deserialize, Serialize};
use chrono::Utc;

use crate::voice::MoshiState;
use crate::server_client::{ServerClient, UserIdentity};
use crate::claude_code::{ClaudeCodeConnector, ClaudeCodeConfig};
use crate::memory::{MemorySystem, MemoryConfig};
use crate::stt::{SttEngine, SttConfig};

/// Configuration for supervisor WebSocket server
#[derive(Debug, Clone)]
pub struct SupervisorConfig {
    /// WebSocket server host
    pub host: String,
    /// WebSocket server port (default 9999, adjacent to voice bridge on 9998)
    pub port: u16,
    /// Authentication token for admin access
    pub auth_token: String,
    /// Maximum queue size (prevent flooding)
    pub max_queue_size: usize,
    /// Minimum time between suggestions (milliseconds)
    pub rate_limit_ms: u64,
}

impl Default for SupervisorConfig {
    fn default() -> Self {
        Self {
            host: "127.0.0.1".to_string(),
            port: 9999,
            auth_token: std::env::var("SUPERVISOR_TOKEN")
                .unwrap_or_else(|_| "dev-token-12345".to_string()),
            max_queue_size: 5,
            rate_limit_ms: 2000, // 1 suggestion per 2 seconds
        }
    }
}

/// Incoming message from Claude Code to MOSHI
#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum SupervisorMessage {
    /// Authenticate connection
    Auth {
        token: String,
    },
    /// Inject a suggestion into MOSHI
    InjectSuggestion {
        text: String,
        #[serde(default)]
        priority: Priority,
    },
    /// Synthesize text to speech (Claude speaking back)
    SynthesizeText {
        text: String,
        #[serde(default)]
        stream_sid: Option<String>,
    },
    /// SMS received from user (sent by Node.js webhook server)
    SmsReceived {
        from: String,
        to: String,
        message: String,
        user: String,
    },
    /// Email received from user (sent by Node.js webhook server)
    EmailReceived {
        from: String,
        to: String,
        subject: String,
        body: String,
        user: String,
    },
    /// Connect to Claude Code session
    ClaudeCodeConnect {
        session_id: String,
        project_path: String,
        user_id: String,
    },
    /// Send message to Claude Code session
    ClaudeCodeMessage {
        session_id: String,
        message: String,
        context: Option<serde_json::Value>,
    },
    /// Disconnect from Claude Code session
    ClaudeCodeDisconnect {
        session_id: String,
    },
    /// Schedule an appointment via natural language
    ScheduleAppointment {
        user_id: String,
        text: String,
    },
    /// Set a reminder
    ScheduleReminder {
        user_id: String,
        title: String,
        due_time: String, // ISO 8601
        priority: Option<i32>,
    },
    /// Get calendar for a time period
    GetCalendar {
        user_id: String,
        period: String, // "today", "week", "month"
    },
    /// Ping to keep connection alive
    Ping,
}

/// Outgoing message from MOSHI to Claude Code
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum SupervisorEvent {
    /// Authentication result
    AuthResult {
        success: bool,
        message: String,
    },
    /// User speech detected
    UserSpeech {
        duration_ms: u64,
        timestamp: String,
    },
    /// User speech transcribed by MOSHI
    UserTranscription {
        text: String,
        timestamp: String,
    },
    /// Suggestion was injected
    SuggestionApplied {
        text: String,
        timestamp: String,
    },
    /// Suggestion rejected (queue full or rate limited)
    SuggestionRejected {
        reason: String,
    },
    /// Text synthesis started (Claude speaking)
    SynthesisStarted {
        text: String,
        timestamp: String,
    },
    /// Text synthesis completed
    SynthesisComplete {
        text: String,
        duration_ms: u64,
        timestamp: String,
    },
    /// Text synthesis failed
    SynthesisFailed {
        text: String,
        error: String,
        timestamp: String,
    },
    /// Send SMS response (to Node.js server for Twilio)
    SendSmsResponse {
        to: String,
        message: String,
        user: String,
    },
    /// Send Email response (to Node.js server for SendGrid)
    SendEmailResponse {
        to: String,
        subject: String,
        body: String,
        user: String,
    },
    /// SMS/Email message acknowledged
    MessageAcknowledged {
        message_type: String,
        user: String,
        timestamp: String,
    },
    /// Claude Code session connected
    ClaudeCodeConnected {
        session_id: String,
        status: String,
        timestamp: String,
    },
    /// Claude Code message received
    ClaudeCodeResponse {
        session_id: String,
        message_id: String,
        content: String,
        cost_usd: Option<f64>,
        timestamp: String,
    },
    /// Claude Code session disconnected
    ClaudeCodeDisconnected {
        session_id: String,
        reason: String,
        timestamp: String,
    },
    /// Appointment scheduled
    AppointmentScheduled {
        appointment_id: String,
        title: String,
        start_time: String,
        end_time: String,
        timestamp: String,
    },
    /// Reminder created
    ReminderCreated {
        reminder_id: String,
        title: String,
        due_time: String,
        timestamp: String,
    },
    /// Reminder is due and needs to be sent
    ReminderDue {
        reminder_id: String,
        appointment_id: String,
        user_id: String,
        method: String,
        message: String,
        timestamp: String,
    },
    /// Reminder was successfully sent
    ReminderSent {
        reminder_id: String,
        method: String,
        timestamp: String,
    },
    /// Reminder failed to send
    ReminderFailed {
        reminder_id: String,
        method: String,
        error: String,
        timestamp: String,
    },
    /// Calendar retrieved
    CalendarRetrieved {
        period: String,
        appointments: Vec<serde_json::Value>,
        timestamp: String,
    },
    /// Pong response
    Pong,
    /// Error occurred
    Error {
        message: String,
    },
}

/// Priority level for suggestions
#[derive(Debug, Deserialize, Clone, Copy, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
enum Priority {
    High,
    Normal,
    Low,
}

impl Default for Priority {
    fn default() -> Self {
        Priority::Normal
    }
}

/// Supervisor server state
pub struct SupervisorServer {
    config: SupervisorConfig,
    moshi_state: Arc<RwLock<MoshiState>>,
    last_injection_time: Arc<Mutex<std::time::Instant>>,
    server_client: Option<Arc<ServerClient>>,
    claude_code_connector: Option<Arc<ClaudeCodeConnector>>,
    memory_system: Option<Arc<MemorySystem>>,
    stt_engine: Option<Arc<SttEngine>>,
}

impl SupervisorServer {
    /// Create a new supervisor server
    pub fn new(config: SupervisorConfig, moshi_state: Arc<RwLock<MoshiState>>) -> Self {
        Self {
            config,
            moshi_state,
            last_injection_time: Arc::new(Mutex::new(std::time::Instant::now())),
            server_client: None,
            claude_code_connector: None,
            memory_system: None,
            stt_engine: None,
        }
    }

    /// Create a new supervisor server with server client for user identity
    pub fn with_server_client(
        config: SupervisorConfig,
        moshi_state: Arc<RwLock<MoshiState>>,
        server_client: Arc<ServerClient>,
    ) -> Self {
        Self {
            config,
            moshi_state,
            last_injection_time: Arc::new(Mutex::new(std::time::Instant::now())),
            server_client: Some(server_client),
            claude_code_connector: None,
            memory_system: None,
            stt_engine: None,
        }
    }

    /// Enable Claude Code integration
    pub fn with_claude_code(mut self, claude_code_config: ClaudeCodeConfig) -> Self {
        self.claude_code_connector = Some(Arc::new(ClaudeCodeConnector::new(claude_code_config)));
        self
    }

    /// Enable semantic memory integration
    pub async fn with_memory_system(mut self, memory_config: MemoryConfig) -> Result<Self> {
        let memory_system = MemorySystem::new(memory_config).await
            .context("Failed to initialize memory system")?;
        self.memory_system = Some(Arc::new(memory_system));
        info!("Semantic memory system enabled for supervisor");
        Ok(self)
    }

    /// Enable speech-to-text transcription
    pub fn with_stt(mut self, stt_config: SttConfig) -> Result<Self> {
        let stt_engine = SttEngine::with_config(stt_config)
            .context("Failed to initialize STT engine")?;
        self.stt_engine = Some(Arc::new(stt_engine));
        info!("Speech-to-text (STT) engine enabled for supervisor");
        Ok(self)
    }

    /// Start background task to poll STT transcriptions and store in memory
    ///
    /// This task continuously checks for completed transcriptions from the STT engine
    /// and stores them in the semantic memory system (if enabled).
    pub fn start_stt_transcription_poller(self: &Arc<Self>) {
        let stt_engine = match &self.stt_engine {
            Some(engine) => engine.clone(),
            None => {
                debug!("STT engine not enabled, skipping transcription poller");
                return;
            }
        };

        let memory_system = self.memory_system.clone();
        let server_client = self.server_client.clone();

        tokio::spawn(async move {
            info!("STT transcription poller started");

            loop {
                // Poll for transcription results
                match stt_engine.get_transcription().await {
                    Ok(Some(result)) => {
                        info!(
                            text_len = result.text.len(),
                            user_id = %result.user_id,
                            session_id = %result.session_id,
                            confidence = result.confidence,
                            processing_time_ms = result.processing_time_ms,
                            "Transcription received from STT engine"
                        );

                        // Store in memory system if enabled
                        if let Some(memory) = &memory_system {
                            // Parse user_id as UUID (or generate a new one for voice sessions)
                            let user_uuid = uuid::Uuid::parse_str(&result.user_id)
                                .unwrap_or_else(|_| {
                                    // If user_id isn't a UUID, generate a random one
                                    // TODO: Consider using a consistent UUID per session_id
                                    uuid::Uuid::new_v4()
                                });

                            match memory.store_conversation(user_uuid, &result.text).await {
                                Ok(session_id) => {
                                    info!(
                                        session_id = %session_id,
                                        user_id = %result.user_id,
                                        "Stored transcription in semantic memory"
                                    );
                                }
                                Err(e) => {
                                    error!(
                                        error = ?e,
                                        user_id = %result.user_id,
                                        "Failed to store transcription in memory"
                                    );
                                }
                            }
                        } else {
                            debug!("Memory system not enabled, skipping transcription storage");
                        }
                    }
                    Ok(None) => {
                        // No transcription ready yet, sleep briefly
                        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                    }
                    Err(e) => {
                        error!(error = ?e, "Error polling STT transcriptions");
                        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                    }
                }
            }
        });
    }

    /// Get user identity from server (if server client is configured)
    pub async fn get_user_identity(&self) -> Option<UserIdentity> {
        if let Some(client) = &self.server_client {
            match client.get_identity().await {
                Ok(identity) => {
                    debug!(
                        user_id = %identity.id,
                        username = %identity.username,
                        "Retrieved user identity from server"
                    );
                    Some(identity)
                }
                Err(e) => {
                    error!(error = ?e, "Failed to get user identity from server");
                    None
                }
            }
        } else {
            warn!("No server client configured - running without user identity");
            None
        }
    }

    /// Start the WebSocket server
    pub async fn start(self: Arc<Self>) -> Result<()> {
        let addr = format!("{}:{}", self.config.host, self.config.port);

        // Use helper function that sets SO_REUSEADDR for immediate port reuse
        let listener = crate::net_utils::create_reusable_tcp_listener(&addr).await
            .with_context(|| format!("Failed to bind supervisor server to {}", addr))?;

        info!(
            host = %self.config.host,
            port = self.config.port,
            "Supervisor WebSocket server listening"
        );

        // Start background task to poll STT transcriptions and store in memory
        self.start_stt_transcription_poller();

        loop {
            match listener.accept().await {
                Ok((stream, peer_addr)) => {
                    info!(?peer_addr, "New supervisor connection");
                    let server = self.clone();
                    tokio::spawn(async move {
                        if let Err(e) = server.handle_connection(stream).await {
                            error!(error = ?e, "Supervisor connection error");
                        }
                    });
                }
                Err(e) => {
                    error!(error = ?e, "Failed to accept supervisor connection");
                }
            }
        }
    }

    /// Handle a single WebSocket connection
    async fn handle_connection(&self, stream: TcpStream) -> Result<()> {
        let ws_stream = accept_async(stream)
            .await
            .context("WebSocket handshake failed")?;

        info!("Supervisor WebSocket connection established");

        let (mut ws_sender, mut ws_receiver) = ws_stream.split();
        let mut authenticated = false;

        // Create channels for bidirectional communication
        let (event_tx, mut event_rx) = tokio::sync::mpsc::unbounded_channel::<SupervisorEvent>();
        let (response_tx, mut response_rx) = tokio::sync::mpsc::unbounded_channel::<SupervisorEvent>();
        let (raw_tx, mut raw_rx) = tokio::sync::mpsc::unbounded_channel::<WsMessage>();

        // Register client with MoshiState for transcription broadcasting
        {
            let moshi_state = self.moshi_state.read().await;
            let mut clients = moshi_state.supervisor_clients.lock().await;
            clients.push(event_tx);
            debug!(client_count = clients.len(), "Registered supervisor client");
        }

        // Spawn task to handle all outgoing messages (events + responses + raw)
        let sender_task = tokio::spawn(async move {
            loop {
                tokio::select! {
                    // Handle broadcast events
                    event = event_rx.recv() => {
                        match event {
                            Some(event) => {
                                let json = match serde_json::to_string(&event) {
                                    Ok(json) => json,
                                    Err(e) => {
                                        error!(error = ?e, "Failed to serialize supervisor event");
                                        continue;
                                    }
                                };
                                if ws_sender.send(WsMessage::Text(json)).await.is_err() {
                                    debug!("Client disconnected during event broadcast");
                                    break;
                                }
                            }
                            None => break, // Channel closed
                        }
                    }
                    // Handle direct responses
                    response = response_rx.recv() => {
                        match response {
                            Some(response) => {
                                let json = match serde_json::to_string(&response) {
                                    Ok(json) => json,
                                    Err(e) => {
                                        error!(error = ?e, "Failed to serialize supervisor response");
                                        continue;
                                    }
                                };
                                if ws_sender.send(WsMessage::Text(json)).await.is_err() {
                                    debug!("Client disconnected during response");
                                    break;
                                }
                            }
                            None => break, // Channel closed
                        }
                    }
                    // Handle raw WebSocket messages (ping/pong)
                    raw_msg = raw_rx.recv() => {
                        match raw_msg {
                            Some(msg) => {
                                if ws_sender.send(msg).await.is_err() {
                                    debug!("Client disconnected during raw message");
                                    break;
                                }
                            }
                            None => break, // Channel closed
                        }
                    }
                }
            }
        });

        while let Some(msg) = ws_receiver.next().await {
            match msg {
                Ok(WsMessage::Text(text)) => {
                    debug!(message = %text, "Received supervisor message");

                    match serde_json::from_str::<SupervisorMessage>(&text) {
                        Ok(message) => {
                            let response = match message {
                                SupervisorMessage::Auth { token } => {
                                    authenticated = self.authenticate(&token);
                                    SupervisorEvent::AuthResult {
                                        success: authenticated,
                                        message: if authenticated {
                                            "Authenticated successfully".to_string()
                                        } else {
                                            "Invalid authentication token".to_string()
                                        },
                                    }
                                }
                                SupervisorMessage::InjectSuggestion { text, priority } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.inject_suggestion(text, priority).await
                                    }
                                }
                                SupervisorMessage::SynthesizeText { text, stream_sid } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.synthesize_text(text, stream_sid).await
                                    }
                                }
                                SupervisorMessage::SmsReceived { from, to, message, user } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_sms_received(from, to, message, user).await
                                    }
                                }
                                SupervisorMessage::EmailReceived { from, to, subject, body, user } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_email_received(from, to, subject, body, user).await
                                    }
                                }
                                SupervisorMessage::ClaudeCodeConnect { session_id, project_path, user_id } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_claude_code_connect(session_id, project_path, user_id).await
                                    }
                                }
                                SupervisorMessage::ClaudeCodeMessage { session_id, message, context } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_claude_code_message(session_id, message, context).await
                                    }
                                }
                                SupervisorMessage::ClaudeCodeDisconnect { session_id } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_claude_code_disconnect(session_id).await
                                    }
                                }
                                SupervisorMessage::ScheduleAppointment { user_id, text } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_schedule_appointment(user_id, text).await
                                    }
                                }
                                SupervisorMessage::ScheduleReminder { user_id, title, due_time, priority } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_schedule_reminder(user_id, title, due_time, priority).await
                                    }
                                }
                                SupervisorMessage::GetCalendar { user_id, period } => {
                                    if !authenticated {
                                        SupervisorEvent::Error {
                                            message: "Not authenticated".to_string(),
                                        }
                                    } else {
                                        self.handle_get_calendar(user_id, period).await
                                    }
                                }
                                SupervisorMessage::Ping => SupervisorEvent::Pong,
                            };

                            if response_tx.send(response).is_err() {
                                error!("Failed to send supervisor response - client disconnected");
                                break;
                            }
                        }
                        Err(e) => {
                            error!(error = ?e, message = %text, "Failed to parse supervisor message");
                            let error_response = SupervisorEvent::Error {
                                message: format!("Invalid message format: {}", e),
                            };
                            let _ = response_tx.send(error_response);
                        }
                    }
                }
                Ok(WsMessage::Binary(_)) => {
                    warn!("Received unexpected binary message from supervisor");
                }
                Ok(WsMessage::Close(_)) => {
                    info!("Supervisor connection closed");
                    break;
                }
                Ok(WsMessage::Ping(data)) => {
                    debug!("Received ping from supervisor");
                    if raw_tx.send(WsMessage::Pong(data)).is_err() {
                        error!("Failed to send pong to supervisor - client disconnected");
                        break;
                    }
                }
                Ok(WsMessage::Pong(_)) => {
                    debug!("Received pong from supervisor");
                }
                Ok(WsMessage::Frame(_)) => {
                    warn!("Received unexpected raw frame from supervisor");
                }
                Err(e) => {
                    error!(error = ?e, "Supervisor WebSocket error");
                    break;
                }
            }
        }

        // Cleanup: abort the sender task and let MoshiState clean up disconnected clients
        sender_task.abort();
        info!("Supervisor connection handler completed");
        Ok(())
    }

    /// Authenticate a connection
    fn authenticate(&self, token: &str) -> bool {
        token == self.config.auth_token
    }

    /// Inject a suggestion into MOSHI's suggestion queue
    async fn inject_suggestion(&self, text: String, priority: Priority) -> SupervisorEvent {
        // Check rate limiting
        {
            let mut last_time = self.last_injection_time.lock().await;
            let elapsed = last_time.elapsed();
            let rate_limit = std::time::Duration::from_millis(self.config.rate_limit_ms);

            if priority != Priority::High && elapsed < rate_limit {
                warn!(
                    elapsed_ms = elapsed.as_millis(),
                    rate_limit_ms = self.config.rate_limit_ms,
                    "Suggestion rejected due to rate limiting"
                );
                return SupervisorEvent::SuggestionRejected {
                    reason: format!(
                        "Rate limited. Wait {} ms between suggestions.",
                        rate_limit.as_millis()
                    ),
                };
            }

            *last_time = std::time::Instant::now();
        }

        // Get MOSHI state and check queue size
        let state = self.moshi_state.read().await;
        let mut queue = state.suggestion_queue.lock().await;

        if queue.len() >= self.config.max_queue_size {
            warn!(
                queue_size = queue.len(),
                max_size = self.config.max_queue_size,
                "Suggestion queue full"
            );
            return SupervisorEvent::SuggestionRejected {
                reason: format!(
                    "Queue full ({}/{})",
                    queue.len(),
                    self.config.max_queue_size
                ),
            };
        }

        // Add to queue
        info!(suggestion = %text, priority = ?priority, "Injecting suggestion");
        queue.push_back(text.clone());

        SupervisorEvent::SuggestionApplied {
            text,
            timestamp: Utc::now().to_rfc3339(),
        }
    }

    /// Broadcast user speech event (called from voice bridge)
    pub async fn broadcast_user_speech(
        &self,
        duration_ms: u64,
    ) -> Result<()> {
        // TODO: Implement broadcast to all connected clients
        // For now, just log it
        debug!(duration_ms, "User speech detected");
        Ok(())
    }

    /// Retrieve relevant memories and inject as context suggestion
    async fn retrieve_and_inject_memories(
        &self,
        user_id: &str,
        query: &str,
        memory_system: &Arc<MemorySystem>,
    ) -> Result<()> {
        use uuid::Uuid;

        // Parse user_id to UUID
        let user_uuid = Uuid::parse_str(user_id)
            .context("Failed to parse user_id as UUID")?;

        // Query memory system for top 3 relevant memories
        let memories = memory_system.retrieve_context(user_uuid, query, 3).await
            .context("Failed to retrieve memory context")?;

        if memories.is_empty() {
            debug!(user_id = %user_id, "No relevant memories found");
            return Ok(());
        }

        // Format memories into context string
        let memory_texts: Vec<String> = memories.iter()
            .map(|m| format!("[Memory: {}]", m.content))
            .collect();
        let context = memory_texts.join(" ");

        info!(
            user_id = %user_id,
            memory_count = memories.len(),
            context_length = context.len(),
            "Retrieved semantic memories"
        );

        // Inject memory context into suggestion queue
        let state = self.moshi_state.read().await;
        let mut queue = state.suggestion_queue.lock().await;

        // Add memory context as a suggestion (will be processed by memory_conditioner in voice.rs)
        queue.push_back(context);

        debug!(
            user_id = %user_id,
            queue_size = queue.len(),
            "Memory context injected into suggestion queue"
        );

        Ok(())
    }

    /// Handle voice transcription and route to Claude Code for Admin users
    pub async fn handle_voice_transcription(&self, user_id: &str, transcription: String) -> Result<Option<String>> {
        info!(
            user_id = %user_id,
            transcription = %transcription,
            "Processing voice transcription"
        );

        // Query semantic memory for relevant context (if memory system is enabled)
        if let Some(memory_system) = &self.memory_system {
            // Retrieve relevant memories and inject as context
            match self.retrieve_and_inject_memories(user_id, &transcription, memory_system).await {
                Ok(_) => {
                    debug!(user_id = %user_id, "Memory context retrieved and injected");
                }
                Err(e) => {
                    warn!(error = ?e, user_id = %user_id, "Failed to retrieve memory context");
                }
            }

            // Store this conversation in memory for future recall
            if let Ok(user_uuid) = uuid::Uuid::parse_str(user_id) {
                match memory_system.store_conversation(user_uuid, &transcription).await {
                    Ok(session_id) => {
                        debug!(
                            user_id = %user_id,
                            session_id = %session_id,
                            "Stored voice transcription in memory"
                        );
                    }
                    Err(e) => {
                        warn!(error = ?e, user_id = %user_id, "Failed to store conversation in memory");
                    }
                }
            }
        }

        // Check if this is an Admin user (via server client if available)
        let is_admin = if let Some(client) = &self.server_client {
            match client.get_identity().await {
                Ok(identity) => {
                    identity.id == user_id && identity.can_provision_numbers
                }
                Err(e) => {
                    warn!(error = ?e, "Failed to get user identity, treating as non-admin");
                    false
                }
            }
        } else {
            false
        };

        // If Admin user and Claude Code is enabled, route to Claude Code
        if is_admin {
            if let Some(connector) = &self.claude_code_connector {
                info!(user_id = %user_id, "Admin voice transcription detected - routing to Claude Code");

                // Find or create active session for this user
                let active_sessions = connector.get_user_sessions(user_id).await;
                let session_id = if let Some(active) = active_sessions.iter().find(|s| s.is_active()) {
                    active.id.clone()
                } else {
                    // Create new session
                    match connector.create_session(user_id.to_string(), "/current/project".to_string()).await {
                        Ok(session) => {
                            info!(session_id = %session.id, "Created new Claude Code session for Admin");
                            let session_id = session.id.clone();
                            // Connect the session
                            if let Err(e) = connector.connect_session(&session_id).await {
                                error!(error = ?e, "Failed to connect Claude Code session");
                                return Err(anyhow::anyhow!("Failed to connect Claude Code: {}", e));
                            }
                            session_id
                        }
                        Err(e) => {
                            error!(error = ?e, "Failed to create Claude Code session");
                            return Err(anyhow::anyhow!("Failed to create session: {}", e));
                        }
                    }
                };

                // Add context about the channel
                let mut context = std::collections::HashMap::new();
                context.insert("channel".to_string(), "voice".to_string());
                context.insert("user_id".to_string(), user_id.to_string());

                // Send message to Claude Code
                match connector.send_message(&session_id, transcription, Some(context)).await {
                    Ok(msg) => {
                        info!(message_id = %msg.id, "Sent voice transcription to Claude Code");

                        // Try to get response (non-blocking with timeout)
                        match connector.receive_response(&session_id).await {
                            Ok(Some(response)) => {
                                info!(response_id = %response.id, "Received response from Claude Code");
                                return Ok(Some(response.content));
                            }
                            Ok(None) => {
                                warn!("No response from Claude Code");
                                return Ok(None);
                            }
                            Err(e) => {
                                error!(error = ?e, "Failed to receive Claude Code response");
                                return Err(anyhow::anyhow!("Claude Code error: {}", e));
                            }
                        }
                    }
                    Err(e) => {
                        error!(error = ?e, "Failed to send message to Claude Code");
                        return Err(anyhow::anyhow!("Failed to send to Claude Code: {}", e));
                    }
                }
            }
        }

        // Non-admin or Claude Code not available
        Ok(None)
    }

    /// Synthesize text to speech and send to active Twilio stream
    async fn synthesize_text(&self, text: String, _stream_sid: Option<String>) -> SupervisorEvent {
        info!(text = %text, "Synthesizing text to speech");

        let start_time = std::time::Instant::now();
        let timestamp = Utc::now().to_rfc3339();

        // Notify that synthesis has started
        let _start_event = SupervisorEvent::SynthesisStarted {
            text: text.clone(),
            timestamp: timestamp.clone(),
        };

        // Get moshi state and create a new TTS engine for this request
        // Note: We create a new engine per request because AudioResampler is not Send+Sync
        let mut moshi_state = self.moshi_state.write().await;
        let mut tts_engine = match crate::tts::TtsEngine::new() {
            Ok(engine) => engine,
            Err(e) => {
                error!(error = ?e, "Failed to create TTS engine");
                return SupervisorEvent::SynthesisFailed {
                    text,
                    error: format!("Failed to initialize TTS engine: {}", e),
                    timestamp: Utc::now().to_rfc3339(),
                };
            }
        };

        // Attempt synthesis
        match tts_engine.synthesize_to_mulaw(&text, &mut moshi_state).await {
            Ok(mulaw_audio) => {
                let duration_ms = start_time.elapsed().as_millis() as u64;
                info!(
                    text = %text,
                    duration_ms = duration_ms,
                    audio_bytes = mulaw_audio.len(),
                    "Text synthesis completed"
                );

                // TODO: Send mulaw_audio to active Twilio stream via voice bridge
                // For now, just log success
                warn!("TTS audio generated but not yet sent to Twilio - voice bridge integration pending");

                SupervisorEvent::SynthesisComplete {
                    text,
                    duration_ms,
                    timestamp: Utc::now().to_rfc3339(),
                }
            }
            Err(e) => {
                error!(error = ?e, text = %text, "Text synthesis failed");
                SupervisorEvent::SynthesisFailed {
                    text,
                    error: e.to_string(),
                    timestamp: Utc::now().to_rfc3339(),
                }
            }
        }
    }

    /// Handle incoming SMS message from Node.js webhook server
    async fn handle_sms_received(
        &self,
        from: String,
        to: String,
        message: String,
        user: String,
    ) -> SupervisorEvent {
        info!(
            user = %user,
            from = %from,
            to = %to,
            message = %message,
            "SMS received from webhook"
        );

        let timestamp = Utc::now().to_rfc3339();

        // Check if this is an Admin user (via server client if available)
        let is_admin = if let Some(client) = &self.server_client {
            match client.get_identity().await {
                Ok(identity) => {
                    // Check if the sender phone matches admin's phone
                    identity.can_provision_numbers &&
                    (identity.user_phone == from || identity.xswarm_phone.as_ref() == Some(&from))
                }
                Err(e) => {
                    warn!(error = ?e, "Failed to get user identity, treating as non-admin");
                    false
                }
            }
        } else {
            false
        };

        // If Admin user and Claude Code is enabled, route to Claude Code
        if is_admin {
            if let Some(connector) = &self.claude_code_connector {
                info!(user = %user, "Admin SMS detected - routing to Claude Code");

                // Find or create active session for this user
                let active_sessions = connector.get_user_sessions(&user).await;
                let session_id = if let Some(active) = active_sessions.iter().find(|s| s.is_active()) {
                    active.id.clone()
                } else {
                    // Create new session
                    match connector.create_session(user.clone(), "/current/project".to_string()).await {
                        Ok(session) => {
                            info!(session_id = %session.id, "Created new Claude Code session for Admin");
                            let session_id = session.id.clone();
                            // Connect the session
                            if let Err(e) = connector.connect_session(&session_id).await {
                                error!(error = ?e, "Failed to connect Claude Code session");
                                return SupervisorEvent::Error {
                                    message: format!("Failed to connect Claude Code: {}", e),
                                };
                            }
                            session_id
                        }
                        Err(e) => {
                            error!(error = ?e, "Failed to create Claude Code session");
                            return SupervisorEvent::Error {
                                message: format!("Failed to create session: {}", e),
                            };
                        }
                    }
                };

                // Add context about the channel
                let mut context = std::collections::HashMap::new();
                context.insert("channel".to_string(), "sms".to_string());
                context.insert("from".to_string(), from.clone());
                context.insert("to".to_string(), to.clone());

                // Send message to Claude Code
                match connector.send_message(&session_id, message.clone(), Some(context)).await {
                    Ok(msg) => {
                        info!(message_id = %msg.id, "Sent SMS to Claude Code");

                        // Try to get response
                        match connector.receive_response(&session_id).await {
                            Ok(Some(response)) => {
                                info!(response_id = %response.id, "Received response from Claude Code");

                                // Send response back via SMS
                                return SupervisorEvent::SendSmsResponse {
                                    to: from,
                                    message: response.content,
                                    user,
                                };
                            }
                            Ok(None) => {
                                warn!("No response from Claude Code");
                                return SupervisorEvent::MessageAcknowledged {
                                    message_type: "sms".to_string(),
                                    user,
                                    timestamp,
                                };
                            }
                            Err(e) => {
                                error!(error = ?e, "Failed to receive Claude Code response");
                                return SupervisorEvent::Error {
                                    message: format!("Claude Code error: {}", e),
                                };
                            }
                        }
                    }
                    Err(e) => {
                        error!(error = ?e, "Failed to send message to Claude Code");
                        return SupervisorEvent::Error {
                            message: format!("Failed to send to Claude Code: {}", e),
                        };
                    }
                }
            }
        }

        // Non-admin or Claude Code not available - just acknowledge
        info!(user = %user, "Non-admin SMS or Claude Code unavailable - acknowledging");

        SupervisorEvent::MessageAcknowledged {
            message_type: "sms".to_string(),
            user,
            timestamp,
        }
    }

    /// Handle incoming Email message from Node.js webhook server
    async fn handle_email_received(
        &self,
        from: String,
        to: String,
        subject: String,
        body: String,
        user: String,
    ) -> SupervisorEvent {
        info!(
            user = %user,
            from = %from,
            to = %to,
            subject = %subject,
            "Email received from webhook"
        );

        let timestamp = Utc::now().to_rfc3339();

        // Check if this is an Admin user (via server client if available)
        let is_admin = if let Some(client) = &self.server_client {
            match client.get_identity().await {
                Ok(identity) => {
                    // Check if the sender email matches admin's email
                    identity.can_provision_numbers &&
                    (identity.email == from || identity.xswarm_email == from)
                }
                Err(e) => {
                    warn!(error = ?e, "Failed to get user identity, treating as non-admin");
                    false
                }
            }
        } else {
            false
        };

        // If Admin user and Claude Code is enabled, route to Claude Code
        if is_admin {
            if let Some(connector) = &self.claude_code_connector {
                info!(user = %user, "Admin email detected - routing to Claude Code");

                // Find or create active session for this user
                let active_sessions = connector.get_user_sessions(&user).await;
                let session_id = if let Some(active) = active_sessions.iter().find(|s| s.is_active()) {
                    active.id.clone()
                } else {
                    // Create new session
                    match connector.create_session(user.clone(), "/current/project".to_string()).await {
                        Ok(session) => {
                            info!(session_id = %session.id, "Created new Claude Code session for Admin");
                            let session_id = session.id.clone();
                            // Connect the session
                            if let Err(e) = connector.connect_session(&session_id).await {
                                error!(error = ?e, "Failed to connect Claude Code session");
                                return SupervisorEvent::Error {
                                    message: format!("Failed to connect Claude Code: {}", e),
                                };
                            }
                            session_id
                        }
                        Err(e) => {
                            error!(error = ?e, "Failed to create Claude Code session");
                            return SupervisorEvent::Error {
                                message: format!("Failed to create session: {}", e),
                            };
                        }
                    }
                };

                // Add context about the channel
                let mut context = std::collections::HashMap::new();
                context.insert("channel".to_string(), "email".to_string());
                context.insert("from".to_string(), from.clone());
                context.insert("to".to_string(), to.clone());
                context.insert("subject".to_string(), subject.clone());

                // Combine subject and body for the message
                let full_message = format!("Subject: {}\n\n{}", subject, body);

                // Send message to Claude Code
                match connector.send_message(&session_id, full_message, Some(context)).await {
                    Ok(msg) => {
                        info!(message_id = %msg.id, "Sent email to Claude Code");

                        // Try to get response
                        match connector.receive_response(&session_id).await {
                            Ok(Some(response)) => {
                                info!(response_id = %response.id, "Received response from Claude Code");

                                // Send response back via Email
                                return SupervisorEvent::SendEmailResponse {
                                    to: from,
                                    subject: format!("Re: {}", subject),
                                    body: response.content,
                                    user,
                                };
                            }
                            Ok(None) => {
                                warn!("No response from Claude Code");
                                return SupervisorEvent::MessageAcknowledged {
                                    message_type: "email".to_string(),
                                    user,
                                    timestamp,
                                };
                            }
                            Err(e) => {
                                error!(error = ?e, "Failed to receive Claude Code response");
                                return SupervisorEvent::Error {
                                    message: format!("Claude Code error: {}", e),
                                };
                            }
                        }
                    }
                    Err(e) => {
                        error!(error = ?e, "Failed to send message to Claude Code");
                        return SupervisorEvent::Error {
                            message: format!("Failed to send to Claude Code: {}", e),
                        };
                    }
                }
            }
        }

        // Non-admin or Claude Code not available - just acknowledge
        info!(user = %user, "Non-admin email or Claude Code unavailable - acknowledging");

        SupervisorEvent::MessageAcknowledged {
            message_type: "email".to_string(),
            user,
            timestamp,
        }
    }

    /// Handle Claude Code connection request
    async fn handle_claude_code_connect(
        &self,
        session_id: String,
        project_path: String,
        user_id: String,
    ) -> SupervisorEvent {
        info!(
            session_id = %session_id,
            user_id = %user_id,
            project_path = %project_path,
            "Claude Code connection request"
        );

        let connector = match &self.claude_code_connector {
            Some(c) => c,
            None => {
                error!("Claude Code integration not enabled");
                return SupervisorEvent::Error {
                    message: "Claude Code integration not enabled".to_string(),
                };
            }
        };

        // Create or connect to session
        match connector.connect_session(&session_id).await {
            Ok(_) => {
                info!(session_id = %session_id, "Claude Code session connected");
                SupervisorEvent::ClaudeCodeConnected {
                    session_id,
                    status: "connected".to_string(),
                    timestamp: Utc::now().to_rfc3339(),
                }
            }
            Err(e) => {
                error!(session_id = %session_id, error = ?e, "Failed to connect Claude Code session");
                SupervisorEvent::Error {
                    message: format!("Failed to connect: {}", e),
                }
            }
        }
    }

    /// Handle Claude Code message
    async fn handle_claude_code_message(
        &self,
        session_id: String,
        message: String,
        context: Option<serde_json::Value>,
    ) -> SupervisorEvent {
        info!(
            session_id = %session_id,
            message_length = message.len(),
            "Claude Code message"
        );

        let connector = match &self.claude_code_connector {
            Some(c) => c,
            None => {
                error!("Claude Code integration not enabled");
                return SupervisorEvent::Error {
                    message: "Claude Code integration not enabled".to_string(),
                };
            }
        };

        // Convert context to HashMap if provided
        let context_map = context.and_then(|v| {
            if let serde_json::Value::Object(map) = v {
                Some(map.into_iter()
                    .filter_map(|(k, v)| v.as_str().map(|s| (k, s.to_string())))
                    .collect())
            } else {
                None
            }
        });

        // Send message
        match connector.send_message(&session_id, message, context_map).await {
            Ok(msg) => {
                info!(
                    session_id = %session_id,
                    message_id = %msg.id,
                    "Message sent to Claude Code"
                );

                // Try to receive response
                match connector.receive_response(&session_id).await {
                    Ok(Some(response)) => {
                        info!(
                            session_id = %session_id,
                            response_id = %response.id,
                            "Received response from Claude Code"
                        );
                        SupervisorEvent::ClaudeCodeResponse {
                            session_id,
                            message_id: response.id,
                            content: response.content,
                            cost_usd: response.cost_usd,
                            timestamp: Utc::now().to_rfc3339(),
                        }
                    }
                    Ok(None) => {
                        warn!(session_id = %session_id, "No response from Claude Code");
                        SupervisorEvent::Error {
                            message: "No response received".to_string(),
                        }
                    }
                    Err(e) => {
                        error!(session_id = %session_id, error = ?e, "Failed to receive response");
                        SupervisorEvent::Error {
                            message: format!("Failed to receive response: {}", e),
                        }
                    }
                }
            }
            Err(e) => {
                error!(session_id = %session_id, error = ?e, "Failed to send message");
                SupervisorEvent::Error {
                    message: format!("Failed to send message: {}", e),
                }
            }
        }
    }

    /// Handle Claude Code disconnection
    async fn handle_claude_code_disconnect(
        &self,
        session_id: String,
    ) -> SupervisorEvent {
        info!(session_id = %session_id, "Claude Code disconnection request");

        let connector = match &self.claude_code_connector {
            Some(c) => c,
            None => {
                error!("Claude Code integration not enabled");
                return SupervisorEvent::Error {
                    message: "Claude Code integration not enabled".to_string(),
                };
            }
        };

        match connector.disconnect_session(&session_id).await {
            Ok(_) => {
                info!(session_id = %session_id, "Claude Code session disconnected");
                SupervisorEvent::ClaudeCodeDisconnected {
                    session_id,
                    reason: "User requested".to_string(),
                    timestamp: Utc::now().to_rfc3339(),
                }
            }
            Err(e) => {
                error!(session_id = %session_id, error = ?e, "Failed to disconnect");
                SupervisorEvent::Error {
                    message: format!("Failed to disconnect: {}", e),
                }
            }
        }
    }

    /// Handle schedule appointment request
    async fn handle_schedule_appointment(
        &self,
        user_id: String,
        text: String,
    ) -> SupervisorEvent {
        info!(
            user_id = %user_id,
            text = %text,
            "Schedule appointment request"
        );

        // TODO: Use scheduler module to parse natural language and create appointment
        // For now, return placeholder response
        warn!("Scheduler integration not yet implemented");

        SupervisorEvent::Error {
            message: "Scheduler integration pending - will be implemented in Rust module".to_string(),
        }
    }

    /// Handle schedule reminder request
    async fn handle_schedule_reminder(
        &self,
        user_id: String,
        title: String,
        due_time: String,
        priority: Option<i32>,
    ) -> SupervisorEvent {
        info!(
            user_id = %user_id,
            title = %title,
            due_time = %due_time,
            "Schedule reminder request"
        );

        // TODO: Use scheduler module to create reminder
        // For now, return placeholder response
        warn!("Scheduler integration not yet implemented");

        SupervisorEvent::Error {
            message: "Scheduler integration pending - will be implemented in Rust module".to_string(),
        }
    }

    /// Handle get calendar request
    async fn handle_get_calendar(
        &self,
        user_id: String,
        period: String,
    ) -> SupervisorEvent {
        info!(
            user_id = %user_id,
            period = %period,
            "Get calendar request"
        );

        // TODO: Query appointments from database via server client
        // For now, return placeholder response
        warn!("Calendar retrieval not yet implemented");

        SupervisorEvent::Error {
            message: "Calendar retrieval pending - will be implemented via server client".to_string(),
        }
    }

    /// Broadcast a reminder notification to connected clients
    ///
    /// This method is called by the ReminderProcessor to send reminders
    /// via the appropriate communication channel (SMS/Email/Voice).
    pub async fn broadcast_reminder_notification(
        &self,
        notification: crate::scheduler::ReminderNotification,
    ) -> Result<()> {
        use crate::scheduler::ReminderMethod;

        info!(
            reminder_id = %notification.reminder_id,
            user_id = %notification.user_id,
            method = ?notification.method,
            "Broadcasting reminder notification"
        );

        // Create the appropriate supervisor event based on method
        match notification.method {
            ReminderMethod::Sms => {
                self.send_sms_reminder(notification).await
            }
            ReminderMethod::Email => {
                self.send_email_reminder(notification).await
            }
            ReminderMethod::Voice => {
                self.send_voice_reminder(notification).await
            }
            ReminderMethod::Push => {
                info!("Push notifications not yet implemented");
                Ok(())
            }
        }
    }

    /// Send reminder via SMS
    async fn send_sms_reminder(
        &self,
        notification: crate::scheduler::ReminderNotification,
    ) -> Result<()> {
        // Get user phone number
        let phone_number = if let Some(client) = &self.server_client {
            match client.get_identity().await {
                Ok(identity) => identity.user_phone,
                Err(e) => {
                    error!(error = ?e, "Failed to get user identity for SMS reminder");
                    return Err(anyhow::anyhow!("Failed to get user phone: {}", e));
                }
            }
        } else {
            return Err(anyhow::anyhow!("No server client configured"));
        };

        // Broadcast SMS reminder event
        let moshi_state = self.moshi_state.read().await;
        let clients = moshi_state.supervisor_clients.lock().await;

        let event = SupervisorEvent::SendSmsResponse {
            to: phone_number,
            message: notification.message.clone(),
            user: notification.user_id.clone(),
        };

        // Send to all connected clients
        for client in clients.iter() {
            let _ = client.send(event.clone());
        }

        // Also log the ReminderSent event
        let sent_event = SupervisorEvent::ReminderSent {
            reminder_id: notification.reminder_id.clone(),
            method: "sms".to_string(),
            timestamp: Utc::now().to_rfc3339(),
        };

        for client in clients.iter() {
            let _ = client.send(sent_event.clone());
        }

        info!(
            reminder_id = %notification.reminder_id,
            "SMS reminder sent"
        );

        Ok(())
    }

    /// Send reminder via Email
    async fn send_email_reminder(
        &self,
        notification: crate::scheduler::ReminderNotification,
    ) -> Result<()> {
        // Get user email
        let email = if let Some(client) = &self.server_client {
            match client.get_identity().await {
                Ok(identity) => identity.email,
                Err(e) => {
                    error!(error = ?e, "Failed to get user identity for email reminder");
                    return Err(anyhow::anyhow!("Failed to get user email: {}", e));
                }
            }
        } else {
            return Err(anyhow::anyhow!("No server client configured"));
        };

        // Broadcast email reminder event
        let moshi_state = self.moshi_state.read().await;
        let clients = moshi_state.supervisor_clients.lock().await;

        let subject = format!("Reminder: {}", notification.appointment_title);

        let event = SupervisorEvent::SendEmailResponse {
            to: email,
            subject,
            body: notification.message.clone(),
            user: notification.user_id.clone(),
        };

        // Send to all connected clients
        for client in clients.iter() {
            let _ = client.send(event.clone());
        }

        // Also log the ReminderSent event
        let sent_event = SupervisorEvent::ReminderSent {
            reminder_id: notification.reminder_id.clone(),
            method: "email".to_string(),
            timestamp: Utc::now().to_rfc3339(),
        };

        for client in clients.iter() {
            let _ = client.send(sent_event.clone());
        }

        info!(
            reminder_id = %notification.reminder_id,
            "Email reminder sent"
        );

        Ok(())
    }

    /// Send reminder via Voice (MOSHI)
    async fn send_voice_reminder(
        &self,
        notification: crate::scheduler::ReminderNotification,
    ) -> Result<()> {
        info!(
            reminder_id = %notification.reminder_id,
            "Sending voice reminder via MOSHI"
        );

        // Use the synthesize_text method to speak the reminder
        let synthesis_result = self.synthesize_text(notification.message.clone(), None).await;

        match synthesis_result {
            SupervisorEvent::SynthesisComplete { .. } => {
                // Broadcast ReminderSent event
                let moshi_state = self.moshi_state.read().await;
                let clients = moshi_state.supervisor_clients.lock().await;

                let sent_event = SupervisorEvent::ReminderSent {
                    reminder_id: notification.reminder_id.clone(),
                    method: "voice".to_string(),
                    timestamp: Utc::now().to_rfc3339(),
                };

                for client in clients.iter() {
                    let _ = client.send(sent_event.clone());
                }

                info!(
                    reminder_id = %notification.reminder_id,
                    "Voice reminder sent successfully"
                );

                Ok(())
            }
            SupervisorEvent::SynthesisFailed { error, .. } => {
                error!(
                    reminder_id = %notification.reminder_id,
                    error = %error,
                    "Voice reminder failed"
                );

                // Broadcast ReminderFailed event
                let moshi_state = self.moshi_state.read().await;
                let clients = moshi_state.supervisor_clients.lock().await;

                let failed_event = SupervisorEvent::ReminderFailed {
                    reminder_id: notification.reminder_id.clone(),
                    method: "voice".to_string(),
                    error: error.clone(),
                    timestamp: Utc::now().to_rfc3339(),
                };

                for client in clients.iter() {
                    let _ = client.send(failed_event.clone());
                }

                Err(anyhow::anyhow!("Voice synthesis failed: {}", error))
            }
            _ => {
                warn!("Unexpected synthesis result");
                Ok(())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_supervisor_config_default() {
        let config = SupervisorConfig::default();
        assert_eq!(config.host, "127.0.0.1");
        assert_eq!(config.port, 9999);
        assert_eq!(config.max_queue_size, 5);
    }

    #[test]
    fn test_priority_default() {
        assert_eq!(Priority::default(), Priority::Normal);
    }
}
