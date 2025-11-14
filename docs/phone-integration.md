# Phone Integration with Moshi Voice

This document explains how to use the Twilio Media Streams + Moshi integration for interactive voice phone calls.

## Architecture

```
Phone Call → Twilio → WebSocket (Media Streams) → MediaStreamsServer
                                                        ↓
                                            TwilioVoiceBridge
                                                        ↓
                                            Audio Converter (mulaw ↔ PCM)
                                                        ↓
                                            MoshiBridge (MLX)
                                                        ↓
                                            PersonaManager + MemoryManager
```

## Audio Format Conversion

**Twilio Format**: mulaw 8kHz (base64 encoded)
**Moshi Format**: PCM 24kHz float32 (numpy array)

The `audio_converter.py` module handles bidirectional conversion:

- **mulaw_to_pcm24k()**: Converts Twilio audio to Moshi format
  - Decodes base64 → mulaw bytes
  - Decodes mulaw → PCM 8kHz int16
  - Resamples 8kHz → 24kHz (scipy)
  - Normalizes to float32 [-1.0, 1.0]

- **pcm24k_to_mulaw()**: Converts Moshi audio to Twilio format
  - Denormalizes float32 → int16
  - Resamples 24kHz → 8kHz (scipy)
  - Encodes PCM → mulaw
  - Encodes to base64

## Phone Call Flow

1. **Incoming Call**:
   - Twilio receives call → establishes WebSocket connection to MediaStreamsServer
   - Server receives 'start' message with call metadata (call_sid, from/to numbers)
   - Server creates TwilioVoiceBridge instance for this call

2. **Audio Streaming**:
   - Twilio sends 'media' messages (mulaw audio chunks)
   - TwilioVoiceBridge:
     - Converts mulaw → PCM 24kHz
     - Buffers audio chunks (accumulates to 1920 samples = 80ms frame)
     - Detects silence using RMS threshold (0.02)
     - After 15 silence frames (~1.2 seconds), processes accumulated speech

3. **Response Generation**:
   - TwilioVoiceBridge calls MoshiBridge.generate_response(user_audio)
   - Moshi generates audio response (NO STT/TTS - direct audio-to-audio)
   - Response converted back to mulaw format
   - Sent back to Twilio via WebSocket 'media' message

4. **Call End**:
   - Twilio sends 'stop' message
   - TwilioVoiceBridge saves conversation transcript to memory
   - Session cleaned up

## Components

### MediaStreamsServer

WebSocket server implementing Twilio Media Streams protocol.

**Key Methods**:
- `start()`: Start WebSocket server
- `handle_connection()`: Handle incoming WebSocket connections
- `_handle_start()`: Initialize call session
- `_handle_media()`: Process audio chunks
- `_handle_stop()`: Cleanup call session
- `send_audio()`: Send audio back to Twilio

**Session Management**:
- Multiple concurrent calls supported
- Each call gets unique TwilioVoiceBridge instance
- Sessions tracked by call_sid

### TwilioVoiceBridge

Manages audio streaming between Twilio and Moshi for a single call.

**Key Features**:
- Audio buffering (1920 samples = 80ms frames at 24kHz)
- Silence detection for turn-taking (RMS threshold + frame counting)
- State tracking: idle → listening → thinking → speaking
- Integration with PersonaManager (voice personality)
- Integration with MemoryManager (conversation history)
- Transcript storage per phone number

**Key Methods**:
- `initialize()`: Load Moshi models and AI client
- `process_audio_chunk()`: Process incoming audio from phone
- `_process_speech()`: Generate Moshi response
- `_build_prompt()`: Build conversation prompt with persona context
- `cleanup()`: Save transcript and cleanup resources

### Audio Converter

Utility functions for format conversion.

**Functions**:
- `mulaw_to_pcm24k(mulaw_base64: str) -> np.ndarray`
- `pcm24k_to_mulaw(pcm_float32: np.ndarray) -> str`
- `get_audio_stats(audio: np.ndarray) -> dict` (debugging)

## Configuration

### Environment Variables

Required in `.env`:

```bash
# Twilio Credentials
TWILIO_ACCOUNT_SID="AC..."
TWILIO_AUTH_TOKEN="..."
ADMIN_ASSISTANT_PHONE_NUMBER="+1..."  # Your Twilio number
ADMIN_PHONE_NUMBER="+1..."            # Your personal number

# AI API Keys (for conversation)
ANTHROPIC_API_KEY="sk-..."
OPENAI_API_KEY="sk-..."
```

### Twilio Setup

1. **Purchase Twilio Phone Number**: Get a voice-capable number from Twilio console

2. **Configure Webhook**: Point to your WebSocket server
   - For local testing: Use ngrok to expose localhost
   - For production: Deploy to cloud with wss:// URL

3. **TwiML Configuration**:
   ```xml
   <Response>
       <Connect>
           <Stream url="wss://YOUR-SERVER-URL" />
       </Connect>
   </Response>
   ```

## Running the Server

### Local Development (with ngrok)

1. **Start the WebSocket server**:
   ```bash
   python scripts/run_twilio_server.py --host 0.0.0.0 --port 5000
   ```

