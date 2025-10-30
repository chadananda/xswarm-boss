# xSwarm-boss Security Policy

**Last Updated:** October 17, 2025
**Version:** 1.0
**Status:** Active

This document defines the security model, policies, and safeguards for xSwarm-boss.

---

## Quick Links

- **[PRD](PRD.md)** - Product requirements
- **[Architecture](ARCHITECTURE.md)** - System design
- **[TODO](TODO.md)** - Development tasks

---

## Table of Contents

1. [Security Principles](#security-principles)
2. [Secret Detection & Prevention](#secret-detection--prevention)
3. [Memory Purging](#memory-purging)
4. [File Monitoring](#file-monitoring)
5. [User Warnings](#user-warnings)
6. [Cross-Project Isolation](#cross-project-isolation)
7. [Audit Logging](#audit-logging)

---

## Security Principles

### Core Security Goals

1. **Secrets Never Stored** - API keys, passwords, tokens never persist in memory or logs
2. **Proactive Warning** - Alert user immediately if secrets detected in public/versioned files
3. **Constant Vigilance** - Continuous monitoring and filtering, not just at boundaries
4. **User Control** - User decides how to handle security warnings
5. **Zero Trust** - Assume all data is potentially sensitive until proven otherwise

### Defense in Depth

```
Layer 1: Input Filtering    → Block secrets at entry
Layer 2: Memory Purging      → Constantly scrub working memory
Layer 3: Output Filtering    → Block secrets before external APIs
Layer 4: File Monitoring     → Warn on secrets in public files
Layer 5: Audit Logging       → Track all security events
```

---

## Secret Detection & Prevention

### What Qualifies as a Secret?

**Always Secrets:**
- API keys (OpenAI, Anthropic, AWS, etc.)
- Authentication tokens (JWT, OAuth, GitHub PAT)
- Database credentials (passwords, connection strings)
- Private keys (SSH, TLS, PGP)
- Encryption keys (AES, RSA)
- Cookie values (session tokens)
- Cloud credentials (AWS access keys, GCP service accounts)

**Context-Dependent:**
- Email addresses (PII, but sometimes necessary)
- IP addresses (internal network may be sensitive)
- File paths (may reveal system structure)

### Secret Detection Patterns

```rust
pub struct SecretDetector {
    patterns: Vec<SecretPattern>,
}

pub struct SecretPattern {
    name: &'static str,
    regex: Regex,
    severity: Severity,
}

pub enum Severity {
    Critical,  // API keys, passwords - MUST block
    High,      // Tokens, SSH keys - SHOULD block
    Medium,    // Email, IPs - WARN user
    Low,       // Suspicious patterns - LOG only
}
```

**Detection Patterns:**

```rust
// API Keys
SecretPattern {
    name: "OpenAI API Key",
    regex: r"sk-[a-zA-Z0-9]{48}",
    severity: Critical,
},
SecretPattern {
    name: "Anthropic API Key",
    regex: r"sk-ant-[a-zA-Z0-9-]{95,}",
    severity: Critical,
},
SecretPattern {
    name: "AWS Access Key",
    regex: r"AKIA[0-9A-Z]{16}",
    severity: Critical,
},

// GitHub Tokens
SecretPattern {
    name: "GitHub Personal Access Token",
    regex: r"ghp_[a-zA-Z0-9]{36}",
    severity: Critical,
},
SecretPattern {
    name: "GitHub OAuth Token",
    regex: r"gho_[a-zA-Z0-9]{36}",
    severity: Critical,
},

// Slack Tokens
SecretPattern {
    name: "Slack Token",
    regex: r"xoxb-[0-9]{11,13}-[0-9]{11,13}-[a-zA-Z0-9]{24}",
    severity: Critical,
},

// Private Keys
SecretPattern {
    name: "SSH Private Key",
    regex: r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----",
    severity: Critical,
},
SecretPattern {
    name: "PGP Private Key",
    regex: r"-----BEGIN PGP PRIVATE KEY BLOCK-----",
    severity: Critical,
},

// Generic Secrets
SecretPattern {
    name: "Generic API Key",
    regex: r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9]{32,})",
    severity: High,
},
SecretPattern {
    name: "Password in Code",
    regex: r"password['\"]?\s*[:=]\s*['\"]([^'\"]+)",
    severity: High,
},

// Database Connection Strings
SecretPattern {
    name: "Database Connection String",
    regex: r"(postgres|mysql|mongodb)://[^@]+:[^@]+@",
    severity: Critical,
},

// PII (Medium Severity)
SecretPattern {
    name: "Email Address",
    regex: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    severity: Medium,
},
SecretPattern {
    name: "Private IP Address",
    regex: r"\b(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)",
    severity: Medium,
},
```

### Entropy Detection

**For unknown patterns with high randomness:**

```rust
fn entropy(s: &str) -> f64 {
    let mut char_counts = HashMap::new();
    for c in s.chars() {
        *char_counts.entry(c).or_insert(0) += 1;
    }

    let len = s.len() as f64;
    -char_counts.values()
        .map(|&count| {
            let p = count as f64 / len;
            p * p.log2()
        })
        .sum::<f64>()
}

// Flag strings with entropy > 4.5 as potentially secret
if entropy(token) > 4.5 && token.len() > 20 {
    warn_possible_secret(token);
}
```

---

## Memory Purging

### Continuous Memory Scrubbing

**Problem:** AI memory accumulates sensitive data during conversations.

**Solution:** Constant purging, not just at project boundaries.

```rust
pub struct MemoryManager {
    working_memory: VecDeque<Message>,
    last_purge: Instant,
    purge_interval: Duration,
}

impl MemoryManager {
    pub fn add_message(&mut self, msg: Message) {
        // Filter secrets BEFORE storing
        let filtered = self.filter_secrets(msg);
        self.working_memory.push_back(filtered);

        // Purge if interval elapsed
        if self.last_purge.elapsed() > self.purge_interval {
            self.purge_all_memory();
        }
    }

    fn purge_all_memory(&mut self) {
        // Re-filter ALL messages in working memory
        for msg in &mut self.working_memory {
            *msg = self.filter_secrets(msg.clone());
        }

        // Purge old messages
        while self.working_memory.len() > MAX_WORKING_MEMORY {
            self.working_memory.pop_front();
        }

        self.last_purge = Instant::now();
    }

    fn filter_secrets(&self, mut msg: Message) -> Message {
        msg.content = self.detector.redact_secrets(&msg.content);
        msg
    }
}
```

**Purge Triggers:**
1. **Time-based:** Every 60 seconds
2. **Size-based:** When working memory > 20 messages
3. **Project switch:** When changing project context
4. **On-demand:** User command or API call

### Redaction Format

```rust
fn redact_secrets(&self, text: &str) -> String {
    let mut redacted = text.to_string();

    for pattern in &self.patterns {
        redacted = pattern.regex.replace_all(
            &redacted,
            |caps: &regex::Captures| {
                format!("[REDACTED:{}]", pattern.name)
            }
        ).to_string();
    }

    redacted
}
```

**Example:**
```
Original: "My API key is sk-abc123def456 for OpenAI"
Redacted: "My API key is [REDACTED:OpenAI API Key] for OpenAI"
```

---

## File Monitoring

### Public File Detection

**Problem:** Users may accidentally commit secrets to version control or save them in public locations.

**Solution:** Monitor file writes and warn immediately.

```rust
pub struct FileMonitor {
    detector: SecretDetector,
    git_watcher: GitWatcher,
}

impl FileMonitor {
    pub async fn monitor_file_write(&self, path: &Path, content: &str) -> Result<()> {
        // Check if file is version controlled
        let is_tracked = self.git_watcher.is_tracked(path);
        let is_public = self.is_public_location(path);

        // Scan for secrets
        let findings = self.detector.scan(content);

        if !findings.is_empty() && (is_tracked || is_public) {
            self.emit_warning(path, findings, is_tracked).await?;
        }

        Ok(())
    }

    fn is_public_location(&self, path: &Path) -> bool {
        // Public locations where secrets should NEVER appear
        let public_patterns = [
            "*/public/*",
            "*/docs/*",
            "*/README.md",
            "*/examples/*",
            "*/.github/*",
        ];

        public_patterns.iter().any(|pattern| {
            path.to_string_lossy().contains(&pattern[2..])
        })
    }
}
```

### Git-Aware Monitoring

```rust
pub struct GitWatcher {
    repo: Repository,
}

impl GitWatcher {
    fn is_tracked(&self, path: &Path) -> bool {
        // Check if file is tracked by git
        self.repo.status_file(path)
            .map(|status| !status.is_ignored())
            .unwrap_or(false)
    }

    fn is_staged(&self, path: &Path) -> bool {
        // Check if file is staged for commit
        self.repo.status_file(path)
            .map(|status| status.is_index_new() || status.is_index_modified())
            .unwrap_or(false)
    }

    fn get_diff(&self, path: &Path) -> Result<String> {
        // Get diff to see what's being added
        let head = self.repo.head()?.peel_to_tree()?;
        let diff = self.repo.diff_tree_to_workdir(Some(&head), None)?;
        // Parse diff for this file
        Ok(format!("{:?}", diff))
    }
}
```

---

## User Warnings

### Warning System

```rust
pub enum SecurityWarning {
    SecretInTrackedFile {
        file: PathBuf,
        secret_type: String,
        severity: Severity,
        line_number: usize,
        preview: String,  // Redacted preview
    },
    SecretInPublicLocation {
        file: PathBuf,
        location_type: String,  // "public/", "docs/", etc.
        secret_type: String,
    },
    SecretInMemory {
        context: String,
        secret_type: String,
    },
    SecretBeingCommitted {
        file: PathBuf,
        secret_type: String,
        diff: String,  // Redacted diff
    },
}

impl SecurityWarning {
    pub fn emit(&self) {
        match self {
            SecretInTrackedFile { file, secret_type, line_number, .. } => {
                eprintln!("
╔═══════════════════════════════════════════════════════════╗
║  ⚠️  SECURITY WARNING: Secret Detected in Tracked File  ║
╚═══════════════════════════════════════════════════════════╝

File: {}:{}
Type: {}
Severity: CRITICAL

This file is tracked by git and contains a secret that should
NOT be committed to version control.

Recommended Actions:
1. Remove the secret from the file
2. Use environment variables (.env file)
3. Add .env to .gitignore
4. Rotate the compromised secret if already committed

xSwarm has REDACTED this secret from memory but cannot remove
it from your file. You must fix this manually.
", file.display(), line_number, secret_type);
            },

            SecretInPublicLocation { file, location_type, secret_type } => {
                eprintln!("
╔═══════════════════════════════════════════════════════════╗
║  🚨  CRITICAL: Secret in Public Location  ║
╚═══════════════════════════════════════════════════════════╝

File: {}
Location: {}
Type: {}

This file is in a PUBLIC location ({}) and contains a secret.
Anyone with access to this directory can see the secret.

IMMEDIATE ACTION REQUIRED:
1. Remove the secret from this file NOW
2. Move secrets to secure location (e.g., ~/.config/xswarm/.env)
3. Update file to reference environment variable

xSwarm will NOT process this file until the secret is removed.
", file.display(), location_type, secret_type, location_type);
            },

            SecretBeingCommitted { file, secret_type, diff } => {
                eprintln!("
╔═══════════════════════════════════════════════════════════╗
║  🛑  BLOCKED: Attempting to Commit Secret  ║
╚═══════════════════════════════════════════════════════════╝

File: {}
Type: {}

You are about to commit a {} to version control.
This commit has been BLOCKED.

Diff preview:
{}

Fix before committing:
1. Unstage the file: git reset {}
2. Remove the secret from the file
3. Use .env file or secrets manager
4. Re-stage and commit

xSwarm will not allow commits containing secrets.
", file.display(), secret_type, secret_type, diff, file.display());
            },

            _ => {
                eprintln!("⚠️  Security Warning: {:?}", self);
            }
        }
    }
}
```

### Interactive Resolution

```rust
pub async fn handle_secret_warning(&self, warning: SecurityWarning) -> Result<Action> {
    warning.emit();

    // Prompt user for action
    println!("\nWhat would you like to do?");
    println!("1. Open file in editor to fix");
    println!("2. Ignore this warning (NOT RECOMMENDED)");
    println!("3. Add to .gitignore");
    println!("4. Show me how to use environment variables");
    println!("5. Cancel operation");

    let choice = read_user_input()?;

    match choice {
        1 => {
            // Open file in $EDITOR
            let editor = env::var("EDITOR").unwrap_or("nano".to_string());
            Command::new(editor)
                .arg(&warning.file())
                .spawn()?
                .wait()?;

            // Re-scan after user edits
            self.rescan_file(warning.file()).await?;
        },
        2 => {
            // Log the ignore (for audit)
            warn!("User ignored security warning for {:?}", warning);
        },
        3 => {
            // Add to .gitignore
            self.add_to_gitignore(warning.file()).await?;
        },
        4 => {
            // Show tutorial
            self.show_env_var_tutorial()?;
        },
        5 => {
            return Err(anyhow!("Operation cancelled by user"));
        },
        _ => {
            return Err(anyhow!("Invalid choice"));
        }
    }

    Ok(Action::Handled)
}
```

### Pre-Commit Hook

**Install git hook to block commits with secrets:**

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running xSwarm security scan..."

# Get list of files to be committed
FILES=$(git diff --cached --name-only --diff-filter=ACM)

# Scan each file
for FILE in $FILES; do
    if xswarm security scan "$FILE"; then
        echo "✓ $FILE: No secrets detected"
    else
        echo "✗ $FILE: Contains secrets"
        echo ""
        echo "Commit BLOCKED. Remove secrets before committing."
        exit 1
    fi
done

echo "Security scan passed. Proceeding with commit."
exit 0
```

---

## Cross-Project Isolation

### Project Context Switching

```rust
pub async fn switch_project_context(
    &mut self,
    from: ProjectId,
    to: ProjectId
) -> Result<()> {
    // 1. Save current project context
    self.save_project_context(from).await?;

    // 2. PURGE working memory
    self.memory.purge_all_memory();

    // 3. PURGE cached secrets (if any lingered)
    self.secret_cache.clear();

    // 4. Load new project context (filtered)
    let context = self.load_project_context(to).await?;
    let filtered_context = self.filter_secrets(context);
    self.memory.load_context(filtered_context);

    // 5. Log the switch for audit
    audit_log!(
        event = "project_context_switch",
        from_project = %from,
        to_project = %to,
        timestamp = %Utc::now(),
    );

    Ok(())
}
```

### Rules-Based Filtering

```rust
pub struct SecurityRules {
    rules: Vec<SecurityRule>,
}

pub struct SecurityRule {
    name: &'static str,
    condition: Box<dyn Fn(&Context) -> bool>,
    action: Action,
}

pub enum Action {
    Block,           // Refuse operation
    Redact,          // Remove secrets, continue
    Warn,            // Alert user, continue
    Log,             // Log only, continue
}

// Example rules
let rules = vec![
    SecurityRule {
        name: "block_secrets_in_api_calls",
        condition: Box::new(|ctx| {
            ctx.operation_type == OpType::ExternalAPI &&
            contains_secret(&ctx.data)
        }),
        action: Action::Block,
    },
    SecurityRule {
        name: "redact_secrets_cross_project",
        condition: Box::new(|ctx| {
            ctx.operation_type == OpType::CrossProject &&
            contains_secret(&ctx.data)
        }),
        action: Action::Redact,
    },
    SecurityRule {
        name: "warn_secrets_in_logs",
        condition: Box::new(|ctx| {
            ctx.operation_type == OpType::Logging &&
            might_contain_secret(&ctx.data)
        }),
        action: Action::Warn,
    },
];
```

---

## Audit Logging

### What Gets Logged

**All security-relevant events:**

```rust
pub enum SecurityEvent {
    SecretDetected {
        secret_type: String,
        location: String,
        severity: Severity,
        action_taken: Action,
    },
    SecretRedacted {
        secret_type: String,
        context: String,
    },
    MemoryPurged {
        messages_purged: usize,
        reason: PurgeReason,
    },
    ProjectSwitched {
        from: ProjectId,
        to: ProjectId,
    },
    WarningIgnored {
        warning_type: String,
        file: PathBuf,
        user_reason: Option<String>,
    },
    CommitBlocked {
        file: PathBuf,
        secret_type: String,
    },
}
```

### Audit Log Format

```rust
pub struct AuditLog {
    timestamp: DateTime<Utc>,
    event: SecurityEvent,
    user: String,
    machine: String,
    session_id: Uuid,
}

impl AuditLog {
    pub fn write(&self) -> Result<()> {
        let log_path = dirs::config_dir()
            .unwrap()
            .join("xswarm/audit.log");

        let entry = json!({
            "timestamp": self.timestamp.to_rfc3339(),
            "event": format!("{:?}", self.event),
            "user": self.user,
            "machine": self.machine,
            "session_id": self.session_id,
        });

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)?;

        writeln!(file, "{}", serde_json::to_string(&entry)?)?;

        Ok(())
    }
}
```

**Example log entry:**
```json
{
  "timestamp": "2025-10-17T14:23:45Z",
  "event": "SecretDetected { secret_type: \"OpenAI API Key\", location: \"src/config.rs:42\", severity: Critical, action_taken: Block }",
  "user": "chad",
  "machine": "overlord",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Tamper Detection

**Audit log is append-only and includes checksums:**

```rust
pub struct AuditLogEntry {
    timestamp: DateTime<Utc>,
    event: SecurityEvent,
    previous_hash: String,  // SHA256 of previous entry
}

impl AuditLogEntry {
    fn compute_hash(&self) -> String {
        let data = format!("{:?}{:?}{}",
            self.timestamp,
            self.event,
            self.previous_hash
        );
        format!("{:x}", sha2::Sha256::digest(data.as_bytes()))
    }

    fn verify_chain(entries: &[AuditLogEntry]) -> bool {
        for window in entries.windows(2) {
            let prev_hash = window[0].compute_hash();
            if window[1].previous_hash != prev_hash {
                return false;  // Chain broken, possible tampering
            }
        }
        true
    }
}
```

---

## Security CLI Commands

```bash
# Scan a file for secrets
xswarm security scan <file>

# Scan entire project
xswarm security scan-project <project-name>

# Check audit log integrity
xswarm security verify-audit-log

# Manually purge memory
xswarm security purge-memory

# Show current security status
xswarm security status

# Install pre-commit hook
xswarm security install-hooks
```

---

## Configuration

**~/.config/xswarm/security.toml**

```toml
[detection]
# Enable/disable secret detection
enabled = true

# Minimum severity to warn on
min_severity = "medium"  # low, medium, high, critical

# Custom patterns (in addition to built-in)
custom_patterns = [
    { name = "Internal Token", regex = "INT-[0-9]{16}", severity = "high" },
]

[memory]
# Purge interval in seconds
purge_interval = 60

# Max messages in working memory
max_working_memory = 20

# Aggressive purging (slower, more secure)
aggressive_purge = true

[monitoring]
# Monitor file writes
file_monitoring = true

# Monitor git operations
git_monitoring = true

# Block commits with secrets
block_commits = true

[warnings]
# Show warnings in terminal
terminal_warnings = true

# Show desktop notifications
desktop_notifications = true

# Interactive prompts for resolutions
interactive_resolution = true

[audit]
# Enable audit logging
enabled = true

# Audit log path
log_path = "~/.config/xswarm/audit.log"

# Rotate log after size (MB)
rotate_size = 100

# Verify chain on startup
verify_on_startup = true
```

---

## Security Best Practices for Users

### DO:
✅ Use environment variables for secrets (`.env` files)
✅ Add `.env` to `.gitignore`
✅ Use secret management tools (1Password, Vault)
✅ Rotate secrets regularly
✅ Review xSwarm security warnings immediately
✅ Keep audit logs for compliance
✅ Use project-specific `.env` files

### DON'T:
❌ Commit secrets to version control
❌ Store secrets in code comments
❌ Ignore security warnings
❌ Share `.env` files
❌ Use production secrets in development
❌ Disable security features

### Recommended `.env` Setup

```bash
# .env (add to .gitignore!)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://...

# .env.example (commit this)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=postgresql://user:pass@host/db
```

---

## Reporting Security Issues

If you discover a security vulnerability in xSwarm-boss:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: security@xswarm.ai (or create private security advisory)
3. Include: Description, reproduction steps, potential impact
4. We will respond within 48 hours
5. We will credit you in the security advisory (if desired)

---

## Future Enhancements

- [ ] Integration with 1Password/Bitwarden for secret management
- [ ] Machine learning-based secret detection (fewer false positives)
- [ ] Secrets rotation helper commands
- [ ] Integration with GitHub Secret Scanning
- [ ] SIEM integration for enterprise audit logging
- [ ] Per-project security policies
- [ ] Encrypted secrets store (vault mode)

---

## Questions?

Open an issue or discussion on GitHub for security policy questions.
