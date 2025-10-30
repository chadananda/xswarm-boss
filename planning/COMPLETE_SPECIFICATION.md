# Boss AI: Complete System Specification

**Version:** 2.0
**Date:** 2025-10-29
**Status:** Comprehensive Architecture Specification

## Executive Summary

Boss AI is a comprehensive personal assistant system that enables seamless communication and project management across multiple channels (SMS, Email, Voice) while coordinating multiple AI coding agents (Claude Code, Gemini, Copilot) for software development projects.

## System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Boss AI System                          │
├─────────────────────────────────────────────────────────────┤
│  Multi-Channel Communication Layer                          │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │    SMS      │    Email    │    Voice    │   Claude    │  │
│  │  (Twilio)   │ (SendGrid)  │  (MOSHI)    │    Code     │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Supervisor System (WebSocket Hub)                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Message Routing • Event Broadcasting • State Mgmt     │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Core Services                                              │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │  Scheduler  │  Projects   │   Agents    │  Personal   │  │
│  │    Mgmt     │    Mgmt     │   Coord     │  Assistant  │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                       │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │  Database   │    Auth     │   Storage   │   Config    │  │
│  │  (Turso)    │    Mgmt     │    (R2)     │    Mgmt     │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Backend (Node.js/Cloudflare Workers)
- **Runtime**: Cloudflare Workers (Node.js compatible)
- **Database**: Turso (libsql) - Distributed SQLite
- **Storage**: Cloudflare R2 (S3-compatible)
- **HTTP Framework**: Hono.js
- **Authentication**: JWT tokens + API keys

#### Client (Rust)
- **Runtime**: Tokio async runtime
- **CLI Framework**: Clap v4
- **TUI Framework**: Ratatui + Crossterm
- **WebSocket Client**: tokio-tungstenite
- **HTTP Client**: reqwest
- **Audio Processing**: MOSHI (Kyutai)

#### External Services
- **SMS**: Twilio Messaging API
- **Email**: SendGrid Web API v3
- **Voice**: Twilio Media Streams + MOSHI
- **AI**: Anthropic Claude API
- **Git**: git2 (libgit2 bindings)

## Functional Requirements

### 1. Multi-Channel Communication System

#### 1.1 SMS Communication
**Specification:**
- **Inbound SMS Processing**: Receive SMS via Twilio webhook
- **Authentication**: Phone number verification against user database
- **Natural Language Processing**: Parse user intents (schedule, remind, query)
- **Response Generation**: AI-powered contextual responses
- **Outbound SMS**: Send reminders, confirmations, status updates

**Data Flow:**
```
User Phone → Twilio → Cloudflare Workers → Boss AI → Claude AI → Response → Twilio → User Phone
```

**API Endpoints:**
- `POST /sms/inbound` - Receive SMS from Twilio
- `POST /sms/outbound` - Send SMS via Twilio

**Message Types:**
- Appointment scheduling: "Schedule meeting tomorrow at 3pm"
- Reminders: "Remind me in 2 hours"
- Project queries: "What's the status of project X?"
- General assistance: "What's on my calendar today?"

#### 1.2 Email Communication
**Specification:**
- **Inbound Email Processing**: Receive emails via SendGrid Inbound Parse
- **Email Parsing**: Extract sender, subject, body, attachments
- **Authentication**: Email address verification
- **Rich Responses**: HTML email templates with project status, calendar views
- **Attachment Handling**: Support for project files, documents

**Data Flow:**
```
User Email → SendGrid → Cloudflare Workers → Boss AI → Claude AI → HTML Response → SendGrid → User Email
```

**API Endpoints:**
- `POST /email/inbound` - Receive emails from SendGrid
- `POST /email/outbound` - Send emails via SendGrid

**Email Templates:**
- Daily digest with calendar and project status
- Project completion notifications
- Weekly progress reports
- Appointment confirmations

#### 1.3 Voice Communication
**Specification:**
- **Real-time Voice Processing**: Twilio Media Streams + MOSHI
- **Speech-to-Text**: MOSHI transcription (24kHz → text)
- **Text-to-Speech**: MOSHI synthesis (text → 24kHz audio)
- **Natural Conversation**: Context-aware voice interactions
- **Audio Format Conversion**: μ-law ↔ PCM for Twilio compatibility

