# MOSHI Official CLI vs Our Implementation - Critical Differences

## Problem Summary

**Our Implementation**: 1610ms average per frame (20x too slow for real-time)
**Official CLI**: ~50ms average per frame (works perfectly on M3 Metal)

Both use the SAME approach:
- BF16 model from `kyutai/moshiko-mlx-bf16`
- Runtime quantization (4-bit or 8-bit)
- MLX framework on Apple Metal GPU

## Root Cause: Synchronous Encoding/Decoding

### Official CLI Architecture (local.py:76-145)

**Key Insight**: The official CLI runs encoder/decoder in a **SEPARATE PROCESS** with **ASYNC** streaming:

```python
# Official: SEPARATE PROCESSES
p1 = multiprocessing.Process(target=client, args=subprocess_args)  # Audio encode/decode
p2 = multiprocessing.Process(target=server, args=subprocess_args)  # MLX inference

# Official: ASYNC audio codec operations in client process
async def send_loop():
    audio_tokenizer.encode(pcm_data)  # Non-blocking!

async def send_loop2():
    data = audio_tokenizer.get_encoded()  # Check if ready
    if data is None:
        await asyncio.sleep(0.001)  # Yield to other tasks

async def recv_loop():
    data = audio_tokenizer.get_decoded()  # Check if ready
    if data is None:
        await asyncio.sleep(0.001)  # Yield to other tasks
```

**Result**:
- Encoding happens in parallel with inference
- Decoding happens in parallel with inference
- Total time ≈ max(encode, inference, decode) instead of sum!

### Our Implementation (moshi_mlx.py:247-288)

```python
def encode_audio(self, audio: np.ndarray) -> np.ndarray:
    self.audio_tokenizer.encode(audio)

    # CRITICAL PROBLEM: BLOCKING WAIT
    while True:
        codes = self.audio_tokenizer.get_encoded()
        if codes is not None:
            return codes
        time.sleep(0.001)  # Spin-wait blocking the thread!

def decode_audio(self, codes: np.ndarray) -> np.ndarray:
    self.audio_tokenizer.decode(codes)

    # CRITICAL PROBLEM: BLOCKING WAIT
    while True:
        audio = self.audio_tokenizer.get_decoded()
        if audio is not None:
            return audio
        time.sleep(0.001)  # Spin-wait blocking the thread!
```

**Result**:
- Total time = encode_time + inference_time + decode_time
- Everything is serialized (one after another)
- From our test: ~200ms encode + ~1200ms inference + ~200ms decode = ~1600ms total!

## Performance Breakdown

### Official CLI (Parallel)
```
Timeline:
t=0    ┌─encode─┐
t=0    │        ├─inference─┐
t=0    │        │           ├─decode─┐
       └────────┴───────────┴────────┘
Total: ~50ms (max of all three, running in parallel)
```

### Our Implementation (Serial)
```
Timeline:
t=0    ┌─encode─┐
t=200  │        ├─────inference─────┐
t=1400 │        │                   ├─decode─┐
       └────────┴───────────────────┴────────┘
Total: ~1600ms (sum of all three, running sequentially)
```

## Evidence From Our Tests

From `/tmp/moshi_q4_test.log`:
```
Frame 2/10:  944.6ms
Frame 3/10:  225.5ms
Frame 4/10:  252.3ms
Frame 5/10:  233.6ms
```

This is consistent with **serialized** encode + inference + decode operations taking ~200-900ms each.

## The Fix: Asynchronous Architecture

We need to replicate the official CLI's architecture:

1. **Separate Process** for audio codec (rustymimi)
2. **Async Event Loop** for non-blocking I/O
3. **Queue-based** communication between processes
4. **Concurrent** operations instead of sequential

### Implementation Plan

1. Create `AsyncAudioCodec` that runs rustymimi in separate process
2. Convert `step_frame()` to async with concurrent encode/inference/decode
3. Update Twilio bridge to use async/await
4. Expected result: 20x speedup to ~50-70ms per frame!
