#!/bin/bash
# Boss AI - Simple One-Command Deployment
# Usage: ./deploy.sh [environment]
# Environment: dev, staging, or production (default: production)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse environment argument
ENVIRONMENT="${1:-production}"

log_info "Starting Boss AI deployment to ${ENVIRONMENT}..."

# Step 1: Check prerequisites
log_info "Checking prerequisites..."

if ! command -v node &> /dev/null; then
    log_error "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    log_error "pnpm is not installed. Please install pnpm: npm install -g pnpm"
    exit 1
fi

if ! command -v wrangler &> /dev/null; then
    log_warning "Wrangler CLI not found. Installing..."
    pnpm add -g wrangler
fi

log_success "Prerequisites check passed"

# Step 2: Install dependencies
log_info "Installing dependencies..."
pnpm install
log_success "Dependencies installed"

# Step 3: Build Rust CLI (optional - only if Cargo is available)
if command -v cargo &> /dev/null; then
    log_info "Building Rust CLI..."
    cargo build --release
    log_success "Rust CLI built"
else
    log_warning "Cargo not found. Skipping Rust CLI build."
fi

# Step 4: Setup database
log_info "Setting up database..."
if [ -f ".env" ]; then
    pnpm --filter @xswarm/server run setup-db
    log_success "Database initialized"
else
    log_warning "No .env file found. Skipping database setup."
    log_warning "Run 'pnpm run setup:env' to configure your environment."
fi

# Step 5: Sync secrets to Cloudflare Workers
log_info "Syncing secrets to Cloudflare Workers..."
if [ -f ".env" ]; then
    pnpm run setup:secrets
    log_success "Secrets synced"
else
    log_error "No .env file found. Cannot sync secrets."
    log_error "Please create .env from .env.example and configure your secrets."
    exit 1
fi

# Step 6: Deploy to Cloudflare Workers
log_info "Deploying to Cloudflare Workers (${ENVIRONMENT})..."
cd packages/server
pnpm run deploy
cd ../..
log_success "Deployed to Cloudflare Workers"

# Step 7: Setup webhooks
log_info "Setting up webhooks..."
if [ "$ENVIRONMENT" = "production" ]; then
    log_info "Setting up production webhooks..."
    pnpm run setup:webhooks
    pnpm run setup:twilio
else
    log_warning "Skipping webhook setup for ${ENVIRONMENT} environment"
    log_warning "Run 'pnpm run setup:webhooks' and 'pnpm run setup:twilio' manually when ready"
fi

# Step 8: Verify deployment
log_info "Verifying deployment..."
WORKER_URL=$(wrangler deployments list --name boss-ai --json 2>/dev/null | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -n "$WORKER_URL" ]; then
    log_success "Deployment verified: ${WORKER_URL}"

    # Test health endpoint
    log_info "Testing health endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${WORKER_URL}/health")

    if [ "$HTTP_CODE" = "200" ]; then
        log_success "Health check passed"
    else
        log_warning "Health check returned HTTP ${HTTP_CODE}"
    fi
else
    log_warning "Could not verify deployment URL. Check manually with: wrangler deployments list"
fi

# Success message
echo ""
log_success "=========================================="
log_success "Boss AI deployed successfully!"
log_success "=========================================="
echo ""
log_info "Next steps:"
echo "  1. Test your deployment: curl ${WORKER_URL}/health"
echo "  2. Send a test SMS to your Twilio number"
echo "  3. Send a test email to your inbound email address"
echo "  4. Check the Rust CLI: cargo run -- --help"
echo ""
log_info "Useful commands:"
echo "  - View logs: wrangler tail"
echo "  - Update secrets: pnpm run setup:secrets"
echo "  - Setup webhooks: pnpm run setup:webhooks"
echo "  - Test webhooks: pnpm run test:webhooks"
echo ""
