# Supercharging Moshi Context with Selective AI-Filtered Conversational Memory Using LibSQL

Modern AI agents demand highly relevant and important memory injections to operate within strict context limitations like those of Moshi. This guide explains—and provides a practical blueprint for—building the next generation of Moshi conversational memory, powered by LibSQL and filtered with application-level AI “thinking engines.” These engines bring human-like discernment over what memories truly deserve context injection, ensuring relevance, personalization, and high recall with minimal bloat.

## 1. Motivation and Overview

Instead of brute-force injecting top-k semantic memories, the protocol leverages a dedicated “thinking engine” (e.g. separate LLM, tool, or filtering module) to audit the candidate recalls against current conversational context. The agent only injects those that are **both relevant and important**, dramatically reducing context bloat and wasted tokens. This harnesses LibSQL’s scalable local vector/graph queries, Moshi’s monologue hooks, and a bespoke AI filter.

## 2. Architecture Deep Dive

### Storage and Retrieval (LibSQL)
- Store all utterances, metadata, and vector embeddings using libsql’s vector index and graph linking.
- At each query turn, retrieve top-k semantic matches.
- Optionally join graph/entity tables for additional chaining.

### AI-Filtered Injection Protocol
- The top-k candidate memories are submitted to the application-provided “thinking engine.”
- The thinking engine reviews recent context, user intent, session goal, and each candidate—scoring for relevance and importance.
- Only inject memories scoring above configured thresholds.

#### Why Filter?
- Moshi’s context window is tiny (512–4,096 tokens). Filtering avoids wasted injections and preserves only critical context.
- Human-like monologue: Only “things I should remind myself of” appear.
- Customizable for project, user style, session complexity.

## 3. Implementation Blueprint

### LibSQL Schema (Summary)
memory table:
id (INT, PK) | text (TEXT) | embedding (VECTOR) | timestamp (INT) | speaker (TEXT) | entities (TEXT) | emotions (TEXT)

graph_links:
parent_id (INT) | child_id (INT) | relation (TEXT)

### Retrieval and Filtering Pipeline

Step 1: On each Moshi turn, embed the current utterance, then retrieve top-k candidate memories using ANN search.

Step 2: Pass candidates and context to the thinking engine. Example API:

def filter_memories(context, candidates):
    scored = []
    for mem in candidates:
        # "score" can use LLM, classifier, or rule-based logic
        score = thinking_engine.evaluate_relevance(context, mem['text'])
        if score['relevant'] and score['important']:
            scored.append(mem)
    return scored

Step 3: Inject the approved (filtered) memories into Moshi’s context builder, either as inner monologue or explicit “injected memory” block.

def inject_memories(moshi_context, memories):
    for mem in memories:
        moshi_context.add_inner_monologue(mem['text'])

### Thinking Engine Approaches

- LLM Prompting: Provide few-shot exemplars (“If user talks colors, remind about last color preference only if it’s important.”).
- Rule-based: “Don’t inject memories older than one month unless they contain urgent tags or user references.”
- Hybrid: Use a lightweight classifier for importance, then LLM for detailed relevance.

### Configuration

- Thresholds for relevance/importance (experimental tuning).
- Top-k adjust for retrieval—filtering usually reduces final injection to 1–3 per turn.
- Switches for emotional weighting, recentness, and session goals.

## 4. Moshi Integration Points

- Retrieval script runs before each reply.
- Thinking engine takes recent context + top-k candidates, returns best subset.
- Moshi context module receives AI-filtered memories for injection.
- Logging function records which memories were considered, filtered, and injected.

## 5. Advanced Strategies

- Train/finetune the thinking engine on user-specific or domain-specific criteria.
- Use graph expansion for multi-hop relevance (“remind me of connected people in this project, if this topic comes up”).
- Experiment with Moshi monologue phrasing—e.g., “I should remember…”, “Recall: …”, or “Thinking: …”

## 6. Example Python Workflow

from libsql_client import Connection

conn = Connection("file:chat_memory.db")

