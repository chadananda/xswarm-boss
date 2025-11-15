# Phone Integration Deployment Guide

Quick guide to deploy and test the Twilio + Moshi voice integration for interactive phone calls.

## Prerequisites

1. **Twilio Account**:
   - Account SID
   - Auth Token
   - Voice-capable phone number

2. **API Keys**:
   - Anthropic API key (Claude)
   - OpenAI API key (fallback)

3. **Environment**:
   - Python 3.11+
   - Apple Silicon Mac or NVIDIA GPU (for Moshi)
   - 16GB+ RAM recommended

## Quick Start

### 1. Configure Environment

Add to `.env`:

```bash
# Twilio
TWILIO_ACCOUNT_SID="AC..."
TWILIO_AUTH_TOKEN="..."
ADMIN_ASSISTANT_PHONE_NUMBER="+1..."  # Your Twilio number

# AI APIs
ANTHROPIC_API_KEY="sk-..."
OPENAI_API_KEY="sk-..."
```

### 2. Test Locally with ngrok

```bash
# Terminal 1: Start Moshi server
cd /path/to/xswarm-boss
python scripts/run_twilio_server.py --host 0.0.0.0 --port 5000

# Terminal 2: Expose via ngrok
ngrok http 5000
```

Note the ngrok URL (e.g., `https://abc123.ngrok.io`)

### 3. Configure Twilio Webhook

In Twilio Console:

1. Go to **Phone Numbers** → **Manage** → **Active Numbers**
2. Click your phone number
3. Under "Voice Configuration":
   - **A CALL COMES IN**: TwiML Bin (create new)
   - TwiML content:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://YOUR-NGROK-URL" />
    </Connect>
</Response>
```

Replace `YOUR-NGROK-URL` with your ngrok websocket URL.

### 4. Make a Test Call

Call your Twilio number from your phone. You should:

1. Hear connection sound
2. Be able to speak
3. Hear Moshi respond in its voice
4. Have natural back-and-forth conversation

## Testing

### Run Audio Converter Tests

```bash
cd packages/assistant
pytest tests/test_audio_converter.py -v
```

Expected: 23/23 tests passing

### Run Phone Integration Tests

```bash
cd packages/assistant
pytest tests/test_phone_integration.py -v
```

Expected: Unit tests for bridging logic

### Manual Test Checklist

- [ ] Call connects without errors
- [ ] Audio is clear (no garbling, static, or echoes)
- [ ] Moshi responds to your speech
- [ ] Turn-taking works smoothly (no cutting off)
- [ ] Conversation makes sense (Moshi remembers context)
- [ ] Call can be ended cleanly

## Troubleshooting

### "Connection Failed" or No Audio

**Check**:
- ngrok is running and forwarding to correct port
- Twilio webhook URL is correct (wss://, not ws://)
- Server is running and listening on correct port

**Debug**:
```bash
# Check server logs
python scripts/run_twilio_server.py --host 0.0.0.0 --port 5000

# You should see:
# ✅ Server ready - waiting for connections...
```

### Audio is Garbled or Robotic

**Check**:
- Moshi models downloaded correctly
- Using q8 quantization (default for phone)
- Not running out of memory

**Debug**:
```bash
# Test audio conversion
cd packages/assistant
pytest tests/test_audio_converter.py::TestAudioConverter::test_roundtrip_sine_wave -v
```

### Moshi Doesn't Respond

**Check**:
- API keys configured correctly in .env
- Moshi models loaded (check server startup logs)
- Silence detection timeout (default: 1.2 seconds)

**Debug**:
```bash
# Check memory initialization
cd packages/assistant
python -c "from assistant.memory import MemoryManager; import asyncio; asyncio.run(MemoryManager().initialize()); print('OK')"
```

### Call Drops After Few Seconds

**Check**:
- ngrok session hasn't expired (free tier = 2 hours)
- Not hitting Moshi timeout (default: 500 steps)
- Memory usage not spiking (each call = ~2GB)

**Solution**:
- Restart ngrok
- Reduce max_tokens in twilio_voice_bridge.py
- Limit concurrent calls to 1-2

## Production Deployment

### Option 1: Cloud VM (Recommended)

Deploy to cloud provider with GPU support:

**Google Cloud (GPU)**:
```bash
# Create VM with T4 GPU
gcloud compute instances create moshi-phone \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud

