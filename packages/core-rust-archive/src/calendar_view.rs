// Calendar View Module - Visual calendar displays for CLI
//
// This module provides rich visual calendar views with:
// - Day view: Hourly time slots for a single day
// - Week view: 7-day overview (Monday-Sunday)
// - Month view: Full month calendar grid
// - Color coding and terminal formatting

use anyhow::{Context, Result};
use chrono::{DateTime, Datelike, Duration, NaiveDate, Timelike, Utc, Weekday};
use crossterm::style::{Color, Stylize};
use serde::{Deserialize, Serialize};

use crate::scheduler::Appointment;

/// Output format for calendar views
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputFormat {
    /// ASCII table with ANSI colors
    Terminal,
    /// Plain text without colors
    Plain,
    /// JSON format
    Json,
}

impl Default for OutputFormat {
    fn default() -> Self {
        OutputFormat::Terminal
    }
}

/// Calendar view type
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ViewType {
    Day,
    Week,
    Month,
}

/// Calendar view configuration
#[derive(Debug, Clone)]
pub struct CalendarViewConfig {
    pub format: OutputFormat,
    pub show_time_grid: bool,
    pub hour_start: u32,
    pub hour_end: u32,
    pub color_by_type: bool,
}

impl Default for CalendarViewConfig {
    fn default() -> Self {
        Self {
            format: OutputFormat::Terminal,
            show_time_grid: true,
            hour_start: 6,  // 6 AM
            hour_end: 22,   // 10 PM
            color_by_type: true,
        }
    }
}

/// Render day view - show appointments for a single day
pub fn render_day_view(
    date: NaiveDate,
    appointments: &[Appointment],
    config: &CalendarViewConfig,
) -> Result<String> {
    match config.format {
        OutputFormat::Json => render_day_view_json(date, appointments),
        OutputFormat::Plain => render_day_view_plain(date, appointments, config),
        OutputFormat::Terminal => render_day_view_terminal(date, appointments, config),
    }
}

/// Render week view - show appointments for a week (Monday-Sunday)
pub fn render_week_view(
    start_date: NaiveDate,
    appointments: &[Appointment],
    config: &CalendarViewConfig,
) -> Result<String> {
    match config.format {
        OutputFormat::Json => render_week_view_json(start_date, appointments),
        OutputFormat::Plain => render_week_view_plain(start_date, appointments, config),
        OutputFormat::Terminal => render_week_view_terminal(start_date, appointments, config),
    }
}

/// Render month view - show appointments for an entire month
pub fn render_month_view(
    year: i32,
    month: u32,
    appointments: &[Appointment],
    config: &CalendarViewConfig,
) -> Result<String> {
    match config.format {
        OutputFormat::Json => render_month_view_json(year, month, appointments),
        OutputFormat::Plain => render_month_view_plain(year, month, appointments, config),
        OutputFormat::Terminal => render_month_view_terminal(year, month, appointments, config),
    }
}

// ============================================================================
// DAY VIEW IMPLEMENTATIONS
// ============================================================================

fn render_day_view_terminal(
    date: NaiveDate,
    appointments: &[Appointment],
    config: &CalendarViewConfig,
) -> Result<String> {
    let mut output = String::new();

    // Header
    output.push_str(&format!("\n{}\n",
        format!("📅 {}", date.format("%A, %B %d, %Y"))
            .bold()
            .with(Color::Cyan)
            .to_string()
    ));
    output.push_str(&"─".repeat(60));
    output.push('\n');

    // Filter appointments for this day
    let day_appointments: Vec<&Appointment> = appointments
        .iter()
        .filter(|a| a.start_time.date_naive() == date)
        .collect();

    if day_appointments.is_empty() {
        output.push_str("\n  No appointments scheduled for this day.\n\n");
        return Ok(output);
    }

    if config.show_time_grid {
        // Time grid view
        for hour in config.hour_start..=config.hour_end {
            let hour_str = format!("{:02}:00", hour);
            output.push_str(&format!("\n{} ", hour_str.with(Color::DarkGrey)));
            output.push_str(&"│ ".with(Color::DarkGrey).to_string());

            // Find appointments for this hour
            let hour_appointments: Vec<&Appointment> = day_appointments
                .iter()
                .filter(|a| {
                    let start_hour = a.start_time.hour();
                    let end_hour = a.end_time.hour();
                    hour >= start_hour && hour < end_hour
                })
                .copied()
                .collect();

            if !hour_appointments.is_empty() {
                for appt in hour_appointments {
                    let time_range = format!(
                        "{} - {}",
                        appt.start_time.format("%H:%M"),
                        appt.end_time.format("%H:%M")
                    );
                    output.push_str(&format!(
                        "{} {} ",
                        "●".with(Color::Green),
                        format!("{}: {}", time_range, appt.title)
                            .with(Color::White)
                    ));
                }
            }
        }
    } else {
        // List view
        for appt in day_appointments {
            let time_range = format!(
                "{} - {}",
                appt.start_time.format("%H:%M"),
                appt.end_time.format("%H:%M")
            );

            output.push_str(&format!(
                "\n  {} {} {}\n",
                "●".with(Color::Green),
                time_range.with(Color::Yellow),
                appt.title.clone().bold()
            ));

            if let Some(desc) = &appt.description {
                output.push_str(&format!("     {}\n", desc.clone().with(Color::DarkGrey)));
            }

            if let Some(location) = &appt.location {
                output.push_str(&format!("     📍 {}\n", location.clone().with(Color::Blue)));
            }
        }
    }

    output.push('\n');
    output.push_str(&"─".repeat(60));
    output.push('\n');

    Ok(output)
}