def retrieve_top_k(embedding, k):
    return conn.execute(
        "SELECT * FROM memory JOIN vector_top_k ON memory.id = vector_top_k.rowid WHERE vector_top_k.embedding = ? LIMIT ?",
        (embedding, k)
    ).fetchall()

def filter_memories(context, candidates):
    approved = []
    for mem in candidates:
        decision = thinking_engine.score(context, mem["text"])
        if decision["relevant"] and decision["important"]:
            approved.append(mem)
    return approved

def inject_filtered_memories(context, memories):
    for mem in memories:
        context.add_inner_monologue(mem["text"])

## 7. Monitoring and Analytics

- Log candidate selection, scoring outcomes, injection stats for continuous refinement.
- Analytics dashboard: Show relevance hit rate, context window conservation, memory injection success.

## 8. Conclusion and Recommendations

This approach moves beyond simple “top-k” memory injection by integrating AI judgment into every memory recall, resulting in context-efficient, human-like conversational memory for Moshi. Combining LibSQL’s vector power, structured metadata, and a thinking engine filter, agents achieve maximum memory precision, personalization, and recall quality—unlocking world-class conversation even within tight context windows.

[1](https://turso.tech/blog/the-space-complexity-of-vector-indexes-in-libsql)
[2](https://turso.tech/blog/approximate-nearest-neighbor-search-with-diskann-in-libsql)
[3](https://kyutai.org/Moshi.pdf)
[4](https://news.ycombinator.com/item?id=45329322)
[5](https://www.reddit.com/r/vectordatabase/comments/1le5b0z/how_do_you_handle_memory_management_in_a_vector/)
[6](https://js.langchain.com/docs/integrations/vectorstores/libsql/)
[7](https://ai.plainenglish.io/personal-knowledge-graphs-in-ai-rag-powered-applications-with-libsql-50b0e7aa10c4)
[8](https://inclusioncloud.com/insights/blog/vector-databases-enterprise-ai/)
[9](https://towardsdatascience.com/retrieval-augmented-generation-in-sqlite/)
[10](https://mindsdb.com/blog/fast-track-knowledge-bases-how-to-build-semantic-ai-search-by-andriy-burkov)# Moshi Full-Duplex Streaming Test

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
# Moshi Phone Integration Test Results

**Date**: 2025-11-15
**Status**: ✅ CALL INITIATED - Testing in progress

## Summary

Successfully fixed Moshi initialization issues and made a test call to verify end-to-end Twilio + Moshi integration.

## Problems Fixed

### Issue: Slow Moshi Initialization (37+ minutes)

**Root Cause**: The `hf_transfer` library was installed and automatically activated by `huggingface_hub`. Even with `local_files_only=True`, it was making network requests to HuggingFace servers, causing connection errors and retries.

**Evidence**:
```
{"timestamp":"2025-11-15T00:31:13.646682Z","level":"WARN","fields":{"message":"Reqwest(reqwest::Error { kind: Request, url: \"https://transfer.xethub.hf.co/xorbs/default/cb0e13492e003437378f37d388f4a2a0cffccfb037da24b90ed346eba28c8ac0?...\" source: hyper_util::client::legacy::Error(Connect, Error { code: -9806, message: \"connection closed via error\" }) }). Retrying..."}}
```

**Fix Applied**:
Modified `packages/assistant/assistant/voice/moshi_mlx.py` to disable `hf_transfer` before importing `huggingface_hub`:

```python
# CRITICAL: Disable hf_transfer BEFORE importing huggingface_hub
# hf_transfer auto-enables when installed and ignores local_files_only=True
# This causes network requests and hangs when offline or files are cached
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
if "HF_HUB_ENABLE_HF_TRANSFER" in os.environ:
    del os.environ["HF_HUB_ENABLE_HF_TRANSFER"]
```

**Results**:
- **First run**: Downloaded 14GB model (2218 seconds / 37 minutes) - expected
- **Second run with cached models**: 7.6 seconds using Apple Silicon M3 GPU ✅

## Test Call Details

### Infrastructure Setup

1. **WebSocket Server**: Running on port 5001
   - Command: `python scripts/run_twilio_server.py --host 0.0.0.0 --port 5001`
   - Process ID: 4344
   - Status: Listening on `*:5001`

2. **Cloudflare Tunnel**: Exposing server to internet
   - URL: `wss://middle-crimes-reaches-hey.trycloudflare.com`
   - Protocol: QUIC
   - Location: sjc07 (San Jose)
   - Status: Connected

3. **Moshi Model**: Loaded and ready
   - Quality: q4 (4-bit quantization)
   - Load time: 7.6 seconds (with cached models)
   - GPU: Apple Silicon M3 Metal

### Call Details

- **From**: +18447472899 (Twilio number)
- **To**: +19167656913 (User's number)
- **Call SID**: CA86199979bd6562238cb70f53d3403ee0
- **Status**: queued → ringing → in-progress
- **WebSocket URL**: `wss://middle-crimes-reaches-hey.trycloudflare.com`

### TwiML Used

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting you to Moshi. Please wait.</Say>
    <Connect>
        <Stream url="wss://middle-crimes-reaches-hey.trycloudflare.com" />
    </Connect>
</Response>
```

## Expected Behavior

When the user answers the phone:

1. **IVR Message**: "Connecting you to Moshi. Please wait."
2. **WebSocket Connection**: Twilio connects to the server via Cloudflare tunnel
3. **Bidirectional Audio**:
   - User's voice (mulaw 8kHz) → Server → Moshi (PCM 24kHz)
   - Moshi response (PCM 24kHz) → Server → User (mulaw 8kHz)
4. **Interactive Conversation**: User can have a real conversation with Moshi

## Files Created/Modified

### Modified Files

- `packages/assistant/assistant/voice/moshi_mlx.py`:
  - Disabled `hf_transfer` at import time
  - Added verbose logging throughout initialization
  - Fixed model loading performance

### New Files

- `scripts/make_moshi_call.py`:
  - Script to make outbound calls with Moshi integration
  - Uses `python-dotenv` to load Twilio credentials
  - Creates TwiML for Media Streams WebSocket connection

- `docs/MOSHI_PHONE_TEST_RESULTS.md`:
  - This document

## Next Steps

1. **Await Call Completion**: User is currently on the call testing Moshi
2. **Monitor Server Logs**: Check for WebSocket connection and audio streaming
3. **Verify Audio Quality**: Ensure bidirectional audio works correctly
4. **Test Conversation**: Verify Moshi can understand and respond naturally
5. **Document Results**: Update this file with test outcomes

## Success Criteria

- [x] Moshi loads quickly (< 10 seconds with cached models)
- [x] Server starts and listens on port 5001
- [x] Cloudflare tunnel exposes server to internet
- [x] Call initiated successfully via Twilio API
- [ ] User answers call and hears IVR message
- [ ] WebSocket connection established
- [ ] User can hear Moshi's voice
- [ ] Moshi can hear user's voice
- [ ] Conversation is interactive and natural
- [ ] Audio quality is acceptable
- [ ] No latency/echo issues

## Technical Details

### System Specs
- **OS**: macOS Darwin 23.4.0
- **CPU**: Apple Silicon M3
- **GPU**: Metal (MLX framework)
- **Model**: Moshi MLX q4 (~2GB VRAM)

### Dependencies
- `moshi_mlx`: MLX-based Moshi implementation
- `rustymimi`: Rust audio codec
- `twilio`: Twilio API client
- `cloudflared`: Cloudflare tunnel client
- `websockets`: WebSocket server library

### Network Flow

```
User's Phone (mulaw 8kHz)
    ↓
Twilio Media Streams
    ↓
Cloudflare Tunnel (wss://)
    ↓
Local WebSocket Server (port 5001)
    ↓
Audio Converter (mulaw → PCM 24kHz)
    ↓
Moshi MLX (M3 GPU)
    ↓
Audio Converter (PCM 24kHz → mulaw)
    ↓
Local WebSocket Server
    ↓
Cloudflare Tunnel
    ↓
Twilio Media Streams
    ↓
User's Phone (mulaw 8kHz)
```

---

**Last Updated**: 2025-11-15 01:53 UTC
**Call Status**: IN PROGRESS - Awaiting user feedback