# SSH and install dependencies
gcloud compute ssh moshi-phone
sudo apt update && sudo apt install -y python3.11 python3-pip nvidia-cuda-toolkit

# Clone repo, install deps, run server
git clone https://github.com/yourorg/xswarm-boss.git
cd xswarm-boss
pip3 install -r requirements.txt
python3 scripts/run_twilio_server.py --host 0.0.0.0 --port 443
```

**AWS (GPU)**:
- Use g4dn.xlarge instance
- Install CUDA drivers
- Deploy as above

### Option 2: Fly.io (No GPU, CPU only)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Deploy app
cd xswarm-boss
fly launch
fly deploy
```

Update Twilio webhook to: `wss://YOUR-FLY-APP.fly.dev`

### Option 3: Railway (Quick Deploy)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
cd xswarm-boss
railway up
```

## Performance Tuning

### Reduce Latency

1. **Deploy close to Twilio**:
   - Use us-east-1 (Virginia) or us-west-2 (Oregon)
   - These regions are close to Twilio data centers

2. **Use faster Moshi quantization**:
   ```python
   # In run_twilio_server.py
   bridge = TwilioVoiceBridge(
       ...
       moshi_quality="q4",  # Faster, lower quality
   )
   ```

3. **Reduce response length**:
   ```python
   # In twilio_voice_bridge.py
   response_audio, response_text = self.moshi.generate_response(
       user_audio,
       text_prompt=text_prompt,
       max_tokens=150  # Shorter responses
   )
   ```

### Handle Concurrent Calls

Each call uses ~2GB RAM. For N concurrent calls:

- **1 call**: 8GB RAM minimum
- **2 calls**: 16GB RAM minimum
- **3 calls**: 24GB RAM minimum

Use instance with appropriate RAM or deploy multiple servers behind load balancer.

## Monitoring

### Server Health

```bash
# Check active calls
curl http://localhost:5000/health

# Expected response:
# {"active_calls": 2, "status": "healthy"}
```

### Call Metrics

Server logs include:

```
[MediaStreams] Call started: CA123
[TwilioVoiceBridge] Initializing for call CA123
[Call CA123] State: listening
[Call CA123] State: thinking
[Call CA123] State: speaking
[MediaStreams] Call ended: CA123
[MediaStreams] Transcript: 12 messages
```

### Error Tracking

Monitor for:

- `WebSocket connection failed`
- `Error generating response`
- `Error sending audio`
- `ZeroDivisionError` (audio conversion bug)

## Security

### Production Checklist

- [ ] Use HTTPS/WSS (required by Twilio)
- [ ] Rotate API keys regularly
- [ ] Use environment variables (never hardcode secrets)
- [ ] Enable rate limiting (max calls per minute)
- [ ] Set up firewall (only allow Twilio IPs)
- [ ] Monitor for unusual call patterns

### Twilio IP Whitelist

Add to firewall rules:

```
# Twilio Media Streams IPs (US)
54.172.60.0/23
54.244.51.0/24
54.171.127.192/26
35.156.191.128/25
```

See [Twilio IP Addresses](https://www.twilio.com/docs/infrastructure/ip-addresses) for latest list.

## Cost Estimation

### Per Minute Costs

- **Twilio**: $0.013/min (US domestic)
- **Moshi Inference**: Free (self-hosted)
- **Cloud GPU**: ~$0.35/hour (g4dn.xlarge)
- **Claude API**: ~$0.01/call (text generation for context)

### Example Monthly Cost

100 hours of calls per month:
- Twilio: 6,000 minutes × $0.013 = $78
- AWS GPU (24/7): 720 hours × $0.35 = $252
- Claude API: ~$50
- **Total**: ~$380/month

## Next Steps

1. **Test locally** with ngrok
2. **Deploy to staging** (cloud VM or PaaS)
3. **Test from multiple phones** (iOS, Android)
4. **Monitor performance** (latency, quality)
5. **Deploy to production** with monitoring
6. **Scale up** as needed

## Support

- **Documentation**: See [phone-integration.md](phone-integration.md)
- **Issues**: [GitHub Issues](https://github.com/yourorg/xswarm-boss/issues)
- **Twilio Support**: https://support.twilio.com/

---

**Status**: Tested with ngrok locally, ready for cloud deployment
**Last Updated**: 2025-11-14
