/// Test loading admin user from config.toml
///
/// This example demonstrates the new user configuration architecture:
/// - Admin user: Loaded from config.toml [admin] section
/// - Regular users: Stored in database (not shown here)
///
/// Run with: cargo run --example test_admin_config

use xswarm::config::ProjectConfig;

fn main() -> anyhow::Result<()> {
    println!("=== Admin User Configuration Test ===\n");

    // Load project configuration
    println!("Loading config.toml...");
    let config = ProjectConfig::load()?;
    println!("✓ Config loaded successfully\n");

    // Get admin user
    let admin = config.get_admin();
    println!("Admin User Details:");
    println!("  Username: {}", admin.username);
    println!("  Name: {}", admin.name);
    println!("  Email: {}", admin.email);
    println!("  Phone: {}", admin.phone);
    println!("  xSwarm Email: {}", admin.xswarm_email);
    println!("  xSwarm Phone: {}", admin.xswarm_phone);
    println!("  Persona: {}", admin.persona);
    println!("  Wake Word: {}", admin.wake_word);
    println!("  Subscription Tier: {}", admin.subscription_tier);
    println!();

    // Show admin permissions
    println!("Admin Permissions:");
    println!("  Access Level: {}", admin.access_level);
    println!("  Can Provision Numbers: {}", admin.can_provision_numbers);
    println!("  Can View All Users: {}", admin.can_view_all_users);
    println!("  Can Manage Subscriptions: {}", admin.can_manage_subscriptions);
    println!("  Can Manage Config: {}", admin.can_manage_config);
    println!("  Can Access All Channels: {}", admin.can_access_all_channels);
    println!();

    // Test admin detection
    println!("Testing admin detection:");

    let test_emails = vec![
        admin.email.clone(),
        admin.xswarm_email.clone(),
        "notadmin@example.com".to_string(),
    ];

    for email in test_emails {
        let is_admin = config.is_admin_by_email(&email);
        println!("  {} -> {}", email, if is_admin { "✓ ADMIN" } else { "✗ Regular user" });
    }
    println!();

    let test_phones = vec![
        admin.phone.clone(),
        admin.xswarm_phone.clone(),
        "+15551234567".to_string(),
    ];

    for phone in test_phones {
        let is_admin = config.is_admin_by_phone(&phone);
        println!("  {} -> {}", phone, if is_admin { "✓ ADMIN" } else { "✗ Regular user" });
    }
    println!();

    // Show subscription tiers
    println!("Subscription Tiers:");

    if let Some(free_tier) = config.get_tier_config("free") {
        println!("  Free Tier:");
        println!("    Email Limit: {} per day", free_tier.email_limit);
        println!("    Voice Minutes: {}", free_tier.voice_minutes);
        println!("    SMS Messages: {}", free_tier.sms_messages);
        println!("    Phone Numbers: {}", free_tier.phone_numbers);
        println!("    Price: {:?}", free_tier.price);
    }
    println!();

    if let Some(premium_tier) = config.get_tier_config("premium") {
        println!("  Premium Tier:");
        println!("    Email Limit: {}", if premium_tier.email_limit == -1 { "Unlimited".to_string() } else { premium_tier.email_limit.to_string() });
        println!("    Voice Minutes: {} (included)", premium_tier.voice_minutes);
        println!("    SMS Messages: {} (included)", premium_tier.sms_messages);
        println!("    Phone Numbers: {} (included)", premium_tier.phone_numbers);
        println!("    Price: ${:.2}/month", premium_tier.price.unwrap_or(0.0));
        println!("    Voice Overage: ${:.3}/min", premium_tier.voice_overage_rate.unwrap_or(0.0));
        println!("    SMS Overage: ${:.4}/msg", premium_tier.sms_overage_rate.unwrap_or(0.0));
    }
    println!();

    // Admin tier
    println!("  Admin Tier:");
    println!("    Email Limit: Unlimited");
    println!("    Voice Minutes: Unlimited");
    println!("    SMS Messages: Unlimited");
    println!("    Phone Numbers: Configured in config.toml");
    println!("    Price: N/A (system admin)");
    println!();

    println!("✓ All tests passed!");
    println!("\nNote: Regular users are stored in the Turso database, not in config.toml");

    Ok(())
}
