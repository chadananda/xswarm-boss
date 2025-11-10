/// Network utilities for robust socket binding
///
/// This module provides utilities for creating TCP listeners with proper
/// socket options to handle port binding issues gracefully.

use anyhow::{Context, Result};
use socket2::{Domain, Socket, Type};
use std::net::SocketAddr;
use std::time::Duration;
use tokio::net::TcpListener;
use tracing::{info, warn};

/// Maximum number of retry attempts for port binding
const MAX_BIND_RETRIES: u32 = 5;

/// Delay between retry attempts in milliseconds
const RETRY_DELAY_MS: u64 = 1000;

/// Create a TCP listener with SO_REUSEADDR and retry logic
///
/// This function creates a TCP listener with the following features:
/// - SO_REUSEADDR enabled to allow immediate port reuse after program exit
/// - Retry logic with exponential backoff to handle transient binding failures
/// - Proper error context for debugging
///
/// # Arguments
/// * `addr` - The socket address to bind to (e.g., "127.0.0.1:9998")
///
/// # Returns
/// A tokio TcpListener ready to accept connections
///
/// # Example
/// ```ignore
/// let listener = create_reusable_tcp_listener("127.0.0.1:9998").await?;
/// loop {
///     let (stream, _) = listener.accept().await?;
///     // handle connection
/// }
/// ```
pub async fn create_reusable_tcp_listener(addr: &str) -> Result<TcpListener> {
    let socket_addr: SocketAddr = addr
        .parse()
        .with_context(|| format!("Invalid socket address: {}", addr))?;

    let mut last_error = None;

    for attempt in 1..=MAX_BIND_RETRIES {
        match try_bind_socket(&socket_addr).await {
            Ok(listener) => {
                if attempt > 1 {
                    info!(
                        addr = %addr,
                        attempt = attempt,
                        "Successfully bound to port after retry"
                    );
                }
                return Ok(listener);
            }
            Err(e) => {
                last_error = Some(e);
                if attempt < MAX_BIND_RETRIES {
                    let delay_ms = RETRY_DELAY_MS * (attempt as u64);
                    warn!(
                        addr = %addr,
                        attempt = attempt,
                        max_retries = MAX_BIND_RETRIES,
                        retry_in_ms = delay_ms,
                        error = ?last_error,
                        "Failed to bind port, retrying..."
                    );
                    tokio::time::sleep(Duration::from_millis(delay_ms)).await;
                }
            }
        }
    }

    Err(last_error.unwrap_or_else(|| {
        anyhow::anyhow!("Failed to bind to {} after {} attempts", addr, MAX_BIND_RETRIES)
    }))
}

/// Internal function to attempt binding a socket once
async fn try_bind_socket(socket_addr: &SocketAddr) -> Result<TcpListener> {
    // Determine the domain (IPv4 or IPv6)
    let domain = if socket_addr.is_ipv4() {
        Domain::IPV4
    } else {
        Domain::IPV6
    };

    // Create a new socket
    let socket = Socket::new(domain, Type::STREAM, None)
        .context("Failed to create socket")?;

    // Enable SO_REUSEADDR - this is the critical fix!
    // This allows the port to be reused immediately after the previous process exits,
    // even if the OS hasn't fully cleaned up the TIME_WAIT state.
    socket
        .set_reuse_address(true)
        .context("Failed to set SO_REUSEADDR")?;

    // On Unix systems, also enable SO_REUSEPORT for better load balancing
    #[cfg(unix)]
    {
        socket
            .set_reuse_port(true)
            .context("Failed to set SO_REUSEPORT")?;
    }

    // Set the socket to non-blocking mode for tokio
    socket
        .set_nonblocking(true)
        .context("Failed to set non-blocking mode")?;

    // Bind the socket
    socket
        .bind(&(*socket_addr).into())
        .with_context(|| format!("Failed to bind to {}", socket_addr))?;

    // Start listening
    socket
        .listen(128) // backlog of 128 pending connections
        .context("Failed to listen on socket")?;

    // Convert socket2::Socket to std::net::TcpListener
    let std_listener: std::net::TcpListener = socket.into();

    // Convert std::net::TcpListener to tokio::net::TcpListener
    let tokio_listener = TcpListener::from_std(std_listener)
        .context("Failed to convert to tokio TcpListener")?;

    Ok(tokio_listener)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_listener() {
        // Use a random high port for testing
        let addr = "127.0.0.1:0"; // Port 0 means OS will assign a free port
        let listener = create_reusable_tcp_listener(addr).await;
        assert!(listener.is_ok());
    }

    #[tokio::test]
    async fn test_reuse_address() {
        // Bind to a specific port
        let addr = "127.0.0.1:19998"; // Use high port for testing

        // Create first listener
        let listener1 = create_reusable_tcp_listener(addr).await;
        assert!(listener1.is_ok());

        // Drop first listener
        drop(listener1);

        // Immediately try to bind again - this should work due to SO_REUSEADDR
        let listener2 = create_reusable_tcp_listener(addr).await;
        assert!(listener2.is_ok(), "SO_REUSEADDR should allow immediate rebind");
    }
}
