// Claude Code Integration Module
//
// This module provides WebSocket-based integration with Claude Code sessions,
// allowing the Boss Assistant to route development conversations and tasks
// to active Claude Code instances for execution.
//
// Architecture:
// - ClaudeCodeSession: Tracks individual Claude Code session state
// - ClaudeCodeConnector: Manages WebSocket connections to Claude Code
// - Session monitoring, cost tracking, and conversation history
// - Integration with supervisor system for bidirectional communication

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{RwLock, Mutex};
use tokio::net::TcpStream;
use tokio_tungstenite::{connect_async, MaybeTlsStream, WebSocketStream, tungstenite::Message as WsMessage};
use futures_util::{StreamExt, SinkExt};
use tracing::{info, warn, error, debug};
use uuid::Uuid;

/// Claude Code session status
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum SessionStatus {
    /// Session is initializing
    Connecting,
    /// Session is active and ready
    Active,
    /// Session is temporarily idle
    Idle,
    /// Session is being disconnected
    Disconnecting,
    /// Session has ended
    Disconnected,
    /// Session encountered an error
    Error,
}

/// Claude Code session information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaudeCodeSession {
    /// Unique session ID
    pub id: String,
    /// User ID who owns this session
    pub user_id: String,
    /// Project path on local filesystem
    pub project_path: String,
    /// Current session status
    pub status: SessionStatus,
    /// Total cost in USD for this session
    pub cost_usd: f64,
    /// When the session started
    pub started_at: DateTime<Utc>,
    /// When the session ended (if applicable)
    pub ended_at: Option<DateTime<Utc>>,
    /// Number of messages exchanged
    pub message_count: u64,
    /// Last activity timestamp
    pub last_activity: DateTime<Utc>,
}

impl ClaudeCodeSession {
    /// Create a new Claude Code session
    pub fn new(user_id: String, project_path: String) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            user_id,
            project_path,
            status: SessionStatus::Connecting,
            cost_usd: 0.0,
            started_at: now,
            ended_at: None,
            message_count: 0,
            last_activity: now,
        }
    }

    /// Update session activity
    pub fn update_activity(&mut self) {
        self.last_activity = Utc::now();
        self.message_count += 1;
    }

    /// Add cost to session
    pub fn add_cost(&mut self, cost: f64) {
        self.cost_usd += cost;
    }

    /// Mark session as ended
    pub fn end_session(&mut self) {
        self.ended_at = Some(Utc::now());
        self.status = SessionStatus::Disconnected;
    }

    /// Get session duration in seconds
    pub fn duration_seconds(&self) -> i64 {
        let end_time = self.ended_at.unwrap_or_else(Utc::now);
        (end_time - self.started_at).num_seconds()
    }

    /// Check if session is active
    pub fn is_active(&self) -> bool {
        matches!(self.status, SessionStatus::Active | SessionStatus::Idle)
    }
}

/// Message sent to Claude Code
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaudeCodeMessage {
    /// Message ID for tracking
    pub id: String,
    /// Session ID this message belongs to
    pub session_id: String,
    /// Message content
    pub content: String,
    /// Message timestamp
    pub timestamp: DateTime<Utc>,
    /// Optional context/metadata
    pub context: Option<HashMap<String, String>>,
}

/// Response from Claude Code
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClaudeCodeResponse {
    /// Response ID
    pub id: String,
    /// Original message ID this responds to
    pub message_id: String,
    /// Response content
    pub content: String,
    /// Response timestamp
    pub timestamp: DateTime<Utc>,
    /// Estimated cost of this interaction
    pub cost_usd: Option<f64>,
    /// Execution status
    pub status: String,
}

/// Claude Code connector configuration
#[derive(Debug, Clone)]
pub struct ClaudeCodeConfig {
    /// Claude Code WebSocket URL
    pub websocket_url: String,
    /// Authentication token (if required)
    pub auth_token: Option<String>,
    /// Maximum concurrent sessions
    pub max_sessions: usize,
    /// Session idle timeout (seconds)
    pub idle_timeout_seconds: u64,
    /// Enable cost tracking
    pub track_costs: bool,
}

