# MOSHI Audio Garbling - Root Cause Analysis

## Issue Summary

**Symptom:** MOSHI audio output sounds like "crowd of people talking at once", completely garbled, cannot tell forward/backward direction

**Test Results:**
- ✅ Whisper API successfully transcribes both test and real-time audio as intelligible speech
- ❌ Human listeners hear completely garbled audio
- ❌ Both test mode (`moshi-response.wav`) and real-time mode (`moshi-debug-audio.wav`) are garbled
- ❌ Playing WAV files directly with `play` command produces same garbled sound

## Root Cause: MIMI Decoder State Not Maintained

### The Problem

**Location:** `packages/core/src/voice.rs:1552`

```rust
let decoded = moshi_state.mimi_model.decode_step(&audio_tensor.into(), &().into())?;
```

The second parameter `&().into()` is a **unit type** `()`, which means **no state is being passed**.

### Why This Causes Garbling

1. **MIMI is a streaming neural codec** - it needs temporal continuity between frames
2. **Each 80ms frame is decoded independently** - no context from previous frames
3. **No temporal structure** - causes "crowd talking" effect (overlapping independent speech fragments)
4. **Phonetic content preserved but structure broken** - explains why Whisper can transcribe but humans can't understand

### Evidence

**All MIMI decode_step calls use `()`:**
- `voice.rs:1169` - Test mode
- `voice.rs:1216` - Test mode (forced text)
- `voice.rs:1552` - Real-time conversation mode
- `voice.rs:490` - Even warmup code uses `()`

**No decoder state in structures:**
- `MoshiState` (lines 279-302): No mimi_decoder_state field
- `ConnectionState` (lines 504-511): Has lm_generator state, but no MIMI state

**LM generator IS stateful:**
```rust
struct ConnectionState {
    lm_generator: moshi::lm_generate_multistream::State,  // ✅ Stateful
    // Missing: mimi_decoder_state ❌
}
```

## Why Whisper Can Transcribe Garbled Audio

Whisper is extremely robust and can extract phonetic patterns from heavily distorted audio. The speech content is present in the frames, but the temporal structure is broken, making it unintelligible to human ears but still processable by Whisper's neural network.

## Expected Behavior

MIMI should maintain decoder state across frames:

```rust
struct ConnectionState {
    lm_generator: moshi::lm_generate_multistream::State,
    mimi_decoder_state: SomeStateType,  // MISSING!
    // ...
}
```

Then in decode:
```rust
let (decoded, new_state) = moshi_state.mimi_model.decode_step(
    &audio_tensor.into(),
    &conn_state.mimi_decoder_state.into()  // Use persistent state
)?;
conn_state.mimi_decoder_state = new_state;  // Update for next frame
```

## Next Steps

1. **Find the correct MIMI state type** - check moshi-rs library documentation/examples
2. **Add mimi_decoder_state to ConnectionState**
3. **Maintain state across frames in process_with_lm_impl**
4. **Test if audio becomes intelligible**

## Impact

This affects:
- ✅ Real-time conversation mode (garbled)
- ✅ Test mode (garbled)
- ✅ Greeting generation (likely also garbled)
- ✅ ANY audio generated through MIMI decoder

## Hypothesis Validation

**If this fix works, we should see:**
- Clear, intelligible speech in real-time playback
- Audio WAV files sound clear when played directly
- "Crowd talking" effect disappears
- Temporal continuity restored

---

**Status:** Root cause identified, awaiting implementation
**Next:** Investigate moshi-rs library for correct StreamingState type
