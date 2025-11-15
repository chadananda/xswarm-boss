#!/bin/bash
#
# Start Moshi phone server with Cloudflare Tunnel
#

echo "================================================"
echo "🎙️  Starting Moshi Phone Integration"
echo "================================================"
echo ""

# Check if Moshi server is running
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "✅ Moshi WebSocket server is running on port 5001"
else
    echo "❌ Moshi server not running on port 5001"
    echo ""
    echo "Start it with:"
    echo "  python scripts/run_twilio_server.py --host 0.0.0.0 --port 5001"
    exit 1
fi

echo ""
echo "🌐 Starting Cloudflare Tunnel..."
echo ""
echo "This will create a temporary public URL for your Moshi server."
echo "The URL will be displayed below and can be used in Twilio webhook."
echo ""
echo "================================================"
echo ""

# Start cloudflare tunnel
cloudflared tunnel --url http://localhost:5001
