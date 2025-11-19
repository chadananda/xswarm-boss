# Official MOSHI CLI Architecture Analysis

## Overview

After studying the official MOSHI CLI source code at `/private/tmp/moshi-official/moshi_mlx/moshi_mlx/local.py`, here are the **CRITICAL differences** between their implementation and ours.

## Key Architecture Differences

### 1. **TWO SEPARATE PROCESSES** (Not Just Codec Worker)

**Official CLI** (lines 279-286):
```python
# Process 1: CLIENT - Handles audio I/O and codec
p1 = multiprocessing.Process(target=client, args=subprocess_args)

# Process 2: SERVER - Handles MLX inference ONLY
p2 = multiprocessing.Process(target=server, args=subprocess_args)

p1.start()
p2.start()
```

**Our Implementation**:
- Single main process runs MLX inference
- Separate codec worker process for encode/decode
- **MISSING**: Audio I/O is NOT in separate process!

**Impact**: Their audio I/O (sounddevice callbacks) runs in completely separate process from MLX, eliminating any potential blocking or GIL issues.

---

### 2. **Server Process: Pure MLX Inference Loop**

**Official CLI Server Loop** (lines 123-144):
```python
while True:
    # BLOCKING wait for encoded audio from client
    data = client_to_server.get()

    # Convert to MLX array
    data = mx.array(data).transpose(1, 0)[:, :8]

    # Single step inference (FAST!)
    text_token = gen.step(data)
    text_token = text_token[0].item()

    # Get audio output
    audio_tokens = gen.last_audio_tokens()

    # Send back to client (non-blocking)
    if audio_tokens is not None:
        audio_tokens = np.array(audio_tokens).astype(np.uint32)
        server_to_client.put_nowait(audio_tokens)
```

**Key Points**:
- Uses `multiprocessing.Queue.get()` (BLOCKING) to wait for input
- No async/await in server loop
- Pure CPU/GPU inference, no I/O
- Non-blocking send to client (`put_nowait`)

**Our Implementation**:
- Similar structure, but runs in same process as codec
- Should be nearly identical

---

### 3. **Client Process: Async Audio I/O with 4 Concurrent Loops**

**Official CLI Client** (lines 163-199, 237-239):
```python
# Four concurrent async loops running simultaneously!
async def send_loop():
    """Read from input_queue → encode → (non-blocking)"""
    while True:
        await asyncio.sleep(0.001)
        try:
            pcm_data = input_queue.get(block=False)
            audio_tokenizer.encode(pcm_data)  # Non-blocking!
        except queue.Empty:
            continue

async def send_loop2():
    """Poll encoded results → send to server"""
    while True:
        data = audio_tokenizer.get_encoded()
        if data is None:
            await asyncio.sleep(0.001)
            continue
        client_to_server.put_nowait(data)

async def recv_loop2():
    """Receive from server → decode → (non-blocking)"""
    while True:
        try:
            audio_tokens = server_to_client.get(block=False)
        except queue.Empty:
            await asyncio.sleep(0.001)
            continue
        audio_tokenizer.decode(audio_tokens)  # Non-blocking!

async def recv_loop():
    """Poll decoded results → output_queue"""
    while True:
        data = audio_tokenizer.get_decoded()
        if data is None:
            await asyncio.sleep(0.001)
            continue
        output_queue.put_nowait(data)

# Run all 4 loops concurrently!
async def go():
    with in_stream, out_stream:
        await asyncio.gather(recv_loop(), send_loop(), recv_loop2(), send_loop2())

asyncio.run(go())  # ONE event loop for entire client lifetime
```

**Key Insights**:
1. **Four independent async loops** handling different stages
2. **asyncio.run() called ONCE** for entire session (not per frame!)
3. Audio I/O streams run with callbacks feeding queues
4. Codec operations are **polled asynchronously** with 1ms sleep

**Our Implementation**:
- ❌ We were calling `asyncio.run()` **per frame** (causing 30x slowdown!)
- ✅ We fixed to use synchronous queues in separate process
- ⚠️ But we're NOT using async loops for codec polling

---

### 4. **Model Loading: Runtime vs Pre-Quantized**

**Official CLI** (lines 88-106):

```python
# They support BOTH approaches!

# Option 1: Pre-quantized checkpoint (FASTER load, same inference speed)
if args.quantized == 8:
    model_file = hf_hub_download(args.hf_repo, "model.q8.safetensors")
elif args.quantized == 4:
    model_file = hf_hub_download(args.hf_repo, "model.q4.safetensors")

# Option 2: Runtime quantization (what we do)
else:
    model_file = hf_hub_download(args.hf_repo, "model.safetensors")

# Load BF16 model
model.set_dtype(mx.bfloat16)

# If using runtime quantization, quantize now
if args.quantized is not None:
    group_size = 32 if args.quantized == 4 else 64
    nn.quantize(model, bits=args.quantized, group_size=group_size)

model.load_weights(model_file, strict=True)
model.warmup()
```