**Data Flow:**
```
User Call → Twilio → WebSocket Stream → Rust Voice Bridge → MOSHI → AI Processing → MOSHI → Twilio → User
```

**WebSocket Endpoints:**
- `ws://voice-bridge:9998` - Twilio Media Stream handler
- `ws://supervisor:9999` - Voice event broadcasting

**Voice Commands:**
- "What's on my calendar today?"
- "Schedule a meeting with John tomorrow at 2pm"
- "What's the status of the website project?"
- "Remind me to call Sarah in 30 minutes"

#### 1.4 Claude Code Integration
**Specification:**
- **Admin Message Routing**: Detect admin user messages across all channels
- **WebSocket Connection**: Direct communication with Claude Code
- **Session Management**: Maintain conversation context
- **Bidirectional Communication**: Questions and responses
- **Cost Tracking**: Monitor usage and expenses

**Data Flow:**
```
Admin User → Any Channel → Boss AI → Claude Code WebSocket → Claude Code → Response → Boss AI → Original Channel
```

**Authentication:**
- Bearer token authentication
- Admin user permission verification
- Session expiration and renewal

### 2. Scheduler and Calendar Management

#### 2.1 Natural Language Date/Time Parsing
**Specification:**
- **Relative Dates**: "tomorrow", "next week", "in 3 days"
- **Absolute Dates**: "January 15, 2024", "15/01/2024"
- **Times**: "3pm", "15:30", "3:30 PM", "noon"
- **Combined**: "tomorrow at 3pm", "next Friday at 2:30"
- **Timezone Support**: PST, EST, UTC, user's local timezone

**Parsing Examples:**
```rust
parse_natural_date("tomorrow at 3pm", "America/Los_Angeles")
  → DateTime<Utc>

parse_natural_date("next Friday", "UTC")
  → DateTime<Utc> (default 9am)

parse_natural_date("in 2 hours", "America/New_York")
  → DateTime<Utc> (relative to now)
```

#### 2.2 Appointment CRUD Operations
**Specification:**
- **Create**: Schedule new appointments with conflict detection
- **Read**: List appointments by date range, user, filters
- **Update**: Modify existing appointments with validation
- **Delete**: Cancel appointments with confirmation
- **Recurring**: Support daily, weekly, monthly, yearly patterns

**API Endpoints:**
- `POST /api/calendar/appointments` - Create appointment
- `GET /api/calendar/appointments` - List appointments
- `PUT /api/calendar/appointments/:id` - Update appointment
- `DELETE /api/calendar/appointments/:id` - Delete appointment
- `GET /api/calendar/today` - Today's schedule
- `GET /api/calendar/week` - Week view

**Database Schema:**
```sql
CREATE TABLE appointments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL, -- ISO 8601
    end_time TEXT NOT NULL,   -- ISO 8601
    timezone TEXT NOT NULL,
    location TEXT,
    participants TEXT,        -- JSON array
    recurring_rule TEXT,      -- JSON object
    reminder_minutes INTEGER,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT
);
```

#### 2.3 Conflict Detection and Resolution
**Specification:**
- **Overlap Detection**: Identify time conflicts between appointments
- **Buffer Time**: Enforce 5-minute buffers between meetings
- **Conflict Types**: Complete overlap, partial overlap, no buffer
- **Alternative Suggestions**: Find free time slots
- **Automatic Resolution**: Reschedule with user confirmation

**Conflict Types:**
```rust
enum ConflictType {
    Complete,       // Appointments completely overlap
    PartialStart,   // New appointment starts before existing ends
    PartialEnd,     // New appointment ends after existing starts
    NoBuffer,       // Back-to-back without 5-minute buffer
}
```

#### 2.4 Recurring Events
**Specification:**
- **Pattern Support**: Daily, weekly, monthly, yearly
- **Advanced Patterns**: Every Tuesday and Thursday, First Monday of month
- **End Conditions**: End date or occurrence count
- **Exception Handling**: Skip holidays, reschedule conflicts
- **Expansion Algorithm**: Generate instances within date ranges

**Recurrence Patterns:**
```rust
struct RecurrencePattern {
    frequency: RecurrenceFrequency,
    interval: u32,                    // Every N units
    end_date: Option<DateTime<Utc>>,
    occurrence_count: Option<u32>,
    days_of_week: Option<Vec<Weekday>>,
    day_of_month: Option<u8>,
}
```

