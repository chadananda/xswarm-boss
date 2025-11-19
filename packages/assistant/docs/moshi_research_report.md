# Moshi Capabilities Research Report

## Executive Summary

Moshi has **strong support for context/prompt injection and fine-grained control**, but **NO native tool use** and **minimal memory mechanisms**. The model can be extensively controlled through:

1. **Context Injection**: Transformer cross-attention, conditioner system, and embedding manipulation
2. **Persona Control**: Temperature, sampling parameters, and hooks for token-level influence
3. **Memory Integration**: Conv/context window management for limited conversation history
4. **Tool Use**: Not native - must be implemented at the tokenization/prompt level

---

## Our Implementation

We've built a complete personal assistant by wrapping Moshi with external systems for personality, memory, thinking, and tools.

### Architecture

```
User (voice) ←→ Moshi MLX ←→ Voice Server ←→ ThinkingEngine ←→ Tools
                   ↑                              ↓
                   └──── Context Injection ←──────┘
```

### Voice Server (`voice_server.py`)

ZeroMQ daemon running Moshi MLX in separate process:

- **Port 5555**: Commands (REQ/REP) - persona, context, history, transcript
- **Port 5556**: Audio in (PUSH/PULL) - mic samples to Moshi
- **Port 5557**: Audio out (PUB/SUB) - Moshi audio + text + amplitudes

Key APIs:
- `inject_context(text)` - Add text to Moshi's context window
- `inject_tool_result(tool, result)` - Inject tool output
- `get_new_text()` - Poll for Moshi's speech output
- `set_persona(name, prompt, traits)` - Configure personality

### ThinkingEngine (`thinking_engine.py`)

Background system monitoring conversations and deciding on actions:

**Two-step architecture:**
1. **Claude Haiku** - Fast decision: search memory? execute tool? inject context?
2. **Claude Sonnet 4.5** - Smart summarization for Moshi's ~3000 token limit

**Monitors:**
- User input (via `process_user_input()`)
- Moshi output (via polling `get_new_text()`)

**Actions:**
- Search memory → summarize → inject as context
- Execute tool → summarize result → inject
- Inject direct context (reminders, preferences)

### Tool System (`tools/`)

ToolRegistry with async handlers:

- **send_email** - SendGrid integration
- **make_call** - Twilio integration
- **search_memory** - Query conversation history
- **change_theme** - Switch TUI colors

Results are summarized to 2-3 sentences before injection.

### Context Management

Moshi has a small ~3000 token context window. We manage this by:

1. Tracking token usage via `get_context_usage()`
2. Summarizing all injections to be terse (max 150 tokens)
3. Clearing old context when needed
4. Using system prompt efficiently

### Example Flow

```
User: "What did we talk about yesterday?"
         ↓
ThinkingEngine (Haiku): Decide to search memory
         ↓
MemoryManager: Query last 24h conversations
         ↓
ThinkingEngine (Sonnet): Summarize to "Yesterday: discussed project deadlines,
                          you preferred morning meetings, asked about weather"
         ↓
voice_server.inject_context(summary)
         ↓
Moshi: "Yesterday we talked about your project deadlines and meeting preferences..."
```

---

## 1. CONTEXT & PROMPT INJECTION

### 1.1 Conditioner System (Primary Control Point)

The Moshi architecture includes a **ConditionProvider** that accepts structured conditioning:

**File**: `/tmp/moshi-official/moshi_mlx/moshi_mlx/modules/conditioner.py`

```python
class ConditionProvider(nn.Module):
    def __init__(self, output_dim: int, cfg: dict):
        self.conditioners = {}
        # Two conditioner types:
        # 1. LutConditioner - Look-up table for categorical values
        # 2. TensorConditioner - Direct tensor conditioning
```

**Two Types of Conditioners**:

#### LutConditioner (Categorical/Text Conditioning)
- Maps string values to embeddings via lookup table
- Configured in model config with `possible_values` mapping
- Example: speaker_id, emotion, formality_level, persona_type
- **Currently DISABLED in production models** (conditioners={} in LmConfig)

```python
class LutConditioner(nn.Module):
    def condition(self, value: str) -> mx.array:
        # "jarvis" -> embedding -> projected output
        # Shape: [1, 1, output_dim] added to transformer input
```

#### TensorConditioner (Continuous/Embedding Conditioning)
- Accepts arbitrary embeddings (e.g., from semantic encodings)
- Linear projection + sinusoidal positional encoding
- Allows injecting:
  - Speaker embeddings (voice cloning)
  - Semantic embeddings (context/mood)
  - Style embeddings (formality, emotion)

**Integration Point** (lm.py:474-475):
```python
if ct is not None:
    xs = xs + mx.expand_dims(ct.tensor, axis=1)  # Add to transformer input
```

### 1.2 Cross-Attention (Context Injection)

**File**: `/tmp/moshi-official/moshi_mlx/moshi_mlx/modules/transformer.py`

The transformer supports **cross-attention** for injecting external context:

```python
class CrossAttention(nn.Module):
    def __call__(self, xs: mx.array, cross_attention_src: mx.array, cache: LayerCache) -> mx.array:
        # Self-attention on sequence
        # Cross-attention to external context (external memory, documents, etc)
        # Cached cross-attention for efficiency
```

**Control Point** (lm.py:478-481):
```python
transformer_out = self.transformer(
    xs,
    cache=self.transformer_cache,
    cross_attention_src=cross_attention_src  # <-- External context here
)
```

**Use Cases**:
- Inject persona description as context
- Inject conversation history
- Inject knowledge base or facts
- Inject user profile information

### 1.3 Text Token Injection (Direct Prompt Engineering)

The text tokenizer is **SentencePiece** (32k vocabulary):
- Encode arbitrary text strings into token sequences
- Inject as initial context: `text_tokens = tokenizer.encode("You are Jarvis...")`
- LmGen prefixes generation with custom text prompts

**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/voice/moshi_mlx.py`
```python
# Can inject persona prompt via tokenization
persona_prompt_tokens = text_tokenizer.encode(persona_description)
# Feed as initial context to LmGen
```

---

## 2. TOOL USE CAPABILITIES

### 2.1 Native Support: NONE

Moshi is **NOT a function-calling model**. It has:
- No native tool/function calling mechanism
- No JSON output mode (audio + text only)
- No action tokens or special markers for tool invocation

### 2.2 Workaround: Prompt-Based Tool Use

Can be implemented via **text token injection**:

```python
# In system prompt:
"""
When you need to perform an action, emit a special token sequence:
[TOOL_CALL] action_name (param1=value1, param2=value2)
[/TOOL_CALL]

Available tools:
- search(query: str) - Search for information
- calculate(expression: str) - Perform calculation
- get_time() - Get current time
"""

# Parse output text for [TOOL_CALL] ... [/TOOL_CALL] patterns
# Execute tool, inject result back into context via cross-attention
```

**Advantages**:
- Works with standard tokenizer
- No model retraining needed
- Follows natural language patterns

**Disadvantages**:
- Hallucinations in bracket generation
- No structured output guarantee
- Text parsing required

### 2.3 Better Approach: Constrained Decoding

Implement at sampling level:
1. After each text token generation, check `text_logits`
2. If special "tool" tokens are high probability, force generation
3. Use logit_bias in Sampler to guide tool token probability

**File**: `/tmp/moshi-official/moshi_mlx/moshi_mlx/utils/sampling.py`

```python
@dataclass
class Sampler:
    logit_bias: dict[int, float] | None = None  # <-- Can bias toward tool tokens
    
    def __call__(self, logits: mx.array) -> tuple[mx.array, mx.array]:
        if self.logit_bias:
            indices = mx.array(list(self.logit_bias.keys()))
            values = mx.array(list(self.logit_bias.values()))
            logits[:, indices] += values  # Increase probability
