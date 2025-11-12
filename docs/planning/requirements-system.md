# xSwarm Boss - System Requirements

**Production Deployment Hardware & Software Requirements**

---

## Overview

xSwarm Boss is a hybrid architecture combining serverless webhooks (Node.js on Cloudflare Workers) with a Rust-based client for voice/AI processing. This document outlines minimum and recommended specifications for production deployment.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│  Cloudflare Workers (Serverless)                        │
│  - SMS Webhooks (Twilio)                                │
│  - Email Webhooks (SendGrid)                            │
│  - Voice Call Webhooks (Twilio)                         │
│  - Stripe Payment Webhooks                              │
│  - Identity API for Rust Client                         │
│  - No hardware requirements (fully managed)             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Rust Client (Self-Hosted)                              │
│  - Voice Bridge (Port 9998)                             │
│  - Supervisor Dashboard (Port 9999)                     │
│  - TUI Monitoring Interface                             │
│  - MOSHI Voice Processing                               │
│  - Requires: CPU/GPU, RAM, Storage                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  External Services (Cloud)                              │
│  - Turso Database (managed libsql)                      │
│  - Cloudflare R2 (S3-compatible storage)                │
│  - Twilio (voice/SMS provider)                          │
│  - SendGrid (email provider)                            │
│  - Stripe (payment processor)                           │
└─────────────────────────────────────────────────────────┘
```

---

## Server Requirements (Cloudflare Workers)

### Cloudflare Workers - Node.js Webhook Server

**Type**: Serverless (fully managed)
**Hardware**: N/A (provided by Cloudflare)
**Maintenance**: Zero (auto-scaling, global CDN)

**Free Tier Limits:**
- 100,000 requests/day (3M/month)
- 10ms CPU time per request
- 128MB memory per request
- Unlimited Workers scripts

**Paid Tier ($5/month):**
- 10 million requests/month included
- $0.50 per additional million
- 50ms CPU time per request
- 128MB memory per request

**Estimated Usage:**
```
Assumptions: 100 users
- 10 voice calls/user/month    = 1,000 requests
- 20 SMS messages/user/month   = 2,000 requests
- 5 email events/user/month    = 500 requests
- 2 Stripe events/user/month   = 200 requests

Total: ~3,700 requests/month (well under free tier)
```

**Requirements:**
- Cloudflare account (free)
- Wrangler CLI (included in project)
- No server hardware needed

---

## Client Requirements (Rust + MOSHI)

### Minimum Specifications (Development/Testing)

**Operating System:**
- macOS 14+ (Sonoma or later) - Apple Silicon (M1/M2/M3/M4)
- Linux: Ubuntu 22.04+, Debian 12+, Fedora 38+
- Windows: Windows 11 (WSL2 recommended for development)

**CPU:**
- Apple Silicon: M1 or newer (Metal GPU acceleration)
- Linux/Windows: x86_64 with AVX2 support
- Minimum: 4 cores / 8 threads
- Recommended: 6+ cores / 12+ threads

**Memory:**
- Minimum: 8GB RAM
- Recommended: 16GB RAM
- Required for MOSHI: ~4GB (model) + 4GB (inference)

**Storage:**
- Minimum: 20GB available space
- Recommended: 50GB+ (for model cache, logs, backups)
- MOSHI models: ~4GB
- HuggingFace cache: Variable (~10GB over time)
- Database backups: ~100MB/month

**Network:**
- Minimum: 10 Mbps upload/download
- Recommended: 50+ Mbps for production voice calls
- Latency: <100ms to Cloudflare edge preferred
- Required ports: 9998 (voice), 9999 (supervisor), 8787 (local dev)

---

### Recommended Specifications (Production)

**Operating System:**
- **Preferred**: macOS 14+ (Apple Silicon) - Best MOSHI performance
- **Alternative**: Ubuntu 22.04 LTS Server - CUDA GPU required
- **Not recommended**: Windows (WSL2 overhead, limited GPU support)

**CPU:**
- Apple Silicon: M2 Pro or higher (for production load)
- Linux: AMD Ryzen 9 / Intel Xeon with 8+ cores
- **Important**: MOSHI on CPU is ~5x slower than GPU

**GPU (Highly Recommended for Production):**

**Apple Silicon (Preferred):**
- M2 Pro (16GB unified): 5-10 concurrent calls
- M2 Max (32GB unified): 10-20 concurrent calls
- M3/M4 Pro/Max: Similar performance
- **Advantage**: Metal acceleration built-in, low power, zero setup

**Linux NVIDIA (Alternative):**
- RTX 3060 (12GB VRAM): 5-10 concurrent calls
- RTX 4070 (12GB VRAM): 10-15 concurrent calls
- RTX 4090 (24GB VRAM): 20+ concurrent calls
- **Requirement**: CUDA 12.0+, cuDNN 8.9+, NVIDIA drivers 535+

**Memory:**
- Minimum: 16GB RAM
- Recommended: 32GB RAM
- **Per concurrent call**: ~500MB RAM overhead
- **MOSHI baseline**: 4GB (model) + 4GB (inference)

**Storage:**
- Minimum: 100GB SSD
- Recommended: 500GB NVMe SSD
- **Performance impact**: Model loading from NVMe is 3-5x faster than HDD
- **IOPS**: 3000+ recommended for model streaming

**Network:**
- Minimum: 100 Mbps dedicated
- Recommended: 1 Gbps dedicated
- **Latency**: <50ms to major CDN edge (Cloudflare, Twilio)
- **Bandwidth per call**: ~50 kbps (MOSHI codec at 1.1kbps + overhead)

---

## Cloud Service Requirements

### Turso Database

**Type**: Managed libsql (SQLite-compatible)
**Free Tier:**
- 9 GB total storage
- 1 billion row reads/month
- 25 million row writes/month
- 3 databases

**Estimated Usage:**
```
100 users:
- User data: ~10 KB/user = 1 MB
- Logs: ~100 KB/user/month = 10 MB/month
- Backups: ~50 MB (30-day retention)