#### 2.5 Reminder System
**Specification:**
- **Multi-Channel Delivery**: SMS, Email, Voice reminders
- **Smart Timing**: Default 15 minutes before, customizable
- **User Preferences**: Preferred channels, quiet hours
- **Retry Logic**: Automatic retries for failed deliveries
- **Status Tracking**: Pending, sent, failed, cancelled

**Reminder Flow:**
```
Appointment Created → Auto-generate Reminder → Check Due Time → Send via Preferred Channel → Update Status
```

**Database Schema:**
```sql
CREATE TABLE appointment_reminders (
    id TEXT PRIMARY KEY,
    appointment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    reminder_time TEXT NOT NULL,  -- ISO 8601
    method TEXT NOT NULL,         -- 'sms', 'email', 'voice'
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);
```

### 3. Project Management System

#### 3.1 Project Structure
**Specification:**
- **Project Metadata**: Name, description, status, priority
- **Technology Stack**: Languages, frameworks, tools used
- **Git Integration**: Repository URL, local path, branch tracking
- **Agent Assignments**: Which AI agents are working on what
- **Timeline Management**: Due dates, milestones, progress tracking

**Project Schema:**
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning', -- planning, active, on_hold, completed, cancelled
    priority TEXT DEFAULT 'medium', -- low, medium, high, critical
    owner_id TEXT NOT NULL,
    repository_url TEXT,
    local_path TEXT,
    technology_stack TEXT,          -- JSON array
    agent_assignments TEXT,         -- JSON object
    due_date TEXT,                  -- ISO 8601
    created_at TEXT NOT NULL,
    updated_at TEXT
);
```

#### 3.2 Task Management
**Specification:**
- **Task Hierarchy**: Projects contain multiple tasks
- **Dependencies**: Tasks can depend on other tasks
- **Agent Assignment**: Assign tasks to specific AI agents
- **Time Tracking**: Estimated vs actual hours
- **Status Workflow**: Todo → In Progress → Done/Blocked

**Task Schema:**
```sql
CREATE TABLE project_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo',     -- todo, in_progress, done, blocked
    priority TEXT DEFAULT 'medium', -- low, medium, high
    assigned_agent TEXT,
    estimated_hours REAL,
    actual_hours REAL,
    due_date TEXT,                  -- ISO 8601
    dependencies TEXT,              -- JSON array of task IDs
    tags TEXT,                      -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

#### 3.3 Git Integration
**Specification:**
- **Repository Operations**: Clone, pull, push, status
- **Branch Management**: Create, switch, merge branches
- **Commit Tracking**: Automated commits with task references
- **Conflict Resolution**: Detect and resolve merge conflicts
- **Multi-Agent Coordination**: Separate branches for each agent

**Git Operations:**
```rust
impl ProjectManager {
    async fn clone_repository(url: &str, path: &Path) -> Result<()>;
    async fn get_repository_status(project_id: &str) -> Result<GitStatus>;
    async fn create_branch(project_id: &str, branch: &str) -> Result<()>;
    async fn commit_changes(project_id: &str, message: &str) -> Result<String>;
    async fn push_changes(project_id: &str, branch: &str) -> Result<()>;
    async fn pull_latest(project_id: &str) -> Result<()>;
    async fn merge_agent_contributions(project_id: &str) -> Result<MergeResult>;
}
```

#### 3.4 Agent Coordination
**Specification:**
- **Agent Types**: Claude Code, Gemini, Copilot, Local, Human
- **Task Distribution**: Intelligent assignment based on workload
- **Workspace Isolation**: Separate working directories per agent
- **Progress Synchronization**: Real-time status updates
- **Conflict Prevention**: Coordinate simultaneous work

**Agent Framework:**
```rust
enum AgentType {
    ClaudeCode,
    Gemini,
    Copilot,
    Local,
    Human,
    Custom(String),
}

struct AgentCoordinator {
    agents: HashMap<AgentType, AgentConnection>,
    workspaces: HashMap<String, WorkspaceInfo>,
    active_tasks: HashMap<String, TaskAssignment>,
}
```

### 4. Personal Assistant Capabilities

