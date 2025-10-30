# Twilio + MOSHI Audio Architecture

**Date**: 2025-10-24
**Issue**: Audio format mismatch between Twilio and MOSHI
**Status**: Design Complete, Implementation Needed

## Problem Statement

### Audio Format Mismatch

| Component | Sample Rate | Format | Channels |
|-----------|-------------|--------|----------|
| **Twilio** | 8kHz | μ-law (8-bit) | Mono |
| **MOSHI** | 24kHz | PCM float32 | Mono |
| **Local Audio** | 24kHz | PCM float32 | Mono |

**Impact**: Need audio resampling and format conversion for Twilio integration

## Complete Architecture

### 1. Local Voice (Mac/Linux/Windows)

```
┌─────────────┐
│ Microphone  │ ← User speaks
└──────┬──────┘
       │ Raw audio (hardware)
       ▼
┌─────────────┐
│ Rust (cpal) │ ← Captures at 24kHz PCM
└──────┬──────┘
       │ WebSocket (24kHz PCM float32)
       ▼
┌──────────────┐
│ Python Bridge│ ← Receives numpy arrays
└──────┬───────┘
       │ MLX arrays (24kHz)
       ▼
┌──────────────┐
│ MOSHI Model  │ ← Native 24kHz
└──────┬───────┘
       │ Response audio (24kHz)
       ▼
┌──────────────┐
│ Rust (cpal)  │ ← Plays to speakers
└──────────────┘
```

**Characteristics**:
- ✅ No resampling needed
- ✅ Native 24kHz throughout
- ✅ Best quality
- ✅ Lowest latency (~200ms)

### 2. Twilio Phone Calls

```
┌──────────────┐
│ Phone (PSTN) │ ← User calls
└──────┬───────┘
       │ PSTN audio
       ▼
┌──────────────────┐
│ Twilio Network   │ ← 8kHz μ-law
└──────┬───────────┘
       │ Media Stream (WebSocket)
       │ Format: base64(μ-law), 8kHz
       ▼
┌───────────────────────────────┐
│ Cloudflare Worker             │
│ (packages/server)             │
│                               │
│ 1. Decode μ-law → 16-bit PCM  │ ← Audio decoding
│ 2. Store in buffer            │
└──────┬────────────────────────┘
       │ WebSocket/HTTP to Python
       │ 8kHz PCM int16
       ▼
┌───────────────────────────────┐
│ Python Voice Bridge           │
│ (packages/voice)              │
│                               │
│ 3. Resample: 8kHz → 24kHz     │ ← Upsampling (scipy/resampy)
│ 4. Convert: int16 → float32   │
│ 5. Normalize to [-1, 1]       │
└──────┬────────────────────────┘
       │ 24kHz PCM float32
       ▼
┌───────────────────────────────┐
│ MOSHI Model                   │ ← Native processing
└──────┬────────────────────────┘
       │ Response (24kHz float32)
       ▼
┌───────────────────────────────┐
│ Python Voice Bridge           │
│                               │
│ 6. Denormalize from [-1, 1]   │
│ 7. Resample: 24kHz → 8kHz     │ ← Downsampling
│ 8. Convert: float32 → int16   │
└──────┬────────────────────────┘
       │ 8kHz PCM int16
       ▼
┌───────────────────────────────┐
│ Cloudflare Worker             │
│                               │
│ 9. Encode: PCM → μ-law        │ ← Audio encoding
│ 10. Base64 encode             │
└──────┬────────────────────────┘
       │ Media Stream (WebSocket)
       │ Format: base64(μ-law)
       ▼
┌──────────────────┐
│ Twilio Network   │
└──────┬───────────┘
       │ PSTN audio
       ▼
┌──────────────┐
│ Phone (PSTN) │ ← User hears
└──────────────┘
```

**Characteristics**:
- ⚠️ Requires resampling (8kHz ↔ 24kHz)
- ⚠️ Quality loss from PSTN (expected)
- ⚠️ Higher latency (~300-400ms total)
- ⚠️ μ-law encoding/decoding needed

## Audio Processing Pipeline

### Twilio → MOSHI (Inbound)

```python
# packages/voice/src/xswarm_voice/audio.py

import numpy as np
from scipy import signal

def twilio_to_moshi(audio_8khz: np.ndarray) -> np.ndarray:
    """
    Convert Twilio audio to MOSHI format.

    Args:
        audio_8khz: 8kHz PCM int16 from Twilio

    Returns:
        24kHz PCM float32 for MOSHI
    """
    # 1. Convert int16 → float32
    audio_float = audio_8khz.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

    # 2. Resample 8kHz → 24kHz (3x upsampling)
    num_samples_24k = int(len(audio_float) * 24000 / 8000)
    audio_24khz = signal.resample(audio_float, num_samples_24k)

    return audio_24khz
```

### MOSHI → Twilio (Outbound)

```python
def moshi_to_twilio(audio_24khz: np.ndarray) -> np.ndarray:
    """
    Convert MOSHI audio to Twilio format.

    Args:
        audio_24khz: 24kHz PCM float32 from MOSHI

    Returns:
        8kHz PCM int16 for Twilio
    """
    # 1. Resample 24kHz → 8kHz (3x downsampling)
    num_samples_8k = int(len(audio_24khz) * 8000 / 24000)
    audio_8khz = signal.resample(audio_24khz, num_samples_8k)

    # 2. Clip to valid range
    audio_8khz = np.clip(audio_8khz, -1.0, 1.0)

    # 3. Convert float32 → int16
    audio_int16 = (audio_8khz * 32767).astype(np.int16)

    return audio_int16
```

