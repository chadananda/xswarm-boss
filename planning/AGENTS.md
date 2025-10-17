# AI Agent Integration Guide

**Last Updated:** October 17, 2025
**Version:** 1.0
**Status:** Planning Phase

This document describes how xSwarm-boss integrates with AI coding assistants to coordinate multi-project development.

---

## Quick Links

- **[PRD](PRD.md)** - Product requirements
- **[Architecture](ARCHITECTURE.md)** - System design
- **[TODO](TODO.md)** - Development tasks

---

## Table of Contents

1. [Overview](#overview)
2. [Supported Agents](#supported-agents)
3. [Agent Lifecycle](#agent-lifecycle)
4. [Integration Patterns](#integration-patterns)
5. [Command Examples](#command-examples)
6. [Security Model](#security-model)

---

## Overview

**xSwarm-boss is an AI orchestration layer** that coordinates multiple AI coding assistants working on different projects across different machines.

### The Problem xSwarm Solves

Modern AI coding assistants (Claude Code, Cursor, Aider) enable developers to work on 10+ projects simultaneously. But this creates chaos:

- **No unified status** - Which AI is working on which project?
- **Dependency hell** - Update library A, now need to update projects B, C, D
- **Resource competition** - Multiple agents fighting for CPU/GPU
- **Context loss** - No cross-project knowledge or coordination

### The xSwarm Solution

**One orchestration layer** that:
- Manages AI agent lifecycle (spawn, monitor, coordinate, terminate)
- Tracks cross-project dependencies
- Allocates resources (which agent runs on which machine)
- Provides unified status and control interface
- Maintains system-wide knowledge base

---

## Supported Agents

### Claude Code

**Primary Integration:** xSwarm's recommended AI coding assistant.

**Integration Method:** API + Local Subprocess
- **API Access:** Via Anthropic SDK (when available)
- **Local Control:** Via `claude-code` CLI
- **Project Context:** Pass project path, task description
- **Status Monitoring:** Stream output, parse completion status

**Example Usage:**
```rust
let agent = ClaudeCodeAgent::spawn()
    .project_path("~/projects/api-gateway")
    .task("Update auth library from v2.1 to v3.0")
    .machine(vassal_id)
    .await?;

// Monitor progress
agent.on_progress(|update| {
    info!("Claude Code: {}", update.message);
});

let result = agent.wait_completion().await?;
```

**Capabilities:**
- Full codebase understanding
- Multi-file refactoring
- Test generation and execution
- Documentation updates

### Cursor

**Status:** Experimental (TBD)

**Integration Method:** CLI or API (investigating)
- **CLI Access:** Via `cursor` command (if available)
- **API Access:** TBD - need to investigate Cursor's automation API
- **Challenges:** May not have command-line automation support

**Research Needed:**
- [ ] Does Cursor provide CLI automation?
- [ ] Is there an API for programmatic control?
- [ ] Can we spawn Cursor instances headlessly?

### Aider

**Status:** Supported

**Integration Method:** CLI Subprocess
- **CLI Access:** Via `aider` command
- **Project Context:** Pass file paths, task via stdin
- **Status Monitoring:** Parse stdout for completion

**Example Usage:**
```rust
let agent = AiderAgent::spawn()
    .project_path("~/projects/user-service")
    .files(vec!["src/auth.rs", "src/tokens.rs"])
    .task("Migrate to async token validation")
    .machine(vassal_id)
    .await?;
```

**Capabilities:**
- Fast, focused changes
- Good for single-file or small refactors
- Git integration built-in

### Future Agents

**Plugin System:** Support for additional AI coding assistants via plugin architecture.

**Potential Candidates:**
- GitHub Copilot Workspace (when automation API available)
- Continue.dev
- Cody
- Custom agents via API

---

## Agent Lifecycle

### 1. Spawn

xSwarm spawns an agent when given a high-level task:

```
User: "Update the auth library in api-gateway"

xSwarm Process:
1. Parse command → identify project (api-gateway)
2. Check available machines → select Speedy (least loaded)
3. Spawn Claude Code agent on Speedy
4. Pass project context + task description
5. Begin monitoring
```

**Spawn Decision Factors:**
- Project size and complexity
- Machine availability (CPU/GPU/RAM)
- Agent type preference (per-project config)
- Current agent workload

### 2. Monitor

xSwarm continuously monitors agent progress:

```rust
pub struct AgentMonitor {
    agent_id: AgentId,
    project: ProjectId,
    machine: VassalId,
    status: AgentStatus,
}

pub enum AgentStatus {
    Initializing,
    Running { progress: f32, current_file: String },
    Testing { tests_passed: u32, tests_failed: u32 },
    Completed { files_changed: Vec<String> },
    Failed { error: String },
}
```

**User Queries:**
```
User: "What's the status of api-gateway?"
HAL: "Claude Code on Speedy is 60% complete. Currently updating
     auth_middleware.rs. 8 of 12 files updated. 2 test failures
     in token validation - investigating now."
```

### 3. Coordinate

xSwarm coordinates multiple agents across projects:

```
User: "Update auth library, then update all dependent projects"

xSwarm Coordination:
1. Agent A: Update auth-service → Complete ✅
2. xSwarm: Analyze changes, identify dependents
3. Agent B: Update api-gateway (parallel) → Running...
4. Agent C: Update user-service (parallel) → Running...
5. Agent D: Update admin-dashboard (queued, waits for B & C)
```

**Dependency-Aware Scheduling:**
```rust
pub struct UpdateCoordinator {
    graph: ProjectGraph,
    agents: AgentPool,
}

impl UpdateCoordinator {
    async fn coordinate_updates(&self, root_project: ProjectId) -> Result<()> {
        let dependents = self.graph.find_dependents(root_project);
        let update_order = self.graph.topological_sort(dependents);

        for wave in update_order {
            // Spawn agents for all projects in this wave (parallel)
            let agents = self.spawn_wave(wave).await?;

            // Wait for wave completion
            let results = join_all(agents).await;

            // Validate before next wave
            self.validate_wave(results)?;
        }
    }
}
```

### 4. Terminate

xSwarm terminates agents when:
- Task completed successfully
- Task failed (max retries exceeded)
- User cancellation
- Machine needs to shut down

**Cleanup Process:**
```rust
impl Agent {
    async fn terminate(&mut self) -> Result<()> {
        // Save state
        self.save_progress().await?;

        // Kill process gracefully
        self.process.terminate().await?;

        // Clean up temporary files
        self.cleanup_workspace().await?;

        // Update metrics
        self.report_completion().await?;
    }
}
```

---

## Integration Patterns

### Pattern 1: Single-Project Task

```
User: "Fix the test failures in api-gateway"

xSwarm Flow:
1. Identify project: api-gateway
2. Select agent: Claude Code (project preference)
3. Choose machine: Speedy (available, good specs)
4. Spawn agent with context
5. Monitor until completion
6. Report results
```

### Pattern 2: Cross-Project Update

```
User: "Update Redis client across all projects"

xSwarm Flow:
1. Search codebase: Find 6 projects using Redis
2. Create dependency graph (some projects depend on others)
3. Compute update order: [lib-a, lib-b, app-1, app-2, app-3, app-4]
4. Wave 1: Update lib-a and lib-b (parallel, 2 agents)
5. Wave 2: Update app-1, app-2 (parallel, wait for lib-a)
6. Wave 3: Update app-3, app-4 (parallel, wait for lib-b)
7. Validate entire chain
8. Report completion
```

### Pattern 3: Status Query

```
User: "What's happening with my Python projects?"

xSwarm Flow:
1. Query agent manager: Active Python project agents
2. Query project graph: All Python projects
3. Aggregate status:
   - api-gateway: Building (Agent on Speedy, 70% done)
   - data-pipeline: Tests passing (Agent on Brawny, completed)
   - ml-service: Idle (no active agent)
   - auth-lib: Failed tests (Agent on Brainy, investigating)
4. Present unified status
```

### Pattern 4: Resource Allocation

```
User: "Start working on project-x"

xSwarm Flow:
1. Analyze project-x requirements:
   - Language: Rust
   - Size: 50k LOC
   - Tests: Heavy (GPU recommended)
2. Check machine availability:
   - Brawny: Idle, 16 cores, 32GB RAM, RTX 3080
   - Speedy: Busy (agent running), 8 cores, 16GB RAM
   - Brainy: Idle, 12 cores, 24GB RAM, no GPU
3. Select: Brawny (best specs, available)
4. Spawn Claude Code on Brawny
```

---

## Command Examples

### High-Level Coordination

```bash
# Multi-project status
"Hey HAL, project status"
"What's building?"
"Show me failing projects"

# Cross-project operations
"Update auth library across all projects"
"Which projects use the old Redis client?"
"Find all Python projects with failing tests"

# Dependency coordination
"Update project-a, then update dependent projects"
"Show me the dependency tree for api-gateway"
"What will break if I change auth-service?"
```

### Single-Project Control

```bash
# Start work
"Start working on api-gateway using Claude Code on Speedy"
"Fix the test failures in user-service"
"Refactor the auth module in admin-dashboard"

# Monitor progress
"How's api-gateway doing?"
"Show me the changes in user-service"
"Are the tests passing?"

# Agent control
"Pause work on api-gateway"
"Cancel the refactor in user-service"
"Resume work on admin-dashboard"
```

### Resource Management

```bash
# Machine queries
"Which machines are available?"
"What's Brawny working on?"
"Show me all active agents"

# Reallocation
"Move the api-gateway work from Speedy to Brawny"
"Start the build on the fastest available machine"
"Balance the workload across all machines"
```

---

## Security Model

### Project Isolation

**Problem:** Secrets from project-a shouldn't leak to project-b.

**Solution:** Rules-based filtering + memory purging:

```rust
pub struct SecurityFilter {
    secret_patterns: Vec<Regex>,
}

impl SecurityFilter {
    fn filter_memory(&self, text: &str) -> String {
        // Remove API keys, tokens, passwords before cross-project operations
        let mut filtered = text.to_string();

        for pattern in &self.secret_patterns {
            filtered = pattern.replace_all(&filtered, "[REDACTED]").to_string();
        }

        filtered
    }
}
```

**Secret Patterns:**
- API keys: `sk-[a-zA-Z0-9]{48}`
- AWS credentials: `AKIA[A-Z0-9]{16}`
- SSH keys: `-----BEGIN.*PRIVATE KEY-----`
- Tokens: `ghp_[a-zA-Z0-9]{36}`, `xoxb-[0-9-]+`

### Memory Purging

**Problem:** Agent memory accumulates sensitive data.

**Solution:** Constant purging between projects:

```rust
async fn switch_project_context(&mut self, from: ProjectId, to: ProjectId) -> Result<()> {
    // Save current project state
    self.save_project_memory(from).await?;

    // Purge working memory
    self.memory.clear_secrets();
    self.memory.filter_pii();

    // Load new project context (filtered)
    self.load_project_memory(to).await?;
}
```

### PII Filtering

**Problem:** Personal information shouldn't reach external APIs.

**Solution:** Pre-filter all outbound communication:

```rust
pub struct PIIFilter {
    patterns: Vec<Regex>,
}

impl PIIFilter {
    fn filter(&self, text: &str) -> String {
        // Remove emails, phones, SSNs, credit cards
        // Replace with generic tokens: [EMAIL], [PHONE], etc.
    }
}
```

### Audit Logging

**All sensitive operations logged:**
- Agent spawn/terminate
- Cross-project context switches
- Secret access attempts
- Memory purge events

```rust
audit_log!(
    event = "agent_spawned",
    agent_type = "claude_code",
    project = "api-gateway",
    machine = "speedy",
    user_command = redact(command),
);
```

---

## Future Enhancements

### Plugin API

Support for custom agents via plugin system:

```rust
pub trait AgentPlugin {
    async fn spawn(&self, ctx: SpawnContext) -> Result<AgentInstance>;
    async fn monitor(&self, agent: &AgentInstance) -> Result<AgentStatus>;
    async fn terminate(&self, agent: &AgentInstance) -> Result<()>;
}

// Example: Custom agent
pub struct MyCustomAgent;

impl AgentPlugin for MyCustomAgent {
    async fn spawn(&self, ctx: SpawnContext) -> Result<AgentInstance> {
        // Custom agent spawning logic
    }
}
```

### Agent Marketplace

Community-contributed agent integrations:
- GitHub repository of agent plugins
- Installation via `xswarm agent install <name>`
- Versioning and compatibility checks

### Multi-Agent Collaboration

Future: Multiple agents working together on one project:
- Agent A: Backend refactor
- Agent B: Frontend updates
- Agent C: Test generation
- xSwarm coordinates to prevent conflicts

---

## Questions?

Open an issue or discussion on GitHub if you have questions about agent integration.
