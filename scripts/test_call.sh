#!/bin/bash
set -e

echo "🧹 Cleaning up old processes..."
killall -9 python3 Python cloudflared 2>/dev/null || true
sleep 2

echo "🚀 Starting Twilio server on port 5001..."
PYTHONUNBUFFERED=1 python3 scripts/run_twilio_server.py --host 0.0.0.0 --port 5001 > /tmp/server.log 2>&1 &
SERVER_PID=$!
echo "⏳ Waiting for Moshi to load (q8 takes ~15 seconds)..."
sleep 20

# Check server started
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ Server failed to start. Log:"
    cat /tmp/server.log
    exit 1
fi
echo "✅ Server running (PID: $SERVER_PID)"

echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --url http://localhost:5001 > /tmp/tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "⏳ Waiting for tunnel to establish..."
sleep 10

# Extract tunnel URL
TUNNEL_URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/tunnel.log | head -1)
if [ -z "$TUNNEL_URL" ]; then
    echo "❌ Failed to get tunnel URL. Log:"
    cat /tmp/tunnel.log
    kill $SERVER_PID $TUNNEL_PID 2>/dev/null
    exit 1
fi
echo "✅ Tunnel ready: $TUNNEL_URL"

# Convert to WebSocket URL
WSS_URL=$(echo $TUNNEL_URL | sed 's/https:/wss:/')
echo "📞 Making test call to +19167656913..."
python3 scripts/make_moshi_call.py --tunnel-url "$WSS_URL" --to "+19167656913"

echo ""
echo "✅ Call initiated!"
echo "Server log: /tmp/server.log"
echo "Tunnel log: /tmp/tunnel.log"
echo ""
echo "To stop servers:"
echo "  kill $SERVER_PID $TUNNEL_PID"
