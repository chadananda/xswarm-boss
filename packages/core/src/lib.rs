/// xSwarm Core Library
///
/// This library provides the core functionality for xSwarm, including
/// configuration management, AI integration, voice processing, and more.

// Public modules
pub mod config;
pub mod ai;
pub mod server_client;
pub mod client;
pub mod claude_code;
pub mod projects;
pub mod scheduler;

// Private modules (re-exported selectively)
mod audio;
mod tts;
mod voice;
mod supervisor;

// Re-export commonly used types
pub use config::{Config, ProjectConfig, AdminUserConfig, UserData};
pub use projects::{
    Project, ProjectTask, ProjectStatus, TaskStatus,
    ProjectPriority, TaskPriority, AgentType,
    ProjectProgress, ProjectTimeline, StatusReport, Milestone,
    ProjectManager,
};
pub use scheduler::{
    Appointment, Reminder, ReminderPriority, RecurringRule,
    Scheduler, SchedulerManager,
};