#### 4.1 Capability Framework
**Specification:**
- **Skill Registration**: Dynamic capability discovery
- **Context Awareness**: Maintain conversation context across channels
- **Preference Learning**: Adapt to user habits and preferences
- **Proactive Assistance**: Suggest actions based on patterns
- **Integration Hub**: Connect with external services and APIs

**Core Capabilities:**
- **Calendar Management**: Scheduling, reminders, conflict resolution
- **Project Coordination**: Multi-agent task management
- **Communication Hub**: Unified messaging across channels
- **Information Retrieval**: Answer questions about projects, schedule
- **Automation**: Routine task automation and workflows

#### 4.2 Capability Summarization
**Specification:**
- **Self-Awareness**: Boss can describe its own capabilities
- **Dynamic Updates**: Capability list updates as features are added
- **Context-Sensitive**: Different capabilities available in different contexts
- **Usage Analytics**: Track which capabilities are used most
- **Help System**: Provide guidance on how to use features

**Capability Categories:**
```rust
enum CapabilityCategory {
    Communication,    // SMS, Email, Voice, Claude Code integration
    Scheduling,       // Calendar, appointments, reminders
    ProjectMgmt,      // Projects, tasks, agent coordination
    Automation,       // Workflows, triggers, routines
    Integration,      // External APIs, services, tools
    Monitoring,       // Status reports, health checks, alerts
}
```

#### 4.3 Workflow Automation
**Specification:**
- **Trigger System**: Event-based automation (time, completion, status change)
- **Action Chains**: Sequence multiple actions together
- **Conditional Logic**: If/then/else workflow branches
- **Template System**: Reusable workflow patterns
- **User Customization**: User-defined automation rules

**Workflow Examples:**
- Daily standup automation: Collect project status → Generate report → Send via email
- Appointment reminders: 24 hours before → 1 hour before → 15 minutes before
- Project completion: Mark complete → Generate summary → Notify stakeholders → Archive

### 5. Multi-Agent Coordination Framework

#### 5.1 Agent Management
**Specification:**
- **Agent Registry**: Discover and register available agents
- **Capability Matching**: Match tasks to agent capabilities
- **Load Balancing**: Distribute work based on agent availability
- **Health Monitoring**: Track agent status and performance
- **Fallback Mechanisms**: Handle agent failures gracefully

**Agent Interface:**
```rust
trait CodingAgent {
    async fn execute_task(task: &ProjectTask) -> Result<TaskResult>;
    async fn get_capabilities() -> Vec<Capability>;
    async fn get_workload() -> WorkloadMetrics;
    async fn health_check() -> HealthStatus;
}
```

#### 5.2 Task Distribution
**Specification:**
- **Intelligent Assignment**: Consider agent strengths, workload, availability
- **Parallel Execution**: Run multiple agents simultaneously on different tasks
- **Dependency Management**: Ensure prerequisite tasks complete first
- **Resource Coordination**: Prevent conflicts over shared resources
- **Progress Aggregation**: Combine progress from multiple agents

**Distribution Algorithm:**
```rust
impl TaskDistributor {
    fn assign_task(&mut self, task: ProjectTask) -> Result<AgentAssignment> {
        let suitable_agents = self.find_capable_agents(&task);
        let available_agents = self.filter_by_availability(suitable_agents);
        let best_agent = self.select_optimal_agent(available_agents, &task);
        self.create_assignment(task, best_agent)
    }
}
```

#### 5.3 Communication Protocols
**Specification:**
- **Message Format**: Standardized messages between agents and Boss
- **Event Broadcasting**: Real-time updates on task progress
- **Status Synchronization**: Keep all agents informed of project state
- **Conflict Resolution**: Mediate conflicts between agents
- **Coordination Meetings**: Virtual standups and planning sessions

**Message Types:**
```rust
enum AgentMessage {
    TaskAssigned { task_id: String, details: TaskDetails },
    TaskCompleted { task_id: String, result: TaskResult },
    StatusUpdate { agent_id: String, status: AgentStatus },
    ConflictDetected { task_id: String, conflict: ConflictInfo },
    ResourceRequest { agent_id: String, resource: ResourceType },
}
```

### 6. Monitoring and Reporting

#### 6.1 Real-time Monitoring
**Specification:**
- **System Health**: Monitor all components for availability and performance
- **Task Progress**: Real-time updates on project and task completion
- **Agent Status**: Track agent workload, performance, errors
- **Communication Metrics**: SMS/Email/Voice usage and success rates
- **Resource Usage**: Monitor database, storage, API usage