**Key Differences**:
- They default to **pre-quantized checkpoints** (`kyutai/moshiko-mlx-q4` or `kyutai/moshiko-mlx-q8`)
- We default to **runtime quantization** (`kyutai/moshiko-mlx-bf16` → quantize at init)
- Same inference speed, but pre-quantized loads faster

**Our Implementation**:
- Uses `kyutai/moshiko-mlx-bf16` + runtime quantization
- This is CORRECT and should have same inference speed
- Pre-quantized would just save ~2-3s at startup

---

### 5. **Audio I/O: sounddevice Callbacks**

**Official CLI** (lines 201-235):

```python
# Input stream callback (runs in separate thread)
def on_input(in_data, frames, time, status):
    in_data = in_data[:, 0].astype(np.float32)
    input_queue.put_nowait(in_data)  # Non-blocking!

in_stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    blocksize=1920,  # 80ms frames
    callback=on_input
)

# Output stream callback (runs in separate thread)
def on_output(out_data, frames, time, status):
    try:
        pcm_data = output_queue.get(block=False)
        out_data[:, 0] = pcm_data
    except queue.Empty:
        out_data.fill(0)  # Output silence if queue empty

out_stream = sd.OutputStream(
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    blocksize=1920,
    callback=on_output
)
```

**Our Implementation**:
- Uses PyAudio with blocking read/write
- Should convert to sounddevice with callbacks for better performance

---

## Critical Findings

### ✅ What We Got Right:
1. Separate process for codec (avoiding GIL/blocking)
2. Runtime quantization with correct group sizes
3. MLX inference loop structure

### ⚠️ What We're Missing:
1. **Separate process for audio I/O** - Official runs client/server in separate processes
2. **Four concurrent async loops** - They have 4 loops polling codec operations
3. **sounddevice callbacks** - Non-blocking audio I/O instead of PyAudio blocking

### 🔍 Performance Bottleneck Hypothesis:

**Our 636ms per frame** likely comes from:
1. ❌ Audio I/O blocking in same process as inference (GIL contention?)
2. ❌ Not using async polling loops for codec (serialize encode→inference→decode)
3. ⚠️ Possibly MLX inference being CPU-bound due to process contention

**Their ~50ms per frame** comes from:
1. ✅ Complete process isolation (client audio I/O, server MLX inference)
2. ✅ Four async loops ensuring operations overlap maximally
3. ✅ Non-blocking audio I/O with sounddevice callbacks
4. ✅ Server process doing ONLY MLX inference (no I/O, no codec)

---

## Recommended Fixes

### Priority 1: Verify MLX Inference Speed in Isolation

Before restructuring everything, let's measure MLX inference **without any codec or I/O**:

```python
# Test: Pure MLX inference (no codec)
import mlx.core as mx
from assistant.voice import moshi_mlx

bridge = moshi_mlx.MoshiBridge(quality="q4")
lm_gen = bridge.create_lm_generator()

# Create dummy audio codes (bypass codec entirely)
dummy_codes = mx.zeros((8, 1), dtype=mx.int32)

# Time ONLY the inference step
import time
times = []
for i in range(100):
    t0 = time.time()
    text_token = lm_gen.step(dummy_codes)
    audio_tokens = lm_gen.last_audio_tokens()
    elapsed = (time.time() - t0) * 1000
    times.append(elapsed)

avg = sum(times) / len(times)
print(f"Pure MLX inference: {avg:.1f}ms")
```

**Expected**: ~40-60ms on M3 Metal
**If we see ~220ms**: MLX has a problem (not fully using GPU, process contention, etc.)
**If we see ~40-60ms**: Our codec/I/O architecture is the bottleneck

### Priority 2: If MLX is Fast, Implement Official Architecture

1. Split into two processes:
   - Client process: Audio I/O, codec, four async loops
   - Server process: MLX inference ONLY

2. Use sounddevice with callbacks instead of PyAudio

3. Implement four async loops like official CLI

### Priority 3: If MLX is Slow, Debug Model Loading

1. Try pre-quantized checkpoint (`kyutai/moshiko-mlx-q4`)
2. Check MLX device settings
3. Verify Metal GPU is actually being used
4. Compare model config with official CLI

---

## Next Steps

1. ✅ Document official CLI architecture (this file)
2. ⏳ Test pure MLX inference speed (Priority 1 above)
3. ⏳ Based on results, either:
   - Fix MLX configuration, OR
   - Implement full two-process architecture

---

## References

- Official CLI: `/private/tmp/moshi-official/moshi_mlx/moshi_mlx/local.py`
- Our implementation: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/voice/moshi_mlx.py`
- Performance test: `/tmp/moshi_q4_test.log`
