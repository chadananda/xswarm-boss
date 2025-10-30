/// Project Management Module
///
/// This module provides comprehensive data structures for managing projects and tasks
/// in the xSwarm system with multi-agent coordination capabilities.

use std::path::{Path, PathBuf};
use std::collections::HashMap;
use std::sync::Arc;
use chrono::{DateTime, Utc, Duration};
use uuid::Uuid;
use serde::{Deserialize, Serialize};
use anyhow::{Result, anyhow};
use tokio::sync::RwLock;
use git2::{Repository, Signature, Oid, BranchType, StatusOptions};

// ============================================================================
// Core Enums
// ============================================================================

/// Project status enumeration
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProjectStatus {
    /// Project is in planning phase
    Planning,
    /// Project is actively being worked on
    Active,
    /// Project is temporarily on hold
    OnHold,
    /// Project has been completed
    Completed,
    /// Project has been cancelled
    Cancelled,
}

impl Default for ProjectStatus {
    fn default() -> Self {
        ProjectStatus::Active
    }
}

/// Project priority enumeration
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProjectPriority {
    Low,
    Medium,
    High,
    Critical,
}

impl Default for ProjectPriority {
    fn default() -> Self {
        ProjectPriority::Medium
    }
}

impl ProjectPriority {
    /// Convert to numeric value (1-4)
    pub fn to_numeric(&self) -> i32 {
        match self {
            ProjectPriority::Low => 1,
            ProjectPriority::Medium => 2,
            ProjectPriority::High => 3,
            ProjectPriority::Critical => 4,
        }
    }

    /// Create from numeric value (1-4)
    pub fn from_numeric(value: i32) -> Self {
        match value {
            1 => ProjectPriority::Low,
            2 => ProjectPriority::Medium,
            3 => ProjectPriority::High,
            4 => ProjectPriority::Critical,
            _ => ProjectPriority::Medium,
        }
    }
}

/// Task status enumeration
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    /// Task is waiting to be started
    Todo,
    /// Task is currently being worked on
    InProgress,
    /// Task has been completed
    Done,
    /// Task is blocked and cannot proceed
    Blocked,
}

impl Default for TaskStatus {
    fn default() -> Self {
        TaskStatus::Todo
    }
}

/// Task priority enumeration
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskPriority {
    Low,
    Medium,
    High,
}

impl Default for TaskPriority {
    fn default() -> Self {
        TaskPriority::Medium
    }
}

impl TaskPriority {
    /// Convert to numeric value (1-3)
    pub fn to_numeric(&self) -> i32 {
        match self {
            TaskPriority::Low => 1,
            TaskPriority::Medium => 2,
            TaskPriority::High => 3,
        }
    }

    /// Create from numeric value (1-3)
    pub fn from_numeric(value: i32) -> Self {
        match value {
            1 => TaskPriority::Low,
            2 => TaskPriority::Medium,
            3 => TaskPriority::High,
            _ => TaskPriority::Medium,
        }
    }
}

/// Agent type enumeration for multi-agent coordination
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AgentType {
    /// Claude Code (Anthropic)
    ClaudeCode,
    /// Google Gemini
    Gemini,
    /// GitHub Copilot
    Copilot,
    /// Local development agent
    Local,
    /// Human developer
    Human,
    /// Custom agent (with name)
    Custom(String),
}

impl AgentType {
    /// Convert to string identifier
    pub fn as_str(&self) -> String {
        match self {
            AgentType::ClaudeCode => "claude-code".to_string(),
            AgentType::Gemini => "gemini".to_string(),
            AgentType::Copilot => "copilot".to_string(),
            AgentType::Local => "local".to_string(),
            AgentType::Human => "human".to_string(),
            AgentType::Custom(name) => name.clone(),
        }
    }

    /// Create from string identifier
    pub fn from_str(s: &str) -> Self {
        match s {
            "claude-code" => AgentType::ClaudeCode,
            "gemini" => AgentType::Gemini,
            "copilot" => AgentType::Copilot,
            "local" => AgentType::Local,
            "human" => AgentType::Human,
            other => AgentType::Custom(other.to_string()),
        }
    }
}

// ============================================================================
// Core Structs
// ============================================================================

/// Project struct representing a development project
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Project {
    /// Unique identifier (UUID)
    pub id: String,
    /// Project name
    pub name: String,
    /// Optional project description
    pub description: Option<String>,
    /// Current project status
    pub status: ProjectStatus,
    /// Project priority
    pub priority: ProjectPriority,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last update timestamp
    pub updated_at: Option<DateTime<Utc>>,
    /// Optional due date
    pub due_date: Option<DateTime<Utc>>,
    /// User ID who owns this project
    pub owner_id: String,
    /// Optional Git repository URL
    pub repository_url: Option<String>,
    /// Local project directory path
    pub local_path: Option<PathBuf>,
    /// Technology stack (languages, frameworks)
    pub technology_stack: Vec<String>,
    /// Agent assignments (agent_id -> role)
    pub agent_assignments: HashMap<String, String>,
}

impl Project {
    /// Create a new project with required fields
    pub fn new(name: String, owner_id: String) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            name,
            description: None,
            status: ProjectStatus::default(),
            priority: ProjectPriority::default(),
            created_at: now,
            updated_at: None,
            due_date: None,
            owner_id,
            repository_url: None,
            local_path: None,
            technology_stack: Vec::new(),
            agent_assignments: HashMap::new(),
        }
    }

    /// Update the project status
    pub fn update_status(&mut self, status: ProjectStatus) {
        self.status = status;
        self.updated_at = Some(Utc::now());
    }

    /// Update the project priority
    pub fn update_priority(&mut self, priority: ProjectPriority) {
        self.priority = priority;
        self.updated_at = Some(Utc::now());
    }

    /// Set the description
    pub fn set_description(&mut self, description: String) {
        self.description = Some(description);
        self.updated_at = Some(Utc::now());
    }

    /// Set the due date
    pub fn set_due_date(&mut self, due_date: DateTime<Utc>) {
        self.due_date = Some(due_date);
        self.updated_at = Some(Utc::now());
    }

    /// Set the repository URL
    pub fn set_repository_url(&mut self, url: String) {
        self.repository_url = Some(url);
        self.updated_at = Some(Utc::now());
    }

    /// Set the local path
    pub fn set_local_path(&mut self, path: PathBuf) {
        self.local_path = Some(path);
        self.updated_at = Some(Utc::now());
    }

    /// Add technology to stack
    pub fn add_technology(&mut self, tech: String) {
        if !self.technology_stack.contains(&tech) {
            self.technology_stack.push(tech);
            self.updated_at = Some(Utc::now());
        }
    }

    /// Assign an agent to a role
    pub fn assign_agent(&mut self, agent_id: String, role: String) {
        self.agent_assignments.insert(agent_id, role);
        self.updated_at = Some(Utc::now());
    }

    /// Remove an agent assignment
    pub fn unassign_agent(&mut self, agent_id: &str) {
        self.agent_assignments.remove(agent_id);
        self.updated_at = Some(Utc::now());
    }
}