Total: <100 MB storage, <1M row reads/month
Cost: $0/month (well under free tier)
```

**Requirements:**
- Turso account (free)
- Primary region: Choose closest to users (e.g., `pdx`, `iad`, `fra`)
- Replica regions: Optional for global edge caching

---

### Cloudflare R2 Storage

**Type**: S3-compatible object storage
**Free Tier:**
- 10 GB storage/month
- 1 million Class A operations (writes)
- 10 million Class B operations (reads)
- Zero egress fees (unlimited downloads)

**Estimated Usage:**
```
100 users:
- Assets: ~50 MB (personas, audio samples)
- Backups: ~100 MB (database dumps, configs)
- Logs: ~50 MB/month

Total: ~200 MB storage, <10K writes/month, <100K reads/month
Cost: $0/month (well under free tier)
```

**Requirements:**
- Cloudflare account (free)
- R2 bucket created
- API token with R2 read/write permissions

---

### Twilio (Voice & SMS)

**Type**: Communication platform
**Free Trial:**
- $15 credit for testing
- Test numbers included

**Production Costs:**
- Toll-free number: $2/month
- Voice calls: $0.013/minute (incoming)
- SMS messages: $0.0075/message (incoming)

**Estimated Usage:**
```
100 users:
- Voice: 10 calls/user/month, 5 min avg = 5,000 minutes
- SMS: 20 messages/user/month = 2,000 messages

Cost: $200/month (numbers) + $65/month (voice) + $15/month (SMS)
Total: ~$280/month
```

**Requirements:**
- Twilio account
- Verified phone numbers
- Webhook endpoints configured

---

### SendGrid (Email)

**Type**: Email delivery platform
**Free Tier:**
- 100 emails/day
- Single sender verification

**Paid Plans:**
- Essentials: $19.95/month (50,000 emails)
- Pro: $89.95/month (100,000 emails)

**Estimated Usage:**
```
100 users:
- Welcome emails: 100 one-time
- Notifications: 5/user/month = 500 emails/month
- Marketing: 10/user/month = 1,000 emails/month

Total: ~1,500 emails/month
Cost: $0/month (free tier sufficient) or $19.95/month for scaling
```

**Requirements:**
- SendGrid account
- Domain verification (SPF, DKIM)
- Sender authentication

---

### Stripe (Payments)

**Type**: Payment processing
**Free Tier:**
- No monthly fee (pay per transaction)

**Transaction Fees:**
- Online payments: 2.9% + $0.30 per transaction
- Subscription billing: Same as above

**Estimated Revenue:**
```
100 users on premium ($9.99/month):
- Monthly revenue: $999
- Stripe fees: 2.9% + $0.30 = ~$30/month