fn render_day_view_plain(
    date: NaiveDate,
    appointments: &[Appointment],
    _config: &CalendarViewConfig,
) -> Result<String> {
    let mut output = String::new();

    output.push_str(&format!("\n{}\n", date.format("%A, %B %d, %Y")));
    output.push_str(&"=".repeat(60));
    output.push('\n');

    let day_appointments: Vec<&Appointment> = appointments
        .iter()
        .filter(|a| a.start_time.date_naive() == date)
        .collect();

    if day_appointments.is_empty() {
        output.push_str("\nNo appointments scheduled for this day.\n\n");
        return Ok(output);
    }

    for appt in day_appointments {
        let time_range = format!(
            "{} - {}",
            appt.start_time.format("%H:%M"),
            appt.end_time.format("%H:%M")
        );

        output.push_str(&format!("\n  {} {}\n", time_range, appt.title));

        if let Some(desc) = &appt.description {
            output.push_str(&format!("    {}\n", desc));
        }

        if let Some(location) = &appt.location {
            output.push_str(&format!("    Location: {}\n", location));
        }
    }

    output.push('\n');
    Ok(output)
}

fn render_day_view_json(date: NaiveDate, appointments: &[Appointment]) -> Result<String> {
    let day_appointments: Vec<&Appointment> = appointments
        .iter()
        .filter(|a| a.start_time.date_naive() == date)
        .collect();

    #[derive(Serialize)]
    struct DayView {
        date: String,
        appointments: Vec<Appointment>,
    }

    let view = DayView {
        date: date.format("%Y-%m-%d").to_string(),
        appointments: day_appointments.into_iter().cloned().collect(),
    };

    serde_json::to_string_pretty(&view).context("Failed to serialize day view")
}

// ============================================================================
// WEEK VIEW IMPLEMENTATIONS
// ============================================================================

fn render_week_view_terminal(
    start_date: NaiveDate,
    appointments: &[Appointment],
    _config: &CalendarViewConfig,
) -> Result<String> {
    let mut output = String::new();

    // Get week range (Monday to Sunday)
    let week_start = start_date - Duration::days(start_date.weekday().num_days_from_monday() as i64);
    let week_end = week_start + Duration::days(6);

    // Header
    output.push_str(&format!("\n{}\n",
        format!("📅 Week of {} - {}",
            week_start.format("%b %d"),
            week_end.format("%b %d, %Y")
        )
        .bold()
        .with(Color::Cyan)
        .to_string()
    ));
    output.push_str(&"─".repeat(80));
    output.push('\n');

    // Render each day
    for day_offset in 0..7 {
        let current_date = week_start + Duration::days(day_offset);
        let day_appointments: Vec<&Appointment> = appointments
            .iter()
            .filter(|a| a.start_time.date_naive() == current_date)
            .collect();

        let day_name = current_date.format("%A").to_string();
        let day_date = current_date.format("%b %d").to_string();

        output.push_str(&format!(
            "\n{} {}\n",
            day_name.bold().with(Color::Yellow),
            day_date.with(Color::DarkGrey)
        ));

        if day_appointments.is_empty() {
            output.push_str(&format!("  {}\n", "No appointments".with(Color::DarkGrey)));
        } else {
            for appt in day_appointments {
                let time_str = appt.start_time.format("%H:%M").to_string();
                output.push_str(&format!(
                    "  {} {} {}\n",
                    "●".with(Color::Green),
                    time_str.with(Color::Yellow),
                    appt.title
                ));
            }
        }
    }

    output.push('\n');
    output.push_str(&"─".repeat(80));
    output.push('\n');

    Ok(output)
}

