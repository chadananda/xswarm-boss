# Git LFS + Cloudflare R2 Setup Guide

This repository uses Git LFS (Large File Storage) with Cloudflare R2 as the storage backend. This keeps the repository lightweight while allowing large files like model weights, persona assets, and AI-generated media to be versioned.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Developer Machine                                           │
│                                                              │
│  git push                                                    │
│      │                                                       │
│      ├─→ Small files ──→ GitHub repository                  │
│      │                                                       │
│      └─→ Large files ──→ Git LFS ──→ Cloudflare Workers     │
│                                           │                  │
│                                           ↓                  │
│                                      Cloudflare R2           │
│                                      (lfs/objects/)          │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- **Fast clones**: Only download LFS pointers (~100 bytes each), not full files
- **On-demand downloads**: `git lfs pull` to download actual files when needed
- **Cost-effective**: R2 has 10GB free storage, zero egress costs
- **Versioned assets**: All large files tracked in git history
- **Content-addressed**: Files stored by SHA256 hash, deduplicated automatically

## What Files Are Tracked?

See `.gitattributes` for the complete list. Key file types:

### Model Weights
- `*.safetensors`, `*.bin`, `*.pt`, `*.pth` - PyTorch/MLX model weights
- `*.onnx`, `*.ckpt`, `*.h5` - Other ML formats
- `*.pkl`, `*.pickle` - Serialized Python objects

### Persona Assets
- `*.apng` - Animated icons (e.g., Eye of Sauron)
- `packages/personas/**/*.wav`, `*.mp3`, `*.flac` - Voice samples for TTS cloning
- `packages/personas/**/*.ogg`, `*.m4a` - Other audio formats

### AI/ML Data
- `*.faiss`, `*.index` - Vector database indices
- `*.npy`, `*.npz` - NumPy arrays
- `*.parquet`, `*.arrow` - Large datasets

## Storage Layout

R2 bucket: `xswarm-boss`

```
lfs/objects/
├── ab/
│   └── cd/
│       └── abcdef123...  (SHA256 hash)
├── 01/
│   └── 23/
│       └── 0123456...
...
```

This matches Git LFS convention and enables efficient listing/cleanup.

## Setup for Developers

### 1. Install Git LFS

**macOS (Apple Silicon recommended):**
```bash
# Use ARM Homebrew for native performance
brew install git-lfs

# Verify ARM64 binary
git lfs version
# Expected: git-lfs/3.7.1 (GitHub; darwin arm64; go 1.25.3)
```

**Linux:**
```bash
sudo apt-get install git-lfs  # Debian/Ubuntu
sudo dnf install git-lfs      # Fedora
```

**Windows:**
Download from https://git-lfs.github.com/

### 2. Initialize Git LFS

```bash
git lfs install
```

This adds LFS hooks to your git config.

### 3. Clone Repository

**New clone (recommended):**
```bash
# Clone without downloading LFS files (fast)
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/chadananda/xswarm-boss.git
cd xswarm-boss

# Download only the LFS files you need
git lfs pull --include="packages/personas/sauron/**"  # Just Sauron assets
git lfs pull  # Or download everything
```

**Existing clone:**
```bash
# Your repo is already configured via .lfsconfig
# Just pull LFS files when needed
git lfs pull
```

### 4. Configure Write Access (Optional)

**Read-only access** is configured in `.lfsconfig` (already done).

**For write access** (pushing new LFS files), add to your local git config:

```bash
# Get write token from team lead or Cloudflare dashboard
# Store securely (e.g., 1Password, macOS Keychain)

# Configure local git (NOT committed to repo)
git config --local lfs.url "https://xswarm-webhooks.CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.workers.dev/lfs"
git config --local lfs.https://xswarm-webhooks.CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.workers.dev/lfs.access basic
git config --local credential.https://xswarm-webhooks.CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.workers.dev.username "xswarm"
git config --local credential.https://xswarm-webhooks.CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.workers.dev.helper "!f() { echo \"username=xswarm\"; echo \"password=$LFS_AUTH_TOKEN_WRITE\"; }; f"
```

**Alternative: Use environment variable**
```bash
# Add to ~/.zshrc or ~/.bashrc
export LFS_AUTH_TOKEN_WRITE="your-write-token-here"

# Then configure credential helper
git config --local credential.helper "!f() { echo \"username=xswarm\"; echo \"password=$LFS_AUTH_TOKEN_WRITE\"; }; f"
```

## Usage

### Adding Large Files

Files matching `.gitattributes` patterns are automatically tracked:

```bash
# Just add and commit as normal
cp big-model.safetensors packages/personas/sauron/model.safetensors
git add packages/personas/sauron/model.safetensors
git commit -m "Add Sauron voice model"
git push

# Git LFS handles upload to R2 automatically
```

### Checking LFS Status

```bash
# See which files are LFS-tracked
git lfs ls-files

# See LFS file details
git lfs ls-files --size

# Check LFS environment
git lfs env
```