/// ProjectTask struct representing a task within a project
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectTask {
    /// Unique identifier (UUID)
    pub id: String,
    /// Project ID this task belongs to
    pub project_id: String,
    /// Task title
    pub title: String,
    /// Optional task description
    pub description: Option<String>,
    /// Current task status
    pub status: TaskStatus,
    /// Task priority
    pub priority: TaskPriority,
    /// Optional assigned agent
    pub assigned_agent: Option<String>,
    /// Estimated hours for completion
    pub estimated_hours: Option<f32>,
    /// Actual hours spent
    pub actual_hours: Option<f32>,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last update timestamp
    pub updated_at: Option<DateTime<Utc>>,
    /// Optional due date
    pub due_date: Option<DateTime<Utc>>,
    /// Task dependencies (task IDs)
    pub dependencies: Vec<String>,
    /// Tags for organization
    pub tags: Vec<String>,
}

impl ProjectTask {
    /// Create a new task
    pub fn new(project_id: String, title: String) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            project_id,
            title,
            description: None,
            status: TaskStatus::default(),
            priority: TaskPriority::default(),
            assigned_agent: None,
            estimated_hours: None,
            actual_hours: None,
            created_at: now,
            updated_at: None,
            due_date: None,
            dependencies: Vec::new(),
            tags: Vec::new(),
        }
    }

    /// Update task status
    pub fn update_status(&mut self, status: TaskStatus) {
        self.status = status;
        self.updated_at = Some(Utc::now());
    }

    /// Update task priority
    pub fn update_priority(&mut self, priority: TaskPriority) {
        self.priority = priority;
        self.updated_at = Some(Utc::now());
    }

    /// Assign to an agent
    pub fn assign_to(&mut self, agent: String) {
        self.assigned_agent = Some(agent);
        self.updated_at = Some(Utc::now());
    }

    /// Set description
    pub fn set_description(&mut self, description: String) {
        self.description = Some(description);
        self.updated_at = Some(Utc::now());
    }

    /// Set estimated hours
    pub fn set_estimated_hours(&mut self, hours: f32) {
        self.estimated_hours = Some(hours);
        self.updated_at = Some(Utc::now());
    }

    /// Set actual hours
    pub fn set_actual_hours(&mut self, hours: f32) {
        self.actual_hours = Some(hours);
        self.updated_at = Some(Utc::now());
    }

    /// Set due date
    pub fn set_due_date(&mut self, due_date: DateTime<Utc>) {
        self.due_date = Some(due_date);
        self.updated_at = Some(Utc::now());
    }

    /// Add a dependency
    pub fn add_dependency(&mut self, task_id: String) {
        if !self.dependencies.contains(&task_id) {
            self.dependencies.push(task_id);
            self.updated_at = Some(Utc::now());
        }
    }

    /// Add a tag
    pub fn add_tag(&mut self, tag: String) {
        if !self.tags.contains(&tag) {
            self.tags.push(tag);
            self.updated_at = Some(Utc::now());
        }
    }
}

// ============================================================================
// Progress Tracking Structs
// ============================================================================

/// Project progress information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectProgress {
    pub project_id: String,
    pub total_tasks: usize,
    pub completed_tasks: usize,
    pub in_progress_tasks: usize,
    pub blocked_tasks: usize,
    pub completion_percentage: f32,
    pub estimated_total_hours: f32,
    pub actual_total_hours: f32,
}

impl ProjectProgress {
    /// Calculate progress from tasks
    pub fn from_tasks(project_id: String, tasks: &[ProjectTask]) -> Self {
        let total = tasks.len();
        let completed = tasks.iter().filter(|t| t.status == TaskStatus::Done).count();
        let in_progress = tasks.iter().filter(|t| t.status == TaskStatus::InProgress).count();
        let blocked = tasks.iter().filter(|t| t.status == TaskStatus::Blocked).count();

        let completion_percentage = if total > 0 {
            (completed as f32 / total as f32) * 100.0
        } else {
            0.0
        };

        let estimated_total_hours: f32 = tasks.iter()
            .filter_map(|t| t.estimated_hours)
            .sum();

        let actual_total_hours: f32 = tasks.iter()
            .filter_map(|t| t.actual_hours)
            .sum();

        Self {
            project_id,
            total_tasks: total,
            completed_tasks: completed,
            in_progress_tasks: in_progress,
            blocked_tasks: blocked,
            completion_percentage,
            estimated_total_hours,
            actual_total_hours,
        }
    }
}

/// Project timeline information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectTimeline {
    pub project_id: String,
    pub start_date: DateTime<Utc>,
    pub estimated_completion_date: Option<DateTime<Utc>>,
    pub actual_completion_date: Option<DateTime<Utc>>,
    pub milestones: Vec<Milestone>,
}

/// Milestone in project timeline
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Milestone {
    pub name: String,
    pub date: DateTime<Utc>,
    pub completed: bool,
}

/// Comprehensive status report
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusReport {
    pub project: Project,
    pub progress: ProjectProgress,
    pub timeline: ProjectTimeline,
    pub agent_workloads: HashMap<String, Vec<ProjectTask>>,
    pub blocked_tasks: Vec<ProjectTask>,
    pub overdue_tasks: Vec<ProjectTask>,
    pub recent_activity: Vec<String>,
}

// ============================================================================
// Git Integration Structs
// ============================================================================

/// Git repository status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitStatus {
    /// Current branch name
    pub current_branch: String,
    /// Number of uncommitted changes
    pub uncommitted_changes: usize,
    /// Number of commits ahead of remote
    pub ahead: usize,
    /// Number of commits behind remote
    pub behind: usize,
    /// List of modified files
    pub modified_files: Vec<String>,
    /// List of untracked files
    pub untracked_files: Vec<String>,
    /// Whether repository is clean
    pub is_clean: bool,
}