```

---

## 3. MEMORY INTEGRATION

### 3.1 KV-Cache (Limited Conversation History)

Moshi uses **KV caching** for efficient autoregressive generation:

**File**: `/tmp/moshi-official/moshi_mlx/moshi_mlx/modules/kv_cache.py`

- Caches keys/values of past tokens
- Context window: **3000 tokens** (config.context)
- Resets between conversation turns (no automatic memory)

**Control Point** (lm.py:316):
```python
self.transformer_cache: list[LayerCache] = self.transformer.make_rot_cache()
```

To persist memory:
1. **Don't reset cache between turns**
2. **Inject previous conversation as text tokens**
3. **Use cross-attention with previous responses**

### 3.2 Context Window Management

**Model Configuration** (configs/moshi_7b_202409.json):
```json
{
  "context": 3000,      // Only 3000 tokens of history
  "max_seq_len": 4096,  // Max sequence length
  "max_period": 10000   // RoPE max period
}
```

**RoPE Positional Encoding**: Allows extrapolation beyond training context (with quality degradation)

### 3.3 Injecting Conversation History

**Current Implementation**:
```python
# In moshi_mlx.py generate_greeting() and step_frame()
# History not persisted between calls
```

**Can be Enhanced**:
```python
class ConversationMemory:
    def __init__(self, max_tokens=2000):
        self.history = []
        self.max_tokens = max_tokens
    
    def add_turn(self, user_text, user_audio, moshi_text, moshi_audio):
        self.history.append({
            'user': (user_text, user_audio),
            'moshi': (moshi_text, moshi_audio)
        })
    
    def get_context_tokens(self):
        # Convert history to text tokens
        # Return as cross-attention source
        context = "Previous conversation:\n"
        for turn in self.history[-10:]:  # Last 10 turns
            context += f"User: {turn['user'][0]}\nMoshi: {turn['moshi'][0]}\n"
        return tokenizer.encode(context)
```

---

## 4. FINE-GRAINED CONTROL MECHANISMS

### 4.1 Sampling Parameters (Temperature, Top-p, Top-k)

**File**: `/tmp/moshi-official/moshi_mlx/moshi_mlx/utils/sampling.py`

```python
@dataclass
class Sampler:
    temp: float = 0.8              # Temperature (0.0 = greedy, 1.0+ = diverse)
    top_p: float = 0.95            # Nucleus sampling threshold
    top_k: int | None = None       # Top-k sampling
    min_p: float = 0.0             # Min probability threshold
    min_tokens_to_keep: int = 1    # Minimum tokens to sample from
    logit_bias: dict[int, float] | None = None  # Token-specific biasing
```

**Control Points**:
```python
# In LmGen.step() -> model._sample()
text_token, _ = text_sampler(text_logits)  # <-- Can customize sampler
audio_tokens = self.depformer.sample(..., audio_sampler, ...)
```

**Dynamic Control**:
```python
# Adjust during generation
text_sampler = Sampler(temp=0.5, top_p=0.9)  # More focused
audio_sampler = Sampler(temp=0.8, top_k=100)  # More varied
```

### 4.2 Classifier-Free Guidance (cfg_coef)

**File** (lm.py:476-487):

```python
if cfg_coef != 1:
    xs = mx.tile(xs, (2, 1, 1))  # Double batch for guided + unguided
    # Generate two sets of logits
    l1, l2 = text_logits.split(2, axis=0)
    text_logits = cfg_coef * l1 - (cfg_coef - 1) * l2  # Guidance