**Monitoring Dashboard:**
```rust
struct MonitoringDashboard {
    system_health: SystemHealth,
    active_projects: Vec<ProjectStatus>,
    agent_workloads: HashMap<AgentType, WorkloadMetrics>,
    communication_stats: CommunicationMetrics,
    recent_events: VecDeque<SystemEvent>,
}
```

#### 6.2 Progress Reporting
**Specification:**
- **Automated Reports**: Daily, weekly, monthly progress summaries
- **Custom Reports**: User-defined reporting schedules and content
- **Multi-Channel Delivery**: Send reports via SMS, Email, or Voice
- **Visual Reports**: Charts and graphs for project progress
- **Executive Summaries**: High-level overviews for stakeholders

**Report Types:**
- **Daily Digest**: Today's appointments, completed tasks, next actions
- **Weekly Summary**: Project progress, agent performance, upcoming deadlines
- **Monthly Review**: Major accomplishments, trends, goal achievement
- **Project Status**: Detailed project health and timeline analysis

#### 6.3 Alerting System
**Specification:**
- **Threshold Monitoring**: Alert when metrics exceed defined limits
- **Failure Detection**: Immediate alerts for system or agent failures
- **Deadline Warnings**: Proactive alerts for approaching deadlines
- **Anomaly Detection**: Identify unusual patterns or behaviors
- **Escalation Procedures**: Escalate critical issues to appropriate contacts

**Alert Categories:**
```rust
enum AlertLevel {
    Info,        // General information
    Warning,     // Potential issues
    Error,       // System errors
    Critical,    // Urgent attention required
}

enum AlertType {
    SystemHealth,
    TaskDeadline,
    AgentFailure,
    CommunicationError,
    SecurityIssue,
}
```

## Technical Architecture

### 7. Database Schema

#### 7.1 Core Tables
```sql
-- Users and Authentication
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    name TEXT NOT NULL,
    timezone TEXT DEFAULT 'UTC',
    preferences TEXT,              -- JSON object
    boss_phone TEXT,               -- Boss phone number for this user
    boss_email TEXT,               -- Boss email for this user
    can_provision_numbers BOOLEAN DEFAULT FALSE,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Calendar System
CREATE TABLE appointments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    timezone TEXT NOT NULL,
    location TEXT,
    participants TEXT,             -- JSON array
    recurring_rule TEXT,           -- JSON object
    reminder_minutes INTEGER,
    status TEXT DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE appointment_reminders (
    id TEXT PRIMARY KEY,
    appointment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    reminder_time TEXT NOT NULL,
    method TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Project Management
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning',
    priority TEXT DEFAULT 'medium',
    owner_id TEXT NOT NULL,
    repository_url TEXT,
    local_path TEXT,
    technology_stack TEXT,         -- JSON array
    agent_assignments TEXT,        -- JSON object
    due_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE TABLE project_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo',
    priority TEXT DEFAULT 'medium',
    assigned_agent TEXT,
    estimated_hours REAL,
    actual_hours REAL,
    due_date TEXT,
    dependencies TEXT,             -- JSON array
    tags TEXT,                     -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Agent Management
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,            -- claude_code, gemini, copilot, etc.
    capabilities TEXT,             -- JSON array
    endpoint_url TEXT,
    auth_token TEXT,
    status TEXT DEFAULT 'active',
    last_health_check TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE agent_tasks (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    status TEXT DEFAULT 'assigned',
    result TEXT,                   -- JSON object
    error_message TEXT,
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (task_id) REFERENCES project_tasks(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Communication Logs
CREATE TABLE communication_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel TEXT NOT NULL,         -- sms, email, voice, claude_code
    direction TEXT NOT NULL,       -- inbound, outbound
    message_content TEXT,
    metadata TEXT,                 -- JSON object
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    processed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- System Events
CREATE TABLE system_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_data TEXT,               -- JSON object
    severity TEXT DEFAULT 'info',
    user_id TEXT,
    project_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

#### 7.2 Indexes for Performance
```sql
-- User lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_boss_phone ON users(boss_phone);

-- Calendar queries
CREATE INDEX idx_appointments_user_time ON appointments(user_id, start_time);
CREATE INDEX idx_appointments_time_range ON appointments(start_time, end_time);
CREATE INDEX idx_reminders_due_time ON appointment_reminders(reminder_time, status);

