# xSwarm Boss - Production Deployment Documentation

**Complete Production Deployment Guide Index**

---

## Overview

This directory contains comprehensive documentation for deploying xSwarm Boss to production. All guides have been created for the current production architecture as of **October 2025-10-28**.

---

## Documentation Index

### 🚀 Essential Deployment Guides

#### 1. [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md)
**Hardware and software requirements for production deployment**

- Minimum and recommended specifications
- Cloud provider recommendations
- Cost estimates for different scales (10, 100, 1,000+ users)
- GPU requirements for MOSHI voice processing
- Network and storage requirements

**Start here** to plan your infrastructure.

---

#### 2. [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
**Step-by-step production deployment guide**

- Pre-deployment checklist
- Infrastructure setup (Cloudflare, Turso, Twilio, etc.)
- Environment configuration
- Server deployment (Cloudflare Workers)
- Client deployment (Rust + MOSHI)
- Post-deployment verification

**This is your main deployment guide.** Follow this step-by-step to deploy xSwarm Boss to production.

---

### 📊 Operational Guides

#### 3. [MONITORING_GUIDE.md](./MONITORING_GUIDE.md)
**Monitoring, logging, and operational procedures**

- Health check endpoints
- Log configuration and analysis
- Metrics and analytics
- Alerting setup
- Performance monitoring
- Backup and recovery procedures
- Scaling procedures

**Use this** for day-to-day operations and monitoring.

---

#### 4. [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)
**Comprehensive troubleshooting for common issues**

- Quick diagnostics checklist
- Server issues (Cloudflare Workers)
- Client issues (Rust)
- MOSHI voice processing problems
- Database issues (Turso)
- Webhook problems
- Performance issues
- Recovery procedures

**Consult this** when things go wrong.

---

### 🔒 Security & Configuration

#### 5. [SECURITY_GUIDE.md](./SECURITY_GUIDE.md)
**Security best practices and configuration**

- API security (authentication, rate limiting)
- Network security (firewall, DDoS protection)
- Data protection (encryption at rest/in transit)
- Access control (permissions, API key rotation)
- Secrets management
- SSL/TLS configuration
- GDPR compliance
- Incident response procedures

**Review this** before deploying to production and regularly for security updates.

---

### ⚙️ Configuration Files

#### 6. [config/production.toml](../config/production.toml)
**Production configuration template**

- Complete production-ready config.toml
- All settings documented with comments
- Environment-specific configurations
- Feature flags and performance tuning
- Security settings

**Copy and customize** this for your production deployment.

---

### 🔧 Automation & Tools

#### 7. [scripts/deploy.sh](../scripts/deploy.sh)
**Automated deployment script**

- Pre-flight checks
- Server and client deployment
- Backup creation
- Post-deployment verification
- Health checks
- Rollback procedures

**Usage:**
```bash
# Deploy both server and client
./scripts/deploy.sh

# Deploy only server
./scripts/deploy.sh --server-only

# Deploy only client
./scripts/deploy.sh --client-only

# Force deployment without prompts
./scripts/deploy.sh --force

# Skip tests (not recommended)
./scripts/deploy.sh --skip-tests
```

---

#### 8. [systemd/](../systemd/)
**Linux service management files**

- `xswarm-voice.service` - Voice Bridge service
- `xswarm-dashboard.service` - Supervisor Dashboard service
- `README.md` - Installation and management guide

**Provides:**
- Automatic startup on boot
- Automatic restart on failure
- Resource limits (CPU, memory)
- Logging to systemd journal
- Security hardening

**See:** [systemd/README.md](../systemd/README.md) for installation instructions.

---

## Quick Start

### For First-Time Deployment

1. **Plan infrastructure:**
   ```bash
   # Read system requirements
   cat planning/SYSTEM_REQUIREMENTS.md
   ```

2. **Deploy to production:**
   ```bash
   # Follow step-by-step guide
   cat planning/PRODUCTION_DEPLOYMENT.md

   # Or use automation script
   ./scripts/deploy.sh
   ```

3. **Set up monitoring:**
   ```bash
   # Configure health checks and alerts
   cat planning/MONITORING_GUIDE.md
   ```

4. **Review security:**
   ```bash
   # Harden security before going live
   cat planning/SECURITY_GUIDE.md
   ```

---

### For Updates & Maintenance

1. **Before updates:**
   ```bash
   # Create backup
   ./scripts/deploy.sh --help  # Shows backup location
   ```

2. **Deploy updates:**
   ```bash
   # Deploy new version
   git pull
   ./scripts/deploy.sh
   ```

3. **Monitor after deployment:**
   ```bash
   # Watch logs for issues
   cd packages/server && pnpm tail
   sudo journalctl -u xswarm-voice -f
   ```

4. **Rollback if needed:**
   ```bash
   # Server rollback
   cd packages/server
   pnpm wrangler deployments list
   pnpm wrangler rollback <deployment-id>

   # Client rollback
   sudo cp /opt/xswarm/backups/latest/* /opt/xswarm/target/release/
   sudo systemctl restart xswarm-voice xswarm-dashboard
   ```

---

### For Troubleshooting

