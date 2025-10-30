# xSwarm systemd Service Files

**Production service management for Linux servers**

---

## Overview

These systemd service files provide automatic startup, restart, and resource management for xSwarm services on Linux production servers.

---

## Services

### xswarm-voice.service
- **Purpose**: Voice Bridge - WebSocket server for MOSHI voice processing
- **Port**: 9998
- **Dependencies**: network-online.target
- **Resource limits**: 16GB RAM, 4 CPU cores
- **Auto-restart**: Yes (10 second delay)

### xswarm-dashboard.service
- **Purpose**: Supervisor Dashboard - Real-time monitoring TUI
- **Port**: 9999
- **Dependencies**: xswarm-voice.service, network-online.target
- **Resource limits**: 1GB RAM, 1 CPU core
- **Auto-restart**: Yes (10 second delay)

---

## Installation

### 1. Create xswarm User

```bash
# Create system user for running services
sudo useradd -r -s /bin/false -d /opt/xswarm xswarm

# Create required directories
sudo mkdir -p /opt/xswarm
sudo mkdir -p /var/lib/xswarm
sudo mkdir -p /var/log/xswarm

# Set ownership
sudo chown -R xswarm:xswarm /opt/xswarm
sudo chown -R xswarm:xswarm /var/lib/xswarm
sudo chown -R xswarm:xswarm /var/log/xswarm
```

---

### 2. Install Application

```bash
# Clone repository
cd /opt/xswarm
sudo -u xswarm git clone https://github.com/xswarm-dev/xswarm-boss.git .

# Build release binaries
sudo -u xswarm cargo build --release

# Create .env file with secrets
sudo -u xswarm nano /opt/xswarm/.env
# (Copy from .env.example and fill in secrets)

# Create config.toml
sudo -u xswarm cp config/production.toml /opt/xswarm/config.toml
sudo -u xswarm nano /opt/xswarm/config.toml
# (Update with production values)
```

---

### 3. Install Service Files

```bash
# Copy service files to systemd directory
sudo cp systemd/*.service /etc/systemd/system/

# Reload systemd to recognize new services
sudo systemctl daemon-reload

# Verify services are recognized
systemctl list-unit-files | grep xswarm
```

**Expected output:**
```
xswarm-voice.service      disabled
xswarm-dashboard.service  disabled
```

---

### 4. Enable and Start Services

```bash
# Enable services (start on boot)
sudo systemctl enable xswarm-voice
sudo systemctl enable xswarm-dashboard

# Start services
sudo systemctl start xswarm-voice
sudo systemctl start xswarm-dashboard

# Check status
sudo systemctl status xswarm-voice
sudo systemctl status xswarm-dashboard
```

**Healthy output:**
```
● xswarm-voice.service - xSwarm Voice Bridge
   Loaded: loaded (/etc/systemd/system/xswarm-voice.service; enabled)
   Active: active (running) since Mon 2025-10-28 10:30:00 UTC; 5min ago
 Main PID: 12345 (xswarm-voice)
   Status: "Voice bridge running (0 active calls)"
    Tasks: 12 (limit: 1024)
   Memory: 2.1G (max: 16.0G)
   CGroup: /system.slice/xswarm-voice.service
           └─12345 /opt/xswarm/target/release/xswarm-voice
```

---

## Service Management

### Start/Stop Services

```bash
# Start
sudo systemctl start xswarm-voice
sudo systemctl start xswarm-dashboard

# Stop
sudo systemctl stop xswarm-voice
sudo systemctl stop xswarm-dashboard

# Restart
sudo systemctl restart xswarm-voice
sudo systemctl restart xswarm-dashboard

# Reload configuration (without restarting)
sudo systemctl reload xswarm-voice
```

---

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable xswarm-voice
sudo systemctl enable xswarm-dashboard

# Disable (don't start on boot)
sudo systemctl disable xswarm-voice
sudo systemctl disable xswarm-dashboard
```

---

### View Logs

```bash
# Real-time logs
sudo journalctl -u xswarm-voice -f
sudo journalctl -u xswarm-dashboard -f

# Last 100 lines
sudo journalctl -u xswarm-voice -n 100
sudo journalctl -u xswarm-dashboard -n 100

# Since specific time
sudo journalctl -u xswarm-voice --since "2025-10-28 10:00:00"

# Filter by priority
sudo journalctl -u xswarm-voice -p err  # Errors only
sudo journalctl -u xswarm-voice -p warning  # Warnings and above
```

---

### Check Service Status

```bash
# Detailed status
sudo systemctl status xswarm-voice
sudo systemctl status xswarm-dashboard

# Quick health check
systemctl is-active xswarm-voice    # Returns: active or inactive
systemctl is-enabled xswarm-voice   # Returns: enabled or disabled
systemctl is-failed xswarm-voice    # Returns: active or failed
```

---

## Resource Limits

### Default Limits

**xswarm-voice (Voice processing):**
- Memory: 16GB max, 14GB high-water mark
- CPU: 400% (4 cores)
- Tasks: 1024 max

**xswarm-dashboard (Monitoring):**
- Memory: 1GB max, 512MB high-water mark
- CPU: 100% (1 core)
- Tasks: 256 max

---

### Adjust Resource Limits

Edit service file:
```bash
sudo nano /etc/systemd/system/xswarm-voice.service
```

Modify these lines:
```ini
MemoryMax=16G      # Maximum memory before OOM kill
MemoryHigh=14G     # Throttle CPU at this point
CPUQuota=400%      # Percentage (100% = 1 core, 400% = 4 cores)
```

Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart xswarm-voice
```

---

### Monitor Resource Usage

