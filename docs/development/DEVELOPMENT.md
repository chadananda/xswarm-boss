# xSwarm Development Guide

Welcome to xSwarm development! This guide will help you set up a cross-platform development environment for building, testing, and extending xSwarm.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss

# 2. Install dependencies
just setup

# 3. Build for your platform
just build

# 4. Run xSwarm
cargo run -- --help
```

## Table of Contents

- [Platform Requirements](#platform-requirements)
- [Development Environment Setup](#development-environment-setup)
- [Building for Different Platforms](#building-for-different-platforms)
- [AI API Configuration](#ai-api-configuration)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Platform Requirements

### macOS (Recommended for Development)

**Minimum:**
- macOS 12.0+ (Monterey or later)
- Apple Silicon (M1/M2/M3) or Intel x86_64
- 8GB RAM minimum, 16GB recommended

**Required Tools:**
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Just (task runner)
brew install just

# Install pnpm (Node.js package manager)
brew install pnpm

# Install Docker Desktop (optional, for dev services)
brew install --cask docker
```

### Linux

**Supported Distributions:**
- Arch Linux (primary development)
- Ubuntu 22.04+ / Debian 12+
- Fedora 38+

**Required Tools:**

**Arch Linux:**
```bash
sudo pacman -S rust just pnpm docker docker-compose
```

**Ubuntu/Debian:**
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Just
cargo install just

# Install pnpm
curl -fsSL https://get.pnpm.io/install.sh | sh -

# Install Docker
sudo apt-get install docker.io docker-compose
```

### Windows (Testing Only)

**Note:** Windows support is primarily for testing builds. Active development on Windows is not fully supported yet.

**Required:**
- Windows 10/11 with WSL2 (Ubuntu recommended)
- Follow Linux instructions inside WSL2

---

## Development Environment Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss

# Install all dependencies (Rust + Node.js)
just setup
```

### 2. Verify Installation

```bash
# Check platform detection
just platform-info

# Build all packages
just build

# Run tests
just test
```

### 3. Start Development Services (Optional)

xSwarm uses Docker Compose for optional development services (Meilisearch for search, LibSQL for database).

```bash
# Start services
just dev

# Verify services are running
just status

# Stop services when done
just dev-stop
```

**Services:**
- **Meilisearch** (vector search): http://localhost:7700
- **LibSQL** (database): http://localhost:8080

---

## Building for Different Platforms

### Check Your Platform

```bash
just platform-info
```

### macOS Builds

**Apple Silicon (M1/M2/M3):**
```bash
just build-macos-arm
```

**Intel:**
```bash
just build-macos-intel
```

**Universal Binary (both architectures):**
```bash
just build-macos-universal
```

Binary location: `target/universal-apple-darwin/release/xswarm`

### Linux Builds

**x86_64:**
```bash
just build-linux
```

**ARM64:**
```bash
just build-linux-arm
```

### Windows Builds

**From macOS/Linux (cross-compilation):**
```bash
# Install cross tool (first time only)
cargo install cross

# Build for Windows
just build-windows
```

Binary location: `target/x86_64-pc-windows-gnu/release/xswarm.exe`

### Build All Platforms

```bash
just build-all-platforms
```

This creates binaries for:
- macOS Universal (Apple Silicon + Intel)
- Windows x86_64
- Linux x86_64

---

## AI API Configuration

xSwarm integrates with Anthropic Claude and OpenAI for natural language interaction. Voice features are currently stubbed, but text-based AI (`ask` and `do` commands) work with API keys.

### Anthropic (Recommended)

**Get API Key:**
1. Sign up at https://console.anthropic.com/
2. Generate an API key
3. Set environment variable:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Add to shell profile (persistent):**

**macOS/Linux (bash/zsh):**
```bash
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### OpenAI (Alternative)

```bash
export OPENAI_API_KEY='your-api-key-here'

# Configure xSwarm to use OpenAI
xswarm config set voice.provider openai
```

### Test AI Integration

```bash
# Build xSwarm
cargo build --release

# Try asking a question
cargo run --release -- ask "What is xSwarm?"

