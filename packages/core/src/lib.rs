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
pub mod memory;
pub mod personas;

// Private modules (re-exported selectively)
mod audio;
pub mod local_audio;
pub mod audio_output;
pub mod permissions;
pub mod tts;  // Text-to-Speech synthesis
pub mod stt;  // Speech-to-Text transcription
pub mod greeting;  // MOSHI greeting generation (direct speech)
pub mod memory_conditioner;  // MOSHI memory conditioning (natural incorporation)
pub mod voice;
pub mod moshi_personality;
pub mod moshi_test;  // MOSHI audio testing with Whisper API
pub mod supervisor;
pub mod net_utils;

// Public modules for wake word detection
pub mod wake_word;

// Public modules for audio visualization
pub mod audio_visualizer;

// Public modules for TUI dashboard
pub mod dashboard;

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
pub use memory::{
    MemorySystem, MemoryConfig, MemoryItem, MemoryType,
    Fact, Entity, EntityType,
    ConversationMemory, ConversationMessage, ConversationSession, Speaker,
};
pub use personas::{
    PersonaConfig, PersonalityTraits, ResponseStyle, VerbosityLevel,
    ToneStyle, VoiceModelConfig, TrainingStatus, ConversationExample,
    PersonaClient, build_persona_prompt, apply_persona_style,
};
pub use moshi_personality::{
    MoshiPersonality, PersonalityManager, AssistantRole, ResponseConfig,
    InterruptHandling,
};
pub use audio_output::AudioOutputDevice;
pub use voice::{GpuInfo, detect_gpu};

// Force compilation of audio_output module
#[cfg(test)]
mod test_audio_output {
    use super::audio_output::AudioOutputDevice;

    #[test]
    fn test_module_exists() {
        // Just ensure the module compiles
        let _ = std::mem::size_of::<AudioOutputDevice>();
    }
}