/// Git commit information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitCommit {
    /// Commit hash
    pub hash: String,
    /// Commit author name
    pub author: String,
    /// Commit author email
    pub email: String,
    /// Commit message
    pub message: String,
    /// Commit timestamp
    pub timestamp: DateTime<Utc>,
}

/// Git branch information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitBranch {
    /// Branch name
    pub name: String,
    /// Whether this is the current branch
    pub is_current: bool,
    /// Last commit on this branch
    pub last_commit: Option<GitCommit>,
}

/// Result of syncing project with remote
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncResult {
    /// Whether sync was successful
    pub success: bool,
    /// Number of commits pulled
    pub commits_pulled: usize,
    /// Number of commits pushed
    pub commits_pushed: usize,
    /// Any conflicts detected
    pub conflicts: Vec<String>,
    /// Sync message
    pub message: String,
}

/// Project structure analysis
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectStructure {
    /// Root directory
    pub root_path: PathBuf,
    /// Total number of files
    pub total_files: usize,
    /// Total lines of code
    pub total_lines: usize,
    /// Directory structure (path -> file count)
    pub directories: HashMap<String, usize>,
    /// File types distribution (extension -> count)
    pub file_types: HashMap<String, usize>,
    /// Main entry points
    pub entry_points: Vec<String>,
}

/// Project complexity metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplexityMetrics {
    /// Total files analyzed
    pub total_files: usize,
    /// Total lines of code
    pub total_lines: usize,
    /// Average file size (lines)
    pub avg_file_size: f32,
    /// Number of dependencies detected
    pub dependencies_count: usize,
    /// Estimated complexity score (1-10)
    pub complexity_score: u8,
    /// Breakdown by language
    pub language_breakdown: HashMap<String, usize>,
}

/// Agent workspace information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkspaceInfo {
    /// Workspace ID
    pub id: String,
    /// Agent assigned to workspace
    pub agent: String,
    /// Working branch name
    pub branch: String,
    /// Local path to workspace
    pub path: PathBuf,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
}

/// Coordination plan for parallel development
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoordinationPlan {
    /// Plan ID
    pub id: String,
    /// Project ID
    pub project_id: String,
    /// Task assignments (agent -> tasks)
    pub assignments: HashMap<String, Vec<String>>,
    /// Estimated completion time
    pub estimated_completion: DateTime<Utc>,
    /// Dependencies between tasks
    pub task_dependencies: HashMap<String, Vec<String>>,
}

/// Agent contribution to be merged
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentContribution {
    /// Contribution ID
    pub id: String,
    /// Agent who made the contribution
    pub agent: String,
    /// Branch containing contribution
    pub branch: String,
    /// Files modified
    pub files_modified: Vec<String>,
    /// Commit message
    pub commit_message: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
}

/// Result of merging contributions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MergeResult {
    /// Whether merge was successful
    pub success: bool,
    /// Number of contributions merged
    pub merged_count: usize,
    /// Conflicts detected
    pub conflicts: Vec<ConflictInfo>,
    /// Final commit hash
    pub final_commit: Option<String>,
    /// Merge message
    pub message: String,
}

/// Project health metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthMetrics {
    /// Overall health score (0-100)
    pub health_score: u8,
    /// Code quality score (0-100)
    pub code_quality_score: u8,
    /// Test coverage percentage
    pub test_coverage: f32,
    /// Number of open issues
    pub open_issues: usize,
    /// Number of bugs
    pub bugs: usize,
    /// Last commit timestamp
    pub last_commit: Option<DateTime<Utc>>,
    /// Days since last activity
    pub days_inactive: i64,
}

/// Conflict information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictInfo {
    /// File path with conflict
    pub file_path: String,
    /// Conflict type
    pub conflict_type: String,
    /// Our version
    pub our_version: Option<String>,
    /// Their version
    pub their_version: Option<String>,
    /// Line numbers affected
    pub line_numbers: Vec<usize>,
}

/// Code quality metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityMetrics {
    /// Overall quality score (0-100)
    pub overall_score: u8,
    /// Maintainability index (0-100)
    pub maintainability: u8,
    /// Code duplication percentage
    pub duplication: f32,
    /// Average complexity per function
    pub avg_complexity: f32,
    /// Issues detected
    pub issues: Vec<QualityIssue>,
}

/// Quality issue
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityIssue {
    /// Issue severity (Low, Medium, High, Critical)
    pub severity: String,
    /// File path
    pub file_path: String,
    /// Line number
    pub line_number: usize,
    /// Issue description
    pub description: String,
}

// ============================================================================
// ProjectManager - Core Coordination
// ============================================================================

/// Central project manager for coordinating multiple projects and agents
pub struct ProjectManager {
    projects: Arc<RwLock<HashMap<String, Project>>>,
    tasks: Arc<RwLock<HashMap<String, ProjectTask>>>,
    project_tasks: Arc<RwLock<HashMap<String, Vec<String>>>>, // project_id -> task_ids
}