fn render_week_view_plain(
    start_date: NaiveDate,
    appointments: &[Appointment],
    _config: &CalendarViewConfig,
) -> Result<String> {
    let mut output = String::new();

    let week_start = start_date - Duration::days(start_date.weekday().num_days_from_monday() as i64);
    let week_end = week_start + Duration::days(6);

    output.push_str(&format!("\nWeek of {} - {}\n",
        week_start.format("%b %d"),
        week_end.format("%b %d, %Y")
    ));
    output.push_str(&"=".repeat(80));
    output.push('\n');

    for day_offset in 0..7 {
        let current_date = week_start + Duration::days(day_offset);
        let day_appointments: Vec<&Appointment> = appointments
            .iter()
            .filter(|a| a.start_time.date_naive() == current_date)
            .collect();

        output.push_str(&format!("\n{} {}\n",
            current_date.format("%A"),
            current_date.format("%b %d")
        ));

        if day_appointments.is_empty() {
            output.push_str("  No appointments\n");
        } else {
            for appt in day_appointments {
                output.push_str(&format!(
                    "  {} {}\n",
                    appt.start_time.format("%H:%M"),
                    appt.title
                ));
            }
        }
    }

    output.push('\n');
    Ok(output)
}

fn render_week_view_json(start_date: NaiveDate, appointments: &[Appointment]) -> Result<String> {
    let week_start = start_date - Duration::days(start_date.weekday().num_days_from_monday() as i64);
    let week_end = week_start + Duration::days(6);

    let week_appointments: Vec<&Appointment> = appointments
        .iter()
        .filter(|a| {
            let date = a.start_time.date_naive();
            date >= week_start && date <= week_end
        })
        .collect();

    #[derive(Serialize)]
    struct WeekView {
        start_date: String,
        end_date: String,
        appointments: Vec<Appointment>,
    }

    let view = WeekView {
        start_date: week_start.format("%Y-%m-%d").to_string(),
        end_date: week_end.format("%Y-%m-%d").to_string(),
        appointments: week_appointments.into_iter().cloned().collect(),
    };

    serde_json::to_string_pretty(&view).context("Failed to serialize week view")
}

// ============================================================================
// MONTH VIEW IMPLEMENTATIONS
// ============================================================================

fn render_month_view_terminal(
    year: i32,
    month: u32,
    appointments: &[Appointment],
    _config: &CalendarViewConfig,
) -> Result<String> {
    let mut output = String::new();

    let first_day = NaiveDate::from_ymd_opt(year, month, 1)
        .context("Invalid year/month")?;

    // Header
    output.push_str(&format!("\n{}\n",
        first_day.format("%B %Y")
            .to_string()
            .bold()
            .with(Color::Cyan)
            .to_string()
    ));
    output.push_str(&"─".repeat(80));
    output.push('\n');

    // Day headers
    output.push_str(&format!("\n{}\n",
        " Mon   Tue   Wed   Thu   Fri   Sat   Sun".with(Color::Yellow)
    ));

    // Get first day of month and number of days
    let days_in_month = get_days_in_month(year, month);
    let first_weekday = first_day.weekday().num_days_from_monday() as usize;

    // Build calendar grid
    let mut current_day = 1;
    let mut week_row = vec![String::new(); 7];

    // Fill in leading spaces
    for i in 0..first_weekday {
        week_row[i] = "     ".to_string();
    }

    // Fill in days
    let mut current_pos = first_weekday;
    while current_day <= days_in_month {
        let current_date = NaiveDate::from_ymd_opt(year, month, current_day)
            .context("Invalid date")?;

        // Count appointments for this day
        let day_count = appointments
            .iter()
            .filter(|a| a.start_time.date_naive() == current_date)
            .count();

        let day_str = if day_count > 0 {
            format!("{:2}({}) ", current_day, day_count)
                .with(Color::Green)
                .to_string()
        } else {
            format!("{:2}    ", current_day)
        };

        week_row[current_pos] = day_str;
        current_pos += 1;

        if current_pos >= 7 {
            output.push_str(&format!("{}\n", week_row.join(" ")));
            week_row = vec![String::new(); 7];
            current_pos = 0;
        }

        current_day += 1;
    }

    // Print final week if needed
    if current_pos > 0 {
        for i in current_pos..7 {
            week_row[i] = "     ".to_string();
        }
        output.push_str(&format!("{}\n", week_row.join(" ")));
    }

    output.push('\n');
    output.push_str(&format!("{}\n", "Numbers in () indicate appointment count".with(Color::DarkGrey)));
    output.push_str(&"─".repeat(80));
    output.push('\n');

    Ok(output)
}

