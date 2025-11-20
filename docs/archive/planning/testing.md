# xSwarm-boss Testing Strategy

**Last Updated:** October 17, 2025
**Version:** 1.0
**Status:** Active

This document defines the testing strategy, quality standards, and validation approaches for xSwarm-boss.

---

## Quick Links

- **[PRD](PRD.md)** - Product requirements
- **[Architecture](ARCHITECTURE.md)** - System design
- **[TODO](TODO.md)** - Development tasks
- **[Code Style](CODESTYLE.md)** - Coding standards

---

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Pyramid](#test-pyramid)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [End-to-End Testing](#end-to-end-testing)
6. [Performance Testing](#performance-testing)
7. [Security Testing](#security-testing)
8. [Voice Interface Testing](#voice-interface-testing)
9. [Coverage Goals](#coverage-goals)
10. [CI/CD Integration](#cicd-integration)

---

## Testing Philosophy

### Core Principles

1. **Test behavior, not implementation** - Focus on what code does, not how
2. **Fast feedback** - Unit tests should run in <10s, full suite in <2min
3. **Reliable tests** - No flaky tests; fix or delete
4. **Maintainable tests** - Tests are code; keep them clean
5. **Test in production-like conditions** - Use realistic data and scenarios

### Quality Gates

All pull requests must:
- [ ] Pass all existing tests
- [ ] Add tests for new functionality
- [ ] Maintain >80% code coverage
- [ ] Pass `cargo clippy` with no warnings
- [ ] Pass security audit (`cargo audit`)

---

## Test Pyramid

```
        ╱╲
       ╱E2E╲          10% - End-to-End (Slow, High-Level)
      ╱━━━━━━╲
     ╱ Integ. ╲        20% - Integration (Medium Speed)
    ╱━━━━━━━━━━╲
   ╱   Unit     ╲      70% - Unit Tests (Fast, Focused)
  ╱━━━━━━━━━━━━━━╲
```

**Distribution:**
- **70% Unit tests** - Fast, isolated, focused on single functions/modules
- **20% Integration tests** - Medium speed, test module interactions
- **10% E2E tests** - Slow, test complete user workflows

---

## Unit Testing

### Rust Unit Tests

**Use standard Rust test framework.**

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_routing_by_capability() {
        // Arrange
        let pool = create_test_vassal_pool();
        let task = Task::new(TaskType::Build, vec!["rust"]);

        // Act
        let vassal_id = pool.route_task(&task).unwrap();

        // Assert
        let vassal = pool.get(vassal_id).unwrap();
        assert!(vassal.capabilities.contains(&"rust"));
    }

    #[test]
    fn test_no_available_vassal_returns_error() {
        let pool = VassalPool::new(0);
        let task = Task::new(TaskType::Build, vec![]);

        let result = pool.route_task(&task);
        assert!(matches!(result, Err(VassalError::NoAvailable)));
    }
}
```

### Test Fixtures

**Create reusable test data.**

```rust
// tests/fixtures/mod.rs
pub fn create_test_vassal(id: u8, capabilities: Vec<&str>) -> Vassal {
    Vassal {
        id: VassalId::from_u8(id),
        capabilities: capabilities.into_iter().map(String::from).collect(),
        status: VassalStatus::Idle,
        cpu_usage: 10.0,
        ram_usage: 20.0,
    }
}

pub fn create_test_vassal_pool() -> VassalPool {
    let mut pool = VassalPool::new(16);
    pool.add(create_test_vassal(1, vec!["rust", "docker"]));
    pool.add(create_test_vassal(2, vec!["node", "python"]));
    pool
}
```

### Mocking

**Use `mockall` for trait mocking.**

```rust
use mockall::*;

#[automock]
pub trait VassalConnection {
    async fn execute(&self, task: Task) -> Result<TaskResult>;
    async fn ping(&self) -> Result<()>;
}

#[tokio::test]
async fn test_task_execution_with_mock() {
    let mut mock_conn = MockVassalConnection::new();
    mock_conn
        .expect_execute()
        .times(1)
        .returning(|_| Ok(TaskResult::Success));

    let result = mock_conn.execute(Task::default()).await;
    assert!(result.is_ok());
}
```

### Property-Based Testing

**Use `proptest` for property testing.**

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_task_id_roundtrip(id in any::<u64>()) {
        let task_id = TaskId::from(id);
        let serialized = serde_json::to_string(&task_id)?;
        let deserialized: TaskId = serde_json::from_str(&serialized)?;
        prop_assert_eq!(task_id, deserialized);
    }

    #[test]
    fn test_priority_queue_ordering(priorities in prop::collection::vec(0u8..=10, 1..100)) {
        let mut queue = TaskQueue::new();
        for priority in priorities {
            queue.push(Task::with_priority(priority));
        }

        let mut prev = 10u8;
        while let Some(task) = queue.pop() {
            prop_assert!(task.priority <= prev);
            prev = task.priority;
        }
    }
}
```

---

## Integration Testing

### Module Integration

**Test interactions between modules.**

```rust
// tests/integration/task_routing.rs
use xswarm_core::{TaskQueue, VassalPool, TaskRouter};

#[tokio::test]
async fn test_task_flows_from_queue_to_vassal() {
    // Arrange
    let pool = VassalPool::new(16);
    let queue = TaskQueue::new();
    let router = TaskRouter::new(pool, queue);

    pool.add(create_test_vassal(1, vec!["rust"]));

    let task = Task::new(TaskType::Build, vec!["rust"]);
    queue.push(task.clone());

    // Act
    router.process_next().await.unwrap();

    // Assert
    let vassal = pool.get_by_capability("rust").unwrap();
    assert!(vassal.current_task.is_some());
    assert_eq!(vassal.current_task.unwrap().id, task.id);
}
```

### Database Integration

**Test LibSQL database operations.**

```rust
#[tokio::test]
async fn test_memory_store_and_retrieve() {
    let db = create_test_database().await;
    let memory = MemorySystem::new(db);

    // Store conversation
    let message = Message::user("Hey HAL, what's up?");
    memory.store_working(message.clone()).await.unwrap();

    // Retrieve from episodic
    let results = memory
        .search_episodic("what's up", 10)
        .await
        .unwrap();

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].content, message.content);
}
```

### Network Integration

**Test WebSocket communication.**

```rust
#[tokio::test]
async fn test_websocket_roundtrip() {
    // Start test server
    let server = start_test_websocket_server().await;
    let client = connect_test_client(server.addr()).await;

    // Send message
    let task = Task::new(TaskType::Test, vec![]);
    client.send(TaskMessage::Execute(task.clone())).await.unwrap();

    // Receive response
    let response = timeout(
        Duration::from_secs(5),
        server.recv()
    ).await.unwrap().unwrap();

    assert_eq!(response.task_id, task.id);
}
```

---

## End-to-End Testing

### CLI Testing

**Test complete CLI workflows.**

```bash
# tests/e2e/cli_test.sh
#!/bin/bash
set -e

# Setup test environment
export XSWARM_CONFIG="./tests/fixtures/test-config.toml"

# Test setup command
xswarm setup --non-interactive
assert_file_exists ~/.config/xswarm/config.toml

# Test daemon start
xswarm daemon &
DAEMON_PID=$!
sleep 2

# Test vassal connection
xswarm vassal add --name test-vassal --addr localhost:8080
assert_vassal_connected test-vassal

# Test task execution
xswarm task run --type build --lang rust
assert_task_completed

# Cleanup
kill $DAEMON_PID
```

### Dashboard Testing

**Test Ratatui UI with snapshot testing.**

```rust
// tests/e2e/dashboard.rs
use ratatui::backend::TestBackend;
use xswarm_core::Dashboard;

#[test]
fn test_dashboard_renders_vassal_grid() {
    let backend = TestBackend::new(80, 24);
    let mut terminal = Terminal::new(backend).unwrap();

    let mut dashboard = Dashboard::new();
    dashboard.add_vassal(create_test_vassal(1, vec!["rust"]));

    terminal.draw(|f| dashboard.render(f)).unwrap();

    // Snapshot comparison
    let buffer = terminal.backend().buffer().clone();
    insta::assert_debug_snapshot!(buffer);
}
```

### Voice Interface Testing

**Test voice pipeline end-to-end.**

```rust
#[tokio::test]
async fn test_voice_command_execution() {
    let voice = VoiceInterface::new(test_config());

    // Load test audio file
    let audio = load_test_audio("hey-hal-start-build.wav");

    // Process voice input
    let result = voice.process_audio(audio).await.unwrap();

    assert_eq!(result.wake_word, "HAL");
    assert_eq!(result.command.intent, Intent::StartTask);
    assert_eq!(result.command.task_type, TaskType::Build);
}
```

---

## Performance Testing

### Benchmarking

**Use `criterion` for benchmarks.**

```rust
// benches/task_routing.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use xswarm_core::{Task, VassalPool};

fn bench_task_routing(c: &mut Criterion) {
    let pool = create_large_vassal_pool(1000);
    let task = Task::new(TaskType::Build, vec!["rust"]);

    c.bench_function("route_task", |b| {
        b.iter(|| {
            pool.route_task(black_box(&task))
        });
    });
}

criterion_group!(benches, bench_task_routing);
criterion_main!(benches);
```

**Run benchmarks:**
```bash
cargo bench --bench task_routing
```

### Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Task routing | <10ms | p99 latency |
| Voice wake word | <100ms | Average |
| Voice command | <1s | End-to-end |
| Semantic search | <100ms | p95 latency |
| Memory retrieval | <50ms | p99 latency |
| Dashboard render | 16ms (60fps) | Frame time |
| WebSocket ping | <50ms | Round-trip |

### Load Testing

**Simulate high task volume.**

```rust
#[tokio::test]
async fn test_high_task_volume() {
    let router = TaskRouter::new(
        create_large_vassal_pool(100),
        TaskQueue::new()
    );

    // Submit 10,000 tasks
    let tasks: Vec<_> = (0..10_000)
        .map(|_| Task::new(TaskType::Test, vec![]))
        .collect();

    let start = Instant::now();

    for task in tasks {
        router.submit(task).await.unwrap();
    }

    let duration = start.elapsed();

    // Should handle 1000+ tasks/second
    assert!(duration < Duration::from_secs(10));
}
```

---

## Security Testing

### Secret Isolation

**Verify MCP server isolation.**

```rust
#[test]
fn test_secrets_never_in_main_memory() {
    let mcp = McpServer::new();
    mcp.store_secret("ANTHROPIC_API_KEY", "sk-test-123");

    // Verify main process cannot access secret directly
    let memory_dump = get_process_memory();
    assert!(!memory_dump.contains("sk-test-123"));

    // Verify access only via MCP
    let key = mcp.get_secret("ANTHROPIC_API_KEY").unwrap();
    assert_eq!(key, "sk-test-123");
}
```

### PII Filtering

**Test PII detection and filtering.**

```rust
#[test]
fn test_pii_filter_removes_sensitive_data() {
    let filter = PiiFilter::new();

    let text = "My email is john@example.com and my API key is sk-abc123";
    let filtered = filter.process(text);

    assert!(!filtered.contains("john@example.com"));
    assert!(!filtered.contains("sk-abc123"));
    assert!(filtered.contains("[EMAIL]"));
    assert!(filtered.contains("[API_KEY]"));
}

#[test]
fn test_pii_patterns() {
    let filter = PiiFilter::new();

    let test_cases = vec![
        ("SSH key: ssh-rsa AAAAB3...", true),
        ("Email: user@domain.com", true),
        ("Phone: 555-123-4567", true),
        ("Normal text", false),
    ];

    for (text, should_match) in test_cases {
        assert_eq!(
            filter.contains_pii(text),
            should_match,
            "Failed for: {}",
            text
        );
    }
}
```

### mTLS Authentication

**Test certificate validation.**

```rust
#[tokio::test]
async fn test_mtls_rejects_invalid_cert() {
    let server = start_mtls_server().await;

    // Try connecting with invalid cert
    let result = connect_with_cert(
        server.addr(),
        load_invalid_cert()
    ).await;

    assert!(matches!(result, Err(TlsError::InvalidCertificate)));
}

#[tokio::test]
async fn test_mtls_accepts_valid_cert() {
    let server = start_mtls_server().await;

    let result = connect_with_cert(
        server.addr(),
        load_valid_cert()
    ).await;

    assert!(result.is_ok());
}
```

---

## Voice Interface Testing

### Wake Word Detection

**Test theme-specific wake words.**

```rust
#[tokio::test]
async fn test_wake_word_detection_all_themes() {
    let themes = vec!["Sauron", "HAL", "JARVIS", "DALEK", "C-3PO", "GLaDOS", "TARS"];

    for theme in themes {
        let detector = WakeWordDetector::new(theme);
        let audio = load_test_audio(&format!("hey-{}.wav", theme.to_lowercase()));

        let result = detector.detect(audio).await.unwrap();
        assert!(result.detected, "Failed to detect wake word for {}", theme);
        assert_eq!(result.theme, theme);
    }
}
```

### Voice Command Accuracy

**Test natural language understanding.**

```rust
#[tokio::test]
async fn test_command_parsing_accuracy() {
    let test_cases = vec![
        ("Start a build on Brawny", Intent::StartTask, TaskType::Build),
        ("What's Speedy doing?", Intent::QueryStatus, TaskType::Unknown),
        ("Deploy to staging", Intent::Deploy, TaskType::Deploy),
        ("Run the tests", Intent::StartTask, TaskType::Test),
    ];

    let parser = CommandParser::new();

    for (input, expected_intent, expected_type) in test_cases {
        let result = parser.parse(input).await.unwrap();
        assert_eq!(result.intent, expected_intent, "Failed for: {}", input);
        assert_eq!(result.task_type, expected_type, "Failed for: {}", input);
    }
}
```

### Voice Latency

**Measure end-to-end voice latency.**

```rust
#[tokio::test]
async fn test_voice_latency_under_1s() {
    let voice = VoiceInterface::new(test_config());
    let audio = load_test_audio("hey-hal-status.wav");

    let start = Instant::now();
    let _result = voice.process_audio(audio).await.unwrap();
    let latency = start.elapsed();

    assert!(latency < Duration::from_secs(1), "Latency: {:?}", latency);
}
```

---

## Coverage Goals

### Overall Coverage

**Target: >80% line coverage across all packages.**

```bash
# Generate coverage report
cargo tarpaulin --out Html --output-dir coverage/
```

### Per-Module Coverage

| Module | Target | Critical |
|--------|--------|----------|
| `core` | 85% | Yes |
| `mcp-server` | 90% | Yes (security) |
| `network` | 85% | Yes |
| `task` | 80% | Yes |
| `dashboard` | 70% | No |
| `theme` | 75% | No |
| `indexer` | 80% | No |

### Uncovered Code

**Acceptable reasons for uncovered code:**
- Unreachable error paths (document with comment)
- Platform-specific code (guard with `#[cfg]`)
- Debug/logging code
- UI rendering code (use snapshot tests instead)

**Mark with:**
```rust
#[cfg(not(tarpaulin_include))]
fn debug_log_state(&self) {
    // Debug-only code
}
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cargo
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Run tests
        run: cargo test --all --verbose

      - name: Run clippy
        run: cargo clippy --all -- -D warnings

      - name: Check formatting
        run: cargo fmt --all -- --check

      - name: Security audit
        run: cargo audit

      - name: Coverage
        uses: actions-rs/tarpaulin@v0.1
        with:
          args: '--out Lcov --output-dir coverage/'

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

### Pre-commit Hooks

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e

echo "Running pre-commit checks..."

# Format check
cargo fmt --all -- --check

# Clippy
cargo clippy --all -- -D warnings

# Tests
cargo test --all

echo "All checks passed!"
```

---

## Test Data Management

### Fixture Organization

```
tests/
├── fixtures/
│   ├── audio/
│   │   ├── hey-hal.wav
│   │   ├── hey-sauron.wav
│   │   └── ...
│   ├── configs/
│   │   ├── test-config.toml
│   │   └── minimal-config.toml
│   ├── themes/
│   │   ├── hal/
│   │   └── sauron/
│   └── certs/
│       ├── valid-cert.pem
│       └── invalid-cert.pem
├── integration/
├── e2e/
└── snapshots/
```

### Test Database

**Use in-memory LibSQL for tests.**

```rust
async fn create_test_database() -> Database {
    Database::open(":memory:").await.unwrap()
}
```

---

## Troubleshooting Tests

### Flaky Tests

**If a test is flaky:**
1. Add timeout to async operations
2. Use deterministic time (mock `Instant::now()`)
3. Increase retry limits for external services
4. Add debug logging
5. If unfixable: delete or mark as `#[ignore]`

### Slow Tests

**If tests are slow:**
1. Use smaller test datasets
2. Mock external services
3. Run tests in parallel (`cargo test -- --test-threads=8`)
4. Move to integration tests if truly slow

### Debugging Failed Tests

```rust
#[test]
fn test_with_debug_output() {
    let result = complex_operation();

    if result.is_err() {
        eprintln!("Debug state: {:#?}", get_debug_state());
    }

    assert!(result.is_ok());
}
```

---

## Resources

- [Rust Testing Book](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Tokio Testing Guide](https://tokio.rs/tokio/topics/testing)
- [Property-Based Testing (proptest)](https://github.com/proptest-rs/proptest)
- [Snapshot Testing (insta)](https://insta.rs/)
- [Mocking (mockall)](https://docs.rs/mockall/)

---

## Questions?

Open an issue or discussion on GitHub if you have questions about testing strategy.
