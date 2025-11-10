# Git Integration & Project Coordination

This document describes the Git integration and advanced project coordination features added to the ProjectManager.

## Overview

The ProjectManager has been enhanced with comprehensive Git integration capabilities and advanced project coordination features to enable Boss to manage Git repositories and coordinate multiple agents working on the same project with proper version control.

## Git Integration Methods

### Repository Management

#### `clone_repository(url: &str, local_path: &Path) -> Result<()>`
Clones a Git repository to a local path.

**Example:**
```rust
manager.clone_repository(
    "https://github.com/user/project.git",
    Path::new("/path/to/local/project")
).await?;
```

#### `get_repository_status(project_id: &str) -> Result<GitStatus>`
Gets the current Git status of a project repository.

**Returns:**
- Current branch name
- Number of uncommitted changes
- Commits ahead/behind remote
- Lists of modified and untracked files
- Whether repository is clean

**Example:**
```rust
let status = manager.get_repository_status("project-123").await?;
println!("Branch: {}", status.current_branch);
println!("Clean: {}", status.is_clean);
```

### Branch Operations

#### `create_branch(project_id: &str, branch_name: &str) -> Result<()>`
Creates a new branch for a project.

**Example:**
```rust
manager.create_branch("project-123", "feature/new-api").await?;
```

### Commit Operations

#### `commit_changes(project_id: &str, message: &str) -> Result<String>`
Commits all changes in the project with the given message.

**Returns:** The commit hash

**Example:**
```rust
let hash = manager.commit_changes(
    "project-123",
    "Add new API endpoints"
).await?;
```

### Remote Operations

#### `push_changes(project_id: &str, branch: &str) -> Result<()>`
Pushes changes to the remote repository.

**Example:**
```rust
manager.push_changes("project-123", "main").await?;
```

#### `pull_latest(project_id: &str) -> Result<()>`
Pulls the latest changes from the remote repository.

**Example:**
```rust
manager.pull_latest("project-123").await?;
```

### History

#### `get_commit_history(project_id: &str, limit: usize) -> Result<Vec<GitCommit>>`
Gets the commit history for a project.

**Example:**
```rust
let commits = manager.get_commit_history("project-123", 10).await?;
for commit in commits {
    println!("{}: {} by {}", commit.hash, commit.message, commit.author);
}
```

## Project Coordination Methods

### Synchronization

#### `sync_project_with_remote(project_id: &str) -> Result<SyncResult>`
Synchronizes a project with its remote repository (pull + push).

**Returns:**
- Success status
- Number of commits pulled/pushed
- Any conflicts detected
- Status message

**Example:**
```rust
let result = manager.sync_project_with_remote("project-123").await?;
if result.success {
    println!("Synced: {} pulled, {} pushed",
        result.commits_pulled, result.commits_pushed);
}
```

### Technology Detection

#### `detect_project_technology_stack(project_path: &Path) -> Result<Vec<String>>`
Automatically detects the technology stack used in a project.

**Detects:**
- Node.js/JavaScript (package.json)
- Rust (Cargo.toml)
- Go (go.mod)
- Python (requirements.txt)
- Ruby (Gemfile)
- Java (pom.xml, build.gradle)
- PHP (composer.json)
- C#/.NET (.csproj)

**Example:**
```rust
let stack = manager.detect_project_technology_stack(
    Path::new("/path/to/project")
).await?;
println!("Technologies: {:?}", stack);
```

### Project Analysis

#### `analyze_project_structure(project_id: &str) -> Result<ProjectStructure>`
Analyzes the complete structure of a project.

**Returns:**
- Total files and lines of code
- Directory structure with file counts
- File type distribution
- Main entry points

**Example:**
```rust
let structure = manager.analyze_project_structure("project-123").await?;
println!("Total files: {}", structure.total_files);
println!("Total lines: {}", structure.total_lines);
```

#### `estimate_project_complexity(project_id: &str) -> Result<ComplexityMetrics>`
Estimates the complexity of a project.

**Returns:**
- Complexity score (1-10)
- Average file size
- Language breakdown
- Total files and lines

**Example:**
```rust
let complexity = manager.estimate_project_complexity("project-123").await?;
println!("Complexity score: {}/10", complexity.complexity_score);
```

## Agent Coordination Features

### Workspace Management

#### `create_agent_workspace(project_id: &str, agent: AgentType) -> Result<WorkspaceInfo>`
Creates an isolated workspace (branch) for an agent to work in.

**Example:**
```rust
let workspace = manager.create_agent_workspace(
    "project-123",
    AgentType::ClaudeCode
).await?;
println!("Agent workspace: {}", workspace.branch);
```

### Parallel Development

#### `coordinate_parallel_development(project_id: &str, tasks: Vec<String>) -> Result<CoordinationPlan>`
Creates a coordination plan for distributing tasks among multiple agents.

**Returns:**
- Task assignments per agent
- Estimated completion time
- Task dependencies

