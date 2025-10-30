# Reminder System Implementation

This document describes the comprehensive reminder system integrated with supervisor notifications.

## Overview

The reminder system enables Boss to proactively notify users about upcoming appointments across all communication channels (SMS, Email, and Voice).

## Components

### 1. Core Data Structures (`scheduler.rs`)

#### ReminderStatus
Tracks the lifecycle of a reminder:
- `Pending` - Reminder is scheduled but not yet sent
- `Sent` - Reminder was successfully delivered
- `Failed` - Reminder delivery failed
- `Cancelled` - Reminder was cancelled before sending
- `Snoozed` - User snoozed the reminder

#### ReminderMethod
Supported delivery methods:
- `Sms` - SMS text message
- `Email` - Email with HTML formatting
- `Voice` - Spoken notification via MOSHI
- `Push` - Push notification (reserved for future use)

#### ReminderPreferences
User's personalization settings:
```rust
pub struct ReminderPreferences {
    pub user_id: String,
    pub preferred_methods: Vec<ReminderMethod>,
    pub default_minutes_before: Vec<u32>,
    pub quiet_hours_start: Option<u8>,
    pub quiet_hours_end: Option<u8>,
    pub timezone: String,
    pub reminders_enabled: bool,
}
```

#### AppointmentReminder
Enhanced reminder with delivery tracking:
```rust
pub struct AppointmentReminder {
    pub id: String,
    pub appointment_id: String,
    pub user_id: String,
    pub minutes_before: u32,
    pub method: ReminderMethod,
    pub status: ReminderStatus,
    pub scheduled_time: DateTime<Utc>,
    pub sent_at: Option<DateTime<Utc>>,
    pub error_message: Option<String>,
    pub retry_count: u32,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}
```

### 2. SchedulerManager API Methods

#### Reminder Management
- `get_due_reminders() -> Result<Vec<AppointmentReminder>>` - Fetch reminders that need to be sent
- `create_reminder_for_appointment(appointment_id, minutes_before) -> Result<AppointmentReminder>` - Create reminder for an appointment
- `mark_reminder_sent(reminder_id, success, error_message) -> Result<()>` - Update reminder status after sending

#### User Preferences
- `update_reminder_preferences(preferences) -> Result<()>` - Update user's reminder preferences
- `get_user_reminder_preferences() -> Result<ReminderPreferences>` - Retrieve user preferences

### 3. ReminderProcessor

Background task that checks for due reminders and processes them.

#### Key Methods
- `check_due_reminders() -> Result<Vec<AppointmentReminder>>` - Find reminders that need to be sent
- `process_reminder(reminder) -> Result<ReminderNotification>` - Format and prepare reminder for sending
- `start_reminder_loop()` - Background loop that checks for due reminders (default: every 60 seconds)

#### Message Formatting
- **SMS**: Concise message under 160 characters
  ```
  Reminder: Team Meeting in 15 min at 2:00 PM in Conference Room A
  ```

- **Email**: Rich HTML with full appointment details
  ```html
  <html>
    <h2>Upcoming Appointment Reminder</h2>
    <div>
      <p><strong>Title:</strong> Team Meeting</p>
      <p><strong>When:</strong> March 15, 2025 at 2:00 PM UTC (in 15 minutes)</p>
      <p><strong>Location:</strong> Conference Room A</p>
    </div>
  </html>
  ```

- **Voice**: Natural spoken text
  ```
  Reminder: You have Team Meeting in 15 minutes at 2:00 PM in Conference Room A.
  ```

#### Features
- **Quiet Hours**: Respects user's do-not-disturb preferences
- **Retry Logic**: Automatically retries failed reminders (max 3 attempts)
- **Timezone Awareness**: Handles timezone conversions for accurate timing

### 4. Supervisor Integration (`supervisor.rs`)

#### New Supervisor Events
- `ReminderDue` - Reminder is ready to be sent
- `ReminderSent` - Reminder was successfully delivered
- `ReminderFailed` - Reminder delivery failed

#### Broadcasting Methods
- `broadcast_reminder_notification(notification) -> Result<()>` - Main entry point for sending reminders
- `send_sms_reminder(notification) -> Result<()>` - Send via SMS
- `send_email_reminder(notification) -> Result<()>` - Send via Email
- `send_voice_reminder(notification) -> Result<()>` - Send via MOSHI voice synthesis

## Usage Example

### Creating a Reminder for an Appointment

```rust
use std::sync::Arc;

// Create scheduler manager
let manager = Arc::new(SchedulerManager::new(
    "http://localhost:8787".to_string(),
    "user-123".to_string(),
    Some("auth-token".to_string()),
));

// Create appointment
let appointment_id = "apt-456";

// Create reminder 15 minutes before appointment
let reminder = manager
    .create_reminder_for_appointment(appointment_id, 15)
    .await?;

println!("Reminder created: {}", reminder.id);
```

### Starting the Reminder Processor

```rust
// Create reminder processor
let processor = Arc::new(ReminderProcessor::new(
    manager.clone(),
    Some(60),  // Check every 60 seconds
    Some(3),   // Max 3 retries
));

// Start background loop
tokio::spawn(async move {
    processor.start_reminder_loop().await;
});
```

