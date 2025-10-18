# xSwarm-boss Task Runner
# Install just: cargo install just
# Usage: just <command>

# Default recipe (list all recipes)
default:
    @just --list

# Build all packages (Rust + Node)
build:
    @echo "🔨 Building all packages..."
    cargo build --workspace
    pnpm -r run build

# Build Rust packages in release mode
build-release:
    @echo "🚀 Building release binaries..."
    cargo build --workspace --release

# Run all tests
test:
    @echo "🧪 Running all tests..."
    cargo test --workspace
    pnpm -r run test

# Start development environment (Docker Compose)
dev:
    @echo "🐳 Starting development environment..."
    docker compose up -d
    @echo "✅ Services running:"
    @echo "   - Meilisearch: http://localhost:7700"
    @echo "   - LibSQL: http://localhost:8080"

# Stop development environment
dev-stop:
    @echo "🛑 Stopping development environment..."
    docker compose down

# Build Docker Arch Linux development container
docker-build:
    @echo "🐳 Building Arch Linux dev container..."
    docker compose build archlinux-dev

# Open interactive shell in Arch Linux container
docker-shell:
    @echo "🐚 Opening shell in Arch Linux container..."
    docker compose run --rm archlinux-dev bash

# Run tests in Docker container
docker-test:
    @echo "🧪 Running tests in Docker..."
    docker compose run --rm archlinux-dev cargo test --workspace

# Clean build artifacts
clean:
    @echo "🧹 Cleaning build artifacts..."
    cargo clean
    pnpm -r run clean
    rm -rf target/
    rm -rf packages/*/target/

# Format code
format:
    @echo "✨ Formatting code..."
    cargo fmt --all
    pnpm run format

# Check code (clippy + tsc)
check:
    @echo "🔍 Checking code..."
    cargo clippy --workspace --all-targets
    pnpm -r run check || true

# Run xSwarm CLI
run *ARGS:
    cargo run --package xswarm -- {{ARGS}}

# Install development dependencies
setup:
    @echo "🚀 Setting up development environment..."
    @echo "Installing Rust dependencies..."
    cargo fetch
    @echo "Installing Node.js dependencies..."
    pnpm install
    @echo "✅ Setup complete!"

# Show project status
status:
    @echo "📊 xSwarm-boss Status"
    @echo ""
    @echo "Git:"
    @git status --short
    @echo ""
    @echo "Docker:"
    @docker compose ps || echo "Docker Compose not running"
