# Dev Mode Quick Start Guide

## New Interactive Login System

No more environment variables! Just run `xswarm --dev` and enter your credentials when prompted.

---

## Quick Test

```bash
# 1. Navigate to project
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss

# 2. Run dev mode
./target/release/xswarm --dev
```

---

## What You'll See

```
🔐 Development Mode Login
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Email: chadananda@gmail.com
Password: ••••••••••••

✅ Login successful!

🚀 DEV MODE - OFFLINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• External services: BYPASSED
• Authentication: BYPASSED
• Supervisor: OFFLINE
• Health checks: DISABLED

📊 Launching dashboard...
```

---

## Your Credentials

Stored in `.env` file at project root:

```env
XSWARM_DEV_ADMIN_EMAIL="chadananda@gmail.com"
XSWARM_DEV_ADMIN_PASS="***REMOVED***"
```

---

## Features

✅ Interactive email/password prompts  
✅ Secure password input (hidden from view)  
✅ No environment variables to set manually  
✅ Clear error messages for invalid credentials  
✅ Dashboard launches automatically after login  

---

## Troubleshooting

### "ERROR: .env file not found"
```bash
cd /Users/chad/Dropbox/Public/JS/Projects/xswarm-boss
# Verify .env exists with your credentials
cat .env | grep XSWARM_DEV
```

### "ERROR: Invalid email"
Make sure you're typing: `chadananda@gmail.com`

### "ERROR: Invalid password"
Make sure you're typing: `***REMOVED***`

---

## Build from Source

If you need to rebuild:

```bash
cd packages/core
cargo build --release
```

Binary will be at: `target/release/xswarm`

---

**That's it!** Much simpler than the old way of setting environment variables.