Net revenue: ~$969/month
```

**Requirements:**
- Stripe account (free)
- Business verification
- Bank account for payouts
- Webhook endpoints configured

---

## Software Dependencies

### Rust Client (xswarm)

**Rust Toolchain:**
- Rust 1.70+ (stable channel)
- Cargo package manager
- Rustup (for toolchain management)

**System Libraries (macOS):**
```bash
# Audio I/O
brew install portaudio

# TLS support
# (Built into macOS)

# Optional: Database CLI
brew install turso-cli
```

**System Libraries (Linux):**
```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  pkg-config \
  libssl-dev \
  portaudio19-dev \
  libasound2-dev

# Fedora
sudo dnf install -y \
  gcc \
  pkg-config \
  openssl-devel \
  portaudio-devel \
  alsa-lib-devel
```

**Python Dependencies (MOSHI):**
- Python 3.10+
- pip or uv (package manager)
- virtualenv (recommended)

**Required Python Packages:**
```
moshi-mlx==0.3.0          # MOSHI voice model
mlx==0.26.5               # Apple MLX framework
mlx-metal==0.26.5         # Metal GPU acceleration (macOS)
rustymimi==0.4.1          # Mimi audio codec
sounddevice==0.5.0        # Audio I/O
websockets==12.0          # WebSocket server
```

**NVIDIA CUDA (Linux only):**
- CUDA Toolkit 12.0+
- cuDNN 8.9+
- NVIDIA driver 535+

---

### Node.js Server (Cloudflare Workers)

**Local Development:**
- Node.js 18+ LTS
- pnpm 8+ (package manager)
- Wrangler CLI (installed via pnpm)

**Production:**
- No Node.js installation needed (runs on Cloudflare)
- Wrangler CLI for deployment

---

## Network Requirements

### Firewall Rules (Inbound)

**Rust Client (if exposing publicly):**
```
Port 9998 (TCP)  - Voice Bridge WebSocket
Port 9999 (TCP)  - Supervisor WebSocket
```

**Development Server:**
```
Port 8787 (TCP)  - Node.js server (local dev only)
```

**Cloudflare Workers:**
- No firewall rules needed (serverless)
- Automatic HTTPS on port 443

### Required Outbound Access

**Rust Client:**
```
api.anthropic.com:443      - Claude API
api.openai.com:443         - OpenAI API
api.twilio.com:443         - Twilio API
huggingface.co:443         - Model downloads
*.workers.dev:443          - Cloudflare Workers (server)
*.turso.io:443             - Turso database
```

**Cloudflare Workers:**
```
*.turso.io:443             - Turso database
*.r2.cloudflarestorage.com - R2 storage
api.twilio.com:443         - Twilio API
api.sendgrid.com:443       - SendGrid API
api.stripe.com:443         - Stripe API
```

---

## SSL/TLS Requirements

### Cloudflare Workers
- **Automatic**: Cloudflare provides SSL certificates
- **Custom domain**: Free SSL via Cloudflare Universal SSL
- **Configuration**: Zero (handled by platform)

### Rust Client
- **WebSocket connections**: Can use `wss://` for encryption
- **Local development**: `ws://` acceptable
- **Production**: Reverse proxy (nginx) recommended for SSL termination

---

## Performance Benchmarks

### MOSHI Voice Processing

**Latency Targets:**
- Theoretical minimum: 160ms (frame + acoustic delay)
- Practical target: <200ms end-to-end
- Acceptable: <300ms for production

**Hardware Performance:**

| Hardware | Latency | Concurrent Calls |
|----------|---------|------------------|
| M1 MacBook Air (CPU) | 400-600ms | 1-2 |
| M1 MacBook Air (GPU) | 180-220ms | 2-4 |
| M2 Pro (GPU) | 160-200ms | 5-10 |
| M2 Max (GPU) | 160-200ms | 10-20 |
| RTX 3060 (12GB) | 170-210ms | 5-10 |
| RTX 4090 (24GB) | 160-190ms | 20+ |

**Bottlenecks:**
- CPU-only: 5-10x slower than GPU
- Memory: Each call needs ~500MB
- Network: Voice quality degrades above 100ms network latency

---

## Scaling Considerations

### Horizontal Scaling (Multiple Instances)

**Cloudflare Workers:**
- Automatic global scaling
- No configuration needed
- 330+ edge locations worldwide