# Try a task
cargo run --release -- do "analyze my git history"
```

### No API Key Development

If you don't have an API key yet, you can still:
- ✅ Build and run xSwarm CLI
- ✅ Manage personas
- ✅ Configure settings
- ✅ Work on UI/TUI components
- ✅ Test configuration system
- ❌ Use `ask` or `do` commands (requires API key)

---

## Development Workflow

### Recommended Workflow

```bash
# 1. Start development services
just dev

# 2. Make changes to code

# 3. Run tests
just test

# 4. Format code
just format

# 5. Check for issues
just check

# 6. Build
just build

# 7. Test locally
cargo run -- persona list
cargo run -- config show
```

### Project Structure

```
xswarm-boss/
├── packages/
│   ├── core/              # Main Rust binary (xswarm CLI)
│   │   ├── src/
│   │   │   ├── main.rs    # CLI entry point
│   │   │   ├── ai.rs      # AI API integration
│   │   │   ├── config.rs  # Configuration management
│   │   │   ├── platform.rs # Platform detection
│   │   │   └── docs.rs    # Documentation indexing
│   │   └── Cargo.toml
│   ├── mcp-server/        # MCP isolation server (stub)
│   ├── indexer/           # Semantic search library
│   ├── personas/          # AI personality themes
│   └── docs/              # Documentation site
├── distribution/          # Packaging configs
├── planning/              # Design documents
├── justfile               # Task runner
├── Cargo.toml             # Rust workspace
└── pnpm-workspace.yaml    # Node.js workspace
```

### Key Files

| File | Purpose |
|------|---------|
| `packages/core/src/main.rs` | CLI commands and entry point |
| `packages/core/src/ai.rs` | AI API integration (Anthropic/OpenAI) |
| `packages/core/src/config.rs` | TOML configuration system |
| `packages/core/src/platform.rs` | Cross-platform compatibility |
| `justfile` | Build and task automation |

### Common Tasks

```bash
# Development
just run ask "test query"       # Run with arguments
just run config show            # Show configuration
just run persona list           # List personas

# Build variants
just build                      # Debug build (fast)
just build-release             # Release build (optimized)
just build-native              # Native platform only

# Code quality
just format                    # Format all code
just check                     # Lint with clippy
just test                      # Run all tests

# Cleaning
just clean                     # Remove build artifacts
```

---

## Testing

### Run All Tests

```bash
just test
```

### Run Specific Tests

```bash
# Rust tests only
cargo test --workspace

# With logging
RUST_LOG=debug cargo test --workspace

# Specific package
cargo test -p xswarm

# Specific test
cargo test test_platform_detection
```

### Docker Testing (Linux)

```bash
# Build Arch Linux dev container
just docker-build

# Run tests in container
just docker-test

# Interactive shell in container
just docker-shell
```

---

## Feature Status

### ✅ Implemented

- [x] Cross-platform builds (Mac, Linux, Windows)
- [x] Configuration system (TOML)
- [x] Persona/theme system (10 characters)
- [x] CLI framework
- [x] AI integration (Anthropic Claude, OpenAI)
- [x] Platform detection
- [x] Basic documentation indexing

### 🚧 In Progress

- [ ] Ratatui TUI Dashboard
- [ ] Voice interface (stubbed)
- [ ] Multi-machine orchestration
- [ ] Memory system

### 📋 Planned

- [ ] Full MCP server implementation
- [ ] Search UI integration
- [ ] Desktop environment integration
- [ ] Package distribution (AUR, Flatpak, Homebrew)

---

## Stubbed Features

These features have configuration and stub implementations, but are not yet functional:

### Voice Interface

**Status:** Configuration exists, implementation stubbed

The voice system is designed but not implemented. Configuration is in place:

```toml
[voice]
provider = "openai_realtime"
model = "gpt-4o-realtime-preview"

[audio]
input_device = "default"
output_device = "default"
sample_rate = 16000

