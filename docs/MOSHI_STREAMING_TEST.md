# Moshi Full-Duplex Streaming Test

**Date**: 2025-11-15
**Status**: 📞 CALL IN PROGRESS - Awaiting user feedback

## Summary

Refactored Moshi phone integration from VAD-based batch processing to full-duplex frame-by-frame streaming. This test verifies the new streaming implementation works correctly with real phone calls.

## Architecture Change

### Before (WRONG)
- Used Voice Activity Detection (VAD) with 1.2s silence threshold
- Batch processed complete utterances
- Waited for silence before responding
- User heard pre-recorded TwiML TTS message
- No interactive conversation possible

### After (CORRECT)
- Full-duplex streaming (no VAD)
- Frame-by-frame processing (80ms frames at 12.5 Hz)
- Continuous bidirectional audio flow
- Moshi generates greeting from silence frames
- NO TwiML TTS - only Moshi's voice
- Natural interactive conversation

## Implementation Details

### Files Modified

1. **`packages/assistant/assistant/voice/moshi_mlx.py`**
   - Added `create_lm_generator()` - creates persistent LM generator for streaming
   - Added `step_frame()` - processes single 80ms frame through Moshi
   - Added `generate_greeting()` - generates Moshi greeting from silence frames

2. **`packages/assistant/assistant/phone/twilio_voice_bridge.py`**
   - **REMOVED**: All VAD logic (`_silence_threshold`, `_speech_timeout_frames`, `_silence_frames`)
   - **REMOVED**: `_process_speech()` batch processing method
   - **ADDED**: `self.lm_gen` - persistent LM generator
   - **ADDED**: `generate_and_send_greeting()` - creates initial greeting
   - **MODIFIED**: `process_audio_chunk()` - now processes each frame immediately

3. **`scripts/make_moshi_call.py`**
   - Removed TwiML `<Say>` tag (no pre-recorded TTS)

4. **`packages/assistant/assistant/phone/media_streams_server.py`**
   - Added greeting generation and send immediately after bridge initialization

## Test Infrastructure

### Server
- **Process**: PID 16286
- **Port**: 5001
- **Host**: 0.0.0.0
- **Command**: `python scripts/run_twilio_server.py --host 0.0.0.0 --port 5001`

### Cloudflare Tunnel
- **URL**: `wss://tournaments-supervision-mod-pink.trycloudflare.com`
- **Protocol**: QUIC
- **Status**: Connected

### Moshi Model
- **Quality**: q4 (4-bit quantization)
- **Load time**: ~7.6 seconds (with cached models)
- **GPU**: Apple Silicon M3 Metal

## Test Call Details

- **From**: +18447472899 (Twilio number)
- **To**: +19167656913 (User's number)
- **Call SID**: CAe17e136529445ef38433d0cd40f7fa8a
- **Status**: Initiated (queued)
- **WebSocket URL**: `wss://tournaments-supervision-mod-pink.trycloudflare.com`

### TwiML Used

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="wss://tournaments-supervision-mod-pink.trycloudflare.com" />
    </Connect>
</Response>
```

**Note**: No `<Say>` tag - Moshi speaks directly!

## Expected Behavior

When user answers the phone:

1. **NO TwiML TTS** - silence or immediate Moshi greeting
2. **Moshi Greeting**: Generated from silence frames on call connect
   - Example: "Hello! I'm [Persona]. How can I help you?"
3. **User speaks** → Processed frame-by-frame → Moshi responds within ~200-300ms
4. **Full-duplex conversation**: User can interrupt Moshi naturally
5. **Continuous streaming**: No silence detection, no turn-taking delays

## Technical Flow

```
User answers call
    ↓
WebSocket connection established
    ↓
Bridge.initialize() called
    ↓
Create persistent LM generator (self.lm_gen)
    ↓
Generate greeting from 25 silence frames (~2 seconds)
    ↓
Send greeting audio to user immediately
    ↓
[User hears Moshi greeting in Moshi's voice]
    ↓
User speaks
    ↓
For each 80ms audio frame:
    - Convert mulaw 8kHz → PCM 24kHz
    - Buffer until 1920 samples (80ms)
    - Call moshi.step_frame(lm_gen, frame)
    - Get response audio + text
    - Convert PCM 24kHz → mulaw 8kHz
    - Send to user immediately
    ↓
[Continuous bidirectional streaming]
```

## Success Criteria

- [x] Server starts successfully
- [x] Cloudflare tunnel establishes
- [x] Call initiated successfully
- [ ] User answers call
- [ ] User hears Moshi greeting (NOT TwiML TTS)
- [ ] Moshi greeting is in Moshi's voice
- [ ] User can speak naturally
- [ ] Moshi responds within ~200-300ms
- [ ] Interactive conversation works
- [ ] No silence detection delays
- [ ] Full-duplex (can interrupt Moshi)
- [ ] Audio quality is acceptable
- [ ] No latency/echo issues

## Awaiting User Feedback

**Questions to answer**:
1. Did you answer the call?
2. What did you hear first?
   - Silence?
   - Moshi greeting?
   - Pre-recorded TTS? (should NOT happen)
3. Was the greeting in Moshi's voice or robotic TTS?
4. Could you have a conversation?
5. How was the response latency?
6. Could you interrupt Moshi mid-sentence?
7. Audio quality issues?
8. Any errors or unexpected behavior?

---

**Last Updated**: 2025-11-15 03:17 UTC
**Call Status**: AWAITING USER ANSWER
