#!/bin/bash
set -e

echo "🧹 Cleaning up old processes..."
killall -9 python3 Python ngrok 2>/dev/null || true
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

echo "🌐 Starting ngrok tunnel..."
ngrok http 5001 --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
echo "⏳ Waiting for ngrok to establish..."
sleep 5

# Extract ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL. Log:"
    cat /tmp/ngrok.log
    kill $SERVER_PID $NGROK_PID 2>/dev/null
    exit 1
fi
echo "✅ ngrok tunnel ready: $NGROK_URL"

# Convert to WebSocket URL (https → wss)
WSS_URL=$(echo $NGROK_URL | sed 's/https:/wss:/')
echo "📞 Making test call to +19167656913..."
python3 scripts/make_moshi_call.py --tunnel-url "$WSS_URL" --to "+19167656913"

echo ""
echo "✅ Call initiated!"
echo "Server log: /tmp/server.log"
echo "ngrok log: /tmp/ngrok.log"
echo "ngrok dashboard: http://localhost:4040"
echo ""
echo "To stop servers:"
echo "  kill $SERVER_PID $NGROK_PID"
echo ""
echo "⚠️  ngrok free tier: 60-minute session timeout"
echo "    If call disconnects after 60 min, restart the tunnel"
