# AUDIO GARBLING ROOT CAUSE - EXECUTIVE SUMMARY

## Problem
voice.rs produces **garbled, backwards-sounding audio** while gen.rs produces **clear, intelligible audio**.

## Root Cause
**Forced text token logic** in voice.rs (lines 1189-1270) constrains the language model to output specific text tokens. This breaks the semantic alignment between text and audio tokens that MOSHI learned during training.

## The Bug (One Line)
```rust
force_text_token,  // ← VARIABLE - sometimes Some(token), sometimes None
                   //   Should ALWAYS be None like gen.rs!
```

## Why It Breaks Audio
1. MOSHI trains text and audio tokens **together** as correlated sequences
2. When you **force** text tokens, the LM must follow an **unnatural** path
3. The audio tokens generated on this path don't match MIMI codec expectations
4. Result: Garbled waveform that sounds backwards/choppy
5. Whisper API falsely reports "success" because corrupted audio still has acoustic features

## The Fix
Delete 2 sections from voice.rs:

**1. Delete lines 1189-1195** (tokenize target phrase):
```rust
let test_phrase = "hello world testing one two three";
let pieces = moshi_state.text_tokenizer.encode(test_phrase)?;
let text_tokens: Vec<u32> = pieces.iter().map(|p| p.id as u32).collect();
// ... rest of initialization
```

**2. Replace lines 1255-1270** with:
```rust
let text_token = lm_generator.step_(
    Some(prev_text_token),
    &codes,
    None,  // ← Always None, natural generation
    None,
    conditions.as_ref(),
)?;
```

## Expected Results
| Before | After |
|--------|-------|
| Garbled audio | Clear, intelligible audio |
| Whisper: false positive | Whisper: accurate transcription |
| Unusable quality | Matches gen.rs (excellent) |

## Key Insight
This demonstrates why **small constraints in language models have huge impacts**:
- A single variable (`force_text_token`) instead of constant `None`
- Breaks the entire text-audio alignment
- Corrupts all downstream audio generation

## Technical Depth
For detailed analysis, see:
- `/AUDIO_ROOT_CAUSE_FOUND.md` - Quick reference
- `/COMPARISON_FINAL_REPORT.md` - Comprehensive analysis
- `/AUDIO_DIFF_SUMMARY.md` - Line-by-line code comparison
- `/docs/debugging/AUDIO_COMPARISON_ANALYSIS.md` - Deep technical dive
