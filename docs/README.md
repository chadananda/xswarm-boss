# xSwarm-Boss Documentation

Welcome to the xSwarm-Boss documentation! This AI-powered voice assistant system combines sophisticated AI agents, a beautiful terminal interface, and seamless integrations to create your personal productivity command center.

## 🚀 Quick Start

**New to xSwarm?** Start here:
- **[Quick Start Guide](quickstart/)** - Get running in 5 minutes
- **[Development Setup](development/guide-development.md)** - Set up your dev environment
- **[Testing Guide](testing/README.md)** - Run tests and verify functionality

## 📚 Documentation Overview

### Getting Started
Quick-start guides for specific features:
- [Buzz Quickstart](quickstart/quickstart-buzz.md) - Community buzz feed
- [Claude Code Integration](quickstart/quickstart-claude-code.md) - AI coding assistant
- [Marketing System](quickstart/quickstart-marketing.md) - Email campaigns
- [Stripe Integration](quickstart/quickstart-stripe.md) - Payments & subscriptions
- [Suggestions Engine](quickstart/quickstart-suggestions.md) - Context-aware AI suggestions
- [Supervisor System](quickstart/quickstart-supervisor.md) - Multi-agent coordination

### Core Features
- **[Dashboard (TUI)](guides/guide-dashboard-implementation.md)** - Terminal user interface with Textual
- **[Persona System](implementations/summary-persona-system.md)** - AI personality switching (JARVIS, GLaDOS, etc.)
- **[Theme System](status/summary-theme-quick.md)** - Dynamic color themes matching personas
- **[Voice Interface (Moshi)](MOSHI_DOWNLOAD_STATUS.md)** - Voice AI with model download infrastructure
- **[Phone Integration](phone-integration.md)** - Interactive phone calls with Twilio + Moshi voice
- **[Authentication](implementations/summary-authentication.md)** - JWT-based auth with session management
- **[Suggestions](implementations/summary-suggestions.md)** - Context-aware AI-powered suggestions
- **[Marketing](implementations/summary-marketing.md)** - Email marketing with SendGrid
- **[Buzz](implementations/summary-buzz.md)** - Community content and listings
- **[Supervisor](planning/system-supervisor.md)** - AI agent coordination system

### Integration & Deployment
- **[Stripe Setup](planning/setups/setup-stripe-products.md)** - Payment processing and subscription tiers
- **[SendGrid Setup](sendgrid/)** - Email delivery configuration
- **[Cloudflare Setup](planning/setups/setup-cloudflare.md)** - CDN and tunnel configuration
- **[Deployment Guide](deployment/guide-deployment.md)** - Production deployment steps
- **[Production Checklist](deployment/checklist-deployment.md)** - Pre-launch verification

### Development
- **[Development Guide](development/guide-development.md)** - Local development setup
- **[Testing Guide](testing/README.md)** - Test strategy and execution
- **[E2E Tests](guides/guide-e2e-tests.md)** - End-to-end testing with pytest-textual
- **[Moshi Model Download](moshi-model-download-lessons.md)** - Large model download strategies and lessons learned
- **[Security](SECURITY.md)** - Security best practices and guidelines

### Planning & Architecture
- **[Complete Specification](planning/specification-complete.md)** - Master technical specification
- **[Architecture](planning/architecture.md)** - System design and components
- **[Database Schema](planning/schema-database.md)** - Data model and relationships
- **[API Documentation](planning/)** - HTTP API endpoints and WebSocket events
- **[Features Roadmap](planning/features.md)** - Planned features and enhancements

## 🏗️ System Architecture

**Current Implementation** (v0.1.0+):
- **Frontend**: Python + Textual (Terminal UI)
- **Backend**: FastAPI (HTTP API) + Cloudflare Workers
- **Database**: SQLite (local) + Turso (LibSQL for cloud)
- **AI**: Anthropic Claude, OpenAI, Perplexity, Gemini
- **Infrastructure**: Cloudflare (CDN, Workers, Tunnels)

**Key Technologies**:
- **Textual** - Rich terminal user interface
- **FastAPI** - Modern Python web framework
- **SQLite/Turso** - Embedded + cloud-sync database
- **WebSockets** - Real-time communication
- **Stripe** - Payment processing
- **SendGrid** - Email delivery
- **Cloudflare** - Global edge network