2. **Expose via ngrok**:
   ```bash
   ngrok http 5000
   ```

3. **Configure Twilio webhook** to point to:
   ```
   wss://YOUR-NGROK-URL
   ```

### Production Deployment

Deploy to a cloud provider with WebSocket support:

- **AWS**: API Gateway + Lambda or EC2
- **Google Cloud**: Cloud Run with WebSocket support
- **Azure**: App Service with WebSocket enabled
- **Fly.io**: Simple deployment with global edge locations

Ensure HTTPS/WSS is enabled (required by Twilio).

## Moshi Quality Settings

The TwilioVoiceBridge supports different quantization levels:

- **bf16**: Full precision (best quality, slowest)
- **q8**: 8-bit quantization (balanced - **default for phone**)
- **q4**: 4-bit quantization (fastest, lowest quality)
- **auto**: Automatically selects q8 for phone calls

Phone calls use q8 by default for optimal balance between quality and performance.

## Conversation Features

### Persona Integration

Each call uses the current active persona from PersonaManager:

- Voice personality (system prompt)
- Conversation style
- Theme colors (for TUI display)

### Memory Integration

Conversations are stored in MemoryManager:

- **User ID**: Phone number (e.g., "19167656913")
- **Messages**: Both user speech and assistant responses
- **Timestamps**: Each message timestamped
- **Retrieval**: Previous conversations can be retrieved for context

### Transcript Access

```python
# During call
transcript = bridge.get_transcript()

# After call ends
call_info = server.get_call_info(call_sid)
transcript = call_info['transcript']
```

## Turn-Taking Logic

The system uses silence detection to determine when the user has finished speaking:

**Parameters**:
- `_frame_size`: 1920 samples (80ms at 24kHz)
- `_silence_threshold`: 0.02 RMS
- `_speech_timeout_frames`: 15 frames (~1.2 seconds)

**Logic**:
1. Buffer incoming audio in 80ms chunks
2. Calculate RMS (root mean square) for each chunk
3. If RMS < 0.02, increment silence counter
4. If silence counter reaches 15 frames, process accumulated speech
5. Generate response, send back to caller
6. Reset buffer and counter, continue listening

## Testing

### Unit Tests

Test audio conversion:

```bash
pytest tests/test_audio_converter.py -v
```

### Integration Tests

Test with mock Twilio messages:

```bash
pytest tests/test_phone_integration.py -v
```

### Manual Testing

1. Start server locally with ngrok
2. Call your Twilio number
3. Speak and verify:
   - Audio is clear and intelligible
   - Responses are relevant and conversational
   - Turn-taking works smoothly (no cutting off)
   - Conversation is saved to memory

## Troubleshooting

### Common Issues

**WebSocket connection fails**:
- Check ngrok is running and forwarding to correct port
- Verify Twilio webhook URL is correct (wss://)
- Check server logs for connection errors

**Audio is garbled**:
- Verify audio conversion is working (run unit tests)
- Check buffer sizes match (1920 samples)
- Verify sample rates (8kHz Twilio, 24kHz Moshi)

**No response from Moshi**:
- Check Moshi models are loaded correctly
- Verify silence detection parameters
- Check AI API keys are configured
- Review server logs for errors

**Call connects but no audio**:
- Verify Media Streams webhook is configured
- Check audio payload is being sent/received
- Verify base64 encoding/decoding

### Debug Mode

Add verbose logging to bridge:

```python
bridge = TwilioVoiceBridge(
    ...,
    on_state_change=lambda state: print(f"State: {state}"),
)
```

Monitor audio stats:

```python
from assistant.phone.audio_converter import get_audio_stats

stats = get_audio_stats(audio)
print(f"Audio: {stats}")
```

## Performance Considerations

**Latency**:
- Audio buffering: ~80ms (1 frame)
- Silence detection: ~1.2s (15 frames)
- Moshi processing: ~500-2000ms (depends on hardware)
- Total round-trip: ~2-4 seconds

**Optimization Tips**:
- Use q8 quantization (already default)
- Deploy server close to Twilio's data centers
- Use Apple Silicon Mac or NVIDIA GPU for Moshi
- Keep responses concise (max_tokens=300)

**Concurrent Calls**:
- Each call gets own TwilioVoiceBridge instance
- Memory usage: ~2GB per active call (Moshi models)
- Recommended: 1-3 concurrent calls per server

## Future Enhancements

- [ ] DTMF menu navigation (keypad input)
- [ ] Multi-party conference calls
- [ ] Call recording and playback
- [ ] Real-time transcription display (TUI)
- [ ] Sentiment analysis during calls
- [ ] Call analytics and metrics
- [ ] Voicemail handling
- [ ] SMS integration for follow-up

## References

- [Twilio Media Streams Documentation](https://www.twilio.com/docs/voice/twiml/stream)
- [Moshi MLX GitHub](https://github.com/kyutai-labs/moshi-mlx)
- [WebSocket Protocol](https://websockets.readthedocs.io/)
- [Mulaw Audio Encoding](https://en.wikipedia.org/wiki/%CE%9C-law_algorithm)