impl ProjectManager {
    /// Create a new ProjectManager
    pub fn new() -> Self {
        Self {
            projects: Arc::new(RwLock::new(HashMap::new())),
            tasks: Arc::new(RwLock::new(HashMap::new())),
            project_tasks: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    // ========================================================================
    // CRUD Operations - Projects
    // ========================================================================

    /// Add a project
    pub async fn add_project(&self, project: Project) -> Result<()> {
        let mut projects = self.projects.write().await;
        projects.insert(project.id.clone(), project);
        Ok(())
    }

    /// Get a project by ID
    pub async fn get_project(&self, project_id: &str) -> Result<Project> {
        let projects = self.projects.read().await;
        projects.get(project_id)
            .cloned()
            .ok_or_else(|| anyhow!("Project not found: {}", project_id))
    }

    /// Update a project
    pub async fn update_project(&self, project: Project) -> Result<()> {
        let mut projects = self.projects.write().await;
        projects.insert(project.id.clone(), project);
        Ok(())
    }

    /// Delete a project
    pub async fn delete_project(&self, project_id: &str) -> Result<()> {
        let mut projects = self.projects.write().await;
        let mut project_tasks = self.project_tasks.write().await;

        projects.remove(project_id)
            .ok_or_else(|| anyhow!("Project not found: {}", project_id))?;

        // Remove all associated tasks
        if let Some(task_ids) = project_tasks.remove(project_id) {
            let mut tasks = self.tasks.write().await;
            for task_id in task_ids {
                tasks.remove(&task_id);
            }
        }

        Ok(())
    }

    /// Get all projects
    pub async fn get_all_projects(&self) -> Vec<Project> {
        let projects = self.projects.read().await;
        projects.values().cloned().collect()
    }

    // ========================================================================
    // CRUD Operations - Tasks
    // ========================================================================

    /// Add a task to a project
    pub async fn add_task(&self, task: ProjectTask) -> Result<()> {
        // Verify project exists
        {
            let projects = self.projects.read().await;
            if !projects.contains_key(&task.project_id) {
                return Err(anyhow!("Project not found: {}", task.project_id));
            }
        }

        let task_id = task.id.clone();
        let project_id = task.project_id.clone();

        // Add task
        let mut tasks = self.tasks.write().await;
        tasks.insert(task_id.clone(), task);

        // Link to project
        let mut project_tasks = self.project_tasks.write().await;
        project_tasks.entry(project_id)
            .or_insert_with(Vec::new)
            .push(task_id);

        Ok(())
    }

    /// Get a task by ID
    pub async fn get_task(&self, task_id: &str) -> Result<ProjectTask> {
        let tasks = self.tasks.read().await;
        tasks.get(task_id)
            .cloned()
            .ok_or_else(|| anyhow!("Task not found: {}", task_id))
    }

    /// Update a task
    pub async fn update_task(&self, task: ProjectTask) -> Result<()> {
        let mut tasks = self.tasks.write().await;
        tasks.insert(task.id.clone(), task);
        Ok(())
    }

    /// Delete a task
    pub async fn delete_task(&self, task_id: &str) -> Result<()> {
        let task = {
            let mut tasks = self.tasks.write().await;
            tasks.remove(task_id)
                .ok_or_else(|| anyhow!("Task not found: {}", task_id))?
        };

        // Remove from project's task list
        let mut project_tasks = self.project_tasks.write().await;
        if let Some(task_ids) = project_tasks.get_mut(&task.project_id) {
            task_ids.retain(|id| id != task_id);
        }

        Ok(())
    }

    /// Get all tasks for a project
    pub async fn get_project_tasks(&self, project_id: &str) -> Result<Vec<ProjectTask>> {
        let project_tasks = self.project_tasks.read().await;
        let task_ids = project_tasks.get(project_id)
            .ok_or_else(|| anyhow!("Project not found: {}", project_id))?;

        let tasks = self.tasks.read().await;
        let mut result = Vec::new();
        for task_id in task_ids {
            if let Some(task) = tasks.get(task_id) {
                result.push(task.clone());
            }
        }

        Ok(result)
    }

    // ========================================================================
    // Agent Coordination Methods
    // ========================================================================

    /// Assign an agent to a task
    pub async fn assign_agent_to_task(&self, task_id: &str, agent: AgentType) -> Result<()> {
        let mut tasks = self.tasks.write().await;
        let task = tasks.get_mut(task_id)
            .ok_or_else(|| anyhow!("Task not found: {}", task_id))?;

        task.assign_to(agent.as_str());
        Ok(())
    }

    /// Get workload for a specific agent
    pub async fn get_agent_workload(&self, agent: AgentType) -> Result<Vec<ProjectTask>> {
        let tasks = self.tasks.read().await;
        let agent_str = agent.as_str();

        let workload: Vec<ProjectTask> = tasks.values()
            .filter(|t| {
                t.assigned_agent.as_ref()
                    .map(|a| a == &agent_str)
                    .unwrap_or(false)
            })
            .cloned()
            .collect();

        Ok(workload)
    }

    /// Find available agents (agents with lowest workload)
    pub async fn find_available_agents(&self) -> Result<Vec<AgentType>> {
        let tasks = self.tasks.read().await;

        // Count tasks per agent
        let mut agent_counts: HashMap<String, usize> = HashMap::new();
        for task in tasks.values() {
            if let Some(agent) = &task.assigned_agent {
                if task.status != TaskStatus::Done {
                    *agent_counts.entry(agent.clone()).or_insert(0) += 1;
                }
            }
        }

        // Define all available agent types
        let all_agents = vec![
            AgentType::ClaudeCode,
            AgentType::Gemini,
            AgentType::Copilot,
            AgentType::Local,
        ];

        // Sort by workload
        let mut available: Vec<(AgentType, usize)> = all_agents.into_iter()
            .map(|agent| {
                let count = agent_counts.get(&agent.as_str()).copied().unwrap_or(0);
                (agent, count)
            })
            .collect();

        available.sort_by_key(|(_, count)| *count);

        Ok(available.into_iter().map(|(agent, _)| agent).collect())
    }

    /// Coordinate multi-agent task (split work among multiple agents)
    pub async fn coordinate_multi_agent_task(
        &self,
        task_id: &str,
        agents: Vec<AgentType>,
    ) -> Result<()> {
        let mut tasks = self.tasks.write().await;
        let task = tasks.get_mut(task_id)
            .ok_or_else(|| anyhow!("Task not found: {}", task_id))?;

        // Add a special tag to indicate multi-agent coordination
        let agent_list = agents.iter()
            .map(|a| a.as_str())
            .collect::<Vec<_>>()
            .join(",");

        task.add_tag(format!("multi-agent:{}", agent_list));
        task.updated_at = Some(Utc::now());

        Ok(())
    }

    // ========================================================================
    // Progress Tracking Methods
    // ========================================================================

    /// Get project progress
    pub async fn get_project_progress(&self, project_id: &str) -> Result<ProjectProgress> {
        let tasks = self.get_project_tasks(project_id).await?;
        Ok(ProjectProgress::from_tasks(project_id.to_string(), &tasks))
    }

    /// Get task dependencies (tasks that this task depends on)
    pub async fn get_task_dependencies(&self, task_id: &str) -> Result<Vec<ProjectTask>> {
        let task = self.get_task(task_id).await?;
        let tasks = self.tasks.read().await;

        let mut dependencies = Vec::new();
        for dep_id in &task.dependencies {
            if let Some(dep_task) = tasks.get(dep_id) {
                dependencies.push(dep_task.clone());
            }
        }

        Ok(dependencies)
    }

    /// Calculate project timeline
    pub async fn calculate_project_timeline(&self, project_id: &str) -> Result<ProjectTimeline> {
        let project = self.get_project(project_id).await?;
        let tasks = self.get_project_tasks(project_id).await?;

        // Calculate estimated completion based on remaining hours
        let remaining_hours: f32 = tasks.iter()
            .filter(|t| t.status != TaskStatus::Done)
            .filter_map(|t| t.estimated_hours)
            .sum();

        // Assume 8 hour work days
        let days_remaining = (remaining_hours / 8.0).ceil() as i64;
        let estimated_completion = if remaining_hours > 0.0 {
            Some(Utc::now() + Duration::days(days_remaining))
        } else {
            None
        };

        // Check if actually completed
        let actual_completion = if project.status == ProjectStatus::Completed {
            project.updated_at
        } else {
            None
        };

        Ok(ProjectTimeline {
            project_id: project_id.to_string(),
            start_date: project.created_at,
            estimated_completion_date: estimated_completion,
            actual_completion_date: actual_completion,
            milestones: Vec::new(), // Could be enhanced with milestone tracking
        })
    }

    /// Generate comprehensive status report
    pub async fn generate_status_report(&self, project_id: &str) -> Result<StatusReport> {
        let project = self.get_project(project_id).await?;
        let progress = self.get_project_progress(project_id).await?;
        let timeline = self.calculate_project_timeline(project_id).await?;
        let tasks = self.get_project_tasks(project_id).await?;

        // Group tasks by agent
        let mut agent_workloads: HashMap<String, Vec<ProjectTask>> = HashMap::new();
        for task in &tasks {
            if let Some(agent) = &task.assigned_agent {
                agent_workloads.entry(agent.clone())
                    .or_insert_with(Vec::new)
                    .push(task.clone());
            }
        }

        // Get blocked tasks
        let blocked_tasks: Vec<ProjectTask> = tasks.iter()
            .filter(|t| t.status == TaskStatus::Blocked)
            .cloned()
            .collect();

        // Get overdue tasks
        let now = Utc::now();
        let overdue_tasks: Vec<ProjectTask> = tasks.iter()
            .filter(|t| {
                if let Some(due) = t.due_date {
                    due < now && t.status != TaskStatus::Done
                } else {
                    false
                }
            })
            .cloned()
            .collect();

        Ok(StatusReport {
            project,
            progress,
            timeline,
            agent_workloads,
            blocked_tasks,
            overdue_tasks,
            recent_activity: Vec::new(), // Could be enhanced with activity tracking
        })
    }

    // ========================================================================
    // Git Integration Methods
    // ========================================================================

    /// Clone a repository to a local path
    pub async fn clone_repository(&self, url: &str, local_path: &Path) -> Result<()> {
        // Ensure parent directory exists
        if let Some(parent) = local_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }

        // Clone repository (blocking operation, run in spawn_blocking)
        let url = url.to_string();
        let local_path = local_path.to_path_buf();

        tokio::task::spawn_blocking(move || {
            Repository::clone(&url, &local_path)
                .map_err(|e| anyhow!("Failed to clone repository: {}", e))?;
            Ok::<_, anyhow::Error>(())
        }).await??;

        Ok(())
    }

    /// Get repository status for a project
    pub async fn get_repository_status(&self, project_id: &str) -> Result<GitStatus> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();

        tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)
                .map_err(|e| anyhow!("Failed to open repository: {}", e))?;

