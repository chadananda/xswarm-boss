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

# === Package Distribution ===

# Build .deb package
package-deb:
    @echo "📦 Building .deb package..."
    @echo "Building docs..."
    cd packages/docs && pnpm install && pnpm build
    @echo "Building Rust binary..."
    cargo build --release
    @echo "Creating .deb package..."
    cargo install cargo-deb || true
    cargo deb -p xswarm
    @echo "✅ .deb package created in target/debian/"

# Build AUR package (creates tarball for AUR submission)
package-aur:
    @echo "📦 Preparing AUR package..."
    @echo "Building docs..."
    cd packages/docs && pnpm install && pnpm build
    @echo "Building release tarball..."
    git archive --format=tar.gz --prefix=xswarm-boss-0.1.0/ HEAD > xswarm-boss-0.1.0.tar.gz
    @echo "Updating PKGBUILD checksum..."
    cd distribution/aur && makepkg --printsrcinfo > .SRCINFO
    @echo "✅ AUR package prepared in distribution/aur/"
    @echo "Upload xswarm-boss-0.1.0.tar.gz to GitHub releases"
    @echo "Then update AUR repository with distribution/aur/{PKGBUILD,.SRCINFO}"

# Build static binary (musl)
package-static:
    @echo "📦 Building static binary..."
    @echo "Installing cross if needed..."
    cargo install cross || true
    @echo "Building for x86_64-unknown-linux-musl..."
    cross build --release --target x86_64-unknown-linux-musl
    @echo "Building for aarch64-unknown-linux-musl..."
    cross build --release --target aarch64-unknown-linux-musl
    @echo "Building docs..."
    cd packages/docs && pnpm install && pnpm build
    @echo "Creating tarballs..."
    mkdir -p dist
    tar czf dist/xswarm-x86_64-linux-musl.tar.gz \
        -C target/x86_64-unknown-linux-musl/release xswarm \
        -C ../../../packages/docs/dist . \
        -C ../../../distribution/systemd xswarm.service xswarm.socket \
        -C ../.. install.sh
    tar czf dist/xswarm-aarch64-linux-musl.tar.gz \
        -C target/aarch64-unknown-linux-musl/release xswarm \
        -C ../../../packages/docs/dist . \
        -C ../../../distribution/systemd xswarm.service xswarm.socket \
        -C ../.. install.sh
    @echo "✅ Static binaries created in dist/"

# Build Flatpak package
package-flatpak:
    @echo "📦 Building Flatpak package..."
    flatpak-builder --force-clean --repo=repo build-dir distribution/flatpak/org.xswarm.Boss.yml
    flatpak build-bundle repo xswarm-boss.flatpak org.xswarm.Boss
    @echo "✅ Flatpak package created: xswarm-boss.flatpak"

# Build all packages
package-all: package-deb package-static
    @echo "✅ All packages built!"
    @echo ""
    @echo "Debian package: target/debian/"
    @echo "Static binaries: dist/"
    @echo ""
    @echo "To build AUR and Flatpak packages:"
    @echo "  just package-aur"
    @echo "  just package-flatpak"