fn render_month_view_plain(
    year: i32,
    month: u32,
    appointments: &[Appointment],
    _config: &CalendarViewConfig,
) -> Result<String> {
    let mut output = String::new();

    let first_day = NaiveDate::from_ymd_opt(year, month, 1)
        .context("Invalid year/month")?;

    output.push_str(&format!("\n{}\n", first_day.format("%B %Y")));
    output.push_str(&"=".repeat(80));
    output.push('\n');

    output.push_str("\n Mon   Tue   Wed   Thu   Fri   Sat   Sun\n");

    let days_in_month = get_days_in_month(year, month);
    let first_weekday = first_day.weekday().num_days_from_monday() as usize;

    let mut current_day = 1;
    let mut week_row = vec![String::new(); 7];

    for i in 0..first_weekday {
        week_row[i] = "     ".to_string();
    }

    let mut current_pos = first_weekday;
    while current_day <= days_in_month {
        let current_date = NaiveDate::from_ymd_opt(year, month, current_day)
            .context("Invalid date")?;

        let day_count = appointments
            .iter()
            .filter(|a| a.start_time.date_naive() == current_date)
            .count();

        week_row[current_pos] = if day_count > 0 {
            format!("{:2}({}) ", current_day, day_count)
        } else {
            format!("{:2}    ", current_day)
        };

        current_pos += 1;

        if current_pos >= 7 {
            output.push_str(&format!("{}\n", week_row.join(" ")));
            week_row = vec![String::new(); 7];
            current_pos = 0;
        }

        current_day += 1;
    }

    if current_pos > 0 {
        for i in current_pos..7 {
            week_row[i] = "     ".to_string();
        }
        output.push_str(&format!("{}\n", week_row.join(" ")));
    }

    output.push_str("\nNumbers in () indicate appointment count\n");
    Ok(output)
}

fn render_month_view_json(year: i32, month: u32, appointments: &[Appointment]) -> Result<String> {
    let first_day = NaiveDate::from_ymd_opt(year, month, 1)
        .context("Invalid year/month")?;
    let days_in_month = get_days_in_month(year, month);

    let last_day = NaiveDate::from_ymd_opt(year, month, days_in_month)
        .context("Invalid date")?;

    let month_appointments: Vec<&Appointment> = appointments
        .iter()
        .filter(|a| {
            let date = a.start_time.date_naive();
            date >= first_day && date <= last_day
        })
        .collect();

    #[derive(Serialize)]
    struct MonthView {
        year: i32,
        month: u32,
        appointments: Vec<Appointment>,
    }

    let view = MonthView {
        year,
        month,
        appointments: month_appointments.into_iter().cloned().collect(),
    };

    serde_json::to_string_pretty(&view).context("Failed to serialize month view")
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

fn get_days_in_month(year: i32, month: u32) -> u32 {
    // Get the first day of the next month, then go back one day
    let next_month = if month == 12 {
        NaiveDate::from_ymd_opt(year + 1, 1, 1)
    } else {
        NaiveDate::from_ymd_opt(year, month + 1, 1)
    };

    if let Some(next) = next_month {
        let last_day = next - Duration::days(1);
        last_day.day()
    } else {
        31 // Fallback
    }
}

/// Parse date string (supports "today", "tomorrow", ISO dates, etc.)
pub fn parse_date_string(input: &str) -> Result<NaiveDate> {
    let input_lower = input.to_lowercase();
    let now = Utc::now();

    match input_lower.as_str() {
        "today" => Ok(now.date_naive()),
        "tomorrow" => Ok((now + Duration::days(1)).date_naive()),
        "yesterday" => Ok((now - Duration::days(1)).date_naive()),
        _ => {
            // Try ISO format first (YYYY-MM-DD)
            if let Ok(date) = NaiveDate::parse_from_str(input, "%Y-%m-%d") {
                return Ok(date);
            }

            // Try other common formats
            if let Ok(date) = NaiveDate::parse_from_str(input, "%m/%d/%Y") {
                return Ok(date);
            }

            if let Ok(date) = NaiveDate::parse_from_str(input, "%d-%m-%Y") {
                return Ok(date);
            }

            anyhow::bail!("Could not parse date: {}. Use 'today', 'tomorrow', or YYYY-MM-DD format.", input)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_date_string() {
        // Test relative dates
        let today = Utc::now().date_naive();
        assert_eq!(parse_date_string("today").unwrap(), today);
        assert_eq!(parse_date_string("tomorrow").unwrap(), today + Duration::days(1));

        // Test ISO format
        assert_eq!(
            parse_date_string("2024-01-15").unwrap(),
            NaiveDate::from_ymd_opt(2024, 1, 15).unwrap()
        );
    }

    #[test]
    fn test_get_days_in_month() {
        assert_eq!(get_days_in_month(2024, 1), 31);  // January
        assert_eq!(get_days_in_month(2024, 2), 29);  // February (leap year)
        assert_eq!(get_days_in_month(2023, 2), 28);  // February (non-leap)
        assert_eq!(get_days_in_month(2024, 4), 30);  // April
    }
}