            // Get current branch
            let head = repo.head()?;
            let current_branch = head.shorthand()
                .unwrap_or("detached HEAD")
                .to_string();

            // Get status
            let mut opts = StatusOptions::new();
            opts.include_untracked(true);
            let statuses = repo.statuses(Some(&mut opts))?;

            let mut modified_files = Vec::new();
            let mut untracked_files = Vec::new();
            let uncommitted_changes = statuses.len();

            for entry in statuses.iter() {
                if let Some(path) = entry.path() {
                    let status = entry.status();
                    if status.is_wt_modified() || status.is_index_modified() {
                        modified_files.push(path.to_string());
                    }
                    if status.is_wt_new() {
                        untracked_files.push(path.to_string());
                    }
                }
            }

            // Calculate ahead/behind (simplified - assumes origin/main)
            let (ahead, behind) = match repo.revparse_ext("origin/main") {
                Ok((remote_obj, _)) => {
                    let local_oid = head.target().unwrap_or_else(|| Oid::zero());
                    let remote_oid = remote_obj.id();

                    let (ahead, behind) = repo.graph_ahead_behind(local_oid, remote_oid)
                        .unwrap_or((0, 0));
                    (ahead, behind)
                },
                Err(_) => (0, 0),
            };

            Ok(GitStatus {
                current_branch,
                uncommitted_changes,
                ahead,
                behind,
                modified_files,
                untracked_files,
                is_clean: uncommitted_changes == 0,
            })
        }).await?
    }

    /// Create a new branch for a project
    pub async fn create_branch(&self, project_id: &str, branch_name: &str) -> Result<()> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();
        let branch_name = branch_name.to_string();

        tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)?;
            let head = repo.head()?;
            let commit = head.peel_to_commit()?;

            repo.branch(&branch_name, &commit, false)
                .map_err(|e| anyhow!("Failed to create branch: {}", e))?;

            Ok::<_, anyhow::Error>(())
        }).await??;

        Ok(())
    }

    /// Commit changes for a project
    pub async fn commit_changes(&self, project_id: &str, message: &str) -> Result<String> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();
        let message = message.to_string();

        let commit_hash = tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)?;
            let mut index = repo.index()?;

            // Add all changes
            index.add_all(["."].iter(), git2::IndexAddOption::DEFAULT, None)?;
            index.write()?;

            let tree_id = index.write_tree()?;
            let tree = repo.find_tree(tree_id)?;

            // Get signature
            let signature = Signature::now("xSwarm Boss", "boss@xswarm.dev")?;

            // Get parent commit
            let head = repo.head()?;
            let parent_commit = head.peel_to_commit()?;

            // Create commit
            let oid = repo.commit(
                Some("HEAD"),
                &signature,
                &signature,
                &message,
                &tree,
                &[&parent_commit],
            )?;

            Ok::<String, anyhow::Error>(oid.to_string())
        }).await??;

        Ok(commit_hash)
    }

    /// Push changes to remote
    pub async fn push_changes(&self, project_id: &str, branch: &str) -> Result<()> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();
        let branch = branch.to_string();

        tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)?;
            let mut remote = repo.find_remote("origin")
                .or_else(|_| repo.remote_anonymous("origin"))?;

            remote.push(&[format!("refs/heads/{}", branch)], None)
                .map_err(|e| anyhow!("Failed to push: {}", e))?;

            Ok::<_, anyhow::Error>(())
        }).await??;

        Ok(())
    }

    /// Pull latest changes from remote
    pub async fn pull_latest(&self, project_id: &str) -> Result<()> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();

        tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)?;

            // Fetch from origin
            let mut remote = repo.find_remote("origin")?;
            remote.fetch(&["main"], None, None)?;

            // Get fetch head
            let fetch_head = repo.find_reference("FETCH_HEAD")?;
            let fetch_commit = repo.reference_to_annotated_commit(&fetch_head)?;

            // Merge
            let analysis = repo.merge_analysis(&[&fetch_commit])?;

            if analysis.0.is_up_to_date() {
                return Ok(());
            } else if analysis.0.is_fast_forward() {
                // Fast-forward merge
                let refname = "refs/heads/main";
                let mut reference = repo.find_reference(refname)?;
                reference.set_target(fetch_commit.id(), "Fast-forward")?;
                repo.set_head(refname)?;
                repo.checkout_head(Some(git2::build::CheckoutBuilder::default().force()))?;
            } else {
                return Err(anyhow!("Merge conflicts detected - manual resolution required"));
            }

            Ok::<_, anyhow::Error>(())
        }).await??;

        Ok(())
    }

    /// Get commit history
    pub async fn get_commit_history(&self, project_id: &str, limit: usize) -> Result<Vec<GitCommit>> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();

        tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)?;
            let mut revwalk = repo.revwalk()?;
            revwalk.push_head()?;

            let mut commits = Vec::new();
            for (i, oid) in revwalk.enumerate() {
                if i >= limit {
                    break;
                }

                let oid = oid?;
                let commit = repo.find_commit(oid)?;

                commits.push(GitCommit {
                    hash: oid.to_string(),
                    author: commit.author().name().unwrap_or("Unknown").to_string(),
                    email: commit.author().email().unwrap_or("unknown@example.com").to_string(),
                    message: commit.message().unwrap_or("").to_string(),
                    timestamp: Utc::now(), // git2 time conversion is complex, simplified here
                });
            }

            Ok::<Vec<GitCommit>, anyhow::Error>(commits)
        }).await?
    }

    // ========================================================================
    // Project Coordination Methods
    // ========================================================================

    /// Sync project with remote repository
    pub async fn sync_project_with_remote(&self, project_id: &str) -> Result<SyncResult> {
        let initial_status = self.get_repository_status(project_id).await?;

        // Pull latest changes
        match self.pull_latest(project_id).await {
            Ok(_) => {},
            Err(e) => {
                return Ok(SyncResult {
                    success: false,
                    commits_pulled: 0,
                    commits_pushed: 0,
                    conflicts: vec![e.to_string()],
                    message: format!("Failed to pull: {}", e),
                });
            }
        }

        // Push any local commits
        let final_status = self.get_repository_status(project_id).await?;
        if final_status.ahead > 0 {
            match self.push_changes(project_id, &final_status.current_branch).await {
                Ok(_) => {},
                Err(e) => {
                    return Ok(SyncResult {
                        success: false,
                        commits_pulled: 0,
                        commits_pushed: 0,
                        conflicts: vec![e.to_string()],
                        message: format!("Failed to push: {}", e),
                    });
                }
            }
        }

        Ok(SyncResult {
            success: true,
            commits_pulled: initial_status.behind,
            commits_pushed: initial_status.ahead,
            conflicts: Vec::new(),
            message: "Sync successful".to_string(),
        })
    }

    /// Detect project technology stack
    pub async fn detect_project_technology_stack(&self, project_path: &Path) -> Result<Vec<String>> {
        let mut technologies = Vec::new();
        let project_path = project_path.to_path_buf();

        tokio::task::spawn_blocking(move || {
            // Check for various technology indicators
            let indicators = vec![
                ("package.json", "Node.js/JavaScript"),
                ("Cargo.toml", "Rust"),
                ("go.mod", "Go"),
                ("requirements.txt", "Python"),
                ("Gemfile", "Ruby"),
                ("pom.xml", "Java/Maven"),
                ("build.gradle", "Java/Gradle"),
                ("composer.json", "PHP"),
                (".csproj", "C#/.NET"),
            ];

            for (file, tech) in indicators {
                let check_path = project_path.join(file);
                if check_path.exists() {
                    technologies.push(tech.to_string());
                }
            }

            Ok::<Vec<String>, anyhow::Error>(technologies)
        }).await?
    }

    /// Analyze project structure
    pub async fn analyze_project_structure(&self, project_id: &str) -> Result<ProjectStructure> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let root_path = local_path.clone();

        tokio::task::spawn_blocking(move || {
            use std::fs;

            let mut total_files = 0;
            let mut total_lines = 0;
            let mut directories: HashMap<String, usize> = HashMap::new();
            let mut file_types: HashMap<String, usize> = HashMap::new();
            let mut entry_points: Vec<String> = Vec::new();

            fn walk_dir(path: &Path, stats: &mut (usize, usize, HashMap<String, usize>, HashMap<String, usize>, Vec<String>)) {
                if let Ok(entries) = fs::read_dir(path) {
                    for entry in entries.flatten() {
                        let path = entry.path();

                        // Skip hidden and vendor directories
                        if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                            if name.starts_with('.') || name == "node_modules" || name == "target" || name == "vendor" {
                                continue;
                            }
                        }

                        if path.is_dir() {
                            let dir_name = path.to_string_lossy().to_string();
                            *stats.2.entry(dir_name.clone()).or_insert(0) += 1;
                            walk_dir(&path, stats);
                        } else if path.is_file() {
                            stats.0 += 1;

                            // Count lines
                            if let Ok(content) = fs::read_to_string(&path) {
                                stats.1 += content.lines().count();
                            }

                            // Track file types
                            if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                                *stats.3.entry(ext.to_string()).or_insert(0) += 1;
                            }

                            // Detect entry points
                            if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                                if name == "main.rs" || name == "main.go" || name == "index.js" ||
                                   name == "app.py" || name == "Main.java" {
                                    stats.4.push(path.to_string_lossy().to_string());
                                }
                            }
                        }
                    }
                }
            }

            let mut stats = (0, 0, HashMap::new(), HashMap::new(), Vec::new());
            walk_dir(&root_path, &mut stats);

            Ok(ProjectStructure {
                root_path,
                total_files: stats.0,
                total_lines: stats.1,
                directories: stats.2,
                file_types: stats.3,
                entry_points: stats.4,
            })
        }).await?
    }

    /// Estimate project complexity
    pub async fn estimate_project_complexity(&self, project_id: &str) -> Result<ComplexityMetrics> {
        let structure = self.analyze_project_structure(project_id).await?;

        // Calculate metrics
        let avg_file_size = if structure.total_files > 0 {
            structure.total_lines as f32 / structure.total_files as f32
        } else {
            0.0
        };

        // Estimate complexity score (1-10)
        let complexity_score = {
            let size_score = (structure.total_lines / 10000).min(3) as u8;
            let file_count_score = (structure.total_files / 100).min(3) as u8;
            let diversity_score = (structure.file_types.len() / 5).min(2) as u8;
            let depth_score = (structure.directories.len() / 20).min(2) as u8;

            (size_score + file_count_score + diversity_score + depth_score).min(10)
        };

        // Language breakdown from file extensions
        let mut language_breakdown = HashMap::new();
        for (ext, count) in &structure.file_types {
            let lang = match ext.as_str() {
                "rs" => "Rust",
                "js" | "jsx" | "ts" | "tsx" => "JavaScript/TypeScript",
                "py" => "Python",
                "go" => "Go",
                "java" => "Java",
                "rb" => "Ruby",
                "php" => "PHP",
                "cs" => "C#",
                _ => continue,
            };
            *language_breakdown.entry(lang.to_string()).or_insert(0) += count;
        }

        Ok(ComplexityMetrics {
            total_files: structure.total_files,
            total_lines: structure.total_lines,
            avg_file_size,
            dependencies_count: 0, // Could be enhanced by parsing package files
            complexity_score,
            language_breakdown,
        })
    }

    /// Create an agent workspace
    pub async fn create_agent_workspace(&self, project_id: &str, agent: AgentType) -> Result<WorkspaceInfo> {
        let project = self.get_project(project_id).await?;
        let branch_name = format!("agent-{}-{}", agent.as_str(), Uuid::new_v4());

        // Create branch for agent
        self.create_branch(project_id, &branch_name).await?;

        Ok(WorkspaceInfo {
            id: Uuid::new_v4().to_string(),
            agent: agent.as_str(),
            branch: branch_name,
            path: project.local_path.unwrap_or_default(),
            created_at: Utc::now(),
        })
    }

    /// Coordinate parallel development
    pub async fn coordinate_parallel_development(
        &self,
        project_id: &str,
        tasks: Vec<String>,
    ) -> Result<CoordinationPlan> {
        let available_agents = self.find_available_agents().await?;

        // Distribute tasks among available agents
        let mut assignments: HashMap<String, Vec<String>> = HashMap::new();
        for (i, task) in tasks.iter().enumerate() {
            let agent_idx = i % available_agents.len();
            let agent = &available_agents[agent_idx];
            assignments.entry(agent.as_str())
                .or_insert_with(Vec::new)
                .push(task.clone());
        }

        // Estimate completion time (simplified)
        let max_tasks_per_agent = assignments.values()
            .map(|tasks| tasks.len())
            .max()
            .unwrap_or(0);
        let estimated_hours = max_tasks_per_agent as i64 * 2; // 2 hours per task estimate
        let estimated_completion = Utc::now() + Duration::hours(estimated_hours);

        Ok(CoordinationPlan {
            id: Uuid::new_v4().to_string(),
            project_id: project_id.to_string(),
            assignments,
            estimated_completion,
            task_dependencies: HashMap::new(),
        })
    }

    /// Merge agent contributions
    pub async fn merge_agent_contributions(
        &self,
        project_id: &str,
        contributions: Vec<AgentContribution>,
    ) -> Result<MergeResult> {
        let mut merged_count = 0;
        let mut conflicts = Vec::new();

        for contribution in contributions {
            // Attempt to merge each contribution
            match self.merge_branch(project_id, &contribution.branch).await {
                Ok(_) => merged_count += 1,
                Err(e) => {
                    conflicts.push(ConflictInfo {
                        file_path: contribution.branch.clone(),
                        conflict_type: "merge".to_string(),
                        our_version: None,
                        their_version: None,
                        line_numbers: Vec::new(),
                    });
                }
            }
        }

        let success = conflicts.is_empty();
        let conflicts_count = conflicts.len();
        let final_commit = if success {
            Some(Uuid::new_v4().to_string())
        } else {
            None
        };

        Ok(MergeResult {
            success,
            merged_count,
            conflicts,
            final_commit,
            message: if success {
                format!("Successfully merged {} contributions", merged_count)
            } else {
                format!("Merged {} contributions with {} conflicts", merged_count, conflicts_count)
            },
        })
    }

    /// Helper method to merge a branch
    async fn merge_branch(&self, project_id: &str, branch: &str) -> Result<()> {
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();
        let branch = branch.to_string();

        tokio::task::spawn_blocking(move || {
            let repo = Repository::open(&local_path)?;
            let branch_ref = repo.find_branch(&branch, BranchType::Local)?;
            let annotated = repo.reference_to_annotated_commit(branch_ref.get())?;

            let analysis = repo.merge_analysis(&[&annotated])?;

            if analysis.0.is_up_to_date() {
                return Ok(());
            } else if analysis.0.is_fast_forward() {
                // Fast-forward merge
                let refname = "refs/heads/main";
                let mut reference = repo.find_reference(refname)?;
                reference.set_target(annotated.id(), "Fast-forward")?;
                repo.set_head(refname)?;
                repo.checkout_head(Some(git2::build::CheckoutBuilder::default().force()))?;
            } else {
                return Err(anyhow!("Merge conflicts detected"));
            }

            Ok::<_, anyhow::Error>(())
        }).await??;

        Ok(())
    }

    // ========================================================================
    // Project Monitoring Methods
    // ========================================================================

    /// Monitor project health
    pub async fn monitor_project_health(&self, project_id: &str) -> Result<HealthMetrics> {
        let project = self.get_project(project_id).await?;
        let tasks = self.get_project_tasks(project_id).await?;
        let complexity = self.estimate_project_complexity(project_id).await?;

        // Calculate health score
        let bugs = tasks.iter().filter(|t| t.tags.contains(&"bug".to_string())).count();
        let open_issues = tasks.iter().filter(|t| t.status != TaskStatus::Done).count();

        let health_score = {
            let bug_penalty = (bugs * 10).min(30) as u8;
            let issue_penalty = (open_issues * 5).min(30) as u8;
            let complexity_penalty = complexity.complexity_score * 4;
            100u8.saturating_sub(bug_penalty).saturating_sub(issue_penalty).saturating_sub(complexity_penalty)
        };

        let code_quality_score = 100u8.saturating_sub(complexity.complexity_score * 10);

        let days_inactive = if let Some(updated) = project.updated_at {
            (Utc::now() - updated).num_days()
        } else {
            (Utc::now() - project.created_at).num_days()
        };

        Ok(HealthMetrics {
            health_score,
            code_quality_score,
            test_coverage: 0.0, // Would require test framework integration
            open_issues,
            bugs,
            last_commit: project.updated_at,
            days_inactive,
        })
    }

    /// Detect merge conflicts
    pub async fn detect_merge_conflicts(&self, project_id: &str) -> Result<Vec<ConflictInfo>> {
        let status = self.get_repository_status(project_id).await?;

        // Check for conflict markers in modified files
        let project = self.get_project(project_id).await?;
        let local_path = project.local_path
            .ok_or_else(|| anyhow!("Project has no local path set"))?;

        let local_path = local_path.clone();
        let modified_files = status.modified_files.clone();

        tokio::task::spawn_blocking(move || {
            use std::fs;
            let mut conflicts = Vec::new();

            for file in modified_files {
                let file_path = local_path.join(&file);
                if let Ok(content) = fs::read_to_string(&file_path) {
                    let lines: Vec<&str> = content.lines().collect();
                    let mut in_conflict = false;
                    let mut conflict_lines = Vec::new();

                    for (i, line) in lines.iter().enumerate() {
                        if line.starts_with("<<<<<<<") {
                            in_conflict = true;
                            conflict_lines.push(i + 1);
                        } else if line.starts_with(">>>>>>>") && in_conflict {
                            in_conflict = false;

                            conflicts.push(ConflictInfo {
                                file_path: file.clone(),
                                conflict_type: "merge".to_string(),
                                our_version: None,
                                their_version: None,
                                line_numbers: conflict_lines.clone(),
                            });
                            conflict_lines.clear();
                        }
                    }
                }
            }

            Ok::<Vec<ConflictInfo>, anyhow::Error>(conflicts)
        }).await?
    }

    /// Analyze code quality
    pub async fn analyze_code_quality(&self, project_id: &str) -> Result<QualityMetrics> {
        let complexity = self.estimate_project_complexity(project_id).await?;

        // Simplified quality analysis
        let overall_score = 100u8.saturating_sub(complexity.complexity_score * 10);
        let maintainability = if complexity.avg_file_size < 300.0 { 85 } else { 60 };

        Ok(QualityMetrics {
            overall_score,
            maintainability,
            duplication: 0.0, // Would require code duplication detection
            avg_complexity: complexity.avg_file_size / 50.0,
            issues: Vec::new(), // Would require linter integration
        })
    }
}