-- Project queries
CREATE INDEX idx_projects_owner_status ON projects(owner_id, status);
CREATE INDEX idx_tasks_project_status ON project_tasks(project_id, status);
CREATE INDEX idx_tasks_agent ON project_tasks(assigned_agent);

-- Communication logs
CREATE INDEX idx_comm_logs_user_channel ON communication_logs(user_id, channel);
CREATE INDEX idx_comm_logs_created ON communication_logs(created_at);

-- System events
CREATE INDEX idx_events_type_created ON system_events(event_type, created_at);
CREATE INDEX idx_events_user ON system_events(user_id);
```

### 8. API Specification

#### 8.1 Authentication
**Base URL**: `https://your-domain.workers.dev`

**Authentication Methods:**
- **API Key**: `Authorization: Bearer <api_key>`
- **JWT Token**: `Authorization: Bearer <jwt_token>`
- **User Identity**: Resolved from phone/email for SMS/Email channels

#### 8.2 Calendar API
```typescript
// Get user's appointments
GET /api/calendar/appointments?user_id={id}&from={date}&to={date}
Response: { appointments: Appointment[] }

// Create appointment
POST /api/calendar/appointments
Body: {
  user_id: string,
  title: string,
  start_time: string,  // ISO 8601
  end_time: string,
  timezone: string,
  description?: string,
  location?: string,
  participants?: string[],
  recurring_rule?: RecurrencePattern,
  reminder_minutes?: number
}
Response: { appointment: Appointment }

// Update appointment
PUT /api/calendar/appointments/{id}
Body: Partial<AppointmentRequest>
Response: { appointment: Appointment }

// Delete appointment
DELETE /api/calendar/appointments/{id}
Response: { success: boolean }

// Get today's schedule
GET /api/calendar/today?user_id={id}
Response: { appointments: Appointment[] }

// Get week view
GET /api/calendar/week?user_id={id}&start_date={date}
Response: { appointments: Appointment[] }

// Check conflicts
POST /api/calendar/conflicts
Body: { appointment: AppointmentRequest, existing_appointments: Appointment[] }
Response: { conflicts: ConflictInfo[] }

// Find free slots
POST /api/calendar/free-slots
Body: {
  duration_minutes: number,
  start_date: string,
  end_date: string,
  existing_appointments: Appointment[]
}
Response: { free_slots: TimeSlot[] }
```

#### 8.3 Project Management API
```typescript
// Project CRUD
GET /api/projects?owner_id={id}&status={status}
POST /api/projects
PUT /api/projects/{id}
DELETE /api/projects/{id}
GET /api/projects/{id}

// Task CRUD
GET /api/projects/{project_id}/tasks?status={status}
POST /api/projects/{project_id}/tasks
PUT /api/tasks/{id}
DELETE /api/tasks/{id}
GET /api/tasks/{id}

// Project status and analytics
GET /api/projects/{id}/status
GET /api/projects/{id}/progress
GET /api/projects/{id}/timeline
GET /api/projects/{id}/health

// Agent management
GET /api/agents?type={type}&status={status}
POST /api/agents/{id}/assign-task
GET /api/agents/{id}/workload
POST /api/agents/{id}/health-check

// Git operations
POST /api/projects/{id}/git/clone
GET /api/projects/{id}/git/status
POST /api/projects/{id}/git/commit
POST /api/projects/{id}/git/push
POST /api/projects/{id}/git/pull
GET /api/projects/{id}/git/history
```

#### 8.4 Communication API
```typescript
// Inbound webhooks
POST /sms/inbound          // Twilio SMS webhook
POST /email/inbound        // SendGrid email webhook
POST /voice/inbound        // Twilio voice webhook

// Outbound messaging
POST /api/messages/sms
Body: { to: string, message: string, user_id: string }

POST /api/messages/email
Body: {
  to: string,
  subject: string,
  body: string,
  html?: string,
  user_id: string
}

POST /api/messages/voice
Body: { to: string, message: string, user_id: string }

// Message history
GET /api/messages/history?user_id={id}&channel={channel}&limit={n}
```

