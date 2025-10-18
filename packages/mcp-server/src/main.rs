use anyhow::Result;
use axum::{routing::get, Router};
use tracing::{info, Level};
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    info!("Starting xSwarm MCP Server...");

    // Build application with routes
    let app = Router::new()
        .route("/", get(health_check))
        .route("/health", get(health_check));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3001")
        .await?;

    info!("MCP Server listening on http://{}", listener.local_addr()?);

    axum::serve(listener, app).await?;

    Ok(())
}

async fn health_check() -> &'static str {
    "xSwarm MCP Server - OK"
}
