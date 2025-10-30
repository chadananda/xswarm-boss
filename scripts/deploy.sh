#!/bin/bash
#
# xSwarm Boss - Production Deployment Script
#
# This script automates the deployment of xSwarm Boss to production.
# It handles both the Cloudflare Workers server and the Rust client.
#
# Usage:
#   ./scripts/deploy.sh [OPTIONS]
#
# Options:
#   --server-only    Deploy only the Cloudflare Workers server
#   --client-only    Deploy only the Rust client
#   --skip-tests     Skip pre-deployment tests
#   --force          Skip confirmation prompts
#   --help           Show this help message
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_SERVER=true
DEPLOY_CLIENT=true
RUN_TESTS=true
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --server-only)
      DEPLOY_CLIENT=false
      shift
      ;;
    --client-only)
      DEPLOY_SERVER=false
      shift
      ;;
    --skip-tests)
      RUN_TESTS=false
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --help)
      head -n 20 "$0" | tail -n +3 | sed 's/^# //; s/^#//'
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Helper functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

confirm() {
  if [ "$FORCE" = true ]; then
    return 0
  fi

  read -p "$1 (yes/no): " response
  case "$response" in
    [yY][eE][sS]|[yY])
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    log_error "$1 is not installed. Please install it first."
    exit 1
  fi
}

# Banner
echo ""
echo "┌─────────────────────────────────────────────────────┐"
echo "│  xSwarm Boss - Production Deployment Script        │"
echo "└─────────────────────────────────────────────────────┘"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# ============================================================================
# Pre-flight Checks
# ============================================================================

log_info "Running pre-flight checks..."

# Check required commands
check_command "git"
check_command "node"
check_command "pnpm"

if [ "$DEPLOY_CLIENT" = true ]; then
  check_command "cargo"
  check_command "python3"
fi

if [ "$DEPLOY_SERVER" = true ]; then
  check_command "wrangler"
fi

log_success "All required commands found"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
  log_warning "You have uncommitted changes"
  if ! confirm "Continue deployment anyway?"; then
    log_error "Deployment cancelled"
    exit 1
  fi
fi

# Get current git commit
GIT_COMMIT=$(git rev-parse HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_info "Deploying commit: $GIT_COMMIT ($GIT_BRANCH)"

# Check for .env file
if [ ! -f ".env" ]; then
  log_error ".env file not found"
  log_info "Copy .env.example to .env and fill in your secrets"
  exit 1
fi

# Check for config.toml
if [ ! -f "config.toml" ]; then
  log_error "config.toml not found"
  log_info "Copy config/production.toml to config.toml and configure it"
  exit 1
fi

log_success "Pre-flight checks passed"

# ============================================================================
# Pre-Deployment Tests
# ============================================================================

if [ "$RUN_TESTS" = true ]; then
  log_info "Running pre-deployment tests..."

  # Test configuration loading
  log_info "Testing configuration..."
  if ! node scripts/load-config.js > /dev/null 2>&1; then
    log_error "Configuration test failed"
    exit 1
  fi

  # Test TypeScript compilation
  if [ "$DEPLOY_SERVER" = true ]; then
    log_info "Testing TypeScript compilation..."
    cd packages/server
    if ! pnpm build > /dev/null 2>&1; then
      log_error "TypeScript compilation failed"
      exit 1
    fi
    cd "$PROJECT_ROOT"
  fi

  # Test Rust compilation (quick check)
  if [ "$DEPLOY_CLIENT" = true ]; then
    log_info "Testing Rust compilation..."
    if ! cargo check --quiet 2>&1; then
      log_error "Rust compilation check failed"
      exit 1
    fi
  fi

  log_success "Pre-deployment tests passed"
else
  log_warning "Skipping pre-deployment tests (--skip-tests)"
fi

# ============================================================================
# Deployment Confirmation
# ============================================================================

echo ""
log_info "Ready to deploy:"
if [ "$DEPLOY_SERVER" = true ]; then
  echo "  - Cloudflare Workers (server)"
fi
if [ "$DEPLOY_CLIENT" = true ]; then
  echo "  - Rust Client (voice bridge + dashboard)"
fi
echo "  - Git commit: $GIT_COMMIT"
echo "  - Branch: $GIT_BRANCH"
echo ""

if ! confirm "Proceed with deployment?"; then
  log_error "Deployment cancelled"
  exit 1
fi

# ============================================================================
# Backup Current Deployment
# ============================================================================

log_info "Creating backup..."

BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup config files
cp config.toml "$BACKUP_DIR/" 2>/dev/null || true
cp .env "$BACKUP_DIR/" 2>/dev/null || true

# Backup binaries (if they exist)
if [ "$DEPLOY_CLIENT" = true ] && [ -f "target/release/xswarm-voice" ]; then
  mkdir -p "$BACKUP_DIR/binaries"
  cp target/release/xswarm-voice "$BACKUP_DIR/binaries/" || true
  cp target/release/xswarm-dashboard "$BACKUP_DIR/binaries/" || true
  log_success "Backed up binaries to $BACKUP_DIR/binaries/"
fi

# Record deployment metadata
cat > "$BACKUP_DIR/deployment.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "git_commit": "$GIT_COMMIT",
  "git_branch": "$GIT_BRANCH",
  "deploy_server": $DEPLOY_SERVER,
  "deploy_client": $DEPLOY_CLIENT
}
EOF