impl Default for ProjectManager {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_project_creation() {
        let project = Project::new("Test Project".to_string(), "user123".to_string());
        assert_eq!(project.name, "Test Project");
        assert_eq!(project.owner_id, "user123");
        assert_eq!(project.status, ProjectStatus::Active);
        assert_eq!(project.priority, ProjectPriority::Medium);
    }

    #[test]
    fn test_task_creation() {
        let task = ProjectTask::new("proj123".to_string(), "Test Task".to_string());
        assert_eq!(task.title, "Test Task");
        assert_eq!(task.project_id, "proj123");
        assert_eq!(task.status, TaskStatus::Todo);
        assert_eq!(task.priority, TaskPriority::Medium);
    }

    #[test]
    fn test_agent_type_conversion() {
        let agent = AgentType::ClaudeCode;
        assert_eq!(agent.as_str(), "claude-code");

        let agent2 = AgentType::from_str("gemini");
        assert_eq!(agent2, AgentType::Gemini);
    }

    #[test]
    fn test_priority_numeric_conversion() {
        let priority = ProjectPriority::High;
        assert_eq!(priority.to_numeric(), 3);

        let priority2 = ProjectPriority::from_numeric(1);
        assert_eq!(priority2, ProjectPriority::Low);
    }

    #[tokio::test]
    async fn test_project_manager_basic_operations() {
        let manager = ProjectManager::new();

        let project = Project::new("Test".to_string(), "user1".to_string());
        let project_id = project.id.clone();

        manager.add_project(project).await.unwrap();

        let retrieved = manager.get_project(&project_id).await.unwrap();
        assert_eq!(retrieved.name, "Test");
    }