### μ-law Encoding/Decoding (Cloudflare Worker)

```javascript
// packages/server/src/lib/audio.js

/**
 * Decode μ-law to 16-bit PCM
 * @param {Uint8Array} mulaw - μ-law encoded audio
 * @returns {Int16Array} - 16-bit PCM
 */
export function mulawToPcm(mulaw) {
  const pcm = new Int16Array(mulaw.length);
  for (let i = 0; i < mulaw.length; i++) {
    pcm[i] = MULAW_DECODE_TABLE[mulaw[i]];
  }
  return pcm;
}

/**
 * Encode 16-bit PCM to μ-law
 * @param {Int16Array} pcm - 16-bit PCM
 * @returns {Uint8Array} - μ-law encoded
 */
export function pcmToMulaw(pcm) {
  const mulaw = new Uint8Array(pcm.length);
  for (let i = 0; i < pcm.length; i++) {
    mulaw[i] = linearToMulaw(pcm[i]);
  }
  return mulaw;
}

// μ-law decode lookup table (standard G.711)
const MULAW_DECODE_TABLE = [/* 256 values */];

function linearToMulaw(sample) {
  // Standard G.711 μ-law encoding algorithm
  // ...
}
```

## Updated Dependencies

### Python (packages/voice/pyproject.toml)

```toml
dependencies = [
    "moshi_mlx>=0.1.0",
    "numpy>=1.24.0",
    "websockets>=12.0",
    "scipy>=1.11.0",      # For signal.resample
    # OR
    "resampy>=0.4.0",     # Alternative: faster resampling
]
```

### JavaScript (packages/server/package.json)

```json
{
  "dependencies": {
    "@twilio/voice-sdk": "^2.x",
    "ws": "^8.x"
  }
}
```

## WebSocket Protocol

### Twilio Media Stream Format

```json
{
  "event": "media",
  "streamSid": "MZ...",
  "media": {
    "track": "inbound",
    "chunk": "1",
    "timestamp": "2024",
    "payload": "base64_encoded_mulaw_audio"
  }
}
```

### Our Bridge Protocol (Worker ↔ Python)

```json
{
  "type": "audio",
  "format": "pcm16",     // 16-bit PCM
  "sampleRate": 8000,    // 8kHz
  "channels": 1,         // Mono
  "data": "base64_pcm"   // Base64 encoded PCM
}
```

## Latency Analysis

### Local Voice
- Capture: ~10ms (cpal)
- WebSocket: ~5ms (local)
- MOSHI: ~160ms (model)
- Playback: ~10ms (cpal)
- **Total: ~185ms** ✅

### Twilio Phone
- PSTN: ~50-100ms (network)
- Twilio → Worker: ~20ms
- μ-law decode: ~1ms
- Resample 8→24kHz: ~5ms
- Worker → Python: ~10ms
- MOSHI: ~160ms (model)
- Resample 24→8kHz: ~5ms
- μ-law encode: ~1ms
- Python → Worker: ~10ms
- Worker → Twilio: ~20ms
- PSTN: ~50-100ms (network)
- **Total: ~332-482ms** ⚠️

**Analysis**: Phone calls will have ~2x latency vs local, but acceptable for phone conversations.

## Quality Considerations

### Upsampling (8kHz → 24kHz)

**Good**:
- Enables MOSHI to work (requires 24kHz)
- Preserves all original information
- No information loss

**Limitations**:
- No new information created above 4kHz (Nyquist)
- MOSHI trained on 24kHz may not be optimal for 8kHz content
- Voice will sound "telephony quality" regardless

### Downsampling (24kHz → 8kHz)

**Good**:
- Standard for telephony
- Efficient bandwidth
- Acceptable for voice

**Limitations**:
- Loses high-frequency content (>4kHz)
- Voice quality limited by PSTN, not MOSHI

## Implementation Priority

### Phase 1: Local Voice (Current)
- ✅ 24kHz native path
- ✅ No resampling needed
- ✅ Best quality and latency

### Phase 2: Twilio Integration (Next)
1. Add `scipy` or `resampy` to dependencies
2. Implement `audio.py` resampling functions
3. Update Cloudflare Worker for μ-law codec
4. Add WebSocket relay Worker ↔ Python
5. Test with Twilio test number

### Phase 3: Optimization (Later)
- Consider using Rust for resampling (faster)
- Evaluate MOSHI fine-tuning on 8kHz audio
- Implement adaptive buffering
- Add jitter buffer for packet loss

## Testing Strategy

### Local Voice Test
```bash
python3 packages/voice/test_core.py
# Should work with 24kHz native
```

### Twilio Integration Test
```bash
# 1. Start bridge
python3 -m xswarm_voice.server

# 2. Start Cloudflare Worker
pnpm dev:webhooks

# 3. Call Twilio test number
# Verify audio quality and latency
```

## Recommendation

**Proceed with current plan**, but add audio resampling in Phase 2:

1. ✅ **Now**: Build local voice (24kHz native) - no resampling
2. **Next week**: Add Twilio support with resampling
3. **Later**: Optimize if latency issues

This ensures:
- Local voice has best quality/latency
- Phone calls work but with acceptable tradeoffs
- Clean separation of concerns

---

**Last Updated**: 2025-10-24
**Decision**: Build local voice first (24kHz), add Twilio resampling in Phase 2
**Dependencies**: Add `scipy` or `resampy` for Phase 2
