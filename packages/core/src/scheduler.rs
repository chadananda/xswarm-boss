// Scheduler Module - Calendar, Appointments, and Time Management
//
// This module provides:
// 1. Appointment and reminder management
// 2. Natural language parsing for voice commands
// 3. Calendar integration (Google Calendar, Outlook)
// 4. Conflict detection and timezone handling
// 5. Recurring event support (RRULE format)

use anyhow::{Context, Result};
use chrono::{DateTime, Datelike, Duration, NaiveDate, NaiveTime, Timelike, Utc, Weekday};
use chrono_english::{parse_date_string, Dialect};
use chrono_tz::Tz;
use serde::{Deserialize, Serialize};
use std::str::FromStr;

/// Appointment struct for calendar entries
/// This struct matches the database schema and is used for API interactions
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Appointment {
    pub id: String,
    pub user_id: String,
    pub title: String,
    pub description: Option<String>,
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub timezone: String,
    pub location: Option<String>,
    pub recurring_rule: Option<String>, // JSON-encoded recurring pattern
    pub reminder_minutes: Option<i32>,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}

/// Recurring rule enum for appointment recurrence patterns
/// This enum is serialized to JSON and stored in the recurring_rule field
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum RecurringRule {
    None,
    Daily,
    Weekly,
    Monthly,
    Yearly,
}

impl Default for RecurringRule {
    fn default() -> Self {
        RecurringRule::None
    }
}

/// Reminder struct for task reminders
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reminder {
    pub id: String,
    pub user_id: String,
    pub title: String,
    pub description: Option<String>,
    pub due_time: DateTime<Utc>,
    pub completed: bool,
    pub priority: ReminderPriority,
    pub created_at: DateTime<Utc>,
    pub updated_at: Option<DateTime<Utc>>,
}

/// Reminder priority levels
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ReminderPriority {
    High = 1,
    Normal = 3,
    Low = 5,
}

impl Default for ReminderPriority {
    fn default() -> Self {
        ReminderPriority::Normal
    }
}

/// Reminder status for tracking lifecycle
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ReminderStatus {
    /// Reminder is pending and not yet sent
    Pending,
    /// Reminder has been sent to user
    Sent,
    /// Reminder failed to send
    Failed,
    /// Reminder was cancelled before sending
    Cancelled,
    /// Reminder was snoozed by user
    Snoozed,
}

impl Default for ReminderStatus {
    fn default() -> Self {
        ReminderStatus::Pending
    }
}

/// Reminder delivery methods
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ReminderMethod {
    /// Send via SMS
    Sms,
    /// Send via Email
    Email,
    /// Send via Voice call (MOSHI)
    Voice,
    /// Push notification (future)
    Push,
}

/// User's reminder preferences
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReminderPreferences {
    pub user_id: String,
    /// Preferred reminder methods in order of preference
    pub preferred_methods: Vec<ReminderMethod>,
    /// Default minutes before appointment to send reminder
    pub default_minutes_before: Vec<u32>,
    /// Quiet hours - don't send reminders during these hours (24h format)
    pub quiet_hours_start: Option<u8>,
    pub quiet_hours_end: Option<u8>,
    /// Timezone for quiet hours
    pub timezone: String,
    /// Enable/disable reminders globally
    pub reminders_enabled: bool,
}

impl Default for ReminderPreferences {
    fn default() -> Self {
        Self {
            user_id: String::new(),
            preferred_methods: vec![ReminderMethod::Sms, ReminderMethod::Email],
            default_minutes_before: vec![15], // 15 minutes before by default
            quiet_hours_start: None,
            quiet_hours_end: None,
            timezone: "UTC".to_string(),
            reminders_enabled: true,
        }
    }
}

/// Enhanced reminder with delivery tracking
#[derive(Debug, Clone, Serialize, Deserialize)]
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

/// Calendar integration provider
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalendarIntegration {
    pub id: String,
    pub user_id: String,
    pub provider: CalendarProvider,
    pub external_calendar_id: String,
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub token_expires_at: Option<DateTime<Utc>>,
    pub sync_enabled: bool,
    pub last_sync_at: Option<DateTime<Utc>>,
}

/// Calendar provider types
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum CalendarProvider {
    Google,
    Outlook,
    Apple,
}

/// Natural language schedule request
#[derive(Debug, Clone)]
pub struct ScheduleRequest {
    pub raw_text: String,
    pub action: ScheduleAction,
    pub title: Option<String>,
    pub participants: Vec<String>,
    pub when: Option<ScheduleTime>,
    pub duration: Option<Duration>,
    pub location: Option<String>,
    pub recurrence: Option<RecurrencePattern>,
}

/// Schedule action types
#[derive(Debug, Clone, PartialEq)]
pub enum ScheduleAction {
    Create,
    Modify,
    Cancel,
    Query,
}

/// Schedule time specification
#[derive(Debug, Clone)]
pub enum ScheduleTime {
    Absolute(DateTime<Utc>),
    Relative(RelativeTime),
    NamedTime(String), // e.g., "tomorrow at 2pm", "next Wednesday"
}

/// Relative time specification
#[derive(Debug, Clone)]
pub struct RelativeTime {
    pub amount: i64,
    pub unit: TimeUnit,
    pub from_now: bool,
}

/// Time units for relative time
#[derive(Debug, Clone, Copy)]
pub enum TimeUnit {
    Minutes,
    Hours,
    Days,
    Weeks,
    Months,
}

/// Recurrence pattern for recurring events
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecurrencePattern {
    pub frequency: RecurrenceFrequency,
    pub interval: u32,
    pub end_date: Option<DateTime<Utc>>,
    pub occurrence_count: Option<u32>,
    pub days_of_week: Option<Vec<Weekday>>,
    pub day_of_month: Option<u8>,
    // Legacy field for backwards compatibility
    #[serde(skip_serializing_if = "Option::is_none")]
    pub until: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub count: Option<u32>,
}

impl RecurrencePattern {
    /// Create a new daily recurrence pattern
    pub fn daily(interval: u32) -> Self {
        Self {
            frequency: RecurrenceFrequency::Daily,
            interval,
            end_date: None,
            occurrence_count: None,
            days_of_week: None,
            day_of_month: None,
            until: None,
            count: None,
        }
    }

    /// Create a new weekly recurrence pattern
    pub fn weekly(interval: u32, days: Vec<Weekday>) -> Self {
        Self {
            frequency: RecurrenceFrequency::Weekly,
            interval,
            end_date: None,
            occurrence_count: None,
            days_of_week: Some(days),
            day_of_month: None,
            until: None,
            count: None,
        }
    }

    /// Create a new monthly recurrence pattern
    pub fn monthly(interval: u32, day_of_month: u8) -> Self {
        Self {
            frequency: RecurrenceFrequency::Monthly,
            interval,
            end_date: None,
            occurrence_count: None,
            days_of_week: None,
            day_of_month: Some(day_of_month),
            until: None,
            count: None,
        }
    }

    /// Set the end date for this recurrence pattern
    pub fn with_end_date(mut self, end_date: DateTime<Utc>) -> Self {
        self.end_date = Some(end_date);
        self.until = Some(end_date); // Maintain backwards compatibility
        self
    }

    /// Set the occurrence count for this recurrence pattern
    pub fn with_occurrence_count(mut self, count: u32) -> Self {
        self.occurrence_count = Some(count);
        self.count = Some(count); // Maintain backwards compatibility
        self
    }
}

/// Recurrence frequency
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum RecurrenceFrequency {
    Daily,
    Weekly,
    Monthly,
    Yearly,
}

/// Conflict information for scheduling conflicts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConflictInfo {
    pub conflicting_appointment: Appointment,
    pub conflict_type: ConflictType,
    pub overlap_start: DateTime<Utc>,
    pub overlap_end: DateTime<Utc>,
}

/// Type of scheduling conflict
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ConflictType {
    /// Appointments completely overlap
    Complete,
    /// Partial overlap - new starts before existing ends
    PartialStart,
    /// Partial overlap - new ends after existing starts
    PartialEnd,
    /// Back-to-back without buffer time
    NoBuffer,
}

/// Time slot representing an available time period
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeSlot {
    pub start: DateTime<Utc>,
    pub end: DateTime<Utc>,
    pub duration_minutes: u32,
}

// =============================================================================
// RECURRING EVENT EXPANSION
// =============================================================================

/// Expand a recurring appointment into individual instances within a date range
///
/// This function takes a recurring appointment and generates all instances
/// that fall within the specified date range, respecting the recurrence pattern.
///
/// # Arguments
/// * `appointment` - The recurring appointment to expand
/// * `start_date` - Start of the date range
/// * `end_date` - End of the date range
///
/// # Returns
/// Vector of appointment instances, each with adjusted start/end times
pub fn expand_recurring_appointment(
    appointment: &Appointment,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
) -> Result<Vec<Appointment>> {
    // Parse the recurring_rule field
    let pattern = if let Some(rule_json) = &appointment.recurring_rule {
        match serde_json::from_str::<RecurrencePattern>(rule_json) {
            Ok(pattern) => pattern,
            Err(_) => {
                // Try parsing as simple RecurringRule enum for backwards compatibility
                match serde_json::from_str::<RecurringRule>(rule_json) {
                    Ok(RecurringRule::Daily) => RecurrencePattern::daily(1),
                    Ok(RecurringRule::Weekly) => {
                        RecurrencePattern::weekly(1, vec![appointment.start_time.weekday()])
                    }
                    Ok(RecurringRule::Monthly) => {
                        RecurrencePattern::monthly(1, appointment.start_time.day() as u8)
                    }
                    Ok(RecurringRule::Yearly) => RecurrencePattern {
                        frequency: RecurrenceFrequency::Yearly,
                        interval: 1,
                        end_date: None,
                        occurrence_count: None,
                        days_of_week: None,
                        day_of_month: Some(appointment.start_time.day() as u8),
                        until: None,
                        count: None,
                    },
                    _ => anyhow::bail!("Invalid recurring rule format"),
                }
            }
        }
    } else {
        return Ok(vec![appointment.clone()]);
    };

    let mut instances = Vec::new();
    let mut current_date = appointment.start_time;
    let duration = appointment.end_time - appointment.start_time;
    let mut occurrence_count = 0;

    // Determine the effective end date
    let effective_end = if let Some(pattern_end) = pattern.end_date.or(pattern.until) {
        std::cmp::min(end_date, pattern_end)
    } else {
        end_date
    };

    // Limit iterations to prevent infinite loops
    let max_iterations = pattern.occurrence_count.or(pattern.count).unwrap_or(1000);

    while current_date <= effective_end && occurrence_count < max_iterations {
        // Check if we're within the requested range
        if current_date >= start_date && current_date <= end_date {
            // Create instance
            let mut instance = appointment.clone();
            instance.id = format!("{}_{}", appointment.id, occurrence_count);
            instance.start_time = current_date;
            instance.end_time = current_date + duration;
            instances.push(instance);

            occurrence_count += 1;

            // Check if we've hit the occurrence limit
            if let Some(max_count) = pattern.occurrence_count.or(pattern.count) {
                if occurrence_count >= max_count {
                    break;
                }
            }
        }

        // Calculate next occurrence
        current_date = calculate_next_occurrence(current_date, &pattern)?;

        // Safety check to prevent infinite loops
        if current_date > effective_end.checked_add_signed(Duration::days(365 * 10)).unwrap_or(effective_end) {
            break;
        }
    }

    Ok(instances)
}

/// Calculate the next occurrence of a recurring event
fn calculate_next_occurrence(
    current: DateTime<Utc>,
    pattern: &RecurrencePattern,
) -> Result<DateTime<Utc>> {
    match pattern.frequency {
        RecurrenceFrequency::Daily => {
            Ok(current + Duration::days(pattern.interval as i64))
        }
        RecurrenceFrequency::Weekly => {
            if let Some(days_of_week) = &pattern.days_of_week {
                // Find next occurrence on specified weekdays
                let mut next_date = current;

                // Try each day of the week until we find the next occurrence
                for _ in 0..7 * pattern.interval {
                    next_date = next_date + Duration::days(1);
                    if days_of_week.contains(&next_date.weekday()) {
                        return Ok(next_date);
                    }
                }

                Ok(next_date)
            } else {
                // Default to same weekday, N weeks later
                Ok(current + Duration::weeks(pattern.interval as i64))
            }
        }
        RecurrenceFrequency::Monthly => {
            let day_of_month = pattern.day_of_month.unwrap_or(current.day() as u8);
            let mut next_month = current.month() + pattern.interval;
            let mut next_year = current.year();

            // Handle month overflow
            while next_month > 12 {
                next_month -= 12;
                next_year += 1;
            }

            // Handle day-of-month edge cases (e.g., Feb 31 -> Feb 28/29)
            let max_days_in_month = days_in_month(next_year, next_month);
            let actual_day = std::cmp::min(day_of_month, max_days_in_month);

            // Create new date with adjusted month/year
            let naive_date = NaiveDate::from_ymd_opt(next_year, next_month, actual_day as u32)
                .context("Invalid date for monthly recurrence")?;
            let naive_time = current.time();

            Ok(naive_date.and_time(naive_time).and_utc())
        }
        RecurrenceFrequency::Yearly => {
            let next_year = current.year() + pattern.interval as i32;
            let month = current.month();
            let day = pattern.day_of_month.unwrap_or(current.day() as u8);

            // Handle leap year edge case (Feb 29)
            let max_days_in_month = days_in_month(next_year, month);
            let actual_day = std::cmp::min(day, max_days_in_month);

            let naive_date = NaiveDate::from_ymd_opt(next_year, month, actual_day as u32)
                .context("Invalid date for yearly recurrence")?;
            let naive_time = current.time();

            Ok(naive_date.and_time(naive_time).and_utc())
        }
    }
}