log_success "Backup created at $BACKUP_DIR"

# ============================================================================
# Deploy Server (Cloudflare Workers)
# ============================================================================

if [ "$DEPLOY_SERVER" = true ]; then
  echo ""
  log_info "Deploying Cloudflare Workers..."

  cd packages/server

  # Install dependencies
  log_info "Installing dependencies..."
  pnpm install --frozen-lockfile

  # Build
  log_info "Building..."
  pnpm build

  # Deploy
  log_info "Deploying to Cloudflare..."
  DEPLOY_OUTPUT=$(pnpm deploy 2>&1)

  if [ $? -eq 0 ]; then
    log_success "Server deployed successfully"

    # Extract Worker URL from output
    WORKER_URL=$(echo "$DEPLOY_OUTPUT" | grep -oE 'https://[a-zA-Z0-9.-]+\.workers\.dev' | head -1)
    if [ -n "$WORKER_URL" ]; then
      log_info "Worker URL: $WORKER_URL"

      # Test health endpoint
      log_info "Testing health endpoint..."
      sleep 5  # Wait for deployment to propagate

      HEALTH_RESPONSE=$(curl -s "$WORKER_URL/health" || echo '{"status":"error"}')
      HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | grep -o '"status":"ok"' || echo "")

      if [ -n "$HEALTH_STATUS" ]; then
        log_success "Health check passed"
      else
        log_warning "Health check failed, but deployment succeeded"
        log_warning "Response: $HEALTH_RESPONSE"
      fi
    fi
  else
    log_error "Server deployment failed"
    echo "$DEPLOY_OUTPUT"
    exit 1
  fi

  cd "$PROJECT_ROOT"
fi

# ============================================================================
# Deploy Client (Rust)
# ============================================================================

