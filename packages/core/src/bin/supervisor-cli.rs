// Supervisor CLI - Monitor and Control MOSHI Voice Conversations
//
// This CLI tool allows Claude Code to monitor MOSHI conversations
// and inject suggestions in real-time.
//
// Usage:
//   cargo run --bin supervisor-cli
//
// Interactive commands:
//   i <text>  - Inject suggestion
//   q         - Quit
//   h         - Help

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::io::{self, Write};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures_util::{SinkExt, StreamExt};
use url::Url;

/// Supervisor message types (incoming from MOSHI)
#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum SupervisorEvent {
    AuthResult {
        success: bool,
        message: String,
    },
    UserSpeech {
        duration_ms: u64,
        timestamp: String,
    },
    SuggestionApplied {
        text: String,
        timestamp: String,
    },
    SuggestionRejected {
        reason: String,
    },
    Pong,
    Error {
        message: String,
    },
}

/// Supervisor commands (outgoing to MOSHI)
#[derive(Debug, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum SupervisorMessage {
    Auth {
        token: String,
    },
    InjectSuggestion {
        text: String,
        #[serde(default)]
        priority: String,
    },
    Ping,
}

fn print_header() {
    println!("\n╔══════════════════════════════════════════════════════════╗");
    println!("║           MOSHI SUPERVISOR - CLI Monitor                 ║");
    println!("║                                                          ║");
    println!("║  Monitor and inject suggestions into MOSHI conversations ║");
    println!("╚══════════════════════════════════════════════════════════╝\n");
}

fn print_help() {
    println!("\n┌─ Commands ────────────────────────────────────────────┐");
    println!("│  i <text>     Inject suggestion into MOSHI            │");
    println!("│  q            Quit the CLI                            │");
    println!("│  h            Show this help message                  │");
    println!("│  clear        Clear the screen                        │");
    println!("└───────────────────────────────────────────────────────┘\n");
}

fn format_timestamp(iso8601: &str) -> String {
    // Extract just time portion (HH:MM:SS)
    iso8601
        .split('T')
        .nth(1)
        .and_then(|t| t.split('.').next())
        .unwrap_or(iso8601)
        .to_string()
}