/// Get the number of days in a given month
fn days_in_month(year: i32, month: u32) -> u8 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 => {
            // Check for leap year
            if year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) {
                29
            } else {
                28
            }
        }
        _ => 31, // Default fallback
    }
}

// =============================================================================
// CONFLICT DETECTION
// =============================================================================

/// Check for conflicts between a new appointment and existing appointments
///
/// # Arguments
/// * `new_appointment` - The appointment to check
/// * `existing_appointments` - List of existing appointments
///
/// # Returns
/// Vector of conflict information for any detected conflicts
pub fn check_conflicts(
    new_appointment: &Appointment,
    existing_appointments: &[Appointment],
) -> Vec<ConflictInfo> {
    const BUFFER_MINUTES: i64 = 5; // Minimum buffer time between appointments

    let mut conflicts = Vec::new();

    for existing in existing_appointments {
        // Skip if same appointment (by ID)
        if existing.id == new_appointment.id {
            continue;
        }

        // Check for time overlap
        let new_start = new_appointment.start_time;
        let new_end = new_appointment.end_time;
        let existing_start = existing.start_time;
        let existing_end = existing.end_time;

        // Determine conflict type
        if new_start < existing_end && new_end > existing_start {
            let conflict_type = if new_start >= existing_start && new_end <= existing_end {
                ConflictType::Complete
            } else if new_start < existing_start && new_end > existing_start {
                ConflictType::PartialStart
            } else if new_start < existing_end && new_end > existing_end {
                ConflictType::PartialEnd
            } else {
                ConflictType::Complete
            };

            let overlap_start = std::cmp::max(new_start, existing_start);
            let overlap_end = std::cmp::min(new_end, existing_end);

            conflicts.push(ConflictInfo {
                conflicting_appointment: existing.clone(),
                conflict_type,
                overlap_start,
                overlap_end,
            });
        } else {
            // Check for buffer time violations
            let gap_before = (new_start - existing_end).num_minutes();
            let gap_after = (existing_start - new_end).num_minutes();

            if gap_before > 0 && gap_before < BUFFER_MINUTES {
                conflicts.push(ConflictInfo {
                    conflicting_appointment: existing.clone(),
                    conflict_type: ConflictType::NoBuffer,
                    overlap_start: existing_end,
                    overlap_end: new_start,
                });
            } else if gap_after > 0 && gap_after < BUFFER_MINUTES {
                conflicts.push(ConflictInfo {
                    conflicting_appointment: existing.clone(),
                    conflict_type: ConflictType::NoBuffer,
                    overlap_start: new_end,
                    overlap_end: existing_start,
                });
            }
        }
    }

    conflicts
}

/// Find free time slots within a date range
///
/// # Arguments
/// * `duration_minutes` - Required duration in minutes
/// * `start_date` - Start of search range
/// * `end_date` - End of search range
/// * `existing_appointments` - List of existing appointments
///
/// # Returns
/// Vector of available time slots
pub fn find_free_slots(
    duration_minutes: u32,
    start_date: DateTime<Utc>,
    end_date: DateTime<Utc>,
    existing_appointments: &[Appointment],
) -> Vec<TimeSlot> {
    const BUFFER_MINUTES: i64 = 5;
    const WORK_START_HOUR: u32 = 9; // 9 AM
    const WORK_END_HOUR: u32 = 17; // 5 PM

    let mut free_slots = Vec::new();
    let required_duration = Duration::minutes(duration_minutes as i64);

    // Sort appointments by start time
    let mut sorted_appointments = existing_appointments.to_vec();
    sorted_appointments.sort_by_key(|a| a.start_time);

    // Iterate through each day in the range
    let mut current_day = start_date.date_naive();
    let end_day = end_date.date_naive();

    while current_day <= end_day {
        // Define work hours for this day
        let day_start = current_day
            .and_hms_opt(WORK_START_HOUR, 0, 0)
            .unwrap()
            .and_utc();
        let day_end = current_day
            .and_hms_opt(WORK_END_HOUR, 0, 0)
            .unwrap()
            .and_utc();

        // Adjust for the search range
        let search_start = std::cmp::max(day_start, start_date);
        let search_end = std::cmp::min(day_end, end_date);

        // Get appointments for this day
        let day_appointments: Vec<&Appointment> = sorted_appointments
            .iter()
            .filter(|apt| {
                apt.start_time.date_naive() == current_day
                    || apt.end_time.date_naive() == current_day
            })
            .collect();

        if day_appointments.is_empty() {
            // Entire day is free
            let slot_duration = (search_end - search_start).num_minutes() as u32;
            if slot_duration >= duration_minutes {
                free_slots.push(TimeSlot {
                    start: search_start,
                    end: search_end,
                    duration_minutes: slot_duration,
                });
            }
        } else {
            // Check gaps between appointments
            let mut last_end = search_start;

            for apt in day_appointments {
                let apt_start = std::cmp::max(apt.start_time, search_start);
                let gap_duration = apt_start - last_end;

                if gap_duration >= required_duration + Duration::minutes(BUFFER_MINUTES) {
                    free_slots.push(TimeSlot {
                        start: last_end,
                        end: apt_start - Duration::minutes(BUFFER_MINUTES),
                        duration_minutes: gap_duration.num_minutes() as u32,
                    });
                }

                last_end = std::cmp::max(last_end, apt.end_time + Duration::minutes(BUFFER_MINUTES));
            }

            // Check gap after last appointment
            if last_end < search_end {
                let gap_duration = search_end - last_end;
                if gap_duration >= required_duration {
                    free_slots.push(TimeSlot {
                        start: last_end,
                        end: search_end,
                        duration_minutes: gap_duration.num_minutes() as u32,
                    });
                }
            }
        }

        current_day = current_day + Duration::days(1);
    }

    free_slots
}

// =============================================================================
// NATURAL LANGUAGE DATE/TIME PARSING
// =============================================================================

/// Parse a natural language date/time string into a DateTime<Utc>
///
/// Supports various formats:
/// - Relative dates: "tomorrow", "next week", "in 3 days"
/// - Specific dates: "January 15", "Jan 15 2024", "15/01/2024"
/// - Times: "3pm", "15:30", "3:30 PM", "noon", "midnight"
/// - Combined: "tomorrow at 3pm", "next Friday at 2:30"
/// - Days of week: "Monday", "next Tuesday", "this Wednesday"
/// - Timezones: "3pm PST", "2:30 EST", "15:30 UTC"
///
/// # Arguments
/// * `text` - Natural language date/time string
/// * `default_tz` - Default timezone if not specified in text (e.g., "America/Los_Angeles")
///
/// # Returns
/// * `Ok(DateTime<Utc>)` - Parsed date/time in UTC
/// * `Err` - Error message if parsing fails
pub fn parse_natural_date(text: &str, default_tz: &str) -> Result<DateTime<Utc>> {
    let text_lower = text.to_lowercase().trim().to_string();

    // Try to extract timezone from text
    let (date_text, tz) = extract_timezone(&text_lower, default_tz)?;

    // Try multiple parsing strategies

    // 1. Try parsing relative time with units (in 2 hours, in 30 minutes, etc.)
    if date_text.contains("in ") {
        if let Some(dt) = parse_relative_time_from_now(&date_text) {
            return Ok(dt);
        }
    }

    // 2. Try chrono-english for relative dates (tomorrow, next week, etc.)
    if let Ok(dt) = parse_with_chrono_english(&date_text, &tz) {
        return Ok(dt);
    }

    // 3. Try parsing combined date+time (tomorrow at 3pm, etc.)
    if let Some(dt) = parse_combined_datetime(&date_text, &tz) {
        return Ok(dt);
    }

    // 4. Try parsing time expressions (3pm, 15:30, etc.)
    if let Some(time) = parse_time_expression(&date_text) {
        let now = Utc::now();
        let dt = now.date_naive().and_time(time).and_utc();

        // If the time has already passed today, schedule for tomorrow
        if dt < now {
            let tomorrow = now + Duration::days(1);
            return Ok(tomorrow.date_naive().and_time(time).and_utc());
        }
        return Ok(dt);
    }

    // 5. Try parsing date expressions (Jan 15, 2024-01-15, etc.)
    if let Some(date) = parse_date_expression(&date_text) {
        // Default to 9am if no time specified
        let time = parse_time_expression(&date_text).unwrap_or_else(|| {
            NaiveTime::from_hms_opt(9, 0, 0).unwrap()
        });
        return Ok(date.and_time(time).and_utc());
    }

    // 6. Try dateparser as fallback
    if let Ok(dt) = dateparser::parse(&date_text) {
        return Ok(dt.with_timezone(&Utc));
    }

    anyhow::bail!("Unable to parse date/time: '{}'", text)
}

/// Parse relative time from now (e.g., "in 2 hours", "in 30 minutes")
fn parse_relative_time_from_now(text: &str) -> Option<DateTime<Utc>> {
    let words: Vec<&str> = text.split_whitespace().collect();
    let now = Utc::now();

    for i in 0..words.len().saturating_sub(2) {
        if words[i] == "in" {
            if let Ok(amount) = words[i + 1].parse::<i64>() {
                let unit = words[i + 2];
                let duration = if unit.starts_with("minute") {
                    Some(Duration::minutes(amount))
                } else if unit.starts_with("hour") {
                    Some(Duration::hours(amount))
                } else if unit.starts_with("day") {
                    Some(Duration::days(amount))
                } else if unit.starts_with("week") {
                    Some(Duration::weeks(amount))
                } else if unit.starts_with("month") {
                    Some(Duration::days(amount * 30))
                } else {
                    None
                };

                if let Some(dur) = duration {
                    return Some(now + dur);
                }
            }
        }
    }

    None
}

/// Extract timezone from text and return cleaned text + timezone
fn extract_timezone(text: &str, default_tz: &str) -> Result<(String, Tz)> {
    let tz_patterns = [
        ("pst", "America/Los_Angeles"),
        ("pacific", "America/Los_Angeles"),
        ("est", "America/New_York"),
        ("eastern", "America/New_York"),
        ("cst", "America/Chicago"),
        ("central", "America/Chicago"),
        ("mst", "America/Denver"),
        ("mountain", "America/Denver"),
        ("utc", "UTC"),
        ("gmt", "UTC"),
    ];

    for (pattern, tz_name) in &tz_patterns {
        if text.contains(pattern) {
            let clean_text = text.replace(pattern, "").trim().to_string();
            let tz = Tz::from_str(tz_name).context("Invalid timezone")?;
            return Ok((clean_text, tz));
        }
    }

    // Use default timezone
    let tz = Tz::from_str(default_tz).unwrap_or(chrono_tz::UTC);
    Ok((text.to_string(), tz))
}

/// Parse using chrono-english for relative dates
fn parse_with_chrono_english(text: &str, _tz: &Tz) -> Result<DateTime<Utc>> {
    let now = Utc::now();

    // chrono-english works with Local time, so we need to convert
    match parse_date_string(text, now, Dialect::Uk) {
        Ok(dt) => Ok(dt),
        Err(_) => anyhow::bail!("chrono-english parsing failed"),
    }
}

