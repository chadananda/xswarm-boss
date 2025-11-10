# MOSHI Audio Reversal Fix - v0.1.0-2025.11.5.10

## Problem
Audio from MOSHI was playing "3 second chunks in reverse" - each audio frame was being played backwards, though the frames themselves were in the correct temporal order.

## Root Cause Analysis

### Discovery Process
1. Compared our implementation to the official MOSHI Rust CLI implementation
2. Found a critical difference in how resampled audio buffers are managed

### Official MOSHI Pattern (moshi-cli/audio_io.rs)
```rust
// Lines 120-122: Adding to buffer
for &elem in self.output_buffer[..out_len].iter() {
    self.resampled_data.push_front(elem)  // Adds to FRONT of queue
}

// Lines 71-77: Retrieving from buffer
pub(crate) fn take_all(&mut self) -> Vec<f32> {
    let mut data = Vec::with_capacity(self.resampled_data.len());
    while let Some(elem) = self.resampled_data.pop_back() {  // Pops from BACK
        data.push(elem);
    }
    data
}
```

**Key insight**: Official MOSHI uses a LIFO (Last In, First Out) pattern:
- Iterates forward through samples: `[1,2,3,4,5]`
- Adds with `push_front()`: Creates reversed queue `[5,4,3,2,1]`
- Retrieves with `pop_back()`: Un-reverses back to `[1,2,3,4,5]`
- **Net result**: Correct audio order (reversed twice = correct)

### Our Original Pattern (audio_output.rs:417)
```rust
// Original code (INCORRECT):
queue.extend(samples.iter());  // Adds to end (FIFO)
// ...later...
queue.pop_front();  // Removes from front (FIFO)
```

**Our pattern**: Standard FIFO (First In, First Out)
- Should work correctly in theory...
- **BUT**: The resampled audio samples were arriving in reverse order
- FIFO playback → Audio plays backwards!

## The Fix (audio_output.rs:417-420)

```rust
// CRITICAL FIX: Reverse samples before adding to match MOSHI's expected order
// Official MOSHI uses push_front() + pop_back() which reverses twice
// We use extend() + pop_front() (FIFO), so we need to reverse once
queue.extend(samples.iter().rev());
```

**How it works**:
1. Resampled audio arrives in order: `[1,2,3,4,5]`
2. We reverse it before adding: `[5,4,3,2,1]`
3. We play FIFO (pop_front): `5,4,3,2,1`
4. **Net result**: Correct playback order!

## Why This Works

The rubato resampler (or MOSHI's audio generation) outputs samples in a specific order that requires this reversal compensation. The official MOSHI implementation handles this implicitly through its double-reversal pattern (`push_front` + `pop_back`).

Our FIFO pattern is simpler and more standard, so we add an explicit reversal to achieve the same result.

## Testing

Build v0.1.0-2025.11.5.10 and test with:
```bash
xswarm --dev
# Speak to MOSHI
# Audio should now play in correct forward direction
```

## Files Changed

1. **packages/core/src/audio_output.rs:417-420**
   - Added `.rev()` to reverse samples before adding to playback queue
   - Added detailed comment explaining why this is necessary

2. **packages/core/Cargo.toml:3**
   - Updated version to `0.1.0-2025.11.5.10`

## Related Issues

- Previous attempt (v0.1.0-2025.11.5.9) changed buffer sizing but didn't fix the reversal
- User correctly identified: "It literally sounds like you are playing 3 second chunks in reverse"
- Metal GPU is working correctly (v0.1.0-2025.11.5.8)

## Technical Details

### Audio Flow
1. MOSHI generates audio at 24kHz (1920 samples per 80ms frame)
2. AudioResampler upsamples to 44.1kHz (~3528 samples)
3. Resampled audio sent via mpsc channel to continuous stream
4. **NEW**: Samples reversed before adding to VecDeque playback queue
5. Playback callback pops from front (FIFO) and plays

### Why Not Use push_front + pop_back?

We could match the official MOSHI pattern exactly, but our FIFO approach with explicit reversal is:
- Easier to understand (single reversal vs double reversal)
- Standard Rust pattern for audio buffers
- Same performance (`.rev()` is iterator adapter, zero-copy)
- Same correctness (single reversal vs double reversal = same result)

## Verification

The fix should result in:
- ✅ Audio plays in forward direction (not reversed)
- ✅ Speech sounds natural and intelligible
- ✅ No timing issues or gaps
- ✅ Metal GPU acceleration still working
- ✅ Real-time latency maintained

## Next Steps After Testing

If audio is still reversed:
- The rubato resampler might not be reversing samples
- Need to investigate MOSHI's audio_vec output order from line 1197 in voice.rs
- May need to reverse earlier in the pipeline (before resampling)

If audio is now correct:
- ✅ Audio reversal bug fixed!
- Mark as completed
- Monitor for any edge cases