#### 8.5 Reminders API
```typescript
// Reminder CRUD
GET /api/reminders?user_id={id}&status={status}&due_before={date}
POST /api/reminders
PUT /api/reminders/{id}
DELETE /api/reminders/{id}

// Reminder preferences
GET /api/users/{id}/reminder-preferences
PUT /api/users/{id}/reminder-preferences

// Create reminder for appointment
POST /api/appointments/{id}/reminders
Body: { minutes_before: number, method: string }

// Process due reminders (internal)
POST /api/reminders/process-due
```

### 9. WebSocket API

#### 9.1 Supervisor WebSocket
**Endpoint**: `ws://127.0.0.1:9999`

**Authentication**: Bearer token in connection headers

**Message Format**:
```typescript
interface SupervisorMessage {
  type: string;
  data: any;
  timestamp: string;
  user_id?: string;
  session_id?: string;
}
```

**Message Types**:
```typescript
// Voice events
{ type: "voice_transcription", data: { text: string, confidence: number } }
{ type: "voice_synthesis", data: { audio_data: string, format: string } }

// Calendar events
{ type: "appointment_created", data: { appointment: Appointment } }
{ type: "reminder_due", data: { reminder: Reminder } }

// Project events
{ type: "task_assigned", data: { task: ProjectTask, agent: string } }
{ type: "task_completed", data: { task_id: string, result: TaskResult } }

// System events
{ type: "agent_status_change", data: { agent_id: string, status: string } }
{ type: "system_health", data: { component: string, status: string } }
```

#### 9.2 Voice Bridge WebSocket
**Endpoint**: `ws://127.0.0.1:9998`

**Protocol**: Twilio Media Stream Protocol

**Message Types**:
```typescript
// Inbound from Twilio
{ event: "connected", protocol: "Call", version: "1.0.0" }
{ event: "start", streamSid: string, callSid: string, tracks: ["inbound"] }
{ event: "media", streamSid: string, media: { track: string, chunk: string, timestamp: string, payload: string } }
{ event: "stop", streamSid: string }

// Outbound to Twilio
{ event: "media", streamSid: string, media: { payload: string } }
{ event: "mark", streamSid: string, mark: { name: string } }
```

#### 9.3 Claude Code Integration WebSocket
**Endpoint**: `ws://localhost:8080` (Claude Code instance)

**Authentication**: Bearer token

**Message Format**:
```typescript
interface ClaudeCodeMessage {
  type: "conversation" | "response" | "error";
  session_id: string;
  data: {
    message?: string;
    channel?: "sms" | "email" | "voice";
    user_id?: string;
    context?: any;
  };
}
```

## Deployment Architecture

### 10. Infrastructure Components

#### 10.1 Cloudflare Workers (Server)
**Location**: `packages/server/`
**Runtime**: Node.js compatible
**Entry Point**: `src/index.js`

**Environment Variables**:
```env
ENVIRONMENT=production
TWILIO_ACCOUNT_SID=ACxxxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_PHONE_NUMBER=+1xxxxxx
SENDGRID_API_KEY=SG.xxxx
ANTHROPIC_API_KEY=sk-ant-xxxx
TURSO_URL=libsql://xxxx
TURSO_AUTH_TOKEN=xxxx
R2_BUCKET_NAME=xswarm-boss
JWT_SECRET=xxxx
```

**Deployment**:
```bash
cd packages/server
wrangler deploy
```

#### 10.2 Rust Client
**Location**: `packages/core/`
**Binary**: `xswarm`
**Target**: Multi-platform (Linux, macOS, Windows)

**Configuration**: `config.toml`
```toml
[server]
base_url = "https://your-domain.workers.dev"
auth_token = "your-jwt-token"

[voice]
host = "127.0.0.1"
port = 9998
supervisor_port = 9999

[claude_code]
enabled = true
url = "ws://localhost:8080"
```

**Installation**:
```bash
cargo install --path packages/core
xswarm --help
```

#### 10.3 Database (Turso)
**Provider**: Turso (Distributed SQLite)
**Primary Location**: Configure based on user location
**Replicas**: Multiple regions for low latency
**Backup**: Automatic continuous backup

**Setup**:
```bash
turso db create xswarm-boss
turso db replicate xswarm-boss <region>
turso db tokens create xswarm-boss
```

#### 10.4 Storage (Cloudflare R2)
**Bucket**: `xswarm-boss`
**Purpose**: File attachments, logs, exports
**Access**: S3-compatible API