**Rust Client:**
- Deploy multiple instances behind load balancer
- Each instance handles N concurrent calls
- Share Turso database (supports edge replication)

**Load Balancer:**
- nginx or HAProxy for WebSocket load balancing
- Sticky sessions recommended (voice call affinity)
- Health check endpoints: `/health` on ports 9998, 9999

### Vertical Scaling (Bigger Hardware)

**Memory:**
- Base: 8GB (1-2 concurrent calls)
- 16GB: 5-10 concurrent calls
- 32GB: 10-20 concurrent calls
- 64GB: 20+ concurrent calls

**GPU VRAM:**
- 8GB: 3-5 concurrent calls
- 12GB: 5-10 concurrent calls
- 24GB: 10-20 concurrent calls
- 48GB: 20+ concurrent calls

---

## Cost Estimate (Monthly)

### Small Deployment (10 users)

**Infrastructure:**
- Cloudflare Workers: $0 (free tier)
- Turso Database: $0 (free tier)
- R2 Storage: $0 (free tier)

**Communication:**
- Twilio (2 numbers): $4/month
- Voice (100 minutes): $1.30/month
- SMS (200 messages): $1.50/month
- SendGrid: $0 (free tier)

**Payments:**
- Stripe fees (on $99 revenue): ~$4/month

**Hardware:**
- M1 Mac Mini: $599 one-time (or use existing Mac)
- OR Cloud GPU (RunPod H100): ~$60/month

**Total: ~$11/month + hardware**

---

### Medium Deployment (100 users)

**Infrastructure:**
- Cloudflare Workers: $0 (free tier sufficient)
- Turso Database: $0 (free tier sufficient)
- R2 Storage: $0 (free tier sufficient)

**Communication:**
- Twilio (20 numbers): $40/month
- Voice (1,000 minutes): $13/month
- SMS (2,000 messages): $15/month
- SendGrid: $19.95/month (paid plan)

**Payments:**
- Stripe fees (on $999 revenue): ~$30/month

**Hardware:**
- M2 Pro Mac Mini: $1,299 one-time
- OR Cloud GPU (RunPod A4000): ~$150/month
- OR Bare metal (Hetzner AX101): €189/month

**Total: ~$118/month + hardware**

---

### Large Deployment (1,000 users)

**Infrastructure:**
- Cloudflare Workers: $5/month (paid plan)
- Turso Database: $29/month (scale plan)
- R2 Storage: $15/month (~1TB)

**Communication:**
- Twilio (200 numbers): $400/month
- Voice (10,000 minutes): $130/month
- SMS (20,000 messages): $150/month
- SendGrid: $89.95/month (pro plan)

**Payments:**
- Stripe fees (on $9,990 revenue): ~$300/month

**Hardware (3x servers for redundancy):**
- 3x bare metal GPU servers: ~€600/month
- OR 3x cloud GPU instances: ~$450/month

**Load Balancer:**
- Cloudflare Load Balancing: $5/month

**Total: ~$1,123/month + hardware (~$450-600/month)**

**Revenue (1,000 users at $9.99/month):**
- Gross: $9,990/month
- Costs: ~$1,700/month
- **Net Profit: ~$8,300/month**

---

## Recommendations

### Development Environment
- **macOS**: M1/M2 MacBook Air (best developer experience)
- **Linux**: Ubuntu 22.04 on AMD Ryzen 7 (budget alternative)
- **Cloud**: Not recommended for development (high latency, costs)

### Production Environment
- **Best**: M2 Pro/Max Mac Mini (low power, zero setup, great performance)
- **Alternative**: Bare metal GPU server (Hetzner, OVH) for higher scale
- **Avoid**: Consumer desktop GPUs (reliability concerns), Windows (compatibility issues)

### Scaling Strategy
1. Start: Single M1/M2 Mac (10-50 users)
2. Grow: M2 Pro/Max Mac (50-200 users)
3. Scale: Multiple GPU servers + load balancer (200+ users)
4. Enterprise: Kubernetes + GPU nodes (1,000+ users)

---

## Related Documentation

- [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) - Deployment guide
- [MONITORING_GUIDE.md](./MONITORING_GUIDE.md) - Operations and monitoring
- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - Security configuration
- [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) - Common issues

---

**Last Updated**: 2025-10-28
**Next Review**: When adding new features or scaling beyond 1,000 users