impl Default for ClaudeCodeConfig {
    fn default() -> Self {
        Self {
            websocket_url: std::env::var("CLAUDE_CODE_WEBSOCKET_URL")
                .unwrap_or_else(|_| "ws://localhost:8080".to_string()),
            auth_token: std::env::var("CLAUDE_CODE_AUTH_TOKEN").ok(),
            max_sessions: 10,
            idle_timeout_seconds: 300, // 5 minutes
            track_costs: true,
        }
    }
}

/// Claude Code connector - manages sessions and WebSocket connections
pub struct ClaudeCodeConnector {
    config: ClaudeCodeConfig,
    sessions: Arc<RwLock<HashMap<String, ClaudeCodeSession>>>,
    active_connections: Arc<Mutex<HashMap<String, Arc<Mutex<WebSocketStream<MaybeTlsStream<TcpStream>>>>>>>,
}

impl ClaudeCodeConnector {
    /// Create a new Claude Code connector
    pub fn new(config: ClaudeCodeConfig) -> Self {
        Self {
            config,
            sessions: Arc::new(RwLock::new(HashMap::new())),
            active_connections: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Create a new Claude Code session
    pub async fn create_session(&self, user_id: String, project_path: String) -> Result<ClaudeCodeSession> {
        // Check session limit
        let sessions = self.sessions.read().await;
        if sessions.len() >= self.config.max_sessions {
            return Err(anyhow::anyhow!(
                "Maximum number of Claude Code sessions ({}) reached",
                self.config.max_sessions
            ));
        }
        drop(sessions);

        // Create new session
        let session = ClaudeCodeSession::new(user_id, project_path);
        let session_id = session.id.clone();

        info!(
            session_id = %session_id,
            user_id = %session.user_id,
            project_path = %session.project_path,
            "Creating new Claude Code session"
        );

        // Store session
        let mut sessions = self.sessions.write().await;
        sessions.insert(session_id.clone(), session.clone());

        Ok(session)
    }

    /// Connect to Claude Code WebSocket
    pub async fn connect_session(&self, session_id: &str) -> Result<()> {
        let mut sessions = self.sessions.write().await;
        let session = sessions.get_mut(session_id)
            .ok_or_else(|| anyhow::anyhow!("Session not found: {}", session_id))?;

        // Update status
        session.status = SessionStatus::Connecting;
        drop(sessions);

        info!(
            session_id = %session_id,
            url = %self.config.websocket_url,
            "Connecting to Claude Code WebSocket"
        );

        // Connect to WebSocket
        let (ws_stream, _) = connect_async(&self.config.websocket_url)
            .await
            .context("Failed to connect to Claude Code WebSocket")?;

        info!(session_id = %session_id, "WebSocket connection established");

        // Store connection
        let mut connections = self.active_connections.lock().await;
        connections.insert(session_id.to_string(), Arc::new(Mutex::new(ws_stream)));

        // Update session status
        let mut sessions = self.sessions.write().await;
        if let Some(session) = sessions.get_mut(session_id) {
            session.status = SessionStatus::Active;
        }

        Ok(())
    }

    /// Send message to Claude Code session
    pub async fn send_message(&self, session_id: &str, content: String, context: Option<HashMap<String, String>>) -> Result<ClaudeCodeMessage> {
        // Get session
        let mut sessions = self.sessions.write().await;
        let session = sessions.get_mut(session_id)
            .ok_or_else(|| anyhow::anyhow!("Session not found: {}", session_id))?;

        if !session.is_active() {
            return Err(anyhow::anyhow!("Session is not active: {}", session_id));
        }

        // Update activity
        session.update_activity();
        drop(sessions);

        // Create message
        let message = ClaudeCodeMessage {
            id: Uuid::new_v4().to_string(),
            session_id: session_id.to_string(),
            content: content.clone(),
            timestamp: Utc::now(),
            context,
        };

        debug!(
            session_id = %session_id,
            message_id = %message.id,
            content_length = content.len(),
            "Sending message to Claude Code"
        );

        // Get WebSocket connection
        let connections = self.active_connections.lock().await;
        let ws_conn = connections.get(session_id)
            .ok_or_else(|| anyhow::anyhow!("No active connection for session: {}", session_id))?;

        // Send message
        let json = serde_json::to_string(&message)?;
        let mut ws_stream = ws_conn.lock().await;
        ws_stream.send(WsMessage::Text(json)).await
            .context("Failed to send message to Claude Code")?;

        Ok(message)
    }

    /// Receive response from Claude Code session
    pub async fn receive_response(&self, session_id: &str) -> Result<Option<ClaudeCodeResponse>> {
        // Get WebSocket connection
        let connections = self.active_connections.lock().await;
        let ws_conn = connections.get(session_id)
            .ok_or_else(|| anyhow::anyhow!("No active connection for session: {}", session_id))?;

        // Receive message
        let mut ws_stream = ws_conn.lock().await;
        match ws_stream.next().await {
            Some(Ok(WsMessage::Text(text))) => {
                let response: ClaudeCodeResponse = serde_json::from_str(&text)
                    .context("Failed to parse Claude Code response")?;

                debug!(
                    session_id = %session_id,
                    response_id = %response.id,
                    status = %response.status,
                    "Received response from Claude Code"
                );

                // Update cost if provided
                if let Some(cost) = response.cost_usd {
                    let mut sessions = self.sessions.write().await;
                    if let Some(session) = sessions.get_mut(session_id) {
                        session.add_cost(cost);
                    }
                }

                Ok(Some(response))
            }
            Some(Ok(WsMessage::Close(_))) => {
                info!(session_id = %session_id, "Claude Code connection closed");
                self.disconnect_session(session_id).await?;
                Ok(None)
            }
            Some(Ok(_)) => {
                warn!(session_id = %session_id, "Received unexpected message type");
                Ok(None)
            }
            Some(Err(e)) => {
                error!(session_id = %session_id, error = ?e, "WebSocket error");
                Err(anyhow::anyhow!("WebSocket error: {}", e))
            }
            None => Ok(None),
        }
    }

    /// Disconnect Claude Code session
    pub async fn disconnect_session(&self, session_id: &str) -> Result<()> {
        info!(session_id = %session_id, "Disconnecting Claude Code session");

        // Close WebSocket connection
        let mut connections = self.active_connections.lock().await;
        if let Some(ws_conn) = connections.remove(session_id) {
            let mut ws_stream = ws_conn.lock().await;
            let _ = ws_stream.close(None).await;
        }

        // Update session
        let mut sessions = self.sessions.write().await;
        if let Some(session) = sessions.get_mut(session_id) {
            session.end_session();
        }

        Ok(())
    }

    /// Get session by ID
    pub async fn get_session(&self, session_id: &str) -> Option<ClaudeCodeSession> {
        let sessions = self.sessions.read().await;
        sessions.get(session_id).cloned()
    }

    /// Get all sessions for a user
    pub async fn get_user_sessions(&self, user_id: &str) -> Vec<ClaudeCodeSession> {
        let sessions = self.sessions.read().await;
        sessions.values()
            .filter(|s| s.user_id == user_id)
            .cloned()
            .collect()
    }

    /// Get all active sessions
    pub async fn get_active_sessions(&self) -> Vec<ClaudeCodeSession> {
        let sessions = self.sessions.read().await;
        sessions.values()
            .filter(|s| s.is_active())
            .cloned()
            .collect()
    }

    /// Calculate total cost for a user
    pub async fn get_user_total_cost(&self, user_id: &str) -> f64 {
        let sessions = self.sessions.read().await;
        sessions.values()
            .filter(|s| s.user_id == user_id)
            .map(|s| s.cost_usd)
            .sum()
    }

    /// Clean up idle sessions
    pub async fn cleanup_idle_sessions(&self) -> Result<usize> {
        let idle_threshold = chrono::Duration::seconds(self.config.idle_timeout_seconds as i64);
        let now = Utc::now();
        let mut cleaned = 0;

        let sessions = self.sessions.read().await;
        let idle_sessions: Vec<String> = sessions.values()
            .filter(|s| s.is_active() && (now - s.last_activity) > idle_threshold)
            .map(|s| s.id.clone())
            .collect();
        drop(sessions);

        for session_id in idle_sessions {
            info!(session_id = %session_id, "Cleaning up idle session");
            if let Err(e) = self.disconnect_session(&session_id).await {
                error!(session_id = %session_id, error = ?e, "Failed to disconnect idle session");
            } else {
                cleaned += 1;
            }
        }

        Ok(cleaned)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_creation() {
        let session = ClaudeCodeSession::new(
            "user123".to_string(),
            "/path/to/project".to_string()
        );

        assert_eq!(session.user_id, "user123");
        assert_eq!(session.project_path, "/path/to/project");
        assert_eq!(session.status, SessionStatus::Connecting);
        assert_eq!(session.cost_usd, 0.0);
        assert_eq!(session.message_count, 0);
        assert!(session.ended_at.is_none());
    }

    #[test]
    fn test_session_activity() {
        let mut session = ClaudeCodeSession::new(
            "user123".to_string(),
            "/path/to/project".to_string()
        );

        let initial_count = session.message_count;
        session.update_activity();
        assert_eq!(session.message_count, initial_count + 1);
    }

    #[test]
    fn test_session_cost() {
        let mut session = ClaudeCodeSession::new(
            "user123".to_string(),
            "/path/to/project".to_string()
        );

        session.add_cost(0.5);
        assert_eq!(session.cost_usd, 0.5);

        session.add_cost(0.3);
        assert_eq!(session.cost_usd, 0.8);
    }

    #[test]
    fn test_session_end() {
        let mut session = ClaudeCodeSession::new(
            "user123".to_string(),
            "/path/to/project".to_string()
        );

        session.status = SessionStatus::Active;
        assert!(session.is_active());

        session.end_session();
        assert!(!session.is_active());
        assert_eq!(session.status, SessionStatus::Disconnected);
        assert!(session.ended_at.is_some());
    }

    #[tokio::test]
    async fn test_connector_creation() {
        let config = ClaudeCodeConfig::default();
        let connector = ClaudeCodeConnector::new(config);

        let sessions = connector.sessions.read().await;
        assert_eq!(sessions.len(), 0);
    }

    #[tokio::test]
    async fn test_create_session() {
        let config = ClaudeCodeConfig::default();
        let connector = ClaudeCodeConnector::new(config);

        let session = connector.create_session(
            "user123".to_string(),
            "/path/to/project".to_string()
        ).await.unwrap();

        assert_eq!(session.user_id, "user123");
        assert_eq!(session.project_path, "/path/to/project");

        let stored_session = connector.get_session(&session.id).await;
        assert!(stored_session.is_some());
    }

    #[tokio::test]
    async fn test_get_user_sessions() {
        let config = ClaudeCodeConfig::default();
        let connector = ClaudeCodeConnector::new(config);

        connector.create_session("user1".to_string(), "/proj1".to_string()).await.unwrap();
        connector.create_session("user1".to_string(), "/proj2".to_string()).await.unwrap();
        connector.create_session("user2".to_string(), "/proj3".to_string()).await.unwrap();

        let user1_sessions = connector.get_user_sessions("user1").await;
        assert_eq!(user1_sessions.len(), 2);

        let user2_sessions = connector.get_user_sessions("user2").await;
        assert_eq!(user2_sessions.len(), 1);
    }

    #[tokio::test]
    async fn test_user_total_cost() {
        let config = ClaudeCodeConfig::default();
        let connector = ClaudeCodeConnector::new(config);

        let session1 = connector.create_session("user1".to_string(), "/proj1".to_string()).await.unwrap();
        let session2 = connector.create_session("user1".to_string(), "/proj2".to_string()).await.unwrap();

        {
            let mut sessions = connector.sessions.write().await;
            sessions.get_mut(&session1.id).unwrap().add_cost(0.5);
            sessions.get_mut(&session2.id).unwrap().add_cost(0.3);
        }

        let total_cost = connector.get_user_total_cost("user1").await;
        assert_eq!(total_cost, 0.8);
    }
}