## 📖 Project Structure

```
docs/
├── README.md (you are here)
├── quickstart/ - Feature-specific quick-start guides
├── development/ - Development setup and guidelines
├── deployment/ - Production deployment guides
├── testing/ - Test strategy and execution
├── planning/ - Architecture, specs, and API docs
├── sendgrid/ - SendGrid email integration
└── archive/ - Historical documentation (Rust era)
    ├── rust-legacy/ - Old Rust implementation docs
    ├── moshi-rust-debugging/ - Audio debugging investigations
    └── sessions/ - Development session logs
```

## 🎨 Features

### Terminal User Interface (TUI)
Beautiful, responsive terminal interface built with Textual:
- **Persona Selection** - Choose AI personality (JARVIS, GLaDOS, HAL 9000, etc.)
- **Theme Switching** - Dynamic colors matching persona
- **Real-time Updates** - WebSocket-powered live data
- **Keyboard Navigation** - Efficient keyboard shortcuts

### AI-Powered Features
- **Voice Interface** - Conversation mode with AI personas
- **Suggestions Engine** - Context-aware recommendations
- **Supervisor System** - Multi-agent task coordination
- **Content Generation** - Marketing copy, emails, blog posts

### Integrations
- **Stripe** - Subscription management (Free, Pro, Enterprise tiers)
- **SendGrid** - Transactional and marketing emails
- **Twilio** - Interactive phone calls with Moshi voice AI
- **Claude Code** - AI coding assistant integration
- **Cloudflare** - Global CDN and secure tunnels

## 🧪 Testing

xSwarm uses comprehensive testing across all layers:
- **Unit Tests** - pytest for business logic
- **Integration Tests** - API endpoint testing
- **E2E Tests** - pytest-textual for TUI testing with SVG snapshots
- **Visual Regression** - Snapshot testing for UI consistency

See [Testing Guide](testing/README.md) for detailed test execution.

## 🔒 Security

Security best practices:
- JWT-based authentication with httpOnly cookies
- API key management via environment variables
- Rate limiting on all endpoints
- CSRF protection
- Secrets scanning with Gitleaks (pre-commit hook)

See [Security Policy](SECURITY.md) for details.

## 📜 Project History

### Current Implementation (Nov 2025 - Present)
**Python** implementation for rapid development and AI integration:
- Migrated to **Textual** for rich terminal UI
- Integrated multiple AI providers (Claude, OpenAI, Perplexity)
- Implemented persona system with dynamic themes
- Added supervisor system for agent coordination

### Legacy Implementation (Archived)
The project was originally prototyped in **Rust** (Q4 2025) but migrated to Python for:
- ✅ Faster iteration and development velocity
- ✅ Better AI/ML library ecosystem
- ✅ Richer TUI framework (Textual vs TUI-rs)
- ✅ Simpler deployment and dependencies

**Legacy Rust documentation** preserved in [`archive/rust-legacy/`](archive/rust-legacy/) for historical reference.

## 🤝 Getting Help

- **Issues**: [GitHub Issues](https://github.com/chadananda/xswarm-boss/issues)
- **Discussions**: [GitHub Discussions](https://github.com/chadananda/xswarm-boss/discussions)
- **Security**: See [Security Policy](SECURITY.md) to report vulnerabilities
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md) in project root

## 📝 Contributing

We welcome contributions! Please see:
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [Development Setup](development/guide-development.md) - Get your environment ready
- [Testing Guide](testing/README.md) - Run tests before submitting

## 🎯 Quick Links

**For Users**:
- [Quick Start](quickstart/) - Get started fast
- [Features](planning/features.md) - What xSwarm can do
- [Pricing](planning/setups/setup-stripe-products.md) - Subscription tiers

**For Developers**:
- [Architecture](planning/architecture.md) - System design
- [API Docs](planning/) - HTTP API reference
- [Database Schema](planning/schema-database.md) - Data model

**For Deployers**:
- [Deployment Guide](deployment/guide-deployment.md) - Production deployment
- [Configuration](planning/) - Environment variables and settings

---

**Last Updated**: 2025-11-12
**Current Version**: 0.1.0-2025.11.12.0
**License**: MIT (see [LICENSE](../LICENSE))

🤖 AI-powered productivity, right in your terminal.