[wake_word]
engine = "porcupine"
sensitivity = 0.5
```

**To contribute voice implementation:**
- See `packages/core/src/ai.rs` (VoiceClient stub)
- See `planning/ARCHITECTURE.md` for design
- Options: OpenAI Realtime, STT→LLM→TTS pipeline, or local (MOSHI)

### Search/Indexing

**Status:** Backend implemented, UI stubbed

The `packages/indexer` library is functional with Meilisearch integration, but there's no UI yet.

**To develop search UI:**
- Indexer API: `packages/indexer/src/client.rs`
- Dashboard integration needed in `packages/core/src/main.rs`

---

## Troubleshooting

### Common Issues

**"cross-compilation requires cross or cargo-xwin"**
```bash
cargo install cross
```

**"API key not configured"**
```bash
export ANTHROPIC_API_KEY='your-key'
# Or
export OPENAI_API_KEY='your-key'
```

**"Docker services not starting"**
```bash
# Check Docker is running
docker ps

# Restart services
just dev-stop
just dev
```

**"lipo: can't open input file"** (macOS Universal Build)
```bash
# Make sure both architectures are built first
rustup target add aarch64-apple-darwin
rustup target add x86_64-apple-darwin
```

**Build fails on Linux with musl target**
```bash
# Install musl toolchain
rustup target add x86_64-unknown-linux-musl
```

### Getting Help

- **Documentation:** See `planning/` directory for detailed design docs
- **Issues:** https://github.com/chadananda/xswarm-boss/issues
- **Architecture:** See `planning/ARCHITECTURE.md`
- **Features:** See `planning/FEATURES.md`

---

## Contributing

### Before Contributing

1. Read `planning/CODESTYLE.md` for coding standards
2. Review `planning/ARCHITECTURE.md` for system design
3. Check `planning/TODO.md` for current priorities

### Development Cycle

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes and test
just test

# 3. Format and check
just format
just check

# 4. Commit with descriptive message
git commit -m "feat: add voice recognition stub"

# 5. Push and create PR
git push origin feature/my-feature
```

### Testing Checklist

- [ ] Code compiles on your platform
- [ ] Tests pass (`just test`)
- [ ] Code is formatted (`just format`)
- [ ] No clippy warnings (`just check`)
- [ ] Documentation updated if needed

---

## Platform-Specific Notes

### macOS

- **Apple Silicon** is the primary development platform
- Use `just build-macos-arm` for fastest builds
- Intel builds work via Rosetta but are slower
- Docker Desktop required for dev services

### Linux

- **Arch Linux** is the primary testing platform
- systemd integration only works on Linux
- Use `just docker-shell` for containerized testing
- Flatpak/AppImage builds planned

### Windows

- **WSL2** required for development
- Native Windows builds are for testing only
- Voice features may not work natively yet
- Use Linux commands inside WSL2

---

## What to Work On

### Good First Issues

- [ ] Improve platform detection edge cases
- [ ] Add more persona personalities
- [ ] Write integration tests
- [ ] Improve error messages
- [ ] Add configuration validation

### High Priority

- [ ] Ratatui TUI implementation
- [ ] Voice interface (any backend)
- [ ] Search UI integration
- [ ] Memory system foundation

### Advanced

- [ ] Multi-machine WebSocket orchestration
- [ ] MCP server implementation
- [ ] Desktop environment integration
- [ ] Package distribution

---

## Resources

### Documentation

- [Architecture](planning/ARCHITECTURE.md) - System design
- [Features](planning/FEATURES.md) - Feature roadmap
- [PRD](planning/PRD.md) - Product requirements
- [Security](planning/SECURITY.md) - Security model
- [Testing](planning/TESTING.md) - Test strategy

### Tools

- [Just](https://github.com/casey/just) - Task runner
- [Ratatui](https://ratatui.rs/) - Terminal UI
- [Clap](https://docs.rs/clap/) - CLI framework
- [Tokio](https://tokio.rs/) - Async runtime
- [Anthropic](https://docs.anthropic.com/) - Claude API

---

## Quick Reference

```bash
# Setup
just setup                    # Install dependencies
just platform-info            # Check platform

# Building
just build                    # Debug build
just build-release            # Release build
just build-macos-arm          # macOS Apple Silicon
just build-windows            # Windows cross-compile
just build-all-platforms      # All platforms

# Development
just dev                      # Start services
just dev-stop                 # Stop services
just run <args>              # Run xSwarm
just test                     # Run tests
just format                   # Format code
just check                    # Lint code

# Cleaning
just clean                    # Remove artifacts

# Packages
just package-deb             # Debian package
just package-static          # Static binaries
just package-all             # All packages
```

---

Happy hacking! 🚀