```

**Use Cases**:
- cfg_coef > 1: Stronger adherence to conditioning (more "persona-like")
- cfg_coef = 1: No guidance
- cfg_coef < 1: Less guidance, more creative

**Current Usage**:
```python
# In our moshi_mlx.py
gen = models.LmGen(model, cfg_coef=1.0)  # Default, no guidance
# Can be adjusted:
gen = models.LmGen(model, cfg_coef=1.5)  # Strong persona guidance
```

### 4.3 Hooks for Token Inspection/Modification

**File** (lm.py:466-467, 489-500):

```python
def _sample(self, ..., on_text_hook=None, on_audio_hook=None):
    # Text tokens can be inspected
    if on_text_hook is not None:
        on_text_hook(text_token)  # Called after each text token
    
    # Audio tokens can be inspected
    if on_audio_hook is not None:
        on_audio_hook(audio_tokens)  # Called after audio tokens
```

**Use Case: Real-time Persona Monitoring**:
```python
def persona_monitor(token):
    token_text = tokenizer.id_to_piece(token[0].item())
    print(f"Generated: {token_text}")
    
    # Could log, filter, or redirect tokens here

gen = models.LmGen(..., on_text_hook=persona_monitor)
```

**Enhancement: Token Filtering**:
```python
def filter_tokens(token):
    # Could modify token generation
    # Check against persona vocabulary whitelist
    # Log to conversation history
    # Update UI in real-time
    pass
```

### 4.4 Logit Manipulation (Pre-sampling)

**Access Point**: After transformer output, before sampling

```python
# In custom sampling:
text_logits = model(...)  # Shape: [batch, vocab_size]

# Apply bias to favor certain tokens
bias = np.zeros(vocab_size)
for token_id in persona_preferred_tokens:
    bias[token_id] = 2.0  # Boost probability

text_logits += mx.array(bias)

# Sample from biased logits
token = text_sampler(text_logits)
```

---

## 5. PERSONALITY/PERSONA CONTROL

### 5.1 Current Implementation

**File**: `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/personas/config.py`

Our system has:
- **PersonalityTraits**: Big Five + custom dimensions (formality, enthusiasm, etc.)
- **VoiceSettings**: pitch, speed, tone, quality
- **ThemeConfig**: Colors, ASCII art, visual style
- **SystemPrompt**: Can be injected via text tokens

**Current Limitations**:
- System prompt is text-only (no conditioning token injection)
- No integration with Moshi's conditioner system (disabled in model)
- No dynamic trait adjustment during generation

### 5.2 Persona Injection Strategies

#### Strategy 1: System Prompt (Currently Used)
```python
persona_prompt = persona.build_system_prompt(include_personality=True)
# "You are Jarvis, curious and open to new ideas, professional and formal..."
# Encode and inject via text tokens
```

**Effectiveness**: Medium (text influence only)

#### Strategy 2: Sampling Adjustment (NEW)
```python
# Extract persona traits
traits = persona.traits

# Adjust samplers
text_sampler = Sampler(
    temp=0.5 + (traits.enthusiasm * 0.5),  # Excited = higher temp
    top_p=0.8 + (traits.formality * 0.15),  # Formal = more focused
)

audio_sampler = Sampler(
    temp=0.7 + (traits.extraversion * 0.3),  # Social = more varied
)
```

**Effectiveness**: High (controls generation style)

#### Strategy 3: Conditioner Tokens (FUTURE)
```python
# If conditioner system is re-enabled:
persona_embedding = encode_persona_traits(persona)  # [1, 1, 2048]
condition_tensor = ConditionTensor(tensor=persona_embedding)

# Pass to LmGen
text_token, audio_token = lm_gen._sample(
    ...,
    ct=condition_tensor  # Persona conditioning
)
```

**Effectiveness**: Very High (architectural integration)

#### Strategy 4: Voice Characteristics
```python
voice_settings = persona.voice
# pitch: affects audio codec parameters (not Moshi)
# speed: can be controlled via frame skip/repetition
# tone: can be influenced via prompt injection
# quality: cfg_coef can enhance quality/coherence
```

#### Strategy 5: Token Vocabulary Enforcement
```python
# Build persona vocabulary from config
preferred_tokens = tokenizer.encode(" ".join(persona.vocabulary['preferred_phrases']))
avoid_tokens = tokenizer.encode(" ".join(persona.vocabulary['avoid_phrases']))