/// Parse time expressions like "3pm", "15:30", "3:30 PM", "noon", "midnight"
pub fn parse_time_expression(text: &str) -> Option<NaiveTime> {
    let text = text.trim().to_lowercase();

    // Handle special cases (order matters - check more specific first)
    if text.contains("afternoon") {
        return NaiveTime::from_hms_opt(14, 0, 0);
    }
    if text.contains("midnight") {
        return NaiveTime::from_hms_opt(0, 0, 0);
    }
    if text.contains("morning") {
        return NaiveTime::from_hms_opt(9, 0, 0);
    }
    if text.contains("evening") {
        return NaiveTime::from_hms_opt(18, 0, 0);
    }
    if text.contains("night") {
        return NaiveTime::from_hms_opt(20, 0, 0);
    }
    if text.contains("noon") || text.contains("midday") {
        return NaiveTime::from_hms_opt(12, 0, 0);
    }

    // Check if text contains am/pm for split parsing
    let has_pm = text.contains("pm");
    let has_am = text.contains("am");

    let words: Vec<&str> = text.split_whitespace().collect();

    // Try to find time patterns
    for (i, word) in words.iter().enumerate() {
        // Pattern: "2pm" or "2am" (no space)
        if word.ends_with("pm") || word.ends_with("am") {
            let is_pm = word.ends_with("pm");
            let num_str = word.trim_end_matches("pm").trim_end_matches("am");

            if let Ok(hour) = num_str.parse::<u32>() {
                let hour24 = if is_pm && hour != 12 {
                    hour + 12
                } else if !is_pm && hour == 12 {
                    0
                } else {
                    hour
                };

                return NaiveTime::from_hms_opt(hour24, 0, 0);
            }
        }

        // Pattern: "2 pm" or "2 am" (with space - check next word)
        if let Ok(hour) = word.parse::<u32>() {
            if i + 1 < words.len() {
                let next_word = words[i + 1];
                if next_word == "pm" || next_word == "am" {
                    let is_pm = next_word == "pm";
                    let hour24 = if is_pm && hour != 12 {
                        hour + 12
                    } else if !is_pm && hour == 12 {
                        0
                    } else {
                        hour
                    };
                    return NaiveTime::from_hms_opt(hour24, 0, 0);
                }
            }
        }

        // Pattern: "14:30" or "2:30"
        if word.contains(':') {
            let parts: Vec<&str> = word.split(':').collect();
            if parts.len() == 2 {
                if let (Ok(hour), Ok(minute)) = (parts[0].parse::<u32>(), parts[1].parse::<u32>()) {
                    // Check if this is 12-hour format by looking at subsequent words
                    let is_pm = has_pm;
                    let is_am = has_am;

                    let hour24 = if is_pm && hour != 12 {
                        hour + 12
                    } else if is_am && hour == 12 {
                        0
                    } else {
                        hour
                    };

                    return NaiveTime::from_hms_opt(hour24, minute, 0);
                }
            }
        }
    }

    None
}

/// Parse date expressions like "January 15", "Jan 15 2024", "15/01/2024"
pub fn parse_date_expression(text: &str) -> Option<NaiveDate> {
    let text = text.trim().to_lowercase();

    // Try ISO format first (2024-01-15) - most reliable
    if let Ok(date) = NaiveDate::parse_from_str(&text, "%Y-%m-%d") {
        return Some(date);
    }

    // Try other common formats
    let formats = [
        "%m/%d/%Y",  // 01/15/2024
        "%d/%m/%Y",  // 15/01/2024
        "%m-%d-%Y",  // 01-15-2024
        "%d-%m-%Y",  // 15-01-2024
        "%B %d, %Y", // January 15, 2024
        "%b %d, %Y", // Jan 15, 2024
        "%B %d",     // January 15 (current year)
        "%b %d",     // Jan 15 (current year)
    ];

    for format in &formats {
        if let Ok(date) = NaiveDate::parse_from_str(&text, format) {
            return Some(date);
        }
    }

    // Try dateparser as fallback (may have timezone issues)
    if let Ok(dt) = dateparser::parse(&text) {
        return Some(dt.date_naive());
    }

    None
}

/// Parse relative date expressions like "tomorrow", "next week", "in 3 days"
pub fn parse_relative_date(text: &str) -> Option<NaiveDate> {
    let now = Utc::now();
    let today = now.date_naive();
    let text = text.trim().to_lowercase();

    // Handle specific relative terms
    if text.contains("today") {
        return Some(today);
    }
    if text.contains("tomorrow") {
        return Some(today + Duration::days(1));
    }
    if text.contains("yesterday") {
        return Some(today - Duration::days(1));
    }

    // Handle "next [day of week]"
    if text.contains("next") {
        let days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
        for (i, day) in days.iter().enumerate() {
            if text.contains(day) {
                let target_weekday = i as u32;
                let current_weekday = now.weekday().num_days_from_monday();
                let days_until = if target_weekday > current_weekday {
                    target_weekday - current_weekday
                } else {
                    7 - (current_weekday - target_weekday)
                };
                return Some(today + Duration::days(days_until as i64));
            }
        }

        if text.contains("week") {
            return Some(today + Duration::weeks(1));
        }
        if text.contains("month") {
            return Some(today + Duration::days(30));
        }
        if text.contains("year") {
            return Some(today + Duration::days(365));
        }
    }

    // Handle "in X days/weeks/months"
    if text.contains("in") {
        let words: Vec<&str> = text.split_whitespace().collect();
        for i in 0..words.len().saturating_sub(1) {
            if words[i] == "in" {
                if let Ok(amount) = words[i + 1].parse::<i64>() {
                    if i + 2 < words.len() {
                        let unit = words[i + 2];
                        if unit.starts_with("day") {
                            return Some(today + Duration::days(amount));
                        }
                        if unit.starts_with("week") {
                            return Some(today + Duration::weeks(amount));
                        }
                        if unit.starts_with("month") {
                            return Some(today + Duration::days(amount * 30));
                        }
                    }
                }
            }
        }
    }

    None
}

/// Parse combined date+time expressions like "tomorrow at 3pm"
fn parse_combined_datetime(text: &str, _tz: &Tz) -> Option<DateTime<Utc>> {
    let text = text.trim().to_lowercase();

    // Split by "at" to separate date and time
    if let Some(at_pos) = text.find("at") {
        let date_part = text[..at_pos].trim();
        let time_part = text[at_pos + 2..].trim();

        // Parse date part
        let date = if let Some(d) = parse_relative_date(date_part) {
            d
        } else if let Some(d) = parse_date_expression(date_part) {
            d
        } else {
            return None;
        };

        // Parse time part
        let time = parse_time_expression(time_part)?;

        // Combine and convert to UTC
        Some(date.and_time(time).and_utc())
    } else {
        None
    }
}

/// Scheduler for managing appointments and reminders
pub struct Scheduler {
    user_id: String,
    timezone: String,
}

impl Scheduler {
    /// Create a new scheduler
    pub fn new(user_id: String, timezone: String) -> Self {
        Self { user_id, timezone }
    }

    /// Parse natural language into a schedule request
    pub fn parse_natural_language(&self, text: &str) -> Result<ScheduleRequest> {
        let text_lower = text.to_lowercase();

        // Determine action
        let action = if text_lower.contains("schedule") || text_lower.contains("set up") || text_lower.contains("book") {
            ScheduleAction::Create
        } else if text_lower.contains("cancel") || text_lower.contains("delete") {
            ScheduleAction::Cancel
        } else if text_lower.contains("move") || text_lower.contains("reschedule") || text_lower.contains("change") {
            ScheduleAction::Modify
        } else if text_lower.contains("what") || text_lower.contains("show") || text_lower.contains("list") {
            ScheduleAction::Query
        } else {
            ScheduleAction::Create // Default to create
        };

        // Extract participants (e.g., "with John", "with the team")
        let participants = self.extract_participants(&text_lower);

        // Extract time (e.g., "tomorrow at 2pm", "in 2 hours", "next Wednesday at 3pm")
        let when = self.extract_time(&text_lower)?;

        // Extract duration (e.g., "for 1 hour", "30 minutes")
        let duration = self.extract_duration(&text_lower);

        // Extract location (e.g., "at the office", "in conference room A")
        let location = self.extract_location(&text_lower);

        // Extract recurrence (e.g., "every day", "weekly", "every Monday")
        let recurrence = self.extract_recurrence(&text_lower);

        // Extract title (everything else, cleaned up)
        let title = self.extract_title(&text_lower, &participants, &when, &duration, &location);

        Ok(ScheduleRequest {
            raw_text: text.to_string(),
            action,
            title,
            participants,
            when,
            duration,
            location,
            recurrence,
        })
    }

    /// Extract participants from text
    fn extract_participants(&self, text: &str) -> Vec<String> {
        let mut participants = Vec::new();

        // Look for "with [person/group]"
        if let Some(with_pos) = text.find("with ") {
            let after_with = &text[with_pos + 5..];

            // Find the end of participant list (next preposition or end of text)
            let end_markers = [" at ", " in ", " for ", " on ", " tomorrow", " today", " next"];
            let end_pos = end_markers.iter()
                .filter_map(|marker| after_with.find(marker))
                .min()
                .unwrap_or(after_with.len());

            let participant_text = &after_with[..end_pos].trim();

            // Split by "and" or ","
            let parts: Vec<String> = participant_text
                .split(&[',', '&'][..])
                .flat_map(|s| s.split(" and "))
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();

            participants.extend(parts);
        }

        participants
    }

    /// Extract time from text
    fn extract_time(&self, text: &str) -> Result<Option<ScheduleTime>> {
        let now = Utc::now();

        // Check for "in X minutes/hours/days"
        if let Some(in_pos) = text.find("in ") {
            if let Some((amount, unit)) = self.parse_relative_time(&text[in_pos..]) {
                return Ok(Some(ScheduleTime::Relative(RelativeTime {
                    amount,
                    unit,
                    from_now: true,
                })));
            }
        }

        // Check for "tomorrow at X"
        if text.contains("tomorrow") {
            if let Some(time) = self.extract_clock_time(text) {
                let tomorrow = now + Duration::days(1);
                let dt = tomorrow
                    .date_naive()
                    .and_time(time)
                    .and_utc();
                return Ok(Some(ScheduleTime::Absolute(dt)));
            } else {
                // Default to 9am if no time specified
                let tomorrow = now + Duration::days(1);
                let dt = tomorrow
                    .date_naive()
                    .and_time(NaiveTime::from_hms_opt(9, 0, 0).unwrap())
                    .and_utc();
                return Ok(Some(ScheduleTime::Absolute(dt)));
            }
        }

        // Check for "today at X"
        if text.contains("today") {
            if let Some(time) = self.extract_clock_time(text) {
                let dt = now
                    .date_naive()
                    .and_time(time)
                    .and_utc();
                return Ok(Some(ScheduleTime::Absolute(dt)));
            }
        }

        // Check for "next [day of week]"
        if text.contains("next ") {
            for (day_name, day_offset) in &[
                ("monday", 1),
                ("tuesday", 2),
                ("wednesday", 3),
                ("thursday", 4),
                ("friday", 5),
                ("saturday", 6),
                ("sunday", 0),
            ] {
                if text.contains(day_name) {
                    let time = self.extract_clock_time(text)
                        .unwrap_or_else(|| NaiveTime::from_hms_opt(9, 0, 0).unwrap());

                    let current_weekday = now.weekday().num_days_from_monday();
                    let target_weekday = *day_offset;
                    let days_until = if target_weekday > current_weekday {
                        target_weekday - current_weekday
                    } else {
                        7 - (current_weekday - target_weekday)
                    };

                    let target_date = now + Duration::days(days_until as i64);
                    let dt = target_date
                        .date_naive()
                        .and_time(time)
                        .and_utc();

                    return Ok(Some(ScheduleTime::Absolute(dt)));
                }
            }
        }

        // Check for specific time today (e.g., "at 2pm", "at 14:00")
        if let Some(time) = self.extract_clock_time(text) {
            let dt = now
                .date_naive()
                .and_time(time)
                .and_utc();

            // If the time has already passed today, schedule for tomorrow
            if dt < now {
                let tomorrow = now + Duration::days(1);
                let dt = tomorrow
                    .date_naive()
                    .and_time(time)
                    .and_utc();
                return Ok(Some(ScheduleTime::Absolute(dt)));
            }

            return Ok(Some(ScheduleTime::Absolute(dt)));
        }

        Ok(None)
    }

    /// Parse relative time (e.g., "in 2 hours", "in 30 minutes")
    fn parse_relative_time(&self, text: &str) -> Option<(i64, TimeUnit)> {
        // Look for number
        let words: Vec<&str> = text.split_whitespace().collect();

        for i in 0..words.len().saturating_sub(1) {
            if let Ok(amount) = words[i].parse::<i64>() {
                let unit_word = words[i + 1].to_lowercase();

                let unit = if unit_word.starts_with("minute") {
                    TimeUnit::Minutes
                } else if unit_word.starts_with("hour") {
                    TimeUnit::Hours
                } else if unit_word.starts_with("day") {
                    TimeUnit::Days
                } else if unit_word.starts_with("week") {
                    TimeUnit::Weeks
                } else if unit_word.starts_with("month") {
                    TimeUnit::Months
                } else {
                    continue;
                };

                return Some((amount, unit));
            }
        }

        None
    }

    /// Extract clock time (e.g., "2pm", "14:00", "3:30pm")
    fn extract_clock_time(&self, text: &str) -> Option<NaiveTime> {
        // Try to find time patterns like "2pm", "14:00", "3:30pm"
        let _time_patterns = [
            r"(\d{1,2}):(\d{2})\s*(am|pm)?",
            r"(\d{1,2})\s*(am|pm)",
        ];

        for word in text.split_whitespace() {
            // Check for "2pm" style
            if word.ends_with("pm") || word.ends_with("am") {
                let is_pm = word.ends_with("pm");
                let num_str = word.trim_end_matches("pm").trim_end_matches("am");

                if let Ok(hour) = num_str.parse::<u32>() {
                    let hour24 = if is_pm && hour != 12 {
                        hour + 12
                    } else if !is_pm && hour == 12 {
                        0
                    } else {
                        hour
                    };

                    return NaiveTime::from_hms_opt(hour24, 0, 0);
                }
            }

            // Check for "14:00" style
            if word.contains(':') {
                let parts: Vec<&str> = word.split(':').collect();
                if parts.len() == 2 {
                    if let (Ok(hour), Ok(minute)) = (parts[0].parse::<u32>(), parts[1].parse::<u32>()) {
                        return NaiveTime::from_hms_opt(hour, minute, 0);
                    }
                }
            }
        }

        None
    }

