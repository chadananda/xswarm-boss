#!/bin/bash
# Omarchy Defender - Cloudflare Pages Deployment Script
# Deploys build/ directory to Cloudflare Pages

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
ENV_FILE="$PROJECT_ROOT/.env"

echo "🚀 Deploying Omarchy Defender to Cloudflare Pages..."

# Check for build directory
if [ ! -d "$BUILD_DIR" ]; then
  echo "❌ Build directory not found. Run ./scripts/build.sh first."
  exit 1
fi

# Load environment variables
if [ -f "$ENV_FILE" ]; then
  echo "📋 Loading environment variables..."
  export $(grep -v '^#' "$ENV_FILE" | xargs)
else
  echo "⚠️  No .env file found. Using existing environment."
fi

# Check for required variables
if [ -z "$CLOUDFLARE_ACCOUNT_ID" ] || [ -z "$CLOUDFLARE_API_TOKEN" ]; then
  echo "❌ Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN"
  echo "   Please set these in your .env file or environment."
  exit 1
fi

# Project name (from config or default)
PROJECT_NAME="${CLOUDFLARE_PROJECT_NAME:-omarchy-defender}"

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
  echo "📦 Installing Wrangler CLI..."
  npm install -g wrangler
fi

# Deploy to Cloudflare Pages
echo "📤 Deploying to Cloudflare Pages..."
cd "$BUILD_DIR"

# Use wrangler pages deploy
CLOUDFLARE_API_TOKEN="$CLOUDFLARE_API_TOKEN" \
wrangler pages deploy . \
  --project-name="$PROJECT_NAME" \
  --branch=main

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🔗 Your site is live at:"
echo "   https://$PROJECT_NAME.pages.dev"
echo "   https://xswarm.ai/omarchy-defender (if custom domain configured)"
echo ""
echo "📊 Cloudflare Dashboard:"
echo "   https://dash.cloudflare.com/$CLOUDFLARE_ACCOUNT_ID/pages/view/$PROJECT_NAME"
