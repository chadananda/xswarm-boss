# xSwarm-boss Code Style Guide

**Last Updated:** October 17, 2025
**Version:** 1.0
**Status:** Active

This document defines coding standards and style guidelines for all xSwarm-boss code contributions.

---

## Quick Links

- **[PRD](PRD.md)** - Product requirements
- **[Architecture](ARCHITECTURE.md)** - System design
- **[TODO](TODO.md)** - Development tasks
- **[Testing](TESTING.md)** - Test strategy

---

## Table of Contents

1. [General Principles](#general-principles)
2. [Rust Style](#rust-style)
3. [TypeScript/JavaScript Style](#typescriptjavascript-style)
4. [Git Conventions](#git-conventions)
5. [Documentation Standards](#documentation-standards)
6. [Code Organization](#code-organization)

---

## General Principles

### Core Values

1. **Clarity over cleverness** - Code should be obvious, not clever
2. **Safety over speed** - Use Rust's type system to prevent bugs
3. **Explicit over implicit** - Make intentions clear
4. **Fail fast** - Error early, recover gracefully
5. **Local-first** - Conversations and memory stay on the user's network

### File Structure

```
xswarm-boss/
├── packages/
│   ├── core/           # Rust orchestrator (main binary)
│   ├── mcp-server/     # MCP security isolation (Rust)
│   ├── indexer/        # Document indexing (Rust)
│   ├── docs/           # Astro documentation site (TS)
│   └── themes/         # Theme packages (YAML + MD)
├── planning/           # Design documents
├── scripts/            # Build/setup scripts
└── tests/              # Integration tests
```

---

## Rust Style

### Formatting

**Use `rustfmt` for all Rust code.**

```bash
cargo fmt --all
```

Configuration in `.rustfmt.toml`:
```toml
max_width = 100
use_small_heuristics = "Max"
edition = "2021"
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Crates | `snake_case` | `xswarm_core`, `mcp_server` |
| Types/Traits | `PascalCase` | `TaskQueue`, `VassalConnection` |
| Functions | `snake_case` | `route_task()`, `connect_vassal()` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_VASSALS`, `DEFAULT_PORT` |
| Lifetimes | `'lowercase` | `'a`, `'conn`, `'static` |
| Type Parameters | Single uppercase | `T`, `E`, `R` |

### Error Handling

**Use `anyhow` for application errors, `thiserror` for library errors.**

```rust
// Application code (binaries)
use anyhow::{Context, Result};

fn load_config(path: &Path) -> Result<Config> {
    std::fs::read_to_string(path)
        .context("Failed to read config file")?
        .parse()
        .context("Failed to parse config")
}

// Library code (reusable crates)
use thiserror::Error;

#[derive(Error, Debug)]
pub enum VassalError {
    #[error("Connection lost to vassal {0}")]
    ConnectionLost(String),

    #[error("Task timeout after {0}s")]
    Timeout(u64),

    #[error(transparent)]
    Network(#[from] std::io::Error),
}
```

### Result Handling

**Prefer early returns over deep nesting.**

```rust
// Good ✅
fn process_task(task: Task) -> Result<()> {
    let vassal = match find_available_vassal(&task) {
        Some(v) => v,
        None => return Err(anyhow!("No available vassals")),
    };

    vassal.execute(task)?;
    Ok(())
}

// Bad ❌
fn process_task(task: Task) -> Result<()> {
    if let Some(vassal) = find_available_vassal(&task) {
        vassal.execute(task)?;
        Ok(())
    } else {
        Err(anyhow!("No available vassals"))
    }
}
```

### Logging

**Use the `tracing` crate for structured logging.**

```rust
use tracing::{info, warn, error, debug, trace};

#[tracing::instrument]
fn route_task(task: &Task) -> Result<VassalId> {
    debug!(task_id = %task.id, "Routing task");

    let vassal = find_best_vassal(task)
        .context("No suitable vassal found")?;

    info!(
        task_id = %task.id,
        vassal_id = %vassal.id,
        "Task routed successfully"
    );

    Ok(vassal.id)
}
```

**Log levels:**
- `trace`: Detailed execution flow (loop iterations, state changes)
- `debug`: Developer debugging (function entry/exit, variable values)
- `info`: User-relevant events (task started, build completed)
- `warn`: Recoverable errors (retry after timeout)
- `error`: Unrecoverable errors (failed to load config)

### Async Code

**Use Tokio for async runtime.**

```rust
// Function naming
async fn connect_to_vassal(addr: SocketAddr) -> Result<VassalConnection> {
    // Implementation
}

// Error propagation
async fn execute_task(task: Task) -> Result<TaskResult> {
    let connection = connect_to_vassal(task.vassal_addr).await?;
    let result = connection.execute(task).await?;
    Ok(result)
}

// Timeouts
use tokio::time::{timeout, Duration};

let result = timeout(
    Duration::from_secs(30),
    execute_task(task)
).await??;
```

### Comments

**Use comments to explain *why*, not *what*.**

```rust
// Good ✅
// We need to keep the connection alive because vassals
// may have long-running tasks that exceed the default timeout
let keepalive = Duration::from_secs(300);

// Bad ❌
// Set keepalive to 300 seconds
let keepalive = Duration::from_secs(300);
```

**Use doc comments for public APIs.**

```rust
/// Routes a task to the most suitable vassal based on:
/// - Available CPU/RAM resources
/// - Task type compatibility
/// - Current workload
///
/// # Errors
/// Returns `VassalError::NoAvailable` if no vassals can handle the task.
///
/// # Example
/// ```
/// let vassal_id = router.route_task(&build_task)?;
/// ```
pub fn route_task(&self, task: &Task) -> Result<VassalId> {
    // Implementation
}
```

### Type Safety

**Use newtypes for domain concepts.**

```rust
// Good ✅
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct VassalId(uuid::Uuid);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct TaskId(uuid::Uuid);

fn assign_task(vassal: VassalId, task: TaskId) { /* ... */ }

// Bad ❌
fn assign_task(vassal: uuid::Uuid, task: uuid::Uuid) { /* ... */ }
```

**Use enums for state machines.**

```rust
pub enum TaskState {
    Queued { priority: u8 },
    Running { vassal_id: VassalId, started_at: Instant },
    Completed { result: TaskResult, duration: Duration },
    Failed { error: String, retry_count: u32 },
}

impl TaskState {
    pub fn is_terminal(&self) -> bool {
        matches!(self, TaskState::Completed { .. } | TaskState::Failed { .. })
    }
}
```

---

## TypeScript/JavaScript Style

### Formatting

**Use Prettier for all TS/JS code.**

```bash
pnpm run format
```

Configuration in `.prettierrc`:
```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2
}
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | `kebab-case.ts` | `theme-loader.ts` |
| Components | `PascalCase.astro` | `ThemeCard.astro` |
| Functions | `camelCase` | `loadTheme()` |
| Constants | `SCREAMING_SNAKE_CASE` | `API_BASE_URL` |
| Types/Interfaces | `PascalCase` | `ThemeConfig`, `VassalStatus` |

### TypeScript Usage

**Always use strict mode.**

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

**Prefer interfaces over types for objects.**

```typescript
// Good ✅
interface ThemeConfig {
  name: string
  icon: string
  wakeWord: string
  colors: ColorScheme
}

// Use types for unions/intersections
type TaskResult = Success | Failure
type WithMetadata<T> = T & { timestamp: Date }
```

**Use unknown instead of any.**

```typescript
// Good ✅
function parseJson(text: string): unknown {
  return JSON.parse(text)
}

const data = parseJson(response)
if (isThemeConfig(data)) {
  // Type guard narrows to ThemeConfig
  console.log(data.wakeWord)
}

// Bad ❌
function parseJson(text: string): any {
  return JSON.parse(text)
}
```

### React/Astro Components

**Use functional components with TypeScript.**

```typescript
// Astro component
---
interface Props {
  theme: ThemeConfig
  active: boolean
}

const { theme, active } = Astro.props
---

<div class:list={['theme-card', { active }]}>
  <span class="icon">{theme.icon}</span>
  <h3>{theme.name}</h3>
</div>

<style>
  .theme-card { /* ... */ }
  .theme-card.active { /* ... */ }
</style>
```

---

## Git Conventions

### Commit Messages

**Use Conventional Commits format.**

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature/fix)
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Build process, dependencies, tooling

**Examples:**
```
feat(dashboard): add hexagonal vassal grid widget

Implements the core dashboard layout with hexagonal grid
displaying vassal status, CPU/RAM usage, and active tasks.

Closes #23

---

fix(network): handle reconnection after vassal timeout

Previously, timeouts would leave stale connections in the pool.
Now connections are properly cleaned up and reconnection is attempted
with exponential backoff.

---

docs(readme): update theme personality examples

Added character-accurate introductions for all 7 themes.

---

chore(deps): bump tokio to 1.35.0
```

### Branch Naming

```
<type>/<short-description>

Examples:
- feat/hexagonal-grid
- fix/vassal-reconnect
- docs/theme-guide
- refactor/task-routing
```

### Pull Requests

**PR titles should match commit message format.**

**PR description template:**
```markdown
## Description
Brief description of changes.

## Changes
- List of specific changes
- Include file paths if helpful

## Testing
How to test these changes.

## Screenshots (if applicable)

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] No new warnings
```

---

## Documentation Standards

### Code Documentation

**Every public API must have rustdoc/JSDoc comments.**

```rust
/// Manages the connection pool for all active vassals.
///
/// The pool maintains persistent WebSocket connections with mTLS
/// authentication. Dead connections are automatically cleaned up
/// via heartbeat monitoring.
pub struct VassalPool {
    connections: Arc<RwLock<HashMap<VassalId, VassalConnection>>>,
    max_size: usize,
}

impl VassalPool {
    /// Creates a new pool with the specified maximum size.
    ///
    /// # Arguments
    /// * `max_size` - Maximum number of concurrent vassal connections
    ///
    /// # Example
    /// ```
    /// let pool = VassalPool::new(16);
    /// ```
    pub fn new(max_size: usize) -> Self {
        // Implementation
    }
}
```

### Markdown Documents

**Use consistent heading hierarchy.**

```markdown
# Document Title (H1 - once per document)

## Major Section (H2)

### Subsection (H3)

#### Detail Section (H4)
```

**Include metadata at the top.**

```markdown
# Document Title

**Last Updated:** October 17, 2025
**Version:** 1.0
**Status:** Active

Brief document description.
```

---

## Code Organization

### Module Structure

```rust
// lib.rs or main.rs
mod config;      // Configuration management
mod network;     // WebSocket + mTLS
mod task;        // Task definitions and routing
mod vassal;      // Vassal management
mod dashboard;   // Ratatui UI
mod theme;       // Theme system

pub use config::Config;
pub use task::{Task, TaskResult};
pub use vassal::{VassalId, VassalPool};
```

### Dependency Guidelines

**Minimize dependencies. Prefer standard library.**

**Allowed core dependencies:**
- `tokio` - Async runtime
- `serde` - Serialization
- `anyhow` / `thiserror` - Error handling
- `tracing` - Logging
- `clap` - CLI parsing
- `ratatui` - Terminal UI

**Evaluate before adding:**
- Size (binary bloat?)
- Maintenance (actively maintained?)
- Security (audit history?)
- Alternatives (can we use stdlib?)

### Feature Flags

**Use Cargo features for optional functionality.**

```toml
[features]
default = ["voice", "search"]
voice = ["dep:webrtc", "dep:opus"]
search = ["dep:meilisearch-sdk"]
vnc = ["dep:libvnc"]
```

```rust
#[cfg(feature = "voice")]
pub mod voice;

#[cfg(feature = "search")]
pub mod search;
```

---

## Review Checklist

Before submitting code:

- [ ] Code compiles without warnings
- [ ] `cargo fmt --all` applied
- [ ] `cargo clippy --all` passes
- [ ] Tests pass (`cargo test --all`)
- [ ] Public APIs documented
- [ ] Error handling comprehensive
- [ ] Logging statements appropriate
- [ ] No secrets in code
- [ ] Git commit message follows conventions
- [ ] Breaking changes documented

---

## Resources

- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- [Effective Rust](https://www.lurklurk.org/effective-rust/)
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/)

---

## Questions?

Open an issue or discussion on GitHub if you have questions about these guidelines.