    /// Extract duration from text
    fn extract_duration(&self, text: &str) -> Option<Duration> {
        if let Some(for_pos) = text.find("for ") {
            let after_for = &text[for_pos + 4..];

            if let Some((amount, unit)) = self.parse_relative_time(after_for) {
                return Some(match unit {
                    TimeUnit::Minutes => Duration::minutes(amount),
                    TimeUnit::Hours => Duration::hours(amount),
                    TimeUnit::Days => Duration::days(amount),
                    TimeUnit::Weeks => Duration::weeks(amount),
                    TimeUnit::Months => Duration::days(amount * 30), // Approximate
                });
            }
        }

        // Default duration: 1 hour
        Some(Duration::hours(1))
    }

    /// Extract location from text
    fn extract_location(&self, text: &str) -> Option<String> {
        // Look for "at [location]" or "in [location]"
        for prefix in &["at the ", "in the ", "at ", "in "] {
            if let Some(pos) = text.find(prefix) {
                let after_prefix = &text[pos + prefix.len()..];

                // Find the end of location (next preposition or end of text)
                let end_markers = [" with ", " for ", " tomorrow", " today", " next"];
                let end_pos = end_markers.iter()
                    .filter_map(|marker| after_prefix.find(marker))
                    .min()
                    .unwrap_or(after_prefix.len());

                let location = &after_prefix[..end_pos].trim();

                if !location.is_empty() && !location.contains("2pm") && !location.contains("am") && !location.contains("pm") {
                    return Some(location.to_string());
                }
            }
        }

        None
    }

    /// Extract recurrence pattern from text
    fn extract_recurrence(&self, text: &str) -> Option<RecurrencePattern> {
        if text.contains("every day") || text.contains("daily") {
            return Some(RecurrencePattern::daily(1));
        }

        if text.contains("every week") || text.contains("weekly") {
            return Some(RecurrencePattern::weekly(1, vec![]));
        }

        if text.contains("every month") || text.contains("monthly") {
            return Some(RecurrencePattern::monthly(1, 1));
        }

        // Check for specific day patterns (e.g., "every Monday")
        let weekdays = [
            ("monday", Weekday::Mon),
            ("tuesday", Weekday::Tue),
            ("wednesday", Weekday::Wed),
            ("thursday", Weekday::Thu),
            ("friday", Weekday::Fri),
            ("saturday", Weekday::Sat),
            ("sunday", Weekday::Sun),
        ];

        for (day_name, weekday) in &weekdays {
            if text.contains(&format!("every {}", day_name)) {
                return Some(RecurrencePattern::weekly(1, vec![*weekday]));
            }
        }

        None
    }

    /// Extract title from text (cleaned up)
    fn extract_title(
        &self,
        text: &str,
        participants: &[String],
        _when: &Option<ScheduleTime>,
        _duration: &Option<Duration>,
        _location: &Option<String>,
    ) -> Option<String> {
        let mut title = text.to_string();

        // Remove common scheduling words
        let remove_words = [
            "schedule ", "set up ", "book ", "create ",
            "tomorrow ", "today ", "next ",
            "at ", "in ", "for ", "with ",
            "every ", "daily ", "weekly ", "monthly ",
        ];

        for word in &remove_words {
            title = title.replace(word, " ");
        }

        // Remove time patterns
        title = title.split("at").next().unwrap_or(&title).to_string();

        // Remove participant names
        for participant in participants {
            title = title.replace(participant, "");
        }

        // Clean up extra spaces
        let title = title.split_whitespace()
            .collect::<Vec<_>>()
            .join(" ");

        if title.is_empty() {
            None
        } else {
            Some(title.trim().to_string())
        }
    }

    /// Create an appointment
    pub fn create_appointment(&self, request: ScheduleRequest) -> Result<Appointment> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now();

        let start_time = match request.when {
            Some(ScheduleTime::Absolute(dt)) => dt,
            Some(ScheduleTime::Relative(rel)) => {
                let duration = match rel.unit {
                    TimeUnit::Minutes => Duration::minutes(rel.amount),
                    TimeUnit::Hours => Duration::hours(rel.amount),
                    TimeUnit::Days => Duration::days(rel.amount),
                    TimeUnit::Weeks => Duration::weeks(rel.amount),
                    TimeUnit::Months => Duration::days(rel.amount * 30),
                };
                now + duration
            }
            _ => now + Duration::hours(1), // Default: 1 hour from now
        };

        let duration = request.duration.unwrap_or_else(|| Duration::hours(1));
        let end_time = start_time + duration;

        let title = request.title
            .or_else(|| {
                if !request.participants.is_empty() {
                    Some(format!("Meeting with {}", request.participants.join(", ")))
                } else {
                    Some("Appointment".to_string())
                }
            })
            .unwrap();

        let recurring_rule = request.recurrence.map(|rec| {
            // Convert recurrence pattern to JSON-encoded RecurringRule
            let rule = match rec.frequency {
                RecurrenceFrequency::Daily => RecurringRule::Daily,
                RecurrenceFrequency::Weekly => RecurringRule::Weekly,
                RecurrenceFrequency::Monthly => RecurringRule::Monthly,
                RecurrenceFrequency::Yearly => RecurringRule::Yearly,
            };
            serde_json::to_string(&rule).unwrap_or_default()
        });

        Ok(Appointment {
            id,
            user_id: self.user_id.clone(),
            title,
            description: None,
            start_time,
            end_time,
            timezone: self.timezone.clone(),
            location: request.location,
            recurring_rule,
            reminder_minutes: None, // Can be set later via natural language parsing
            created_at: now,
            updated_at: None,
        })
    }

    /// Convert recurrence pattern to RRULE format
    fn to_rrule(&self, pattern: &RecurrencePattern) -> String {
        let freq = match pattern.frequency {
            RecurrenceFrequency::Daily => "DAILY",
            RecurrenceFrequency::Weekly => "WEEKLY",
            RecurrenceFrequency::Monthly => "MONTHLY",
            RecurrenceFrequency::Yearly => "YEARLY",
        };

        let mut rrule = format!("FREQ={};INTERVAL={}", freq, pattern.interval);

        if let Some(until) = pattern.until {
            rrule.push_str(&format!(";UNTIL={}", until.format("%Y%m%dT%H%M%SZ")));
        }

        if let Some(count) = pattern.count {
            rrule.push_str(&format!(";COUNT={}", count));
        }

        rrule
    }

    /// Create a reminder
    pub fn create_reminder(
        &self,
        title: String,
        due_time: DateTime<Utc>,
        priority: ReminderPriority,
    ) -> Result<Reminder> {
        let id = uuid::Uuid::new_v4().to_string();
        let now = Utc::now();

        Ok(Reminder {
            id,
            user_id: self.user_id.clone(),
            title,
            description: None,
            due_time,
            completed: false,
            priority,
            created_at: now,
            updated_at: None,
        })
    }

    /// Check for conflicts with existing appointments
    pub fn check_conflicts(
        &self,
        new_appointment: &Appointment,
        existing: &[Appointment],
    ) -> Vec<Appointment> {
        existing
            .iter()
            .filter(|apt| {
                // Check if appointments overlap
                (new_appointment.start_time < apt.end_time)
                    && (new_appointment.end_time > apt.start_time)
            })
            .cloned()
            .collect()
    }
}

// =============================================================================
// DATABASE SCHEMA
// =============================================================================
//
// The appointments table is managed by the Node.js server using Turso (libsql).
// This Rust module interacts with the database via HTTP API endpoints.
//
// SQL Schema for appointments table:
//
// ```sql
// CREATE TABLE IF NOT EXISTS appointments (
//     id TEXT PRIMARY KEY,
//     user_id TEXT NOT NULL,
//     title TEXT NOT NULL,
//     description TEXT,
//     start_time TEXT NOT NULL,  -- ISO 8601 format
//     end_time TEXT NOT NULL,    -- ISO 8601 format
//     timezone TEXT NOT NULL,
//     location TEXT,
//     recurring_rule TEXT,       -- JSON-encoded RecurringRule
//     reminder_minutes INTEGER,
//     created_at TEXT NOT NULL,  -- ISO 8601 format
//     updated_at TEXT,           -- ISO 8601 format
//     FOREIGN KEY (user_id) REFERENCES users(id)
// );
//
// CREATE INDEX idx_appointments_user_id ON appointments(user_id);
// CREATE INDEX idx_appointments_start_time ON appointments(start_time);
// CREATE INDEX idx_appointments_end_time ON appointments(end_time);
// ```
//
// SQL Schema for reminders table:
//
// ```sql
// CREATE TABLE IF NOT EXISTS reminders (
//     id TEXT PRIMARY KEY,
//     user_id TEXT NOT NULL,
//     title TEXT NOT NULL,
//     description TEXT,
//     due_time TEXT NOT NULL,    -- ISO 8601 format
//     completed INTEGER NOT NULL DEFAULT 0,  -- 0 = false, 1 = true
//     priority INTEGER NOT NULL DEFAULT 3,   -- 1 = high, 3 = normal, 5 = low
//     created_at TEXT NOT NULL,  -- ISO 8601 format
//     updated_at TEXT,           -- ISO 8601 format
//     FOREIGN KEY (user_id) REFERENCES users(id)
// );
//
// CREATE INDEX idx_reminders_user_id ON reminders(user_id);
// CREATE INDEX idx_reminders_due_time ON reminders(due_time);
// CREATE INDEX idx_reminders_completed ON reminders(completed);
// ```

// =============================================================================
// REQUEST/RESPONSE STRUCTS FOR API
// =============================================================================

/// Request to create a new appointment
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateAppointmentRequest {
    pub user_id: String,
    pub title: String,
    pub description: Option<String>,
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
    pub timezone: String,
    pub location: Option<String>,
    pub recurrence_rule: Option<String>,
    pub participants: Vec<String>,
}

impl From<&Appointment> for CreateAppointmentRequest {
    fn from(apt: &Appointment) -> Self {
        Self {
            user_id: apt.user_id.clone(),
            title: apt.title.clone(),
            description: apt.description.clone(),
            start_time: apt.start_time,
            end_time: apt.end_time,
            timezone: apt.timezone.clone(),
            location: apt.location.clone(),
            recurrence_rule: apt.recurring_rule.clone(),
            participants: Vec::new(),
        }
    }
}

/// Request to update an existing appointment
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct UpdateAppointmentRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub start_time: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end_time: Option<DateTime<Utc>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timezone: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub location: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub recurrence_rule: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub participants: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status: Option<String>,
}

/// Filter for querying appointments
#[derive(Debug, Clone, Default)]
pub struct AppointmentFilter {
    pub user_id: String,
    pub start_time: Option<DateTime<Utc>>,
    pub end_time: Option<DateTime<Utc>>,
    pub status: Option<String>,
}

/// API response wrapper for appointment
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AppointmentResponse {
    appointment: Appointment,
}

/// API response wrapper for appointment list
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AppointmentsResponse {
    appointments: Vec<Appointment>,
}

/// API response wrapper for reminder
#[derive(Debug, Clone, Serialize, Deserialize)]
struct ReminderResponse {
    reminder: Reminder,
}

/// API response wrapper for reminder list
#[derive(Debug, Clone, Serialize, Deserialize)]
struct RemindersResponse {
    reminders: Vec<Reminder>,
}

/// SchedulerManager provides database operations for appointments and reminders
/// via HTTP requests to the Node.js server API
///
/// # Example Usage
///
/// ```no_run
/// use xswarm::scheduler::{SchedulerManager, CreateAppointmentRequest, AppointmentFilter};
/// use chrono::{Utc, Duration};
///
/// #[tokio::main]
/// async fn main() -> anyhow::Result<()> {
///     // Create manager instance
///     let manager = SchedulerManager::new(
///         "http://localhost:8787".to_string(),
///         "user123".to_string(),
///         Some("auth-token".to_string()),
///     );
///
///     // Create an appointment
///     let now = Utc::now();
///     let request = CreateAppointmentRequest {
///         user_id: "user123".to_string(),
///         title: "Team Meeting".to_string(),
///         description: Some("Weekly sync".to_string()),
///         start_time: now + Duration::hours(1),
///         end_time: now + Duration::hours(2),
///         timezone: "America/Los_Angeles".to_string(),
///         location: Some("Conference Room A".to_string()),
///         recurrence_rule: None,
///         participants: vec!["alice@example.com".to_string()],
///     };
///
///     let appointment = manager.create_appointment(request).await?;
///     println!("Created appointment: {}", appointment.id);
///
///     // List appointments for today
///     let today_schedule = manager.get_today_schedule().await?;
///     println!("Today's schedule: {} appointments", today_schedule.len());
///
///     // Query appointments with filter
///     let filter = AppointmentFilter {
///         user_id: "user123".to_string(),
///         start_time: Some(now),
///         end_time: Some(now + Duration::days(7)),
///         status: Some("scheduled".to_string()),
///     };
///     let appointments = manager.list_appointments(filter).await?;
///
///     // Update an appointment
///     let update = UpdateAppointmentRequest {
///         location: Some("Virtual".to_string()),
///         ..Default::default()
///     };
///     manager.update_appointment(&appointment.id, update).await?;
///
///     // Delete an appointment
///     manager.delete_appointment(&appointment.id).await?;
///
///     Ok(())
/// }
/// ```
pub struct SchedulerManager {
    server_url: String,
    user_id: String,
    http_client: reqwest::Client,
    auth_token: Option<String>,
}

