# Phone Integration Testing Guide

## Summary

The Twilio + Moshi phone integration is **complete and ready for testing**. All code is written, tested, and documented. The only remaining step is to test it live with a real phone call.

## What's Complete ✅

1. **Core Components** (4 files, ~650 lines):
   - `audio_converter.py` - Mulaw ↔ PCM 24kHz conversion
   - `twilio_voice_bridge.py` - Moshi phone integration
   - `media_streams_server.py` - WebSocket server
   - `run_twilio_server.py` - Server startup script

2. **Tests** (36 tests, all passing):
   - Audio converter tests (23 tests)
   - Phone integration unit tests (13 tests)

3. **Documentation**:
   - Architecture guide (`phone-integration.md`)
   - Deployment guide (`phone-deployment-guide.md`)
   - Implementation summary (`PHONE_INTEGRATION_SUMMARY.md`)

## Testing Options

### Option 1: Manual Testing (Quick & Easy)

For quick manual testing without phone calls:

```bash
# Terminal 1: Start the server
python scripts/run_twilio_server.py --host 0.0.0.0 --port 5001

# Wait for "✅ Server ready" message
# (This will take ~30-60 seconds on first run while Moshi loads into memory)
```

**Note**: The server loads Moshi models into memory on first call, which takes time. This is normal and only happens once.

### Option 2: Local Voice Testing (No Phone)

Test Moshi voice locally through your computer's microphone/speakers:

```bash
# Talk to Moshi directly (no phone required)
python scripts/test_moshi_local.py --persona GLaDOS --quality q8

# This will:
# 1. Load Moshi models (~30-60 seconds first time)
# 2. Listen to your microphone
# 3. Respond with Moshi voice through speakers
# 4. Ctrl+C to exit
```

### Option 3: Full Phone Call Testing (Cloud Deployment)

For real phone calls with Twilio + Cloudflare Tunnel:

```bash
# Terminal 1: Start the WebSocket server
python scripts/run_twilio_server.py --host 0.0.0.0 --port 5001

# Terminal 2: Expose via Cloudflare Tunnel
cloudflared tunnel --url http://localhost:5001

# Output will show:
# "Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):"
# https://random-name.trycloudflare.com

# Terminal 3: Update Twilio webhook
# Go to: https://console.twilio.com/
# Phone Numbers → Your Number → Voice Configuration
# Set webhook to:
```

**TwiML for Twilio Webhook**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://random-name.trycloudflare.com" />
    </Connect>
</Response>
```

Replace `random-name.trycloudflare.com` with your actual Cloudflare Tunnel URL.

Then call your Twilio number and talk to Moshi!

## Known Issue: Moshi Model Loading

**Symptom**: Server hangs or takes a long time to start

**Cause**: Moshi models (~2GB) are loaded into memory on first call. This is CPU/memory intensive and can take 30-60 seconds.

**Solutions**:

1. **Wait it out**: First load takes time, but subsequent calls are fast
2. **Use q4 instead of q8**: Faster loading, lower quality
   ```python
   # In run_twilio_server.py, change:
   moshi_quality="q4",  # Faster, smaller models
   ```
3. **Pre-warm the models**: Make a test call first to load models, then real calls are instant

## Testing Checklist

### Audio Converter ✅
- [x] 23 tests passing
- [x] Roundtrip conversion tested
- [x] Edge cases handled

### Phone Integration ✅
- [x] 13 unit tests passing
- [x] Buffering logic tested
- [x] Silence detection tested

### End-to-End Testing ⏳
- [ ] Start server locally
- [ ] Test with Cloudflare Tunnel
- [ ] Configure Twilio webhook
- [ ] Make test phone call
- [ ] Verify audio quality
- [ ] Verify conversation works
- [ ] Verify transcript saved

## Quick Commands Reference

```bash
# Check if Moshi models are downloaded
ls -lh ~/.cache/huggingface/hub/ | grep moshiko

# Expected output:
# models--kyutai--moshiko-mlx-q8   (for q8)
# models--kyutai--moshiko-mlx-q4   (for q4)
# models--kyutai--moshiko-mlx-bf16 (for bf16)

# Kill any hanging processes
pkill -f "run_twilio_server"
pkill -f "test_moshi_local"
lsof -ti:5001 | xargs kill -9  # Kill process on port 5001

# Check if server is running
lsof -i:5001

# Test WebSocket connection
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:5001
```

## Troubleshooting

### Server Won't Start
```bash
# Check if port is in use
lsof -i:5001

# Kill the process
lsof -ti:5001 | xargs kill -9

# Try again
python scripts/run_twilio_server.py --host 0.0.0.0 --port 5001
```

### Moshi Models Not Found
```bash
# Check cache
ls ~/.cache/huggingface/hub/ | grep moshiko

# If missing, download them:
python -c "
from huggingface_hub import snapshot_download
snapshot_download('kyutai/moshiko-mlx-q8')
"
```

### Cloudflare Tunnel Issues
```bash
# Make sure cloudflared is installed
which cloudflared

# If not installed:
brew install cloudflared

# Test tunnel
cloudflared tunnel --url http://localhost:5001
```

## Next Steps

1. **Local Testing**: Run `test_moshi_local.py` to verify Moshi works
2. **Server Testing**: Start the WebSocket server and verify it runs
3. **Phone Testing**: Set up Cloudflare Tunnel + Twilio webhook
4. **Make Test Call**: Call your Twilio number and talk to Moshi
5. **Iterate**: Adjust quality, silence detection, or response length as needed

## Support

- **Documentation**: See `docs/phone-integration.md`
- **Deployment**: See `docs/phone-deployment-guide.md`
- **Summary**: See `docs/PHONE_INTEGRATION_SUMMARY.md`

---

**Status**: ✅ Code complete, ready for live testing
**Last Updated**: 2025-11-14
