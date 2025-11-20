# Current Task (v0.1.0-2025.11.5.35)

## Goal
Automated MOSHI voice testing WITHOUT manual interaction.

## Status
❌ BUILD FAILED - 2 compile errors (borrow-after-move)

## The Bug
Lines 1160 & 1203 in voice.rs: trying to use `frame_samples.len()` after moving.

## The Fix
```rust
let frame_len = frame_samples.len();  // Store BEFORE move
all_audio_samples.extend(frame_samples);  // Move
// Use frame_len instead of frame_samples.len()
```

## Next: Fix both errors → Build → Test with `MOSHI_TEST_MODE=1 ~/.local/bin/xswarm --dev`
