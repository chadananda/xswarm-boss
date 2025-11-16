# TUI Layout Improvements - Implementation Complete

## Overview
Implemented four key improvements to the TUI layout and audio visualizer behavior for better user experience.

## Changes Implemented

### 1. Hide Audio Visualizer Until Voice Initialized ✅

**Problem**: Visualizer was visible on startup even though voice system wasn't ready yet.

**Solution**: 
- Set `visualizer.display = False` on initial compose
- Show visualizer (`display = True`) when `initialize_voice()` completes
- Also show visualizer when legacy `initialize_moshi()` completes

**Files Modified**:
- `packages/assistant/assistant/dashboard/app.py`:
  - Line 136: Set `viz_panel.display = False` in `compose()`
  - Lines 615-620: Show visualizer in `initialize_voice()`
  - Lines 719-725: Show visualizer in `initialize_moshi()`

### 2. Show Minimal Waveform When Idle ✅

**Problem**: Waveform was completely flat/empty when idle, making it unclear if system was working.

**Solution**:
- Apply baseline amplitude of 0.05 when state is "idle" or "ready"
- This creates minimal dot pattern showing system is alive
- Full amplitude response when speaking/listening

**Files Modified**:
- `packages/assistant/assistant/dashboard/app.py`:
  - Lines 1131-1134: Apply baseline to voice bridge amplitudes
  - Lines 1146-1148: Apply baseline to legacy audio callback amplitudes

**Behavior**:
- Idle/Ready: Small dots (baseline 0.05) scrolling across bottom
- Speaking/Listening: Full amplitude response to audio

### 3. Move Persona Name Below Visualizer ✅

**Problem**: Persona name was in header, but should be below visualizer for better layout.

**Solution**:
- Added new `Static` widget with id `persona-name` below visualizer
- Displays persona in format: `◈ JARVIS ◈`
- Centered and styled with theme colors

**Files Modified**:
- `packages/assistant/assistant/dashboard/app.py`:
  - Line 140: Added persona name Static widget in `compose()`
  - Lines 357-363: Initialize persona name in `on_mount()`
  - Lines 548-554: Update persona name on theme change
  - Lines 895-901: Update persona name on persona rotation

- `packages/assistant/assistant/dashboard/styles.tcss`:
  - Lines 203-212: Added CSS styling for `.persona-name-label`

**Styling**:
```css
.persona-name-label {
    width: 100%;
    height: 1;
    text-align: center;
    color: $shade-5;  /* Lightest shade */
    text-style: bold;
    margin: 1 0;
    padding: 0 0;
}
```

### 4. Change Header to "xSwarm Assistant" ✅

**Problem**: Header showed persona name, but should be static "xSwarm Assistant".

**Solution**:
- Changed `visualizer.border_title` to static "xSwarm Assistant"
- Removed all dynamic persona name updates to visualizer title
- Kept persona name in separate label below visualizer

**Files Modified**:
- `packages/assistant/assistant/dashboard/app.py`:
  - Line 353: Set static title in `on_mount()`
  - Line 723: Keep static title in `initialize_moshi()` (removed dynamic update)
  - Line 554: Removed visualizer title update in theme change handler
  - Line 901: Removed visualizer title update in persona rotation

## Layout Structure

```
┌─ xSwarm Assistant ─────────────┐
│                                 │  <- Visualizer panel (hidden until voice ready)
│   [Audio Visualization]         │
│                                 │
└─────────────────────────────────┘
          ◈ JARVIS ◈                <- Persona name (centered, dynamic)

┌─ Tabs ─────────────────────────┐
│  📊  Status                     │
│  ⚙️   Settings                  │
│  🔧  Tools                      │
│  💬  Chat                       │
└─────────────────────────────────┘
```

## Testing Checklist

To verify all changes are working:

### Visual Tests
- [ ] **On startup**: Visualizer is hidden (only see persona name and tabs)
- [ ] **After ~30s**: Visualizer appears when Moshi models load
- [ ] **Idle state**: Minimal waveform with small dots scrolling (not flat)
- [ ] **Speaking**: Full amplitude waveform responds to voice
- [ ] **Persona name**: Shows centered below visualizer (e.g., "◈ JARVIS ◈")
- [ ] **Header**: Always shows "xSwarm Assistant" (never changes)

### Interaction Tests
- [ ] **Theme change**: Persona name updates, header stays "xSwarm Assistant"
- [ ] **Persona rotation**: Persona name updates, visualizer still shows
- [ ] **Voice toggle**: Waveform responds, then returns to minimal baseline

## Code Quality

### Clean Implementation
- No code duplication
- Proper error handling with try/except blocks
- Consistent naming conventions
- Comments explain intent

### Maintainability
- All visualizer title changes centralized in `on_mount()`
- Persona name updates use single query pattern
- Baseline amplitude logic isolated in `update_visualizer()`

## Performance Impact

- **Minimal**: Only adds one Static widget (persona name label)
- **Baseline amplitude**: Simple max() operation, negligible overhead
- **Display toggle**: Native Textual property, no performance impact

## Browser Compatibility

N/A - This is a terminal TUI application.

## Accessibility

- Clear visual hierarchy with persona name separated from visualizer
- Minimal waveform provides feedback that system is active
- Static header reduces cognitive load (no unexpected changes)

## Future Enhancements

Potential improvements (not in scope):
1. Animate persona name on change (fade/pulse effect)
2. Add persona avatar/icon next to name
3. Make baseline amplitude configurable
4. Add loading spinner before visualizer appears

## Related Documentation

- `docs/testing-guide.md` - Comprehensive testing guide
- `packages/assistant/assistant/dashboard/app.py` - Main TUI application
- `packages/assistant/assistant/dashboard/widgets/panels/voice_visualizer_panel.py` - Visualizer widget

## Implementation Date

2025-11-16

## Author

Claude Code (Coder Agent)