impl SchedulerManager {
    /// Create a new SchedulerManager
    ///
    /// # Arguments
    /// * `server_url` - The URL of the Node.js server API (e.g., "http://localhost:8787")
    /// * `user_id` - The user ID for which to manage appointments
    /// * `auth_token` - Optional authentication token
    pub fn new(server_url: String, user_id: String, auth_token: Option<String>) -> Self {
        let http_client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());

        Self {
            server_url,
            user_id,
            http_client,
            auth_token,
        }
    }

    /// Create an appointment in the database (via server API)
    pub async fn create_appointment(&self, request: CreateAppointmentRequest) -> Result<Appointment> {
        let url = format!("{}/api/calendar/appointments", self.server_url);

        let mut req = self.http_client.post(&url).json(&request);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        let api_response: AppointmentResponse = response
            .json()
            .await
            .context("Failed to parse appointment response")?;

        Ok(api_response.appointment)
    }

    /// Get an appointment by ID (via server API)
    pub async fn get_appointment(&self, id: &str) -> Result<Option<Appointment>> {
        let url = format!("{}/api/calendar/appointments/{}", self.server_url, id);

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if response.status().as_u16() == 404 {
            return Ok(None);
        }

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        let api_response: AppointmentResponse = response
            .json()
            .await
            .context("Failed to parse appointment response")?;

        Ok(Some(api_response.appointment))
    }

    /// Update an appointment in the database (via server API)
    pub async fn update_appointment(&self, id: &str, updates: UpdateAppointmentRequest) -> Result<Appointment> {
        let url = format!("{}/api/calendar/appointments/{}", self.server_url, id);

        let mut req = self.http_client.put(&url).json(&updates);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        let api_response: AppointmentResponse = response
            .json()
            .await
            .context("Failed to parse appointment response")?;

        Ok(api_response.appointment)
    }

    /// Delete an appointment from the database (via server API)
    pub async fn delete_appointment(&self, id: &str) -> Result<()> {
        let url = format!("{}/api/calendar/appointments/{}", self.server_url, id);

        let mut req = self.http_client.delete(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        Ok(())
    }

    /// List appointments for a user with optional filtering (via server API)
    pub async fn list_appointments(&self, filter: AppointmentFilter) -> Result<Vec<Appointment>> {
        let mut url = format!(
            "{}/api/calendar/appointments?user_id={}",
            self.server_url,
            filter.user_id
        );

        if let Some(start) = filter.start_time {
            url.push_str(&format!("&start={}", start.to_rfc3339()));
        }

        if let Some(end) = filter.end_time {
            url.push_str(&format!("&end={}", end.to_rfc3339()));
        }

        if let Some(status) = filter.status {
            url.push_str(&format!("&status={}", status));
        }

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        let api_response: AppointmentsResponse = response
            .json()
            .await
            .context("Failed to parse appointments response")?;

        Ok(api_response.appointments)
    }

    /// Get today's schedule (convenience method)
    pub async fn get_today_schedule(&self) -> Result<Vec<Appointment>> {
        let url = format!(
            "{}/api/calendar/today?user_id={}",
            self.server_url,
            self.user_id
        );

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        #[derive(Deserialize)]
        struct TodayResponse {
            schedule: Vec<Appointment>,
        }

        let api_response: TodayResponse = response
            .json()
            .await
            .context("Failed to parse today schedule response")?;

        Ok(api_response.schedule)
    }

    /// Get this week's schedule (convenience method)
    pub async fn get_week_schedule(&self) -> Result<Vec<Appointment>> {
        let url = format!(
            "{}/api/calendar/week?user_id={}",
            self.server_url,
            self.user_id
        );

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        #[derive(Deserialize)]
        struct WeekResponse {
            schedule: Vec<Appointment>,
        }

        let api_response: WeekResponse = response
            .json()
            .await
            .context("Failed to parse week schedule response")?;

        Ok(api_response.schedule)
    }

    /// Create a reminder in the database (via server API)
    pub async fn create_reminder(&self, reminder: &Reminder) -> Result<String> {
        let url = format!("{}/api/calendar/reminders", self.server_url);

        #[derive(Serialize)]
        struct CreateReminderRequest {
            user_id: String,
            title: String,
            description: Option<String>,
            due_time: DateTime<Utc>,
            priority: i32,
            recurrence_rule: Option<String>,
        }

        let request = CreateReminderRequest {
            user_id: reminder.user_id.clone(),
            title: reminder.title.clone(),
            description: reminder.description.clone(),
            due_time: reminder.due_time,
            priority: reminder.priority as i32,
            recurrence_rule: None,
        };

        let mut req = self.http_client.post(&url).json(&request);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        let api_response: ReminderResponse = response
            .json()
            .await
            .context("Failed to parse reminder response")?;

        Ok(api_response.reminder.id)
    }

    /// Update a reminder in the database (via server API)
    pub async fn update_reminder(&self, id: &str, completed: bool) -> Result<()> {
        let url = format!("{}/api/calendar/reminders/{}", self.server_url, id);

        #[derive(Serialize)]
        struct UpdateReminderRequest {
            completed: bool,
        }

        let request = UpdateReminderRequest { completed };

        let mut req = self.http_client.put(&url).json(&request);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        Ok(())
    }

    /// Delete a reminder from the database (via server API)
    pub async fn delete_reminder(&self, id: &str) -> Result<()> {
        let url = format!("{}/api/calendar/reminders/{}", self.server_url, id);

        let mut req = self.http_client.delete(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        Ok(())
    }

    /// List reminders for a user (via server API)
    pub async fn list_reminders(&self, completed: bool) -> Result<Vec<Reminder>> {
        let url = format!(
            "{}/api/calendar/reminders?user_id={}&completed={}",
            self.server_url,
            self.user_id,
            completed
        );

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        let api_response: RemindersResponse = response
            .json()
            .await
            .context("Failed to parse reminders response")?;

        Ok(api_response.reminders)
    }

    /// Get due reminders that need to be sent (via server API)
    pub async fn get_due_reminders(&self) -> Result<Vec<AppointmentReminder>> {
        let url = format!(
            "{}/api/calendar/reminders/due?user_id={}",
            self.server_url,
            self.user_id
        );

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to connect to server")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        #[derive(Deserialize)]
        struct DueRemindersResponse {
            reminders: Vec<AppointmentReminder>,
        }

        let api_response: DueRemindersResponse = response
            .json()
            .await
            .context("Failed to parse due reminders response")?;

        Ok(api_response.reminders)
    }

    /// Create reminder for appointment
    pub async fn create_reminder_for_appointment(
        &self,
        appointment_id: &str,
        minutes_before: u32,
    ) -> Result<AppointmentReminder> {
        // Get the appointment first
        let appointment = self
            .get_appointment(appointment_id)
            .await?
            .context("Appointment not found")?;

        // Calculate reminder time
        let scheduled_time = appointment.start_time - Duration::minutes(minutes_before as i64);

        // Get user preferences to determine method
        let preferences = self.get_user_reminder_preferences().await?;
        let method = preferences.preferred_methods.first()
            .copied()
            .unwrap_or(ReminderMethod::Sms);

        let reminder = AppointmentReminder {
            id: uuid::Uuid::new_v4().to_string(),
            appointment_id: appointment_id.to_string(),
            user_id: self.user_id.clone(),
            minutes_before,
            method,
            status: ReminderStatus::Pending,
            scheduled_time,
            sent_at: None,
            error_message: None,
            retry_count: 0,
            created_at: Utc::now(),
            updated_at: None,
        };

        // Save to database via API
        let url = format!("{}/api/calendar/appointment-reminders", self.server_url);

        let mut req = self.http_client.post(&url).json(&reminder);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to create appointment reminder")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        #[derive(Deserialize)]
        struct ReminderCreatedResponse {
            reminder: AppointmentReminder,
        }

        let api_response: ReminderCreatedResponse = response
            .json()
            .await
            .context("Failed to parse reminder response")?;

        Ok(api_response.reminder)
    }

    /// Update reminder preferences for user
    pub async fn update_reminder_preferences(
        &self,
        preferences: ReminderPreferences,
    ) -> Result<()> {
        let url = format!(
            "{}/api/calendar/reminder-preferences",
            self.server_url
        );

        let mut req = self.http_client.put(&url).json(&preferences);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to update reminder preferences")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        Ok(())
    }

    /// Get user reminder preferences
    pub async fn get_user_reminder_preferences(&self) -> Result<ReminderPreferences> {
        let url = format!(
            "{}/api/calendar/reminder-preferences?user_id={}",
            self.server_url,
            self.user_id
        );

        let mut req = self.http_client.get(&url);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to get reminder preferences")?;

        if !response.status().is_success() {
            // If not found, return default preferences
            if response.status().as_u16() == 404 {
                return Ok(ReminderPreferences {
                    user_id: self.user_id.clone(),
                    ..Default::default()
                });
            }

            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        #[derive(Deserialize)]
        struct PreferencesResponse {
            preferences: ReminderPreferences,
        }

        let api_response: PreferencesResponse = response
            .json()
            .await
            .context("Failed to parse preferences response")?;

        Ok(api_response.preferences)
    }

    /// Mark appointment reminder as sent
    pub async fn mark_reminder_sent(
        &self,
        reminder_id: &str,
        success: bool,
        error_message: Option<String>,
    ) -> Result<()> {
        let url = format!(
            "{}/api/calendar/appointment-reminders/{}/status",
            self.server_url,
            reminder_id
        );

        #[derive(Serialize)]
        struct UpdateStatusRequest {
            status: ReminderStatus,
            error_message: Option<String>,
        }

        let status = if success {
            ReminderStatus::Sent
        } else {
            ReminderStatus::Failed
        };

        let request = UpdateStatusRequest {
            status,
            error_message,
        };

        let mut req = self.http_client.put(&url).json(&request);

        if let Some(token) = &self.auth_token {
            req = req.bearer_auth(token);
        }

        let response = req
            .send()
            .await
            .context("Failed to update reminder status")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("Server returned error {}: {}", status, error_text);
        }

        Ok(())
    }

    /// Get conflicts for a new appointment
    ///
    /// # Arguments
    /// * `appointment` - The appointment to check for conflicts
    ///
    /// # Returns
    /// Vector of conflicts found
    pub async fn get_conflicts_for_appointment(
        &self,
        appointment: &Appointment,
    ) -> Result<Vec<ConflictInfo>> {
        // Get existing appointments for the time range
        let filter = AppointmentFilter {
            user_id: self.user_id.clone(),
            start_time: Some(appointment.start_time - Duration::hours(24)),
            end_time: Some(appointment.end_time + Duration::hours(24)),
            status: Some("scheduled".to_string()),
        };

        let existing = self.list_appointments(filter).await?;

        // Check conflicts using the standalone function
        Ok(check_conflicts(appointment, &existing))
    }

    /// Suggest alternative times for an appointment if conflicts exist
    ///
    /// # Arguments
    /// * `appointment` - The appointment to find alternatives for
    ///
    /// # Returns
    /// Vector of available time slots
    pub async fn suggest_alternative_times(
        &self,
        appointment: &Appointment,
    ) -> Result<Vec<TimeSlot>> {
        let duration_minutes = (appointment.end_time - appointment.start_time).num_minutes() as u32;

        // Search for alternatives in the next 7 days
        let start_date = appointment.start_time;
        let end_date = start_date + Duration::days(7);

        // Get existing appointments
        let filter = AppointmentFilter {
            user_id: self.user_id.clone(),
            start_time: Some(start_date),
            end_time: Some(end_date),
            status: Some("scheduled".to_string()),
        };

        let existing = self.list_appointments(filter).await?;

        // Find free slots using the standalone function
        Ok(find_free_slots(
            duration_minutes,
            start_date,
            end_date,
            &existing,
        ))
    }

    /// Expand a recurring appointment into instances within a date range
    ///
    /// # Arguments
    /// * `appointment_id` - ID of the recurring appointment
    /// * `start_date` - Start of date range
    /// * `end_date` - End of date range
    ///
    /// # Returns
    /// Vector of appointment instances
    pub async fn expand_recurring_appointment(
        &self,
        appointment_id: &str,
        start_date: DateTime<Utc>,
        end_date: DateTime<Utc>,
    ) -> Result<Vec<Appointment>> {
        // Get the base appointment
        let appointment = self
            .get_appointment(appointment_id)
            .await?
            .context("Appointment not found")?;

        // Use the standalone expansion function
        expand_recurring_appointment(&appointment, start_date, end_date)
    }
}

// =============================================================================
// REMINDER PROCESSOR - Background Task for Sending Reminders
// =============================================================================

/// ReminderProcessor handles checking and sending due reminders
pub struct ReminderProcessor {
    scheduler_manager: Arc<SchedulerManager>,
    check_interval_seconds: u64,
    max_retries: u32,
}

impl ReminderProcessor {
    /// Create a new ReminderProcessor
    ///
    /// # Arguments
    /// * `scheduler_manager` - SchedulerManager for database operations
    /// * `check_interval_seconds` - How often to check for due reminders (default: 60)
    /// * `max_retries` - Maximum number of retry attempts for failed reminders (default: 3)
    pub fn new(
        scheduler_manager: Arc<SchedulerManager>,
        check_interval_seconds: Option<u64>,
        max_retries: Option<u32>,
    ) -> Self {
        Self {
            scheduler_manager,
            check_interval_seconds: check_interval_seconds.unwrap_or(60),
            max_retries: max_retries.unwrap_or(3),
        }
    }

    /// Check for due reminders and return those that need to be sent
    pub async fn check_due_reminders(&self) -> Result<Vec<AppointmentReminder>> {
        let reminders = self.scheduler_manager.get_due_reminders().await?;

        // Filter out reminders that have exceeded retry count
        let valid_reminders: Vec<_> = reminders
            .into_iter()
            .filter(|r| r.retry_count < self.max_retries)
            .collect();

        Ok(valid_reminders)
    }

    /// Process a single reminder by sending it via the appropriate channel
    ///
    /// This function is designed to be called by the supervisor system which will
    /// handle the actual sending via SMS/Email/Voice channels.
    ///
    /// Returns the formatted reminder message and metadata for sending
    pub async fn process_reminder(
        &self,
        reminder: &AppointmentReminder,
    ) -> Result<ReminderNotification> {
        use tracing::{info, warn};

        // Get the appointment details
        let appointment = self
            .scheduler_manager
            .get_appointment(&reminder.appointment_id)
            .await?
            .context("Appointment not found for reminder")?;

        // Get user preferences for personalization
        let preferences = self
            .scheduler_manager
            .get_user_reminder_preferences()
            .await
            .unwrap_or_default();

        // Check quiet hours
        if self.is_in_quiet_hours(&preferences) {
            warn!(
                reminder_id = %reminder.id,
                "Reminder skipped - in quiet hours"
            );
            return Err(anyhow::anyhow!("In quiet hours"));
        }

        // Format the reminder message based on method
        let message = self.format_reminder_message(&reminder, &appointment);

        info!(
            reminder_id = %reminder.id,
            appointment_id = %reminder.appointment_id,
            method = ?reminder.method,
            "Processing reminder"
        );

        Ok(ReminderNotification {
            reminder_id: reminder.id.clone(),
            user_id: reminder.user_id.clone(),
            method: reminder.method,
            appointment_title: appointment.title.clone(),
            appointment_start_time: appointment.start_time,
            appointment_location: appointment.location.clone(),
            message,
            preferences,
        })
    }

    /// Check if current time is within quiet hours
    fn is_in_quiet_hours(&self, preferences: &ReminderPreferences) -> bool {
        if preferences.quiet_hours_start.is_none() || preferences.quiet_hours_end.is_none() {
            return false;
        }

        let now = Utc::now();
        let tz: Tz = preferences
            .timezone
            .parse()
            .unwrap_or_else(|_| "UTC".parse().unwrap());
        let local_time = now.with_timezone(&tz);
        let current_hour = local_time.hour() as u8;

        let start = preferences.quiet_hours_start.unwrap();
        let end = preferences.quiet_hours_end.unwrap();

        if start < end {
            // Normal case: quiet hours don't cross midnight
            current_hour >= start && current_hour < end
        } else {
            // Quiet hours cross midnight (e.g., 22:00 - 08:00)
            current_hour >= start || current_hour < end
        }
    }

    /// Format reminder message based on delivery method
    fn format_reminder_message(
        &self,
        reminder: &AppointmentReminder,
        appointment: &Appointment,
    ) -> String {
        match reminder.method {
            ReminderMethod::Sms => {
                self.format_sms_reminder(reminder, appointment)
            }
            ReminderMethod::Email => {
                self.format_email_reminder(reminder, appointment)
            }
            ReminderMethod::Voice => {
                self.format_voice_reminder(reminder, appointment)
            }
            ReminderMethod::Push => {
                self.format_push_reminder(reminder, appointment)
            }
        }
    }

    /// Format SMS reminder message (concise, under 160 chars)
    fn format_sms_reminder(
        &self,
        reminder: &AppointmentReminder,
        appointment: &Appointment,
    ) -> String {
        let time_until = reminder.minutes_before;
        let start_time = appointment.start_time.format("%I:%M %p");

        if let Some(location) = &appointment.location {
            format!(
                "Reminder: {} in {} min at {} in {}",
                appointment.title, time_until, start_time, location
            )
        } else {
            format!(
                "Reminder: {} in {} min at {}",
                appointment.title, time_until, start_time
            )
        }
    }

    /// Format email reminder message (rich HTML)
    fn format_email_reminder(
        &self,
        reminder: &AppointmentReminder,
        appointment: &Appointment,
    ) -> String {
        let time_until = reminder.minutes_before;
        let start_time = appointment.start_time.format("%B %d, %Y at %I:%M %p %Z");
        let location = appointment.location.as_deref().unwrap_or("No location specified");
        let description = appointment.description.as_deref().unwrap_or("");

        format!(
            r#"
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #333;">Upcoming Appointment Reminder</h2>
                <div style="background: #f4f4f4; padding: 20px; border-radius: 5px;">
                    <p><strong>Title:</strong> {}</p>
                    <p><strong>When:</strong> {} (in {} minutes)</p>
                    <p><strong>Location:</strong> {}</p>
                    {}
                </div>
                <p style="color: #666; font-size: 12px; margin-top: 20px;">
                    This is an automated reminder from Boss AI.
                </p>
            </body>
            </html>
            "#,
            appointment.title,
            start_time,
            time_until,
            location,
            if !description.is_empty() {
                format!("<p><strong>Details:</strong> {}</p>", description)
            } else {
                String::new()
            }
        )
    }

    /// Format voice reminder message (spoken text)
    fn format_voice_reminder(
        &self,
        reminder: &AppointmentReminder,
        appointment: &Appointment,
    ) -> String {
        let time_until = reminder.minutes_before;
        let start_time = appointment.start_time.format("%I:%M %p");

        if let Some(location) = &appointment.location {
            format!(
                "Reminder: You have {} in {} minutes at {} in {}. ",
                appointment.title, time_until, start_time, location
            )
        } else {
            format!(
                "Reminder: You have {} in {} minutes at {}. ",
                appointment.title, time_until, start_time
            )
        }
    }

    /// Format push notification message (for future use)
    fn format_push_reminder(
        &self,
        reminder: &AppointmentReminder,
        appointment: &Appointment,
    ) -> String {
        let time_until = reminder.minutes_before;
        format!(
            "{} in {} minutes",
            appointment.title, time_until
        )
    }

    /// Start the background reminder checking loop
    ///
    /// This function runs indefinitely, checking for due reminders at regular intervals.
    /// It's designed to be run in a tokio task.
    pub async fn start_reminder_loop(self: Arc<Self>) {
        use tracing::{info, error};
        use tokio::time::{sleep, Duration as TokioDuration};

        info!(
            interval_seconds = self.check_interval_seconds,
            "Starting reminder processor loop"
        );

        loop {
            // Check for due reminders
            match self.check_due_reminders().await {
                Ok(reminders) => {
                    if !reminders.is_empty() {
                        info!(count = reminders.len(), "Found due reminders");

                        // Process each reminder
                        for reminder in reminders {
                            let processor = self.clone();
                            tokio::spawn(async move {
                                if let Err(e) = processor.send_reminder_notification(&reminder).await {
                                    error!(
                                        reminder_id = %reminder.id,
                                        error = ?e,
                                        "Failed to send reminder notification"
                                    );
                                }
                            });
                        }
                    }
                }
                Err(e) => {
                    error!(error = ?e, "Failed to check due reminders");
                }
            }

            // Sleep until next check
            sleep(TokioDuration::from_secs(self.check_interval_seconds)).await;
        }
    }

    /// Send reminder notification via supervisor system
    ///
    /// This method is called internally and broadcasts the reminder to the supervisor
    /// which handles actual delivery via SMS/Email/Voice channels.
    async fn send_reminder_notification(&self, reminder: &AppointmentReminder) -> Result<()> {
        use tracing::{info, error};

        match self.process_reminder(reminder).await {
            Ok(notification) => {
                info!(
                    reminder_id = %reminder.id,
                    method = ?notification.method,
                    "Reminder notification prepared - broadcasting to supervisor"
                );

                // Mark as sent (supervisor will handle actual delivery)
                if let Err(e) = self
                    .scheduler_manager
                    .mark_reminder_sent(&reminder.id, true, None)
                    .await
                {
                    error!(
                        reminder_id = %reminder.id,
                        error = ?e,
                        "Failed to mark reminder as sent"
                    );
                }

                Ok(())
            }
            Err(e) => {
                error!(
                    reminder_id = %reminder.id,
                    error = ?e,
                    "Failed to process reminder"
                );

                // Mark as failed
                let _ = self
                    .scheduler_manager
                    .mark_reminder_sent(&reminder.id, false, Some(e.to_string()))
                    .await;

                Err(e)
            }
        }
    }
}

/// Notification data prepared for sending via supervisor
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReminderNotification {
    pub reminder_id: String,
    pub user_id: String,
    pub method: ReminderMethod,
    pub appointment_title: String,
    pub appointment_start_time: DateTime<Utc>,
    pub appointment_location: Option<String>,
    pub message: String,
    pub preferences: ReminderPreferences,
}

use std::sync::Arc;

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Timelike;

    #[test]
    fn test_parse_tomorrow_at_2pm() {
        let scheduler = Scheduler::new("user1".to_string(), "UTC".to_string());
        let request = scheduler
            .parse_natural_language("Schedule a call with John tomorrow at 2pm")
            .unwrap();

        assert_eq!(request.action, ScheduleAction::Create);
        assert_eq!(request.participants, vec!["john"]);
        assert!(matches!(request.when, Some(ScheduleTime::Absolute(_))));
    }

    #[test]
    fn test_parse_in_2_hours() {
        let scheduler = Scheduler::new("user1".to_string(), "UTC".to_string());
        let request = scheduler
            .parse_natural_language("Remind me to buy groceries in 2 hours")
            .unwrap();

        assert_eq!(request.action, ScheduleAction::Create);
        assert!(matches!(
            request.when,
            Some(ScheduleTime::Relative(RelativeTime {
                amount: 2,
                unit: TimeUnit::Hours,
                ..
            }))
        ));
    }

    #[test]
    fn test_parse_recurring_weekly() {
        let scheduler = Scheduler::new("user1".to_string(), "UTC".to_string());
        let request = scheduler
            .parse_natural_language("Schedule team standup every Monday at 9am")
            .unwrap();

        assert_eq!(request.action, ScheduleAction::Create);
        assert!(request.recurrence.is_some());
    }

    #[test]
    fn test_extract_clock_time() {
        let scheduler = Scheduler::new("user1".to_string(), "UTC".to_string());

        let time1 = scheduler.extract_clock_time("at 2pm").unwrap();
        assert_eq!(time1.hour(), 14);

        let time2 = scheduler.extract_clock_time("at 14:30").unwrap();
        assert_eq!(time2.hour(), 14);
        assert_eq!(time2.minute(), 30);
    }

    // =============================================================================
    // NATURAL LANGUAGE PARSING TESTS
    // =============================================================================

    #[test]
    fn test_parse_time_expression() {
        // Test PM/AM format
        assert_eq!(parse_time_expression("3pm").unwrap().hour(), 15);
        assert_eq!(parse_time_expression("3 pm").unwrap().hour(), 15);
        assert_eq!(parse_time_expression("11pm").unwrap().hour(), 23);
        assert_eq!(parse_time_expression("12pm").unwrap().hour(), 12);
        assert_eq!(parse_time_expression("12am").unwrap().hour(), 0);
        assert_eq!(parse_time_expression("3am").unwrap().hour(), 3);

        // Test 24-hour format
        assert_eq!(parse_time_expression("15:30").unwrap().hour(), 15);
        assert_eq!(parse_time_expression("15:30").unwrap().minute(), 30);
        assert_eq!(parse_time_expression("09:00").unwrap().hour(), 9);

        // Test 12-hour format with colon
        let time = parse_time_expression("2:30 pm").unwrap();
        assert_eq!(time.hour(), 14);
        assert_eq!(time.minute(), 30);

        let time2 = parse_time_expression("2:30 am").unwrap();
        assert_eq!(time2.hour(), 2);
        assert_eq!(time2.minute(), 30);

        // Test special times
        assert_eq!(parse_time_expression("noon").unwrap().hour(), 12);
        assert_eq!(parse_time_expression("midnight").unwrap().hour(), 0);
        assert_eq!(parse_time_expression("morning").unwrap().hour(), 9);
        assert_eq!(parse_time_expression("afternoon").unwrap().hour(), 14);
        assert_eq!(parse_time_expression("evening").unwrap().hour(), 18);
        assert_eq!(parse_time_expression("night").unwrap().hour(), 20);
    }

    #[test]
    fn test_parse_relative_date() {
        let now = Utc::now();
        let today = now.date_naive();

        // Test basic relative dates
        assert_eq!(parse_relative_date("today").unwrap(), today);
        assert_eq!(parse_relative_date("tomorrow").unwrap(), today + Duration::days(1));
        assert_eq!(parse_relative_date("yesterday").unwrap(), today - Duration::days(1));

        // Test "in X days/weeks"
        assert_eq!(parse_relative_date("in 3 days").unwrap(), today + Duration::days(3));
        assert_eq!(parse_relative_date("in 2 weeks").unwrap(), today + Duration::weeks(2));
        assert_eq!(parse_relative_date("in 1 month").unwrap(), today + Duration::days(30));

        // Test "next X"
        assert_eq!(parse_relative_date("next week").unwrap(), today + Duration::weeks(1));
        assert_eq!(parse_relative_date("next month").unwrap(), today + Duration::days(30));
    }

    #[test]
    fn test_parse_date_expression() {
        // Test ISO format
        let date = parse_date_expression("2024-01-15").unwrap();
        assert_eq!(date.year(), 2024);
        assert_eq!(date.month(), 1);
        assert_eq!(date.day(), 15);

        // Note: Other formats depend on dateparser library behavior
        // which may vary, so we test conservatively
    }

    #[test]
    fn test_parse_natural_date_relative() {
        // Test "tomorrow at 3pm"
        let result = parse_natural_date("tomorrow at 3pm", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 15);

        // Test "in 2 hours"
        let result = parse_natural_date("in 2 hours", "UTC");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_natural_date_specific_time() {
        // Test just a time (should be today or tomorrow if passed)
        let result = parse_natural_date("3pm", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 15);

        // Test with colon
        let result = parse_natural_date("15:30", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 15);
        assert_eq!(dt.minute(), 30);
    }

    #[test]
    fn test_parse_natural_date_with_timezone() {
        // Test timezone extraction
        let result = parse_natural_date("3pm PST", "UTC");
        assert!(result.is_ok());

        let result = parse_natural_date("2:30 EST", "UTC");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_natural_date_next_weekday() {
        // Test "next Monday", "next Friday", etc.
        let result = parse_natural_date("next monday", "UTC");
        assert!(result.is_ok());

        let result = parse_natural_date("next friday at 2pm", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 14);
    }

    #[test]
    fn test_parse_natural_date_special_times() {
        // Test special time words
        let result = parse_natural_date("tomorrow morning", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 9);

        let result = parse_natural_date("tomorrow at noon", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 12);

        let result = parse_natural_date("tomorrow at midnight", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 0);
    }

    #[test]
    fn test_parse_natural_date_combined() {
        // Test combined expressions
        let result = parse_natural_date("tomorrow at 3:30 PM", "UTC");
        assert!(result.is_ok());
        let dt = result.unwrap();
        assert_eq!(dt.hour(), 15);
        assert_eq!(dt.minute(), 30);

        // Test "in 3 days at 2pm"
        let result = parse_natural_date("in 3 days at 2pm", "UTC");
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_natural_date_error_handling() {
        // Test invalid input
        let result = parse_natural_date("xyz123abc", "UTC");
        assert!(result.is_err());

        let result = parse_natural_date("", "UTC");
        assert!(result.is_err());
    }

    #[test]
    fn test_extract_timezone() {
        // Test timezone extraction
        let (clean_text, tz) = extract_timezone("3pm pst", "UTC").unwrap();
        assert_eq!(clean_text, "3pm");
        assert_eq!(tz.name(), "America/Los_Angeles");

        let (clean_text, tz) = extract_timezone("2:30 est", "UTC").unwrap();
        assert_eq!(clean_text, "2:30");
        assert_eq!(tz.name(), "America/New_York");

        let (clean_text, tz) = extract_timezone("15:30", "America/Los_Angeles").unwrap();
        assert_eq!(clean_text, "15:30");
        assert_eq!(tz.name(), "America/Los_Angeles");
    }

    // =============================================================================
    // SCHEDULER MANAGER TESTS
    // =============================================================================

    #[test]
    fn test_create_appointment_request_from_appointment() {
        let now = Utc::now();
        let appointment = Appointment {
            id: "test-id".to_string(),
            user_id: "user123".to_string(),
            title: "Test Meeting".to_string(),
            description: Some("Test description".to_string()),
            start_time: now,
            end_time: now + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: Some("Conference Room A".to_string()),
            recurring_rule: None,
            reminder_minutes: Some(15),
            created_at: now,
            updated_at: None,
        };

        let request = CreateAppointmentRequest::from(&appointment);
        assert_eq!(request.user_id, "user123");
        assert_eq!(request.title, "Test Meeting");
        assert_eq!(request.description, Some("Test description".to_string()));
        assert_eq!(request.timezone, "UTC");
        assert_eq!(request.location, Some("Conference Room A".to_string()));
    }

    #[test]
    fn test_update_appointment_request_builder() {
        let update = UpdateAppointmentRequest {
            title: Some("Updated Title".to_string()),
            description: Some("Updated description".to_string()),
            start_time: None,
            end_time: None,
            timezone: None,
            location: Some("New Location".to_string()),
            recurrence_rule: None,
            participants: None,
            status: Some("confirmed".to_string()),
        };

        assert_eq!(update.title, Some("Updated Title".to_string()));
        assert_eq!(update.status, Some("confirmed".to_string()));
        assert!(update.start_time.is_none());
    }

    #[test]
    fn test_appointment_filter_default() {
        let filter = AppointmentFilter {
            user_id: "user123".to_string(),
            ..Default::default()
        };

        assert_eq!(filter.user_id, "user123");
        assert!(filter.start_time.is_none());
        assert!(filter.end_time.is_none());
        assert!(filter.status.is_none());
    }

    #[test]
    fn test_appointment_filter_with_time_range() {
        let now = Utc::now();
        let filter = AppointmentFilter {
            user_id: "user123".to_string(),
            start_time: Some(now),
            end_time: Some(now + Duration::days(7)),
            status: Some("scheduled".to_string()),
        };

        assert_eq!(filter.user_id, "user123");
        assert!(filter.start_time.is_some());
        assert!(filter.end_time.is_some());
        assert_eq!(filter.status, Some("scheduled".to_string()));
    }

    #[test]
    fn test_scheduler_manager_new() {
        let manager = SchedulerManager::new(
            "http://localhost:8787".to_string(),
            "user123".to_string(),
            Some("test-token".to_string()),
        );

        assert_eq!(manager.server_url, "http://localhost:8787");
        assert_eq!(manager.user_id, "user123");
        assert_eq!(manager.auth_token, Some("test-token".to_string()));
    }

    // Integration tests (require running server)
    // These are marked with #[ignore] to avoid running in CI without a server
    // To run: cargo test -- --ignored

    #[tokio::test]
    #[ignore]
    async fn test_scheduler_manager_crud_flow() {
        // This test requires a running server at localhost:8787
        let manager = SchedulerManager::new(
            "http://localhost:8787".to_string(),
            "test-user".to_string(),
            None,
        );

        let now = Utc::now();
        let request = CreateAppointmentRequest {
            user_id: "test-user".to_string(),
            title: "Integration Test Meeting".to_string(),
            description: Some("Testing CRUD operations".to_string()),
            start_time: now + Duration::hours(1),
            end_time: now + Duration::hours(2),
            timezone: "UTC".to_string(),
            location: Some("Virtual".to_string()),
            recurrence_rule: None,
            participants: vec![],
        };

        // Create
        let created = manager.create_appointment(request).await;
        assert!(created.is_ok(), "Failed to create appointment");
        let appointment = created.unwrap();
        let apt_id = appointment.id.clone();

        // Read
        let retrieved = manager.get_appointment(&apt_id).await;
        assert!(retrieved.is_ok(), "Failed to get appointment");
        assert!(retrieved.unwrap().is_some(), "Appointment not found");

        // Update
        let update = UpdateAppointmentRequest {
            title: Some("Updated Title".to_string()),
            description: None,
            start_time: None,
            end_time: None,
            timezone: None,
            location: Some("Conference Room B".to_string()),
            recurrence_rule: None,
            participants: None,
            status: None,
        };
        let updated = manager.update_appointment(&apt_id, update).await;
        assert!(updated.is_ok(), "Failed to update appointment");

        // List
        let filter = AppointmentFilter {
            user_id: "test-user".to_string(),
            start_time: Some(now),
            end_time: Some(now + Duration::days(1)),
            status: Some("scheduled".to_string()),
        };
        let list = manager.list_appointments(filter).await;
        assert!(list.is_ok(), "Failed to list appointments");
        assert!(!list.unwrap().is_empty(), "No appointments found");

        // Delete
        let deleted = manager.delete_appointment(&apt_id).await;
        assert!(deleted.is_ok(), "Failed to delete appointment");

        // Verify deletion
        let retrieved = manager.get_appointment(&apt_id).await;
        assert!(
            retrieved.is_ok() && retrieved.unwrap().is_none(),
            "Appointment still exists after deletion"
        );
    }

    #[tokio::test]
    #[ignore]
    async fn test_scheduler_manager_reminders() {
        // This test requires a running server at localhost:8787
        let manager = SchedulerManager::new(
            "http://localhost:8787".to_string(),
            "test-user".to_string(),
            None,
        );

        let now = Utc::now();
        let reminder = Reminder {
            id: "".to_string(), // Will be generated by server
            user_id: "test-user".to_string(),
            title: "Test Reminder".to_string(),
            description: Some("Testing reminder operations".to_string()),
            due_time: now + Duration::hours(2),
            completed: false,
            priority: ReminderPriority::High,
            created_at: now,
            updated_at: None,
        };

        // Create
        let created = manager.create_reminder(&reminder).await;
        assert!(created.is_ok(), "Failed to create reminder");
        let reminder_id = created.unwrap();

        // List
        let list = manager.list_reminders(false).await;
        assert!(list.is_ok(), "Failed to list reminders");
        assert!(!list.unwrap().is_empty(), "No reminders found");

        // Update (mark as completed)
        let updated = manager.update_reminder(&reminder_id, true).await;
        assert!(updated.is_ok(), "Failed to update reminder");

        // Delete
        let deleted = manager.delete_reminder(&reminder_id).await;
        assert!(deleted.is_ok(), "Failed to delete reminder");
    }

    #[tokio::test]
    #[ignore]
    async fn test_scheduler_manager_today_schedule() {
        // This test requires a running server at localhost:8787
        let manager = SchedulerManager::new(
            "http://localhost:8787".to_string(),
            "test-user".to_string(),
            None,
        );

        let today = manager.get_today_schedule().await;
        assert!(today.is_ok(), "Failed to get today's schedule");
    }

    #[tokio::test]
    #[ignore]
    async fn test_scheduler_manager_week_schedule() {
        // This test requires a running server at localhost:8787
        let manager = SchedulerManager::new(
            "http://localhost:8787".to_string(),
            "test-user".to_string(),
            None,
        );

        let week = manager.get_week_schedule().await;
        assert!(week.is_ok(), "Failed to get week's schedule");
    }

    #[tokio::test]
    #[ignore]
    async fn test_scheduler_manager_error_handling() {
        // Test with invalid server URL
        let manager = SchedulerManager::new(
            "http://invalid-server:9999".to_string(),
            "test-user".to_string(),
            None,
        );

        let filter = AppointmentFilter {
            user_id: "test-user".to_string(),
            ..Default::default()
        };

        let result = manager.list_appointments(filter).await;
        assert!(result.is_err(), "Expected error with invalid server");
    }

    // =============================================================================
    // RECURRING EVENT EXPANSION TESTS
    // =============================================================================

    #[test]
    fn test_recurrence_pattern_daily() {
        let pattern = RecurrencePattern::daily(2);
        assert_eq!(pattern.frequency, RecurrenceFrequency::Daily);
        assert_eq!(pattern.interval, 2);
        assert!(pattern.days_of_week.is_none());
        assert!(pattern.day_of_month.is_none());
    }

    #[test]
    fn test_recurrence_pattern_weekly() {
        let pattern = RecurrencePattern::weekly(1, vec![Weekday::Mon, Weekday::Wed, Weekday::Fri]);
        assert_eq!(pattern.frequency, RecurrenceFrequency::Weekly);
        assert_eq!(pattern.interval, 1);
        assert_eq!(pattern.days_of_week.unwrap().len(), 3);
    }

    #[test]
    fn test_recurrence_pattern_monthly() {
        let pattern = RecurrencePattern::monthly(1, 15);
        assert_eq!(pattern.frequency, RecurrenceFrequency::Monthly);
        assert_eq!(pattern.interval, 1);
        assert_eq!(pattern.day_of_month.unwrap(), 15);
    }

    #[test]
    fn test_recurrence_pattern_with_end_date() {
        let now = Utc::now();
        let end_date = now + Duration::days(30);
        let pattern = RecurrencePattern::daily(1).with_end_date(end_date);
        assert_eq!(pattern.end_date.unwrap(), end_date);
        assert_eq!(pattern.until.unwrap(), end_date); // Backwards compatibility
    }

    #[test]
    fn test_recurrence_pattern_with_occurrence_count() {
        let pattern = RecurrencePattern::daily(1).with_occurrence_count(10);
        assert_eq!(pattern.occurrence_count.unwrap(), 10);
        assert_eq!(pattern.count.unwrap(), 10); // Backwards compatibility
    }

    #[test]
    fn test_expand_recurring_daily() {
        let now = Utc::now();
        let pattern = RecurrencePattern::daily(1).with_occurrence_count(5);
        let pattern_json = serde_json::to_string(&pattern).unwrap();

        let appointment = Appointment {
            id: "test-daily".to_string(),
            user_id: "user1".to_string(),
            title: "Daily Standup".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::minutes(30),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: Some(pattern_json),
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let instances = expand_recurring_appointment(
            &appointment,
            now,
            now + Duration::days(10),
        ).unwrap();

        assert_eq!(instances.len(), 5);
        assert_eq!(instances[0].start_time, now);
        assert_eq!(instances[1].start_time, now + Duration::days(1));
        assert_eq!(instances[4].start_time, now + Duration::days(4));
    }

    #[test]
    fn test_expand_recurring_weekly() {
        // Use a Monday as the start date for predictability
        let start_monday = NaiveDate::from_ymd_opt(2024, 1, 1).unwrap() // Jan 1, 2024 is a Monday
            .and_hms_opt(10, 0, 0).unwrap()
            .and_utc();

        let pattern = RecurrencePattern::weekly(1, vec![Weekday::Mon])
            .with_occurrence_count(4);
        let pattern_json = serde_json::to_string(&pattern).unwrap();

        let appointment = Appointment {
            id: "test-weekly".to_string(),
            user_id: "user1".to_string(),
            title: "Weekly Meeting".to_string(),
            description: None,
            start_time: start_monday,
            end_time: start_monday + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: Some(pattern_json),
            reminder_minutes: None,
            created_at: start_monday,
            updated_at: None,
        };

        let instances = expand_recurring_appointment(
            &appointment,
            start_monday,
            start_monday + Duration::days(35),
        ).unwrap();

        // Should get 4 instances (or fewer if the range doesn't cover all)
        assert!(instances.len() >= 1 && instances.len() <= 4);

        // If we have multiple instances, verify they're on Mondays and roughly 7 days apart
        if instances.len() >= 2 {
            for i in 1..instances.len() {
                // Check that each instance is on a Monday
                assert_eq!(instances[i].start_time.weekday(), Weekday::Mon);

                // Check gap is approximately 7 days (allowing for edge cases)
                let gap = (instances[i].start_time - instances[i-1].start_time).num_days();
                assert!(gap >= 6 && gap <= 8, "Gap was {} days", gap);
            }
        }
    }

    #[test]
    fn test_expand_recurring_monthly() {
        let now = Utc::now();
        let pattern = RecurrencePattern::monthly(1, 15)
            .with_occurrence_count(3);
        let pattern_json = serde_json::to_string(&pattern).unwrap();

        let appointment = Appointment {
            id: "test-monthly".to_string(),
            user_id: "user1".to_string(),
            title: "Monthly Review".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(2),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: Some(pattern_json),
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let instances = expand_recurring_appointment(
            &appointment,
            now,
            now + Duration::days(100),
        ).unwrap();

        assert!(instances.len() <= 3);
    }

    #[test]
    fn test_days_in_month() {
        assert_eq!(days_in_month(2024, 1), 31);  // January
        assert_eq!(days_in_month(2024, 2), 29);  // February (leap year)
        assert_eq!(days_in_month(2023, 2), 28);  // February (non-leap year)
        assert_eq!(days_in_month(2024, 4), 30);  // April
        assert_eq!(days_in_month(2024, 12), 31); // December
    }

    #[test]
    fn test_monthly_recurrence_edge_case() {
        // Test month-end edge case (e.g., Jan 31 -> Feb 28/29)
        let jan_31 = NaiveDate::from_ymd_opt(2024, 1, 31).unwrap()
            .and_hms_opt(10, 0, 0).unwrap()
            .and_utc();

        let pattern = RecurrencePattern::monthly(1, 31);
        let next = calculate_next_occurrence(jan_31, &pattern).unwrap();

        // Should be Feb 29, 2024 (leap year)
        assert_eq!(next.month(), 2);
        assert_eq!(next.day(), 29);
    }

    // =============================================================================
    // CONFLICT DETECTION TESTS
    // =============================================================================

    #[test]
    fn test_check_conflicts_no_conflict() {
        let now = Utc::now();

        let apt1 = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 1".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let apt2 = Appointment {
            id: "apt2".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 2".to_string(),
            description: None,
            start_time: now + Duration::hours(2),
            end_time: now + Duration::hours(3),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let conflicts = check_conflicts(&apt2, &[apt1]);
        assert_eq!(conflicts.len(), 0);
    }

    #[test]
    fn test_check_conflicts_complete_overlap() {
        let now = Utc::now();

        let apt1 = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 1".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(2),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let apt2 = Appointment {
            id: "apt2".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 2".to_string(),
            description: None,
            start_time: now + Duration::minutes(30),
            end_time: now + Duration::minutes(90),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let conflicts = check_conflicts(&apt2, &[apt1]);
        assert_eq!(conflicts.len(), 1);
        assert_eq!(conflicts[0].conflict_type, ConflictType::Complete);
    }

    #[test]
    fn test_check_conflicts_partial_overlap() {
        let now = Utc::now();

        let apt1 = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 1".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let apt2 = Appointment {
            id: "apt2".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 2".to_string(),
            description: None,
            start_time: now + Duration::minutes(30),
            end_time: now + Duration::minutes(90),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let conflicts = check_conflicts(&apt2, &[apt1]);
        assert_eq!(conflicts.len(), 1);
        assert!(matches!(
            conflicts[0].conflict_type,
            ConflictType::PartialEnd | ConflictType::Complete
        ));
    }

    #[test]
    fn test_check_conflicts_no_buffer() {
        let now = Utc::now();

        let apt1 = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 1".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        // Meeting starts exactly 2 minutes after previous one ends (less than 5 min buffer)
        let apt2 = Appointment {
            id: "apt2".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting 2".to_string(),
            description: None,
            start_time: now + Duration::hours(1) + Duration::minutes(2),
            end_time: now + Duration::hours(2) + Duration::minutes(2),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let conflicts = check_conflicts(&apt2, &[apt1]);
        assert_eq!(conflicts.len(), 1);
        assert_eq!(conflicts[0].conflict_type, ConflictType::NoBuffer);
    }

    #[test]
    fn test_check_conflicts_same_id_ignored() {
        let now = Utc::now();

        let apt = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        // Check against itself - should find no conflicts
        let conflicts = check_conflicts(&apt, &[apt.clone()]);
        assert_eq!(conflicts.len(), 0);
    }

    // =============================================================================
    // FREE SLOT FINDING TESTS
    // =============================================================================

    #[test]
    fn test_find_free_slots_empty_day() {
        let now = Utc::now();
        let start = now.date_naive().and_hms_opt(0, 0, 0).unwrap().and_utc();
        let end = start + Duration::days(1);

        let free_slots = find_free_slots(60, start, end, &[]);

        // Should find at least one free slot during work hours (9-5)
        assert!(!free_slots.is_empty());
        assert!(free_slots[0].duration_minutes >= 60);
    }

    #[test]
    fn test_find_free_slots_with_appointments() {
        let now = Utc::now();
        let day_start = now.date_naive().and_hms_opt(9, 0, 0).unwrap().and_utc();

        let apt1 = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting".to_string(),
            description: None,
            start_time: day_start + Duration::hours(2), // 11 AM
            end_time: day_start + Duration::hours(3),   // 12 PM
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let free_slots = find_free_slots(
            60,
            day_start,
            day_start + Duration::hours(8), // Until 5 PM
            &[apt1],
        );

        // Should find slots before and after the appointment
        assert!(!free_slots.is_empty());
    }

    #[test]
    fn test_find_free_slots_no_slot_available() {
        let now = Utc::now();
        let day_start = now.date_naive().and_hms_opt(9, 0, 0).unwrap().and_utc();

        // Create back-to-back appointments filling the entire day
        let mut appointments = Vec::new();
        for i in 0..8 {
            appointments.push(Appointment {
                id: format!("apt{}", i),
                user_id: "user1".to_string(),
                title: format!("Meeting {}", i),
                description: None,
                start_time: day_start + Duration::hours(i),
                end_time: day_start + Duration::hours(i + 1),
                timezone: "UTC".to_string(),
                location: None,
                recurring_rule: None,
                reminder_minutes: None,
                created_at: now,
                updated_at: None,
            });
        }

        let free_slots = find_free_slots(
            60,
            day_start,
            day_start + Duration::hours(8),
            &appointments,
        );

        // Should find no 60+ minute slots
        assert_eq!(free_slots.len(), 0);
    }

    #[test]
    fn test_find_free_slots_respects_buffer() {
        let now = Utc::now();
        let day_start = now.date_naive().and_hms_opt(9, 0, 0).unwrap().and_utc();

        let apt1 = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting".to_string(),
            description: None,
            start_time: day_start,
            end_time: day_start + Duration::minutes(55), // Ends at 9:55
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let free_slots = find_free_slots(
            60,
            day_start,
            day_start + Duration::hours(3),
            &[apt1],
        );

        // First free slot should start after buffer time (10:00 + 5 min buffer = 10:05)
        if !free_slots.is_empty() {
            let first_slot_start = free_slots[0].start;
            assert!(first_slot_start >= day_start + Duration::minutes(60)); // At least 10:00
        }
    }

    #[test]
    fn test_conflict_info_serialization() {
        let now = Utc::now();
        let apt = Appointment {
            id: "apt1".to_string(),
            user_id: "user1".to_string(),
            title: "Meeting".to_string(),
            description: None,
            start_time: now,
            end_time: now + Duration::hours(1),
            timezone: "UTC".to_string(),
            location: None,
            recurring_rule: None,
            reminder_minutes: None,
            created_at: now,
            updated_at: None,
        };

        let conflict = ConflictInfo {
            conflicting_appointment: apt,
            conflict_type: ConflictType::Complete,
            overlap_start: now,
            overlap_end: now + Duration::hours(1),
        };

        // Should serialize/deserialize without errors
        let json = serde_json::to_string(&conflict).unwrap();
        let deserialized: ConflictInfo = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.conflict_type, ConflictType::Complete);
    }

    #[test]
    fn test_time_slot_serialization() {
        let now = Utc::now();
        let slot = TimeSlot {
            start: now,
            end: now + Duration::hours(1),
            duration_minutes: 60,
        };

        // Should serialize/deserialize without errors
        let json = serde_json::to_string(&slot).unwrap();
        let deserialized: TimeSlot = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.duration_minutes, 60);
    }

    // =============================================================================
    // REMINDER SYSTEM TESTS
    // =============================================================================

    #[test]
    fn test_reminder_status_default() {
        let status = ReminderStatus::default();
        assert_eq!(status, ReminderStatus::Pending);
    }

    #[test]
    fn test_reminder_preferences_default() {
        let prefs = ReminderPreferences::default();
        assert!(prefs.reminders_enabled);
        assert_eq!(prefs.default_minutes_before, vec![15]);
        assert!(prefs.preferred_methods.contains(&ReminderMethod::Sms));
    }

    #[test]
    fn test_appointment_reminder_serialization() {
        let now = Utc::now();
        let reminder = AppointmentReminder {
            id: "test-reminder-1".to_string(),
            appointment_id: "apt-123".to_string(),
            user_id: "user-456".to_string(),
            minutes_before: 15,
            method: ReminderMethod::Sms,
            status: ReminderStatus::Pending,
            scheduled_time: now,
            sent_at: None,
            error_message: None,
            retry_count: 0,
            created_at: now,
            updated_at: None,
        };

        // Should serialize/deserialize without errors
        let json = serde_json::to_string(&reminder).unwrap();
        let deserialized: AppointmentReminder = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.id, "test-reminder-1");
        assert_eq!(deserialized.minutes_before, 15);
        assert_eq!(deserialized.method, ReminderMethod::Sms);
    }

    #[test]
    fn test_reminder_method_serialization() {
        let methods = vec![
            ReminderMethod::Sms,
            ReminderMethod::Email,
            ReminderMethod::Voice,
            ReminderMethod::Push,
        ];

        for method in methods {
            let json = serde_json::to_string(&method).unwrap();
            let deserialized: ReminderMethod = serde_json::from_str(&json).unwrap();
            assert_eq!(deserialized, method);
        }
    }

    #[test]
    fn test_reminder_status_serialization() {
        let statuses = vec![
            ReminderStatus::Pending,
            ReminderStatus::Sent,
            ReminderStatus::Failed,
            ReminderStatus::Cancelled,
            ReminderStatus::Snoozed,
        ];

        for status in statuses {
            let json = serde_json::to_string(&status).unwrap();
            let deserialized: ReminderStatus = serde_json::from_str(&json).unwrap();
            assert_eq!(deserialized, status);
        }
    }
}
