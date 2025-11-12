# Overnight Moshi Integration Progress

**Session Date:** 2025-11-12  
**Status:** MLX Implementation Complete, Awaiting Testing

---

## ✅ Completed Work

### 1. Tool Calling System (`assistant/tools/`)

**Files Created:**
- `tools/__init__.py` - Package exports
- `tools/registry.py` - Tool registry with JSON schema generation
- `tools/theme_tool.py` - Theme switching tool

**Features:**
- JSON schema generation for LLM context
- Tool call parsing: `TOOL_CALL: {"name": "...", "arguments": {...}}`
- Async tool execution with error handling
- Extensible architecture

**Flow:**
```
User: "Change to GLaDOS"
  ↓
Moshi generates: TOOL_CALL: {"name": "change_theme", "arguments": {"persona_name": "GLaDOS"}}
  ↓
System executes tool → Theme changes → Auto re-introduction
  ↓
GLaDOS: "Well well well, look who switched to me..."
```

### 2. Memory System Integration

**File:** `assistant/memory.py` (already existed from previous session)

**Features:**
- Dual-mode: HTTP API to server + in-memory fallback
- Auto-stores all messages with metadata (persona, tools used)
- Retrieved in `_build_conversation_prompt()` for context
- Max history: 100 messages

### 3. Persona Consistency

**Implementation:**
- `self.current_persona_name` reactive property
- Included in all prompts: "You are {persona}."
- Moshi identifies as current theme (JARVIS, GLaDOS, etc.)

### 4. Automatic Re-introductions

**Modified:** `generate_greeting(re_introduction=False)`

**Modes:**
- Initial: "You are {persona}. Greet the user warmly."
- Re-introduction: "You just changed to {persona}. Introduce yourself with enthusiasm!"

**Trigger:** Theme change tool automatically calls `generate_greeting(re_introduction=True)`

### 5. Comprehensive Conversation Prompts

**New Method:** `_build_conversation_prompt(persona) → str`

**Assembles:**
1. Persona identity: "You are {persona}."
2. System prompt: Full personality traits
3. Conversation history: Last 10 messages from memory
4. Tool descriptions: JSON schemas with usage instructions

### 6. Moshi MLX Bridge (`assistant/voice/moshi_mlx.py`)

**Why MLX?**
- PyTorch Moshi has MPS limitations on M3:
  - `torch.compile` for MPS is unstable
  - MPS has 4GB temp array limit - Moshi exceeds this
- MLX is Apple's framework optimized for Metal GPU
- Uses quantized models (4-bit or 8-bit) for efficiency

**Key Components:**
```python
class MoshiBridge:
    def __init__(
        self,
        hf_repo="kyutai/moshiko-mlx-q8",  # 8-bit quantized
        quantized=8,
        max_steps=500
    )
    
    def encode_audio(audio: np.ndarray) → np.ndarray:
        # RustyMimi codec (Rust implementation)
    
    def decode_audio(codes: np.ndarray) → np.ndarray:
        # RustyMimi decoder
    
    def generate_response(
        user_audio: np.ndarray,
        text_prompt: Optional[str],
        max_frames: int = 125
    ) → tuple[np.ndarray, str]:
        # MLX LmGen streaming generation
```

**Dependencies:**
- `mlx.core` & `mlx.nn` - Apple ML framework
- `rustymimi` - Fast Rust audio codec
- `moshi_mlx` - MLX models from Kyutai
- `sentencepiece` - Text tokenizer

**Models Downloaded:**
- `~/.cache/huggingface/hub/models--kyutai--moshiko-mlx-q8/` ✓
- `~/.cache/huggingface/hub/models--kyutai--moshiko-mlx-q4/` ✓

---

## 📊 Git Commits

1. `8900412` - Tool calling system with theme changes
2. `bb8d3e6` - Moshi API compatibility fixes
3. `2749eba` - Streaming API with LMGen
4. `88b3498` - Documentation

---

## ⏳ Pending Testing

### Phase 1: MLX Audio Generation
- ⏳ Initialize MoshiBridge with MLX
- ⏳ Test audio encoding/decoding
- ⏳ Test greeting generation
- ⏳ Verify text decoding works

### Phase 2: Voice Interaction
- ⏳ Mic input capture
- ⏳ Voice-to-voice conversation
- ⏳ Amplitude visualization

### Phase 3: Tool Calling
- ⏳ Theme change via voice
- ⏳ Automatic re-introduction
- ⏳ Persona consistency

### Phase 4: Memory & Context
- ⏳ Message storage
- ⏳ History retrieval
- ⏳ Context awareness

### Phase 5: Stability
- ⏳ 20+ message conversation
- ⏳ Multiple theme changes
- ⏳ No memory leaks
- ⏳ Smooth animations

---

## 🎯 Current Blocker: Mic Waveform Visualization

**User Request:** 
> "new dots appearing on the left are sized based on current mic amplitude, but then they stay that size scrolling off to the right, making a brief pattern based on mic input"

**Current Implementation:** `assistant/dashboard/widgets/panels/voice_visualizer_panel.py`
- Method: `_render_waveform_dots()` (lines 407-473)
- Uses dot characters: `[" ", "·", "•", "●", "⬤"]`
- Samples from end of buffer backwards (newest first)
- Should display: newest on left, scroll right

**Issue:** Implementation exists but needs verification/fixes before testing Moshi audio.

---

## 🔧 Technical Architecture

```
User Voice Input
    ↓
Audio Capture (sounddevice, 24kHz, 80ms chunks)
    ↓
Moshi MLX Encoding (RustyMimi → audio codes)
    ↓
Prompt Builder (persona + history + tools)
    ↓
Moshi LM Generation (MLX, quantized models)
    ↓
Tool Call Parser (checks for TOOL_CALL: pattern)
    ├─→ Tool Found: Execute → Update state → Re-introduce
    └─→ No Tool: Continue to playback
    ↓
Audio Decoding (RustyMimi → PCM audio)
    ↓
Playback (sounddevice output + amplitude visualization)
    ↓
Memory Storage (save message with metadata)
```

---

## 📝 Next Steps

1. **Fix mic waveform visualization** (current task)
2. **Test MLX audio generation** - Verify models load and generate
3. **Test full conversation flow** - Voice → Moshi → Tools → Memory
4. **Run stability tests** - Long conversations, theme changes
5. **Document results** - Update this file with test outcomes

---

**Auto-generated progress report**  
**Last Updated:** 2025-11-12 06:40 PST