    #[tokio::test]
    async fn test_task_management() {
        let manager = ProjectManager::new();

        let project = Project::new("Test".to_string(), "user1".to_string());
        let project_id = project.id.clone();
        manager.add_project(project).await.unwrap();

        let task = ProjectTask::new(project_id.clone(), "Task 1".to_string());
        manager.add_task(task).await.unwrap();

        let tasks = manager.get_project_tasks(&project_id).await.unwrap();
        assert_eq!(tasks.len(), 1);
        assert_eq!(tasks[0].title, "Task 1");
    }

    #[tokio::test]
    async fn test_agent_assignment() {
        let manager = ProjectManager::new();

        let project = Project::new("Test".to_string(), "user1".to_string());
        let project_id = project.id.clone();
        manager.add_project(project).await.unwrap();

        let task = ProjectTask::new(project_id.clone(), "Task 1".to_string());
        let task_id = task.id.clone();
        manager.add_task(task).await.unwrap();

        manager.assign_agent_to_task(&task_id, AgentType::ClaudeCode).await.unwrap();

        let updated_task = manager.get_task(&task_id).await.unwrap();
        assert_eq!(updated_task.assigned_agent, Some("claude-code".to_string()));
    }

    #[tokio::test]
    async fn test_project_progress() {
        let manager = ProjectManager::new();

        let project = Project::new("Test".to_string(), "user1".to_string());
        let project_id = project.id.clone();
        manager.add_project(project).await.unwrap();

        let mut task1 = ProjectTask::new(project_id.clone(), "Task 1".to_string());
        task1.update_status(TaskStatus::Done);
        manager.add_task(task1).await.unwrap();

        let task2 = ProjectTask::new(project_id.clone(), "Task 2".to_string());
        manager.add_task(task2).await.unwrap();

        let progress = manager.get_project_progress(&project_id).await.unwrap();
        assert_eq!(progress.total_tasks, 2);
        assert_eq!(progress.completed_tasks, 1);
        assert_eq!(progress.completion_percentage, 50.0);
    }
}
