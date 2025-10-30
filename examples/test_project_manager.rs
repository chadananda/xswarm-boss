/// Example demonstrating ProjectManager and Git Integration
///
/// This example shows how to use the ProjectManager to:
/// - Manage multiple projects
/// - Add and track tasks
/// - Get Git integration status
/// - Generate project health reports
/// - Detect stalled projects

use std::path::PathBuf;
use xswarm::projects::{
    Project, ProjectTask, ProjectManager, ProjectStatus, TaskStatus,
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    println!("=== ProjectManager and Git Integration Demo ===\n");

    // Create a new ProjectManager
    let manager = ProjectManager::new();
    println!("✓ Created ProjectManager\n");

    // Create and add some test projects
    let mut project1 = Project::new(
        "xSwarm Boss".to_string(),
        PathBuf::from("/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss"),
        "user123".to_string(),
    );
    project1.set_description("AI orchestration layer for multi-project development".to_string());
    project1.assign_agent("claude-code".to_string())?;
    let project1_id = project1.id.clone();

    let mut project2 = Project::new(
        "Example Project".to_string(),
        PathBuf::from("/tmp/example-project"),
        "user123".to_string(),
    );
    project2.set_description("A test project for demonstration".to_string());
    project2.update_status(ProjectStatus::Paused);
    let project2_id = project2.id.clone();

    manager.add_project(project1).await?;
    manager.add_project(project2).await?;
    println!("✓ Added 2 projects to manager\n");

    // Add some tasks to project1
    let mut task1 = ProjectTask::new(project1_id.clone(), "Implement ProjectManager".to_string());
    task1.set_description("Create ProjectManager struct with Git integration".to_string());
    task1.set_priority(1); // High priority
    task1.start()?;

    let mut task2 = ProjectTask::new(project1_id.clone(), "Add Git integration".to_string());
    task2.set_description("Integrate Git status and commit tracking".to_string());
    task2.set_priority(1);
    task2.complete()?;

    let mut task3 = ProjectTask::new(project1_id.clone(), "Write documentation".to_string());
    task3.set_description("Document the new features".to_string());
    task3.set_priority(2);

    manager.add_task(task1).await?;
    manager.add_task(task2).await?;
    manager.add_task(task3).await?;
    println!("✓ Added 3 tasks to project 1\n");

    // List all projects
    println!("=== All Projects ===");
    let all_projects = manager.get_all_projects().await;
    for project in &all_projects {
        println!(
            "  - {} (Status: {:?}, Progress: {}%)",
            project.name, project.status, project.progress_percentage
        );
    }
    println!();

    // List active projects only
    println!("=== Active Projects ===");
    let active_projects = manager.get_active_projects().await;
    for project in &active_projects {
        println!("  - {} (Agent: {:?})", project.name, project.assigned_agent);
    }
    println!();

    // Get detailed project status with Git integration
    println!("=== Project Status Report (with Git Integration) ===");
    match manager.get_project_status(&project1_id).await {
        Ok(report) => {
            println!("Project: {}", report.name);
            println!("Status: {:?}", report.status);
            println!("Progress: {}%", report.progress);
            println!("Health Score: {:.2}", report.health_score);

            println!("\nTask Summary:");
            println!("  Total Tasks: {}", report.task_summary.total_tasks);
            println!("  Completed: {}", report.task_summary.completed_tasks);
            println!("  In Progress: {}", report.task_summary.in_progress_tasks);
            println!("  Pending: {}", report.task_summary.pending_tasks);
            println!("  Blocked: {}", report.task_summary.blocked_tasks);
            println!("  Completion Rate: {:.1}%", report.task_summary.completion_percentage());

            if let Some(git_status) = &report.git_status {
                println!("\nGit Status:");
                println!("  Branch: {}", git_status.branch);
                println!("  Clean: {}", git_status.is_clean);
                println!("  Ahead: {}, Behind: {}", git_status.ahead, git_status.behind);
                println!("  Modified Files: {}", git_status.modified_files.len());
                println!("  Untracked Files: {}", git_status.untracked_files.len());
            } else {
                println!("\nGit Status: Not a Git repository");
            }

            if !report.recent_commits.is_empty() {
                println!("\nRecent Commits ({}):", report.recent_commits.len());
                for (i, commit) in report.recent_commits.iter().take(5).enumerate() {
                    println!("  {}. {} - {}",
                        i + 1,
                        &commit.hash[..8],
                        commit.message.lines().next().unwrap_or("No message")
                    );
                    println!("     Author: {}, Files: {}, +{} -{}",
                        commit.author,
                        commit.files_changed,
                        commit.lines_added,
                        commit.lines_removed
                    );
                }
            }
        }
        Err(e) => {
            println!("Error getting project status: {}", e);
        }
    }
    println!();

    // Update project from Git
    println!("=== Syncing Project with Git ===");
    match manager.update_project_from_git(&project1_id).await {
        Ok(_) => println!("✓ Successfully synced project with Git repository"),
        Err(e) => println!("⚠ Git sync failed: {} (this is normal if not a Git repo)", e),
    }
    println!();

    // Check for stalled projects
    println!("=== Stalled Projects (no activity in 24 hours) ===");
    let stalled = manager.get_stalled_projects(24).await?;
    if stalled.is_empty() {
        println!("  No stalled projects found!");
    } else {
        for project in &stalled {
            let hours_since = if let Some(last_activity) = project.last_activity {
                let duration = chrono::Utc::now() - last_activity;
                duration.num_hours()
            } else {
                -1
            };
            println!("  - {} (last activity: {} hours ago)", project.name, hours_since);
        }
    }
    println!();

    // Generate comprehensive status report for all projects
    println!("=== Comprehensive Status Report ===");
    match manager.generate_status_report().await {
        Ok(reports) => {
            println!("Generated reports for {} projects (sorted by health score):\n", reports.len());
            for (i, report) in reports.iter().enumerate() {
                println!("{}. {} - Health: {:.2}, Progress: {}%, Status: {:?}",
                    i + 1,
                    report.name,
                    report.health_score,
                    report.progress,
                    report.status
                );
            }
        }
        Err(e) => {
            println!("Error generating status report: {}", e);
        }
    }
    println!();

    // Retrieve and display a specific project
    println!("=== Get Specific Project ===");
    let retrieved = manager.get_project(&project1_id).await?;
    println!("Project: {}", retrieved.name);
    println!("  ID: {}", retrieved.id);
    println!("  Path: {}", retrieved.path.display());
    println!("  Status: {:?}", retrieved.status);
    println!("  Priority: {}", retrieved.priority);
    println!("  Agent: {:?}", retrieved.assigned_agent);
    println!();

    // Demonstrate project removal
    println!("=== Remove Project ===");
    manager.remove_project(&project2_id).await?;
    println!("✓ Removed project 2");

    let remaining = manager.get_all_projects().await;
    println!("Remaining projects: {}", remaining.len());
    println!();

    println!("=== Demo Complete ===");

    Ok(())
}