```bash
# Quick health check
curl https://xswarm-webhooks.your-subdomain.workers.dev/health
curl http://localhost:9998/health
curl http://localhost:9999/health

# Check service status
sudo systemctl status xswarm-voice
sudo systemctl status xswarm-dashboard

# View logs
cd packages/server && pnpm tail
sudo journalctl -u xswarm-voice -f

# Full troubleshooting guide
cat planning/TROUBLESHOOTING_GUIDE.md
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Cloudflare Workers (Serverless)                            │
│  - Port: 443 (HTTPS)                                        │
│  - SMS webhooks (Twilio)                                    │
│  - Email webhooks (SendGrid)                                │
│  - Voice call webhooks (Twilio)                             │
│  - Payment webhooks (Stripe)                                │
│  - Identity API for Rust client                             │
│  - Database: Turso (libsql)                                 │
│  - Storage: Cloudflare R2                                   │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTPS
┌─────────────────────────────────────────────────────────────┐
│  Rust Client (Self-Hosted)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Voice Bridge (Port 9998)                           │   │
│  │  - WebSocket server                                 │   │
│  │  - MOSHI voice processing                           │   │
│  │  - Real-time audio streaming                        │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Supervisor Dashboard (Port 9999)                   │   │
│  │  - WebSocket server                                 │   │
│  │  - Real-time monitoring TUI                         │   │
│  │  - System metrics and status                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Technologies

### Server Stack
- **Cloudflare Workers** - Serverless compute (Node.js)
- **Turso** - Distributed SQLite database (libsql)
- **Cloudflare R2** - S3-compatible object storage

### Client Stack
- **Rust** - System programming language
- **MOSHI (Kyutai Labs)** - AI voice model (7B parameters)
- **MLX** - Apple Silicon GPU acceleration
- **Python** - MOSHI voice bridge

### External Services
- **Twilio** - Voice calls and SMS
- **SendGrid** - Email delivery
- **Stripe** - Payment processing
- **Anthropic** - Claude AI (text processing)

---

## Deployment Checklist

### Before Deployment

- [ ] Read [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md)
- [ ] Provision required accounts (Cloudflare, Turso, Twilio, etc.)
- [ ] Prepare hardware (Mac or Linux GPU server)
- [ ] Review [SECURITY_GUIDE.md](./SECURITY_GUIDE.md)
- [ ] Configure custom domain (optional but recommended)

### During Deployment

- [ ] Follow [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) step-by-step
- [ ] Configure production config.toml
- [ ] Set up all secrets in .env
- [ ] Deploy Cloudflare Workers
- [ ] Build and deploy Rust client
- [ ] Install systemd services (Linux)
- [ ] Configure webhooks (Twilio, Stripe)
- [ ] Set up SSL/TLS certificates

### After Deployment

- [ ] Test all health endpoints
- [ ] Test voice call functionality
- [ ] Test SMS functionality
- [ ] Test email functionality
- [ ] Test payment flow (Stripe)
- [ ] Set up monitoring and alerts
- [ ] Configure backup schedules
- [ ] Document deployment (server URLs, credentials)
- [ ] Review [MONITORING_GUIDE.md](./MONITORING_GUIDE.md)

---

## Cost Estimates

### Small (10 users)
- Infrastructure: $0/month (free tiers)
- Communication: $7/month (Twilio)
- Hardware: M1 Mac Mini ($599 one-time)
- **Total: ~$7/month + hardware**

### Medium (100 users)
- Infrastructure: $0/month (free tiers)
- Communication: $88/month (Twilio + SendGrid)
- Payments: $30/month (Stripe fees)
- Hardware: M2 Pro Mac Mini ($1,299 one-time) or Cloud GPU ($150/month)
- **Total: ~$118/month + hardware**

### Large (1,000 users)
- Infrastructure: $49/month (Cloudflare + Turso + R2)
- Communication: $770/month (Twilio + SendGrid)
- Payments: $300/month (Stripe fees)
- Hardware: 3x GPU servers (~$600/month)
- **Total: ~$1,719/month**
- **Revenue: $9,990/month (1,000 users × $9.99)**
- **Profit: ~$8,271/month**

See [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md) for detailed cost breakdown.

---

## Support

### Documentation
- Full documentation: [planning/](.)
- Code examples: [packages/](../packages/)
- Configuration: [config/](../config/)

### Issues
- GitHub: [xswarm-dev/xswarm-boss/issues](https://github.com/xswarm-dev/xswarm-boss/issues)
- Include logs and system info
- Follow issue template

### Emergency
- Follow [Incident Response](./SECURITY_GUIDE.md#incident-response) procedures
- Check [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)
- Use [Recovery Procedures](./TROUBLESHOOTING_GUIDE.md#recovery-procedures)

---

## Updates & Maintenance

### Regular Maintenance

**Weekly:**
- Check health endpoints
- Review error logs
- Monitor resource usage

**Monthly:**
- Review security logs
- Test backup restoration
- Check for dependency updates
- Rotate API keys (as needed)

**Quarterly:**
- Review and update documentation
- Conduct security audit
- Review scaling needs
- Update disaster recovery plan

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2025-10-28 | Initial production deployment documentation |

---

## Contributing

Improvements to deployment documentation are welcome!

1. Test your changes in staging environment
2. Update relevant documentation files
3. Submit pull request with clear description
4. Include deployment notes if applicable

---

## License

See [LICENSE](../LICENSE) file in repository root.

---

**Last Updated:** 2025-10-28
**Maintained By:** xSwarm Development Team
**Documentation Version:** 1.0.0

---

## Next Steps

1. Start with [SYSTEM_REQUIREMENTS.md](./SYSTEM_REQUIREMENTS.md)
2. Follow [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
3. Configure [MONITORING_GUIDE.md](./MONITORING_GUIDE.md)
4. Review [SECURITY_GUIDE.md](./SECURITY_GUIDE.md)
5. Bookmark [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md)

**Ready to deploy?** Start here: [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md)