### Integrating with Supervisor

```rust
// In supervisor server initialization
let supervisor = Arc::new(SupervisorServer::new(
    supervisor_config,
    moshi_state,
));

// When a reminder is due
let notification = processor.process_reminder(&reminder).await?;
supervisor.broadcast_reminder_notification(notification).await?;
```

## Database Schema

### appointment_reminders Table

```sql
CREATE TABLE IF NOT EXISTS appointment_reminders (
    id TEXT PRIMARY KEY,
    appointment_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    minutes_before INTEGER NOT NULL,
    method TEXT NOT NULL,  -- 'sms', 'email', 'voice', 'push'
    status TEXT NOT NULL,  -- 'pending', 'sent', 'failed', 'cancelled', 'snoozed'
    scheduled_time TEXT NOT NULL,  -- ISO 8601
    sent_at TEXT,  -- ISO 8601
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,  -- ISO 8601
    updated_at TEXT,  -- ISO 8601
    FOREIGN KEY (appointment_id) REFERENCES appointments(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_appointment_reminders_scheduled ON appointment_reminders(scheduled_time);
CREATE INDEX idx_appointment_reminders_status ON appointment_reminders(status);
CREATE INDEX idx_appointment_reminders_user ON appointment_reminders(user_id);
```

### reminder_preferences Table

```sql
CREATE TABLE IF NOT EXISTS reminder_preferences (
    user_id TEXT PRIMARY KEY,
    preferred_methods TEXT NOT NULL,  -- JSON array of methods
    default_minutes_before TEXT NOT NULL,  -- JSON array of integers
    quiet_hours_start INTEGER,  -- 0-23
    quiet_hours_end INTEGER,  -- 0-23
    timezone TEXT NOT NULL DEFAULT 'UTC',
    reminders_enabled INTEGER NOT NULL DEFAULT 1,  -- 0 = false, 1 = true
    created_at TEXT NOT NULL,  -- ISO 8601
    updated_at TEXT,  -- ISO 8601
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## API Endpoints (Server Implementation Required)

### GET /api/calendar/reminders/due
Returns all pending reminders that are due to be sent.

**Query Parameters:**
- `user_id` - User ID

**Response:**
```json
{
  "reminders": [
    {
      "id": "reminder-123",
      "appointment_id": "apt-456",
      "user_id": "user-789",
      "minutes_before": 15,
      "method": "sms",
      "status": "pending",
      "scheduled_time": "2025-03-15T14:45:00Z",
      "sent_at": null,
      "error_message": null,
      "retry_count": 0,
      "created_at": "2025-03-15T14:00:00Z",
      "updated_at": null
    }
  ]
}
```

### POST /api/calendar/appointment-reminders
Create a new appointment reminder.

**Request Body:**
```json
{
  "appointment_id": "apt-456",
  "user_id": "user-789",
  "minutes_before": 15,
  "method": "sms",
  "scheduled_time": "2025-03-15T14:45:00Z"
}
```

### PUT /api/calendar/appointment-reminders/:id/status
Update reminder status.

**Request Body:**
```json
{
  "status": "sent",
  "error_message": null
}
```

### GET /api/calendar/reminder-preferences
Get user's reminder preferences.

**Query Parameters:**
- `user_id` - User ID

### PUT /api/calendar/reminder-preferences
Update user's reminder preferences.

**Request Body:**
```json
{
  "user_id": "user-789",
  "preferred_methods": ["sms", "email"],
  "default_minutes_before": [15, 60],
  "quiet_hours_start": 22,
  "quiet_hours_end": 8,
  "timezone": "America/New_York",
  "reminders_enabled": true
}
```

## Testing

The implementation includes comprehensive tests:

```bash
# Run reminder system tests
cargo test test_reminder

# Run all scheduler tests
cargo test scheduler::tests
```

Tests cover:
- Reminder status lifecycle
- User preferences defaults
- Serialization/deserialization
- Message formatting (SMS, Email, Voice)
- Quiet hours logic

## Integration Checklist

To fully enable the reminder system:

- [ ] Implement database tables (appointment_reminders, reminder_preferences)
- [ ] Implement server API endpoints
- [ ] Start ReminderProcessor background task
- [ ] Connect supervisor to ReminderProcessor
- [ ] Add webhook handlers for SMS/Email delivery
- [ ] Test end-to-end reminder flow
- [ ] Set up monitoring and error alerts

## Future Enhancements

1. **Push Notifications**: Add support for mobile push notifications
2. **Smart Scheduling**: Use AI to determine optimal reminder times
3. **Multi-Language**: Support reminder messages in multiple languages
4. **Custom Templates**: Allow users to customize reminder message templates
5. **Escalation**: Send follow-up reminders if initial reminder is not acknowledged
6. **Calendar Sync**: Sync reminders with external calendars (Google, Outlook)

## Files Modified

- `packages/core/src/scheduler.rs` - Core reminder data structures and processor
- `packages/core/src/supervisor.rs` - Supervisor integration for multi-channel delivery