**Setup**:
```bash
wrangler r2 bucket create xswarm-boss
```

### 11. Security Considerations

#### 11.1 Authentication & Authorization
- **Multi-factor authentication** for admin users
- **Phone/email verification** for user identification
- **JWT tokens** with expiration and refresh
- **API key rotation** for service accounts
- **Permission-based access** to features and data

#### 11.2 Data Protection
- **Encryption at rest** for sensitive data
- **TLS encryption** for all API communication
- **WebSocket security** with authentication
- **Input validation** and sanitization
- **Rate limiting** to prevent abuse

#### 11.3 Privacy Compliance
- **Data minimization** - collect only necessary data
- **User consent** for data processing
- **Data retention policies** with automatic cleanup
- **Export capabilities** for user data portability
- **Deletion capabilities** for right to be forgotten

### 12. Testing Strategy

#### 12.1 Unit Testing
**Rust Tests**:
```bash
cargo test                          # All tests
cargo test --package xswarm         # Core package
cargo test scheduler::tests         # Specific module
```

**Node.js Tests**:
```bash
npm test                            # All API tests
npm run test:integration            # Integration tests
npm run test:e2e                    # End-to-end tests
```

#### 12.2 Integration Testing
**Test Scenarios**:
- SMS → Boss → Claude Code → SMS response
- Email → Boss → Calendar appointment → Reminder
- Voice → Boss → Project status → Voice response
- Multi-agent task coordination
- Git workflow automation

**Test Scripts**:
```bash
./scripts/test-sms-flow.js
./scripts/test-email-flow.js
./scripts/test-voice-flow.js
./scripts/test-agent-coordination.js
```

#### 12.3 Performance Testing
**Load Testing**:
- Concurrent SMS/Email processing
- Voice call capacity (simultaneous calls)
- Database query performance
- Agent coordination scalability

**Monitoring**:
- Response time metrics
- Error rate tracking
- Resource utilization
- Cost monitoring

## Implementation Roadmap

### Phase 1: Foundation (COMPLETED ✅)
- [x] Claude Code WebSocket connector
- [x] Complete scheduler system
- [x] Project management framework
- [x] Git integration
- [x] Multi-channel communication

### Phase 2: Integration (IN PROGRESS)
- [ ] Database migrations and schema setup
- [ ] Node.js API routes for project management
- [ ] Supervisor integration with project events
- [ ] CLI commands for all features
- [ ] Testing framework expansion

### Phase 3: Advanced Features
- [ ] Boss as self-managing project
- [ ] Full personal assistant capabilities
- [ ] Agent coordination framework
- [ ] Periodic progress reporting
- [ ] Advanced workflow automation

### Phase 4: Production Ready
- [ ] Comprehensive monitoring and alerting
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Documentation and user guides
- [ ] Deployment automation

### Phase 5: AI Enhancement
- [ ] Machine learning for preference learning
- [ ] Predictive scheduling
- [ ] Intelligent agent selection
- [ ] Natural language understanding improvements
- [ ] Proactive assistance features

## Success Metrics

### User Experience
- **Response Time**: < 5 seconds for all interactions
- **Availability**: 99.9% uptime for core services
- **Accuracy**: > 95% for natural language parsing
- **User Satisfaction**: Regular feedback collection

### System Performance
- **Throughput**: Handle 1000+ concurrent requests
- **Scalability**: Linear scaling with user growth
- **Cost Efficiency**: Optimize per-user operational costs
- **Reliability**: Zero data loss, automatic recovery

### Feature Adoption
- **Channel Usage**: Track SMS vs Email vs Voice usage
- **Feature Utilization**: Monitor which features are used most
- **Agent Effectiveness**: Measure agent productivity and success rates
- **Automation Success**: Track workflow automation adoption

## Conclusion

This specification defines a comprehensive Boss AI system that serves as a powerful personal assistant with advanced project management and multi-agent coordination capabilities. The system provides seamless communication across multiple channels while intelligently coordinating software development projects with various AI coding agents.

The modular architecture ensures scalability, maintainability, and extensibility as new features and capabilities are added. The focus on user experience, security, and performance makes this a production-ready solution for personal and professional productivity enhancement.

**Next Steps**: Proceed with Phase 2 implementation, starting with database migrations and API route development to connect the Rust client with the Node.js server infrastructure.