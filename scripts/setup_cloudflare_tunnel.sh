#!/bin/bash
#
# Setup Cloudflare Tunnel for Twilio Media Streams WebSocket
#
# This script will:
# 1. Authenticate with Cloudflare (opens browser)
# 2. Create a tunnel named "moshi-phone"
# 3. Configure it to route to localhost:5000
# 4. Give you the public URL to use in Twilio webhook
#

set -e

echo "================================================"
echo "Cloudflare Tunnel Setup for Moshi Phone Calls"
echo "================================================"
echo ""

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed"
    echo ""
    echo "Install with:"
    echo "  brew install cloudflared"
    echo ""
    exit 1
fi

echo "✅ cloudflared is installed"
echo ""

# Step 1: Login to Cloudflare
echo "Step 1: Authenticate with Cloudflare..."
echo ""
echo "This will open your browser. Please:"
echo "  1. Log in to Cloudflare"
echo "  2. Authorize cloudflared"
echo "  3. Come back here when done"
echo ""
read -p "Press ENTER to continue..."

cloudflared tunnel login

echo ""
echo "✅ Authenticated with Cloudflare"
echo ""

# Step 2: Create tunnel
echo "Step 2: Creating tunnel 'moshi-phone'..."
echo ""

# Delete existing tunnel if it exists
cloudflared tunnel delete moshi-phone 2>/dev/null || true

# Create new tunnel
cloudflared tunnel create moshi-phone

echo ""
echo "✅ Tunnel created"
echo ""

# Step 3: Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep moshi-phone | awk '{print $1}')

echo "📋 Tunnel ID: $TUNNEL_ID"
echo ""

# Step 4: Create config file
echo "Step 3: Creating tunnel configuration..."
echo ""

mkdir -p ~/.cloudflared

cat > ~/.cloudflared/config.yml <<EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json

ingress:
  # Route to Moshi Media Streams WebSocket server
  - hostname: moshi-phone.yourdomain.com
    service: ws://localhost:5000
    originRequest:
      noTLSVerify: true

  # Catch-all rule (required)
  - service: http_status:404
EOF

echo "✅ Configuration created at ~/.cloudflared/config.yml"
echo ""

# Step 5: Get tunnel URL
echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "Your tunnel is ready. To use it:"
echo ""
echo "1. Start the Moshi server:"
echo "   python scripts/run_twilio_server.py --host 0.0.0.0 --port 5000"
echo ""
echo "2. In another terminal, start the tunnel:"
echo "   cloudflared tunnel run moshi-phone"
echo ""
echo "3. Your public URL will be:"
echo "   wss://moshi-phone.yourdomain.com"
echo ""
echo "4. Update Twilio webhook to:"
echo "   wss://moshi-phone.yourdomain.com"
echo ""
echo "================================================"
echo ""
echo "OR, for quick testing without DNS setup:"
echo ""
echo "Run this command for instant access:"
echo "  cloudflared tunnel --url http://localhost:5000"
echo ""
echo "It will give you a temporary URL like:"
echo "  https://random-name.trycloudflare.com"
echo ""
echo "Use that URL (change https:// to wss://) in Twilio webhook"
echo "================================================"