```bash
# Real-time resource usage
sudo systemctl status xswarm-voice

# Detailed cgroup stats
systemd-cgtop

# Memory breakdown
systemd-cgls /system.slice/xswarm-voice.service
```

---

## Troubleshooting

### Service Fails to Start

**Symptom:**
```
Failed to start xswarm-voice.service: Unit xswarm-voice.service has failed.
```

**Check logs:**
```bash
sudo journalctl -u xswarm-voice -n 50
```

**Common causes:**
1. Missing .env file
   ```bash
   sudo ls -l /opt/xswarm/.env
   ```

2. Wrong permissions
   ```bash
   sudo chown xswarm:xswarm /opt/xswarm/.env
   sudo chmod 600 /opt/xswarm/.env
   ```

3. Binary not found
   ```bash
   sudo ls -l /opt/xswarm/target/release/xswarm-voice
   ```

4. Port already in use
   ```bash
   sudo netstat -tulpn | grep 9998
   ```

---

### Service Keeps Restarting

**Symptom:**
```
Active: activating (auto-restart) (Result: exit-code)
```

**Check restart count:**
```bash
sudo systemctl status xswarm-voice | grep Restart
```

**View crash logs:**
```bash
sudo journalctl -u xswarm-voice --since "5 minutes ago"
```

**Common causes:**
1. Configuration error (check config.toml)
2. Missing dependencies (MOSHI models)
3. Database connection failure
4. Out of memory (check MemoryMax)

**Temporarily disable restart to debug:**
```bash
# Edit service file
sudo systemctl edit --full xswarm-voice.service

# Change Restart=always to Restart=no
# Save and reload
sudo systemctl daemon-reload
sudo systemctl start xswarm-voice

# Check logs without auto-restart interference
```

---

### High Memory Usage

**Check current usage:**
```bash
systemctl status xswarm-voice | grep Memory
```

**If approaching limit:**
1. Reduce `max_concurrent_calls` in config.toml
2. Increase `MemoryMax` in service file
3. Add more RAM to server
4. Deploy multiple instances with load balancer

---

### Service Won't Stop

**Symptom:**
```
Stopping xSwarm Voice Bridge... (30s timeout)
```

**Force stop:**
```bash
# Send SIGKILL after timeout
sudo systemctl kill xswarm-voice

# Or immediately
sudo systemctl kill -s SIGKILL xswarm-voice
```

**Find and kill process manually:**
```bash
ps aux | grep xswarm-voice
sudo kill -9 <PID>
```

---

## Security Hardening

### Current Security Features

**Enabled in service files:**
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolates /tmp directory
- `ProtectSystem=strict` - Makes system directories read-only
- `ProtectHome=read-only` - Makes home directories read-only
- `ReadWritePaths=/var/lib/xswarm /var/log/xswarm` - Only these writable

---

### Additional Hardening (Optional)

Edit service file and add:
```ini
# Restrict network access
RestrictAddressFamilies=AF_INET AF_INET6

# Restrict system calls
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Make /usr, /boot, /etc read-only
ProtectSystem=full

# Deny access to other users' data
PrivateUsers=yes

# Use separate network namespace
PrivateNetwork=yes
```

**Note:** These may break functionality. Test thoroughly.

---

## Backup Before Updates

```bash
# Backup current binaries
sudo cp /opt/xswarm/target/release/xswarm-voice \
        /opt/xswarm/backup/xswarm-voice-$(date +%F)

# Backup service files
sudo cp /etc/systemd/system/xswarm-*.service \
        /opt/xswarm/backup/
```

---

## Rollback Procedure

```bash
# Stop services
sudo systemctl stop xswarm-voice xswarm-dashboard

# Restore previous binaries
sudo cp /opt/xswarm/backup/xswarm-voice-2025-10-27 \
        /opt/xswarm/target/release/xswarm-voice

# Restore previous service files (if changed)
sudo cp /opt/xswarm/backup/xswarm-voice.service \
        /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Restart services
sudo systemctl start xswarm-voice xswarm-dashboard

# Verify
sudo systemctl status xswarm-voice
```

---

## Performance Tuning

### Optimize for Latency (Real-time voice)

```ini
# In service file
CPUSchedulingPolicy=fifo  # Real-time scheduling
CPUSchedulingPriority=99   # Highest priority
Nice=-10                   # Higher CPU priority
```

---

### Optimize for Throughput (Batch processing)

```ini
# In service file
Nice=10                    # Lower CPU priority
IOSchedulingClass=best-effort
IOSchedulingPriority=7     # Lowest I/O priority
```

---

## Multi-Instance Deployment

To run multiple instances (for scaling):

**Create instance-specific service:**
```bash
# Copy service file
sudo cp /etc/systemd/system/xswarm-voice.service \
        /etc/systemd/system/xswarm-voice@.service

# Edit to use instance parameter
# ExecStart=/opt/xswarm/target/release/xswarm-voice --instance %i
```

**Start instances:**
```bash
sudo systemctl start xswarm-voice@1
sudo systemctl start xswarm-voice@2
sudo systemctl start xswarm-voice@3
```

**Configure each instance to use different ports:**
```toml
# config.toml
[voice.bridge]
port = 9998  # Instance 1: 9998, Instance 2: 9999, Instance 3: 10000
```

---

## Related Documentation

- [PRODUCTION_DEPLOYMENT.md](../planning/PRODUCTION_DEPLOYMENT.md) - Full deployment guide
- [MONITORING_GUIDE.md](../planning/MONITORING_GUIDE.md) - Monitoring and logs
- [TROUBLESHOOTING_GUIDE.md](../planning/TROUBLESHOOTING_GUIDE.md) - Detailed troubleshooting

---

**Last Updated**: 2025-10-28