#[tokio::main]
async fn main() -> Result<()> {
    // Configuration
    let host = std::env::var("SUPERVISOR_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let port = std::env::var("SUPERVISOR_PORT").unwrap_or_else(|_| "9999".to_string());
    let token = std::env::var("SUPERVISOR_TOKEN").unwrap_or_else(|_| "dev-token-12345".to_string());

    print_header();

    // Connect to supervisor WebSocket
    let url = format!("ws://{}:{}", host, port);
    println!("🔌 Connecting to supervisor at {}", url);

    let url = Url::parse(&url)?;
    let (ws_stream, _) = connect_async(url)
        .await
        .context("Failed to connect to supervisor")?;

    println!("✓ Connected to supervisor WebSocket");

    let (mut ws_sender, mut ws_receiver) = ws_stream.split();

    // Authenticate
    let auth_msg = serde_json::to_string(&SupervisorMessage::Auth {
        token: token.clone(),
    })?;
    ws_sender.send(Message::Text(auth_msg)).await?;

    println!("🔐 Authenticating...");

    // Wait for auth response
    if let Some(msg) = ws_receiver.next().await {
        match msg {
            Ok(Message::Text(text)) => {
                match serde_json::from_str::<SupervisorEvent>(&text) {
                    Ok(SupervisorEvent::AuthResult { success, message }) => {
                        if success {
                            println!("✓ Authenticated successfully");
                        } else {
                            anyhow::bail!("Authentication failed: {}", message);
                        }
                    }
                    Ok(event) => {
                        println!("⚠ Unexpected event during auth: {:?}", event);
                    }
                    Err(e) => {
                        anyhow::bail!("Failed to parse auth response: {}", e);
                    }
                }
            }
            Ok(Message::Close(_)) => {
                anyhow::bail!("Connection closed during authentication");
            }
            Err(e) => {
                anyhow::bail!("WebSocket error during authentication: {}", e);
            }
            _ => {}
        }
    }

    println!("\n╔══════════════════════════════════════════════════════════╗");
    println!("║                   SUPERVISOR ACTIVE                      ║");
    println!("║                                                          ║");
    println!("║  Monitoring MOSHI voice bridge on port 9998             ║");
    println!("║  Type 'h' for help, 'q' to quit                         ║");
    println!("╚══════════════════════════════════════════════════════════╝\n");

    // Start CLI interaction loop
    let (cmd_tx, mut cmd_rx) = tokio::sync::mpsc::channel::<String>(32);

    // Spawn CLI input handler
    tokio::spawn(async move {
        let stdin = io::stdin();
        loop {
            print!("\n> ");
            io::stdout().flush().unwrap();

            let mut input = String::new();
            if stdin.read_line(&mut input).is_ok() {
                let input = input.trim().to_string();
                if !input.is_empty() {
                    if cmd_tx.send(input).await.is_err() {
                        break;
                    }
                }
            }
        }
    });

    // Main event loop
    loop {
        tokio::select! {
            // Handle WebSocket messages from MOSHI
            Some(msg) = ws_receiver.next() => {
                match msg {
                    Ok(Message::Text(text)) => {
                        match serde_json::from_str::<SupervisorEvent>(&text) {
                            Ok(event) => handle_event(event),
                            Err(e) => {
                                eprintln!("❌ Failed to parse event: {}", e);
                            }
                        }
                    }
                    Ok(Message::Close(_)) => {
                        println!("\n⚠ Connection closed by server");
                        break;
                    }
                    Err(e) => {
                        eprintln!("\n❌ WebSocket error: {}", e);
                        break;
                    }
                    _ => {}
                }
            }

            // Handle CLI commands
            Some(input) = cmd_rx.recv() => {
                if input == "q" || input == "quit" {
                    println!("\n👋 Closing supervisor connection...");
                    break;
                } else if input == "h" || input == "help" {
                    print_help();
                } else if input == "clear" {
                    print!("\x1B[2J\x1B[1;1H");
                    print_header();
                } else if input.starts_with("i ") {
                    let text = input[2..].trim().to_string();
                    if text.is_empty() {
                        println!("❌ No suggestion text provided");
                        continue;
                    }

                    let inject_msg = serde_json::to_string(&SupervisorMessage::InjectSuggestion {
                        text: text.clone(),
                        priority: "normal".to_string(),
                    })?;

                    if let Err(e) = ws_sender.send(Message::Text(inject_msg)).await {
                        eprintln!("❌ Failed to send suggestion: {}", e);
                        break;
                    }

                    println!("📤 Injecting: {}", text);
                } else {
                    println!("❌ Unknown command: '{}'", input);
                    println!("   Type 'h' for help");
                }
            }
        }
    }

    // Send close frame
    let _ = ws_sender.send(Message::Close(None)).await;

    println!("✓ Supervisor CLI disconnected\n");

    Ok(())
}

fn handle_event(event: SupervisorEvent) {
    match event {
        SupervisorEvent::UserSpeech { duration_ms, timestamp } => {
            println!(
                "\n[{}] 🎤 USER: [audio detected - {:.1}s]",
                format_timestamp(&timestamp),
                duration_ms as f64 / 1000.0
            );
        }
        SupervisorEvent::SuggestionApplied { text, timestamp } => {
            println!(
                "\n[{}] ✅ INJECTED: {}",
                format_timestamp(&timestamp),
                text
            );
        }
        SupervisorEvent::SuggestionRejected { reason } => {
            println!("\n❌ REJECTED: {}", reason);
        }
        SupervisorEvent::Pong => {
            // Silent - just connection keepalive
        }
        SupervisorEvent::Error { message } => {
            eprintln!("\n❌ ERROR: {}", message);
        }
        SupervisorEvent::AuthResult { .. } => {
            // Already handled during connection setup
        }
    }
}