### Downloading Specific Files

```bash
# Pull specific paths only
git lfs pull --include="packages/personas/sauron/**"

# Pull everything except certain paths
git lfs pull --exclude="packages/personas/wizard/**"
```

### Pruning Old Files

```bash
# Remove old LFS objects from local cache
git lfs prune

# Keep files from last 10 days only
git lfs prune --verify-remote --recent 10
```

## Server Configuration (For Maintainers)

### LFS Authentication Tokens

Two tokens control access:
- `LFS_AUTH_TOKEN_READ` - Read-only (for public clones)
- `LFS_AUTH_TOKEN_WRITE` - Read + write (for contributors)

**Generate secure tokens:**
```bash
# Read token (less sensitive, can be shared)
openssl rand -base64 32

# Write token (keep secret!)
openssl rand -base64 32
```

**Deploy to Cloudflare Workers:**
```bash
cd packages/server

# Set read token (for public access)
pnpm wrangler secret put LFS_AUTH_TOKEN_READ

# Set write token (for contributors)
pnpm wrangler secret put LFS_AUTH_TOKEN_WRITE

# Verify deployment
pnpm wrangler deploy
```

### Testing LFS Server

```bash
# Test health endpoint
curl https://xswarm-webhooks.CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.workers.dev/health

# Test LFS batch API (with auth)
curl -X POST https://xswarm-webhooks.CLOUDFLARE_ACCOUNT_ID_PLACEHOLDER.workers.dev/lfs/objects/batch \
  -H "Authorization: Bearer $LFS_AUTH_TOKEN_READ" \
  -H "Content-Type: application/vnd.git-lfs+json" \
  -d '{
    "operation": "download",
    "objects": [
      {
        "oid": "abc123...",
        "size": 1234567
      }
    ]
  }'
```

## Troubleshooting

### "Authentication required" error

**Problem:** Git LFS push fails with 401 Unauthorized

**Solution:**
1. Verify you have write token: `echo $LFS_AUTH_TOKEN_WRITE`
2. Check credential helper: `git config --local credential.helper`
3. Re-configure write access (see Setup section)

### Files not being tracked

**Problem:** Large file committed as regular git object

**Solution:**
1. Check pattern matches: `git lfs track --dry-run path/to/file.ext`
2. If no match, file is stored in git (bad!)
3. Remove from git: `git rm --cached path/to/file.ext`
4. Add pattern to `.gitattributes`: `*.ext filter=lfs diff=lfs merge=lfs -text`
5. Re-add: `git add path/to/file.ext`

### Slow clones

**Problem:** Clone downloads all LFS files (slow)

**Solution:** Use `GIT_LFS_SKIP_SMUDGE=1` (see Setup section)

### macOS Gatekeeper error

**Problem:** "git-lfs cannot be opened because the developer cannot be verified"

**Solution:**
```bash
# Check if using old x86_64 binary
file $(which git-lfs)

# If x86_64, reinstall with ARM Homebrew
brew reinstall git-lfs

# Verify ARM64
git lfs version
```

## Architecture Details

### Git LFS Batch API

Cloudflare Workers implements Git LFS Batch API v1:
- Spec: https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md
- Endpoints:
  - `POST /lfs/objects/batch` - Negotiate transfers
  - `PUT /lfs/objects/{oid}` - Upload object
  - `GET /lfs/objects/{oid}` - Download object
  - `POST /lfs/verify` - Verify upload (optional)

### Security Model

1. **Authentication**: Bearer tokens in Authorization header
2. **Read tokens**: Accept either read or write token
3. **Write tokens**: Require write token specifically
4. **Object verification**: SHA256 hash in URL prevents tampering
5. **Content-addressed**: Identical files stored once (deduplication)

### Cost Analysis

**Cloudflare R2 Free Tier:**
- 10GB storage
- Zero egress costs
- 1M Class A operations/month (PUT, LIST)
- 10M Class B operations/month (GET, HEAD)

**Estimated usage for xSwarm:**
- Models: ~4GB (MOSHI, voice clones)
- Persona assets: ~500MB (audio samples, animations)
- Total: ~5GB (well within free tier)
- Operations: ~1K/month (low traffic repo)

**Cost: $0/month** 🎉

## Related Files

- `.gitattributes` - LFS file patterns (committed)
- `.lfsconfig` - Read-only LFS endpoint (committed)
- `.git/config` - Local write access (NOT committed)
- `packages/server/src/routes/lfs.js` - LFS server implementation
- `packages/server/wrangler.toml` - R2 bucket binding

## References

- Git LFS: https://git-lfs.github.com/
- Git LFS Spec: https://github.com/git-lfs/git-lfs/tree/main/docs
- Cloudflare R2: https://developers.cloudflare.com/r2/
- Workers Bindings: https://developers.cloudflare.com/workers/runtime-apis/bindings/