# In logit_bias:
logit_bias = {
    token: 0.5 for token in preferred_tokens    # Boost
}
logit_bias.update({
    token: -2.0 for token in avoid_tokens       # Suppress
})

sampler = Sampler(logit_bias=logit_bias)
```

**Effectiveness**: High (explicit vocabulary control)

---

## 6. CONTROL POINT SUMMARY

### Injection Points (Input)
| Control Point | Type | Strength | Implementation |
|---|---|---|---|
| **Cross-Attention** | Context | Very High | Persona description, conversation history |
| **Text Token Injection** | Prompt | High | System prompt with traits |
| **Conditioner (LutConditioner)** | Embedding | Very High | Persona ID -> embedding (if enabled) |
| **Conditioner (TensorConditioner)** | Embedding | Very High | Continuous persona vectors (if enabled) |
| **Temperature** | Sampling | Medium | Trait-based adjustment |
| **Top-p/Top-k** | Sampling | Medium | Style-based adjustment |
| **Classifier-Free Guidance** | Generation | High | Force adherence to conditioning |
| **Logit Bias** | Sampling | High | Token whitelist/blacklist |

### Monitoring Points (Output)
| Control Point | Type | Strength | Implementation |
|---|---|---|---|
| **on_text_hook** | Callback | Medium | Real-time token inspection |
| **on_audio_hook** | Callback | Medium | Real-time audio token inspection |
| **KV Cache** | State | Medium | Access to transformer hidden states |
| **Text Tokenizer** | Decoding | High | Convert tokens back to text |

### Generation Control
| Control Point | Type | Strength | Implementation |
|---|---|---|---|
| **cfg_coef** | Strength | High | Force persona adherence (1.5-2.0) |
| **max_steps** | Length | High | Control generation length |
| **Sampler Type** | Quality | Medium | Switch between top-p, top-k, min-p |

---

## 7. MOSHI VS LLMS: KEY DIFFERENCES

### Moshi (Speech-Text Foundation Model)
- **Input**: Audio tokens + text tokens (interleaved)
- **Output**: Audio tokens + text tokens (interleaved)
- **Context Window**: 3000 tokens (shared audio+text)
- **Tool Use**: Not supported natively
- **Conditioning**: Architectural support (currently unused)
- **Latency**: ~200ms real-time capable
- **Focus**: Streaming speech dialogue

### LLMs (Text-Only, e.g., GPT-4)
- **Input**: Text tokens only
- **Output**: Text tokens only
- **Context Window**: 8000-128000 tokens
- **Tool Use**: Native function calling
- **Conditioning**: Prompt engineering only
- **Latency**: Batch processing (100ms-10s per request)
- **Focus**: General-purpose reasoning

### Implications for Persona+Memory+Tools
1. **Memory**: Moshi's shared context is more limited - need to rotate old data out
2. **Tools**: Implement via prompt patterns + text parsing, not native
3. **Persona**: Can use both prompting and sampling-level control
4. **Real-time**: Moshi is better for streaming; LLMs for batch reasoning

---

## 8. RECOMMENDED ARCHITECTURE FOR XSWARM

### Phase 1: Immediate (Persona Enhancement)
```python
# Leverage existing infrastructure
persona.traits -> Sampler parameters
persona.vocabulary -> logit_bias
persona.system_prompt -> text token injection
```

**Code Changes**: 20-30 lines in moshi_mlx.py

### Phase 2: Short-term (Memory Integration)
```python
# Conversation memory
ConversationMemory class
Store last N turns (text + implicit audio)
Inject as cross-attention context before each generation
```

**Code Changes**: 50-100 lines in voice layer

### Phase 3: Medium-term (Tool Use)
```python
# Prompt-based tool invocation
System prompt includes tool definitions
Parse [TOOL] markers in output
Execute tool, inject result back
```

**Code Changes**: 100-150 lines

### Phase 4: Long-term (Re-enable Conditioners)
```python
# If model is fine-tuned to accept conditioners
Encode persona traits as embeddings
Pass via ct: ConditionTensor
Requires model retraining (Kyutai labs resource)
```

**Effort**: High (needs training infrastructure)

---

## 9. CONSTRAINTS & LIMITATIONS

### Hard Limits
1. **No tool use** - Must implement via text parsing
2. **3000-token context** - Must rotate old data
3. **No training** - Can't fine-tune on xswarm data without GPU farm
4. **No native conditioning** - Conditioner system unused in current models
5. **Audio output only** - Can't return structured JSON

### Soft Limits
1. **Hallucinations** - May generate false tool calls
2. **Latency** - ~200ms real-time, not streaming-continuous
3. **Memory leaks** - KV cache grows if not reset
4. **Token counting** - Interleaved audio+text makes length prediction hard

### Workarounds
1. Use sampling parameters to reduce hallucinations
2. Implement token pruning in KV cache
3. Monitor token count and reset between turns
4. Use cfg_coef to enforce adherence to instructions

---

## 10. IMPLEMENTATION CHECKLIST

### Quick Wins (1-2 days)
- [ ] Integrate persona traits -> Sampler parameters
- [ ] Add vocabulary whitelist/blacklist via logit_bias
- [ ] Extract system prompt from PersonaConfig
- [ ] Add on_text_hook for real-time monitoring

### Medium Effort (3-5 days)
- [ ] Implement ConversationMemory class
- [ ] Wire cross-attention with memory context
- [ ] Add conversation history to system prompt
- [ ] Test multi-turn coherence

### High Effort (1-2 weeks)
- [ ] Implement tool use via text markers
- [ ] Parser for [TOOL_CALL] ... [/TOOL_CALL] patterns
- [ ] Integration layer for tool execution
- [ ] Fallback for malformed tool calls

### Research (TBD)
- [ ] Evaluate re-enabling conditioner system
- [ ] Contact Kyutai labs for fine-tuning guidance
- [ ] Explore audio-level persona control (pitch shift, etc.)
- [ ] Compare with whisper-based text transcription approach

---

## 11. REFERENCE FILES

### Moshi MLX Implementation
- `/tmp/moshi-official/moshi_mlx/moshi_mlx/models/lm.py` - Main model (_sample, sample methods)
- `/tmp/moshi-official/moshi_mlx/moshi_mlx/models/generate.py` - LmGen class
- `/tmp/moshi-official/moshi_mlx/moshi_mlx/modules/conditioner.py` - Conditioning system
- `/tmp/moshi-official/moshi_mlx/moshi_mlx/modules/transformer.py` - Cross-attention
- `/tmp/moshi-official/moshi_mlx/moshi_mlx/utils/sampling.py` - Sampler class

### Our Implementation
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/voice/moshi_mlx.py` - MLX bridge
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/personas/config.py` - Persona config
- `/Users/chad/Dropbox/Public/JS/Projects/xswarm-boss/packages/assistant/assistant/voice/conversation.py` - Conversation logic

### Configuration
- `/tmp/moshi-official/configs/moshi_7b_202409.json` - 7B model config (not used)
- `/tmp/moshi-official/moshi_mlx/moshi_mlx/models/lm.py:546-605` - 1B model config (used)

---

## 12. NEXT STEPS

1. **Validate**: Test sampler parameter control with personas
2. **Implement**: Add logit_bias and on_text_hook integration
3. **Measure**: Track persona consistency in generated speech
4. **Iterate**: A/B test different control strategies
5. **Scale**: Integrate memory and tool use

---

**Report Generated**: 2024-11-18
**Moshi Version**: 1.0 (Kyutai Labs)
**MLX Implementation**: Latest from /tmp/moshi-official
**Research Scope**: MLX implementation + our integration layer