**Example:**
```rust
let tasks = vec![
    "Implement API".to_string(),
    "Write tests".to_string(),
    "Update docs".to_string(),
];
let plan = manager.coordinate_parallel_development(
    "project-123",
    tasks
).await?;
```

### Contribution Merging

#### `merge_agent_contributions(project_id: &str, contributions: Vec<AgentContribution>) -> Result<MergeResult>`
Merges contributions from multiple agents.

**Returns:**
- Success status
- Number of contributions merged
- Any conflicts detected
- Final commit hash

**Example:**
```rust
let contributions = vec![
    AgentContribution {
        id: "contrib-1".to_string(),
        agent: "claude-code".to_string(),
        branch: "agent-claude-xyz".to_string(),
        files_modified: vec!["api.rs".to_string()],
        commit_message: "Add API".to_string(),
        timestamp: Utc::now(),
    }
];
let result = manager.merge_agent_contributions(
    "project-123",
    contributions
).await?;
```

## Project Monitoring

### Health Monitoring

#### `monitor_project_health(project_id: &str) -> Result<HealthMetrics>`
Monitors the overall health of a project.

**Returns:**
- Health score (0-100)
- Code quality score (0-100)
- Open issues and bugs count
- Days inactive
- Last commit timestamp

**Example:**
```rust
let health = manager.monitor_project_health("project-123").await?;
println!("Health score: {}/100", health.health_score);
println!("Quality score: {}/100", health.code_quality_score);
```

### Conflict Detection

#### `detect_merge_conflicts(project_id: &str) -> Result<Vec<ConflictInfo>>`
Detects merge conflicts in the project files.

**Example:**
```rust
let conflicts = manager.detect_merge_conflicts("project-123").await?;
for conflict in conflicts {
    println!("Conflict in {}: {}",
        conflict.file_path, conflict.conflict_type);
}
```

### Quality Analysis

#### `analyze_code_quality(project_id: &str) -> Result<QualityMetrics>`
Analyzes the code quality of a project.

**Returns:**
- Overall quality score (0-100)
- Maintainability index (0-100)
- Average complexity
- Detected issues

**Example:**
```rust
let quality = manager.analyze_code_quality("project-123").await?;
println!("Quality: {}/100", quality.overall_score);
println!("Maintainability: {}/100", quality.maintainability);
```

## Data Structures

### GitStatus
```rust
pub struct GitStatus {
    pub current_branch: String,
    pub uncommitted_changes: usize,
    pub ahead: usize,
    pub behind: usize,
    pub modified_files: Vec<String>,
    pub untracked_files: Vec<String>,
    pub is_clean: bool,
}
```

### GitCommit
```rust
pub struct GitCommit {
    pub hash: String,
    pub author: String,
    pub email: String,
    pub message: String,
    pub timestamp: DateTime<Utc>,
}
```

### ProjectStructure
```rust
pub struct ProjectStructure {
    pub root_path: PathBuf,
    pub total_files: usize,
    pub total_lines: usize,
    pub directories: HashMap<String, usize>,
    pub file_types: HashMap<String, usize>,
    pub entry_points: Vec<String>,
}
```

### ComplexityMetrics
```rust
pub struct ComplexityMetrics {
    pub total_files: usize,
    pub total_lines: usize,
    pub avg_file_size: f32,
    pub dependencies_count: usize,
    pub complexity_score: u8,
    pub language_breakdown: HashMap<String, usize>,
}
```

### HealthMetrics
```rust
pub struct HealthMetrics {
    pub health_score: u8,
    pub code_quality_score: u8,
    pub test_coverage: f32,
    pub open_issues: usize,
    pub bugs: usize,
    pub last_commit: Option<DateTime<Utc>>,
    pub days_inactive: i64,
}
```

## Error Handling

All methods return `Result<T, anyhow::Error>` for comprehensive error handling:

```rust
match manager.push_changes("project-123", "main").await {
    Ok(_) => println!("Push successful"),
    Err(e) => eprintln!("Push failed: {}", e),
}
```

## Dependencies

The Git integration uses the `git2` crate (version 0.19), which provides Rust bindings to libgit2. This has been added to the workspace dependencies.

## Implementation Notes

1. **Async Operations**: All Git operations use `tokio::task::spawn_blocking` since libgit2 is synchronous
2. **Authentication**: Currently supports default Git credentials (SSH keys, credential helpers)
3. **Conflict Detection**: Uses simple marker-based detection (`<<<<<<<`, `>>>>>>>`)
4. **Branch Assumptions**: Several methods assume a `main` branch as default
5. **Complexity Scoring**: Uses heuristics based on file count, lines of code, and directory structure

## Future Enhancements

Potential improvements for future versions:

1. Custom Git authentication (tokens, SSH key paths)
2. More sophisticated conflict resolution
3. Integration with test frameworks for coverage metrics
4. Linter integration for quality analysis
5. Dependency parsing for accurate dependency counts
6. Support for multiple default branches (main/master/develop)
7. Git LFS support
8. Submodule handling