if [ "$DEPLOY_CLIENT" = true ]; then
  echo ""
  log_info "Building Rust client..."

  # Install Python dependencies
  log_info "Installing Python dependencies..."
  cd packages/voice
  python3 -m pip install -e . --quiet
  cd "$PROJECT_ROOT"

  # Build Rust release binaries
  log_info "Compiling Rust binaries (this may take a few minutes)..."
  START_TIME=$(date +%s)

  if cargo build --release 2>&1 | tee /tmp/cargo-build.log | grep -q "Finished"; then
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    log_success "Rust binaries built in ${BUILD_TIME}s"

    # List built binaries
    log_info "Built binaries:"
    ls -lh target/release/xswarm* 2>/dev/null | grep -v ".d$" | awk '{print "  - " $9 " (" $5 ")"}'
  else
    log_error "Rust compilation failed"
    cat /tmp/cargo-build.log
    exit 1
  fi

  # Install systemd services (if on Linux and running as root/sudo)
  if [ "$(uname)" = "Linux" ] && [ "$EUID" -eq 0 ]; then
    log_info "Installing systemd services..."

    # Stop services if running
    systemctl stop xswarm-voice xswarm-dashboard 2>/dev/null || true

    # Copy service files
    cp systemd/*.service /etc/systemd/system/

    # Reload systemd
    systemctl daemon-reload

    # Restart services
    log_info "Starting services..."
    systemctl start xswarm-voice
    systemctl start xswarm-dashboard

    # Check status
    sleep 2
    if systemctl is-active --quiet xswarm-voice; then
      log_success "xswarm-voice service started"
    else
      log_error "xswarm-voice service failed to start"
      systemctl status xswarm-voice --no-pager
    fi

    if systemctl is-active --quiet xswarm-dashboard; then
      log_success "xswarm-dashboard service started"
    else
      log_error "xswarm-dashboard service failed to start"
      systemctl status xswarm-dashboard --no-pager
    fi
  else
    log_info "Manual service restart required (not running as root or not on Linux)"
    log_info "To restart services: sudo systemctl restart xswarm-voice xswarm-dashboard"
  fi
fi

# ============================================================================
# Post-Deployment Verification
# ============================================================================

echo ""
log_info "Running post-deployment verification..."

# Test server health
if [ "$DEPLOY_SERVER" = true ] && [ -n "${WORKER_URL:-}" ]; then
  log_info "Testing server health..."
  HEALTH_RESPONSE=$(curl -s "$WORKER_URL/health")
  if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    log_success "Server is healthy"
  else
    log_warning "Server health check failed"
  fi
fi

# Test client health
if [ "$DEPLOY_CLIENT" = true ]; then
  log_info "Testing client health..."

  # Test voice bridge
  VOICE_HEALTH=$(curl -s http://localhost:9998/health 2>/dev/null || echo '{"status":"error"}')
  if echo "$VOICE_HEALTH" | grep -q '"status":"ok"'; then
    log_success "Voice bridge is healthy"
  else
    log_warning "Voice bridge health check failed (it may take a minute to start)"
  fi

  # Test supervisor
  SUPERVISOR_HEALTH=$(curl -s http://localhost:9999/health 2>/dev/null || echo '{"status":"error"}')
  if echo "$SUPERVISOR_HEALTH" | grep -q '"status":"ok"'; then
    log_success "Supervisor is healthy"
  else
    log_warning "Supervisor health check failed"
  fi
fi

# ============================================================================
# Deployment Summary
# ============================================================================

echo ""
echo "┌─────────────────────────────────────────────────────┐"
echo "│  Deployment Complete                                │"
echo "└─────────────────────────────────────────────────────┘"
echo ""

log_success "Deployment finished successfully!"
echo ""
echo "Deployment details:"
echo "  - Timestamp: $(date)"
echo "  - Git commit: $GIT_COMMIT"
echo "  - Branch: $GIT_BRANCH"
echo "  - Backup: $BACKUP_DIR"
echo ""

if [ "$DEPLOY_SERVER" = true ] && [ -n "${WORKER_URL:-}" ]; then
  echo "Server URLs:"
  echo "  - Health: $WORKER_URL/health"
  echo "  - Voice webhook: $WORKER_URL/voice/{userId}"
  echo "  - SMS webhook: $WORKER_URL/sms/{userId}"
  echo ""
fi

if [ "$DEPLOY_CLIENT" = true ]; then
  echo "Client endpoints:"
  echo "  - Voice bridge: http://localhost:9998"
  echo "  - Supervisor: http://localhost:9999"
  echo ""
fi

echo "Next steps:"
echo "  1. Monitor logs for errors:"
if [ "$DEPLOY_SERVER" = true ]; then
  echo "     - Server: cd packages/server && pnpm tail"
fi
if [ "$DEPLOY_CLIENT" = true ]; then
  echo "     - Voice: sudo journalctl -u xswarm-voice -f"
  echo "     - Dashboard: sudo journalctl -u xswarm-dashboard -f"
fi
echo "  2. Test all communication channels (voice, SMS, email)"
echo "  3. Monitor resource usage for first hour"
echo "  4. Update monitoring alerts if needed"
echo ""

log_info "See MONITORING_GUIDE.md for operational procedures"
echo ""

# Record successful deployment
cat > "$PROJECT_ROOT/.last_deployment" << EOF
timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
commit=$GIT_COMMIT
branch=$GIT_BRANCH
server=$DEPLOY_SERVER
client=$DEPLOY_CLIENT
EOF

exit 0
